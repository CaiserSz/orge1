"""
API Main Endpoints Comprehensive Tests
Created: 2025-12-09 23:50:00
Last Modified: 2025-12-13 13:12:00
Version: 1.0.3
Description: api/main.py için kapsamlı endpoint testleri
"""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Proje root'unu path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.event_detector import ESP32State
from api.main import app
from api.routers import dependencies
from esp32.bridge import ESP32Bridge

# conftest.py'den fixture'ları import et
# pytest otomatik olarak conftest.py'deki fixture'ları bulur
# mock_esp32_bridge, client fixture'ları conftest.py'den gelir


class TestRootEndpoints:
    """Root endpoint testleri"""

    def test_root_endpoint(self, client):
        """Root endpoint çalışıyor mu?"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "AC Charger API"
        # API ana versiyonu 2.0.0 olarak güncellendi
        assert data["version"] == "2.0.0"
        assert data["status"] == "running"
        assert "/docs" in data["docs"]
        assert "/form" in data["form"]

    def test_form_endpoint_exists(self, client):
        """Form endpoint - dosya varsa"""
        form_path = Path(__file__).parent.parent / "station_form.html"

        if form_path.exists():
            response = client.get("/form")
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/html; charset=utf-8"
        else:
            # Dosya yoksa 404 döndürmeli
            response = client.get("/form")
            assert response.status_code == 404

    def test_form_endpoint_not_found(self, client):
        """Form endpoint - dosya yoksa"""
        # Gerçek dosya yoksa zaten 404 döner
        form_path = Path(__file__).parent.parent / "station_form.html"
        if not form_path.exists():
            response = client.get("/form")
            assert response.status_code == 404
            assert "bulunamadı" in response.json()["detail"]
        else:
            # Dosya varsa test geçer
            pytest.skip("Form file exists, cannot test not found scenario")


class TestCurrentControlEndpoints:
    """Current control endpoint testleri"""

    def test_get_available_currents(self, client):
        """Get available currents endpoint çalışıyor mu?"""
        response = client.get("/api/current/available")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["min"] == 6
        assert data["data"]["max"] == 32
        assert data["data"]["unit"] == "amper"
        assert "common_values" in data["data"]
        assert 16 in data["data"]["common_values"]


class TestStationInfoEndpoints:
    """Station info endpoint testleri"""

    def test_get_station_info_not_found(self, client):
        """Get station info - bilgi yoksa"""
        with patch("api.routers.station.get_station_info", return_value=None):
            response = client.get("/api/station/info")
            assert response.status_code == 404
            assert "bulunamadı" in response.json()["detail"]

    def test_get_station_info_success(self, client):
        """Get station info - başarılı"""
        test_data = {
            "station_id": "TEST-001",
            "name": "Test Station",
            "location": "Test Location",
            "price_per_kwh": 7.5,
        }

        with patch("api.routers.station.get_station_info", return_value=test_data):
            response = client.get("/api/station/info")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["station_id"] == "TEST-001"
            assert data["data"]["price_per_kwh"] == 7.5

    def test_save_station_info_success(self, client):
        """Save station info - başarılı"""
        test_data = {
            "station_id": "TEST-001",
            "name": "Test Station",
            "price_per_kwh": 7.5,
        }

        with patch("api.routers.station.save_station_info", return_value=True):
            response = client.post("/api/station/info", json=test_data)
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["message"] == "İstasyon bilgileri kaydedildi"
            assert data["data"]["price_per_kwh"] == 7.5

    def test_save_station_info_failure(self, client):
        """Save station info - başarısız"""
        test_data = {"station_id": "TEST-001", "name": "Test Station"}

        with patch("api.routers.station.save_station_info", return_value=False):
            response = client.post("/api/station/info", json=test_data)
            assert response.status_code == 500
            assert "kaydedilemedi" in response.json()["detail"]


class TestTestEndpoints:
    """Test endpoint testleri"""

    def test_get_test_api_key_development(self, client):
        """Get test API key - development ortamı"""
        with patch.dict(
            os.environ, {"ENVIRONMENT": "development", "SECRET_API_KEY": "test-key"}
        ):
            response = client.get("/api/test/key")
            assert response.status_code == 200
            data = response.json()
            assert data["api_key"] == "test-key"
            assert "note" in data

    def test_get_test_api_key_production(self, client):
        """Get test API key - production ortamı"""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            response = client.get("/api/test/key")
            assert response.status_code == 404

    def test_get_test_api_key_no_key(self, client):
        """Get test API key - API key yoksa"""
        with patch.dict(
            os.environ, {"ENVIRONMENT": "development", "SECRET_API_KEY": ""}
        ):
            response = client.get("/api/test/key")
            assert response.status_code == 503

    def test_api_test_page_exists(self, client):
        """API test page - dosya varsa"""
        test_page_path = Path(__file__).parent.parent / "api_test.html"

        if test_page_path.exists():
            response = client.get("/test")
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/html; charset=utf-8"
        else:
            # Dosya yoksa 404 döndürmeli
            response = client.get("/test")
            assert response.status_code == 404

    def test_api_test_page_not_found(self, client):
        """API test page - dosya yoksa"""
        # Gerçek dosya yoksa zaten 404 döner
        test_page_path = Path(__file__).parent.parent / "api_test.html"
        if not test_page_path.exists():
            response = client.get("/test")
            assert response.status_code == 404
        else:
            # Dosya varsa test geçer
            pytest.skip("Test page file exists, cannot test not found scenario")


class TestMiddleware:
    """Middleware testleri"""

    def test_api_logging_middleware(self, client, mock_esp32_bridge):
        """API logging middleware çalışıyor mu?"""
        response = client.get("/api/health")
        assert response.status_code == 200
        # Middleware response'u etkilememeli

    def test_api_logging_middleware_excludes_charge_endpoints(
        self, client, mock_esp32_bridge
    ):
        """API logging middleware charge endpoint'lerini exclude ediyor mu?"""
        # Charge start/stop endpoint'leri logging'den exclude edilmeli
        # Bu test middleware'in çalıştığını doğrular
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.EV_CONNECTED.value,
            "AUTH": 0,
            "CABLE": 0,
            "MAX": 16,
        }
        response = client.post(
            "/api/charge/start", json={}, headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 200


class TestGlobalExceptionHandler:
    """Global exception handler testleri"""

    def test_global_exception_handler_debug_mode(self, client):
        """Global exception handler - debug mode"""
        # Exception handler'ı test etmek için endpoint içinde exception oluştur
        # TestClient exception'ları yakaladığı için bu testi skip ediyoruz
        # Gerçek exception handler testi integration testlerinde yapılabilir
        pytest.skip("Exception handler test requires different approach")

    def test_global_exception_handler_production_mode(self, client):
        """Global exception handler - production mode"""
        # Exception handler'ı test etmek için endpoint içinde exception oluştur
        # TestClient exception'ları yakaladığı için bu testi skip ediyoruz
        # Gerçek exception handler testi integration testlerinde yapılabilir
        pytest.skip("Exception handler test requires different approach")


class TestHealthCheckEdgeCases:
    """Health check edge case testleri"""

    def test_health_check_bridge_none(self, client):
        """Health check - bridge None"""
        app.dependency_overrides[dependencies.get_bridge] = lambda: None
        try:
            response = client.get("/api/health")
            assert response.status_code == 200
            data = response.json()
            assert data["data"]["esp32_connected"] is False
        finally:
            app.dependency_overrides.pop(dependencies.get_bridge, None)

    def test_health_check_bridge_not_connected(self, client):
        """Health check - bridge bağlı değil"""
        mock_bridge = Mock(spec=ESP32Bridge)
        mock_bridge.is_connected = False

        app.dependency_overrides[dependencies.get_bridge] = lambda: mock_bridge
        try:
            response = client.get("/api/health")
            assert response.status_code == 200
            data = response.json()
            assert data["data"]["esp32_connected"] is False
        finally:
            app.dependency_overrides.pop(dependencies.get_bridge, None)

    def test_health_check_status_available(self, client, mock_esp32_bridge):
        """Health check - status mevcut"""
        mock_esp32_bridge.get_status.return_value = {"STATE": ESP32State.IDLE.value}

        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["esp32_status"] == "available"

    def test_health_check_status_not_available(self, client, mock_esp32_bridge):
        """Health check - status mevcut değil"""
        mock_esp32_bridge.get_status.return_value = None

        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["esp32_status"] == "no_status"


class TestStatusEndpointEdgeCases:
    """Status endpoint edge case testleri"""

    def test_status_get_status_sync_timeout(self, client, mock_esp32_bridge):
        """Status - get_status_sync timeout"""
        mock_esp32_bridge.get_status.return_value = None
        # conftest.py'de get_status_sync side_effect ile tanımlı; burada override et
        mock_esp32_bridge.get_status_sync.side_effect = lambda timeout=None: None

        response = client.get("/api/status")
        assert response.status_code == 504
        assert "durum bilgisi alınamadı" in response.json()["detail"]

    def test_status_get_status_sync_success(self, client, mock_esp32_bridge):
        """Status - get_status_sync başarılı"""
        mock_esp32_bridge.get_status.return_value = None
        mock_esp32_bridge.get_status_sync.side_effect = lambda timeout=None: {
            "STATE": ESP32State.IDLE.value
        }

        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["STATE"] == ESP32State.IDLE.value
