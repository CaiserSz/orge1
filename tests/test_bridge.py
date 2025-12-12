"""
ESP32 Bridge Unit and Edge Case Tests
Created: 2025-12-10 18:15:00
Last Modified: 2025-12-12 03:35:00
Version: 1.0.1
Description: ESP32Bridge sınıfı için kapsamlı unit ve edge case testleri
"""

import json
from datetime import datetime, timedelta
from unittest.mock import Mock, mock_open, patch

import serial

from esp32.bridge import BAUDRATE, ESP32Bridge


def _connected_bridge() -> ESP32Bridge:
    bridge = ESP32Bridge()
    bridge.is_connected = True
    bridge.serial_connection = Mock()
    bridge.serial_connection.is_open = True
    bridge.serial_connection.write = Mock()
    bridge.serial_connection.flush = Mock()
    return bridge


class TestESP32BridgeInit:
    @patch("esp32.bridge.ESP32Bridge._load_protocol")
    def test_init_default(self, mock_load_protocol):
        mock_load_protocol.return_value = {}
        bridge = ESP32Bridge()
        assert bridge.port is None
        assert bridge.baudrate == BAUDRATE
        assert bridge.serial_connection is None
        assert bridge.is_connected is False
        assert bridge.last_status is None

    @patch("esp32.bridge.ESP32Bridge._load_protocol")
    def test_init_custom_port_baudrate(self, mock_load_protocol):
        mock_load_protocol.return_value = {}
        bridge = ESP32Bridge(port="/dev/ttyUSB0", baudrate=9600)
        assert bridge.port == "/dev/ttyUSB0"
        assert bridge.baudrate == 9600


class TestLoadProtocol:
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"commands": {"test": "data"}}',
    )
    @patch("os.path.join")
    def test_load_protocol_success(self, mock_join, mock_file):
        mock_join.return_value = "/path/to/protocol.json"
        bridge = ESP32Bridge()
        assert bridge.protocol_data == {"commands": {"test": "data"}}

    @patch("builtins.open", side_effect=FileNotFoundError("File not found"))
    @patch("esp32.bridge.esp32_logger")
    def test_load_protocol_file_not_found(self, mock_logger, mock_file):
        bridge = ESP32Bridge()
        assert bridge.protocol_data == {}
        mock_logger.error.assert_called()

    @patch("builtins.open", side_effect=json.JSONDecodeError("Invalid JSON", "", 0))
    @patch("esp32.bridge.esp32_logger")
    def test_load_protocol_invalid_json(self, mock_logger, mock_file):
        bridge = ESP32Bridge()
        assert bridge.protocol_data == {}
        mock_logger.error.assert_called()


class TestFindESP32Port:
    @patch("esp32.bridge.serial.tools.list_ports.comports")
    def test_find_esp32_port_success(self, mock_comports):
        mock_port = Mock()
        mock_port.description = "USB Serial Port"
        mock_port.device = "/dev/ttyUSB0"
        mock_comports.return_value = [mock_port]
        assert ESP32Bridge().find_esp32_port() == "/dev/ttyUSB0"

    @patch("esp32.bridge.serial.tools.list_ports.comports")
    def test_find_esp32_port_not_found_or_empty(self, mock_comports):
        bridge = ESP32Bridge()
        mock_port = Mock()
        mock_port.description = "Other Device"

        mock_comports.return_value = [mock_port]
        assert bridge.find_esp32_port() is None

        mock_comports.return_value = []
        assert bridge.find_esp32_port() is None


