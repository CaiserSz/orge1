"""
Performance Tests
Created: 2025-12-10 00:05:00
Last Modified: 2025-12-10 00:05:00
Version: 1.0.0
Description: Performance testleri - pytest-benchmark kullanarak
"""

import pytest
import sys
from unittest.mock import Mock, patch
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.main import app


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
        'PP': 0,
        'CPV': 3920,
        'PPV': 2455,
        'RL': 0,
        'LOCK': 0,
        'MOTOR': 0,
        'PWM': 255,
        'PB': 0,
        'STOP': 0
    })
    mock.get_status_sync = Mock(return_value={
        'STATE': 1,
        'AUTH': 0,
        'CABLE': 0,
        'MAX': 16
    })
    mock.send_authorization = Mock(return_value=True)
    mock.send_charge_stop = Mock(return_value=True)
    mock.send_current_set = Mock(return_value=True)
    return mock


@pytest.fixture
def client(mock_bridge):
    """Test client"""
    import os
    os.environ['SECRET_API_KEY'] = 'test-api-key'

    with patch('api.main.get_esp32_bridge', return_value=mock_bridge):
        yield TestClient(app)


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
            headers={"X-API-Key": "test-api-key"}
        )
        assert result.status_code == 200

    def test_start_charge_performance(self, client, benchmark):
        """Start charge endpoint performance"""
        result = benchmark(
            client.post,
            "/api/charge/start",
            json={},
            headers={"X-API-Key": "test-api-key"}
        )
        assert result.status_code == 200

    def test_stop_charge_performance(self, client, benchmark):
        """Stop charge endpoint performance"""
        result = benchmark(
            client.post,
            "/api/charge/stop",
            json={},
            headers={"X-API-Key": "test-api-key"}
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
                    headers={"X-API-Key": "test-api-key"}
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

        start_time = time.time()
        response = client.get("/api/health")
        elapsed_time = (time.time() - start_time) * 1000  # milliseconds

        assert response.status_code == 200
        assert elapsed_time < 100  # 100ms'den az olmalı

    def test_status_endpoint_response_time(self, client):
        """Status endpoint response time threshold"""
        import time

        start_time = time.time()
        response = client.get("/api/status")
        elapsed_time = (time.time() - start_time) * 1000  # milliseconds

        assert response.status_code == 200
        assert elapsed_time < 200  # 200ms'den az olmalı

    def test_set_current_response_time(self, client):
        """Set current response time threshold"""
        import time

        start_time = time.time()
        response = client.post(
            "/api/maxcurrent",
            json={"amperage": 16},
            headers={"X-API-Key": "test-api-key"}
        )
        elapsed_time = (time.time() - start_time) * 1000  # milliseconds

        assert response.status_code == 200
        assert elapsed_time < 200  # 200ms'den az olmalı

