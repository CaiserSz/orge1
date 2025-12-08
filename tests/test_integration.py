"""
Integration Testleri - Gerçek Senaryolar
Created: 2025-12-09 02:25:00
Last Modified: 2025-12-09 02:25:00
Version: 1.0.0
Description: Gerçek kullanım senaryoları ve integration testleri
"""

import pytest
import sys
from unittest.mock import Mock, patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def mock_bridge():
    """Mock ESP32 bridge"""
    mock = Mock()
    mock.is_connected = True
    mock.get_status = Mock(return_value={
        'STATE': 1,
        'AUTH': 0,
        'CABLE': 0,
        'MAX': 16,
        'CP': 0,
        'PP': 0
    })
    mock.send_authorization = Mock(return_value=True)
    mock.send_charge_stop = Mock(return_value=True)
    mock.send_current_set = Mock(return_value=True)
    return mock


@pytest.fixture
def client(mock_bridge):
    """Test client"""
    with patch('api.main.esp32_bridge', mock_bridge):
        with patch('api.main.get_esp32_bridge', return_value=mock_bridge):
            yield TestClient(app)


class TestRealWorldScenarios:
    """Gerçek dünya senaryoları"""
    
    def test_complete_charging_flow(self, client, mock_bridge):
        """Tam şarj akışı senaryosu"""
        # 1. Durum kontrolü
        response = client.get("/api/status")
        assert response.status_code == 200
        
        # 2. Akım ayarlama
        mock_bridge.get_status.return_value = {'STATE': 1}
        response = client.post("/api/maxcurrent", json={"amperage": 16})
        assert response.status_code == 200
        
        # 3. Kablo takıldı (STATE=2)
        mock_bridge.get_status.return_value = {'STATE': 2, 'PP': 1, 'CABLE': 32}
        response = client.get("/api/status")
        assert response.status_code == 200
        assert response.json()['data']['STATE'] == 2
        
        # 4. Araç bağlandı (STATE=3)
        mock_bridge.get_status.return_value = {'STATE': 3, 'CP': 1}
        response = client.get("/api/status")
        assert response.status_code == 200
        
        # 5. Şarj başlatma
        response = client.post("/api/charge/start", json={"id_tag": "TEST-001"})
        assert response.status_code == 200
        
        # 6. Şarj aktif (STATE=5)
        mock_bridge.get_status.return_value = {'STATE': 5, 'AUTH': 1, 'CABLE': 16}
        response = client.get("/api/status")
        assert response.status_code == 200
        
        # 7. Şarj durdurma
        response = client.post("/api/charge/stop", json={})
        assert response.status_code == 200
        
        # 8. Şarj bitirildi (STATE=7)
        mock_bridge.get_status.return_value = {'STATE': 7}
        response = client.get("/api/status")
        assert response.status_code == 200
    
    def test_multiple_current_changes(self, client, mock_bridge):
        """Birden fazla akım değişikliği"""
        mock_bridge.get_status.return_value = {'STATE': 1}
        
        # 8A ayarla
        response = client.post("/api/maxcurrent", json={"amperage": 8})
        assert response.status_code == 200
        
        # 16A ayarla
        response = client.post("/api/maxcurrent", json={"amperage": 16})
        assert response.status_code == 200
        
        # 24A ayarla
        response = client.post("/api/maxcurrent", json={"amperage": 24})
        assert response.status_code == 200
        
        # 32A ayarla
        response = client.post("/api/maxcurrent", json={"amperage": 32})
        assert response.status_code == 200
    
    def test_charging_with_different_currents(self, client, mock_bridge):
        """Farklı akımlarla şarj başlatma"""
        currents = [8, 16, 24, 32]
        
        for current in currents:
            # Akım ayarla
            mock_bridge.get_status.return_value = {'STATE': 1}
            response = client.post("/api/maxcurrent", json={"amperage": current})
            assert response.status_code == 200
            
            # Şarj başlat
            mock_bridge.get_status.return_value = {'STATE': 2}
            response = client.post("/api/charge/start", json={"id_tag": "TEST"})
            assert response.status_code == 200
            
            # Şarj durdur
            response = client.post("/api/charge/stop", json={})
            assert response.status_code == 200
    
    def test_error_recovery_flow(self, client, mock_bridge):
        """Hata kurtarma akışı"""
        # 1. ESP32 bağlantısı kopmuş
        mock_bridge.is_connected = False
        response = client.get("/api/status")
        assert response.status_code == 503
        
        # 2. Bağlantı yeniden kuruldu
        mock_bridge.is_connected = True
        mock_bridge.get_status.return_value = {'STATE': 1}
        response = client.get("/api/status")
        assert response.status_code == 200
        
        # 3. Normal işlemler devam edebilir
        response = client.post("/api/maxcurrent", json={"amperage": 16})
        assert response.status_code == 200
    
    def test_rapid_state_changes(self, client, mock_bridge):
        """Hızlı state değişiklikleri"""
        states = [1, 2, 3, 4, 5, 6, 7]
        
        for state in states:
            mock_bridge.get_status.return_value = {'STATE': state}
            response = client.get("/api/status")
            assert response.status_code == 200
            assert response.json()['data']['STATE'] == state

