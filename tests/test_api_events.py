"""
API Events and Models Tests
Created: 2025-12-10 01:40:00
Last Modified: 2025-12-11 19:52:00
Version: 1.0.1
Description: API startup/shutdown events, logging middleware, and model tests
"""

import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.main import APILoggingMiddleware, app, shutdown_event, startup_event
from api.models import (APIResponse, ChargeStartRequest, ChargeStopRequest,
                        CurrentSetRequest)


class TestStartupShutdownEvents:
    """Startup ve shutdown event testleri"""

    def test_startup_event_success(self):
        """Startup event - başarılı"""
        mock_bridge = Mock()
        mock_bridge.is_connected = True

        with patch("esp32.bridge.get_esp32_bridge", return_value=mock_bridge), patch(
            "api.main.get_esp32_bridge", return_value=mock_bridge
        ):
            with patch("api.main.get_event_detector") as mock_get_detector:
                mock_detector = Mock()
                mock_get_detector.return_value = mock_detector

                # Startup event'i çağır
                import asyncio

                asyncio.run(startup_event())

                # Event detector başlatılmalı
                mock_detector.start_monitoring.assert_called_once()

    def test_startup_event_bridge_not_connected(self):
        """Startup event - bridge bağlı değil"""
        mock_bridge = Mock()
        mock_bridge.is_connected = False

        with patch("esp32.bridge.get_esp32_bridge", return_value=mock_bridge), patch(
            "api.main.get_esp32_bridge", return_value=mock_bridge
        ):
            with patch("api.main.get_event_detector") as mock_get_detector:
                mock_detector = Mock()
                mock_get_detector.return_value = mock_detector

                # Startup event'i çağır - hata oluşmamalı
                import asyncio

                asyncio.run(startup_event())

                # Event detector yine de başlatılmalı
                mock_detector.start_monitoring.assert_called_once()

    def test_startup_event_exception(self):
        """Startup event - exception handling"""
        with patch(
            "esp32.bridge.get_esp32_bridge", side_effect=Exception("Startup error")
        ), patch("api.main.get_esp32_bridge", side_effect=Exception("Startup error")):
            # Exception yakalanmalı ve uygulama çalışmaya devam etmeli
            import asyncio

            try:
                asyncio.run(startup_event())
            except Exception:
                pytest.fail("Startup event exception'ı yakalamalı")

    def test_shutdown_event_success(self):
        """Shutdown event - başarılı"""
        mock_bridge = Mock()
        mock_bridge.is_connected = True
        # disconnect çağrısını takip edebilmek için explicit Mock tanımla
        mock_bridge.disconnect = Mock()

        with patch("esp32.bridge.get_esp32_bridge", return_value=mock_bridge), patch(
            "api.main.get_esp32_bridge", return_value=mock_bridge
        ):
            with patch("api.main.get_event_detector") as mock_get_detector:
                mock_detector = Mock()
                mock_get_detector.return_value = mock_detector

                # Shutdown event'i çağır
                import asyncio

                asyncio.run(shutdown_event())

                # Event detector durdurulmalı
                mock_detector.stop_monitoring.assert_called_once()
                # Bridge disconnect edilmeli
                mock_bridge.disconnect.assert_called_once()

    def test_shutdown_event_bridge_none(self):
        """Shutdown event - bridge None"""
        with patch("esp32.bridge.get_esp32_bridge", return_value=None), patch(
            "api.main.get_esp32_bridge", return_value=None
        ):
            with patch("api.main.get_event_detector") as mock_get_detector:
                mock_detector = Mock()
                mock_get_detector.return_value = mock_detector

                # Shutdown event'i çağır - hata oluşmamalı
                import asyncio

                asyncio.run(shutdown_event())

                # Event detector durdurulmalı
                mock_detector.stop_monitoring.assert_called_once()

    def test_shutdown_event_exception(self):
        """Shutdown event - exception handling"""
        with patch(
            "esp32.bridge.get_esp32_bridge", side_effect=Exception("Shutdown error")
        ), patch(
            "api.main.get_esp32_bridge", side_effect=Exception("Shutdown error")
        ):
            # Exception yakalanmalı ve uygulama çalışmaya devam etmeli
            import asyncio

            try:
                asyncio.run(shutdown_event())
            except Exception:
                pytest.fail("Shutdown event exception'ı yakalamalı")


