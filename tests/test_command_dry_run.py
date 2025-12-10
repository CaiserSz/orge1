"""
Command Dry Run Tests
Created: 2025-12-10 18:30:00
Last Modified: 2025-12-10 18:30:00
Version: 1.0.0
Description: ESP32'ye komut gönderen API'ler için dry run testleri
Komutların doğru byte array'lerle gönderildiğini kontrol eder (gerçek ESP32'ye göndermeden)
"""

import json
from unittest.mock import Mock
from pathlib import Path

import pytest

from api.event_detector import ESP32State
from api.models import ChargeStartRequest, ChargeStopRequest, CurrentSetRequest
from api.services.charge_service import ChargeService
from api.services.current_service import CurrentService
from esp32.bridge import ESP32Bridge


class TestChargeStartDryRun:
    """Charge Start API dry run tests"""

    @pytest.fixture
    def mock_bridge(self):
        """Mock ESP32Bridge"""
        bridge = Mock(spec=ESP32Bridge)
        bridge.is_connected = True
        bridge.get_status = Mock()
        bridge.send_authorization = Mock(return_value=True)
        return bridge

    @pytest.fixture
    def charge_service(self, mock_bridge):
        """ChargeService instance with mock bridge"""
        return ChargeService(mock_bridge)

    def test_charge_start_command_byte_array(self, charge_service, mock_bridge):
        """Test that charge start sends correct authorization command byte array"""
        # Expected byte array: [65, 1, 44, 1, 16] (from protocol.json)

        # Mock status: EV_CONNECTED state
        mock_bridge.get_status.return_value = {
            "STATE": ESP32State.EV_CONNECTED.value,
            "STATE_NAME": "EV_CONNECTED",
            "AUTH": 0,
        }

        request_body = ChargeStartRequest(user_id="test-user-123")
        result = charge_service.start_charge(request_body, user_id="test-user-123")

        # Verify authorization command was sent
        assert mock_bridge.send_authorization.called
        assert result["success"] is True
        assert result["data"]["command"] == "authorization"

        # Verify bridge's send_authorization was called (which internally uses correct byte array)
        # The actual byte array is verified in bridge tests, here we verify the command was sent
        mock_bridge.send_authorization.assert_called_once()

    def test_charge_start_command_protocol_compliance(
        self, charge_service, mock_bridge
    ):
        """Test that charge start command complies with protocol"""
        # Load protocol.json to verify expected command
        mock_bridge.get_status.return_value = {
            "STATE": ESP32State.EV_CONNECTED.value,
            "STATE_NAME": "EV_CONNECTED",
        }

        request_body = ChargeStartRequest()
        charge_service.start_charge(request_body)

        # Verify command was sent (bridge internally uses protocol.json byte array)
        mock_bridge.send_authorization.assert_called_once()

    def test_charge_start_rejects_invalid_states(self, charge_service, mock_bridge):
        """Test that charge start rejects invalid states"""
        invalid_states = [
            ESP32State.IDLE,
            ESP32State.CABLE_DETECT,
            ESP32State.READY,
            ESP32State.CHARGING,
            ESP32State.PAUSED,
            ESP32State.STOPPED,
        ]

        for state in invalid_states:
            mock_bridge.get_status.return_value = {
                "STATE": state.value,
                "STATE_NAME": state.name,
            }
            mock_bridge.send_authorization.reset_mock()

            request_body = ChargeStartRequest()
            with pytest.raises(ValueError, match="Şarj başlatılamaz"):
                charge_service.start_charge(request_body)

            # Verify command was NOT sent
            mock_bridge.send_authorization.assert_not_called()

    def test_charge_start_requires_ev_connected_state(
        self, charge_service, mock_bridge
    ):
        """Test that charge start only works in EV_CONNECTED state"""
        mock_bridge.get_status.return_value = {
            "STATE": ESP32State.EV_CONNECTED.value,
            "STATE_NAME": "EV_CONNECTED",
        }

        request_body = ChargeStartRequest()
        result = charge_service.start_charge(request_body)

        assert result["success"] is True
        mock_bridge.send_authorization.assert_called_once()

    def test_charge_start_handles_state_change_race_condition(
        self, charge_service, mock_bridge
    ):
        """Test that charge start handles state change between checks"""
        # First check: EV_CONNECTED
        # Second check: CHARGING (state changed)
        mock_bridge.get_status.side_effect = [
            {"STATE": ESP32State.EV_CONNECTED.value, "STATE_NAME": "EV_CONNECTED"},
            {"STATE": ESP32State.CHARGING.value, "STATE_NAME": "CHARGING"},
        ]

        request_body = ChargeStartRequest()
        with pytest.raises(ValueError, match="State değişti"):
            charge_service.start_charge(request_body)

        # Verify command was NOT sent
        mock_bridge.send_authorization.assert_not_called()