class TestConnectDisconnectReconnect:
    @patch("esp32.bridge.ESP32Bridge.find_esp32_port")
    @patch("esp32.bridge.ESP32Bridge._start_monitoring")
    @patch("esp32.bridge.serial.Serial")
    @patch("esp32.bridge.time.sleep")
    def test_connect_success(self, mock_sleep, mock_serial, mock_monitor, mock_find_port):
        mock_find_port.return_value = "/dev/ttyUSB0"
        serial_instance = Mock()
        serial_instance.is_open = True
        mock_serial.return_value = serial_instance

        bridge = ESP32Bridge()
        assert bridge.connect() is True
        assert bridge.is_connected is True
        mock_serial.assert_called_once()
        mock_monitor.assert_called_once()

    @patch("esp32.bridge.ESP32Bridge.find_esp32_port")
    def test_connect_no_port(self, mock_find_port):
        mock_find_port.return_value = None
        bridge = ESP32Bridge()
        assert bridge.connect() is False
        assert bridge.is_connected is False

    @patch("esp32.bridge.ESP32Bridge.find_esp32_port")
    @patch(
        "esp32.bridge.serial.Serial",
        side_effect=serial.SerialException("Connection failed"),
    )
    def test_connect_serial_exception(self, mock_serial, mock_find_port):
        mock_find_port.return_value = "/dev/ttyUSB0"
        bridge = ESP32Bridge()
        assert bridge.connect() is False
        assert bridge.is_connected is False

    @patch("esp32.bridge.ESP32Bridge.disconnect")
    @patch("esp32.bridge.ESP32Bridge.find_esp32_port")
    @patch("esp32.bridge.ESP32Bridge._start_monitoring")
    @patch("esp32.bridge.serial.Serial")
    @patch("esp32.bridge.time.sleep")
    def test_connect_already_connected(
        self, mock_sleep, mock_serial, mock_monitor, mock_find_port, mock_disconnect
    ):
        mock_find_port.return_value = "/dev/ttyUSB0"
        serial_instance = Mock()
        serial_instance.is_open = True
        mock_serial.return_value = serial_instance

        bridge = ESP32Bridge()
        bridge.serial_connection = Mock()
        bridge.serial_connection.is_open = True
        assert bridge.connect() is True
        mock_disconnect.assert_called_once()

    @patch("esp32.bridge.ESP32Bridge._stop_monitoring")
    def test_disconnect_success(self, mock_stop):
        bridge = ESP32Bridge()
        bridge.serial_connection = Mock()
        bridge.serial_connection.is_open = True
        bridge.is_connected = True
        bridge.disconnect()
        assert bridge.is_connected is False
        assert bridge._reconnect_enabled is False
        mock_stop.assert_called_once()

    @patch("esp32.bridge.ESP32Bridge.connect")
    @patch("esp32.bridge.time.sleep")
    def test_reconnect_success_and_disabled(self, mock_sleep, mock_connect):
        bridge = ESP32Bridge()

        bridge._reconnect_enabled = True
        mock_connect.return_value = True
        assert bridge.reconnect() is True

        bridge._reconnect_enabled = False
        assert bridge.reconnect() is False


class TestSendCommandBytes:
    def test_send_command_bytes_success(self):
        bridge = _connected_bridge()
        assert bridge._send_command_bytes([0x41, 0x01, 0x2C, 0x01, 0x10]) is True
        bridge.serial_connection.write.assert_called_once()
        bridge.serial_connection.flush.assert_called_once()

    def test_send_command_bytes_failures(self):
        bridge = ESP32Bridge()
        bridge.is_connected = False
        assert bridge._send_command_bytes([0x41, 0x01, 0x2C, 0x01, 0x10]) is False

        bridge = _connected_bridge()
        assert bridge._send_command_bytes([0x41, 0x01, 0x2C]) is False

        bridge = _connected_bridge()
        bridge.serial_connection.write.side_effect = Exception("Write error")
        assert bridge._send_command_bytes([0x41, 0x01, 0x2C, 0x01, 0x10]) is False


class TestHighLevelCommands:
    def test_send_status_request(self):
        bridge = _connected_bridge()
        bridge.protocol_data = {"commands": {"status": {"byte_array": [65, 0, 44, 0, 16]}}}
        bridge._send_command_bytes = Mock(return_value=True)
        assert bridge.send_status_request() is True

        bridge.protocol_data = {"commands": {}}
        assert bridge.send_status_request() is True
        bridge._send_command_bytes.assert_called_with([65, 0, 44, 0, 16])

    def test_send_authorization_and_charge_stop(self):
        bridge = _connected_bridge()
        bridge.protocol_data = {
            "commands": {
                "authorization": {"byte_array": [65, 1, 44, 1, 16]},
                "charge_stop": {"byte_array": [65, 4, 44, 7, 16]},
            }
        }
        bridge._send_command_bytes = Mock(return_value=True)
        bridge._wait_for_ack = Mock(return_value={"CMD": "AUTH", "STATUS": "OK"})

        assert bridge.send_authorization() is True
        bridge._wait_for_ack.assert_called_once_with("AUTH", timeout=1.0)

        # charge_stop default: wait_for_ack=False
        assert bridge.send_charge_stop() is True


class TestSendCurrentSet:
    def test_send_current_set_various_values(self):
        bridge = _connected_bridge()
        bridge._send_command_bytes = Mock(return_value=True)
        bridge._wait_for_ack = Mock(return_value={"CMD": "SETMAXAMP", "STATUS": "OK"})

        for amperage in [6, 16, 32]:
            assert bridge.send_current_set(amperage) is True

        for invalid in [5, 33, 0, -1]:
            assert bridge.send_current_set(invalid) is False