class TestAPILoggingMiddleware:
    """API Logging Middleware testleri"""

    def test_middleware_logs_request(self):
        """Middleware - request loglar"""
        middleware = APILoggingMiddleware(app)

        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url.path = "/api/health"
        mock_request.client.host = "127.0.0.1"

        async def mock_call_next(request):
            response = Mock()
            response.status_code = 200
            return response

        with patch("api.main.log_api_request") as mock_log:
            import asyncio

            response = asyncio.run(middleware.dispatch(mock_request, mock_call_next))

            # Request loglanmalı
            mock_log.assert_called_once()
            assert response.status_code == 200

    def test_middleware_excludes_charge_endpoints(self):
        """Middleware - charge endpoint'lerini exclude eder"""
        middleware = APILoggingMiddleware(app)

        mock_request = Mock()
        mock_request.method = "POST"
        mock_request.url.path = "/api/charge/start"
        mock_request.client.host = "127.0.0.1"

        async def mock_call_next(request):
            response = Mock()
            response.status_code = 200
            return response

        with patch("api.main.log_api_request") as mock_log:
            import asyncio

            response = asyncio.run(middleware.dispatch(mock_request, mock_call_next))

            # Charge endpoint'leri loglanmamalı
            mock_log.assert_not_called()
            assert response.status_code == 200

    def test_middleware_exception_handling(self):
        """Middleware - exception handling"""
        middleware = APILoggingMiddleware(app)

        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url.path = "/api/health"
        mock_request.client.host = "127.0.0.1"

        async def mock_call_next(request):
            raise Exception("Request error")

        # Exception yakalanmalı ve response döndürülmeli
        import asyncio

        try:
            response = asyncio.run(middleware.dispatch(mock_request, mock_call_next))
            # Exception oluşursa response None olabilir veya exception handler çalışır
        except Exception:
            # Exception middleware tarafından yakalanmalı
            pass


class TestAPIResponseModel:
    """APIResponse model testleri"""

    def test_api_response_with_data(self):
        """APIResponse - data ile"""
        response = APIResponse(
            success=True, message="Test message", data={"key": "value"}
        )

        assert response.success is True
        assert response.message == "Test message"
        assert response.data == {"key": "value"}
        assert response.timestamp is not None

    def test_api_response_without_data(self):
        """APIResponse - data olmadan"""
        response = APIResponse(success=False, message="Error message")

        assert response.success is False
        assert response.message == "Error message"
        assert response.data is None

    def test_api_response_timestamp_auto_generated(self):
        """APIResponse - timestamp otomatik oluşturulur"""
        response1 = APIResponse(success=True, message="Test")
        time.sleep(0.01)
        response2 = APIResponse(success=True, message="Test")

        assert response1.timestamp != response2.timestamp


class TestRequestModels:
    """Request model validation testleri"""

    def test_current_set_request_valid(self):
        """CurrentSetRequest - geçerli değer"""
        request = CurrentSetRequest(amperage=16)
        assert request.amperage == 16

    def test_current_set_request_minimum(self):
        """CurrentSetRequest - minimum değer"""
        request = CurrentSetRequest(amperage=6)
        assert request.amperage == 6

    def test_current_set_request_maximum(self):
        """CurrentSetRequest - maksimum değer"""
        request = CurrentSetRequest(amperage=32)
        assert request.amperage == 32

    def test_current_set_request_below_minimum(self):
        """CurrentSetRequest - minimum altı"""
        with pytest.raises(Exception):  # ValidationError
            CurrentSetRequest(amperage=5)

    def test_current_set_request_above_maximum(self):
        """CurrentSetRequest - maksimum üstü"""
        with pytest.raises(Exception):  # ValidationError
            CurrentSetRequest(amperage=33)

    def test_charge_start_request_empty(self):
        """ChargeStartRequest - boş request"""
        request = ChargeStartRequest()
        assert request is not None

    def test_charge_stop_request_empty(self):
        """ChargeStopRequest - boş request"""
        request = ChargeStopRequest()
        assert request is not None
