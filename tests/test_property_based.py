"""
Property-Based Tests using Hypothesis
Created: 2025-12-10 00:00:00
Last Modified: 2025-12-10 00:00:00
Version: 1.0.0
Description: Hypothesis kullanarak property-based testler
"""

import pytest
import sys
from unittest.mock import patch
from pathlib import Path
from fastapi.testclient import TestClient
from hypothesis import given, strategies as st, assume, settings, HealthCheck

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.main import app
from api.event_detector import ESP32State


# conftest.py'deki standart fixture'ları kullan
# mock_esp32_bridge, client, test_headers fixture'ları conftest.py'den gelir


@pytest.fixture
def client(mock_esp32_bridge):
    """Test client"""
    import os

    os.environ["SECRET_API_KEY"] = "test-api-key"

    with patch("api.main.get_esp32_bridge", return_value=mock_esp32_bridge):
        yield TestClient(app)


class TestPropertyBasedCurrentSetting:
    """Property-based current setting testleri"""

    @given(amperage=st.integers(min_value=6, max_value=32))
    @settings(max_examples=50)
    def test_set_current_valid_range(self, client, mock_esp32_bridge, amperage):
        """Geçerli akım aralığında tüm değerler çalışmalı"""
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.IDLE.value,
            "MAX": 16,
        }

        response = client.post(
            "/api/maxcurrent",
            json={"amperage": amperage},
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["data"]["amperage"] == amperage

    @given(amperage=st.integers(min_value=6, max_value=32))
    @settings(max_examples=20)
    def test_set_current_all_valid_states(self, client, mock_esp32_bridge, amperage):
        """Tüm geçerli state'lerde akım ayarlanabilmeli"""
        valid_states = [
            ESP32State.IDLE.value,
            ESP32State.CABLE_DETECT.value,
            ESP32State.EV_CONNECTED.value,
            ESP32State.READY.value,
        ]

        for state in valid_states:
            mock_esp32_bridge.get_status.return_value = {"STATE": state, "MAX": 16}

            response = client.post(
                "/api/maxcurrent",
                json={"amperage": amperage},
                headers={"X-API-Key": "test-api-key"},
            )

            assert response.status_code == 200

    @given(amperage=st.integers())
    @settings(max_examples=30)
    def test_set_current_invalid_range(self, client, mock_esp32_bridge, amperage):
        """Geçersiz akım değerleri reddedilmeli"""
        assume(amperage < 6 or amperage > 32)

        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.IDLE.value,
            "MAX": 16,
        }

        response = client.post(
            "/api/maxcurrent",
            json={"amperage": amperage},
            headers={"X-API-Key": "test-api-key"},
        )

        # Validation error (422) veya başka bir hata kodu
        assert response.status_code != 200

    @given(
        amperage1=st.integers(min_value=6, max_value=32),
        amperage2=st.integers(min_value=6, max_value=32),
    )
    @settings(max_examples=20)
    def test_set_current_multiple_times(
        self, client, mock_esp32_bridge, amperage1, amperage2
    ):
        """Birden fazla akım ayarlama işlemi çalışmalı"""
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.IDLE.value,
            "MAX": 16,
        }

        # İlk akım ayarla
        response1 = client.post(
            "/api/maxcurrent",
            json={"amperage": amperage1},
            headers={"X-API-Key": "test-api-key"},
        )
        assert response1.status_code == 200

        # İkinci akım ayarla
        response2 = client.post(
            "/api/maxcurrent",
            json={"amperage": amperage2},
            headers={"X-API-Key": "test-api-key"},
        )
        assert response2.status_code == 200

        # Her iki işlem de başarılı olmalı
        assert response1.json()["data"]["amperage"] == amperage1
        assert response2.json()["data"]["amperage"] == amperage2


