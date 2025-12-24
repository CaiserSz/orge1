"""
API Authentication Tests
Created: 2025-12-09 17:20:00
Last Modified: 2025-12-22 17:55:00
Version: 1.0.4
Description: API authentication testleri
"""

import base64
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

# Proje root'unu path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.auth import get_secret_api_key, verify_api_key
from api.main import app
from api.routers import dependencies


class TestAuthentication:
    """API Authentication testleri"""

    def test_get_secret_api_key_success(self):
        """SECRET_API_KEY başarıyla okunuyor mu?"""
        # Config modülünü reload et
        from api import config as config_module

        original_key = config_module.config.SECRET_API_KEY
        os.environ["SECRET_API_KEY"] = "test-secret-key-123"
        config_module.config.load()  # Config'i yeniden yükle
        key = get_secret_api_key()
        assert key == "test-secret-key-123"
        # Orijinal değeri geri yükle
        if original_key:
            os.environ["SECRET_API_KEY"] = original_key
        else:
            if "SECRET_API_KEY" in os.environ:
                del os.environ["SECRET_API_KEY"]
        config_module.config.load()

    def test_get_secret_api_key_missing(self):
        """SECRET_API_KEY eksikse hata veriyor mu?"""
        from api import config as config_module

        original_key = config_module.config.SECRET_API_KEY
        if "SECRET_API_KEY" in os.environ:
            del os.environ["SECRET_API_KEY"]
        config_module.config.load()  # Config'i yeniden yükle

        with pytest.raises(ValueError, match="SECRET_API_KEY"):
            get_secret_api_key()

        # Orijinal değeri geri yükle
        if original_key:
            os.environ["SECRET_API_KEY"] = original_key
        config_module.config.load()

    def test_verify_api_key_success(self):
        """Doğru API key kabul ediliyor mu?"""
        from api import config as config_module

        original_key = config_module.config.SECRET_API_KEY
        os.environ["SECRET_API_KEY"] = "test-secret-key-123"
        config_module.config.load()  # Config'i yeniden yükle
        result = verify_api_key("test-secret-key-123")
        assert result == "test-secret-key-123"
        # Orijinal değeri geri yükle
        if original_key:
            os.environ["SECRET_API_KEY"] = original_key
        else:
            if "SECRET_API_KEY" in os.environ:
                del os.environ["SECRET_API_KEY"]
        config_module.config.load()

    def test_verify_api_key_invalid(self):
        """Yanlış API key reddediliyor mu?"""
        from api import config as config_module

        os.environ["SECRET_API_KEY"] = "test-secret-key-123"
        config_module.config.load()  # Config'i yeniden yükle

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            verify_api_key("wrong-key")

        assert exc_info.value.status_code == 401
        assert "Invalid API key" in str(exc_info.value.detail)

    def test_verify_api_key_missing(self):
        """API key eksikse hata veriyor mu?"""
        from api import config as config_module

        os.environ["SECRET_API_KEY"] = "test-secret-key-123"
        config_module.config.load()  # Config'i yeniden yükle

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            verify_api_key(None)

        assert exc_info.value.status_code == 401
        assert "API key required" in str(exc_info.value.detail)


