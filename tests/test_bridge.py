"""
ESP32 Bridge Unit and Edge Case Tests
Created: 2025-12-10 18:15:00
Last Modified: 2025-12-10 18:15:00
Version: 1.0.0
Description: ESP32Bridge sınıfı için kapsamlı unit ve edge case testleri
"""

import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, mock_open

import serial

from esp32.bridge import (
    ESP32Bridge,
    BAUDRATE,
)


class TestESP32BridgeInit:
    """ESP32Bridge initialization tests"""

    @patch("esp32.bridge.ESP32Bridge._load_protocol")
    def test_init_default(self, mock_load_protocol):
        """Test default initialization"""
        mock_load_protocol.return_value = {}
        bridge = ESP32Bridge()
        assert bridge.port is None
        assert bridge.baudrate == BAUDRATE
        assert bridge.serial_connection is None
        assert bridge.is_connected is False
        assert bridge.last_status is None
        assert bridge._monitor_running is False
        assert bridge._reconnect_enabled is True

    @patch("esp32.bridge.ESP32Bridge._load_protocol")
    def test_init_custom_port(self, mock_load_protocol):
        """Test initialization with custom port"""
        mock_load_protocol.return_value = {}
        bridge = ESP32Bridge(port="/dev/ttyUSB0")
        assert bridge.port == "/dev/ttyUSB0"
        assert bridge.baudrate == BAUDRATE

    @patch("esp32.bridge.ESP32Bridge._load_protocol")
    def test_init_custom_baudrate(self, mock_load_protocol):
        """Test initialization with custom baudrate"""
        mock_load_protocol.return_value = {}
        bridge = ESP32Bridge(baudrate=9600)
        assert bridge.baudrate == 9600


class TestLoadProtocol:
    """Protocol loading tests"""

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"commands": {"test": "data"}}',
    )
    @patch("os.path.join")
    def test_load_protocol_success(self, mock_join, mock_file):
        """Test successful protocol loading"""
        mock_join.return_value = "/path/to/protocol.json"
        bridge = ESP32Bridge()
        assert bridge.protocol_data == {"commands": {"test": "data"}}

    @patch("builtins.open", side_effect=FileNotFoundError("File not found"))
    @patch("esp32.bridge.esp32_logger")
    def test_load_protocol_file_not_found(self, mock_logger, mock_file):
        """Test protocol loading when file not found"""
        bridge = ESP32Bridge()
        assert bridge.protocol_data == {}
        mock_logger.error.assert_called()

    @patch("builtins.open", side_effect=json.JSONDecodeError("Invalid JSON", "", 0))
    @patch("esp32.bridge.esp32_logger")
    def test_load_protocol_invalid_json(self, mock_logger, mock_file):
        """Test protocol loading with invalid JSON"""
        bridge = ESP32Bridge()
        assert bridge.protocol_data == {}
        mock_logger.error.assert_called()


class TestFindESP32Port:
    """Port finding tests"""

    @patch("esp32.bridge.serial.tools.list_ports.comports")
    def test_find_esp32_port_success(self, mock_comports):
        """Test successful port finding"""
        mock_port = Mock()
        mock_port.description = "USB Serial Port"
        mock_port.device = "/dev/ttyUSB0"
        mock_comports.return_value = [mock_port]

        bridge = ESP32Bridge()
        port = bridge.find_esp32_port()
        assert port == "/dev/ttyUSB0"

    @patch("esp32.bridge.serial.tools.list_ports.comports")
    def test_find_esp32_port_not_found(self, mock_comports):
        """Test port finding when no ESP32 port found"""
        mock_port = Mock()
        mock_port.description = "Other Device"
        mock_comports.return_value = [mock_port]

        bridge = ESP32Bridge()
        port = bridge.find_esp32_port()
        assert port is None

    @patch("esp32.bridge.serial.tools.list_ports.comports")
    def test_find_esp32_port_empty_list(self, mock_comports):
        """Test port finding when no ports available"""
        mock_comports.return_value = []
        bridge = ESP32Bridge()
        port = bridge.find_esp32_port()
        assert port is None