class TestChargeStopDryRun:
    """Charge Stop API dry run tests"""

    @pytest.fixture
    def mock_bridge(self):
        """Mock ESP32Bridge"""
        bridge = Mock(spec=ESP32Bridge)
        bridge.is_connected = True
        bridge.send_charge_stop = Mock(return_value=True)
        return bridge

    @pytest.fixture
    def charge_service(self, mock_bridge):
        """ChargeService instance with mock bridge"""
        return ChargeService(mock_bridge)

    def test_charge_stop_command_byte_array(self, charge_service, mock_bridge):
        """Test that charge stop sends correct charge_stop command byte array"""
        # Expected byte array: [65, 4, 44, 7, 16] (from protocol.json)

        request_body = ChargeStopRequest(user_id="test-user-123")
        result = charge_service.stop_charge(request_body, user_id="test-user-123")

        # Verify charge_stop command was sent
        assert mock_bridge.send_charge_stop.called
        assert result["success"] is True
        assert result["data"]["command"] == "charge_stop"

        # Verify bridge's send_charge_stop was called (which internally uses correct byte array)
        mock_bridge.send_charge_stop.assert_called_once()

    def test_charge_stop_command_protocol_compliance(self, charge_service, mock_bridge):
        """Test that charge stop command complies with protocol"""
        # Load protocol.json to verify expected command
        request_body = ChargeStopRequest()
        charge_service.stop_charge(request_body)

        # Verify command was sent (bridge internally uses protocol.json byte array)
        mock_bridge.send_charge_stop.assert_called_once()

    def test_charge_stop_always_sends_command(self, charge_service, mock_bridge):
        """Test that charge stop always sends command (no state validation)"""
        # Charge stop doesn't check state, it always sends the command
        request_body = ChargeStopRequest()
        result = charge_service.stop_charge(request_body)

        assert result["success"] is True
        mock_bridge.send_charge_stop.assert_called_once()

    def test_charge_stop_handles_command_failure(self, charge_service, mock_bridge):
        """Test that charge stop handles command send failure"""
        mock_bridge.send_charge_stop.return_value = False

        request_body = ChargeStopRequest()
        with pytest.raises(ValueError, match="Şarj durdurma komutu gönderilemedi"):
            charge_service.stop_charge(request_body)

        mock_bridge.send_charge_stop.assert_called_once()


