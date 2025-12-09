"""
Session Management Module
Created: 2025-12-10 03:00:00
Last Modified: 2025-12-10 03:00:00
Version: 1.0.0
Description: Şarj session'larını yöneten modül - session oluşturma, event tracking, session storage
"""

import threading
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import sys
import os

# Logging modülünü import et
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from api.logging_config import system_logger, log_event
from api.event_detector import EventType, ESP32State


class SessionStatus(Enum):
    """Session durumları"""

    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAULTED = "FAULTED"


class ChargingSession:
    """
    Şarj session'ı temsil eden sınıf

    Her session bir UUID ile tanımlanır ve başlangıç/bitiş zamanları,
    event'ler ve diğer metadata'yı içerir.
    """

    def __init__(self, session_id: str, start_time: datetime, start_state: int):
        """
        Session oluşturucu

        Args:
            session_id: Session UUID
            start_time: Session başlangıç zamanı
            start_state: Session başlangıç state'i
        """
        self.session_id = session_id
        self.start_time = start_time
        self.end_time: Optional[datetime] = None
        self.start_state = start_state
        self.end_state: Optional[int] = None
        self.status = SessionStatus.ACTIVE
        self.events: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}
        self.lock = threading.Lock()

    def add_event(self, event_type: EventType, event_data: Dict[str, Any]):
        """
        Session'a event ekle

        Args:
            event_type: Event type
            event_data: Event data dict'i
        """
        with self.lock:
            event_record = {
                "event_type": event_type.value,
                "timestamp": datetime.now().isoformat(),
                "data": event_data,
            }
            self.events.append(event_record)

    def end_session(self, end_time: datetime, end_state: int, status: SessionStatus):
        """
        Session'ı sonlandır

        Args:
            end_time: Session bitiş zamanı
            end_state: Session bitiş state'i
            status: Session durumu
        """
        with self.lock:
            self.end_time = end_time
            self.end_state = end_state
            self.status = status

    def to_dict(self) -> Dict[str, Any]:
        """
        Session'ı dict formatına dönüştür

        Returns:
            Session dict'i
        """
        with self.lock:
            return {
                "session_id": self.session_id,
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "start_state": self.start_state,
                "end_state": self.end_state,
                "status": self.status.value,
                "duration_seconds": (
                    (self.end_time - self.start_time).total_seconds()
                    if self.end_time
                    else None
                ),
                "event_count": len(self.events),
                "events": self.events,
                "metadata": self.metadata,
            }


class SessionManager:
    """
    Session yönetim modülü

    Event Detector'dan gelen event'leri dinler ve session'ları yönetir.
    Thread-safe çalışır.
    """

    def __init__(self):
        """Session Manager başlatıcı"""
        self.sessions: Dict[str, ChargingSession] = {}
        self.current_session: Optional[ChargingSession] = None
        self.sessions_lock = threading.Lock()
        self.max_sessions = 1000  # Maksimum saklanacak session sayısı

    def _on_event(self, event_type: EventType, event_data: Dict[str, Any]):
        """
        Event Detector'dan gelen event'leri işle

        Args:
            event_type: Event type
            event_data: Event data dict'i
        """
        try:
            # Session başlatma event'leri
            if event_type == EventType.CHARGE_STARTED:
                self._start_session(event_data)

            # Session sonlandırma event'leri
            elif event_type in [EventType.CHARGE_STOPPED, EventType.CABLE_DISCONNECTED]:
                self._end_session(event_type, event_data)

            # Aktif session'a event ekle
            elif self.current_session:
                self.current_session.add_event(event_type, event_data)

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

            self.current_session = session
            self.sessions[session_id] = session

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

    def _cleanup_old_sessions(self):
        """Eski session'ları temizle (maksimum session sayısını aşmamak için)"""
        if len(self.sessions) > self.max_sessions:
            # En eski session'ları bul ve sil
            sessions_by_time = sorted(
                self.sessions.items(), key=lambda x: x[1].start_time
            )

            # İlk %10'unu sil (en eski session'lar)
            to_remove = int(len(self.sessions) * 0.1)
            for session_id, _ in sessions_by_time[:to_remove]:
                del self.sessions[session_id]

            system_logger.info(
                f"Eski session'lar temizlendi: {to_remove} session silindi"
            )

    def get_current_session(self) -> Optional[Dict[str, Any]]:
        """
        Aktif session'ı döndür

        Returns:
            Aktif session dict'i veya None
        """
        with self.sessions_lock:
            if self.current_session:
                return self.current_session.to_dict()
            return None

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Belirli bir session'ı döndür

        Args:
            session_id: Session UUID

        Returns:
            Session dict'i veya None
        """
        with self.sessions_lock:
            session = self.sessions.get(session_id)
            if session:
                return session.to_dict()
            return None

    def get_sessions(
        self, limit: int = 100, offset: int = 0, status: Optional[SessionStatus] = None
    ) -> List[Dict[str, Any]]:
        """
        Session listesini döndür

        Args:
            limit: Maksimum döndürülecek session sayısı
            offset: Başlangıç offset'i
            status: Filtreleme için status (opsiyonel)

        Returns:
            Session listesi
        """
        with self.sessions_lock:
            sessions = list(self.sessions.values())

            # Status filtresi
            if status:
                sessions = [s for s in sessions if s.status == status]

            # Zaman sırasına göre sırala (en yeni önce)
            sessions.sort(key=lambda x: x.start_time, reverse=True)

            # Pagination
            return [s.to_dict() for s in sessions[offset : offset + limit]]

    def get_session_count(self, status: Optional[SessionStatus] = None) -> int:
        """
        Session sayısını döndür

        Args:
            status: Filtreleme için status (opsiyonel)

        Returns:
            Session sayısı
        """
        with self.sessions_lock:
            if status:
                return sum(1 for s in self.sessions.values() if s.status == status)
            return len(self.sessions)

    def register_with_event_detector(self, event_detector):
        """
        Event Detector'a callback olarak kaydol

        Args:
            event_detector: EventDetector instance'ı
        """
        event_detector.register_callback(self._on_event)
        system_logger.info("Session manager event detector'a kaydedildi")


# Singleton instance
session_manager_instance: Optional[SessionManager] = None
session_manager_lock = threading.Lock()


def get_session_manager() -> SessionManager:
    """
    Session Manager singleton instance'ı döndür

    Returns:
        SessionManager instance
    """
    global session_manager_instance

    if session_manager_instance is None:
        with session_manager_lock:
            if session_manager_instance is None:
                session_manager_instance = SessionManager()

    return session_manager_instance