class TestConnect:
    """Connection tests"""

    @patch("esp32.bridge.ESP32Bridge.find_esp32_port")
    @patch("esp32.bridge.ESP32Bridge._start_monitoring")
    @patch("esp32.bridge.serial.Serial")
    @patch("esp32.bridge.time.sleep")
    @patch("esp32.bridge.esp32_logger")
    def test_connect_success(
        self, mock_logger, mock_sleep, mock_serial, mock_monitor, mock_find_port
    ):
        """Test successful connection"""
        mock_find_port.return_value = "/dev/ttyUSB0"
        mock_serial_instance = Mock()
        mock_serial_instance.is_open = True
        mock_serial.return_value = mock_serial_instance

        bridge = ESP32Bridge()
        result = bridge.connect()
        assert result is True
        assert bridge.is_connected is True
        mock_serial.assert_called_once()
        mock_monitor.assert_called_once()

    @patch("esp32.bridge.ESP32Bridge.find_esp32_port")
    @patch("esp32.bridge.esp32_logger")
    def test_connect_no_port(self, mock_logger, mock_find_port):
        """Test connection when no port found"""
        mock_find_port.return_value = None
        bridge = ESP32Bridge()
        result = bridge.connect()
        assert result is False
        assert bridge.is_connected is False

    @patch("esp32.bridge.ESP32Bridge.find_esp32_port")
    @patch(
        "esp32.bridge.serial.Serial",
        side_effect=serial.SerialException("Connection failed"),
    )
    @patch("esp32.bridge.esp32_logger")
    def test_connect_serial_exception(self, mock_logger, mock_serial, mock_find_port):
        """Test connection when serial exception occurs"""
        mock_find_port.return_value = "/dev/ttyUSB0"
        bridge = ESP32Bridge()
        result = bridge.connect()
        assert result is False
        assert bridge.is_connected is False

    @patch("esp32.bridge.ESP32Bridge.disconnect")
    @patch("esp32.bridge.ESP32Bridge.find_esp32_port")
    @patch("esp32.bridge.ESP32Bridge._start_monitoring")
    @patch("esp32.bridge.serial.Serial")
    @patch("esp32.bridge.time.sleep")
    def test_connect_already_connected(
        self, mock_sleep, mock_serial, mock_monitor, mock_find_port, mock_disconnect
    ):
        """Test connection when already connected"""
        mock_find_port.return_value = "/dev/ttyUSB0"
        mock_serial_instance = Mock()
        mock_serial_instance.is_open = True
        mock_serial.return_value = mock_serial_instance

        bridge = ESP32Bridge()
        bridge.serial_connection = Mock()
        bridge.serial_connection.is_open = True
        result = bridge.connect()
        assert result is True
        mock_disconnect.assert_called_once()


class TestDisconnect:
    """Disconnection tests"""

    @patch("esp32.bridge.ESP32Bridge._stop_monitoring")
    @patch("esp32.bridge.esp32_logger")
    def test_disconnect_success(self, mock_logger, mock_stop):
        """Test successful disconnection"""
        bridge = ESP32Bridge()
        bridge.serial_connection = Mock()
        bridge.serial_connection.is_open = True
        bridge.is_connected = True
        bridge.disconnect()
        assert bridge.is_connected is False
        assert bridge._reconnect_enabled is False
        mock_stop.assert_called_once()

    @patch("esp32.bridge.ESP32Bridge._stop_monitoring")
    @patch("esp32.bridge.esp32_logger")
    def test_disconnect_not_connected(self, mock_logger, mock_stop):
        """Test disconnection when not connected"""
        bridge = ESP32Bridge()
        bridge.is_connected = False
        bridge.disconnect()
        assert bridge.is_connected is False
        mock_stop.assert_called_once()

    @patch("esp32.bridge.ESP32Bridge._stop_monitoring")
    @patch("esp32.bridge.esp32_logger")
    def test_disconnect_close_exception(self, mock_logger, mock_stop):
        """Test disconnection when close raises exception"""
        bridge = ESP32Bridge()
        bridge.serial_connection = Mock()
        bridge.serial_connection.is_open = True
        bridge.serial_connection.close.side_effect = Exception("Close error")
        bridge.disconnect()
        assert bridge.is_connected is False


