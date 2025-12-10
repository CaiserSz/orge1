"""
Session API Endpoint Testleri
Created: 2025-12-10 13:30:00
Last Modified: 2025-12-10 13:30:00
Version: 1.0.0
Description: Session API endpoint'leri için testler
"""

import sys
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.session import SessionStatus

# conftest.py'deki standart fixture'ları kullan
# mock_esp32_bridge, client, test_headers fixture'ları conftest.py'den gelir


class TestSessionAPIEndpoints:
    """Session API endpoint testleri"""

    def test_get_current_session(self, client, mock_esp32_bridge):
        """
        GET /api/sessions/current endpoint testi

        Senaryo:
        1. Aktif session varsa session döndürmeli
        2. Aktif session yoksa null döndürmeli
        """
        # Mock session manager
        mock_session_manager = patch("api.routers.sessions.get_session_manager")
        with mock_session_manager as mock_get_manager:
            # 1. Aktif session var
            mock_manager = mock_get_manager.return_value
            mock_manager.get_current_session.return_value = {
                "session_id": "test-session-123",
                "status": "ACTIVE",
                "start_time": "2025-12-10T10:00:00",
            }

            response = client.get("/api/sessions/current")
            assert response.status_code == 200
            assert response.json()["success"] is True
            assert response.json()["session"] is not None
            assert response.json()["session"]["session_id"] == "test-session-123"

            # 2. Aktif session yok
            mock_manager.get_current_session.return_value = None

            response = client.get("/api/sessions/current")
            assert response.status_code == 200
            assert response.json()["success"] is True
            assert response.json()["session"] is None
            assert "Aktif session yok" in response.json()["message"]

    def test_get_session_by_id(self, client, mock_esp32_bridge):
        """
        GET /api/sessions/{session_id} endpoint testi

        Senaryo:
        1. Session bulunursa session döndürmeli
        2. Session bulunamazsa 404 hatası döndürmeli
        """
        mock_session_manager = patch("api.routers.sessions.get_session_manager")
        with mock_session_manager as mock_get_manager:
            # 1. Session bulundu
            mock_manager = mock_get_manager.return_value
            mock_manager.get_session.return_value = {
                "session_id": "test-session-123",
                "status": "COMPLETED",
                "start_time": "2025-12-10T10:00:00",
                "end_time": "2025-12-10T11:00:00",
            }

            response = client.get("/api/sessions/test-session-123")
            assert response.status_code == 200
            assert response.json()["success"] is True
            assert response.json()["session"]["session_id"] == "test-session-123"

            # 2. Session bulunamadı
            mock_manager.get_session.return_value = None

            response = client.get("/api/sessions/non-existent-session")
            assert response.status_code == 404
            assert "Session bulunamadı" in response.json()["detail"]

    def test_get_session_metrics(self, client, mock_esp32_bridge):
        """
        GET /api/sessions/{session_id}/metrics endpoint testi

        Senaryo:
        1. Session bulunursa metrikleri döndürmeli
        2. Session bulunamazsa 404 hatası döndürmeli
        """
        mock_session_manager = patch("api.routers.sessions.get_session_manager")
        with mock_session_manager as mock_get_manager:
            # 1. Session bulundu ve metrikleri var
            mock_manager = mock_get_manager.return_value
            mock_manager.get_session.return_value = {
                "session_id": "test-session-123",
                "duration_seconds": 3600,
                "charging_duration_seconds": 3000,
                "idle_duration_seconds": 600,
                "total_energy_kwh": 10.5,
                "start_energy_kwh": 0.0,
                "end_energy_kwh": 10.5,
                "max_power_kw": 3.5,
                "avg_power_kw": 3.0,
                "min_power_kw": 2.5,
                "max_current_a": 16.0,
                "avg_current_a": 15.0,
                "min_current_a": 14.0,
                "set_current_a": 16.0,
                "max_voltage_v": 230.0,
                "avg_voltage_v": 225.0,
                "min_voltage_v": 220.0,
                "event_count": 5,
            }

            response = client.get("/api/sessions/test-session-123/metrics")
            assert response.status_code == 200
            assert response.json()["success"] is True
            assert response.json()["metrics"]["session_id"] == "test-session-123"
            assert response.json()["metrics"]["duration_seconds"] == 3600
            assert response.json()["metrics"]["total_energy_kwh"] == 10.5

            # 2. Session bulunamadı
            mock_manager.get_session.return_value = None

            response = client.get("/api/sessions/non-existent-session/metrics")
            assert response.status_code == 404
            assert "Session bulunamadı" in response.json()["detail"]

    def test_get_sessions_list(self, client, mock_esp32_bridge):
        """
        GET /api/sessions endpoint testi

        Senaryo:
        1. Session listesi döndürmeli
        2. Pagination parametreleri çalışmalı
        3. Status filtresi çalışmalı
        4. User ID filtresi çalışmalı
        """
        mock_session_manager = patch("api.routers.sessions.get_session_manager")
        with mock_session_manager as mock_get_manager:
            # 1. Tüm session'ları listele
            mock_manager = mock_get_manager.return_value
            mock_manager.get_sessions.return_value = [
                {
                    "session_id": "session-1",
                    "status": "COMPLETED",
                    "start_time": "2025-12-10T10:00:00",
                },
                {
                    "session_id": "session-2",
                    "status": "ACTIVE",
                    "start_time": "2025-12-10T11:00:00",
                },
            ]
            mock_manager.get_session_count.return_value = 2

            response = client.get("/api/sessions")
            assert response.status_code == 200
            assert response.json()["success"] is True
            assert len(response.json()["sessions"]) == 2
            assert response.json()["total_count"] == 2

            # 2. Pagination parametreleri
            mock_manager.get_sessions.return_value = [
                {
                    "session_id": "session-1",
                    "status": "COMPLETED",
                    "start_time": "2025-12-10T10:00:00",
                }
            ]
            mock_manager.get_session_count.return_value = 1

            response = client.get("/api/sessions?limit=1&offset=0")
            assert response.status_code == 200
            assert len(response.json()["sessions"]) == 1

            # 3. Status filtresi
            mock_manager.get_sessions.return_value = [
                {
                    "session_id": "session-1",
                    "status": "COMPLETED",
                    "start_time": "2025-12-10T10:00:00",
                }
            ]
            mock_manager.get_session_count.return_value = 1

            response = client.get("/api/sessions?status=COMPLETED")
            assert response.status_code == 200
            assert response.json()["success"] is True

            # 4. Geçersiz status filtresi
            response = client.get("/api/sessions?status=INVALID")
            assert response.status_code == 400
            assert "Geçersiz status filtresi" in response.json()["detail"]

    def test_get_user_sessions(self, client, mock_esp32_bridge):
        """
        GET /api/sessions/users/{user_id}/sessions endpoint testi

        Senaryo:
        1. Belirli bir kullanıcının session'larını döndürmeli
        2. Pagination parametreleri çalışmalı
        3. Status filtresi çalışmalı
        """
        mock_session_manager = patch("api.routers.sessions.get_session_manager")
        with mock_session_manager as mock_get_manager:
            # 1. User'ın session'larını listele
            mock_manager = mock_get_manager.return_value
            mock_manager.get_sessions.return_value = [
                {
                    "session_id": "session-1",
                    "user_id": "user-123",
                    "status": "COMPLETED",
                    "start_time": "2025-12-10T10:00:00",
                }
            ]
            mock_manager.get_session_count.return_value = 1

            response = client.get("/api/sessions/users/user-123/sessions")
            assert response.status_code == 200
            assert response.json()["success"] is True
            assert response.json()["user_id"] == "user-123"
            assert len(response.json()["sessions"]) == 1

            # 2. Pagination parametreleri
            response = client.get(
                "/api/sessions/users/user-123/sessions?limit=10&offset=0"
            )
            assert response.status_code == 200

            # 3. Status filtresi
            response = client.get(
                "/api/sessions/users/user-123/sessions?status=COMPLETED"
            )
            assert response.status_code == 200

    def test_get_session_stats(self, client, mock_esp32_bridge):
        """
        GET /api/sessions/count/stats endpoint testi

        Senaryo:
        1. Session istatistiklerini döndürmeli
        """
        mock_session_manager = patch("api.routers.sessions.get_session_manager")
        with mock_session_manager as mock_get_manager:
            mock_manager = mock_get_manager.return_value
            mock_manager.get_session_count.side_effect = (
                lambda status=None, user_id=None: {
                    None: 10,  # Total
                    SessionStatus.ACTIVE: 2,
                    SessionStatus.COMPLETED: 6,
                    SessionStatus.CANCELLED: 1,
                    SessionStatus.FAULTED: 1,
                }.get(status, 0)
            )

            response = client.get("/api/sessions/count/stats")
            assert response.status_code == 200
            assert response.json()["success"] is True
            assert response.json()["stats"]["total"] == 10
            assert response.json()["stats"]["active"] == 2
            assert response.json()["stats"]["completed"] == 6
            assert response.json()["stats"]["cancelled"] == 1
            assert response.json()["stats"]["faulted"] == 1
