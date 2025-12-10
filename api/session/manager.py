"""
Session Manager Class
Created: 2025-12-10 05:00:00
Last Modified: 2025-12-10 05:00:00
Version: 2.0.0
Description: Session yönetim modülü - Event Detector entegrasyonu ve database yönetimi
"""

import os
import sys
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

# Logging modülünü import et
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from api.database import get_database
from api.logging_config import system_logger
from api.session.events import SessionEventMixin
from api.session.metrics import SessionMetricsCalculator
from api.session.session import ChargingSession
from api.session.status import SessionStatus


class SessionManager(SessionEventMixin):
    """
    Session yönetim modülü

    Event Detector'dan gelen event'leri dinler ve session'ları yönetir.
    Thread-safe çalışır.
    """

    def __init__(self):
        """Session Manager başlatıcı"""
        self.db = get_database()
        self.current_session: Optional[ChargingSession] = None
        self.sessions_lock = threading.Lock()
        self.max_sessions = 1000  # Maksimum saklanacak session sayısı
        # charge_start event'inden gelen user_id'yi geçici olarak sakla
        self.pending_user_id: Optional[str] = None
        self.pending_user_id_lock = threading.Lock()

        # Meter entegrasyonu için hazırlık
        try:
            from api.meter import get_meter

            self.meter = get_meter()
            # Meter bağlantısını dene (başarısız olursa sorun değil)
            try:
                self.meter.connect()
            except Exception:
                pass  # Meter yok, sorun değil
        except ImportError:
            self.meter = None

        # Startup'ta aktif session'ı restore et
        self._restore_active_session()

    def _cleanup_old_sessions(self):
        """Eski session'ları temizle (maksimum session sayısını aşmamak için)"""
        self.db.cleanup_old_sessions(self.max_sessions)

    def _restore_active_session(self):
        """Startup'ta aktif session'ı database'den restore et"""
        try:
            db_session = self.db.get_current_session()
            if db_session:
                # Database'den aktif session'ı yükle
                start_time = datetime.fromisoformat(db_session["start_time"])
                session = ChargingSession(
                    db_session["session_id"],
                    start_time,
                    db_session["start_state"],
                )
                session.events = db_session["events"]
                session.metadata = db_session["metadata"]
                session.status = SessionStatus(db_session["status"])

                self.current_session = session
                system_logger.info(
                    f"Aktif session restore edildi: {session.session_id}",
                    extra={"session_id": session.session_id},
                )
        except Exception as e:
            system_logger.error(f"Active session restore error: {e}", exc_info=True)

    def get_current_session(self) -> Optional[Dict[str, Any]]:
        """
        Aktif session'ı döndür

        Returns:
            Aktif session dict'i veya None
        """
        with self.sessions_lock:
            if self.current_session:
                return self.current_session.to_dict()
            # Database'den kontrol et
            db_session = self.db.get_current_session()
            if db_session:
                return db_session
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
            # Önce memory'de kontrol et (aktif session)
            if self.current_session and self.current_session.session_id == session_id:
                return self.current_session.to_dict()
            # Database'den al
            return self.db.get_session(session_id)

    def get_sessions(
        self,
        limit: int = 100,
        offset: int = 0,
        status: Optional[SessionStatus] = None,
        user_id: Optional[str] = None,
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
        # Database'den al
        status_str = status.value if status else None
        return self.db.get_sessions(
            limit=limit, offset=offset, status=status_str, user_id=user_id
        )

    def get_session_count(
        self, status: Optional[SessionStatus] = None, user_id: Optional[str] = None
    ) -> int:
        """
        Session sayısını döndür

        Args:
            status: Filtreleme için status (opsiyonel)
            user_id: Filtreleme için user_id (opsiyonel)

        Returns:
            Session sayısı
        """
        # Database'den al
        status_str = status.value if status else None
        return self.db.get_session_count(status=status_str, user_id=user_id)

    def _update_session_metrics(self, event_data: Dict[str, Any]):
        """
        Session metriklerini real-time güncelle

        Args:
            event_data: Event data dict'i
        """
        if not self.current_session:
            return

        status = event_data.get("status", {})
        current_a = status.get("CABLE") or status.get("CURRENT")
        voltage_v = status.get("CPV") or status.get("PPV")

        # Metrikleri metadata'da sakla (geçici, final hesaplamada kullanılacak)
        if current_a is not None:
            currents = self.current_session.metadata.get("_metrics_currents", [])
            currents.append(float(current_a))
            self.current_session.metadata["_metrics_currents"] = currents

        if voltage_v is not None:
            voltages = self.current_session.metadata.get("_metrics_voltages", [])
            voltages.append(float(voltage_v))
            self.current_session.metadata["_metrics_voltages"] = voltages

        # Set current (MAX)
        max_current = status.get("MAX")
        if (
            max_current is not None
            and "set_current_a" not in self.current_session.metadata
        ):
            self.current_session.metadata["set_current_a"] = float(max_current)

    def _calculate_final_metrics(
        self, session: ChargingSession, end_time: datetime
    ) -> Dict[str, Any]:
        """
        Session sonunda final metrikleri hesapla

        Args:
            session: Session objesi
            end_time: Bitiş zamanı

        Returns:
            Metrikler dict'i
        """
        calculator = SessionMetricsCalculator()

        # Tüm event'leri ekle
        for event in session.events:
            calculator.add_event(event)

        # Metrikleri hesapla
        metrics = calculator.calculate_metrics(session.start_time, end_time)

        # Event count
        metrics["event_count"] = len(session.events)

        return metrics

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
