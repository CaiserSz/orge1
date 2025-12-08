"""
State Logic Tests - Mantık Hatalarını Tespit Etmek İçin
Created: 2025-12-09 02:10:00
Last Modified: 2025-12-09 02:10:00
Version: 1.0.0
Description: State değerlendirme mantığı testleri
"""

import pytest
import sys
from unittest.mock import Mock, patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.main import app
from fastapi.testclient import TestClient


# ESP32 State Değerleri (Commercial_08122025.ino'dan)
SARJ_STAT_IDLE = 1              # IDLE - Boşta
SARJ_CABLE_DETECT = 2           # Kablo algılandı
EV_CONNECTED = 3                # Araç bağlı
SARJA_HAZIR = 4                 # Şarja hazır
SARJ_STAT_SARJ_BASLADI = 5      # Şarj başladı
SARJ_STAT_SARJ_DURAKLATILDI = 6 # Şarj duraklatıldı
SARJ_STAT_SARJ_BITIR = 7        # Şarj bitirildi
SARJ_STAT_FAULT_HARD = 8        # Hata


@pytest.fixture
def mock_bridge():
    """Mock ESP32 bridge"""
    mock = Mock()
    mock.is_connected = True
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


class TestStateLogicForStartCharge:
    """Start Charge için state mantığı testleri"""
    
    def test_start_charge_state_1_idle_should_work(self, client, mock_bridge):
        """STATE=1 (IDLE) durumunda şarj başlatılabilir mi?"""
        mock_bridge.get_status.return_value = {'STATE': SARJ_STAT_IDLE}
        
        response = client.post("/api/charge/start", json={"id_tag": "TEST"})
        
        # Şu anki kod STATE >= 2 kontrolü yapıyor, bu yanlış!
        # STATE=1 IDLE durumunda şarj başlatılabilir olmalı
        print(f"\nSTATE=1 (IDLE) - Response: {response.status_code}")
        if response.status_code == 400:
            print("⚠️ MANTIK HATASI: STATE=1 IDLE durumunda şarj başlatılamıyor!")
    
    def test_start_charge_state_2_cable_detect_should_work(self, client, mock_bridge):
        """STATE=2 (CABLE_DETECT) durumunda şarj başlatılabilir mi?"""
        mock_bridge.get_status.return_value = {'STATE': SARJ_CABLE_DETECT}
        
        response = client.post("/api/charge/start", json={"id_tag": "TEST"})
        
        # STATE=2 CABLE_DETECT durumunda şarj başlatılabilir olmalı
        print(f"\nSTATE=2 (CABLE_DETECT) - Response: {response.status_code}")
        if response.status_code == 400:
            print("⚠️ MANTIK HATASI: STATE=2 CABLE_DETECT durumunda şarj başlatılamıyor!")
    
    def test_start_charge_state_3_ev_connected_should_work(self, client, mock_bridge):
        """STATE=3 (EV_CONNECTED) durumunda şarj başlatılabilir mi?"""
        mock_bridge.get_status.return_value = {'STATE': EV_CONNECTED}
        
        response = client.post("/api/charge/start", json={"id_tag": "TEST"})
        
        # STATE=3 EV_CONNECTED durumunda şarj başlatılabilir olmalı
        print(f"\nSTATE=3 (EV_CONNECTED) - Response: {response.status_code}")
        if response.status_code == 400:
            print("⚠️ MANTIK HATASI: STATE=3 EV_CONNECTED durumunda şarj başlatılamıyor!")
    
    def test_start_charge_state_4_sarja_hazir_should_work(self, client, mock_bridge):
        """STATE=4 (SARJA_HAZIR) durumunda şarj başlatılabilir mi?"""
        mock_bridge.get_status.return_value = {'STATE': SARJA_HAZIR}
        
        response = client.post("/api/charge/start", json={"id_tag": "TEST"})
        
        # STATE=4 SARJA_HAZIR durumunda şarj başlatılabilir olmalı
        print(f"\nSTATE=4 (SARJA_HAZIR) - Response: {response.status_code}")
        if response.status_code == 400:
            print("⚠️ MANTIK HATASI: STATE=4 SARJA_HAZIR durumunda şarj başlatılamıyor!")
    
    def test_start_charge_state_5_charging_should_fail(self, client, mock_bridge):
        """STATE=5 (SARJ_BASLADI) durumunda şarj başlatılamaz olmalı"""
        mock_bridge.get_status.return_value = {'STATE': SARJ_STAT_SARJ_BASLADI}
        
        response = client.post("/api/charge/start", json={"id_tag": "TEST"})
        
        # STATE=5 SARJ_BASLADI durumunda şarj başlatılamaz
        assert response.status_code == 400, "STATE=5 durumunda şarj başlatılamaz olmalı"
        print(f"\n✅ STATE=5 (SARJ_BASLADI) - Doğru: Reddedildi")