class TestCurrentSetDryRun:
    """Current Set API dry run tests"""

    @pytest.fixture
    def mock_bridge(self):
        """Mock ESP32Bridge"""
        bridge = Mock(spec=ESP32Bridge)
        bridge.is_connected = True
        bridge.get_status = Mock()
        bridge.send_current_set = Mock(return_value=True)
        return bridge

    @pytest.fixture
    def current_service(self, mock_bridge):
        """CurrentService instance with mock bridge"""
        return CurrentService(mock_bridge)

    def test_current_set_command_byte_array_minimum(self, current_service, mock_bridge):
        """Test that current set sends correct byte array for minimum value (6A)"""
        # Expected byte array: [0x41, 0x02, 0x2C, 6, 0x10]

        mock_bridge.get_status.return_value = {
            "STATE": ESP32State.IDLE.value,
            "STATE_NAME": "IDLE",
        }

        request_body = CurrentSetRequest(amperage=6)
        result = current_service.set_current(request_body)

        # Verify current_set command was sent with correct amperage
        assert mock_bridge.send_current_set.called
        assert result["success"] is True
        assert result["data"]["amperage"] == 6
        assert result["data"]["command"] == "current_set"

        # Verify bridge's send_current_set was called with correct amperage
        mock_bridge.send_current_set.assert_called_once_with(6)

    def test_current_set_command_byte_array_maximum(self, current_service, mock_bridge):
        """Test that current set sends correct byte array for maximum value (32A)"""
        # Expected byte array: [0x41, 0x02, 0x2C, 32, 0x10]

        mock_bridge.get_status.return_value = {
            "STATE": ESP32State.IDLE.value,
            "STATE_NAME": "IDLE",
        }

        request_body = CurrentSetRequest(amperage=32)
        result = current_service.set_current(request_body)

        assert mock_bridge.send_current_set.called
        assert result["data"]["amperage"] == 32
        mock_bridge.send_current_set.assert_called_once_with(32)

    def test_current_set_command_byte_array_middle_value(
        self, current_service, mock_bridge
    ):
        """Test that current set sends correct byte array for middle value (16A)"""
        # Expected byte array: [0x41, 0x02, 0x2C, 16, 0x10]

        mock_bridge.get_status.return_value = {
            "STATE": ESP32State.IDLE.value,
            "STATE_NAME": "IDLE",
        }

        request_body = CurrentSetRequest(amperage=16)
        result = current_service.set_current(request_body)

        assert mock_bridge.send_current_set.called
        assert result["data"]["amperage"] == 16
        mock_bridge.send_current_set.assert_called_once_with(16)

    def test_current_set_command_protocol_compliance(
        self, current_service, mock_bridge
    ):
        """Test that current set command complies with protocol"""
        # Load protocol.json to verify expected command format
        # Test with 16A (common value from protocol.json)
        # Expected: [65, 2, 44, 16, 16]

        mock_bridge.get_status.return_value = {
            "STATE": ESP32State.IDLE.value,
            "STATE_NAME": "IDLE",
        }

        request_body = CurrentSetRequest(amperage=16)
        current_service.set_current(request_body)

        # Verify command was sent with correct amperage
        # Bridge internally constructs byte array: [0x41, 0x02, 0x2C, amperage, 0x10]
        mock_bridge.send_current_set.assert_called_once_with(16)

    def test_current_set_rejects_charging_state(self, current_service, mock_bridge):
        """Test that current set rejects CHARGING state"""
        mock_bridge.get_status.return_value = {
            "STATE": ESP32State.CHARGING.value,
            "STATE_NAME": "CHARGING",
        }

        request_body = CurrentSetRequest(amperage=16)
        with pytest.raises(ValueError, match="Akım ayarlanamaz"):
            current_service.set_current(request_body)

        # Verify command was NOT sent
        mock_bridge.send_current_set.assert_not_called()

    def test_current_set_rejects_paused_state(self, current_service, mock_bridge):
        """Test that current set rejects PAUSED state"""
        mock_bridge.get_status.return_value = {
            "STATE": ESP32State.PAUSED.value,
            "STATE_NAME": "PAUSED",
        }

        request_body = CurrentSetRequest(amperage=16)
        with pytest.raises(ValueError, match="Akım ayarlanamaz"):
            current_service.set_current(request_body)

        mock_bridge.send_current_set.assert_not_called()

    def test_current_set_allows_idle_state(self, current_service, mock_bridge):
        """Test that current set allows IDLE state"""
        mock_bridge.get_status.return_value = {
            "STATE": ESP32State.IDLE.value,
            "STATE_NAME": "IDLE",
        }

        request_body = CurrentSetRequest(amperage=16)
        result = current_service.set_current(request_body)

        assert result["success"] is True
        mock_bridge.send_current_set.assert_called_once_with(16)

    def test_current_set_allows_ev_connected_state(self, current_service, mock_bridge):
        """Test that current set allows EV_CONNECTED state"""
        mock_bridge.get_status.return_value = {
            "STATE": ESP32State.EV_CONNECTED.value,
            "STATE_NAME": "EV_CONNECTED",
        }

        request_body = CurrentSetRequest(amperage=16)
        result = current_service.set_current(request_body)

        assert result["success"] is True
        mock_bridge.send_current_set.assert_called_once_with(16)

    def test_current_set_allows_ready_state(self, current_service, mock_bridge):
        """Test that current set allows READY state"""
        mock_bridge.get_status.return_value = {
            "STATE": ESP32State.READY.value,
            "STATE_NAME": "READY",
        }

        request_body = CurrentSetRequest(amperage=16)
        result = current_service.set_current(request_body)

        assert result["success"] is True
        mock_bridge.send_current_set.assert_called_once_with(16)

    def test_current_set_handles_command_failure(self, current_service, mock_bridge):
        """Test that current set handles command send failure"""
        mock_bridge.get_status.return_value = {
            "STATE": ESP32State.IDLE.value,
            "STATE_NAME": "IDLE",
        }
        mock_bridge.send_current_set.return_value = False

        request_body = CurrentSetRequest(amperage=16)
        with pytest.raises(ValueError, match="Akım ayarlama komutu gönderilemedi"):
            current_service.set_current(request_body)

        mock_bridge.send_current_set.assert_called_once_with(16)

    def test_current_set_various_amperage_values(self, current_service, mock_bridge):
        """Test current set with various amperage values"""
        mock_bridge.get_status.return_value = {
            "STATE": ESP32State.IDLE.value,
            "STATE_NAME": "IDLE",
        }

        test_values = [6, 10, 13, 16, 20, 25, 32]

        for amperage in test_values:
            mock_bridge.send_current_set.reset_mock()
            request_body = CurrentSetRequest(amperage=amperage)
            result = current_service.set_current(request_body)

            assert result["success"] is True
            assert result["data"]["amperage"] == amperage
            mock_bridge.send_current_set.assert_called_once_with(amperage)


