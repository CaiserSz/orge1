"""
API Authentication Tests
Created: 2025-12-09 17:20:00
Last Modified: 2025-12-09 17:20:00
Version: 1.0.0
Description: API authentication testleri
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

# Proje root'unu path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.main import app
from api.auth import verify_api_key, get_secret_api_key


class TestAuthentication:
    """API Authentication testleri"""
    
    def test_get_secret_api_key_success(self):
        """SECRET_API_KEY başarıyla okunuyor mu?"""
        os.environ['SECRET_API_KEY'] = 'test-secret-key-123'
        key = get_secret_api_key()
        assert key == 'test-secret-key-123'
    
    def test_get_secret_api_key_missing(self):
        """SECRET_API_KEY eksikse hata veriyor mu?"""
        if 'SECRET_API_KEY' in os.environ:
            del os.environ['SECRET_API_KEY']
        
        with pytest.raises(ValueError, match="SECRET_API_KEY"):
            get_secret_api_key()
    
    def test_verify_api_key_success(self):
        """Doğru API key kabul ediliyor mu?"""
        os.environ['SECRET_API_KEY'] = 'test-secret-key-123'
        result = verify_api_key('test-secret-key-123')
        assert result == 'test-secret-key-123'
    
    def test_verify_api_key_invalid(self):
        """Yanlış API key reddediliyor mu?"""
        os.environ['SECRET_API_KEY'] = 'test-secret-key-123'
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            verify_api_key('wrong-key')
        
        assert exc_info.value.status_code == 401
        assert 'Invalid API key' in str(exc_info.value.detail)
    
    def test_verify_api_key_missing(self):
        """API key eksikse hata veriyor mu?"""
        os.environ['SECRET_API_KEY'] = 'test-secret-key-123'
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            verify_api_key(None)
        
        assert exc_info.value.status_code == 401
        assert 'API key required' in str(exc_info.value.detail)


class TestAPIAuthentication:
    """API endpoint authentication testleri"""
    
    @pytest.fixture
    def client(self):
        """Test client fixture"""
        os.environ['SECRET_API_KEY'] = 'test-api-key'
        return TestClient(app)
    
    def test_charge_start_without_api_key(self, client):
        """API key olmadan şarj başlatma reddediliyor mu?"""
        response = client.post(
            "/api/charge/start",
            json={}
        )
        assert response.status_code == 401
        assert 'API key required' in response.json()['detail']
    
    def test_charge_start_with_invalid_api_key(self, client):
        """Yanlış API key ile şarj başlatma reddediliyor mu?"""
        response = client.post(
            "/api/charge/start",
            json={},
            headers={"X-API-Key": "wrong-key"}
        )
        assert response.status_code == 401
        assert 'Invalid API key' in response.json()['detail']
    
    def test_charge_start_with_valid_api_key(self, client):
        """Doğru API key ile şarj başlatma çalışıyor mu?"""
        # Mock ESP32 bridge
        from unittest.mock import Mock, patch
        mock_bridge = Mock()
        mock_bridge.is_connected = True
        mock_bridge.get_status.return_value = {'STATE': 1}
        mock_bridge.send_authorization.return_value = True
        
        with patch('api.main.get_esp32_bridge', return_value=mock_bridge):
            response = client.post(
                "/api/charge/start",
                json={},
                headers={"X-API-Key": "test-api-key"}
            )
            assert response.status_code == 200
    
    def test_charge_stop_without_api_key(self, client):
        """API key olmadan şarj durdurma reddediliyor mu?"""
        response = client.post(
            "/api/charge/stop",
            json={}
        )
        assert response.status_code == 401
    
    def test_maxcurrent_without_api_key(self, client):
        """API key olmadan akım ayarlama reddediliyor mu?"""
        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 16}
        )
        assert response.status_code == 401
    
    def test_status_without_api_key(self, client):
        """Status endpoint API key gerektirmiyor mu?"""
        # Status endpoint authentication gerektirmemeli
        from unittest.mock import Mock, patch
        mock_bridge = Mock()
        mock_bridge.is_connected = True
        mock_bridge.get_status.return_value = {'STATE': 1}
        
        with patch('api.main.get_esp32_bridge', return_value=mock_bridge):
            response = client.get("/api/status")
            # Status endpoint authentication gerektirmiyor, 200 veya 503 olabilir
            assert response.status_code in [200, 503]

