"""
ESP32-RPi Bridge Module
Created: 2025-12-08
Last Modified: 2025-12-12 11:00:00
Version: 2.0.0
Description: ESP32 ile USB seri port üzerinden iletişim köprüsü (Refactored - Modüler yapı)
"""

import os
import queue
import sys
import threading
import time
from collections import deque
from datetime import datetime
from typing import Any, Dict, Optional

import serial

# Logging modülünü import et
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from api.logging_config import esp32_logger, log_esp32_message
from esp32.command_sender import CommandSender

# Yeni modülleri import et
from esp32.connection_manager import ConnectionManager
from esp32.protocol_handler import (
    BAUDRATE,
    PROTOCOL_FOOTER,
    PROTOCOL_HEADER,
    PROTOCOL_SEPARATOR,
    STATUS_UPDATE_INTERVAL,
    load_protocol,
    parse_ack_message,
    parse_status_message,
)
from esp32.status_parser import StatusInspector

# Backward compatibility için constants export et
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
    """
    ESP32 ile USB seri port üzerinden iletişim köprüsü (Facade Pattern)

    Bu sınıf, modüler yapıdaki alt modülleri koordine eder ve tek bir
    unified interface sağlar.
    """

    def __init__(self, port: Optional[str] = None, baudrate: int = BAUDRATE):
        """
        ESP32 Bridge başlatıcı

        Args:
            port: Seri port adı (None ise otomatik bulunur)
            baudrate: Baudrate (varsayılan: 115200)
        """
        self.port = port
        self.baudrate = baudrate

        # Protokol verilerini yükle
        self.protocol_data = load_protocol()

        # Status yönetimi
        self.last_status: Optional[Dict[str, Any]] = None
        self.status_lock = threading.Lock()
        self._status_buffer = deque(maxlen=50)  # Son 50 status mesajı

        # ACK yönetimi
        self._ack_queue = queue.Queue(maxsize=20)  # ACK mesajları için queue
        self._ack_buffer = deque(maxlen=30)  # Son 30 ACK mesajı

        # Komut queue'su
        self._command_queue = queue.Queue(maxsize=50)
        self._serial_lock = threading.Lock()  # Serial port okuma/yazma için lock

        # Connection manager'ı initialize et
        self._connection_manager = ConnectionManager(
            port=port,
            baudrate=baudrate,
            reconnect_enabled=True,
            max_reconnect_attempts=3,
            reconnect_delay=5.0,
        )

        # Status inspector'ı initialize et
        self._status_inspector = StatusInspector()

        # Command sender'ı initialize et (bağlantı kurulunca güncellenecek)
        self._command_sender: Optional[CommandSender] = None

        # Monitor thread yönetimi
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_running = False

        # Connection state (connection_manager ile senkronize)
        self.is_connected = False

    def connect(self) -> bool:
        """
        ESP32'ye bağlan

        Returns:
            Başarı durumu
        """
        success = self._connection_manager.connect()
        if success:
            self.serial_connection = self._connection_manager.serial_connection
            self.is_connected = self._connection_manager.is_connected

            # Command sender'ı initialize et
            self._command_sender = CommandSender(
                serial_connection=self.serial_connection,
                serial_lock=self._serial_lock,
                ack_queue=self._ack_queue,
                ack_buffer=self._ack_buffer,
                protocol_data=self.protocol_data,
                is_connected_ref=lambda: self.is_connected,
                command_queue=self._command_queue,
            )

            # Durum izleme thread'ini başlat
            self._start_monitoring()

            # Queue'daki bekleyen komutları gönder
            if self._command_sender:
                self._command_sender.process_command_queue()

        return success

    def disconnect(self):
        """ESP32 bağlantısını kapat"""
        self._stop_monitoring()
        self._connection_manager.disconnect()
        self.is_connected = self._connection_manager.is_connected
        self.serial_connection = None
        self._command_sender = None

    def reconnect(
        self, max_retries: Optional[int] = None, retry_delay: Optional[float] = None
    ) -> bool:
        """
        ESP32 bağlantısını yeniden kur

        Args:
            max_retries: Maksimum yeniden deneme sayısı
            retry_delay: İlk yeniden deneme aralığı (saniye)

        Returns:
            Başarı durumu
        """
        success = self._connection_manager.reconnect(
            max_retries=max_retries, retry_delay=retry_delay
        )
        if success:
            self.serial_connection = self._connection_manager.serial_connection
            self.is_connected = self._connection_manager.is_connected

            # Command sender'ı yeniden initialize et
            if self.serial_connection:
                self._command_sender = CommandSender(
                    serial_connection=self.serial_connection,
                    serial_lock=self._serial_lock,
                    ack_queue=self._ack_queue,
                    ack_buffer=self._ack_buffer,
                    protocol_data=self.protocol_data,
                    is_connected_ref=lambda: self.is_connected,
                    command_queue=self._command_queue,
                )

        return success

    def find_esp32_port(self) -> Optional[str]:
        """
        ESP32 seri portunu otomatik bul

        Returns:
            Port adı veya None
        """
        return self._connection_manager.find_esp32_port()

    # Command methods - CommandSender'a delegate et
    def send_status_request(self) -> bool:
        """Status komutu gönder"""
        if not self._command_sender:
            return False
        return self._command_sender.send_status_request()

    def send_authorization(
        self, wait_for_ack: bool = True, timeout: float = 1.0, max_retries: int = 1
    ) -> bool:
        """
        Authorization komutu gönder (şarj başlatma)

        Args:
            wait_for_ack: ACK mesajını bekle
            timeout: ACK bekleme timeout süresi (saniye)
            max_retries: Maksimum retry sayısı

        Returns:
            Başarı durumu
        """
        if not self._command_sender:
            return False
        return self._command_sender.send_authorization(
            wait_for_ack=wait_for_ack, timeout=timeout, max_retries=max_retries
        )

    def send_current_set(
        self,
        amperage: int,
        wait_for_ack: bool = True,
        timeout: float = 1.0,
        max_retries: int = 1,
    ) -> bool:
        """
        Akım set komutu gönder

        Args:
            amperage: Amper değeri (6-32 aralığında)
            wait_for_ack: ACK mesajını bekle
            timeout: ACK bekleme timeout süresi (saniye)
            max_retries: Maksimum retry sayısı

        Returns:
            Başarı durumu
        """
        if not self._command_sender:
            return False
        return self._command_sender.send_current_set(
            amperage=amperage,
            wait_for_ack=wait_for_ack,
            timeout=timeout,
            max_retries=max_retries,
        )

    def send_charge_stop(
        self, wait_for_ack: bool = False, timeout: float = 1.0
    ) -> bool:
        """
        Şarj durdurma komutu gönder

        Args:
            wait_for_ack: ACK mesajını bekle
            timeout: ACK bekleme timeout süresi (saniye)

        Returns:
            Başarı durumu
        """
        if not self._command_sender:
            return False
        return self._command_sender.send_charge_stop(
            wait_for_ack=wait_for_ack, timeout=timeout
        )

    def get_pending_commands_count(self) -> int:
        """
        Bekleyen komut sayısını al

        Returns:
            Queue'daki komut sayısı
        """
        return self._command_queue.qsize()

    def clear_command_queue(self):
        """Komut queue'sunu temizle"""
        while not self._command_queue.empty():
            try:
                self._command_queue.get_nowait()
            except queue.Empty:
                break
        esp32_logger.info("Komut queue temizlendi")

    # Status methods
    def get_status(self, max_age_seconds: float = 10.0) -> Optional[Dict[str, Any]]:
        """
        Son durum bilgisini al

        Args:
            max_age_seconds: Maksimum veri yaşı (saniye)

        Returns:
            Durum dict'i veya None
        """
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
        """
        Status komutu gönder ve yanıt bekle (senkron)

        Args:
            timeout: Timeout süresi (saniye)

        Returns:
            Durum dict'i veya None
        """
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
        """
        Status mesaj geçmişini al

        Args:
            limit: Maksimum mesaj sayısı

        Returns:
            Status mesaj listesi (en yeni önce)
        """
        with self.status_lock:
            return list(self._status_buffer)[-limit:]

    def get_ack_history(self, limit: int = 10) -> list:
        """
        ACK mesaj geçmişini al

        Args:
            limit: Maksimum mesaj sayısı

        Returns:
            ACK mesaj listesi (en yeni önce)
        """
        return list(self._ack_buffer)[-limit:]

    # Monitor loop methods
    def _start_monitoring(self):
        """Durum izleme thread'ini başlat"""
        if self._monitor_running:
            return

        self._monitor_running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def _stop_monitoring(self):
        """Durum izleme thread'ini durdur"""
        self._monitor_running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)

    def _read_status_messages(self):
        """
        Seri porttan durum mesajlarını oku ve işle
        """
        if not self.serial_connection or not self.serial_connection.is_open:
            # Bağlantı yoksa reconnection dene
            if self._connection_manager._reconnect_enabled and self.is_connected:
                esp32_logger.warning(
                    "Serial port bağlantısı kopmuş, reconnection deneniyor"
                )
                self.is_connected = False
                self.reconnect()
            return

        try:
            # Thread-safe okuma
            with self._serial_lock:
                lines_read = 0
                max_lines = 5
                read_lines = []

                while self.serial_connection.in_waiting > 0 and lines_read < max_lines:
                    line = (
                        self.serial_connection.readline()
                        .decode("utf-8", errors="ignore")
                        .strip()
                    )
                    lines_read += 1
                    if line:
                        read_lines.append(line)

            # Buffer overflow koruması
            if lines_read >= max_lines:
                remaining_bytes = self.serial_connection.in_waiting
                if remaining_bytes > 0:
                    esp32_logger.warning(
                        f"Buffer overflow riski: {lines_read} satır okundu, "
                        f"{remaining_bytes} byte daha var. Buffer temizleniyor."
                    )
                    try:
                        remaining_line = (
                            self.serial_connection.readline()
                            .decode("utf-8", errors="ignore")
                            .strip()
                        )
                        if remaining_line:
                            self._process_message(remaining_line)
                    except Exception:
                        pass
                self.serial_connection.reset_input_buffer()

            # Mesajları işle
            for line in read_lines:
                self._process_message(line)

        except serial.SerialException as e:
            error_msg = str(e)
            esp32_logger.error(f"Serial port hatası: {error_msg}")

            if (
                "device disconnected" in error_msg.lower()
                or "multiple access" in error_msg.lower()
                or "device or resource busy" in error_msg.lower()
            ):
                if self._connection_manager._reconnect_enabled and self.is_connected:
                    esp32_logger.warning(
                        "Serial port bağlantısı kopmuş, reconnection deneniyor"
                    )
                    self.is_connected = False
                    self.reconnect()
            elif "timeout" in error_msg.lower():
                esp32_logger.warning(f"Serial port timeout: {error_msg}")
                if self.serial_connection and not self.serial_connection.is_open:
                    self.is_connected = False
                    if self._connection_manager._reconnect_enabled:
                        self.reconnect()
            else:
                esp32_logger.error(f"Status okuma hatası: {e}", exc_info=True)
                if self.serial_connection and not self.serial_connection.is_open:
                    self.is_connected = False
                    if self._connection_manager._reconnect_enabled:
                        self.reconnect()
        except Exception as e:
            esp32_logger.error(f"Status okuma hatası: {e}", exc_info=True)

    def _process_message(self, line: str):
        """
        Tek bir mesajı işle (status veya ACK)

        Args:
            line: Mesaj satırı
        """
        # Status mesajı kontrolü
        if "<STAT;" in line:
            status = parse_status_message(line)
            if status:
                with self.status_lock:
                    self.last_status = status
                    self._status_buffer.append(status)
                esp32_logger.debug(f"Status güncellendi: {status.get('STATE', 'N/A')}")
                log_esp32_message("status", "rx", data=status)
                self._status_inspector.inspect_status_for_incidents(status)
        # ACK mesajı kontrolü
        elif "<ACK;" in line:
            ack = parse_ack_message(line)
            if ack:
                esp32_logger.debug(
                    f"ACK alındı: {ack.get('CMD', 'N/A')} - {ack.get('STATUS', 'N/A')}"
                )
                log_esp32_message("ack", "rx", data=ack)
                self._ack_buffer.append(ack)
                # ACK'ı queue'ya ekle
                try:
                    self._ack_queue.put_nowait(ack)
                except queue.Full:
                    # Queue dolu, en eski ACK'yı çıkar ve yenisini ekle
                    try:
                        self._ack_queue.get_nowait()
                        self._ack_queue.put_nowait(ack)
                        esp32_logger.warning("ACK queue dolu, eski ACK atıldı")
                    except queue.Empty:
                        pass

    def _monitor_loop(self):
        """
        Durum izleme döngüsü
        """
        consecutive_errors = 0
        max_consecutive_errors = 10

        while self._monitor_running:
            try:
                if self.is_connected:
                    self._read_status_messages()
                    # Queue'daki bekleyen komutları işle
                    if not self._command_queue.empty() and self._command_sender:
                        self._command_sender.process_command_queue()
                    consecutive_errors = 0
                elif self._connection_manager._reconnect_enabled:
                    # Bağlantı yoksa reconnection dene
                    if consecutive_errors == 0:
                        esp32_logger.info(
                            "Monitor loop: Bağlantı yok, reconnection deneniyor"
                        )
                        self.reconnect()
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
            except Exception as e:
                consecutive_errors += 1
                esp32_logger.error(f"Monitor loop error: {e}", exc_info=True)
                time.sleep(0.5)
            else:
                time.sleep(0.1)  # 100ms bekleme

    # Property accessors for backward compatibility
    @property
    def serial_connection(self):
        """Serial connection property"""
        return self._connection_manager.serial_connection

    @serial_connection.setter
    def serial_connection(self, value):
        """Serial connection setter"""
        self._connection_manager.serial_connection = value


# Singleton instance (thread-safe)
_esp32_bridge_instance: Optional[ESP32Bridge] = None
_bridge_lock = threading.Lock()


def get_esp32_bridge() -> ESP32Bridge:
    """
    ESP32 bridge singleton instance'ı al (thread-safe)

    Returns:
        ESP32Bridge instance

    Raises:
        RuntimeError: ESP32 bağlantısı kurulamazsa
    """
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
            instance = ESP32Bridge()
            if not instance.connect():
                esp32_logger.error("ESP32 bağlantısı kurulamadı")
                raise RuntimeError("ESP32 bağlantısı kurulamadı")
            _esp32_bridge_instance = instance
            esp32_logger.info("ESP32 bridge singleton instance oluşturuldu")

    return _esp32_bridge_instance
