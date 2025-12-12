"""
ESP32 Connection Manager Module
Created: 2025-12-12 10:55:00
Last Modified: 2025-12-12 10:55:00
Version: 1.0.0
Description: ESP32 bağlantı yönetimi ve reconnection modülü
"""

import time
from typing import Optional

import serial
import serial.tools.list_ports

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from api.logging_config import esp32_logger, log_esp32_message
from esp32.retry import RetryConfig, RetryStrategy
from esp32.protocol_handler import BAUDRATE


class ConnectionManager:
    """
    ESP32 bağlantı yönetimi ve reconnection sınıfı
    """

    def __init__(
        self,
        port: Optional[str] = None,
        baudrate: int = BAUDRATE,
        reconnect_enabled: bool = True,
        max_reconnect_attempts: int = 3,
        reconnect_delay: float = 5.0,
    ):
        """
        Connection manager başlatıcı

        Args:
            port: Seri port adı (None ise otomatik bulunur)
            baudrate: Baudrate (varsayılan: 115200)
            reconnect_enabled: Reconnection aktif mi?
            max_reconnect_attempts: Maksimum reconnection denemesi
            reconnect_delay: Reconnection delay (saniye)
        """
        self.port = port
        self.baudrate = baudrate
        self.serial_connection: Optional[serial.Serial] = None
        self.is_connected = False
        self._reconnect_enabled = reconnect_enabled
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = max_reconnect_attempts
        self._reconnect_delay = reconnect_delay
        self._last_connection_error: Optional[str] = None

    def find_esp32_port(self) -> Optional[str]:
        """
        ESP32 seri portunu otomatik bul

        Returns:
            Port adı veya None
        """
        ports = serial.tools.list_ports.comports()
        # ESP32 genellikle USB Serial veya CP210x, CH340 gibi chipsetler kullanır
        for port in ports:
            # ESP32 için yaygın tanımlayıcılar
            if any(
                keyword in port.description.lower()
                for keyword in ["usb", "serial", "cp210", "ch340", "ftdi"]
            ):
                return port.device
        return None

    def connect(self) -> bool:
        """
        ESP32'ye bağlan

        Returns:
            Başarı durumu
        """
        try:
            if self.serial_connection and self.serial_connection.is_open:
                self.disconnect()

            port = self.port or self.find_esp32_port()
            if not port:
                esp32_logger.warning("ESP32 portu bulunamadı")
                return False

            self.serial_connection = serial.Serial(
                port=port,
                baudrate=self.baudrate,
                timeout=1.0,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
            )

            # Bağlantıyı test et
            time.sleep(0.5)  # Port'un hazır olması için bekle
            self.is_connected = True

            esp32_logger.info(f"ESP32'ye bağlandı: {port}")
            log_esp32_message(
                "connection", "tx", {"port": port, "baudrate": self.baudrate}
            )
            return True

        except Exception as e:
            esp32_logger.error(f"ESP32 bağlantı hatası: {e}", exc_info=True)
            self.is_connected = False
            return False

    def disconnect(self):
        """ESP32 bağlantısını kapat"""
        self._reconnect_enabled = False  # Reconnection'ı durdur
        if self.serial_connection and self.serial_connection.is_open:
            try:
                self.serial_connection.close()
            except Exception as e:
                esp32_logger.warning(f"Serial port kapatma hatası: {e}")
        self.is_connected = False
        self._reconnect_attempts = 0
        esp32_logger.info("ESP32 bağlantısı kapatıldı")
        log_esp32_message("disconnection", "tx")

    def reconnect(
        self, max_retries: Optional[int] = None, retry_delay: Optional[float] = None
    ) -> bool:
        """
        ESP32 bağlantısını yeniden kur (reconnection mekanizması - exponential backoff)

        Args:
            max_retries: Maksimum yeniden deneme sayısı (None ise varsayılan kullanılır)
            retry_delay: İlk yeniden deneme aralığı (saniye, None ise varsayılan kullanılır)

        Returns:
            Başarı durumu
        """
        if not self._reconnect_enabled:
            esp32_logger.debug("Reconnection devre dışı")
            return False

        max_retries = max_retries or self._max_reconnect_attempts
        initial_delay = retry_delay or self._reconnect_delay

        # Exponential backoff retry config
        retry_config = RetryConfig(
            max_retries=max_retries,
            initial_delay=initial_delay,
            max_delay=30.0,  # Maksimum 30 saniye bekleme
            strategy=RetryStrategy.EXPONENTIAL,
            multiplier=2.0,
        )

        esp32_logger.info(f"ESP32 reconnection başlatılıyor (max {max_retries} deneme)")

        for attempt in range(1, max_retries + 1):
            try:
                esp32_logger.info(f"Reconnection denemesi {attempt}/{max_retries}")
                if self.connect():
                    self._reconnect_attempts = 0
                    self._last_connection_error = None
                    esp32_logger.info(f"ESP32 reconnection başarılı (deneme {attempt})")
                    return True
                else:
                    self._last_connection_error = "Connection failed"
            except Exception as e:
                self._last_connection_error = str(e)
                esp32_logger.warning(f"Reconnection denemesi {attempt} başarısız: {e}")

            if attempt < max_retries:
                delay = retry_config.calculate_delay(attempt - 1)
                esp32_logger.debug(
                    f"Reconnection retry delay: {delay:.2f}s (attempt {attempt}/{max_retries})"
                )
                time.sleep(delay)

        self._reconnect_attempts += 1
        esp32_logger.error(
            f"ESP32 reconnection başarısız ({max_retries} deneme sonrası)"
        )
        return False

    def enable_reconnect(self):
        """Reconnection'ı aktif et"""
        self._reconnect_enabled = True

    def disable_reconnect(self):
        """Reconnection'ı devre dışı bırak"""
        self._reconnect_enabled = False