class TestReconnect:
    """Reconnection tests"""

    @patch("esp32.bridge.ESP32Bridge.connect")
    @patch("esp32.bridge.time.sleep")
    @patch("esp32.bridge.esp32_logger")
    def test_reconnect_success(self, mock_logger, mock_sleep, mock_connect):
        """Test successful reconnection"""
        mock_connect.return_value = True
        bridge = ESP32Bridge()
        bridge._reconnect_enabled = True
        result = bridge.reconnect()
        assert result is True
        assert bridge._reconnect_attempts == 0

    @patch("esp32.bridge.ESP32Bridge.connect")
    @patch("esp32.bridge.time.sleep")
    @patch("esp32.bridge.esp32_logger")
    def test_reconnect_disabled(self, mock_logger, mock_sleep, mock_connect):
        """Test reconnection when disabled"""
        bridge = ESP32Bridge()
        bridge._reconnect_enabled = False
        result = bridge.reconnect()
        assert result is False

    @patch("esp32.bridge.ESP32Bridge.connect")
    @patch("esp32.bridge.time.sleep")
    @patch("esp32.bridge.esp32_logger")
    def test_reconnect_max_retries(self, mock_logger, mock_sleep, mock_connect):
        """Test reconnection with max retries"""
        mock_connect.return_value = False
        bridge = ESP32Bridge()
        bridge._reconnect_enabled = True
        bridge._max_reconnect_attempts = 2
        result = bridge.reconnect()
        assert result is False
        assert bridge._reconnect_attempts == 1


class TestSendCommandBytes:
    """Command sending tests"""

    def test_send_command_bytes_success(self):
        """Test successful command sending"""
        bridge = ESP32Bridge()
        bridge.is_connected = True
        bridge.serial_connection = Mock()
        bridge.serial_connection.is_open = True
        bridge.serial_connection.write = Mock()
        bridge.serial_connection.flush = Mock()

        result = bridge._send_command_bytes([0x41, 0x01, 0x2C, 0x01, 0x10])
        assert result is True
        bridge.serial_connection.write.assert_called_once()
        bridge.serial_connection.flush.assert_called_once()

    def test_send_command_bytes_not_connected(self):
        """Test command sending when not connected"""
        bridge = ESP32Bridge()
        bridge.is_connected = False
        result = bridge._send_command_bytes([0x41, 0x01, 0x2C, 0x01, 0x10])
        assert result is False

    def test_send_command_bytes_invalid_length(self):
        """Test command sending with invalid length"""
        bridge = ESP32Bridge()
        bridge.is_connected = True
        bridge.serial_connection = Mock()
        bridge.serial_connection.is_open = True

        result = bridge._send_command_bytes([0x41, 0x01, 0x2C])
        assert result is False

    def test_send_command_bytes_write_exception(self):
        """Test command sending when write raises exception"""
        bridge = ESP32Bridge()
        bridge.is_connected = True
        bridge.serial_connection = Mock()
        bridge.serial_connection.is_open = True
        bridge.serial_connection.write.side_effect = Exception("Write error")

        result = bridge._send_command_bytes([0x41, 0x01, 0x2C, 0x01, 0x10])
        assert result is False


class TestSendStatusRequest:
    """Status request tests"""

    def test_send_status_request_success(self):
        """Test successful status request"""
        bridge = ESP32Bridge()
        bridge.protocol_data = {
            "commands": {"status": {"byte_array": [65, 0, 44, 0, 16]}}
        }
        bridge.is_connected = True
        bridge.serial_connection = Mock()
        bridge.serial_connection.is_open = True
        bridge.serial_connection.write = Mock()
        bridge.serial_connection.flush = Mock()
        bridge._send_command_bytes = Mock(return_value=True)

        result = bridge.send_status_request()
        assert result is True

    def test_send_status_request_fallback(self):
        """Test status request with fallback byte array"""
        bridge = ESP32Bridge()
        bridge.protocol_data = {"commands": {}}
        bridge.is_connected = True
        bridge.serial_connection = Mock()
        bridge.serial_connection.is_open = True
        bridge._send_command_bytes = Mock(return_value=True)

        result = bridge.send_status_request()
        assert result is True
        bridge._send_command_bytes.assert_called_with([65, 0, 44, 0, 16])


