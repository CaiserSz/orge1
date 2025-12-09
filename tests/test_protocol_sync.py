"""
Protocol JSON Senkronizasyon Testleri

ESP32 firmware ve protocol.json arasındaki senkronizasyonu kontrol eder.
Protocol JSON'daki komutların ESP32 firmware ile uyumlu olduğunu doğrular.

Oluşturulma Tarihi: 2025-12-10 01:40:00
"""

import json
import os
import pytest
from pathlib import Path


# ESP32 firmware komut tanımları (Commercial_08122025.ino'dan)
ESP32_COMMANDS = {
    "KOMUT_READ_STAT": 0,
    "KOMUT_AUTH": 1,
    "KOMUT_SET_MAX_AMP": 2,
    "KOMUT_KILIT": 3,
    "STATE_MACH": 4,
}

# ESP32 firmware komut listesi (Commercial_08122025.ino:176-185)
ESP32_COMMAND_NAMES = [
    "READSTAT",
    "AUTH=",
    "STOP",
    "SETMAXAMP=",
    "UNLOCK",
    "LOCK",
]

# ESP32 firmware state tanımları (Commercial_08122025.ino:189-197)
ESP32_STATES = {
    "SARJ_STAT_IDLE": 1,
    "SARJ_CABLE_DETECT": 2,
    "EV_CONNECTED": 3,
    "SARJA_HAZIR": 4,
    "SARJ_STAT_SARJ_BASLADI": 5,
    "SARJ_STAT_SARJ_DURAKLATILDI": 6,
    "SARJ_STAT_SARJ_BITIR": 7,
    "SARJ_STAT_FAULT_HARD": 8,
    "HARDFAULT_END": 0,
}

# Protocol JSON dosya yolu
PROTOCOL_JSON_PATH = Path(__file__).parent.parent / "esp32" / "protocol.json"


