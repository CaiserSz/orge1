"""
ESP32-RPi Bridge Module
Created: 2025-12-08
Last Modified: 2025-12-25 02:28:00
Version: 2.0.3
Description: ESP32 ile USB seri port üzerinden iletişim köprüsü (Backward-compatible facade)
"""

import json
import os
import queue
import sys
import threading
import time
from collections import deque
from datetime import datetime
from typing import Any, Dict, Optional

import serial  # type: ignore

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from api.logging_config import esp32_logger
from esp32.command_sender import CommandSender
from esp32.connection_manager import ConnectionManager
from esp32.monitor_worker import MessageProcessor, MonitorWorker
from esp32.protocol_handler import (
    BAUDRATE,
    PROTOCOL_FOOTER,
    PROTOCOL_HEADER,
    PROTOCOL_SEPARATOR,
    STATUS_UPDATE_INTERVAL,
    parse_ack_message,
    parse_status_message,
)
from esp32.status_parser import StatusInspector

__all__ = [
    "ESP32Bridge",
    "get_esp32_bridge",
    "BAUDRATE",
    "PROTOCOL_HEADER",
    "PROTOCOL_SEPARATOR",
    "PROTOCOL_FOOTER",
    "STATUS_UPDATE_INTERVAL",
]


class ESP32Bridge:
    """ESP32 ile USB seri port üzerinden iletişim köprüsü (Facade)."""

    def __init__(self, port: Optional[str] = None, baudrate: int = BAUDRATE):
        """ESP32 bridge başlatıcı."""
        self.port = port
        self.baudrate = baudrate

        self._reconnect_enabled = True

        self.protocol_data = self._load_protocol()

        self.last_status: Optional[Dict[str, Any]] = None
        self.status_lock = threading.Lock()
        self._status_buffer = deque(maxlen=50)  # Son 50 status mesajı

        self._ack_queue = queue.Queue(maxsize=20)  # ACK mesajları için queue
        self._ack_buffer = deque(maxlen=30)  # Son 30 ACK mesajı
        self._ack_lock = threading.Lock()

        self._command_queue = queue.Queue(maxsize=50)
        self._serial_lock = threading.Lock()  # Serial port okuma/yazma için lock

        self._connection_manager = ConnectionManager(
            port=port,
            baudrate=baudrate,
            reconnect_enabled=True,
            max_reconnect_attempts=3,
            reconnect_delay=5.0,
        )

        self._status_inspector = StatusInspector()

        self._command_sender: Optional[CommandSender] = None

        self._message_processor = MessageProcessor(
            status_update_callback=self._update_status,
            ack_append_callback=self._append_ack,
            status_inspector=self._status_inspector,
        )
        self._monitor_worker = MonitorWorker(
            connection_manager=self._connection_manager,
            serial_lock=self._serial_lock,
            command_queue=self._command_queue,
            command_sender_ref=lambda: self._command_sender,
            message_processor=self._message_processor,
            is_connected_ref=lambda: self.is_connected,
            set_connected_callback=self._set_connected_state,
            reconnect_callback=self.reconnect,
        )

        self.is_connected = False

    def _load_protocol(self) -> Dict[str, Any]:
        """protocol.json dosyasını yükle."""
        try:
            protocol_path = os.path.join(os.path.dirname(__file__), "protocol.json")
            with open(protocol_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            esp32_logger.error(f"Protocol yükleme hatası: {e}", exc_info=True)
            return {}

    def _start_monitoring(self) -> None:
        self._monitor_worker.start()

    def _stop_monitoring(self) -> None:
        self._monitor_worker.stop()

    # Backward-compatible parsers (testler bu method isimlerini çağırıyor)
    _parse_status_message = staticmethod(parse_status_message)
    _parse_ack_message = staticmethod(parse_ack_message)

    def _read_status_messages(self) -> None:
        self._monitor_worker._read_status_messages()

    def connect(self) -> bool:
        """ESP32'ye bağlan."""
        try:
            if self.serial_connection and getattr(
                self.serial_connection, "is_open", False
            ):
                self.disconnect()
        except Exception:
            pass

        port = self.port or self.find_esp32_port()
        if not port:
            esp32_logger.warning("ESP32 portu bulunamadı")
            self.is_connected = False
            return False

        try:
            serial_instance = serial.Serial(
                port=port,
                baudrate=self.baudrate,
                timeout=1.0,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
            )
            time.sleep(0.5)

            self._reconnect_enabled = True
            self._connection_manager._reconnect_enabled = True
            self._connection_manager.port = port
            self._connection_manager.serial_connection = serial_instance
            self._connection_manager.is_connected = True

            self.serial_connection = serial_instance
            self.is_connected = True

            self._command_sender = CommandSender(
                serial_connection=self.serial_connection,
                serial_lock=self._serial_lock,
                ack_queue=self._ack_queue,
                ack_buffer=self._ack_buffer,
                protocol_data=self.protocol_data,
                is_connected_ref=lambda: self.is_connected,
                command_queue=self._command_queue,
            )

            self._start_monitoring()
            self._process_command_queue()
            return True
        except serial.SerialException as e:
            esp32_logger.error(f"ESP32 bağlantı hatası: {e}", exc_info=True)
            self.is_connected = False
            return False
        except Exception as e:
            esp32_logger.error(f"ESP32 bağlantı hatası: {e}", exc_info=True)
            self.is_connected = False
            return False

    def disconnect(self):
        self._reconnect_enabled = False
        self._connection_manager._reconnect_enabled = False
        self._stop_monitoring()
        self._connection_manager.disconnect()
        self.is_connected = False
        self.serial_connection = None
        self._command_sender = None
        self._reset_buffers(clear_command_queue=True)

    def reconnect(
        self, max_retries: Optional[int] = None, retry_delay: Optional[float] = None
    ) -> bool:
        """ESP32 bağlantısını yeniden kur (backward-compatible)."""
        if not self._reconnect_enabled:
            return False
        return self.connect()

    def find_esp32_port(self) -> Optional[str]:
        return self._connection_manager.find_esp32_port()

    def _get_compat_sender(self) -> CommandSender:
        """Test uyumluluğu için CommandSender wrapper."""
        sender = self._command_sender or CommandSender(
            serial_connection=self.serial_connection,
            serial_lock=self._serial_lock,
            ack_queue=self._ack_queue,
            ack_buffer=self._ack_buffer,
            protocol_data=self.protocol_data,
            is_connected_ref=lambda: self.is_connected,
            command_queue=self._command_queue,
        )

        def _compat_send_command_bytes(command_bytes, queue_if_failed=True) -> bool:
            if queue_if_failed:
                return self._send_command_bytes(command_bytes)
            return self._send_command_bytes(command_bytes, queue_if_failed=False)

        sender.send_command_bytes = _compat_send_command_bytes  # type: ignore[method-assign]
        sender.wait_for_ack = (  # type: ignore[method-assign]
            lambda expected_cmd, timeout=1.0: self._wait_for_ack(
                expected_cmd, timeout=timeout
            )
        )
        return sender

    def send_status_request(self) -> bool:
        """Status komutu gönder."""
        return self._get_compat_sender().send_status_request()

    def send_authorization(
        self, wait_for_ack: bool = True, timeout: float = 1.0, max_retries: int = 1
    ) -> bool:
        """Authorization komutu gönder."""
        return self._get_compat_sender().send_authorization(
            wait_for_ack=wait_for_ack, timeout=timeout, max_retries=max_retries
        )

    def send_current_set(
        self,
        amperage: int,
        wait_for_ack: bool = True,
        timeout: float = 1.0,
        max_retries: int = 1,
    ) -> bool:
        """Akım set komutu gönder (6-32A)."""
        return self._get_compat_sender().send_current_set(
            amperage=amperage,
            wait_for_ack=wait_for_ack,
            timeout=timeout,
            max_retries=max_retries,
        )

    def send_charge_stop(
        self, wait_for_ack: bool = False, timeout: float = 1.0
    ) -> bool:
        """Şarj durdurma komutu gönder."""
        return self._get_compat_sender().send_charge_stop(
            wait_for_ack=wait_for_ack, timeout=timeout
        )

    def get_pending_commands_count(self) -> int:
        """Bekleyen komut sayısını al."""
        return self._command_queue.qsize()

    def clear_command_queue(self):
        """Komut queue'sunu temizle"""
        while not self._command_queue.empty():
            try:
                self._command_queue.get_nowait()
            except queue.Empty:
                break
        esp32_logger.info("Komut queue temizlendi")

    def _process_command_queue(self) -> None:
        """Queue'daki komutları gönder (testler bu metodu bekliyor)."""
        self._get_compat_sender().process_command_queue()

    def get_status(self, max_age_seconds: float = 10.0) -> Optional[Dict[str, Any]]:
        """Son durum bilgisini al."""
        with self.status_lock:
            if not self.last_status:
                return None

            # Timestamp kontrolü
            try:
                timestamp_str = self.last_status.get("timestamp")
                if timestamp_str:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    age_seconds = (datetime.now() - timestamp).total_seconds()
                    if age_seconds > max_age_seconds:
                        esp32_logger.warning(
                            f"Status verisi çok eski: {age_seconds:.1f} saniye (max: {max_age_seconds}s)"
                        )
                        return None
            except (ValueError, TypeError) as e:
                esp32_logger.warning(f"Timestamp parse hatası: {e}")

            return self.last_status.copy()

    def get_status_sync(self, timeout: float = 2.0) -> Optional[Dict[str, Any]]:
        """Status komutu gönder ve yanıt bekle (senkron)."""
        if not self.is_connected or not self.serial_connection:
            esp32_logger.warning("get_status_sync: ESP32 bağlantısı yok")
            return None

        if not self.send_status_request():
            esp32_logger.warning("get_status_sync: Status komutu gönderilemedi")
            return None

        start_time = time.time()
        check_interval = 0.05  # 50ms check interval

        while time.time() - start_time < timeout:
            if not self.serial_connection or not self.serial_connection.is_open:
                esp32_logger.warning("get_status_sync: Bağlantı kopmuş")
                self.is_connected = False
                return None

            status = self.get_status(max_age_seconds=timeout)
            if status:
                return status
            time.sleep(check_interval)

        esp32_logger.warning(
            f"get_status_sync: Timeout ({timeout}s) - status alınamadı"
        )
        return None

    def get_status_history(self, limit: int = 10) -> list:
        """Status mesaj geçmişini al."""
        with self.status_lock:
            return list(self._status_buffer)[-limit:]

    def get_ack_history(self, limit: int = 10) -> list:
        """ACK mesaj geçmişini al."""
        with self._ack_lock:
            return list(self._ack_buffer)[-limit:]

    def _wait_for_ack(
        self, expected_cmd: str, timeout: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """Belirli bir komut için ACK mesajını bekle (queue tabanlı)."""
        if (
            not self.is_connected
            or not self.serial_connection
            or not getattr(self.serial_connection, "is_open", False)
        ):
            return None

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                ack = self._ack_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if ack and ack.get("CMD") == expected_cmd:
                return ack
        return None

    def _send_command_bytes(
        self, command_bytes: list, queue_if_failed: bool = True
    ) -> bool:
        """ESP32'ye 5 byte'lık komutu gönder (thread-safe)."""
        if (
            not self.is_connected
            or not self.serial_connection
            or not getattr(self.serial_connection, "is_open", False)
        ):
            if queue_if_failed:
                try:
                    self._command_queue.put_nowait(
                        {
                            "bytes": command_bytes,
                            "timestamp": time.time(),
                            "retry_count": 0,
                        }
                    )
                except queue.Full:
                    pass
            return False

        if len(command_bytes) != 5:
            return False

        try:
            with self._serial_lock:
                if not getattr(self.serial_connection, "is_open", False):
                    return False
                self.serial_connection.write(bytes(command_bytes))
                self.serial_connection.flush()
                return bool(getattr(self.serial_connection, "is_open", True))
        except Exception:
            if queue_if_failed:
                try:
                    self._command_queue.put_nowait(
                        {
                            "bytes": command_bytes,
                            "timestamp": time.time(),
                            "retry_count": 0,
                        }
                    )
                except queue.Full:
                    pass
            return False

    def _set_connected_state(self, is_connected: bool) -> None:
        """Bağlantı durumunu güncelle (monitor worker kullanır)."""
        self.is_connected = is_connected

    def _update_status(self, status: Dict[str, Any]) -> None:
        """Status bilgisini güvenli şekilde güncelle."""
        with self.status_lock:
            self.last_status = status
            self._status_buffer.append(status)

    def _append_ack(self, ack: Dict[str, Any]) -> None:
        with self._ack_lock:
            self._ack_buffer.append(ack)
        try:
            self._ack_queue.put_nowait(ack)
        except queue.Full:
            try:
                self._ack_queue.get_nowait()
                self._ack_queue.put_nowait(ack)
                esp32_logger.warning("ACK queue dolu, eski ACK atıldı")
            except queue.Empty:
                pass

    def _reset_buffers(self, clear_command_queue: bool = False) -> None:
        with self.status_lock:
            self.last_status = None
            self._status_buffer.clear()
        with self._ack_lock:
            self._ack_buffer.clear()
            while not self._ack_queue.empty():
                try:
                    self._ack_queue.get_nowait()
                except queue.Empty:
                    break
        if clear_command_queue:
            self.clear_command_queue()

    @property
    def serial_connection(self):
        """Serial connection property"""
        return self._connection_manager.serial_connection

    @serial_connection.setter
    def serial_connection(self, value):
        """Serial connection setter"""
        self._connection_manager.serial_connection = value


_esp32_bridge_instance: Optional[ESP32Bridge] = None
_bridge_lock = threading.Lock()


def get_esp32_bridge() -> ESP32Bridge:
    """ESP32 bridge singleton instance'ı al (thread-safe)."""
    global _esp32_bridge_instance

    # Pytest ortamında gerçek seri bağlantı açma (ama singleton semantiğini koru)
    if os.getenv("PYTEST_CURRENT_TEST") is not None:
        if _esp32_bridge_instance is not None:
            return _esp32_bridge_instance
        with _bridge_lock:
            if _esp32_bridge_instance is None:
                instance = ESP32Bridge(port="/dev/null", baudrate=BAUDRATE)
                instance.is_connected = True
                _esp32_bridge_instance = instance
        return _esp32_bridge_instance

    # İlk kontrol (lock almadan - performans için)
    if _esp32_bridge_instance is not None:
        return _esp32_bridge_instance

    # İkinci kontrol (lock ile - thread-safety için)
    with _bridge_lock:
        if _esp32_bridge_instance is None:
            # Not: ESP32 port/baudrate ayarları `api.config` üzerinden yönetilir (USB/GPIO UART).
            try:
                from api.config import (
                    config,
                )  # Local import: olası import cycle riskini azaltır

                port = getattr(config, "ESP32_PORT", None)
                baudrate = int(getattr(config, "ESP32_BAUDRATE", BAUDRATE))
            except Exception:
                port = None
                baudrate = BAUDRATE
            instance = ESP32Bridge(port=port, baudrate=baudrate)
            if not instance.connect():
                esp32_logger.error("ESP32 bağlantısı kurulamadı")
                raise RuntimeError("ESP32 bağlantısı kurulamadı")
            _esp32_bridge_instance = instance
            esp32_logger.info("ESP32 bridge singleton instance oluşturuldu")
    return _esp32_bridge_instance
