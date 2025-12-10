"""
Event Detection Module
Created: 2025-12-09 22:50:00
Last Modified: 2025-12-09 22:50:00
Version: 1.0.0
Description: ESP32 state transition detection ve event classification modülü
"""

import threading
import time
from typing import Optional, Dict, Any, Callable
from datetime import datetime
from enum import Enum
import sys
import os

# Logging modülünü import et
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from api.logging_config import system_logger, log_event

# ESP32 State değerleri (ESP32 firmware'den)
class ESP32State(Enum):
    """ESP32 state değerleri"""
    HARDFAULT_END = 0  # ESP32 firmware'de tanımlı (Commercial_08122025.ino:197)
    IDLE = 1
    CABLE_DETECT = 2
    EV_CONNECTED = 3
    READY = 4
    CHARGING = 5
    PAUSED = 6
    STOPPED = 7
    FAULT_HARD = 8

# Event types
class EventType(Enum):
    """Event type'ları"""
    CABLE_CONNECTED = "CABLE_CONNECTED"
    EV_CONNECTED = "EV_CONNECTED"
    CHARGE_READY = "CHARGE_READY"
    CHARGE_STARTED = "CHARGE_STARTED"
    CHARGE_PAUSED = "CHARGE_PAUSED"
    CHARGE_STOPPED = "CHARGE_STOPPED"
    CHARGE_START_REQUESTED = "CHARGE_START_REQUESTED"  # charge_start log event'i için
    CABLE_DISCONNECTED = "CABLE_DISCONNECTED"
    FAULT_DETECTED = "FAULT_DETECTED"
    STATE_CHANGED = "STATE_CHANGED"  # Genel state değişikliği


