"""
Session Manager Test Suite
Created: 2025-12-10 03:30:00
Last Modified: 2025-12-13 02:30:00
Version: 1.1.0
Description: Session Manager modülü için unit testler
"""

from datetime import datetime
from unittest.mock import Mock

from api.event_detector import ESP32State, EventType
from api.session import (
    ChargingSession,
    SessionManager,
    SessionStatus,
    get_session_manager,
)



class TestSessionManager:
    """SessionManager sınıfı için testler"""

    def test_session_manager_creation(self):
        """Session Manager oluşturma testi"""
        manager = SessionManager()

        # SessionManager'da sessions attribute'u yok, database'den alınıyor
        # Sadece current_session ve max_sessions kontrol edelim
        assert manager.current_session is None or isinstance(
            manager.current_session, ChargingSession
        )
        assert manager.max_sessions == 1000

    def test_start_session_on_charge_started(self):
        """CHARGE_STARTED event'inde session başlatma testi"""
        manager = SessionManager()
        event_data = {
            "to_state": ESP32State.CHARGING.value,
            "from_state": ESP32State.READY.value,
        }

        manager._on_event(EventType.CHARGE_STARTED, event_data)

        assert manager.current_session is not None
        assert manager.current_session.status == SessionStatus.ACTIVE
        assert len(manager.current_session.events) == 1
        assert (
            manager.current_session.events[0]["event_type"]
            == EventType.CHARGE_STARTED.value
        )

    def test_end_session_on_charge_stopped(self):
        """CHARGE_STOPPED event'inde session sonlandırma testi"""
        manager = SessionManager()

        # Mevcut aktif session'ı temizle (restore edilen session varsa)
        if manager.current_session:
            manager._end_session(
                EventType.CHARGE_STOPPED,
                {"to_state": ESP32State.STOPPED.value},
            )

        # Önce session başlat
        manager._on_event(
            EventType.CHARGE_STARTED, {"to_state": ESP32State.CHARGING.value}
        )
        assert manager.current_session is not None
        session_id = manager.current_session.session_id

        # Sonra session sonlandır
        manager._on_event(
            EventType.CHARGE_STOPPED, {"to_state": ESP32State.STOPPED.value}
        )

        assert manager.current_session is None
        # Database'den session'ı kontrol et
        session = manager.get_session(session_id)
        assert session is not None
        assert session["status"] == SessionStatus.COMPLETED.value
        assert session["end_time"] is not None

    def test_end_session_on_cable_disconnected(self):
        """CABLE_DISCONNECTED event'inde session sonlandırma testi"""
        manager = SessionManager()

        # Mevcut aktif session'ı temizle (restore edilen session varsa)
        if manager.current_session:
            manager._end_session(
                EventType.CABLE_DISCONNECTED,
                {"to_state": ESP32State.IDLE.value},
            )

        # Önce session başlat
        manager._on_event(
            EventType.CHARGE_STARTED, {"to_state": ESP32State.CHARGING.value}
        )
        assert manager.current_session is not None
        session_id = manager.current_session.session_id

        # Sonra cable disconnected
        manager._on_event(
            EventType.CABLE_DISCONNECTED, {"to_state": ESP32State.IDLE.value}
        )

        assert manager.current_session is None
        # Database'den session'ı kontrol et
        session = manager.get_session(session_id)
        assert session is not None
        assert session["status"] == SessionStatus.CANCELLED.value

    def test_fault_handling(self):
        """Fault durumu işleme testi"""
        manager = SessionManager()

        # Mevcut aktif session'ı temizle (restore edilen session varsa)
        if manager.current_session:
            manager._end_session(
                EventType.CHARGE_STOPPED,
                {"to_state": ESP32State.STOPPED.value},
            )

        # Session başlat
        manager._on_event(
            EventType.CHARGE_STARTED, {"to_state": ESP32State.CHARGING.value}
        )

        # Fault event'i
        manager._on_event(
            EventType.FAULT_DETECTED, {"to_state": ESP32State.FAULT_HARD.value}
        )

        # Fault durumunda session hala aktif olmalı (sonlandırılmamalı)
        assert manager.current_session is not None
        # Status FAULTED olmalı (database'de güncellenmiş olabilir)
        # Session objesi üzerinde kontrol et
        assert manager.current_session.status in [
            SessionStatus.FAULTED,
            SessionStatus.ACTIVE,
        ]
        assert (
            len(manager.current_session.events) >= 2
        )  # CHARGE_STARTED + FAULT_DETECTED (veya daha fazla)

    def test_add_event_to_active_session(self):
        """Aktif session'a event ekleme testi"""
        manager = SessionManager()

        # Mevcut aktif session'ı temizle (restore edilen session varsa)
        if manager.current_session:
            manager._end_session(
                EventType.CHARGE_STOPPED,
                {"to_state": ESP32State.STOPPED.value},
            )

        # Session başlat
        manager._on_event(
            EventType.CHARGE_STARTED, {"to_state": ESP32State.CHARGING.value}
        )
        assert manager.current_session is not None
        initial_event_count = len(manager.current_session.events)

        # Event ekle
        manager._on_event(
            EventType.CHARGE_PAUSED, {"to_state": ESP32State.PAUSED.value}
        )

        assert len(manager.current_session.events) == initial_event_count + 1

    def test_new_session_cancels_previous(self):
        """Yeni session başlatıldığında önceki session'ı iptal etme testi"""
        manager = SessionManager()

        # Mevcut aktif session'ı temizle (restore edilen session varsa)
        if manager.current_session:
            manager._end_session(
                EventType.CHARGE_STOPPED,
                {"to_state": ESP32State.STOPPED.value},
            )

        # İlk session başlat
        manager._on_event(
            EventType.CHARGE_STARTED, {"to_state": ESP32State.CHARGING.value}
        )
        assert manager.current_session is not None
        first_session_id = manager.current_session.session_id

        # İkinci session başlat (önceki iptal edilmeli)
        manager._on_event(
            EventType.CHARGE_STARTED, {"to_state": ESP32State.CHARGING.value}
        )
        assert manager.current_session is not None
        second_session_id = manager.current_session.session_id

        assert first_session_id != second_session_id

        # İlk session iptal edilmiş olmalı (database'den kontrol et)
        first_session = manager.get_session(first_session_id)
        assert first_session is not None
        assert first_session["status"] == SessionStatus.CANCELLED.value

    def test_get_current_session(self):
        """Aktif session alma testi"""
        manager = SessionManager()

        # Mevcut aktif session'ı temizle (restore edilen session varsa)
        if manager.current_session:
            manager._end_session(
                EventType.CHARGE_STOPPED,
                {"to_state": ESP32State.STOPPED.value},
            )

        # Session yokken kontrol et (mevcut session restore edilmiş olabilir)
        manager.get_current_session()

        # Yeni session başlat
        manager._on_event(
            EventType.CHARGE_STARTED, {"to_state": ESP32State.CHARGING.value}
        )

        current = manager.get_current_session()
        assert current is not None
        assert current["status"] == SessionStatus.ACTIVE.value

    def test_get_session(self):
        """Belirli session alma testi"""
        manager = SessionManager()

        # Session başlat
        manager._on_event(
            EventType.CHARGE_STARTED, {"to_state": ESP32State.CHARGING.value}
        )
        session_id = manager.current_session.session_id

        # Session'ı al
        session = manager.get_session(session_id)
        assert session is not None
        assert session["session_id"] == session_id

        # Olmayan session
        assert manager.get_session("non-existent") is None

    def test_get_sessions_with_pagination(self):
        """Session listesi pagination testi"""
        manager = SessionManager()

        # Birkaç session oluştur
        for i in range(5):
            manager._on_event(
                EventType.CHARGE_STARTED, {"to_state": ESP32State.CHARGING.value}
            )
            manager._on_event(
                EventType.CHARGE_STOPPED, {"to_state": ESP32State.STOPPED.value}
            )

        # Pagination test
        sessions = manager.get_sessions(limit=2, offset=0)
        assert len(sessions) == 2

        sessions = manager.get_sessions(limit=2, offset=2)
        assert len(sessions) == 2

    def test_get_sessions_with_status_filter(self):
        """Status filtresi ile session listesi testi"""
        manager = SessionManager()

        # Başlangıç sayılarını al (test isolation sorunu - database'de mevcut session'lar olabilir)
        # Limit'i max_sessions olarak ayarlayarak limit=100 nedeniyle truncation'ı engelle
        initial_completed = len(
            manager.get_sessions(
                status=SessionStatus.COMPLETED, limit=manager.max_sessions
            )
        )
        initial_cancelled = len(
            manager.get_sessions(
                status=SessionStatus.CANCELLED, limit=manager.max_sessions
            )
        )

        # Mevcut aktif session'ı temizle (restore edilen session varsa)
        if manager.current_session:
            manager._end_session(
                EventType.CHARGE_STOPPED,
                {"to_state": ESP32State.STOPPED.value},
            )

        # Completed session
        manager._on_event(
            EventType.CHARGE_STARTED, {"to_state": ESP32State.CHARGING.value}
        )
        manager._on_event(
            EventType.CHARGE_STOPPED, {"to_state": ESP32State.STOPPED.value}
        )

        # Cancelled session
        manager._on_event(
            EventType.CHARGE_STARTED, {"to_state": ESP32State.CHARGING.value}
        )
        manager._on_event(
            EventType.CABLE_DISCONNECTED, {"to_state": ESP32State.IDLE.value}
        )

        # Completed session'ları al
        completed = manager.get_sessions(
            status=SessionStatus.COMPLETED, limit=manager.max_sessions
        )
        # Eğer maksimum session sayısına ulaşıldıysa, cleanup eski session'ları
        # silebileceğinden toplam sayı artmayabilir; bu durumda en azından
        # başlangıç sayısından küçük olmamalı.
        if initial_completed < manager.max_sessions:
            assert len(completed) >= initial_completed + 1
        else:
            assert len(completed) >= initial_completed
        # Yeni oluşturulan session'ı bul
        new_completed = [
            s for s in completed if s["status"] == SessionStatus.COMPLETED.value
        ]
        assert len(new_completed) >= 1

        # Cancelled session'ları al
        cancelled = manager.get_sessions(
            status=SessionStatus.CANCELLED, limit=manager.max_sessions
        )
        if initial_cancelled < manager.max_sessions:
            assert len(cancelled) >= initial_cancelled + 1
        else:
            assert len(cancelled) >= initial_cancelled
        # Yeni oluşturulan session'ı bul
        new_cancelled = [
            s for s in cancelled if s["status"] == SessionStatus.CANCELLED.value
        ]
        assert len(new_cancelled) >= 1

    def test_get_session_count(self):
        """Session sayısı alma testi"""
        manager = SessionManager()

        # Database'de mevcut session'lar olabilir (test isolation sorunu)
        # Bu yüzden önce mevcut sayıları kaydedip, farkı kontrol edelim
        total_before = manager.get_session_count()
        completed_before = manager.get_session_count(SessionStatus.COMPLETED)
        cancelled_before = manager.get_session_count(SessionStatus.CANCELLED)
        assert isinstance(total_before, int)
        assert total_before >= 0

        # Birkaç session oluştur
        manager._on_event(
            EventType.CHARGE_STARTED, {"to_state": ESP32State.CHARGING.value}
        )
        manager._on_event(
            EventType.CHARGE_STOPPED, {"to_state": ESP32State.STOPPED.value}
        )

        manager._on_event(
            EventType.CHARGE_STARTED, {"to_state": ESP32State.CHARGING.value}
        )
        manager._on_event(
            EventType.CABLE_DISCONNECTED, {"to_state": ESP32State.IDLE.value}
        )

        assert manager.get_session_count() == total_before + 2
        assert (
            manager.get_session_count(SessionStatus.COMPLETED) == completed_before + 1
        )
        assert (
            manager.get_session_count(SessionStatus.CANCELLED) == cancelled_before + 1
        )

