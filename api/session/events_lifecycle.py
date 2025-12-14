"""
Session Lifecycle Helpers
Created: 2025-12-13 02:12:00
Last Modified: 2025-12-14 00:18:00
Version: 1.0.4
Description: Session başlatma, sonlandırma ve fault yönetimi mixin'i.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict

from api.event_detector import ESP32State, EventType
from api.logging_config import log_event, log_incident, system_logger
from api.session.events_logging import SessionEventLoggingMixin
from api.session.session import ChargingSession
from api.session.status import SessionStatus
from api.station_info import get_station_info


class SessionLifecycleMixin(SessionEventLoggingMixin):
    """Session yaşam döngüsü işlemleri."""

    @staticmethod
    def _extract_meter_import_energy_kwh(meter_reading: Any) -> Any:
        """
        Meter'dan mümkünse import enerji register'ını (kWh) seçer.

        Not: Mobile tarafındaki canlı enerji `energy_import_kwh` register'ını önceliklendiriyor.
        Session başlangıç/bitişinde aynı register baz alınmazsa ACTIVE session için delta hesabı
        tutarsızlaşabilir ve `session.energy_kwh` alanı null kalabilir.
        """
        try:
            totals = getattr(meter_reading, "totals", None)
            if isinstance(totals, dict):
                if totals.get("energy_import_kwh") is not None:
                    return totals.get("energy_import_kwh")
                if totals.get("energy_kwh") is not None:
                    return totals.get("energy_kwh")
        except Exception:
            pass
        return getattr(meter_reading, "energy_kwh", None)

    def _start_session(self, event_data: Dict[str, Any]):
        with self.sessions_lock:
            if self.current_session:
                system_logger.warning(
                    f"Yeni session başlatılıyor ama aktif session var: {self.current_session.session_id}"
                )
                self._end_session_internal(
                    self.current_session,
                    datetime.now(),
                    event_data.get("to_state", ESP32State.CHARGING.value),
                    SessionStatus.CANCELLED,
                )

            session_id = str(uuid.uuid4())
            start_time = datetime.now()
            start_state = event_data.get("to_state", ESP32State.CHARGING.value)

            # Tek konnektör varsayımı: DB'de ACTIVE kalan başka session varsa kapat
            try:
                self.db.cancel_other_active_sessions(
                    exclude_session_id=None,
                    end_time=start_time,
                    end_state=start_state,
                    status=SessionStatus.CANCELLED.value,
                )
            except Exception:
                # Non-critical; session start devam eder
                pass

            session = ChargingSession(session_id, start_time, start_state)
            session.add_event(EventType.CHARGE_STARTED, event_data)

            user_id = event_data.get("user_id") or event_data.get("data", {}).get(
                "user_id"
            )
            if not user_id:
                with self.pending_user_id_lock:
                    user_id = self.pending_user_id
                    self.pending_user_id = None

            if user_id:
                session.metadata["user_id"] = user_id

            self.current_session = session

            if self.meter:
                try:
                    # Başlangıçta meter bağlantısı düşmüşse tekrar bağlanmayı dene
                    if hasattr(self.meter, "is_connected") and hasattr(
                        self.meter, "connect"
                    ):
                        try:
                            if not self.meter.is_connected():
                                self.meter.connect()
                        except Exception:
                            pass
                    meter_reading = self.meter.read_all()
                    if meter_reading and meter_reading.is_valid:
                        start_energy = self._extract_meter_import_energy_kwh(
                            meter_reading
                        )
                        if start_energy is not None:
                            session.metadata["start_energy_kwh"] = start_energy
                        session.metadata["meter_available"] = True
                except Exception as exc:
                    system_logger.warning(
                        f"Meter okuma hatası (session başlangıcı): {exc}"
                    )
                    session.metadata["meter_available"] = False
            else:
                session.metadata["meter_available"] = False

            self.db.create_session(
                session_id=session_id,
                start_time=start_time,
                start_state=start_state,
                events=session.events,
                metadata=session.metadata,
                user_id=user_id,
            )

            self._save_event_to_table(EventType.CHARGE_STARTED, event_data, user_id)

            self._log_session_snapshot(
                session_id=session_id,
                event_label=EventType.CHARGE_STARTED.value,
                summary="Session started",
                event_data=event_data,
                user_id=user_id,
            )

            self._cleanup_old_sessions()

            system_logger.info(
                f"Yeni session başlatıldı: {session_id}",
                extra={"session_id": session_id, "start_time": start_time.isoformat()},
            )

            log_event(
                event_type="SESSION_STARTED",
                event_data={
                    "session_id": session_id,
                    "start_time": start_time.isoformat(),
                    "start_state": start_state,
                },
            )

    def _end_session(self, event_type: EventType, event_data: Dict[str, Any]):
        with self.sessions_lock:
            if not self.current_session:
                system_logger.warning(
                    "Session sonlandırma denemesi ama aktif session yok"
                )
                return

            status = (
                SessionStatus.CANCELLED
                if event_type == EventType.CABLE_DISCONNECTED
                else SessionStatus.COMPLETED
            )

            end_state = event_data.get("to_state", ESP32State.STOPPED.value)
            user_id = event_data.get("user_id") or event_data.get("data", {}).get(
                "user_id"
            )

            self.current_session.add_event(event_type, event_data)
            self._save_event_to_table(event_type, event_data, user_id)
            self._end_session_internal(
                self.current_session, datetime.now(), end_state, status
            )

            self.current_session = None

    def _end_session_internal(
        self,
        session: ChargingSession,
        end_time: datetime,
        end_state: int,
        status: SessionStatus,
    ):
        session.end_session(end_time, end_state, status)

        final_metrics = self._calculate_final_metrics(session, end_time)

        if self.meter and self.meter.is_connected():
            try:
                meter_reading = self.meter.read_all()
                if meter_reading and meter_reading.is_valid:
                    end_energy = self._extract_meter_import_energy_kwh(meter_reading)
                    start_energy = session.metadata.get("start_energy_kwh")

                    if start_energy is not None:
                        total_energy = end_energy - start_energy
                        session.metadata["end_energy_kwh"] = end_energy
                        session.metadata["total_energy_kwh"] = max(0, total_energy)
                        session.metadata["energy_source"] = "meter"
                        # Meter varsa total_energy metriklerini meter delta ile normalize et
                        try:
                            final_metrics["start_energy_kwh"] = float(start_energy)
                            final_metrics["end_energy_kwh"] = float(end_energy)
                            final_metrics["total_energy_kwh"] = float(
                                max(0, total_energy)
                            )
                        except Exception:
                            pass

                        # Meter varsa güç/akım/voltaj metriklerini CPV/PPV gibi ham değerlerden değil,
                        # gerçek meter ölçümlerinden türet (saha doğruluğu).
                        try:
                            duration_s = int(
                                final_metrics.get("charging_duration_seconds") or 0
                            ) or int(final_metrics.get("duration_seconds") or 0)
                            total_energy_kwh = float(max(0, total_energy))
                            if duration_s > 0 and total_energy_kwh >= 0:
                                hours = duration_s / 3600.0
                                avg_power_kw = (
                                    (total_energy_kwh / hours) if hours > 0 else None
                                )
                                if avg_power_kw is not None:
                                    avg_power_kw = round(avg_power_kw, 3)
                                    final_metrics["avg_power_kw"] = avg_power_kw
                                    # Max/min için örnekleme yoksa avg ile normalize et (en azından fiziksel aralıkta kalsın)
                                    final_metrics["max_power_kw"] = avg_power_kw
                                    final_metrics["min_power_kw"] = avg_power_kw

                            phase_values = getattr(meter_reading, "phase_values", None)
                            if isinstance(phase_values, dict):
                                pv_v = phase_values.get("voltage_v") or {}
                                pv_i = phase_values.get("current_a") or {}
                                voltages = [
                                    pv_v.get("l1"),
                                    pv_v.get("l2"),
                                    pv_v.get("l3"),
                                ]
                                currents = [
                                    pv_i.get("l1"),
                                    pv_i.get("l2"),
                                    pv_i.get("l3"),
                                ]
                                voltages = [float(v) for v in voltages if v is not None]
                                currents = [float(i) for i in currents if i is not None]
                                if voltages:
                                    final_metrics["max_voltage_v"] = round(
                                        max(voltages), 2
                                    )
                                    final_metrics["min_voltage_v"] = round(
                                        min(voltages), 2
                                    )
                                    final_metrics["avg_voltage_v"] = round(
                                        sum(voltages) / len(voltages), 2
                                    )
                                if currents:
                                    final_metrics["max_current_a"] = round(
                                        max(currents), 2
                                    )
                                    final_metrics["min_current_a"] = round(
                                        min(currents), 2
                                    )
                                    final_metrics["avg_current_a"] = round(
                                        sum(currents) / len(currents), 2
                                    )

                            # Maliyet için faydalı metadata (DB alanı eklemeden)
                            try:
                                station_info = get_station_info() or {}
                                per_kwh = station_info.get("price_per_kwh")
                                if per_kwh is not None:
                                    per_kwh_f = float(per_kwh)
                                    session.metadata["price_per_kwh"] = per_kwh_f
                                    session.metadata["total_cost"] = round(
                                        total_energy_kwh * per_kwh_f, 2
                                    )
                            except Exception:
                                pass
                        except Exception:
                            # Non-critical; session kapanışını bozma
                            pass
                    else:
                        session.metadata["end_energy_kwh"] = end_energy
                        try:
                            final_metrics["end_energy_kwh"] = float(end_energy)
                        except Exception:
                            pass
            except Exception as exc:
                system_logger.warning(f"Meter okuma hatası (session bitişi): {exc}")
                session.metadata["energy_source"] = "calculated"
        else:
            session.metadata["energy_source"] = "calculated"

        self.db.update_session(
            session_id=session.session_id,
            end_time=end_time,
            end_state=end_state,
            status=status.value,
            events=session.events,
            metadata=session.metadata,
            **final_metrics,
        )

        # Tek konnektör varsayımı: DB'de ACTIVE kalan başka session varsa kapat (ghost session önleme)
        try:
            self.db.cancel_other_active_sessions(
                exclude_session_id=session.session_id,
                end_time=end_time,
                end_state=end_state,
                status=SessionStatus.CANCELLED.value,
            )
        except Exception:
            pass

        system_logger.info(
            f"Session sonlandırıldı: {session.session_id}",
            extra={
                "session_id": session.session_id,
                "end_time": end_time.isoformat(),
                "status": status.value,
                "duration_seconds": (end_time - session.start_time).total_seconds(),
            },
        )

        log_event(
            event_type="SESSION_ENDED",
            event_data={
                "session_id": session.session_id,
                "end_time": end_time.isoformat(),
                "status": status.value,
                "duration_seconds": (end_time - session.start_time).total_seconds(),
            },
        )

        self._log_session_snapshot(
            session_id=session.session_id,
            event_label="SESSION_ENDED",
            summary=f"Session ended with status {status.value}",
            event_data={
                "from_state": session.start_state,
                "to_state": end_state,
            },
            status=status.value,
            metrics=final_metrics,
        )

    def _handle_fault(self, event_data: Dict[str, Any]):
        with self.sessions_lock:
            if self.current_session:
                self.current_session.add_event(EventType.FAULT_DETECTED, event_data)
                self.current_session.status = SessionStatus.FAULTED

                self.db.update_session(
                    session_id=self.current_session.session_id,
                    status=SessionStatus.FAULTED.value,
                    events=self.current_session.events,
                    metadata=self.current_session.metadata,
                )

                self._log_session_snapshot(
                    self.current_session.session_id,
                    EventType.FAULT_DETECTED.value,
                    "Fault detected during session",
                    event_data=event_data,
                    severity="warning",
                )
                log_incident(
                    title="Session fault detected",
                    severity="warning",
                    description="ESP32 fault event kaydedildi",
                    session_id=self.current_session.session_id,
                    event_data=event_data,
                )
