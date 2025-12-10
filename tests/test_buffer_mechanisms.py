"""
Buffer and Cache Mechanism Tests
Created: 2025-12-10 19:25:00
Last Modified: 2025-12-10 19:25:00
Version: 1.0.0
Description: Buffer ve cache mekanizmaları için testler
"""

from unittest.mock import Mock

import pytest

from esp32.bridge import ESP32Bridge


class TestStatusBuffer:
    """Status buffer (ring buffer) tests"""

    @pytest.fixture
    def bridge(self):
        """ESP32Bridge instance"""
        bridge = ESP32Bridge()
        bridge.is_connected = True
        bridge.serial_connection = Mock()
        bridge.serial_connection.is_open = True
        return bridge

    def test_status_buffer_initial_empty(self, bridge):
        """Test that status buffer is initially empty"""
        assert len(bridge._status_buffer) == 0

    def test_status_buffer_ring_behavior(self, bridge):
        """Test that status buffer acts as ring buffer"""
        # 50'den fazla status mesajı ekle
        for i in range(60):
            status = {"STATE": i % 9, "timestamp": f"2025-12-10T19:00:{i:02d}"}
            bridge._status_buffer.append(status)

        # Buffer maksimum 50 eleman tutmalı
        assert len(bridge._status_buffer) == 50

        # İlk eklenenler kaybolmalı, son eklenenler olmalı
        assert bridge._status_buffer[-1]["STATE"] == 59 % 9

    def test_get_status_history(self, bridge):
        """Test get_status_history method"""
        # Status mesajları ekle
        for i in range(15):
            status = {"STATE": i % 9, "timestamp": f"2025-12-10T19:00:{i:02d}"}
            bridge._status_buffer.append(status)

        # Son 10 mesajı al
        history = bridge.get_status_history(limit=10)
        assert len(history) == 10
        assert history[-1]["STATE"] == 14 % 9


class TestACKBuffer:
    """ACK buffer (ring buffer) tests"""

    @pytest.fixture
    def bridge(self):
        """ESP32Bridge instance"""
        bridge = ESP32Bridge()
        bridge.is_connected = True
        bridge.serial_connection = Mock()
        bridge.serial_connection.is_open = True
        return bridge

    def test_ack_buffer_initial_empty(self, bridge):
        """Test that ACK buffer is initially empty"""
        assert len(bridge._ack_buffer) == 0

    def test_ack_buffer_ring_behavior(self, bridge):
        """Test that ACK buffer acts as ring buffer"""
        # 30'dan fazla ACK mesajı ekle
        for i in range(35):
            ack = {"CMD": f"CMD{i}", "STATUS": "OK"}
            bridge._ack_buffer.append(ack)

        # Buffer maksimum 30 eleman tutmalı
        assert len(bridge._ack_buffer) == 30

        # İlk eklenenler kaybolmalı, son eklenenler olmalı
        assert bridge._ack_buffer[-1]["CMD"] == "CMD34"

    def test_get_ack_history(self, bridge):
        """Test get_ack_history method"""
        # ACK mesajları ekle
        for i in range(15):
            ack = {"CMD": f"CMD{i}", "STATUS": "OK"}
            bridge._ack_buffer.append(ack)

        # Son 10 mesajı al
        history = bridge.get_ack_history(limit=10)
        assert len(history) == 10
        assert history[-1]["CMD"] == "CMD14"


class TestCommandQueue:
    """Command queue tests"""

    @pytest.fixture
    def bridge(self):
        """ESP32Bridge instance"""
        bridge = ESP32Bridge()
        bridge.is_connected = True
        bridge.serial_connection = Mock()
        bridge.serial_connection.is_open = True
        bridge._send_command_bytes = Mock(return_value=True)
        return bridge

    def test_command_queue_initial_empty(self, bridge):
        """Test that command queue is initially empty"""
        assert bridge.get_pending_commands_count() == 0

    def test_command_queue_add_command(self, bridge):
        """Test adding command to queue"""
        command_bytes = [0x41, 0x01, 0x2C, 0x01, 0x10]
        bridge._command_queue.put_nowait(
            {"bytes": command_bytes, "timestamp": 0, "retry_count": 0}
        )
        assert bridge.get_pending_commands_count() == 1

    def test_command_queue_maxsize(self, bridge):
        """Test that command queue respects maxsize"""
        # Queue maxsize=50, 60 komut eklemeye çalış
        added = 0
        for i in range(60):
            try:
                bridge._command_queue.put_nowait(
                    {
                        "bytes": [0x41, 0x01, 0x2C, 0x01, 0x10],
                        "timestamp": 0,
                        "retry_count": 0,
                    }
                )
                added += 1
            except Exception:
                break

        # Maksimum 50 komut eklenebilmeli
        assert bridge.get_pending_commands_count() <= 50

    def test_clear_command_queue(self, bridge):
        """Test clearing command queue"""
        # Queue'ya komutlar ekle
        for i in range(10):
            bridge._command_queue.put_nowait(
                {
                    "bytes": [0x41, 0x01, 0x2C, 0x01, 0x10],
                    "timestamp": 0,
                    "retry_count": 0,
                }
            )

        assert bridge.get_pending_commands_count() == 10

        # Queue'yu temizle
        bridge.clear_command_queue()

        assert bridge.get_pending_commands_count() == 0


