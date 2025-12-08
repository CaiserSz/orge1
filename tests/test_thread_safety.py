"""
Thread Safety ve Race Condition Testleri
Created: 2025-12-09 02:20:00
Last Modified: 2025-12-09 02:20:00
Version: 1.0.0
Description: Thread safety, race condition ve concurrent access testleri
"""

import pytest
import sys
import threading
import time
from unittest.mock import Mock, patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from esp32.bridge import ESP32Bridge


class TestThreadSafety:
    """Thread safety testleri"""
    
    def test_concurrent_status_access(self):
        """Eşzamanlı status erişimi thread-safe mi?"""
        mock_serial = Mock()
        mock_serial.is_open = True
        mock_serial.readline = Mock(return_value=b'<STAT;STATE=1;AUTH=0;>\n')
        
        with patch('serial.Serial', return_value=mock_serial):
            bridge = ESP32Bridge(port='/dev/ttyUSB0')
            bridge.serial_connection = mock_serial
            bridge.is_connected = True
            
            # Mock status data
            bridge.last_status = {'STATE': 1, 'AUTH': 0}
            
            results = []
            errors = []
            
            def get_status():
                try:
                    status = bridge.get_status()
                    results.append(status)
                except Exception as e:
                    errors.append(e)
            
            # 10 thread eşzamanlı status al
            threads = [threading.Thread(target=get_status) for _ in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            
            # Hata olmamalı ve tüm thread'ler sonuç almalı
            assert len(errors) == 0, f"Thread safety hatası: {errors}"
            assert len(results) == 10
    
    def test_status_lock_mechanism(self):
        """Status lock mekanizması çalışıyor mu?"""
        mock_serial = Mock()
        mock_serial.is_open = True
        
        with patch('serial.Serial', return_value=mock_serial):
            bridge = ESP32Bridge(port='/dev/ttyUSB0')
            bridge.serial_connection = mock_serial
            bridge.is_connected = True
            
            # Lock mekanizması var mı?
            assert hasattr(bridge, 'status_lock'), "Status lock mekanizması yok"
            assert bridge.status_lock is not None


class TestRaceConditions:
    """Race condition testleri"""
    
    def test_concurrent_command_sending(self):
        """Eşzamanlı komut gönderme race condition'ı var mı?"""
        mock_serial = Mock()
        mock_serial.is_open = True
        mock_serial.write = Mock()
        mock_serial.flush = Mock()
        
        with patch('serial.Serial', return_value=mock_serial):
            bridge = ESP32Bridge(port='/dev/ttyUSB0')
            bridge.serial_connection = mock_serial
            bridge.is_connected = True
            
            write_count = []
            
            def send_command():
                result = bridge.send_authorization()
                write_count.append(mock_serial.write.call_count)
                return result
            
            # 5 thread eşzamanlı komut gönder
            threads = [threading.Thread(target=send_command) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            
            # Tüm komutlar gönderilmeli
            assert mock_serial.write.call_count == 5
    
    def test_status_update_during_command(self):
        """Komut gönderilirken status güncellemesi race condition'ı"""
        mock_serial = Mock()
        mock_serial.is_open = True
        mock_serial.write = Mock()
        mock_serial.flush = Mock()
        mock_serial.readline = Mock(return_value=b'<STAT;STATE=2;>\n')
        
        with patch('serial.Serial', return_value=mock_serial):
            bridge = ESP32Bridge(port='/dev/ttyUSB0')
            bridge.serial_connection = mock_serial
            bridge.is_connected = True
            
            results = []
            
            def update_status():
                bridge.last_status = {'STATE': 2}
                results.append(bridge.get_status())
            
            def send_command():
                bridge.send_authorization()
            
            # Status güncelleme ve komut gönderme eşzamanlı
            t1 = threading.Thread(target=update_status)
            t2 = threading.Thread(target=send_command)
            
            t1.start()
            t2.start()
            t1.join()
            t2.join()
            
            # Her iki işlem de başarılı olmalı
            assert len(results) == 1
            assert mock_serial.write.call_count == 1