class TestSendAuthorization:
    """Authorization command tests"""

    def test_send_authorization_success(self):
        """Test successful authorization command"""
        bridge = ESP32Bridge()
        bridge.protocol_data = {
            "commands": {"authorization": {"byte_array": [65, 1, 44, 1, 16]}}
        }
        bridge.is_connected = True
        bridge.serial_connection = Mock()
        bridge.serial_connection.is_open = True
        bridge._send_command_bytes = Mock(return_value=True)
        bridge._wait_for_ack = Mock(return_value={"CMD": "AUTH", "STATUS": "OK"})

        result = bridge.send_authorization()
        assert result is True
        bridge._wait_for_ack.assert_called_once_with("AUTH", timeout=1.0)

    def test_send_authorization_fallback(self):
        """Test authorization with fallback byte array"""
        bridge = ESP32Bridge()
        bridge.protocol_data = {"commands": {}}
        bridge.is_connected = True
        bridge.serial_connection = Mock()
        bridge.serial_connection.is_open = True
        bridge._send_command_bytes = Mock(return_value=True)
        bridge._wait_for_ack = Mock(return_value={"CMD": "AUTH", "STATUS": "OK"})

        result = bridge.send_authorization()
        assert result is True
        bridge._send_command_bytes.assert_called_with([65, 1, 44, 1, 16])
        bridge._wait_for_ack.assert_called_once_with("AUTH", timeout=1.0)


class TestSendCurrentSet:
    """Current set command tests"""

    def test_send_current_set_success(self):
        """Test successful current set command"""
        bridge = ESP32Bridge()
        bridge.is_connected = True
        bridge.serial_connection = Mock()
        bridge.serial_connection.is_open = True
        bridge._send_command_bytes = Mock(return_value=True)
        bridge._wait_for_ack = Mock(return_value={"CMD": "SETMAXAMP", "STATUS": "OK"})

        result = bridge.send_current_set(16)
        assert result is True
        bridge._send_command_bytes.assert_called_with([0x41, 0x02, 0x2C, 16, 0x10])
        bridge._wait_for_ack.assert_called_once_with("SETMAXAMP", timeout=1.0)

    def test_send_current_set_minimum(self):
        """Test current set with minimum value (6A)"""
        bridge = ESP32Bridge()
        bridge.is_connected = True
        bridge.serial_connection = Mock()
        bridge.serial_connection.is_open = True
        bridge._send_command_bytes = Mock(return_value=True)
        bridge._wait_for_ack = Mock(return_value={"CMD": "SETMAXAMP", "STATUS": "OK"})

        result = bridge.send_current_set(6)
        assert result is True
        bridge._send_command_bytes.assert_called_with([0x41, 0x02, 0x2C, 6, 0x10])
        bridge._wait_for_ack.assert_called_once_with("SETMAXAMP", timeout=1.0)

    def test_send_current_set_maximum(self):
        """Test current set with maximum value (32A)"""
        bridge = ESP32Bridge()
        bridge.is_connected = True
        bridge.serial_connection = Mock()
        bridge.serial_connection.is_open = True
        bridge._send_command_bytes = Mock(return_value=True)
        bridge._wait_for_ack = Mock(return_value={"CMD": "SETMAXAMP", "STATUS": "OK"})

        result = bridge.send_current_set(32)
        assert result is True
        bridge._send_command_bytes.assert_called_with([0x41, 0x02, 0x2C, 32, 0x10])
        bridge._wait_for_ack.assert_called_once_with("SETMAXAMP", timeout=1.0)

    def test_send_current_set_below_minimum(self):
        """Test current set with value below minimum (5A)"""
        bridge = ESP32Bridge()
        bridge.is_connected = True
        result = bridge.send_current_set(5)
        assert result is False

    def test_send_current_set_above_maximum(self):
        """Test current set with value above maximum (33A)"""
        bridge = ESP32Bridge()
        bridge.is_connected = True
        result = bridge.send_current_set(33)
        assert result is False

    def test_send_current_set_zero(self):
        """Test current set with zero value"""
        bridge = ESP32Bridge()
        bridge.is_connected = True
        result = bridge.send_current_set(0)
        assert result is False

    def test_send_current_set_negative(self):
        """Test current set with negative value"""
        bridge = ESP32Bridge()
        bridge.is_connected = True
        result = bridge.send_current_set(-1)
        assert result is False


