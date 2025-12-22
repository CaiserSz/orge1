"""
Event Detection Module
Created: 2025-12-09 22:50:00
Last Modified: 2025-12-22 06:05:00
Version: 1.1.1
Description: ESP32 state transition detection ve event classification modülü
"""

import os
import sys
import logging
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from api.config import config
from api.event_types import ESP32State, EventType
from api.logging_config import log_event, log_incident, system_logger

__all__ = ["EventDetector", "ESP32State", "EventType", "get_event_detector"]

_STATE_NAMES: dict[int, str] = {
    0: "HARDFAULT_END",
    1: "IDLE",
    2: "CABLE_DETECT",
    3: "EV_CONNECTED",
    4: "READY",
    5: "CHARGING",
    6: "PAUSED",
    7: "STOPPED",
    8: "FAULT_HARD",
}


class EventDetector:
    """ESP32 state transition detection + event classification."""

    def __init__(self, bridge_getter: Callable):
        """EventDetector (bridge_getter: ESP32Bridge döndüren callable)."""
        self.bridge_getter = bridge_getter
        self.current_state: Optional[int] = None
        self.previous_state: Optional[int] = None
        self.state_lock = threading.Lock()
        self.is_monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self.event_callbacks: list[Callable] = []

        # Resume validation (PAUSED -> CHARGING) için stateful kontrol
        self._resume_validation_lock = threading.Lock()
        self._resume_validation_in_progress = False
        self._resume_last_suppressed_monotonic: Optional[float] = None

    def start_monitoring(self):
        """Event detection monitoring'i başlat."""
        if self.is_monitoring:
            return

        self.is_monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        system_logger.info("Event detection monitoring başlatıldı")

    def stop_monitoring(self):
        """Event detection monitoring'i durdur."""
        self.is_monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
        system_logger.info("Event detection monitoring durduruldu")

    def _monitor_loop(self):
        """State monitoring döngüsü (bridge status poll)."""
        while self.is_monitoring:
            try:
                bridge = self.bridge_getter()
                if bridge and bridge.is_connected:
                    status = bridge.get_status()
                    if status and "STATE" in status:
                        state = status["STATE"]
                        self._check_state_transition(state, status)
                time.sleep(0.5)  # 500ms bekleme
            except Exception as e:
                system_logger.error(
                    f"Event detection monitor loop error: {e}", exc_info=True
                )
                time.sleep(1.0)  # Hata durumunda daha uzun bekle

    def _check_state_transition(self, new_state: int, status: Dict[str, Any]):
        """State transition kontrolü ve event üretimi."""
        # Not: PAUSED -> CHARGING transition bazı araçlarda UI paused iken kısa süreli "bounce" yapabilir.
        # Bu nedenle bu transition'ı "resume" olarak kabul etmeden önce meter power + debounce ile doğruluyoruz.
        with self.state_lock:
            prev_state = self.current_state

            # İlk durum - event oluşturma
            if prev_state is None:
                self.previous_state = None
                self.current_state = new_state
                system_logger.debug(f"İlk state tespit edildi: {new_state}")
                return

            # State değişmemişse event oluşturma
            if prev_state == new_state:
                return

            # Resume adayı: PAUSED -> CHARGING (doğrulama yapılacak)
            if (
                prev_state == ESP32State.PAUSED.value
                and new_state == ESP32State.CHARGING.value
                and bool(getattr(config, "RESUME_VALIDATION_ENABLED", True))
            ):
                # current_state'i PAUSED olarak bırakıyoruz; doğrulama geçerse CHARGING'e geçirip event üreteceğiz
                self._schedule_resume_validation(status=status)
                return

            # Normal transition: state'i güncelle ve event oluştur
            self.previous_state = prev_state
            self.current_state = new_state

        # Lock dışında event üret (callback'ler ağır olabilir)
        event_type = self._classify_event(prev_state, new_state)
        if event_type:
            self._create_event(event_type, prev_state, new_state, status)

    def _schedule_resume_validation(self, status: Dict[str, Any]) -> None:
        """PAUSED -> CHARGING için power-threshold tabanlı resume doğrulamasını başlat."""
        now_mono = time.monotonic()
        cooldown = float(
            getattr(config, "RESUME_SUPPRESS_COOLDOWN_SECONDS", 30.0) or 0.0
        )
        last_suppressed = self._resume_last_suppressed_monotonic
        if last_suppressed is not None and (now_mono - last_suppressed) < cooldown:
            return

        with self._resume_validation_lock:
            if self._resume_validation_in_progress:
                return
            self._resume_validation_in_progress = True

        threading.Thread(
            target=self._resume_validation_worker,
            daemon=True,
            name="resume_validation_worker",
        ).start()

    def _resume_validation_worker(self) -> None:
        """Resume doğrulama worker'ı."""
        min_power_kw = float(getattr(config, "RESUME_MIN_POWER_KW", 1.0) or 1.0)
        debounce_seconds = float(
            getattr(config, "RESUME_DEBOUNCE_SECONDS", 10.0) or 0.0
        )
        sample_interval = float(
            getattr(config, "RESUME_SAMPLE_INTERVAL_SECONDS", 1.0) or 1.0
        )
        required_consecutive = int(
            getattr(config, "RESUME_REQUIRED_CONSECUTIVE_SAMPLES", 3) or 3
        )
        required_consecutive = max(1, required_consecutive)

        start_mono = time.monotonic()
        consecutive = 0
        last_power_kw: Optional[float] = None
        last_status: Optional[Dict[str, Any]] = None

        def _read_power_kw() -> Optional[float]:
            try:
                from api.meter import get_meter

                meter = get_meter()
                if not meter:
                    return None
                # best-effort connect
                try:
                    if hasattr(meter, "connect") and hasattr(meter, "is_connected"):
                        if not meter.is_connected():
                            meter.connect()
                except Exception:
                    pass

                reading = meter.read_all() if hasattr(meter, "read_all") else None
                if not reading or not getattr(reading, "is_valid", False):
                    return None
                power_kw = getattr(reading, "power_kw", None)
                return float(power_kw) if isinstance(power_kw, (int, float)) else None
            except Exception:
                return None

        try:
            while (time.monotonic() - start_mono) <= debounce_seconds:
                # En güncel status'ı al (araç fiilen CHARGING değilse doğrulamayı kes)
                bridge = None
                try:
                    bridge = self.bridge_getter()
                except Exception:
                    bridge = None

                try:
                    if bridge and getattr(bridge, "is_connected", False):
                        last_status = bridge.get_status()
                    else:
                        last_status = None
                except Exception:
                    last_status = None

                state_val = None
                if isinstance(last_status, dict):
                    state_val = last_status.get("STATE")

                # Araç tekrar PAUSED/STOPPED/IDLE'a döndüyse resume doğrulamasını iptal et
                if (
                    state_val is not None
                    and int(state_val) != ESP32State.CHARGING.value
                ):
                    break

                last_power_kw = _read_power_kw()
                if last_power_kw is not None and last_power_kw >= min_power_kw:
                    consecutive += 1
                    if consecutive >= required_consecutive:
                        # Resume doğrulandı: state'i güncelle ve CHARGE_STARTED event'i üret
                        with self.state_lock:
                            self.previous_state = ESP32State.PAUSED.value
                            self.current_state = ESP32State.CHARGING.value

                        payload_status = (
                            last_status if isinstance(last_status, dict) else {}
                        )
                        self._create_event(
                            EventType.CHARGE_STARTED,
                            ESP32State.PAUSED.value,
                            ESP32State.CHARGING.value,
                            payload_status,
                        )
                        return
                else:
                    consecutive = 0

                time.sleep(sample_interval)

            # Resume doğrulanamadı → suppress et (event üretme)
            self._resume_last_suppressed_monotonic = time.monotonic()
            log_event(
                event_type="RESUME_SUPPRESSED",
                event_data={
                    "reason": "resume_not_validated_by_power_threshold",
                    "min_power_kw": min_power_kw,
                    "required_consecutive_samples": required_consecutive,
                    "debounce_seconds": debounce_seconds,
                    "sample_interval_seconds": sample_interval,
                    "last_power_kw": last_power_kw,
                    "last_status": last_status,
                },
                level=logging.INFO,
            )
        finally:
            with self._resume_validation_lock:
                self._resume_validation_in_progress = False

    def _classify_event(self, from_state: int, to_state: int) -> Optional[EventType]:
        """State transition -> EventType (bilinen mapping yoksa STATE_CHANGED)."""
        # Not: ESP32 firmware bazı akışlarda READY'yi atlayıp EV_CONNECTED/IDLE -> CHARGING geçebilir.
        s = ESP32State
        transitions = {
            (s.IDLE.value, s.CABLE_DETECT.value): EventType.CABLE_CONNECTED,
            (s.CABLE_DETECT.value, s.EV_CONNECTED.value): EventType.EV_CONNECTED,
            (s.EV_CONNECTED.value, s.READY.value): EventType.CHARGE_READY,
            (s.READY.value, s.CHARGING.value): EventType.CHARGE_STARTED,
            (s.EV_CONNECTED.value, s.CHARGING.value): EventType.CHARGE_STARTED,
            (s.IDLE.value, s.CHARGING.value): EventType.CHARGE_STARTED,
            (s.CHARGING.value, s.PAUSED.value): EventType.CHARGE_PAUSED,
            (s.PAUSED.value, s.CHARGING.value): EventType.CHARGE_STARTED,
            (s.CHARGING.value, s.STOPPED.value): EventType.CHARGE_STOPPED,
            (s.PAUSED.value, s.STOPPED.value): EventType.CHARGE_STOPPED,
            (s.CHARGING.value, s.IDLE.value): EventType.CHARGE_STOPPED,
            (s.PAUSED.value, s.IDLE.value): EventType.CHARGE_STOPPED,
            (s.CABLE_DETECT.value, s.IDLE.value): EventType.CABLE_DISCONNECTED,
            (s.EV_CONNECTED.value, s.IDLE.value): EventType.CABLE_DISCONNECTED,
            # Firmware davranışı: PAUSED -> READY görülebiliyor; genel state değişikliği olarak loglanır.
            (s.PAUSED.value, s.READY.value): EventType.STATE_CHANGED,
            (s.FAULT_HARD.value, s.HARDFAULT_END.value): EventType.FAULT_DETECTED,
            (s.HARDFAULT_END.value, s.IDLE.value): EventType.STATE_CHANGED,
        }

        # Fault detection (herhangi bir state'den FAULT_HARD'a geçiş)
        # NOT: FAULT_HARD → HARDFAULT_END transition'ı yukarıda tanımlı
        if (
            to_state == ESP32State.FAULT_HARD.value
            and from_state != ESP32State.HARDFAULT_END.value
        ):
            return EventType.FAULT_DETECTED

        # Bilinen transition
        transition_key = (from_state, to_state)
        if transition_key in transitions:
            return transitions[transition_key]

        # Bilinmeyen transition - genel state değişikliği
        return EventType.STATE_CHANGED

    def _create_event(
        self,
        event_type: EventType,
        from_state: int,
        to_state: int,
        status: Dict[str, Any],
    ):
        """Event oluştur, logla ve callback'leri çağır."""
        event_data = {
            "event_type": event_type.value,
            "from_state": from_state,
            "to_state": to_state,
            "from_state_name": self._get_state_name(from_state),
            "to_state_name": self._get_state_name(to_state),
            "timestamp": datetime.now().isoformat(),
            "status": status,
        }

        log_event(event_type=event_type.value, event_data=event_data)

        incident_payload = self._detect_power_supply_warning(status)
        if incident_payload:
            log_incident(
                title=incident_payload["title"],
                severity=incident_payload.get("severity", "warning"),
                description=incident_payload.get("description"),
                status=status,
                event_type=event_type.value,
            )

        failed_callbacks = []
        for i, callback in enumerate(self.event_callbacks):
            try:
                callback(event_type, event_data)
            except Exception as e:
                system_logger.error(
                    f"Event callback error (callback {i}): {e}", exc_info=True
                )
                failed_callbacks.append(i)

        if failed_callbacks:
            for i in reversed(failed_callbacks):
                try:
                    self.event_callbacks.pop(i)
                    system_logger.warning(
                        f"Hatalı callback listeden çıkarıldı (index {i})"
                    )
                except IndexError:
                    pass

    def _get_state_name(self, state: int) -> str:
        """State değerinden state adını döndür."""
        return _STATE_NAMES.get(state, f"UNKNOWN_{state}")

    def _detect_power_supply_warning(
        self, status: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Status sözlüğünde EV'nin güç alamadığına dair işaretleri arar."""
        if not status:
            return None

        warning_text = ""
        for key in ("WARNING", "MESSAGE", "MSG"):
            value = status.get(key)
            if isinstance(value, str):
                warning_text = value.lower()
                break

        if warning_text and "external" in warning_text and "power" in warning_text:
            return {
                "title": "Vehicle power warning",
                "description": status.get(
                    key, "Vehicle reports external equipment issue."
                ),
                "severity": "warning",
            }

        return None

    def register_callback(self, callback: Callable):
        """Event callback kaydet (signature: callback(event_type, event_data))."""
        self.event_callbacks.append(callback)

    def unregister_callback(self, callback: Callable):
        """Event callback kaldır."""
        if callback in self.event_callbacks:
            self.event_callbacks.remove(callback)

    def get_current_state(self) -> Optional[int]:
        """Mevcut state değerini döndür."""
        with self.state_lock:
            return self.current_state

    def get_previous_state(self) -> Optional[int]:
        """Önceki state değerini döndür."""
        with self.state_lock:
            return self.previous_state


# Singleton instance
event_detector_instance: Optional[EventDetector] = None
event_detector_lock = threading.Lock()


def get_event_detector(bridge_getter: Callable) -> EventDetector:
    """EventDetector singleton instance'ı döndür."""
    global event_detector_instance

    if event_detector_instance is None:
        with event_detector_lock:
            if event_detector_instance is None:
                event_detector_instance = EventDetector(bridge_getter)

    return event_detector_instance
