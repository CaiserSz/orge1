"""
Pytest Configuration and Shared Fixtures
Created: 2025-12-10 10:50:00
Last Modified: 2025-12-10 10:50:00
Version: 1.0.0
Description: Standart pytest fixture'ları ve konfigürasyonu
"""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

# Proje root'unu path'e ekle
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from api.event_detector import ESP32State
from api.main import app
from esp32.bridge import ESP32Bridge


@pytest.fixture
def mock_esp32_bridge():
    """
    Standart ESP32 bridge mock fixture

    Tüm test dosyalarında kullanılacak standart mock bridge.
    """
    mock_bridge = Mock(spec=ESP32Bridge)
    mock_bridge.is_connected = True

    # get_status için default return value
    default_status = {
        "STATE": ESP32State.IDLE.value,
        "AUTH": 0,
        "CABLE": 0,
        "MAX": 16,
        "CP": 0,
        "PP": 0,
        "CPV": 3920,
        "PPV": 2455,
        "RL": 0,
        "LOCK": 0,
        "MOTOR": 0,
        "PWM": 255,
        "PB": 0,
        "STOP": 0,
    }
    # get_status fonksiyonu max_age_seconds parametresini kabul etmeli
    # return_value kullanarak test içinde değiştirilebilir hale getir
    mock_bridge.get_status = Mock(return_value=default_status)

    # get_status_sync için timeout parametresi olmadan çalışmalı
    def mock_get_status_sync(timeout=None):
        return {
            "STATE": ESP32State.IDLE.value,
            "AUTH": 0,
            "CABLE": 0,
            "MAX": 16,
        }
    mock_bridge.get_status_sync = Mock(side_effect=mock_get_status_sync)
    mock_bridge.send_authorization = Mock(return_value=True)
    mock_bridge.send_charge_stop = Mock(return_value=True)
    mock_bridge.send_current_set = Mock(return_value=True)
    return mock_bridge


@pytest.fixture
def client(mock_esp32_bridge):
    """
    Standart FastAPI test client fixture

    Tüm test dosyalarında kullanılacak standart test client.
    Mock bridge otomatik olarak inject edilir.
    """
    # Test için API key set et
    os.environ["SECRET_API_KEY"] = "test-api-key"

    # Standart mock yöntemi: Tüm bridge getter'ları patch et
    with patch("api.routers.dependencies.get_bridge", return_value=mock_esp32_bridge):
        with patch("esp32.bridge.get_esp32_bridge", return_value=mock_esp32_bridge):
            # Event detector için de mock bridge gerekli
            with patch("api.event_detector.get_event_detector") as mock_get_event_detector:
                # Mock event detector oluştur
                mock_event_detector = Mock()
                mock_event_detector.is_monitoring = True
                mock_event_detector._monitor_thread = Mock()
                mock_event_detector._monitor_thread.is_alive = Mock(return_value=True)
                mock_get_event_detector.return_value = mock_event_detector
                yield TestClient(app)


@pytest.fixture
def api_key():
    """
    Standart API key fixture

    Test için kullanılacak API key.
    """
    return "test-api-key"


@pytest.fixture
def test_headers(api_key):
    """
    Standart test headers fixture

    API key içeren header'lar.
    """
    return {"X-API-Key": api_key}


@pytest.fixture
def mock_status_idle():
    """
    IDLE state mock status fixture
    """
    return {"STATE": ESP32State.IDLE.value, "AUTH": 0, "CABLE": 0, "MAX": 16}


@pytest.fixture
def mock_status_cable_detect():
    """
    CABLE_DETECT state mock status fixture
    """
    return {"STATE": ESP32State.CABLE_DETECT.value, "PP": 1, "CABLE": 32}


@pytest.fixture
def mock_status_ev_connected():
    """
    EV_CONNECTED state mock status fixture
    """
    return {"STATE": ESP32State.EV_CONNECTED.value, "CP": 1}


@pytest.fixture
def mock_status_ready():
    """
    READY state mock status fixture
    """
    return {"STATE": ESP32State.READY.value, "AUTH": 1}


@pytest.fixture
def mock_status_charging():
    """
    CHARGING state mock status fixture
    """
    return {
        "STATE": ESP32State.CHARGING.value,
        "AUTH": 1,
        "CABLE": 16,
        "MAX": 16,
    }


@pytest.fixture
def mock_status_fault():
    """
    FAULT_HARD state mock status fixture
    """
    return {"STATE": ESP32State.FAULT_HARD.value}

