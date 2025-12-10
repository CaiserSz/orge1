"""
Session Events Module
Created: 2025-12-10 20:40:00
Last Modified: 2025-12-10 20:40:00
Version: 1.0.0
Description: Session event handling metodları - Event operations mixin
"""

import os
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

# Logging modülünü import et
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from api.event_detector import ESP32State, EventType
from api.logging_config import log_event, system_logger
from api.session.metrics import calculate_power
from api.session.session import ChargingSession
from api.session.status import SessionStatus


class SessionEventMixin:
    """
    Session event handling metodları mixin
    Bu mixin SessionManager sınıfına event handling metodlarını ekler
    """

    def _on_event(self, event_type: EventType, event_data: Dict[str, Any]):
        """
        Event Detector'dan gelen event'leri işle

        Args:
            event_type: Event type
            event_data: Event data dict'i
        """
        try:
            # charge_start event'ini dinle ve user_id'yi sakla
            if event_type == EventType.CHARGE_START_REQUESTED:
                user_id = event_data.get("user_id")
                if user_id:
                    with self.pending_user_id_lock:
                        self.pending_user_id = user_id

            # Session başlatma event'leri
            if event_type == EventType.CHARGE_STARTED:
                # Resume kontrolü: Eğer aktif session varsa ve son state PAUSED ise,
                # yeni session oluşturma, mevcut session'a event ekle
                if self.current_session:
                    # Son event'i kontrol et - CHARGE_PAUSED var mı?
                    last_event_type = None
                    if self.current_session.events:
                        last_event = self.current_session.events[-1]
                        last_event_type = last_event.get("event_type")

                    # Eğer son event CHARGE_PAUSED ise, bu resume durumudur
                    if last_event_type == EventType.CHARGE_PAUSED.value:
                        # Resume: Mevcut session'a CHARGE_STARTED event'i ekle
                        self.current_session.add_event(event_type, event_data)
                        # Metrikleri güncelle (real-time)
                        self._update_session_metrics(event_data)
                        # user_id'yi event_data'dan çıkar
                        user_id = event_data.get("user_id") or event_data.get(
                            "data", {}
                        ).get("user_id")
                        # Normalized event tablosuna kaydet
                        self._save_event_to_table(event_type, event_data, user_id)
                        # Database'e kaydet
                        self.db.update_session(
                            session_id=self.current_session.session_id,
                            events=self.current_session.events,
                            metadata=self.current_session.metadata,
                        )
                        system_logger.info(
                            f"Resume event'i mevcut session'a eklendi: {self.current_session.session_id}"
                        )
                    else:
                        # Yeni session başlat (normal CHARGE_STARTED)
                        self._start_session(event_data)
                else:
                    # Aktif session yok, yeni session başlat
                    self._start_session(event_data)

            # Session sonlandırma event'leri
            elif event_type in [
                EventType.CHARGE_STOPPED,
                EventType.CABLE_DISCONNECTED,
            ]:
                self._end_session(event_type, event_data)

            # Aktif session'a event ekle
            elif self.current_session:
                self.current_session.add_event(event_type, event_data)
                # Metrikleri güncelle (real-time)
                self._update_session_metrics(event_data)
                # user_id'yi event_data'dan çıkar
                user_id = event_data.get("user_id") or event_data.get("data", {}).get(
                    "user_id"
                )
                # Normalized event tablosuna kaydet
                self._save_event_to_table(event_type, event_data, user_id)
                # Database'e kaydet (backward compatibility için events JSON'ı da koru)
                self.db.update_session(
                    session_id=self.current_session.session_id,
                    events=self.current_session.events,
                    metadata=self.current_session.metadata,
                )

            # Fault durumunda session'ı fault olarak işaretle
            elif event_type == EventType.FAULT_DETECTED:
                self._handle_fault(event_data)

        except Exception as e:
            system_logger.error(
                f"Session manager event handling error: {e}", exc_info=True
            )

    def _start_session(self, event_data: Dict[str, Any]):
        """
        Yeni session başlat

        Args:
            event_data: Event data dict'i
        """
        with self.sessions_lock:
            # Eğer zaten aktif bir session varsa, önce onu sonlandır
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

            # Yeni session oluştur
            session_id = str(uuid.uuid4())
            start_time = datetime.now()
            start_state = event_data.get("to_state", ESP32State.CHARGING.value)

            session = ChargingSession(session_id, start_time, start_state)
            session.add_event(EventType.CHARGE_STARTED, event_data)

            # user_id'yi event_data'dan veya pending_user_id'den al
            user_id = event_data.get("user_id") or event_data.get("data", {}).get(
                "user_id"
            )
            # Eğer event_data'da yoksa, pending_user_id'den al
            if not user_id:
                with self.pending_user_id_lock:
                    user_id = self.pending_user_id
                    self.pending_user_id = None  # Kullanıldıktan sonra temizle

            # user_id'yi metadata'ya ekle
            if user_id:
                session.metadata["user_id"] = user_id

            # Normalized event tablosuna kaydet
            self._save_event_to_table(EventType.CHARGE_STARTED, event_data, user_id)

            # Meter'dan başlangıç enerji seviyesini oku (eğer meter varsa)
            if self.meter and self.meter.is_connected():
                try:
                    meter_reading = self.meter.read_all()
                    if meter_reading and meter_reading.is_valid:
                        session.metadata["start_energy_kwh"] = meter_reading.energy_kwh
                        session.metadata["meter_available"] = True
                except Exception as e:
                    system_logger.warning(
                        f"Meter okuma hatası (session başlangıcı): {e}"
                    )
                    session.metadata["meter_available"] = False
            else:
                session.metadata["meter_available"] = False

            # Database'e kaydet
            self.db.create_session(
                session_id=session_id,
                start_time=start_time,
                start_state=start_state,
                events=session.events,
                metadata=session.metadata,
                user_id=user_id,
            )

            self.current_session = session

            # Maksimum session sayısını kontrol et
            self._cleanup_old_sessions()

            system_logger.info(
                f"Yeni session başlatıldı: {session_id}",
                extra={"session_id": session_id, "start_time": start_time.isoformat()},
            )

            # Session başlatma event'ini logla
            log_event(
                event_type="SESSION_STARTED",
                event_data={
                    "session_id": session_id,
                    "start_time": start_time.isoformat(),
                    "start_state": start_state,
                },
            )

    def _end_session(self, event_type: EventType, event_data: Dict[str, Any]):
        """
        Aktif session'ı sonlandır

        Args:
            event_type: Event type (CHARGE_STOPPED veya CABLE_DISCONNECTED)
            event_data: Event data dict'i
        """
        with self.sessions_lock:
            if not self.current_session:
                system_logger.warning(
                    "Session sonlandırma denemesi ama aktif session yok"
                )
                return

            # Session durumunu belirle
            if event_type == EventType.CABLE_DISCONNECTED:
                status = SessionStatus.CANCELLED
            else:  # CHARGE_STOPPED
                status = SessionStatus.COMPLETED

            end_state = event_data.get("to_state", ESP32State.STOPPED.value)
            # user_id'yi event_data'dan çıkar
            user_id = event_data.get("user_id") or event_data.get("data", {}).get(
                "user_id"
            )

            # CHARGE_STOPPED event'ini session'a ekle (sonlandırmadan önce)
            self.current_session.add_event(event_type, event_data)

            # Normalized event tablosuna kaydet
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
        """
        Session'ı içsel olarak sonlandır

        Args:
            session: Sonlandırılacak session
            end_time: Bitiş zamanı
            end_state: Bitiş state'i
            status: Session durumu
        """
        session.end_session(end_time, end_state, status)

        # Final metrikleri hesapla
        final_metrics = self._calculate_final_metrics(session, end_time)

        # Meter'dan bitiş enerji seviyesini oku (eğer meter varsa)
        if self.meter and self.meter.is_connected():
            try:
                meter_reading = self.meter.read_all()
                if meter_reading and meter_reading.is_valid:
                    end_energy = meter_reading.energy_kwh
                    start_energy = session.metadata.get("start_energy_kwh")

                    if start_energy is not None:
                        # Gerçek enerji tüketimi = bitiş - başlangıç
                        total_energy = end_energy - start_energy
                        session.metadata["end_energy_kwh"] = end_energy
                        session.metadata["total_energy_kwh"] = max(
                            0, total_energy
                        )  # Negatif olamaz
                        session.metadata["energy_source"] = "meter"
                    else:
                        # Başlangıç enerjisi yoksa sadece bitiş enerjisini kaydet
                        session.metadata["end_energy_kwh"] = end_energy
            except Exception as e:
                system_logger.warning(f"Meter okuma hatası (session bitişi): {e}")
                session.metadata["energy_source"] = (
                    "calculated"  # Fallback: hesaplanmış
                )
        else:
            session.metadata["energy_source"] = (
                "calculated"  # Meter yok, hesaplanmış kullan
            )

        # Database'e kaydet (metriklerle birlikte)
        self.db.update_session(
            session_id=session.session_id,
            end_time=end_time,
            end_state=end_state,
            status=status.value,
            events=session.events,
            metadata=session.metadata,
            **final_metrics,  # Tüm metrikleri kaydet
        )

        system_logger.info(
            f"Session sonlandırıldı: {session.session_id}",
            extra={
                "session_id": session.session_id,
                "end_time": end_time.isoformat(),
                "status": status.value,
                "duration_seconds": (end_time - session.start_time).total_seconds(),
            },
        )

        # Session sonlandırma event'ini logla
        log_event(
            event_type="SESSION_ENDED",
            event_data={
                "session_id": session.session_id,
                "end_time": end_time.isoformat(),
                "status": status.value,
                "duration_seconds": (end_time - session.start_time).total_seconds(),
            },
        )

    def _handle_fault(self, event_data: Dict[str, Any]):
        """
        Fault durumunu işle

        Args:
            event_data: Event data dict'i
        """
        with self.sessions_lock:
            if self.current_session:
                self.current_session.add_event(EventType.FAULT_DETECTED, event_data)
                # Session'ı fault olarak işaretle ama sonlandırma
                # (CABLE_DISCONNECTED veya CHARGE_STOPPED event'i gelecek)
                self.current_session.status = SessionStatus.FAULTED

                # Database'e kaydet
                self.db.update_session(
                    session_id=self.current_session.session_id,
                    status=SessionStatus.FAULTED.value,
                    events=self.current_session.events,
                    metadata=self.current_session.metadata,
                )

    def _save_event_to_table(
        self,
        event_type: EventType,
        event_data: Dict[str, Any],
        user_id: Optional[str] = None,
    ):
        """
        Event'i normalized session_events tablosuna kaydet

        Args:
            event_type: Event type
            event_data: Event data dict'i
            user_id: User ID (opsiyonel)
        """
        if not self.current_session:
            return

        try:
            status = event_data.get("status", {})
            current_a = status.get("CABLE") or status.get("CURRENT")
            voltage_v = status.get("CPV") or status.get("PPV")
            power_kw = None
            if current_a is not None and voltage_v is not None:
                power_kw = calculate_power(current_a, voltage_v)

            # user_id'yi session'dan al (eğer event_data'da yoksa)
            if not user_id:
                user_id = self.current_session.metadata.get("user_id")

            self.db.create_event(
                session_id=self.current_session.session_id,
                event_type=event_type.value,
                event_timestamp=datetime.now(),
                from_state=event_data.get("from_state"),
                to_state=event_data.get("to_state"),
                from_state_name=event_data.get("from_state_name"),
                to_state_name=event_data.get("to_state_name"),
                current_a=current_a,
                voltage_v=voltage_v,
                power_kw=power_kw,
                event_data=event_data,
                status_data=status,
                user_id=user_id,
            )
        except Exception as e:
            system_logger.warning(f"Event kaydetme hatası (session_events): {e}")