class EventDetector:
    """
    ESP32 state transition detection ve event classification modülü

    State transition'ları izler ve event'leri oluşturur.
    Event'ler structured logging ile loglanır.
    """

    def __init__(self, bridge_getter: Callable):
        """
        Event Detector başlatıcı

        Args:
            bridge_getter: ESP32Bridge instance'ı döndüren callable
        """
        self.bridge_getter = bridge_getter
        self.current_state: Optional[int] = None
        self.previous_state: Optional[int] = None
        self.state_lock = threading.Lock()
        self.is_monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self.event_callbacks: list[Callable] = []

    def start_monitoring(self):
        """Event detection monitoring'i başlat"""
        if self.is_monitoring:
            return

        self.is_monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        system_logger.info("Event detection monitoring başlatıldı")

    def stop_monitoring(self):
        """Event detection monitoring'i durdur"""
        self.is_monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
        system_logger.info("Event detection monitoring durduruldu")

    def _monitor_loop(self):
        """
        State monitoring döngüsü

        ESP32 bridge'den state değerlerini alır ve transition'ları tespit eder.
        """
        while self.is_monitoring:
            try:
                bridge = self.bridge_getter()
                if bridge and bridge.is_connected:
                    status = bridge.get_status()
                    if status and 'STATE' in status:
                        state = status['STATE']
                        self._check_state_transition(state, status)
                time.sleep(0.5)  # 500ms bekleme
            except Exception as e:
                system_logger.error(f"Event detection monitor loop error: {e}", exc_info=True)
                time.sleep(1.0)  # Hata durumunda daha uzun bekle

    def _check_state_transition(self, new_state: int, status: Dict[str, Any]):
        """
        State transition kontrolü ve event oluşturma

        Args:
            new_state: Yeni state değeri
            status: Tam status dict'i
        """
        with self.state_lock:
            self.previous_state = self.current_state
            self.current_state = new_state

            # İlk durum - event oluşturma
            if self.previous_state is None:
                system_logger.debug(f"İlk state tespit edildi: {new_state}")
                return

            # State değişmemişse event oluşturma
            if self.previous_state == self.current_state:
                return

            # State transition tespit edildi
            event_type = self._classify_event(self.previous_state, self.current_state)
            if event_type:
                self._create_event(event_type, self.previous_state, self.current_state, status)

    def _classify_event(self, from_state: int, to_state: int) -> Optional[EventType]:
        """
        State transition'dan event type belirleme

        Args:
            from_state: Önceki state
            to_state: Yeni state

        Returns:
            EventType veya None
        """
        # State transition mapping
        transitions = {
            (ESP32State.IDLE.value, ESP32State.CABLE_DETECT.value): EventType.CABLE_CONNECTED,
            (ESP32State.CABLE_DETECT.value, ESP32State.EV_CONNECTED.value): EventType.EV_CONNECTED,
            (ESP32State.EV_CONNECTED.value, ESP32State.READY.value): EventType.CHARGE_READY,
            (ESP32State.READY.value, ESP32State.CHARGING.value): EventType.CHARGE_STARTED,
            # EV_CONNECTED → CHARGING transition (ESP32 firmware gerçek davranışı)
            # Authorization verildikten sonra READY'ye geçmeden direkt CHARGING state'ine geçebilir
            (ESP32State.EV_CONNECTED.value, ESP32State.CHARGING.value): EventType.CHARGE_STARTED,
            # IDLE → CHARGING transition (ESP32 firmware gerçek davranışı)
            # Authorization verildikten sonra direkt CHARGING state'ine geçebilir
            (ESP32State.IDLE.value, ESP32State.CHARGING.value): EventType.CHARGE_STARTED,
            (ESP32State.CHARGING.value, ESP32State.PAUSED.value): EventType.CHARGE_PAUSED,
            # PAUSED → CHARGING transition (şarja devam etme)
            # Suspended durumundan şarja devam edildiğinde CHARGE_STARTED event'i üretilmeli
            (ESP32State.PAUSED.value, ESP32State.CHARGING.value): EventType.CHARGE_STARTED,
            (ESP32State.CHARGING.value, ESP32State.STOPPED.value): EventType.CHARGE_STOPPED,
            (ESP32State.PAUSED.value, ESP32State.STOPPED.value): EventType.CHARGE_STOPPED,
            (ESP32State.CABLE_DETECT.value, ESP32State.IDLE.value): EventType.CABLE_DISCONNECTED,
            (ESP32State.EV_CONNECTED.value, ESP32State.IDLE.value): EventType.CABLE_DISCONNECTED,
            # PAUSED → READY transition (ESP32 firmware gerçek davranışı)
            # NOT: ESP32 firmware'de bu transition mantık hatası olabilir (CHARGING olmalı)
            # Ancak gerçek davranış bu olduğu için RPi tarafı buna uyum sağlamalı
            (ESP32State.PAUSED.value, ESP32State.READY.value): EventType.STATE_CHANGED,
            # Fault handling transitions
            (ESP32State.FAULT_HARD.value, ESP32State.HARDFAULT_END.value): EventType.FAULT_DETECTED,
            (ESP32State.HARDFAULT_END.value, ESP32State.IDLE.value): EventType.STATE_CHANGED,
        }

        # Fault detection (herhangi bir state'den FAULT_HARD'a geçiş)
        # NOT: FAULT_HARD → HARDFAULT_END transition'ı yukarıda tanımlı
        if to_state == ESP32State.FAULT_HARD.value and from_state != ESP32State.HARDFAULT_END.value:
            return EventType.FAULT_DETECTED

        # Bilinen transition
        transition_key = (from_state, to_state)
        if transition_key in transitions:
            return transitions[transition_key]

        # Bilinmeyen transition - genel state değişikliği
        return EventType.STATE_CHANGED

    def _create_event(self, event_type: EventType, from_state: int, to_state: int, status: Dict[str, Any]):
        """
        Event oluşturma ve loglama

        Args:
            event_type: Event type
            from_state: Önceki state
            to_state: Yeni state
            status: Tam status dict'i
        """
        event_data = {
            "event_type": event_type.value,
            "from_state": from_state,
            "to_state": to_state,
            "from_state_name": self._get_state_name(from_state),
            "to_state_name": self._get_state_name(to_state),
            "timestamp": datetime.now().isoformat(),
            "status": status
        }

        # Event'i logla
        log_event(
            event_type=event_type.value,
            event_data=event_data
        )

        # Callback'leri çağır (hata toleranslı)
        failed_callbacks = []
        for i, callback in enumerate(self.event_callbacks):
            try:
                callback(event_type, event_data)
            except Exception as e:
                system_logger.error(f"Event callback error (callback {i}): {e}", exc_info=True)
                # Hatalı callback'i işaretle (sonra temizlenecek)
                failed_callbacks.append(i)

        # Hatalı callback'leri listeden çıkar (ters sırada, index kaymasını önlemek için)
        if failed_callbacks:
            for i in reversed(failed_callbacks):
                try:
                    removed_callback = self.event_callbacks.pop(i)
                    system_logger.warning(f"Hatalı callback listeden çıkarıldı (index {i})")
                except IndexError:
                    # Callback zaten çıkarılmış olabilir
                    pass

    def _get_state_name(self, state: int) -> str:
        """
        State değerinden state adını döndür

        Args:
            state: State değeri

        Returns:
            State adı
        """
        state_names = {
            0: "HARDFAULT_END",
            1: "IDLE",
            2: "CABLE_DETECT",
            3: "EV_CONNECTED",
            4: "READY",
            5: "CHARGING",
            6: "PAUSED",
            7: "STOPPED",
            8: "FAULT_HARD"
        }
        return state_names.get(state, f"UNKNOWN_{state}")

    def register_callback(self, callback: Callable):
        """
        Event callback kaydetme

        Args:
            callback: Event oluştuğunda çağrılacak fonksiyon
                     Signature: callback(event_type: EventType, event_data: Dict[str, Any])
        """
        self.event_callbacks.append(callback)

    def unregister_callback(self, callback: Callable):
        """Event callback kaldırma"""
        if callback in self.event_callbacks:
            self.event_callbacks.remove(callback)

    def get_current_state(self) -> Optional[int]:
        """Mevcut state değerini döndür"""
        with self.state_lock:
            return self.current_state

    def get_previous_state(self) -> Optional[int]:
        """Önceki state değerini döndür"""
        with self.state_lock:
            return self.previous_state


# Singleton instance
event_detector_instance: Optional[EventDetector] = None
event_detector_lock = threading.Lock()


def get_event_detector(bridge_getter: Callable) -> EventDetector:
    """
    Event Detector singleton instance'ı döndür

    Args:
        bridge_getter: ESP32Bridge instance'ı döndüren callable

    Returns:
        EventDetector instance
    """
    global event_detector_instance

    if event_detector_instance is None:
        with event_detector_lock:
            if event_detector_instance is None:
                event_detector_instance = EventDetector(bridge_getter)

    return event_detector_instance