class TestParseStatusMessage:
    def test_parse_status_message_success_and_minimal(self):
        bridge = ESP32Bridge()
        msg = "<STAT;ID=1;CP=2;CPV=1847;PP=1;PPV=1566;RL=1;LOCK=1;MOTOR=0;PWM=84;MAX=23;CABLE=20;AUTH=1;STATE=5;PB=0;STOP=0;>"
        result = bridge._parse_status_message(msg)
        assert result is not None
        assert result["ID"] == 1
        assert result["STATE"] == 5
        assert result["STATE_NAME"] == "CHARGING"
        assert "timestamp" in result

        minimal = bridge._parse_status_message("<STAT;STATE=1;>")
        assert minimal is not None
        assert minimal["STATE"] == 1
        assert minimal["STATE_NAME"] == "IDLE"

    def test_parse_status_message_invalid_inputs(self):
        bridge = ESP32Bridge()
        for message in ["INVALID MESSAGE", "", "<STAT;STATE=1;", "<STAT;;STATE=1;;>"]:
            result = bridge._parse_status_message(message)
            if message in ["INVALID MESSAGE", "", "<STAT;STATE=1;"]:
                assert result is None
            else:
                assert result is not None

    def test_parse_status_message_all_states_and_unknown(self):
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
            result = bridge._parse_status_message(f"<STAT;STATE={state_value};>")
            assert result is not None
            assert result["STATE"] == state_value
            assert result["STATE_NAME"] == expected_name

        unknown = bridge._parse_status_message("<STAT;STATE=99;>")
        assert unknown is not None
        assert unknown["STATE_NAME"] == "UNKNOWN_99"

    def test_parse_status_message_value_types(self):
        bridge = ESP32Bridge()
        result = bridge._parse_status_message("<STAT;CPV=1847.5;PPV=1566.2;STATE=1;>")
        assert result is not None
        assert result["CPV"] == 1847.5
        assert result["PPV"] == 1566.2

        result = bridge._parse_status_message("<STAT;ID=test;STATE=1;>")
        assert result is not None
        assert result["ID"] == "test"

        result = bridge._parse_status_message("<STAT; ID = 1 ; CP = 2 ; STATE = 5 ; >")
        assert result is not None
        assert result["ID"] == 1
        assert result["CP"] == 2
        assert result["STATE"] == 5


class TestGetStatus:
    def test_get_status_variants(self):
        bridge = ESP32Bridge()
        bridge.last_status = None
        assert bridge.get_status() is None

        bridge.last_status = {"STATE": 5, "CP": 2, "timestamp": datetime.now().isoformat()}
        assert bridge.get_status()["STATE"] == 5

        old_ts = (datetime.now() - timedelta(seconds=20)).isoformat()
        bridge.last_status = {"STATE": 5, "timestamp": old_ts}
        assert bridge.get_status(max_age_seconds=10.0) is None

        bridge.last_status = {"STATE": 5, "timestamp": "invalid-timestamp"}
        assert bridge.get_status() is not None


class TestGetStatusSync:
    @patch("esp32.bridge.ESP32Bridge.send_status_request")
    @patch("esp32.bridge.ESP32Bridge.get_status")
    @patch("esp32.bridge.time.sleep")
    def test_get_status_sync_success(self, mock_sleep, mock_get_status, mock_send_request):
        mock_send_request.return_value = True
        mock_get_status.return_value = {"STATE": 5}
        bridge = ESP32Bridge()
        bridge.is_connected = True
        bridge.serial_connection = Mock()
        bridge.serial_connection.is_open = True
        result = bridge.get_status_sync()
        assert result is not None
        assert result["STATE"] == 5

    @patch("esp32.bridge.ESP32Bridge.send_status_request")
    @patch("esp32.bridge.ESP32Bridge.get_status")
    @patch("esp32.bridge.time.sleep")
    def test_get_status_sync_timeout(self, mock_sleep, mock_get_status, mock_send_request):
        mock_send_request.return_value = True
        mock_get_status.return_value = None
        bridge = ESP32Bridge()
        bridge.is_connected = True
        bridge.serial_connection = Mock()
        bridge.serial_connection.is_open = True
        assert bridge.get_status_sync(timeout=0.1) is None

    @patch("esp32.bridge.ESP32Bridge.send_status_request")
    def test_get_status_sync_request_failed(self, mock_send_request):
        mock_send_request.return_value = False
        bridge = ESP32Bridge()
        bridge.is_connected = True
        bridge.serial_connection = Mock()
        bridge.serial_connection.is_open = True
        assert bridge.get_status_sync() is None