class TestSendChargeStop:
    """Charge stop command tests"""

    def test_send_charge_stop_success(self):
        """Test successful charge stop command"""
        bridge = ESP32Bridge()
        bridge.protocol_data = {
            "commands": {"charge_stop": {"byte_array": [65, 4, 44, 7, 16]}}
        }
        bridge.is_connected = True
        bridge.serial_connection = Mock()
        bridge.serial_connection.is_open = True
        bridge._send_command_bytes = Mock(return_value=True)
        # Charge stop için wait_for_ack varsayılan olarak False
        # Bu yüzden _wait_for_ack çağrılmamalı

        result = bridge.send_charge_stop()
        assert result is True

    def test_send_charge_stop_fallback(self):
        """Test charge stop with fallback byte array"""
        bridge = ESP32Bridge()
        bridge.protocol_data = {"commands": {}}
        bridge.is_connected = True
        bridge.serial_connection = Mock()
        bridge.serial_connection.is_open = True
        bridge._send_command_bytes = Mock(return_value=True)
        # Charge stop için wait_for_ack varsayılan olarak False

        result = bridge.send_charge_stop()
        assert result is True
        bridge._send_command_bytes.assert_called_with([65, 4, 44, 7, 16])


class TestParseStatusMessage:
    """Status message parsing tests"""

    def test_parse_status_message_success(self):
        """Test successful status message parsing"""
        bridge = ESP32Bridge()
        message = "<STAT;ID=1;CP=2;CPV=1847;PP=1;PPV=1566;RL=1;LOCK=1;MOTOR=0;PWM=84;MAX=23;CABLE=20;AUTH=1;STATE=5;PB=0;STOP=0;>"
        result = bridge._parse_status_message(message)
        assert result is not None
        assert result["ID"] == 1
        assert result["CP"] == 2
        assert result["CPV"] == 1847
        assert result["STATE"] == 5
        assert result["STATE_NAME"] == "CHARGING"
        assert "timestamp" in result

    def test_parse_status_message_minimal(self):
        """Test parsing minimal status message"""
        bridge = ESP32Bridge()
        message = "<STAT;STATE=1;>"
        result = bridge._parse_status_message(message)
        assert result is not None
        assert result["STATE"] == 1
        assert result["STATE_NAME"] == "IDLE"

    def test_parse_status_message_invalid_format(self):
        """Test parsing invalid format message"""
        bridge = ESP32Bridge()
        message = "INVALID MESSAGE"
        result = bridge._parse_status_message(message)
        assert result is None

    def test_parse_status_message_empty(self):
        """Test parsing empty message"""
        bridge = ESP32Bridge()
        message = ""
        result = bridge._parse_status_message(message)
        assert result is None

    def test_parse_status_message_missing_closing(self):
        """Test parsing message with missing closing bracket"""
        bridge = ESP32Bridge()
        message = "<STAT;STATE=1;"
        result = bridge._parse_status_message(message)
        assert result is None

    def test_parse_status_message_all_states(self):
        """Test parsing all possible states"""
        bridge = ESP32Bridge()
        states = {
            0: "HARDFAULT_END",
            1: "IDLE",
            2: "CABLE_DETECT",
            3: "EV_CONNECTED",
            4: "READY",
            5: "CHARGING",
            6: "PAUSED",
            7: "STOPPED",
            8: "FAULT_HARD",
        }
        for state_value, expected_name in states.items():
            message = f"<STAT;STATE={state_value};>"
            result = bridge._parse_status_message(message)
            assert result is not None
            assert result["STATE"] == state_value
            assert result["STATE_NAME"] == expected_name

    def test_parse_status_message_unknown_state(self):
        """Test parsing message with unknown state"""
        bridge = ESP32Bridge()
        message = "<STAT;STATE=99;>"
        result = bridge._parse_status_message(message)
        assert result is not None
        assert result["STATE"] == 99
        assert result["STATE_NAME"] == "UNKNOWN_99"

    def test_parse_status_message_float_values(self):
        """Test parsing message with float values"""
        bridge = ESP32Bridge()
        message = "<STAT;CPV=1847.5;PPV=1566.2;STATE=1;>"
        result = bridge._parse_status_message(message)
        assert result is not None
        assert result["CPV"] == 1847.5
        assert result["PPV"] == 1566.2

    def test_parse_status_message_string_values(self):
        """Test parsing message with string values"""
        bridge = ESP32Bridge()
        message = "<STAT;ID=test;STATE=1;>"
        result = bridge._parse_status_message(message)
        assert result is not None
        assert result["ID"] == "test"

    def test_parse_status_message_whitespace(self):
        """Test parsing message with whitespace"""
        bridge = ESP32Bridge()
        message = "<STAT; ID = 1 ; CP = 2 ; STATE = 5 ; >"
        result = bridge._parse_status_message(message)
        assert result is not None
        assert result["ID"] == 1
        assert result["CP"] == 2
        assert result["STATE"] == 5

    def test_parse_status_message_empty_fields(self):
        """Test parsing message with empty fields"""
        bridge = ESP32Bridge()
        message = "<STAT;;STATE=1;;>"
        result = bridge._parse_status_message(message)
        assert result is not None
        assert result["STATE"] == 1


