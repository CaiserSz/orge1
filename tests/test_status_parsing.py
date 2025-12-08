"""
Status Parsing Edge Case Testleri
Created: 2025-12-09 02:25:00
Last Modified: 2025-12-09 02:25:00
Version: 1.0.0
Description: Status mesajı parsing edge case'leri ve hata senaryoları
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from esp32.bridge import ESP32Bridge


class TestStatusParsing:
    """Status parsing testleri"""
    
    def setup_method(self):
        """Test setup"""
        self.bridge = ESP32Bridge()
    
    def test_valid_status_message(self):
        """Geçerli status mesajı parse edilmeli"""
        message = "<STAT;CP=0;CPV=3920;PP=1;PPV=910;RL=0;LOCK=0;MOTOR=0;PWM=255;MAX=16;CABLE=32;AUTH=0;STATE=2;PB=0;STOP=0;>"
        result = self.bridge._parse_status_message(message)
        
        assert result is not None
        assert result['CP'] == 0
        assert result['CPV'] == 3920
        assert result['PP'] == 1
        assert result['STATE'] == 2
        assert result['MAX'] == 16
        assert result['CABLE'] == 32
        assert 'timestamp' in result
    
    def test_incomplete_status_message(self):
        """Eksik alanlı status mesajı"""
        message = "<STAT;CP=0;STATE=1;>"
        result = self.bridge._parse_status_message(message)
        
        assert result is not None
        assert result['CP'] == 0
        assert result['STATE'] == 1
    
    def test_malformed_status_message(self):
        """Hatalı formatlı status mesajı"""
        message = "<STAT;CP=0;STATE=1"  # Kapanış tag'i yok
        result = self.bridge._parse_status_message(message)
        
        assert result is None
    
    def test_empty_status_message(self):
        """Boş status mesajı"""
        message = ""
        result = self.bridge._parse_status_message(message)
        
        assert result is None
    
    def test_status_with_float_values(self):
        """Float değerli status mesajı"""
        message = "<STAT;CPV=3920.5;PPV=910.2;STATE=1;>"
        result = self.bridge._parse_status_message(message)
        
        assert result is not None
        assert result['CPV'] == 3920.5
        assert result['PPV'] == 910.2
    
    def test_status_with_string_values(self):
        """String değerli status mesajı"""
        message = "<STAT;STATE=1;MESSAGE=test;>"
        result = self.bridge._parse_status_message(message)
        
        assert result is not None
        assert result['STATE'] == 1
        assert result['MESSAGE'] == 'test'
    
    def test_status_with_special_characters(self):
        """Özel karakterli status mesajı"""
        message = "<STAT;STATE=1;MSG=test-value;>"
        result = self.bridge._parse_status_message(message)
        
        assert result is not None
        assert result['MSG'] == 'test-value'
    
    def test_status_with_multiple_equals(self):
        """Eşittir karakteri içeren değer"""
        message = "<STAT;STATE=1;MSG=test=value;>"
        result = self.bridge._parse_status_message(message)
        
        assert result is not None
        # İlk eşittirden sonrası değer olarak alınmalı
        assert result['MSG'] == 'test=value'
    
    def test_status_with_empty_values(self):
        """Boş değerli alanlar"""
        message = "<STAT;STATE=1;EMPTY=;>"
        result = self.bridge._parse_status_message(message)
        
        assert result is not None
        assert result['STATE'] == 1
        # Boş değer string olarak kalmalı veya None olmalı
        assert 'EMPTY' in result
    
    def test_status_with_whitespace(self):
        """Whitespace içeren status mesajı"""
        message = "<STAT; CP=0 ; STATE=1 ; >"
        result = self.bridge._parse_status_message(message)
        
        assert result is not None
        assert result['CP'] == 0
        assert result['STATE'] == 1
    
    def test_status_with_newlines(self):
        """Newline içeren status mesajı"""
        message = "<STAT;CP=0;\nSTATE=1;>"
        result = self.bridge._parse_status_message(message)
        
        assert result is not None
        assert result['CP'] == 0
        assert result['STATE'] == 1
    
    def test_status_with_unicode(self):
        """Unicode karakter içeren status mesajı"""
        message = "<STAT;STATE=1;MSG=test-üğşç;>"
        result = self.bridge._parse_status_message(message)
        
        assert result is not None
        assert result['MSG'] == 'test-üğşç'
    
    def test_status_with_very_large_numbers(self):
        """Çok büyük sayılar"""
        message = "<STAT;STATE=1;LARGE=999999999;>"
        result = self.bridge._parse_status_message(message)
        
        assert result is not None
        assert result['LARGE'] == 999999999
    
    def test_status_with_negative_numbers(self):
        """Negatif sayılar"""
        message = "<STAT;STATE=1;NEG=-1;>"
        result = self.bridge._parse_status_message(message)
        
        assert result is not None
        assert result['NEG'] == -1
    
    def test_status_with_id_field(self):
        """ID alanı içeren status mesajı"""
        message = "<STAT;ID=123;CP=0;STATE=1;>"
        result = self.bridge._parse_status_message(message)
        
        assert result is not None
        assert result['ID'] == 123
        assert result['CP'] == 0
        assert result['STATE'] == 1