class TestAPIAuthentication:
    """API endpoint authentication testleri"""

    @pytest.fixture
    def client(self):
        """Test client fixture"""
        from api import config as config_module

        os.environ["SECRET_API_KEY"] = "test-api-key"
        config_module.config.load()  # Config'i yeniden yükle
        return TestClient(app, raise_server_exceptions=False)

    def test_charge_start_without_api_key(self, client):
        """API key olmadan şarj başlatma reddediliyor mu?"""
        response = client.post("/api/charge/start", json={})
        assert response.status_code == 401
        assert "API key required" in response.json()["detail"]

    def test_charge_start_with_invalid_api_key(self, client):
        """Yanlış API key ile şarj başlatma reddediliyor mu?"""
        response = client.post(
            "/api/charge/start", json={}, headers={"X-API-Key": "wrong-key"}
        )
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]

    def test_charge_start_with_valid_api_key(self, client):
        """Doğru API key ile şarj başlatma çalışıyor mu?"""
        # Mock ESP32 bridge
        mock_bridge = Mock()
        mock_bridge.is_connected = True
        # Charge start yalnızca EV_CONNECTED (3) durumunda kabul edilir
        mock_bridge.get_status.return_value = {"STATE": 3}
        mock_bridge.send_authorization.return_value = True

        app.dependency_overrides[dependencies.get_bridge] = lambda: mock_bridge
        try:
            response = client.post(
                "/api/charge/start", json={}, headers={"X-API-Key": "test-api-key"}
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(dependencies.get_bridge, None)

    def test_charge_stop_without_api_key(self, client):
        """API key olmadan şarj durdurma reddediliyor mu?"""
        response = client.post("/api/charge/stop", json={})
        assert response.status_code == 401

    def test_maxcurrent_without_api_key(self, client):
        """API key olmadan akım ayarlama reddediliyor mu?"""
        response = client.post("/api/maxcurrent", json={"amperage": 16})
        assert response.status_code == 401

    def test_status_without_api_key(self, client):
        """Status endpoint API key gerektirmiyor mu?"""
        # Status endpoint authentication gerektirmemeli
        mock_bridge = Mock()
        mock_bridge.is_connected = True
        mock_bridge.get_status.return_value = {"STATE": 1}

        with patch(
            "api.routers.dependencies.get_esp32_bridge", return_value=mock_bridge
        ):
            response = client.get("/api/status")
            # Status endpoint authentication gerektirmiyor, 200 veya 503 olabilir
            assert response.status_code in [200, 503]


class TestAdminUI:
    """Admin UI (HTTP Basic) smoke tests."""

    @pytest.fixture
    def client(self, tmp_path):
        """
        Test client with isolated DB.

        Not:
          - Admin UI endpoint'leri DB kullanır (admin_users + ocpp_station_profiles).
          - Production DB etkilenmesin diye singleton DB instance'ını tmp dosyaya yönlendiririz.
        """
        from api.database import core as db_core

        # Reset singleton (defensive)
        db_core.database_instance = None
        db_core.database_instance = db_core.Database(str(tmp_path / "test_sessions.db"))

        return TestClient(app, raise_server_exceptions=False)

    def _basic(self, username: str, password: str) -> str:
        token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode(
            "ascii"
        )
        return f"Basic {token}"

    def test_admin_requires_basic_auth(self, client):
        resp = client.get("/admin")
        assert resp.status_code == 401
        assert resp.headers.get("www-authenticate") == "Basic"

    def test_admin_accepts_default_credentials(self, client):
        resp = client.get(
            "/admin",
            headers={"Authorization": self._basic("admin", "admin123")},
        )
        assert resp.status_code == 200
        assert "Charger Admin" in resp.text

    def test_admin_profiles_list_json(self, client):
        resp = client.get(
            "/admin/api/profiles",
            headers={"Authorization": self._basic("admin", "admin123")},
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_admin_profile_validation_returns_400(self, client):
        resp = client.post(
            "/admin/api/profiles",
            headers={"Authorization": self._basic("admin", "admin123")},
            json={
                "profile_key": "ORGE_AC_001_201_TEST",
                "station_name": "ORGE_AC_001_201_TEST",
                "ocpp_version": "2.0.1",
                # ocpp201_url intentionally missing to trigger validation error
                "ocpp16_url": "wss://lixhium.xyz/ocpp16/ORGE_AC_001_201_TEST",
                "vendor_name": "ORGE",
                "model": "ORGE",
                "password_env_var": "OCPP_STATION_PASSWORD",
                "heartbeat_seconds": 60,
                "enabled": True,
            },
        )
        assert resp.status_code == 400
        assert "ocpp201_url" in resp.json().get("detail", "")
