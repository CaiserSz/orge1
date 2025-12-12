"""
Protocol Rule Tests
Created: 2025-12-13 02:40:00
Last Modified: 2025-12-13 02:40:00
Version: 1.0.0
Description: ESP32 protokol kuralları ve edge case testleri.
"""

import json
from pathlib import Path

import pytest


class TestProtocolRules:
    """Protocol rules validation tests"""

    @pytest.fixture
    def rules(self):
        """Load rules section"""
        protocol_path = Path(__file__).parent.parent / "esp32" / "protocol.json"
        with open(protocol_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("rules", {})

    def test_rules_exist(self, rules):
        """Test that rules section exists and has content"""
        assert len(rules) > 0, "rules bölümü boş"

    def test_current_set_only_before_charging_rule(self, rules):
        """Test current_set_only_before_charging rule"""
        assert (
            "current_set_only_before_charging" in rules
        ), "current_set_only_before_charging kuralı bulunamadı"

    def test_only_defined_commands_rule(self, rules):
        """Test only_defined_commands rule"""
        assert (
            "only_defined_commands" in rules
        ), "only_defined_commands kuralı bulunamadı"

    def test_current_set_range_rule(self, rules):
        """Test current_set_range rule"""
        assert "current_set_range" in rules, "current_set_range kuralı bulunamadı"
        rule_text = rules["current_set_range"]
        assert (
            "6-32" in rule_text
        ), "current_set_range kuralı 6-32 aralığını belirtmiyor"


class TestProtocolEdgeCases:
    """Protocol edge case tests"""

    @pytest.fixture
    def protocol_data(self):
        """Load protocol.json data"""
        protocol_path = Path(__file__).parent.parent / "esp32" / "protocol.json"
        with open(protocol_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_no_duplicate_command_ids(self, protocol_data):
        """Test that no two commands have same ID and value combination"""
        commands = protocol_data.get("commands", {})
        id_value_pairs = {}
        for cmd_name, cmd_data in commands.items():
            cmd_id = cmd_data.get("id")
            cmd_value = cmd_data.get("value")
            pair = (cmd_id, cmd_value)
            if pair in id_value_pairs:
                # current_set commands can have same ID but different values
                if not cmd_name.startswith("current_set_"):
                    pytest.fail(
                        f"{cmd_name} ve {id_value_pairs[pair]} aynı ID ve value'ya sahip"
                    )
            else:
                id_value_pairs[pair] = cmd_name

    def test_all_hex_values_valid(self, protocol_data):
        """Test that all hex values are valid"""
        commands = protocol_data.get("commands", {})
        for cmd_name, cmd_data in commands.items():
            hex_str = cmd_data.get("hex", "")
            if hex_str:
                # Hex string'i parse etmeye çalış
                hex_bytes = hex_str.split()
                for hex_byte in hex_bytes:
                    try:
                        int(hex_byte, 16)
                    except ValueError:
                        pytest.fail(
                            f"{cmd_name} komutunda geçersiz hex değer: {hex_byte}"
                        )

    def test_byte_array_matches_hex(self, protocol_data):
        """Test that byte_array matches hex string"""
        commands = protocol_data.get("commands", {})
        for cmd_name, cmd_data in commands.items():
            hex_str = cmd_data.get("hex", "")
            byte_array = cmd_data.get("byte_array", [])
            if hex_str and byte_array:
                hex_bytes = [int(b, 16) for b in hex_str.split()]
                assert (
                    byte_array == hex_bytes
                ), f"{cmd_name} byte_array hex ile eşleşmiyor"

    def test_no_missing_categories(self, protocol_data):
        """Test that all commands have valid categories"""
        commands = protocol_data.get("commands", {})
        valid_categories = ["status", "charge_control", "current_set"]
        for cmd_name, cmd_data in commands.items():
            category = cmd_data.get("category", "")
            assert (
                category in valid_categories
            ), f"{cmd_name} geçersiz category: {category}"
