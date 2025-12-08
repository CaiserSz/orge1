"""
ESP32 Bridge Unit Tests
Created: 2025-12-09 02:00:00
Last Modified: 2025-12-09 02:00:00
Version: 1.0.0
Description: ESP32 bridge modülü için unit testler - Hex kod doğrulama
"""

import pytest
import sys
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

# Proje root'unu path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent))

from esp32.bridge import ESP32Bridge, PROTOCOL_HEADER, PROTOCOL_SEPARATOR, PROTOCOL_FOOTER


class TestESP32BridgeHexCodes:
    """ESP32 Bridge hex kod doğrulama testleri"""
    
    def setup_method(self):
        """Her test öncesi mock bridge oluştur"""
        self.mock_serial = Mock()
        self.mock_serial.is_open = True
        self.mock_serial.write = Mock()
        self.mock_serial.flush = Mock()
        
        with patch('serial.Serial', return_value=self.mock_serial):
            self.bridge = ESP32Bridge(port='/dev/ttyUSB0')
            self.bridge.serial_connection = self.mock_serial
            self.bridge.is_connected = True
    
    def test_authorization_hex_code(self):
        """Authorization komutu hex kodu doğru mu?"""
        # Beklenen: 41 01 2C 01 10 = [65, 1, 44, 1, 16]
        expected_bytes = [0x41, 0x01, 0x2C, 0x01, 0x10]
        
        result = self.bridge.send_authorization()
        
        assert result is True
        assert self.mock_serial.write.called
        call_args = self.mock_serial.write.call_args[0][0]
        assert list(call_args) == expected_bytes, \
            f"Beklenen: {expected_bytes}, Gönderilen: {list(call_args)}"
    
    def test_charge_stop_hex_code(self):
        """Charge stop komutu hex kodu doğru mu?"""
        # Beklenen: 41 04 2C 07 10 = [65, 4, 44, 7, 16]
        expected_bytes = [0x41, 0x04, 0x2C, 0x07, 0x10]
        
        result = self.bridge.send_charge_stop()
        
        assert result is True
        assert self.mock_serial.write.called
        call_args = self.mock_serial.write.call_args[0][0]
        assert list(call_args) == expected_bytes, \
            f"Beklenen: {expected_bytes}, Gönderilen: {list(call_args)}"
    
    def test_current_set_8A_hex_code(self):
        """Current set 8A komutu hex kodu doğru mu?"""
        # Beklenen: 41 02 2C 08 10 = [65, 2, 44, 8, 16]
        expected_bytes = [0x41, 0x02, 0x2C, 0x08, 0x10]
        
        result = self.bridge.send_current_set(8)
        
        assert result is True
        assert self.mock_serial.write.called
        call_args = self.mock_serial.write.call_args[0][0]
        assert list(call_args) == expected_bytes, \
            f"Beklenen: {expected_bytes}, Gönderilen: {list(call_args)}"
    
    def test_current_set_16A_hex_code(self):
        """Current set 16A komutu hex kodu doğru mu?"""
        # Beklenen: 41 02 2C 10 10 = [65, 2, 44, 16, 16]
        expected_bytes = [0x41, 0x02, 0x2C, 0x10, 0x10]
        
        result = self.bridge.send_current_set(16)
        
        assert result is True
        assert self.mock_serial.write.called
        call_args = self.mock_serial.write.call_args[0][0]
        assert list(call_args) == expected_bytes, \
            f"Beklenen: {expected_bytes}, Gönderilen: {list(call_args)}"
    
    def test_current_set_24A_hex_code(self):
        """Current set 24A komutu hex kodu doğru mu?"""
        # Beklenen: 41 02 2C 18 10 = [65, 2, 44, 24, 16]
        expected_bytes = [0x41, 0x02, 0x2C, 0x18, 0x10]
        
        result = self.bridge.send_current_set(24)
        
        assert result is True
        assert self.mock_serial.write.called
        call_args = self.mock_serial.write.call_args[0][0]
        assert list(call_args) == expected_bytes, \
            f"Beklenen: {expected_bytes}, Gönderilen: {list(call_args)}"
    
    def test_current_set_32A_hex_code(self):
        """Current set 32A komutu hex kodu doğru mu?"""
        # Beklenen: 41 02 2C 20 10 = [65, 2, 44, 32, 16]
        expected_bytes = [0x41, 0x02, 0x2C, 0x20, 0x10]
        
        result = self.bridge.send_current_set(32)
        
        assert result is True
        assert self.mock_serial.write.called
        call_args = self.mock_serial.write.call_args[0][0]
        assert list(call_args) == expected_bytes, \
            f"Beklenen: {expected_bytes}, Gönderilen: {list(call_args)}"
    
    def test_current_set_invalid_low(self):
        """Geçersiz düşük akım değeri reddedilmeli"""
        result = self.bridge.send_current_set(5)
        
        assert result is False
        assert not self.mock_serial.write.called
    
    def test_current_set_invalid_high(self):
        """Geçersiz yüksek akım değeri reddedilmeli"""
        result = self.bridge.send_current_set(33)
        
        assert result is False
        assert not self.mock_serial.write.called
    
    def test_status_request_hex_code(self):
        """Status request komutu hex kodu doğru mu?"""
        # Beklenen: 41 00 2C 00 10 = [65, 0, 44, 0, 16]
        expected_bytes = [0x41, 0x00, 0x2C, 0x00, 0x10]
        
        result = self.bridge.send_status_request()
        
        assert result is True
        assert self.mock_serial.write.called
        call_args = self.mock_serial.write.call_args[0][0]
        assert list(call_args) == expected_bytes, \
            f"Beklenen: {expected_bytes}, Gönderilen: {list(call_args)}"
    
    def test_command_format_validation(self):
        """Tüm komutlar 5 byte uzunluğunda olmalı"""
        commands = [
            (self.bridge.send_authorization, []),
            (self.bridge.send_charge_stop, []),
            (self.bridge.send_status_request, []),
            (self.bridge.send_current_set, [8]),
            (self.bridge.send_current_set, [16]),
            (self.bridge.send_current_set, [24]),
            (self.bridge.send_current_set, [32]),
        ]
        
        for cmd_func, args in commands:
            self.mock_serial.write.reset_mock()
            cmd_func(*args)
            
            if self.mock_serial.write.called:
                call_args = self.mock_serial.write.call_args[0][0]
                assert len(call_args) == 5, \
                    f"{cmd_func.__name__} komutu 5 byte olmalı, {len(call_args)} byte gönderildi"
    
    def test_protocol_constants(self):
        """Protokol sabitleri doğru mu?"""
        assert PROTOCOL_HEADER == 0x41, "Header 0x41 olmalı"
        assert PROTOCOL_SEPARATOR == 0x2C, "Separator 0x2C olmalı"
        assert PROTOCOL_FOOTER == 0x10, "Footer 0x10 olmalı"
    
    def test_current_set_all_valid_values(self):
        """6-32 aralığındaki tüm geçerli değerler test edilmeli"""
        for amperage in range(6, 33):
            self.mock_serial.write.reset_mock()
            result = self.bridge.send_current_set(amperage)
            
            assert result is True, f"{amperage}A geçerli olmalı"
            assert self.mock_serial.write.called
            
            call_args = self.mock_serial.write.call_args[0][0]
            # Format kontrolü: 41 02 2C [amperage] 10
            assert call_args[0] == 0x41, "Header yanlış"
            assert call_args[1] == 0x02, "Komut ID yanlış"
            assert call_args[2] == 0x2C, "Separator yanlış"
            assert call_args[3] == amperage, f"Amperage değeri yanlış: {call_args[3]} != {amperage}"
            assert call_args[4] == 0x10, "Footer yanlış"