class TestGetStatus:
    """Status retrieval tests"""

    def test_get_status_success(self):
        """Test successful status retrieval"""
        bridge = ESP32Bridge()
        test_status = {"STATE": 5, "CP": 2, "timestamp": datetime.now().isoformat()}
        bridge.last_status = test_status
        result = bridge.get_status()
        assert result is not None
        assert result["STATE"] == 5

    def test_get_status_none(self):
        """Test status retrieval when no status available"""
        bridge = ESP32Bridge()
        bridge.last_status = None
        result = bridge.get_status()
        assert result is None

    def test_get_status_too_old(self):
        """Test status retrieval when status is too old"""
        bridge = ESP32Bridge()
        old_timestamp = (datetime.now() - timedelta(seconds=20)).isoformat()
        bridge.last_status = {"STATE": 5, "timestamp": old_timestamp}
        result = bridge.get_status(max_age_seconds=10.0)
        assert result is None

    def test_get_status_fresh(self):
        """Test status retrieval when status is fresh"""
        bridge = ESP32Bridge()
        fresh_timestamp = datetime.now().isoformat()
        bridge.last_status = {"STATE": 5, "timestamp": fresh_timestamp}
        result = bridge.get_status(max_age_seconds=10.0)
        assert result is not None

    def test_get_status_invalid_timestamp(self):
        """Test status retrieval with invalid timestamp"""
        bridge = ESP32Bridge()
        bridge.last_status = {"STATE": 5, "timestamp": "invalid-timestamp"}
        # Should return status even with invalid timestamp (with warning)
        result = bridge.get_status()
        assert result is not None


class TestGetStatusSync:
    """Synchronous status retrieval tests"""

    @patch("esp32.bridge.ESP32Bridge.send_status_request")
    @patch("esp32.bridge.ESP32Bridge.get_status")
    @patch("esp32.bridge.time.sleep")
    def test_get_status_sync_success(
        self, mock_sleep, mock_get_status, mock_send_request
    ):
        """Test successful synchronous status retrieval"""
        mock_send_request.return_value = True
        mock_get_status.return_value = {"STATE": 5}
        bridge = ESP32Bridge()
        result = bridge.get_status_sync()
        assert result is not None
        assert result["STATE"] == 5

    @patch("esp32.bridge.ESP32Bridge.send_status_request")
    @patch("esp32.bridge.ESP32Bridge.get_status")
    @patch("esp32.bridge.time.sleep")
    def test_get_status_sync_timeout(
        self, mock_sleep, mock_get_status, mock_send_request
    ):
        """Test synchronous status retrieval with timeout"""
        mock_send_request.return_value = True
        mock_get_status.return_value = None
        bridge = ESP32Bridge()
        result = bridge.get_status_sync(timeout=0.1)
        assert result is None

    @patch("esp32.bridge.ESP32Bridge.send_status_request")
    def test_get_status_sync_request_failed(self, mock_send_request):
        """Test synchronous status retrieval when request fails"""
        mock_send_request.return_value = False
        bridge = ESP32Bridge()
        result = bridge.get_status_sync()
        assert result is None
