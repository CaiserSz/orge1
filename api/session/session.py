"""
Charging Session Class
Created: 2025-12-10 05:00:00
Last Modified: 2025-12-10 05:00:00
Version: 2.0.0
Description: Şarj session'ı temsil eden sınıf
"""

import threading
from typing import Optional, Dict, Any, List
from datetime import datetime
import sys
import os

# Logging modülünü import et
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from api.event_detector import EventType
from api.session.status import SessionStatus


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
            # user_id'yi metadata'dan çıkar (varsa)
            user_id = self.metadata.get("user_id")

            # Aktif session için süre hesapla (end_time yoksa şu anki zamanı kullan)
            from datetime import datetime
            if self.end_time:
                duration_seconds = (self.end_time - self.start_time).total_seconds()
            else:
                # Aktif session için şu anki zaman ile başlangıç zamanı arasındaki fark
                duration_seconds = (datetime.now() - self.start_time).total_seconds()

            result = {
                "session_id": self.session_id,
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "start_state": self.start_state,
                "end_state": self.end_state,
                "status": self.status.value,
                "duration_seconds": duration_seconds,
                "event_count": len(self.events),
                "events": self.events,
                "metadata": self.metadata,
            }

            # user_id varsa ayrı bir field olarak ekle
            if user_id:
                result["user_id"] = user_id

            return result
