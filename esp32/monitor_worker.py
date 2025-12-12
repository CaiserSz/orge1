"""
ESP32 Monitor Worker Module
Created: 2025-12-12 12:30:00
Last Modified: 2025-12-12 12:55:00
Version: 1.0.0
Description: ESP32 bridge için monitor loop, seri okuma ve mesaj işleme
"""

import threading
import time
from typing import Callable, Optional

import serial  # type: ignore

from api.logging_config import esp32_logger, log_esp32_message
from esp32.protocol_handler import parse_ack_message, parse_status_message


class MessageProcessor:
    """
    Status ve ACK mesajlarını işleyen yardımcı sınıf.
    """

    def __init__(
        self,
        status_update_callback: Callable,
        ack_append_callback: Callable,
        status_inspector,
    ):
        self._status_update_callback = status_update_callback
        self._ack_append_callback = ack_append_callback
        self._status_inspector = status_inspector

    def process_line(self, line: str) -> None:
        """Tek bir mesaj satırını işle."""
        if "<STAT;" in line:
            status = parse_status_message(line)
            if status:
                self._status_update_callback(status)
                esp32_logger.debug(f"Status güncellendi: {status.get('STATE', 'N/A')}")
                log_esp32_message("status", "rx", data=status)
                self._status_inspector.inspect_status_for_incidents(status)
        elif "<ACK;" in line:
            ack = parse_ack_message(line)
            if ack:
                esp32_logger.debug(
                    f"ACK alındı: {ack.get('CMD', 'N/A')} - {ack.get('STATUS', 'N/A')}"
                )
                log_esp32_message("ack", "rx", data=ack)
                self._ack_append_callback(ack)


class MonitorWorker:
    """
    ESP32 seri bağlantısını izleyen ve mesajları işleyen worker.
    """

    def __init__(
        self,
        connection_manager,
        serial_lock: threading.Lock,
        command_queue,
        command_sender_ref: Callable[[], Optional[object]],
        message_processor: MessageProcessor,
        is_connected_ref: Callable[[], bool],
        set_connected_callback: Callable[[bool], None],
        reconnect_callback: Callable[[], bool],
    ):
        self._connection_manager = connection_manager
        self._serial_lock = serial_lock
        self._command_queue = command_queue
        self._command_sender_ref = command_sender_ref
        self._message_processor = message_processor
        self._is_connected_ref = is_connected_ref
        self._set_connected_callback = set_connected_callback
        self._reconnect_callback = reconnect_callback

        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_running = False

    def start(self) -> None:
        """Monitor thread'ini başlat."""
        if self._monitor_running:
            return
        self._monitor_running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop(self) -> None:
        """Monitor thread'ini durdur."""
        self._monitor_running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)

    def _monitor_loop(self) -> None:
        """Durum izleme döngüsü."""
        consecutive_errors = 0
        max_consecutive_errors = 10

        while self._monitor_running:
            try:
                if self._is_connected_ref():
                    self._read_status_messages()
                    command_sender = self._command_sender_ref()
                    if command_sender and not self._command_queue.empty():
                        command_sender.process_command_queue()
                    consecutive_errors = 0
                elif self._connection_manager._reconnect_enabled:
                    if consecutive_errors == 0:
                        esp32_logger.info(
                            "Monitor loop: Bağlantı yok, reconnection deneniyor"
                        )
                        self._reconnect_callback()
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        esp32_logger.warning(
                            f"Monitor loop: {max_consecutive_errors} ardışık hata, reconnection duraklatılıyor"
                        )
                        wait_time = min(
                            30 * (2 ** (consecutive_errors - max_consecutive_errors)),
                            300,
                        )
                        esp32_logger.info(
                            f"Monitor loop: {wait_time:.1f} saniye bekleniyor"
                        )
                        time.sleep(wait_time)
                        consecutive_errors = 0
                time.sleep(0.1)
            except Exception as e:
                consecutive_errors += 1
                esp32_logger.error(f"Monitor loop error: {e}", exc_info=True)
                time.sleep(0.5)

    def _read_status_messages(self) -> None:
        """Seri porttan durum mesajlarını oku ve işle."""
        serial_connection = self._connection_manager.serial_connection

        if not serial_connection or not serial_connection.is_open:
            if self._connection_manager._reconnect_enabled and self._is_connected_ref():
                esp32_logger.warning(
                    "Serial port bağlantısı kopmuş, reconnection deneniyor"
                )
                self._set_connected_callback(False)
                self._reconnect_callback()
            return

        try:
            with self._serial_lock:
                lines_read = 0
                max_lines = 5
                read_lines = []

                while serial_connection.in_waiting > 0 and lines_read < max_lines:
                    line = (
                        serial_connection.readline()
                        .decode("utf-8", errors="ignore")
                        .strip()
                    )
                    lines_read += 1
                    if line:
                        read_lines.append(line)

            if lines_read >= max_lines:
                remaining_bytes = serial_connection.in_waiting
                if remaining_bytes > 0:
                    esp32_logger.warning(
                        f"Buffer overflow riski: {lines_read} satır okundu, "
                        f"{remaining_bytes} byte daha var. Buffer temizleniyor."
                    )
                    try:
                        remaining_line = (
                            serial_connection.readline()
                            .decode("utf-8", errors="ignore")
                            .strip()
                        )
                        if remaining_line:
                            self._message_processor.process_line(remaining_line)
                    except Exception:
                        pass
                serial_connection.reset_input_buffer()

            for line in read_lines:
                self._message_processor.process_line(line)

        except serial.SerialException as e:
            error_msg = str(e)
            esp32_logger.error(f"Serial port hatası: {error_msg}")
            self._set_connected_callback(False)

            if (
                "device disconnected" in error_msg.lower()
                or "multiple access" in error_msg.lower()
                or "device or resource busy" in error_msg.lower()
            ):
                if self._connection_manager._reconnect_enabled:
                    esp32_logger.warning(
                        "Serial port bağlantısı kopmuş, reconnection deneniyor"
                    )
                    self._reconnect_callback()
            elif "timeout" in error_msg.lower():
                esp32_logger.warning(f"Serial port timeout: {error_msg}")
                serial_connection = self._connection_manager.serial_connection
                if serial_connection and not serial_connection.is_open:
                    if self._connection_manager._reconnect_enabled:
                        self._reconnect_callback()
            else:
                esp32_logger.error(f"Status okuma hatası: {e}", exc_info=True)
                serial_connection = self._connection_manager.serial_connection
                if serial_connection and not serial_connection.is_open:
                    if self._connection_manager._reconnect_enabled:
                        self._reconnect_callback()
        except Exception as e:
            esp32_logger.error(f"Status okuma hatası: {e}", exc_info=True)
