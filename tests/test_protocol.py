"""
ESP32 Protocol JSON Unit and Edge Case Tests
Created: 2025-12-10 18:15:00
Last Modified: 2025-12-16 09:55:00
Version: 1.1.1
Description: protocol.json dosyası için kapsamlı unit ve edge case testleri
"""

import json
from pathlib import Path

import pytest

from esp32.bridge import PROTOCOL_HEADER, PROTOCOL_SEPARATOR, PROTOCOL_FOOTER


class TestProtocolFile:
    """Protocol file existence and format tests"""

    def test_protocol_file_exists(self):
        """Test that protocol.json file exists"""
        protocol_path = Path(__file__).parent.parent / "esp32" / "protocol.json"
        assert protocol_path.exists(), "protocol.json dosyası bulunamadı"

    def test_protocol_file_valid_json(self):
        """Test that protocol.json is valid JSON"""
        protocol_path = Path(__file__).parent.parent / "esp32" / "protocol.json"
        with open(protocol_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict), "protocol.json geçerli bir JSON dict değil"

    def test_protocol_file_encoding(self):
        """Test that protocol.json uses UTF-8 encoding"""
        protocol_path = Path(__file__).parent.parent / "esp32" / "protocol.json"
        with open(protocol_path, "r", encoding="utf-8") as f:
            content = f.read()
        # UTF-8 encoding ile okunabilmeli
        assert isinstance(content, str)


