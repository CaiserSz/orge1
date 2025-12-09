"""
Concurrency Edge Cases Tests
Created: 2025-12-10 00:25:00
Last Modified: 2025-12-10 09:00:00
Version: 1.0.0
Description: Concurrency edge case testleri
"""

import sys
import threading
import logging
from unittest.mock import Mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.event_detector import EventDetector
from api.logging_config import thread_safe_log


class TestConcurrencyEdgeCases:
    """Concurrency edge case testleri"""

    def test_event_detector_concurrent_state_access(self):
        """Event detector - eşzamanlı state erişimi"""
        mock_bridge = Mock()

        def bridge_getter():
            return mock_bridge

        detector = EventDetector(bridge_getter)

        states_read = []

        def read_state():
            current = detector.get_current_state()
            previous = detector.get_previous_state()
            states_read.append((current, previous))

        def write_state():
            detector._check_state_transition(1, {"STATE": 1})
            detector._check_state_transition(2, {"STATE": 2})

        # Okuma ve yazma thread'leri
        read_threads = [threading.Thread(target=read_state) for _ in range(5)]
        write_threads = [threading.Thread(target=write_state) for _ in range(2)]

        for thread in write_threads + read_threads:
            thread.start()

        for thread in write_threads + read_threads:
            thread.join()

        # Tüm thread'ler başarılı olmalı
        assert len(states_read) == 5

    def test_logging_concurrent_access(self):
        """Logging - eşzamanlı erişim"""
        logger = logging.getLogger("test_concurrent_logging_final")
        logger.setLevel(logging.DEBUG)

        # Handler yoksa ekle (test için)
        if not logger.handlers:
            handler = logging.NullHandler()  # NullHandler kullan (output yok)
            handler.setLevel(logging.DEBUG)
            logger.addHandler(handler)

        errors = []

        def log_message(msg_id):
            try:
                thread_safe_log(logger, 20, f"Message {msg_id}", id=msg_id)
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(10):  # Daha az thread ile test et
            thread = threading.Thread(target=log_message, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join(timeout=1.0)  # Timeout ekle

        # Hata oluşmamalı
        assert len(errors) == 0