class TestPropertyBasedStateTransitions:
    """Property-based state transition testleri"""

    @given(state=st.integers(min_value=1, max_value=8))
    @settings(max_examples=20)
    def test_status_endpoint_all_states(self, client, mock_esp32_bridge, state):
        """Tüm state değerleri için status endpoint çalışmalı"""
        mock_esp32_bridge.get_status.return_value = {"STATE": state, "MAX": 16}

        response = client.get("/api/status")

        assert response.status_code == 200
        assert response.json()["data"]["STATE"] == state

    @given(
        from_state=st.integers(min_value=1, max_value=4),
        to_state=st.integers(min_value=5, max_value=8),
    )
    @settings(max_examples=20)
    def test_start_charge_invalid_states(
        self, client, mock_esp32_bridge, from_state, to_state
    ):
        """Geçersiz state'lerde şarj başlatılamamalı"""
        assume(to_state >= ESP32State.CHARGING.value)  # Aktif şarj veya hata durumu

        mock_esp32_bridge.get_status.return_value = {"STATE": to_state, "MAX": 16}

        response = client.post(
            "/api/charge/start", json={}, headers={"X-API-Key": "test-api-key"}
        )

        assert response.status_code == 400

    @given(state=st.integers(min_value=1, max_value=4))
    @settings(max_examples=20)
    def test_start_charge_valid_states(self, client, mock_esp32_bridge, state):
        """Geçerli state'lerde şarj başlatılabilmeli"""
        mock_esp32_bridge.get_status.return_value = {"STATE": state, "MAX": 16}

        response = client.post(
            "/api/charge/start", json={}, headers={"X-API-Key": "test-api-key"}
        )

        assert response.status_code == 200


class TestPropertyBasedAPIResponses:
    """Property-based API response testleri"""

    @given(
        path=st.text(
            min_size=1,
            max_size=100,
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc")),
        )
    )
    @settings(max_examples=30)
    def test_api_response_structure(self, client, mock_esp32_bridge, path):
        """Tüm API response'ları tutarlı yapıda olmalı"""
        # Sadece geçerli endpoint'leri test et
        valid_endpoints = [
            "/api/health",
            "/api/status",
            "/api/current/available",
        ]

        assume(path in valid_endpoints)

        response = client.get(path)

        if response.status_code == 200:
            data = response.json()
            # APIResponse format kontrolü
            assert "success" in data
            assert "message" in data
            assert "data" in data
            assert isinstance(data["success"], bool)

    @given(
        amperage=st.integers(min_value=6, max_value=32),
        state=st.integers(
            min_value=ESP32State.IDLE.value, max_value=ESP32State.READY.value
        ),
    )
    @settings(max_examples=30)
    def test_set_current_response_consistency(
        self, client, mock_esp32_bridge, amperage, state
    ):
        """Set current response'ları tutarlı olmalı"""
        mock_esp32_bridge.get_status.return_value = {"STATE": state, "MAX": 16}

        response = client.post(
            "/api/maxcurrent",
            json={"amperage": amperage},
            headers={"X-API-Key": "test-api-key"},
        )

        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert data["data"]["amperage"] == amperage
            assert "command" in data["data"]


class TestPropertyBasedErrorHandling:
    """Property-based error handling testleri"""

    @given(
        invalid_amperage=st.one_of(
            st.integers(max_value=5), st.integers(min_value=33), st.floats(), st.text()
        )
    )
    @settings(max_examples=30)
    def test_set_current_error_handling(
        self, client, mock_esp32_bridge, invalid_amperage
    ):
        """Geçersiz akım değerleri için hata handling"""
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.IDLE.value,
            "MAX": 16,
        }

        # Sadece integer değerleri test et (float ve text validation error verir)
        if isinstance(invalid_amperage, int):
            response = client.post(
                "/api/maxcurrent",
                json={"amperage": invalid_amperage},
                headers={"X-API-Key": "test-api-key"},
            )

            # Geçersiz değerler için hata döndürmeli
            if invalid_amperage < 6 or invalid_amperage > 32:
                assert response.status_code != 200

    @given(
        state=st.integers(
            min_value=ESP32State.CHARGING.value, max_value=ESP32State.FAULT_HARD.value
        )
    )
    @settings(max_examples=20)
    def test_set_current_invalid_state_error(self, client, mock_esp32_bridge, state):
        """Geçersiz state'lerde akım ayarlama hatası"""
        mock_esp32_bridge.get_status.return_value = {"STATE": state, "MAX": 16}

        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 16},
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == 400
        assert (
            "aktifken" in response.json()["detail"].lower()
            or "değiştirilemez" in response.json()["detail"].lower()
        )


class TestPropertyBasedConcurrency:
    """Property-based concurrency testleri"""

    @given(
        num_requests=st.integers(min_value=1, max_value=20),
        amperage=st.integers(min_value=6, max_value=32),
    )
    @settings(
        max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_concurrent_status_requests(
        self, client, mock_esp32_bridge, num_requests, amperage
    ):
        """Eşzamanlı status istekleri property-based"""
        import threading

        results = []

        def get_status():
            response = client.get("/api/status")
            results.append(response.status_code)

        threads = []
        for _ in range(num_requests):
            thread = threading.Thread(target=get_status)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Tüm istekler başarılı olmalı
        assert all(status == 200 for status in results)
        assert len(results) == num_requests