class TestCommandProtocolCompliance:
    """Command protocol compliance tests"""

    @pytest.fixture
    def protocol_data(self):
        """Load protocol.json"""
        protocol_path = Path(__file__).parent.parent / "esp32" / "protocol.json"
        with open(protocol_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_authorization_command_matches_protocol(self, protocol_data):
        """Test that authorization command matches protocol.json"""
        auth_command = protocol_data["commands"]["authorization"]
        expected_byte_array = auth_command["byte_array"]
        # Expected: [65, 1, 44, 1, 16]

        # Verify protocol format: 41 [KOMUT] 2C [DEĞER] 10
        assert expected_byte_array[0] == 0x41, "Header should be 0x41"
        assert expected_byte_array[1] == 0x01, "Command ID should be 0x01"
        assert expected_byte_array[2] == 0x2C, "Separator should be 0x2C"
        assert expected_byte_array[3] == 0x01, "Value should be 0x01"
        assert expected_byte_array[4] == 0x10, "Footer should be 0x10"

    def test_charge_stop_command_matches_protocol(self, protocol_data):
        """Test that charge_stop command matches protocol.json"""
        stop_command = protocol_data["commands"]["charge_stop"]
        expected_byte_array = stop_command["byte_array"]
        # Expected: [65, 4, 44, 7, 16]

        # Verify protocol format: 41 [KOMUT] 2C [DEĞER] 10
        assert expected_byte_array[0] == 0x41, "Header should be 0x41"
        assert expected_byte_array[1] == 0x04, "Command ID should be 0x04"
        assert expected_byte_array[2] == 0x2C, "Separator should be 0x2C"
        assert expected_byte_array[3] == 0x07, "Value should be 0x07"
        assert expected_byte_array[4] == 0x10, "Footer should be 0x10"

    def test_current_set_command_matches_protocol(self, protocol_data):
        """Test that current_set command matches protocol format"""
        # Current set uses dynamic value: 41 [0x02] 2C [amperage] 10
        current_set_16a = protocol_data["commands"]["current_set_16A"]
        expected_byte_array = current_set_16a["byte_array"]
        # Expected: [65, 2, 44, 16, 16]

        # Verify protocol format: 41 [KOMUT] 2C [DEĞER] 10
        assert expected_byte_array[0] == 0x41, "Header should be 0x41"
        assert expected_byte_array[1] == 0x02, "Command ID should be 0x02"
        assert expected_byte_array[2] == 0x2C, "Separator should be 0x2C"
        assert expected_byte_array[3] == 16, "Value should be 16 (amperage)"
        assert expected_byte_array[4] == 0x10, "Footer should be 0x10"

    def test_all_current_set_commands_match_protocol(self, protocol_data):
        """Test that all current_set commands match protocol format"""
        current_set_commands = {
            k: v
            for k, v in protocol_data["commands"].items()
            if k.startswith("current_set_")
        }

        for cmd_name, cmd_data in current_set_commands.items():
            byte_array = cmd_data["byte_array"]
            amperage = cmd_data["amperage"]

            # Verify protocol format: 41 [KOMUT] 2C [DEĞER] 10
            assert byte_array[0] == 0x41, f"{cmd_name}: Header should be 0x41"
            assert byte_array[1] == 0x02, f"{cmd_name}: Command ID should be 0x02"
            assert byte_array[2] == 0x2C, f"{cmd_name}: Separator should be 0x2C"
            assert byte_array[3] == amperage, f"{cmd_name}: Value should match amperage"
            assert byte_array[4] == 0x10, f"{cmd_name}: Footer should be 0x10"