def load_protocol_json():
    """Protocol JSON dosyasını yükle"""
    with open(PROTOCOL_JSON_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


class TestProtocolJSONStructure:
    """Protocol JSON yapısal testleri"""

    def test_protocol_json_exists(self):
        """Protocol JSON dosyası var mı?"""
        assert PROTOCOL_JSON_PATH.exists(), f"Protocol JSON dosyası bulunamadı: {PROTOCOL_JSON_PATH}"

    def test_protocol_json_valid_json(self):
        """Protocol JSON geçerli JSON formatında mı?"""
        protocol_data = load_protocol_json()
        assert isinstance(protocol_data, dict), "Protocol JSON dict olmalı"

    def test_protocol_json_has_required_keys(self):
        """Protocol JSON gerekli anahtarlara sahip mi?"""
        protocol_data = load_protocol_json()
        required_keys = ["protocol", "commands", "status_message"]
        for key in required_keys:
            assert key in protocol_data, f"Protocol JSON'da '{key}' anahtarı eksik"

    def test_protocol_json_protocol_info(self):
        """Protocol JSON protocol bilgileri doğru mu?"""
        protocol_data = load_protocol_json()
        protocol = protocol_data.get("protocol", {})

        assert "name" in protocol, "Protocol name eksik"
        assert "version" in protocol, "Protocol version eksik"
        assert "baudrate" in protocol, "Protocol baudrate eksik"
        assert protocol.get("baudrate") == 115200, "Baudrate 115200 olmalı"
        assert protocol.get("packet_size") == 5, "Packet size 5 olmalı"


class TestProtocolJSONCommands:
    """Protocol JSON komut testleri"""

    def test_protocol_json_has_status_command(self):
        """Status komutu protocol JSON'da var mı?"""
        protocol_data = load_protocol_json()
        commands = protocol_data.get("commands", {})

        assert "status" in commands, "Status komutu eksik"
        status_cmd = commands["status"]
        assert status_cmd.get("id") == "0x00", "Status komut ID'si 0x00 olmalı"
        assert status_cmd.get("byte_array") == [65, 0, 44, 0, 16], "Status komut byte array yanlış"

    def test_protocol_json_has_authorization_command(self):
        """Authorization komutu protocol JSON'da var mı?"""
        protocol_data = load_protocol_json()
        commands = protocol_data.get("commands", {})

        assert "authorization" in commands, "Authorization komutu eksik"
        auth_cmd = commands["authorization"]
        assert auth_cmd.get("id") == "0x01", "Authorization komut ID'si 0x01 olmalı"
        assert auth_cmd.get("byte_array") == [65, 1, 44, 1, 16], "Authorization komut byte array yanlış"

    def test_protocol_json_has_current_set_commands(self):
        """Current set komutları protocol JSON'da var mı?"""
        protocol_data = load_protocol_json()
        commands = protocol_data.get("commands", {})

        # Current set komutları kontrol et
        current_set_commands = [k for k in commands.keys() if k.startswith("current_set_")]
        assert len(current_set_commands) > 0, "Current set komutları eksik"

        # Tüm current set komutlarının ID'si 0x02 olmalı
        for cmd_name in current_set_commands:
            cmd = commands[cmd_name]
            assert cmd.get("id") == "0x02", f"{cmd_name} komut ID'si 0x02 olmalı"

    def test_protocol_json_has_charge_stop_command(self):
        """Charge stop komutu protocol JSON'da var mı?"""
        protocol_data = load_protocol_json()
        commands = protocol_data.get("commands", {})

        assert "charge_stop" in commands, "Charge stop komutu eksik"
        stop_cmd = commands["charge_stop"]
        assert stop_cmd.get("id") == "0x04", "Charge stop komut ID'si 0x04 olmalı"
        assert stop_cmd.get("value") == "0x07", "Charge stop komut değeri 0x07 olmalı"

    def test_protocol_json_command_format(self):
        """Protocol JSON komut formatı doğru mu?"""
        protocol_data = load_protocol_json()
        commands = protocol_data.get("commands", {})

        for cmd_name, cmd_data in commands.items():
            # Her komutun gerekli alanları olmalı
            assert "id" in cmd_data, f"{cmd_name} komutunda 'id' eksik"
            assert "hex" in cmd_data, f"{cmd_name} komutunda 'hex' eksik"
            assert "byte_array" in cmd_data, f"{cmd_name} komutunda 'byte_array' eksik"

            # Byte array uzunluğu 5 olmalı
            byte_array = cmd_data.get("byte_array", [])
            assert len(byte_array) == 5, f"{cmd_name} komut byte array uzunluğu 5 olmalı"

            # Byte array formatı kontrolü: 41 [KOMUT] 2C [DEĞER] 10
            assert byte_array[0] == 0x41, f"{cmd_name} komut byte array[0] 0x41 olmalı"
            assert byte_array[2] == 0x2C, f"{cmd_name} komut byte array[2] 0x2C olmalı"
            assert byte_array[4] == 0x10, f"{cmd_name} komut byte array[4] 0x10 olmalı"


class TestProtocolJSONStatusMessage:
    """Protocol JSON status message testleri"""

    def test_protocol_json_has_status_message(self):
        """Status message format protocol JSON'da var mı?"""
        protocol_data = load_protocol_json()

        assert "status_message" in protocol_data, "Status message format eksik"
        status_msg = protocol_data["status_message"]

        assert "format" in status_msg, "Status message format string eksik"
        assert "fields" in status_msg, "Status message fields eksik"

    def test_protocol_json_status_message_fields(self):
        """Status message alanları doğru mu?"""
        protocol_data = load_protocol_json()
        status_msg = protocol_data.get("status_message", {})
        fields = status_msg.get("fields", {})

        # ESP32 firmware'deki status mesajı alanları (sendStat fonksiyonundan)
        expected_fields = [
            "ID", "CP", "CPV", "PP", "PPV", "RL", "LOCK", "MOTOR",
            "PWM", "MAX", "CABLE", "AUTH", "STATE", "PB", "STOP"
        ]

        for field in expected_fields:
            assert field in fields, f"Status message'da '{field}' alanı eksik"

    def test_protocol_json_status_message_format(self):
        """Status message format string doğru mu?"""
        protocol_data = load_protocol_json()
        status_msg = protocol_data.get("status_message", {})
        format_str = status_msg.get("format", "")

        # Format string'de gerekli alanlar olmalı
        assert "STATE=" in format_str, "Status message format'ında STATE= eksik"
        assert "AUTH=" in format_str, "Status message format'ında AUTH= eksik"
        assert "CP=" in format_str, "Status message format'ında CP= eksik"


class TestProtocolJSONSync:
    """Protocol JSON ve ESP32 firmware senkronizasyon testleri"""

    def test_status_command_sync(self):
        """Status komutu ESP32 firmware ile senkronize mi?"""
        protocol_data = load_protocol_json()
        commands = protocol_data.get("commands", {})

        # ESP32 firmware: KOMUT_READ_STAT = 0
        status_cmd = commands.get("status", {})
        assert status_cmd.get("id") == "0x00", "Status komut ID'si ESP32 firmware ile uyumsuz"

    def test_authorization_command_sync(self):
        """Authorization komutu ESP32 firmware ile senkronize mi?"""
        protocol_data = load_protocol_json()
        commands = protocol_data.get("commands", {})

        # ESP32 firmware: KOMUT_AUTH = 1
        auth_cmd = commands.get("authorization", {})
        assert auth_cmd.get("id") == "0x01", "Authorization komut ID'si ESP32 firmware ile uyumsuz"

    def test_current_set_command_sync(self):
        """Current set komutu ESP32 firmware ile senkronize mi?"""
        protocol_data = load_protocol_json()
        commands = protocol_data.get("commands", {})

        # ESP32 firmware: KOMUT_SET_MAX_AMP = 2
        # Current set komutlarından birini kontrol et
        current_set_6A = commands.get("current_set_6A", {})
        assert current_set_6A.get("id") == "0x02", "Current set komut ID'si ESP32 firmware ile uyumsuz"

    def test_charge_stop_command_sync(self):
        """Charge stop komutu ESP32 firmware ile senkronize mi?"""
        protocol_data = load_protocol_json()
        commands = protocol_data.get("commands", {})

        # ESP32 firmware: STATE_MACH = 4, değer = 7 (SARJ_STAT_SARJ_BITIR)
        stop_cmd = commands.get("charge_stop", {})
        assert stop_cmd.get("id") == "0x04", "Charge stop komut ID'si ESP32 firmware ile uyumsuz"
        assert stop_cmd.get("value") == "0x07", "Charge stop komut değeri ESP32 firmware ile uyumsuz"

    def test_command_byte_array_format(self):
        """Komut byte array formatı ESP32 firmware ile uyumlu mu?"""
        protocol_data = load_protocol_json()
        commands = protocol_data.get("commands", {})

        # Format: 41 [KOMUT] 2C [DEĞER] 10
        for cmd_name, cmd_data in commands.items():
            byte_array = cmd_data.get("byte_array", [])

            # Header: 0x41
            assert byte_array[0] == 0x41, f"{cmd_name} komut header 0x41 olmalı"

            # Separator: 0x2C
            assert byte_array[2] == 0x2C, f"{cmd_name} komut separator 0x2C olmalı"

            # Footer: 0x10
            assert byte_array[4] == 0x10, f"{cmd_name} komut footer 0x10 olmalı"


class TestProtocolJSONCurrentSetRange:
    """Protocol JSON current set aralığı testleri"""

    def test_current_set_range(self):
        """Current set komutları 6-32A aralığında mı?"""
        protocol_data = load_protocol_json()
        commands = protocol_data.get("commands", {})

        # Current set komutlarını bul
        current_set_commands = {k: v for k, v in commands.items() if k.startswith("current_set_")}

        assert len(current_set_commands) > 0, "Current set komutları bulunamadı"

        # Her komutun amperage değeri 6-32 aralığında olmalı
        for cmd_name, cmd_data in current_set_commands.items():
            amperage = cmd_data.get("amperage")
            assert amperage is not None, f"{cmd_name} komutunda amperage eksik"
            assert 6 <= amperage <= 32, f"{cmd_name} komut amperage değeri 6-32 aralığında olmalı"

    def test_current_set_value_matches_amperage(self):
        """Current set komut değeri amperage ile eşleşiyor mu?"""
        protocol_data = load_protocol_json()
        commands = protocol_data.get("commands", {})

        current_set_commands = {k: v for k, v in commands.items() if k.startswith("current_set_")}

        for cmd_name, cmd_data in current_set_commands.items():
            amperage = cmd_data.get("amperage")
            value_hex = cmd_data.get("value")

            if amperage is not None and value_hex is not None:
                # Hex değeri integer'a çevir
                value_int = int(value_hex, 16)
                assert value_int == amperage, f"{cmd_name} komut değeri ({value_int}) amperage ({amperage}) ile eşleşmiyor"


class TestProtocolJSONRules:
    """Protocol JSON kuralları testleri"""

    def test_protocol_json_has_rules(self):
        """Protocol JSON'da kurallar var mı?"""
        protocol_data = load_protocol_json()

        assert "rules" in protocol_data, "Protocol JSON'da rules eksik"
        rules = protocol_data.get("rules", {})
        assert isinstance(rules, dict), "Rules dict olmalı"

    def test_protocol_json_rules_content(self):
        """Protocol JSON kuralları içeriği doğru mu?"""
        protocol_data = load_protocol_json()
        rules = protocol_data.get("rules", {})

        # Beklenen kurallar
        expected_rules = [
            "current_set_only_before_charging",
            "only_defined_commands",
            "current_set_range"
        ]

        for rule in expected_rules:
            assert rule in rules, f"Protocol JSON'da '{rule}' kuralı eksik"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

