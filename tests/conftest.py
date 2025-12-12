"""
Pytest Configuration and Shared Fixtures
Created: 2025-12-10 10:50:00
Last Modified: 2025-12-11 20:05:00
Version: 1.0.4
Description: Standart pytest fixture'ları ve konfigürasyonu
"""

import os
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

# Test modunda rate limiting'i konfigürasyon seviyesinde devre dışı bırak
os.environ.setdefault("PYTEST_DISABLE_RATE_LIMIT", "1")
from api import config as config_module

config_module.config.load()

from api.event_detector import ESP32State
from api.main import app
from api.routers import dependencies
from esp32 import bridge as esp32_bridge_module
from esp32.bridge import ESP32Bridge

# Test ortamında gerçek startup/shutdown hook'larını iptal et (donanım bağlantısını engellemek için)
app.router.on_startup.clear()
app.router.on_shutdown.clear()


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


@pytest.fixture(autouse=True)
def override_bridge_dependencies(mock_esp32_bridge, request):
    """
    Tüm testlerde varsayılan olarak ESP32 bridge dependency'lerini mock'lar.

    - FastAPI dependency_overrides ile `get_bridge` dependency'si mocklanır.
    - `esp32.bridge.get_esp32_bridge`, `api.routers.dependencies.get_esp32_bridge`
      ve `api.main.get_esp32_bridge` patch edilir
      ki doğrudan bu fonksiyonları kullanan kod da mock bridge ile çalışsın.
    - Test içinde özel bir bridge senaryosu gerekiyorsa, ilgili test
      `app.dependency_overrides[dependencies.get_bridge]` üzerinden kendi
      override'ını verebilir (ve test sonunda geri almalıdır).
    """
    # ESP32Bridge'in kendi unit testlerinde gerçek `connect()` davranışını
    # (serial mock'ları ile) doğrulamak istiyoruz; burada `connect()` no-op
    # patch'i bu testleri bozuyor. Bu yüzden ilgili test dosyalarında
    # global override'ı devre dışı bırak.
    test_path = str(getattr(request, "fspath", ""))
    if (
        test_path.endswith("tests/test_bridge.py")
        or "/tests/esp32/" in test_path
        or test_path.endswith("tests/esp32/test_bridge_additional_edge_cases.py")
    ):
        # Önceki testlerden kalmış override varsa temizle
        app.dependency_overrides.pop(dependencies.get_bridge, None)
        yield
        app.dependency_overrides.pop(dependencies.get_bridge, None)
        return

    # Singleton'ı temizle ve connect'i no-op yap
    esp32_bridge_module._esp32_bridge_instance = None
    with patch.object(ESP32Bridge, "connect", return_value=True):
        with patch(
            "esp32.bridge.get_esp32_bridge", return_value=mock_esp32_bridge
        ), patch(
            "api.routers.dependencies.get_esp32_bridge", return_value=mock_esp32_bridge
        ), patch("api.main.get_esp32_bridge", return_value=mock_esp32_bridge):
            # FastAPI dependency override: tüm router'larda mock bridge kullan
            app.dependency_overrides[dependencies.get_bridge] = (
                lambda: mock_esp32_bridge
            )
            # Modül seviyesindeki singleton'ı da mock ile değiştir (varsa)
            if hasattr(esp32_bridge_module, "_bridge"):
                esp32_bridge_module._bridge = mock_esp32_bridge
            yield
            app.dependency_overrides.pop(dependencies.get_bridge, None)


@pytest.fixture
def client(mock_esp32_bridge):
    """
    Standart FastAPI test client fixture

    Tüm test dosyalarında kullanılacak standart test client.
    Mock bridge otomatik olarak inject edilir.
    """
    # Test için API key set et ve config'i bu anahtar ile yeniden yükle
    os.environ["SECRET_API_KEY"] = "test-api-key"
    from api import config as config_module

    config_module.config.load()

    # Standart mock yöntemi: esp32 bridge getter'ını ve event detector'ı patch et
    with patch("esp32.bridge.get_esp32_bridge", return_value=mock_esp32_bridge):
        with patch(
            "api.routers.dependencies.get_esp32_bridge", return_value=mock_esp32_bridge
        ):
            # Event detector için de mock bridge gerekli
            with patch(
                "api.event_detector.get_event_detector"
            ) as mock_get_event_detector:
                # Mock event detector oluştur
                mock_event_detector = Mock()
                mock_event_detector.is_monitoring = True
                mock_event_detector._monitor_thread = Mock()
                mock_event_detector._monitor_thread.is_alive = Mock(return_value=True)
                mock_get_event_detector.return_value = mock_event_detector
                # Tüm isteklerde varsayılan olarak geçerli API key header'ı gönder
                client = TestClient(
                    app,
                    headers={
                        "X-API-Key": os.environ.get("SECRET_API_KEY", "test-api-key")
                    },
                    raise_server_exceptions=False,
                )
                yield client


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