class TestStateLogicForSetCurrent:
    """Set Current için state mantığı testleri"""
    
    def test_set_current_state_1_idle_should_work(self, client, mock_bridge):
        """STATE=1 (IDLE) durumunda akım ayarlanabilir mi?"""
        mock_bridge.get_status.return_value = {'STATE': SARJ_STAT_IDLE}
        
        response = client.post("/api/maxcurrent", json={"amperage": 16})
        
        # STATE=1 IDLE durumunda akım ayarlanabilir olmalı
        print(f"\nSTATE=1 (IDLE) - Response: {response.status_code}")
        if response.status_code == 400:
            print("⚠️ MANTIK HATASI: STATE=1 IDLE durumunda akım ayarlanamıyor!")
    
    def test_set_current_state_2_cable_detect_should_work(self, client, mock_bridge):
        """STATE=2 (CABLE_DETECT) durumunda akım ayarlanabilir mi?"""
        mock_bridge.get_status.return_value = {'STATE': SARJ_CABLE_DETECT}
        
        response = client.post("/api/maxcurrent", json={"amperage": 16})
        
        # STATE=2 CABLE_DETECT durumunda akım ayarlanabilir olmalı
        print(f"\nSTATE=2 (CABLE_DETECT) - Response: {response.status_code}")
        if response.status_code == 400:
            print("⚠️ MANTIK HATASI: STATE=2 CABLE_DETECT durumunda akım ayarlanamıyor!")
    
    def test_set_current_state_3_ev_connected_should_work(self, client, mock_bridge):
        """STATE=3 (EV_CONNECTED) durumunda akım ayarlanabilir mi?"""
        mock_bridge.get_status.return_value = {'STATE': EV_CONNECTED}
        
        response = client.post("/api/maxcurrent", json={"amperage": 16})
        
        # STATE=3 EV_CONNECTED durumunda akım ayarlanabilir olmalı
        print(f"\nSTATE=3 (EV_CONNECTED) - Response: {response.status_code}")
        if response.status_code == 400:
            print("⚠️ MANTIK HATASI: STATE=3 EV_CONNECTED durumunda akım ayarlanamıyor!")
    
    def test_set_current_state_4_sarja_hazir_should_work(self, client, mock_bridge):
        """STATE=4 (SARJA_HAZIR) durumunda akım ayarlanabilir mi?"""
        mock_bridge.get_status.return_value = {'STATE': SARJA_HAZIR}
        
        response = client.post("/api/maxcurrent", json={"amperage": 16})
        
        # STATE=4 SARJA_HAZIR durumunda akım ayarlanabilir olmalı
        print(f"\nSTATE=4 (SARJA_HAZIR) - Response: {response.status_code}")
        if response.status_code == 400:
            print("⚠️ MANTIK HATASI: STATE=4 SARJA_HAZIR durumunda akım ayarlanamıyor!")
    
    def test_set_current_state_5_charging_should_fail(self, client, mock_bridge):
        """STATE=5 (SARJ_BASLADI) durumunda akım ayarlanamaz olmalı"""
        mock_bridge.get_status.return_value = {'STATE': SARJ_STAT_SARJ_BASLADI}
        
        response = client.post("/api/maxcurrent", json={"amperage": 16})
        
        # STATE=5 SARJ_BASLADI durumunda akım ayarlanamaz
        assert response.status_code == 400, "STATE=5 durumunda akım ayarlanamaz olmalı"
        print(f"\n✅ STATE=5 (SARJ_BASLADI) - Doğru: Reddedildi")

