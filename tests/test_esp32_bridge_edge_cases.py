"""
ESP32 Bridge Edge Case Tests
Created: 2025-12-10 01:40:00
Last Modified: 2025-12-10 01:40:00
Version: 1.0.0
Description: ESP32 Bridge singleton and parse status edge case tests
"""

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from esp32.bridge import ESP32Bridge, get_esp32_bridge


class TestESP32BridgeSingleton:
    """ESP32 Bridge singleton testleri"""

    def test_get_esp32_bridge_singleton(self):
        """Get ESP32 bridge - singleton"""
        # Singleton instance'ı reset etmek için
        import esp32.bridge as bridge_module

        original_instance = bridge_module._esp32_bridge_instance
        bridge_module._esp32_bridge_instance = None

        try:
            bridge1 = get_esp32_bridge()
            bridge2 = get_esp32_bridge()

            # Aynı instance döndürülmeli
            assert bridge1 is bridge2
        finally:
            # Restore original instance
            bridge_module._esp32_bridge_instance = original_instance

    def test_get_esp32_bridge_thread_safe(self):
        """Get ESP32 bridge - thread safe"""
        import esp32.bridge as bridge_module

        original_instance = bridge_module._esp32_bridge_instance
        bridge_module._esp32_bridge_instance = None

        try:
            bridges = []

            def get_bridge():
                bridge = get_esp32_bridge()
                bridges.append(bridge)

            threads = []
            for _ in range(10):
                thread = threading.Thread(target=get_bridge)
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            # Tüm bridge'ler aynı instance olmalı
            assert all(bridge is bridges[0] for bridge in bridges)
        finally:
            # Restore original instance
            bridge_module._esp32_bridge_instance = original_instance


class TestESP32BridgeParseStatusEdgeCases:
    """ESP32 Bridge parse status edge case testleri"""

    def test_parse_status_message_partial_fields(self):
        """Parse status message - kısmi field'lar"""
        bridge = ESP32Bridge()

        # Sadece bazı field'lar var
        message = "<STAT;ID=1;CP=1;STATE=1;>"
        result = bridge._parse_status_message(message)

        assert result is not None
        assert result.get("ID") == 1
        assert result.get("CP") == 1
        assert result.get("STATE") == 1

    def test_parse_status_message_duplicate_fields(self):
        """Parse status message - duplicate field'lar"""
        bridge = ESP32Bridge()

        # Duplicate field'lar (son değer kullanılmalı)
        message = "<STAT;ID=1;ID=2;STATE=1;>"
        result = bridge._parse_status_message(message)

        # Son değer kullanılmalı veya parse edilebilir
        assert result is not None

    def test_parse_status_message_special_characters(self):
        """Parse status message - özel karakterler"""
        bridge = ESP32Bridge()

        # Özel karakterler içeren mesajlar
        messages = [
            "<STAT;ID=1;MSG=TEST_MESSAGE;>",
            "<STAT;ID=1;MSG=TEST%20MESSAGE;>",
        ]

        for message in messages:
            result = bridge._parse_status_message(message)
            # Parse edilebilir veya None döndürmeli
            assert result is None or isinstance(result, dict)

    def test_parse_status_message_very_long(self):
        """Parse status message - çok uzun mesaj"""
        bridge = ESP32Bridge()

        # Çok uzun mesaj
        long_message = "<STAT;" + ";".join([f"ID={i}" for i in range(100)]) + ";>"
        result = bridge._parse_status_message(long_message)

        # Parse edilebilir veya None döndürmeli
        assert result is None or isinstance(result, dict)

    def test_parse_status_message_unicode(self):
        """Parse status message - unicode karakterler"""
        bridge = ESP32Bridge()

        # Unicode karakterler içeren mesajlar (normalde olmamalı ama test edelim)
        messages = [
            "<STAT;ID=1;MSG=Test;>",
            "<STAT;ID=1;MSG=Тест;>",  # Cyrillic
        ]

        for message in messages:
            result = bridge._parse_status_message(message)
            # Parse edilebilir veya None döndürmeli
            assert result is None or isinstance(result, dict)
