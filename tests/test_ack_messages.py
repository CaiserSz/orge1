"""
ACK Message Parsing and Handling Tests
Created: 2025-12-10 18:50:00
Last Modified: 2025-12-10 18:50:00
Version: 1.0.0
Description: ACK mesajlarını parse etme ve işleme testleri
"""

from unittest.mock import Mock

import pytest

from esp32.bridge import ESP32Bridge


class TestParseACKMessage:
    """ACK message parsing tests"""

    def test_parse_ack_message_success(self):
        """Test successful ACK message parsing"""
        bridge = ESP32Bridge()
        message = "<ACK;CMD=AUTH;STATUS=OK;>"
        result = bridge._parse_ack_message(message)
        assert result is not None
        assert result["CMD"] == "AUTH"
        assert result["STATUS"] == "OK"
        assert "timestamp" in result

    def test_parse_ack_message_with_extra_fields(self):
        """Test parsing ACK message with extra fields"""
        bridge = ESP32Bridge()
        message = "<ACK;CMD=SETMAXAMP;STATUS=OK;VALUE=16;>"
        result = bridge._parse_ack_message(message)
        assert result is not None
        assert result["CMD"] == "SETMAXAMP"
        assert result["STATUS"] == "OK"
        assert result["VALUE"] == "16"

    def test_parse_ack_message_error_status(self):
        """Test parsing ACK message with error status"""
        bridge = ESP32Bridge()
        message = "<ACK;CMD=SETMAXAMP;STATUS=ERR;>"
        result = bridge._parse_ack_message(message)
        assert result is not None
        assert result["CMD"] == "SETMAXAMP"
        assert result["STATUS"] == "ERR"

    def test_parse_ack_message_invalid_format(self):
        """Test parsing invalid ACK format"""
        bridge = ESP32Bridge()
        message = "INVALID MESSAGE"
        result = bridge._parse_ack_message(message)
        assert result is None

    def test_parse_ack_message_empty(self):
        """Test parsing empty message"""
        bridge = ESP32Bridge()
        message = ""
        result = bridge._parse_ack_message(message)
        assert result is None

    def test_parse_ack_message_missing_closing(self):
        """Test parsing message with missing closing bracket"""
        bridge = ESP32Bridge()
        message = "<ACK;CMD=AUTH;STATUS=OK;"
        result = bridge._parse_ack_message(message)
        assert result is None

    def test_parse_ack_message_whitespace(self):
        """Test parsing ACK message with whitespace"""
        bridge = ESP32Bridge()
        message = "<ACK; CMD = AUTH ; STATUS = OK ; >"
        result = bridge._parse_ack_message(message)
        assert result is not None
        assert result["CMD"] == "AUTH"
        assert result["STATUS"] == "OK"


class TestWaitForACK:
    """Wait for ACK message tests"""

    @pytest.fixture
    def mock_bridge(self):
        """Mock ESP32Bridge with serial connection"""
        bridge = ESP32Bridge()
        bridge.is_connected = True
        bridge.serial_connection = Mock()
        bridge.serial_connection.is_open = True
        bridge.serial_connection.in_waiting = 0
        bridge.serial_connection.readline = Mock()
        return bridge

    def test_wait_for_ack_success(self, mock_bridge):
        """Test successful ACK wait"""
        # ACK queue mekanizması kullanılıyor, queue'ya ACK ekle
        ack = {"CMD": "AUTH", "STATUS": "OK", "timestamp": "2025-12-10T19:00:00"}
        mock_bridge._ack_queue.put_nowait(ack)

        result = mock_bridge._wait_for_ack("AUTH", timeout=0.1)
        assert result is not None
        assert result["CMD"] == "AUTH"
        assert result["STATUS"] == "OK"

    def test_wait_for_ack_timeout(self, mock_bridge):
        """Test ACK wait timeout"""
        mock_bridge.serial_connection.in_waiting = 0
        result = mock_bridge._wait_for_ack("AUTH", timeout=0.1)
        assert result is None

    def test_wait_for_ack_wrong_command(self, mock_bridge):
        """Test ACK wait with wrong command"""
        ack_message = "<ACK;CMD=SETMAXAMP;STATUS=OK;>"
        mock_bridge.serial_connection.in_waiting = len(ack_message)
        mock_bridge.serial_connection.readline.return_value = ack_message.encode(
            "utf-8"
        )

        result = mock_bridge._wait_for_ack("AUTH", timeout=0.1)
        assert result is None  # Wrong command, should timeout

    def test_wait_for_ack_not_connected(self):
        """Test ACK wait when not connected"""
        bridge = ESP32Bridge()
        bridge.is_connected = False
        result = bridge._wait_for_ack("AUTH", timeout=0.1)
        assert result is None


