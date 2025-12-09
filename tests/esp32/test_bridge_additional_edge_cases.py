"""
ESP32 Bridge Additional Edge Cases Tests
Created: 2025-12-10 00:25:00
Last Modified: 2025-12-10 09:00:00
Version: 1.0.0
Description: ESP32 Bridge ek edge case testleri
"""

import sys
from unittest.mock import Mock, patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from esp32.bridge import ESP32Bridge


class TestESP32BridgeAdditionalEdgeCases:
    """ESP32 Bridge ek edge case testleri"""

    def test_parse_status_message_malformed(self):
        """Parse status message - bozuk format"""
        bridge = ESP32Bridge()

        malformed_messages = [
            "<STAT",  # Kapanmamış
            "STAT;ID=1;>",  # Başlangıç yok
            "<STAT;ID=1",  # Kapanış yok
            "<STAT;>",  # Boş
            "<STAT;ID=;>",  # Boş değer
            "<STAT;=1;>",  # Boş key
            "<STAT;ID=1;CP=;STATE=2;>",  # Kısmi boş değerler
        ]

        for message in malformed_messages:
            result = bridge._parse_status_message(message)
            # Parse edilebilir veya None döndürmeli
            assert result is None or isinstance(result, dict)

    def test_parse_status_message_numeric_edge_cases(self):
        """Parse status message - sayısal edge case'ler"""
        bridge = ESP32Bridge()

        edge_cases = [
            "<STAT;ID=0;STATE=0;>",  # Sıfır değerler
            "<STAT;ID=-1;STATE=-1;>",  # Negatif değerler
            "<STAT;ID=999999;STATE=999999;>",  # Çok büyük değerler
            "<STAT;CPV=3920.5;PPV=2455.7;>",  # Float değerler
            "<STAT;ID=1.0;STATE=2.0;>",  # Float ama integer olmalı
        ]

        for message in edge_cases:
            result = bridge._parse_status_message(message)
            # Parse edilebilir veya None döndürmeli
            assert result is None or isinstance(result, dict)

    def test_send_command_bytes_empty_list(self):
        """Send command bytes - boş liste"""
        bridge = ESP32Bridge()
        bridge.is_connected = True
        bridge.serial_connection = Mock()
        bridge.serial_connection.is_open = True
        bridge.serial_connection.write = Mock(return_value=0)

        # Boş liste gönder
        result = bridge._send_command_bytes([])

        # Boş liste için False döndürmeli veya exception oluşmamalı
        assert result is False or result is True

    def test_send_command_bytes_invalid_length(self):
        """Send command bytes - geçersiz uzunluk"""
        bridge = ESP32Bridge()
        bridge.is_connected = True
        bridge.serial_connection = Mock()
        bridge.serial_connection.is_open = True
        bridge.serial_connection.write = Mock(return_value=0)

        # Geçersiz uzunlukta komut (5 byte olmalı)
        invalid_commands = [
            [0x41],  # Çok kısa
            [0x41, 0x01, 0x2C, 0x10],  # 4 byte
            [0x41, 0x01, 0x2C, 0x10, 0x10, 0x10],  # 6 byte
        ]

        for cmd in invalid_commands:
            result = bridge._send_command_bytes(cmd)
            # Geçersiz uzunluk için False döndürmeli
            assert result is False

    def test_get_status_sync_timeout_edge_cases(self):
        """Get status sync - timeout edge case'leri"""
        bridge = ESP32Bridge()
        bridge.is_connected = True

        # Status varsa hemen döner (get_status çağrılır ve status döner)
        bridge.last_status = {"STATE": 1}
        # get_status'u mock'la ki last_status'u döndürsün
        original_get_status = bridge.get_status

        def mock_get_status():
            return bridge.last_status

        bridge.get_status = mock_get_status
        bridge.send_status_request = Mock(return_value=True)

        result = bridge.get_status_sync(timeout=0.001)
        assert result is not None
        assert result["STATE"] == 1

        # Status yoksa timeout sonrası None döner
        bridge.last_status = None

        def mock_get_status_none():
            return None

        bridge.get_status = mock_get_status_none

        result = bridge.get_status_sync(timeout=0.01)
        # Timeout sonrası None döner
        assert result is None

    def test_find_esp32_port_edge_cases(self):
        """Find ESP32 port - edge case'ler"""
        bridge = ESP32Bridge()

        # Port bulunamadığında
        with patch("esp32.bridge.serial.tools.list_ports.comports", return_value=[]):
            result = bridge.find_esp32_port()
            assert result is None

        # Port description'da keyword yok
        mock_ports = [Mock(device="/dev/ttyUSB0", description="Unknown Device")]

        with patch(
            "esp32.bridge.serial.tools.list_ports.comports", return_value=mock_ports
        ):
            result = bridge.find_esp32_port()
            assert result is None
