"""
Performance Tests
Created: 2025-12-10 00:05:00
Last Modified: 2025-12-11 20:00:00
Version: 1.0.2
Description: Performance testleri - pytest-benchmark kullanarak
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.event_detector import ESP32State
from api.main import app

# conftest.py'deki standart fixture'ları kullan
# mock_esp32_bridge, client, test_headers fixture'ları conftest.py'den gelir


@pytest.fixture
def client(mock_esp32_bridge):
    """Test client"""
    import os

    os.environ["SECRET_API_KEY"] = "test-api-key"

    with patch(
        "api.routers.dependencies.get_esp32_bridge", return_value=mock_esp32_bridge
    ):
        yield TestClient(app, raise_server_exceptions=False)


class TestAPIPerformance:
    """API performance testleri"""

    def test_health_check_performance(self, client, benchmark):
        """Health check endpoint performance"""
        result = benchmark(client.get, "/api/health")
        assert result.status_code == 200

    def test_status_endpoint_performance(self, client, benchmark):
        """Status endpoint performance"""
        result = benchmark(client.get, "/api/status")
        assert result.status_code == 200

    def test_get_available_currents_performance(self, client, benchmark):
        """Get available currents endpoint performance"""
        result = benchmark(client.get, "/api/current/available")
        assert result.status_code == 200

    def test_set_current_performance(self, client, benchmark):
        """Set current endpoint performance"""
        result = benchmark(
            client.post,
            "/api/maxcurrent",
            json={"amperage": 16},
            headers={"X-API-Key": "test-api-key"},
        )
        assert result.status_code == 200

    def test_start_charge_performance(self, client, benchmark, mock_esp32_bridge):
        """Start charge endpoint performance"""
        # Charge start yalnızca EV_CONNECTED state'inde geçerli
        mock_esp32_bridge.get_status.return_value = {
            "STATE": ESP32State.EV_CONNECTED.value
        }
        result = benchmark(
            client.post,
            "/api/charge/start",
            json={},
            headers={"X-API-Key": "test-api-key"},
        )
        assert result.status_code == 200

    def test_stop_charge_performance(self, client, benchmark):
        """Stop charge endpoint performance"""
        result = benchmark(
            client.post,
            "/api/charge/stop",
            json={},
            headers={"X-API-Key": "test-api-key"},
        )
        assert result.status_code == 200


class TestConcurrentPerformance:
    """Eşzamanlı performans testleri"""

    def test_concurrent_status_requests_performance(self, client, benchmark):
        """Eşzamanlı status istekleri performance"""
        import threading

        def concurrent_requests():
            results = []

            def get_status():
                response = client.get("/api/status")
                results.append(response.status_code)

            threads = []
            for _ in range(10):
                thread = threading.Thread(target=get_status)
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            return all(status == 200 for status in results)

        result = benchmark(concurrent_requests)
        assert result is True

    def test_concurrent_current_set_performance(self, client, benchmark):
        """Eşzamanlı current set istekleri performance"""
        import threading

        def concurrent_requests():
            results = []

            def set_current(amperage):
                response = client.post(
                    "/api/maxcurrent",
                    json={"amperage": amperage},
                    headers={"X-API-Key": "test-api-key"},
                )
                results.append(response.status_code)

            threads = []
            amperages = [6, 10, 13, 16, 20, 25, 32]
            for amp in amperages:
                thread = threading.Thread(target=set_current, args=(amp,))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            return all(status == 200 for status in results)

        result = benchmark(concurrent_requests)
        assert result is True


class TestResponseTimeThresholds:
    """Response time threshold testleri"""

    def test_health_check_response_time(self, client):
        """Health check response time threshold"""
        import time

        # Warm-up (ilk request genellikle startup/cache etkileriyle yavaş olabilir)
        client.get("/api/health")

        start_time = time.perf_counter()
        response = client.get("/api/health")
        elapsed_time = (time.perf_counter() - start_time) * 1000  # milliseconds

        assert response.status_code == 200
        # RPi ve CI ortamlarında zamanlama dalgalanmaları olabildiği için threshold daha toleranslı
        assert elapsed_time < 500  # ms

    def test_status_endpoint_response_time(self, client):
        """Status endpoint response time threshold"""
        import time

        # Warm-up
        client.get("/api/status")

        start_time = time.perf_counter()
        response = client.get("/api/status")
        elapsed_time = (time.perf_counter() - start_time) * 1000  # milliseconds

        assert response.status_code == 200
        assert elapsed_time < 800  # ms

    def test_set_current_response_time(self, client):
        """Set current response time threshold"""
        import time

        # Warm-up
        client.post(
            "/api/maxcurrent",
            json={"amperage": 16},
            headers={"X-API-Key": "test-api-key"},
        )

        start_time = time.perf_counter()
        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 16},
            headers={"X-API-Key": "test-api-key"},
        )
        elapsed_time = (time.perf_counter() - start_time) * 1000  # milliseconds

        assert response.status_code == 200
        assert elapsed_time < 800  # ms
