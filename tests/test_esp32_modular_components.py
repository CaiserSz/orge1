"""
ESP32 modüler bileşen testleri
Created: 2025-12-12 12:45:00
Last Modified: 2025-12-12 12:45:00
Description: CommandSender, MessageProcessor ve StatusInspector için hızlı kontroller
"""

import queue
import threading
import time
from types import SimpleNamespace

from api.event_detector import ESP32State
from esp32.command_sender import CommandSender
from esp32.monitor_worker import MessageProcessor
from esp32.protocol_handler import parse_status_message
from esp32.status_parser import StatusInspector


class FakeSerial:
    """Minimal seri port taklidi."""

    def __init__(self):
        self.is_open = True
        self.written = []

    def write(self, data):
        self.written.append(data)

    def flush(self):
        return None


def test_protocol_handler_maps_state_name():
    status = parse_status_message("<STAT;STATE=5;>")
    assert status is not None
    assert status["STATE_NAME"] == "CHARGING"


def test_command_sender_rejects_invalid_amperage():
    serial_connection = FakeSerial()
    sender = CommandSender(
        serial_connection=serial_connection,
        serial_lock=threading.Lock(),
        ack_queue=queue.Queue(),
        ack_buffer=[],
        protocol_data={},
        is_connected_ref=lambda: True,
        command_queue=queue.Queue(),
    )

    result = sender.send_current_set(amperage=3)
    assert result is False
    assert serial_connection.written == []


def test_command_sender_wait_for_ack_times_out():
    serial_connection = FakeSerial()
    sender = CommandSender(
        serial_connection=serial_connection,
        serial_lock=threading.Lock(),
        ack_queue=queue.Queue(),
        ack_buffer=[],
        protocol_data={},
        is_connected_ref=lambda: True,
        command_queue=queue.Queue(),
    )

    ack = sender.wait_for_ack(expected_cmd="AUTH", timeout=0.05)
    assert ack is None


def test_message_processor_updates_status_and_ack(monkeypatch):
    statuses = []
    acks = []

    # Warning loglarını bastır
    monkeypatch.setattr(
        "api.logging_config.esp32_logger",
        SimpleNamespace(debug=lambda *_, **__: None),  # type: ignore
    )

    processor = MessageProcessor(
        status_update_callback=lambda s: statuses.append(s),
        ack_append_callback=lambda a: acks.append(a),
        status_inspector=StatusInspector(),
    )

    processor.process_line("<STAT;STATE=1;>")
    processor.process_line("<ACK;CMD=AUTH;STATUS=OK;>")

    assert statuses and statuses[0]["STATE_NAME"] == "IDLE"
    assert acks and acks[0]["CMD"] == "AUTH"


def test_status_inspector_flags_zero_current(monkeypatch):
    incidents = []
    monkeypatch.setattr(
        "esp32.status_parser.log_incident",
        lambda **kwargs: incidents.append(kwargs),
    )

    inspector = StatusInspector()
    inspector._zero_current_threshold = 0.0  # Hızlı tetikleme için
    inspector._last_current_draw_ts = time.time() - 1.0

    status = {"STATE": ESP32State.CHARGING.value, "CABLE": 0}
    inspector.inspect_status_for_incidents(status)

    assert incidents, "Zero-current durumu için incident üretilmeli"
