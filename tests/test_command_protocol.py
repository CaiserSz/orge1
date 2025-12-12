"""
Command Protocol Compliance Tests
Created: 2025-12-13 02:37:00
Last Modified: 2025-12-13 02:37:00
Version: 1.0.0
Description: ESP32 komut protokolü dry-run uyumluluk testleri.
"""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from api.event_detector import ESP32State
from api.session import SessionStatus
from esp32.bridge import ESP32Bridge


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