class TestSendCommandWithACK:
    """Command sending with ACK tests"""

    @pytest.fixture
    def mock_bridge(self):
        """Mock ESP32Bridge"""
        bridge = ESP32Bridge()
        bridge.is_connected = True
        bridge.serial_connection = Mock()
        bridge.serial_connection.is_open = True
        bridge._send_command_bytes = Mock(return_value=True)
        bridge._wait_for_ack = Mock()
        return bridge

    def test_send_authorization_with_ack_success(self, mock_bridge):
        """Test authorization with ACK success"""
        mock_bridge.protocol_data = {
            "commands": {"authorization": {"byte_array": [65, 1, 44, 1, 16]}}
        }
        mock_bridge._wait_for_ack.return_value = {"CMD": "AUTH", "STATUS": "OK"}

        result = mock_bridge.send_authorization(wait_for_ack=True)
        assert result is True
        mock_bridge._wait_for_ack.assert_called_once_with("AUTH", timeout=1.0)

    def test_send_authorization_with_ack_cleared(self, mock_bridge):
        """Test authorization with ACK cleared status"""
        mock_bridge.protocol_data = {
            "commands": {"authorization": {"byte_array": [65, 1, 44, 1, 16]}}
        }
        mock_bridge._wait_for_ack.return_value = {"CMD": "AUTH", "STATUS": "CLEARED"}

        result = mock_bridge.send_authorization(wait_for_ack=True)
        assert result is True  # CLEARED is also considered success

    def test_send_authorization_with_ack_error(self, mock_bridge):
        """Test authorization with ACK error status"""
        mock_bridge.protocol_data = {
            "commands": {"authorization": {"byte_array": [65, 1, 44, 1, 16]}}
        }
        mock_bridge._wait_for_ack.return_value = {
            "CMD": "AUTH",
            "STATUS": "NOT CLEARED",
        }

        result = mock_bridge.send_authorization(wait_for_ack=True)
        assert result is False  # NOT CLEARED is not success

    def test_send_authorization_with_ack_timeout(self, mock_bridge):
        """Test authorization with ACK timeout"""
        mock_bridge.protocol_data = {
            "commands": {"authorization": {"byte_array": [65, 1, 44, 1, 16]}}
        }
        mock_bridge._wait_for_ack.return_value = None  # Timeout

        result = mock_bridge.send_authorization(wait_for_ack=True)
        assert result is False

    def test_send_authorization_without_ack(self, mock_bridge):
        """Test authorization without waiting for ACK"""
        mock_bridge.protocol_data = {
            "commands": {"authorization": {"byte_array": [65, 1, 44, 1, 16]}}
        }

        result = mock_bridge.send_authorization(wait_for_ack=False)
        assert result is True
        mock_bridge._wait_for_ack.assert_not_called()

    def test_send_current_set_with_ack_success(self, mock_bridge):
        """Test current set with ACK success"""
        mock_bridge._wait_for_ack.return_value = {"CMD": "SETMAXAMP", "STATUS": "OK"}

        result = mock_bridge.send_current_set(16, wait_for_ack=True)
        assert result is True
        mock_bridge._wait_for_ack.assert_called_once_with("SETMAXAMP", timeout=1.0)

    def test_send_current_set_with_ack_error(self, mock_bridge):
        """Test current set with ACK error"""
        mock_bridge._wait_for_ack.return_value = {"CMD": "SETMAXAMP", "STATUS": "ERR"}

        result = mock_bridge.send_current_set(16, wait_for_ack=True)
        assert result is False  # ERR is not success

    def test_send_current_set_without_ack(self, mock_bridge):
        """Test current set without waiting for ACK"""
        result = mock_bridge.send_current_set(16, wait_for_ack=False)
        assert result is True
        mock_bridge._wait_for_ack.assert_not_called()

    def test_send_charge_stop_without_ack(self, mock_bridge):
        """Test charge stop without ACK (default behavior)"""
        mock_bridge.protocol_data = {
            "commands": {"charge_stop": {"byte_array": [65, 4, 44, 7, 16]}}
        }

        result = mock_bridge.send_charge_stop()
        assert result is True
        # Charge stop için varsayılan olarak wait_for_ack=False
        mock_bridge._wait_for_ack.assert_not_called()