class TestCommandQueueProcessing:
    """Command queue processing tests"""

    @pytest.fixture
    def bridge(self):
        """ESP32Bridge instance"""
        bridge = ESP32Bridge()
        bridge.is_connected = True
        bridge.serial_connection = Mock()
        bridge.serial_connection.is_open = True
        bridge._send_command_bytes = Mock(return_value=True)
        return bridge

    def test_process_command_queue_success(self, bridge):
        """Test processing command queue successfully"""
        import time

        # Queue'ya komut ekle (güncel timestamp ile)
        command_bytes = [0x41, 0x01, 0x2C, 0x01, 0x10]
        bridge._command_queue.put_nowait(
            {"bytes": command_bytes, "timestamp": time.time(), "retry_count": 0}
        )

        # Queue'yu işle
        bridge._process_command_queue()

        # Komut gönderilmeli (queue_if_failed=False ile)
        bridge._send_command_bytes.assert_called_with(
            command_bytes, queue_if_failed=False
        )
        # Queue boş olmalı (komut gönderildi)
        assert bridge.get_pending_commands_count() == 0

    def test_process_command_queue_old_commands_skipped(self, bridge):
        """Test that old commands are skipped"""
        import time

        # Eski komut ekle (10 saniyeden eski)
        old_command = {
            "bytes": [0x41, 0x01, 0x2C, 0x01, 0x10],
            "timestamp": time.time() - 15.0,  # 15 saniye önce
            "retry_count": 0,
        }
        bridge._command_queue.put_nowait(old_command)

        # Yeni komut ekle
        new_command = {
            "bytes": [0x41, 0x02, 0x2C, 0x10, 0x10],
            "timestamp": time.time(),
            "retry_count": 0,
        }
        bridge._command_queue.put_nowait(new_command)

        # Queue'yu işle
        bridge._process_command_queue()

        # Sadece yeni komut gönderilmeli
        assert bridge._send_command_bytes.call_count == 1

    def test_process_command_queue_retry_limit(self, bridge):
        """Test that commands exceeding retry limit are dropped"""
        bridge._send_command_bytes.return_value = False  # Gönderme başarısız

        # Retry sayısı 3 olan komut ekle
        command = {
            "bytes": [0x41, 0x01, 0x2C, 0x01, 0x10],
            "timestamp": 0,
            "retry_count": 3,  # Maksimum retry sayısı
        }
        bridge._command_queue.put_nowait(command)

        # Queue'yu işle
        bridge._process_command_queue()

        # Komut gönderilmeye çalışılmamalı (retry limit aşıldı)
        # veya gönderilmeye çalışılıp queue'ya geri eklenmemeli
        # Queue boş olmalı (komut atıldı)
        assert bridge.get_pending_commands_count() == 0


class TestBufferOverflowProtection:
    """Buffer overflow protection tests"""

    @pytest.fixture
    def bridge(self):
        """ESP32Bridge instance"""
        bridge = ESP32Bridge()
        bridge.is_connected = True
        bridge.serial_connection = Mock()
        bridge.serial_connection.is_open = True
        bridge.serial_connection.in_waiting = 0
        bridge.serial_connection.readline = Mock()
        bridge.serial_connection.reset_input_buffer = Mock()
        return bridge

    def test_buffer_overflow_protection_important_messages(self, bridge):
        """Test that important messages are read before buffer clear"""
        # Buffer overflow durumunu simüle et (max_lines=5'ten fazla)
        lines = []
        for i in range(7):
            if i < 5:
                lines.append(f"<STAT;STATE={i};>\n")
            else:
                lines.append(f"<ACK;CMD=CMD{i};STATUS=OK;>\n")

        bridge.serial_connection.in_waiting = sum(len(line) for line in lines)
        bridge.serial_connection.readline.side_effect = [
            line.encode("utf-8") for line in lines
        ]

        # Status mesajlarını oku
        bridge._read_status_messages()

        # Önemli mesajlar (STAT, ACK) okunmuş olmalı
        # Buffer temizlenmeden önce son mesaj da okunmaya çalışılmalı
        assert bridge.serial_connection.reset_input_buffer.called