class TestProtocolStructure:
    """Protocol structure validation tests"""

    @pytest.fixture
    def protocol_data(self):
        """Load protocol.json data"""
        protocol_path = Path(__file__).parent.parent / "esp32" / "protocol.json"
        with open(protocol_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_protocol_has_protocol_section(self, protocol_data):
        """Test that protocol section exists"""
        assert "protocol" in protocol_data, "protocol bölümü bulunamadı"

    def test_protocol_has_commands_section(self, protocol_data):
        """Test that commands section exists"""
        assert "commands" in protocol_data, "commands bölümü bulunamadı"

    def test_protocol_has_status_message_section(self, protocol_data):
        """Test that status_message section exists"""
        assert "status_message" in protocol_data, "status_message bölümü bulunamadı"

    def test_protocol_has_rules_section(self, protocol_data):
        """Test that rules section exists"""
        assert "rules" in protocol_data, "rules bölümü bulunamadı"


class TestProtocolMetadata:
    """Protocol metadata validation tests"""

    @pytest.fixture
    def protocol_metadata(self):
        """Load protocol metadata"""
        protocol_path = Path(__file__).parent.parent / "esp32" / "protocol.json"
        with open(protocol_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("protocol", {})

    def test_protocol_name(self, protocol_metadata):
        """Test protocol name"""
        assert "name" in protocol_metadata, "protocol name bulunamadı"
        assert isinstance(protocol_metadata["name"], str), "protocol name string değil"

    def test_protocol_version(self, protocol_metadata):
        """Test protocol version"""
        assert "version" in protocol_metadata, "protocol version bulunamadı"
        assert isinstance(
            protocol_metadata["version"], str
        ), "protocol version string değil"

    def test_protocol_baudrate(self, protocol_metadata):
        """Test protocol baudrate"""
        assert "baudrate" in protocol_metadata, "protocol baudrate bulunamadı"
        assert protocol_metadata["baudrate"] == 115200, "baudrate 115200 değil"

    def test_protocol_packet_size(self, protocol_metadata):
        """Test protocol packet size"""
        assert "packet_size" in protocol_metadata, "protocol packet_size bulunamadı"
        assert protocol_metadata["packet_size"] == 5, "packet_size 5 değil"

    def test_protocol_format(self, protocol_metadata):
        """Test protocol format"""
        assert "format" in protocol_metadata, "protocol format bulunamadı"
        assert "41" in protocol_metadata["format"], "format header içermiyor"
        assert "2C" in protocol_metadata["format"], "format separator içermiyor"
        assert "10" in protocol_metadata["format"], "format footer içermiyor"

    def test_protocol_constants(self, protocol_metadata):
        """Test protocol constants"""
        assert "constants" in protocol_metadata, "protocol constants bulunamadı"
        constants = protocol_metadata["constants"]
        assert constants["header"] == "0x41", "header 0x41 değil"
        assert constants["separator"] == "0x2C", "separator 0x2C değil"
        assert constants["footer"] == "0x10", "footer 0x10 değil"


class TestProtocolCommands:
    """Protocol commands validation tests"""

    @pytest.fixture
    def commands(self):
        """Load commands"""
        protocol_path = Path(__file__).parent.parent / "esp32" / "protocol.json"
        with open(protocol_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("commands", {})

    def test_status_command_exists(self, commands):
        """Test that status command exists"""
        assert "status" in commands, "status komutu bulunamadı"

    def test_authorization_command_exists(self, commands):
        """Test that authorization command exists"""
        assert "authorization" in commands, "authorization komutu bulunamadı"

    def test_charge_stop_command_exists(self, commands):
        """Test that charge_stop command exists"""
        assert "charge_stop" in commands, "charge_stop komutu bulunamadı"

    def test_current_set_commands_exist(self, commands):
        """Test that current_set commands exist"""
        current_set_commands = [
            k for k in commands.keys() if k.startswith("current_set_")
        ]
        assert len(current_set_commands) > 0, "current_set komutları bulunamadı"

    def test_command_structure(self, commands):
        """Test that each command has required structure"""
        required_fields = [
            "id",
            "value",
            "hex",
            "byte_array",
            "description",
            "category",
        ]
        for cmd_name, cmd_data in commands.items():
            for field in required_fields:
                assert field in cmd_data, f"{cmd_name} komutunda {field} bulunamadı"

    def test_command_byte_array_length(self, commands):
        """Test that all command byte arrays have length 5"""
        for cmd_name, cmd_data in commands.items():
            byte_array = cmd_data.get("byte_array", [])
            assert (
                len(byte_array) == 5
            ), f"{cmd_name} komutunun byte_array uzunluğu 5 değil"

    def test_command_byte_array_format(self, commands):
        """Test that command byte arrays follow protocol format"""
        for cmd_name, cmd_data in commands.items():
            byte_array = cmd_data.get("byte_array", [])
            if len(byte_array) == 5:
                assert byte_array[0] == PROTOCOL_HEADER, f"{cmd_name} header yanlış"
                assert byte_array[1] == int(
                    cmd_data["id"], 16
                ), f"{cmd_name} command ID yanlış"
                assert (
                    byte_array[2] == PROTOCOL_SEPARATOR
                ), f"{cmd_name} separator yanlış"
                assert byte_array[3] == int(
                    cmd_data["value"], 16
                ), f"{cmd_name} value yanlış"
                assert byte_array[4] == PROTOCOL_FOOTER, f"{cmd_name} footer yanlış"

    def test_status_command_values(self, commands):
        """Test status command specific values"""
        status_cmd = commands.get("status", {})
        assert status_cmd["id"] == "0x00", "status command ID yanlış"
        assert status_cmd["value"] == "0x00", "status command value yanlış"
        assert status_cmd["byte_array"] == [
            65,
            0,
            44,
            0,
            16,
        ], "status command byte_array yanlış"

    def test_authorization_command_values(self, commands):
        """Test authorization command specific values"""
        auth_cmd = commands.get("authorization", {})
        assert auth_cmd["id"] == "0x01", "authorization command ID yanlış"
        assert auth_cmd["value"] == "0x01", "authorization command value yanlış"
        assert auth_cmd["byte_array"] == [
            65,
            1,
            44,
            1,
            16,
        ], "authorization command byte_array yanlış"

    def test_charge_stop_command_values(self, commands):
        """Test charge_stop command specific values"""
        stop_cmd = commands.get("charge_stop", {})
        assert stop_cmd["id"] == "0x04", "charge_stop command ID yanlış"
        assert stop_cmd["value"] == "0x07", "charge_stop command value yanlış"
        assert stop_cmd["byte_array"] == [
            65,
            4,
            44,
            7,
            16,
        ], "charge_stop command byte_array yanlış"

    def test_current_set_command_ids(self, commands):
        """Test that all current_set commands have same ID"""
        current_set_commands = {
            k: v for k, v in commands.items() if k.startswith("current_set_")
        }
        if current_set_commands:
            first_id = list(current_set_commands.values())[0]["id"]
            for cmd_name, cmd_data in current_set_commands.items():
                assert cmd_data["id"] == first_id, f"{cmd_name} command ID farklı"

    def test_current_set_command_amperage(self, commands):
        """Test that current_set commands have amperage field"""
        current_set_commands = {
            k: v for k, v in commands.items() if k.startswith("current_set_")
        }
        for cmd_name, cmd_data in current_set_commands.items():
            assert "amperage" in cmd_data, f"{cmd_name} amperage field'ı yok"
            amperage = cmd_data["amperage"]
            assert (
                6 <= amperage <= 32
            ), f"{cmd_name} amperage değeri 6-32 aralığında değil"

    def test_current_set_command_value_matches_amperage(self, commands):
        """Test that current_set command value matches amperage"""
        current_set_commands = {
            k: v for k, v in commands.items() if k.startswith("current_set_")
        }
        for cmd_name, cmd_data in current_set_commands.items():
            amperage = cmd_data.get("amperage")
            value_hex = cmd_data.get("value", "")
            if amperage and value_hex:
                value_int = int(value_hex, 16)
                assert (
                    value_int == amperage
                ), f"{cmd_name} value amperage ile eşleşmiyor"


class TestProtocolStatusMessage:
    """Protocol status message format validation tests"""

    @pytest.fixture
    def status_message(self):
        """Load status_message section"""
        protocol_path = Path(__file__).parent.parent / "esp32" / "protocol.json"
        with open(protocol_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("status_message", {})

    def test_status_message_format_exists(self, status_message):
        """Test that status message format exists"""
        assert "format" in status_message, "status_message format bulunamadı"

    def test_status_message_format_structure(self, status_message):
        """Test that status message format has correct structure"""
        format_str = status_message.get("format", "")
        assert "<STAT;" in format_str, "format <STAT; içermiyor"
        assert ">" in format_str, "format > içermiyor"
        assert "STATE=" in format_str, "format STATE= içermiyor"

    def test_status_message_fields_exists(self, status_message):
        """Test that status message fields exist"""
        assert "fields" in status_message, "status_message fields bulunamadı"

    def test_status_message_fields_completeness(self, status_message):
        """Test that status message fields are complete"""
        fields = status_message.get("fields", {})
        required_fields = [
            "ID",
            "CP",
            "CPV",
            "PP",
            "PPV",
            "RL",
            "LOCK",
            "MOTOR",
            "PWM",
            "MAX",
            "CABLE",
            "AUTH",
            "STATE",
            "PB",
            "STOP",
        ]
        for field in required_fields:
            assert field in fields, f"{field} field'ı bulunamadı"

    def test_status_message_update_interval(self, status_message):
        """Test that status message update interval is defined"""
        assert (
            "update_interval_seconds" in status_message
        ), "update_interval_seconds bulunamadı"
        assert (
            status_message["update_interval_seconds"] == 5
        ), "update_interval_seconds 5 değil"
