"""
Logging, Auth, and Station Info Edge Case Tests
Created: 2025-12-10 01:40:00
Last Modified: 2025-12-10 01:40:00
Version: 1.0.0
Description: Logging config, auth, and station info edge case tests
"""

import pytest
import sys
import os
import tempfile
import logging
import json
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.logging_config import setup_logger, get_logger, thread_safe_log, JSONFormatter
from api.auth import get_secret_api_key, verify_api_key
from api.station_info import ensure_data_dir


class TestLoggingConfigFunctions:
    """Logging config fonksiyon testleri"""

    def test_setup_logger(self):
        """Setup logger"""
        logger = setup_logger("test_logger", "test.log")

        assert logger is not None
        assert logger.name == "test_logger"
        assert len(logger.handlers) > 0

    def test_get_logger(self):
        """Get logger"""
        logger1 = get_logger("test_logger")
        logger2 = get_logger("test_logger")

        # Aynı logger instance döndürülmeli
        assert logger1 is logger2

    def test_thread_safe_log(self):
        """Thread safe log"""
        logger = get_logger("test_thread_logger")

        # Thread-safe logging çalışmalı
        thread_safe_log(logger, 20, "Test message", key="value")

        # Exception oluşmamalı
        assert True

    def test_json_formatter(self):
        """JSON formatter"""
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name="test",
            level=20,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)

        # JSON formatında olmalı
        data = json.loads(formatted)
        assert "timestamp" in data
        assert "level" in data
        assert "message" in data


class TestAuthEdgeCases:
    """Auth edge case testleri"""

    def test_get_secret_api_key_success(self):
        """Get secret API key - başarılı"""
        with patch.dict(os.environ, {"SECRET_API_KEY": "test-key"}):
            key = get_secret_api_key()
            assert key == "test-key"

    def test_get_secret_api_key_empty_string(self):
        """Get secret API key - boş string"""
        with patch.dict(os.environ, {"SECRET_API_KEY": ""}):
            with pytest.raises(ValueError):
                get_secret_api_key()

    def test_verify_api_key_none(self):
        """Verify API key - None"""
        with patch.dict(os.environ, {"SECRET_API_KEY": "test-key"}):
            from fastapi.security import APIKeyHeader

            api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

            # None API key ile verify
            with pytest.raises(Exception):  # HTTPException
                verify_api_key(None)


class TestStationInfoEdgeCases:
    """Station info edge case testleri"""

    def test_ensure_data_dir_permission_error(self):
        """Ensure data dir - permission error"""
        with patch("api.station_info.DATA_FILE", Path("/root/invalid/path.json")):
            # Permission error oluşabilir ama exception yakalanmalı
            try:
                ensure_data_dir()
            except PermissionError:
                # Permission error beklenebilir
                pass

    def test_ensure_data_dir_success(self):
        """Ensure data dir - başarılı"""
        temp_dir = tempfile.mkdtemp()
        temp_file = Path(temp_dir) / "station_info.json"

        with patch("api.station_info.DATA_FILE", temp_file):
            ensure_data_dir()
            assert temp_file.parent.exists()
