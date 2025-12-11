"""
ESP32-RPi Bridge Module
Created: 2025-12-08
Last Modified: 2025-12-08
Version: 1.0.0
Description: ESP32 ile USB seri port üzerinden iletişim modülü
"""

import json
import os
import queue
import re
import sys
import threading
import time
from collections import deque
from datetime import datetime
from typing import Any, Dict, Optional

import serial
import serial.tools.list_ports

# Logging modülünü import et
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from api.logging_config import esp32_logger, log_esp32_message
from esp32.retry import RetryConfig, RetryStrategy

# Protocol constants
PROTOCOL_HEADER = 0x41
PROTOCOL_SEPARATOR = 0x2C
PROTOCOL_FOOTER = 0x10
BAUDRATE = 115200
STATUS_UPDATE_INTERVAL = 5  # seconds

# Status message format: <STAT;ID=X;CP=X;CPV=X;PP=X;PPV=X;RL=X;LOCK=X;MOTOR=X;PWM=X;MAX=X;CABLE=X;AUTH=X;STATE=X;PB=X;STOP=X;>


class ESP32Bridge:
    """
    ESP32 ile USB seri port üzerinden iletişim köprüsü
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
        self.serial_connection: Optional[serial.Serial] = None
        self.protocol_data = self._load_protocol()
        self.last_status: Optional[Dict[str, Any]] = None
        self.status_lock = threading.Lock()
        self._serial_lock = threading.Lock()  # Serial port okuma/yazma için lock
        self._ack_queue = queue.Queue(
            maxsize=20
        )  # ACK mesajları için queue (max 20 ACK)
        # Mesaj buffer'lar (ring buffer) - son N mesajı sakla
        self._status_buffer = deque(maxlen=50)  # Son 50 status mesajı
        self._ack_buffer = deque(maxlen=30)  # Son 30 ACK mesajı
        # Komut gönderme buffer'ı (bağlantı kopması durumu için)
        self._command_queue = queue.Queue(maxsize=50)  # Gönderilecek komutlar
        self._pending_commands = {}  # {command_id: CommandInfo}
        self._command_counter = 0
        self._command_lock = threading.Lock()  # Komut tracking için lock
        self.is_connected = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_running = False
        self._reconnect_enabled = True
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 3
        self._reconnect_delay = 5  # seconds
        self._last_connection_error: Optional[str] = None

    def _load_protocol(self) -> Dict[str, Any]:
        """Protokol tanımlarını yükle"""
        try:
            import os

            protocol_path = os.path.join(os.path.dirname(__file__), "protocol.json")
            with open(protocol_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            esp32_logger.error(f"Protocol yükleme hatası: {e}", exc_info=True)
            return {}

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

            # Durum izleme thread'ini başlat
            self._start_monitoring()

            # Queue'daki bekleyen komutları gönder
            self._process_command_queue()

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
        self._stop_monitoring()
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

    def _send_command_bytes(
        self, command_bytes: list, queue_if_failed: bool = True
    ) -> bool:
        """
        ESP32'ye byte array komutu gönder

        Args:
            command_bytes: 5 byte'lık komut dizisi
            queue_if_failed: Bağlantı yoksa komutu queue'ya ekle (varsayılan: True)

        Returns:
            Başarı durumu
        """
        if (
            not self.is_connected
            or not self.serial_connection
            or not self.serial_connection.is_open
        ):
            if queue_if_failed:
                # Komutu queue'ya ekle (bağlantı kurulunca gönderilecek)
                try:
                    self._command_queue.put_nowait(
                        {
                            "bytes": command_bytes,
                            "timestamp": time.time(),
                            "retry_count": 0,
                        }
                    )
                    esp32_logger.debug(
                        f"Komut queue'ya eklendi (bağlantı yok): {command_bytes}"
                    )
                except queue.Full:
                    esp32_logger.warning("Komut queue dolu, komut atıldı")
            else:
                esp32_logger.warning("ESP32 bağlantısı yok")
            return False

        try:
            if len(command_bytes) != 5:
                esp32_logger.error(
                    f"Geçersiz komut uzunluğu: {len(command_bytes)} (beklenen: 5)"
                )
                return False

            # Thread-safe komut gönderme
            with self._serial_lock:
                # Bağlantı durumunu tekrar kontrol et (race condition önlemi)
                if not self.serial_connection or not self.serial_connection.is_open:
                    if queue_if_failed:
                        try:
                            self._command_queue.put_nowait(
                                {
                                    "bytes": command_bytes,
                                    "timestamp": time.time(),
                                    "retry_count": 0,
                                }
                            )
                            esp32_logger.debug(
                                f"Komut queue'ya eklendi (bağlantı koptu): {command_bytes}"
                            )
                        except queue.Full:
                            pass
                    esp32_logger.warning("Bağlantı komut gönderilirken koptu")
                    return False

                self.serial_connection.write(bytes(command_bytes))
                self.serial_connection.flush()

                # Komut gönderildikten sonra bağlantıyı tekrar kontrol et
                if not self.serial_connection.is_open:
                    if queue_if_failed:
                        try:
                            self._command_queue.put_nowait(
                                {
                                    "bytes": command_bytes,
                                    "timestamp": time.time(),
                                    "retry_count": 1,  # Bir kez gönderildi ama başarısız
                                }
                            )
                        except queue.Full:
                            pass
                    esp32_logger.warning("Bağlantı komut gönderildikten sonra koptu")
                    return False

            return True

        except Exception as e:
            esp32_logger.error(f"Komut gönderme hatası: {e}", exc_info=True)
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

    def send_status_request(self) -> bool:
        """Status komutu gönder"""
        cmd = self.protocol_data.get("commands", {}).get("status", {})
        byte_array = cmd.get("byte_array", [65, 0, 44, 0, 16])
        result = self._send_command_bytes(byte_array)
        if result:
            log_esp32_message(
                "status_request",
                "tx",
                data={"command": "status_request", "bytes": byte_array},
            )
        return result

    def send_authorization(
        self, wait_for_ack: bool = True, timeout: float = 1.0, max_retries: int = 1
    ) -> bool:
        """
        Authorization komutu gönder (şarj başlatma)

        Args:
            wait_for_ack: ACK mesajını bekle (varsayılan: True)
            timeout: ACK bekleme timeout süresi (saniye)
            max_retries: Maksimum retry sayısı (varsayılan: 1, toplam 2 deneme)

        Returns:
            Başarı durumu (ACK bekleniyorsa ACK alındıysa True)
        """
        cmd = self.protocol_data.get("commands", {}).get("authorization", {})
        byte_array = cmd.get("byte_array", [65, 1, 44, 1, 16])

        for attempt in range(max_retries + 1):
            result = self._send_command_bytes(byte_array)
            if result:
                log_esp32_message(
                    "authorization",
                    "tx",
                    data={
                        "command": "authorization",
                        "bytes": byte_array,
                        "attempt": attempt + 1,
                    },
                )
                # ACK bekleniyorsa bekle
                if wait_for_ack:
                    ack = self._wait_for_ack("AUTH", timeout=timeout)
                    if ack:
                        status = ack.get("STATUS", "")
                        # OK veya CLEARED durumları başarılı sayılır
                        if status in ["OK", "CLEARED"]:
                            return True
                        # STATUS hatalı ama komut gönderildi, retry yapma
                        esp32_logger.warning(
                            f"Authorization ACK STATUS={status}, komut gönderildi ama durum beklenmeyen"
                        )
                        return False
                    # ACK alınamadı, retry yap (exponential backoff)
                    if attempt < max_retries:
                        retry_config = RetryConfig(
                            max_retries=max_retries,
                            initial_delay=0.1,
                            max_delay=1.0,
                            strategy=RetryStrategy.EXPONENTIAL,
                            multiplier=2.0,
                        )
                        delay = retry_config.calculate_delay(attempt)
                        esp32_logger.debug(
                            f"Authorization ACK timeout, retry {attempt + 1}/{max_retries} (delay: {delay:.2f}s)"
                        )
                        time.sleep(delay)
                        continue
                    return False  # Tüm retry'lar başarısız
                return True  # ACK beklenmiyor, komut gönderildi
            # Komut gönderilemedi, retry yap (exponential backoff)
            if attempt < max_retries:
                retry_config = RetryConfig(
                    max_retries=max_retries,
                    initial_delay=0.1,
                    max_delay=1.0,
                    strategy=RetryStrategy.EXPONENTIAL,
                    multiplier=2.0,
                )
                delay = retry_config.calculate_delay(attempt)
                esp32_logger.debug(
                    f"Authorization komut gönderme başarısız, retry {attempt + 1}/{max_retries} (delay: {delay:.2f}s)"
                )
                time.sleep(delay)
                continue

        return False  # Tüm denemeler başarısız

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
            amperage: Amper değeri (6-32 aralığında herhangi bir tam sayı)
            wait_for_ack: ACK mesajını bekle (varsayılan: True)
            timeout: ACK bekleme timeout süresi (saniye)
            max_retries: Maksimum retry sayısı (varsayılan: 1, toplam 2 deneme)

        Returns:
            Başarı durumu (ACK bekleniyorsa ACK alındıysa ve STATUS=OK ise True)
        """
        # 6-32 amper aralığında herhangi bir değer geçerlidir
        if not (6 <= amperage <= 32):
            esp32_logger.warning(
                f"Geçersiz akım değeri: {amperage} (geçerli aralık: 6-32A)"
            )
            return False

        # Komut formatı: 41 [KOMUT=0x02] 2C [DEĞER=amperage] 10
        # Değer doğrudan amper cinsinden hex formatında gönderilir
        command_bytes = [0x41, 0x02, 0x2C, amperage, 0x10]

        for attempt in range(max_retries + 1):
            result = self._send_command_bytes(command_bytes)
            if result:
                log_esp32_message(
                    "current_set",
                    "tx",
                    data={
                        "command": "current_set",
                        "amperage": amperage,
                        "bytes": command_bytes,
                        "attempt": attempt + 1,
                    },
                )
                # ACK bekleniyorsa bekle
                if wait_for_ack:
                    ack = self._wait_for_ack("SETMAXAMP", timeout=timeout)
                    if ack:
                        status = ack.get("STATUS", "")
                        if status == "OK":
                            return True
                        # STATUS=ERR, retry yapma (ESP32 reddetmiş)
                        esp32_logger.warning(
                            "Current set ACK STATUS=ERR, komut ESP32 tarafından reddedildi"
                        )
                        return False
                    # ACK alınamadı, retry yap (exponential backoff)
                    if attempt < max_retries:
                        retry_config = RetryConfig(
                            max_retries=max_retries,
                            initial_delay=0.1,
                            max_delay=1.0,
                            strategy=RetryStrategy.EXPONENTIAL,
                            multiplier=2.0,
                        )
                        delay = retry_config.calculate_delay(attempt)
                        esp32_logger.debug(
                            f"Current set ACK timeout, retry {attempt + 1}/{max_retries} (delay: {delay:.2f}s)"
                        )
                        time.sleep(delay)
                        continue
                    return False  # Tüm retry'lar başarısız
                return True  # ACK beklenmiyor, komut gönderildi
            # Komut gönderilemedi, retry yap (exponential backoff)
            if attempt < max_retries:
                retry_config = RetryConfig(
                    max_retries=max_retries,
                    initial_delay=0.1,
                    max_delay=1.0,
                    strategy=RetryStrategy.EXPONENTIAL,
                    multiplier=2.0,
                )
                delay = retry_config.calculate_delay(attempt)
                esp32_logger.debug(
                    f"Current set komut gönderme başarısız, retry {attempt + 1}/{max_retries} (delay: {delay:.2f}s)"
                )
                time.sleep(delay)
                continue

        return False  # Tüm denemeler başarısız

    def send_charge_stop(
        self, wait_for_ack: bool = False, timeout: float = 1.0
    ) -> bool:
        """
        Şarj durdurma komutu gönder

        Args:
            wait_for_ack: ACK mesajını bekle (varsayılan: False, çünkü charge_stop için ACK yok)
            timeout: ACK bekleme timeout süresi (saniye)

        Returns:
            Başarı durumu
        """
        cmd = self.protocol_data.get("commands", {}).get("charge_stop", {})
        byte_array = cmd.get("byte_array", [65, 4, 44, 7, 16])
        result = self._send_command_bytes(byte_array)
        if result:
            log_esp32_message(
                "charge_stop",
                "tx",
                data={"command": "charge_stop", "bytes": byte_array},
            )
            # Charge stop için ACK mesajı yok (ESP32 firmware'da tanımlı değil)
            # Ancak wait_for_ack=True ise yine de bekle (ileride eklenebilir)
            if wait_for_ack:
                ack = self._wait_for_ack("STOP", timeout=timeout)
                if ack:
                    status = ack.get("STATUS", "")
                    return status == "OK"
                # ACK alınamadı ama komut gönderildi, True döndür
                return True
        return result

    def _parse_status_message(self, message: str) -> Optional[Dict[str, Any]]:
        """
        ESP32'den gelen status mesajını parse et

        Args:
            message: Status mesajı string'i

        Returns:
            Parse edilmiş durum dict'i veya None
        """
        # Format: <STAT;ID=X;CP=X;CPV=X;PP=X;PPV=X;RL=X;LOCK=X;MOTOR=X;PWM=X;MAX=X;CABLE=X;AUTH=X;STATE=X;PB=X;STOP=X;>
        pattern = r"<STAT;(.*?)>"
        match = re.search(pattern, message)
        if not match:
            return None

        status_data = {}
        fields = match.group(1).split(";")

        for field in fields:
            # Whitespace temizle
            field = field.strip()
            if not field:
                continue
            if "=" in field:
                key, value = field.split("=", 1)
                key = key.strip()
                value = value.strip()
                # Sayısal değerleri dönüştür
                try:
                    if "." in value:
                        status_data[key] = float(value)
                    else:
                        status_data[key] = int(value)
                except ValueError:
                    status_data[key] = value

        status_data["timestamp"] = datetime.now().isoformat()

        # STATE değerini STATE_NAME'e çevir
        if "STATE" in status_data:
            state_value = status_data["STATE"]
            # ESP32State enum mapping
            state_names = {
                0: "HARDFAULT_END",
                1: "IDLE",
                2: "CABLE_DETECT",
                3: "EV_CONNECTED",
                4: "READY",
                5: "CHARGING",
                6: "PAUSED",
                7: "STOPPED",
                8: "FAULT_HARD",
            }
            status_data["STATE_NAME"] = state_names.get(
                state_value, f"UNKNOWN_{state_value}"
            )

        return status_data

    def _parse_ack_message(self, message: str) -> Optional[Dict[str, Any]]:
        """
        ESP32'den gelen ACK mesajını parse et

        Args:
            message: ACK mesajı string'i

        Returns:
            Parse edilmiş ACK dict'i veya None
        """
        # Format: <ACK;CMD=[KOMUT];STATUS=[DURUM];[EK_BILGI];>
        pattern = r"<ACK;(.*?)>"
        match = re.search(pattern, message)
        if not match:
            return None

        ack_data = {}
        fields = match.group(1).split(";")

        for field in fields:
            # Whitespace temizle
            field = field.strip()
            if not field:
                continue
            if "=" in field:
                key, value = field.split("=", 1)
                key = key.strip()
                value = value.strip()
                ack_data[key] = value

        ack_data["timestamp"] = datetime.now().isoformat()
        return ack_data

    def _wait_for_ack(
        self, expected_cmd: str, timeout: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """
        Belirli bir komut için ACK mesajını bekle

        Args:
            expected_cmd: Beklenen komut adı (örn: "AUTH", "SETMAXAMP")
            timeout: Timeout süresi (saniye)

        Returns:
            ACK dict'i veya None (timeout veya hata)
        """
        if not self.serial_connection or not self.serial_connection.is_open:
            return None

        start_time = time.time()
        # Queue'dan beklenen komutun ACK'sını bekle (thread-safe)
        while time.time() - start_time < timeout:
            try:
                # Queue'dan ACK mesajını al (timeout ile)
                try:
                    ack = self._ack_queue.get(timeout=0.1)
                    if ack and ack.get("CMD") == expected_cmd:
                        esp32_logger.debug(
                            f"ACK alındı: {expected_cmd} - {ack.get('STATUS', 'N/A')}"
                        )
                        log_esp32_message("ack", "rx", data=ack)
                        return ack
                    # Yanlış komutun ACK'sı, queue'ya geri koy (başka thread bekliyor olabilir)
                    # Ancak bu durumda queue'ya geri koymak yerine kaybolmasına izin veriyoruz
                    # Çünkü doğru ACK zaten monitor thread tarafından queue'ya eklenmiş olmalı
                except queue.Empty:
                    # Queue boş, devam et
                    pass
                time.sleep(0.01)  # 10ms bekleme
            except Exception as e:
                esp32_logger.warning(f"ACK okuma hatası: {e}")
                break

        esp32_logger.warning(
            f"ACK timeout: {expected_cmd} komutu için {timeout}s içinde yanıt alınamadı"
        )
        return None

    def _read_status_messages(self):
        """
        Seri porttan durum mesajlarını oku

        NOT: reset_input_buffer() kullanılmıyor çünkü bu bazı mesajların kaybolmasına neden olabilir.
        Bunun yerine mevcut buffer'daki tüm satırları okumaya çalışıyoruz.
        """
        if not self.serial_connection or not self.serial_connection.is_open:
            # Bağlantı yoksa reconnection dene
            if self._reconnect_enabled and self.is_connected:
                esp32_logger.warning(
                    "Serial port bağlantısı kopmuş, reconnection deneniyor"
                )
                self.is_connected = False
                self.reconnect()
            return

        try:
            # Thread-safe okuma (lock ile)
            with self._serial_lock:
                # Mevcut buffer'daki tüm satırları oku (reset yapmadan)
                # ESP32 7.5 saniyede bir gönderiyor, buffer'da genellikle 1-2 mesaj olur
                lines_read = 0
                max_lines = 5  # Maksimum okuma sayısı (buffer overflow koruması)
                read_lines = []  # Okunan satırları sakla (lock dışında işle)

                while self.serial_connection.in_waiting > 0 and lines_read < max_lines:
                    line = (
                        self.serial_connection.readline()
                        .decode("utf-8", errors="ignore")
                        .strip()
                    )
                    lines_read += 1
                    if line:
                        read_lines.append(line)

            # Eğer çok fazla satır okunduysa, buffer'ı temizle (overflow koruması)
            # Ancak önce önemli mesajları (STAT, ACK) kontrol et
            if lines_read >= max_lines:
                remaining_bytes = self.serial_connection.in_waiting
                if remaining_bytes > 0:
                    esp32_logger.warning(
                        f"Buffer overflow riski: {lines_read} satır okundu, "
                        f"{remaining_bytes} byte daha var. Buffer temizleniyor."
                    )
                    # Önemli mesajları kaçırmamak için bir kez daha oku
                    try:
                        remaining_line = (
                            self.serial_connection.readline()
                            .decode("utf-8", errors="ignore")
                            .strip()
                        )
                        if remaining_line:
                            if "<STAT;" in remaining_line:
                                status = self._parse_status_message(remaining_line)
                                if status:
                                    with self.status_lock:
                                        self.last_status = status
                                        self._status_buffer.append(status)
                            elif "<ACK;" in remaining_line:
                                ack = self._parse_ack_message(remaining_line)
                                if ack:
                                    self._ack_buffer.append(ack)
                                    try:
                                        self._ack_queue.put_nowait(ack)
                                    except queue.Full:
                                        try:
                                            self._ack_queue.get_nowait()
                                            self._ack_queue.put_nowait(ack)
                                        except queue.Empty:
                                            pass
                    except Exception:
                        pass
                self.serial_connection.reset_input_buffer()

            # Lock dışında mesajları işle (uzun sürebilir)
            for line in read_lines:
                # Status mesajı kontrolü
                if "<STAT;" in line:
                    status = self._parse_status_message(line)
                    if status:
                        with self.status_lock:
                            self.last_status = status
                            # Ring buffer'a ekle (geçmiş mesajlar için)
                            self._status_buffer.append(status)
                        esp32_logger.debug(
                            f"Status güncellendi: {status.get('STATE', 'N/A')}"
                        )
                        log_esp32_message("status", "rx", data=status)
                        # En son mesajı bulduk, diğerlerini okumaya devam et (en güncel olanı almak için)
                # ACK mesajı kontrolü - Queue'ya ekle (thread-safe)
                elif "<ACK;" in line:
                    ack = self._parse_ack_message(line)
                    if ack:
                        esp32_logger.debug(
                            f"ACK alındı: {ack.get('CMD', 'N/A')} - {ack.get('STATUS', 'N/A')}"
                        )
                        log_esp32_message("ack", "rx", data=ack)
                        # Ring buffer'a ekle (geçmiş ACK'lar için)
                        self._ack_buffer.append(ack)
                        # ACK'ı queue'ya ekle (_wait_for_ack tarafından okunacak)
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

        except serial.SerialException as e:
            # Serial port hatası - reconnection dene (improved error recovery)
            error_msg = str(e)
            esp32_logger.error(f"Serial port hatası: {error_msg}")

            # Connection error recovery - farklı hata türleri için farklı recovery stratejileri
            if (
                "device disconnected" in error_msg.lower()
                or "multiple access" in error_msg.lower()
                or "device or resource busy" in error_msg.lower()
            ):
                if self._reconnect_enabled and self.is_connected:
                    esp32_logger.warning(
                        "Serial port bağlantısı kopmuş, reconnection deneniyor"
                    )
                    self.is_connected = False
                    # Exponential backoff ile reconnect (retry modülü kullanılıyor)
                    self.reconnect()
            elif "timeout" in error_msg.lower():
                # Timeout hatası - bağlantı hala açık olabilir, sadece uyarı ver
                esp32_logger.warning(f"Serial port timeout: {error_msg}")
                # Bağlantı durumunu kontrol et
                if self.serial_connection and not self.serial_connection.is_open:
                    self.is_connected = False
                    if self._reconnect_enabled:
                        self.reconnect()
            else:
                esp32_logger.error(f"Status okuma hatası: {e}", exc_info=True)
                # Bilinmeyen hata - bağlantı durumunu kontrol et
                if self.serial_connection and not self.serial_connection.is_open:
                    self.is_connected = False
                    if self._reconnect_enabled:
                        self.reconnect()
        except Exception as e:
            esp32_logger.error(f"Status okuma hatası: {e}", exc_info=True)

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

    def _process_command_queue(self):
        """
        Queue'daki bekleyen komutları gönder (bağlantı kurulunca çağrılır)
        """
        if not self.is_connected:
            return

        processed = 0
        max_process = 10  # Bir seferde maksimum 10 komut işle

        while processed < max_process and not self._command_queue.empty():
            try:
                command_info = self._command_queue.get_nowait()
                command_bytes = command_info["bytes"]
                retry_count = command_info.get("retry_count", 0)
                timestamp = command_info.get("timestamp", 0)

                # Eski komutları atla (10 saniyeden eski)
                if time.time() - timestamp > 10.0:
                    esp32_logger.debug(
                        f"Eski komut atlandı (10s'den eski): {command_bytes}"
                    )
                    continue

                # Komutu gönder (queue_if_failed=False, çünkü zaten queue'da)
                if self._send_command_bytes(command_bytes, queue_if_failed=False):
                    esp32_logger.debug(
                        f"Queue'dan komut gönderildi: {command_bytes}, retry: {retry_count}"
                    )
                    processed += 1
                else:
                    # Gönderilemedi, tekrar queue'ya ekle (retry sayısını artır)
                    retry_count += 1
                    if retry_count < 3:  # Maksimum 3 retry
                        try:
                            command_info["retry_count"] = retry_count
                            command_info["timestamp"] = time.time()
                            self._command_queue.put_nowait(command_info)
                        except queue.Full:
                            esp32_logger.warning(
                                f"Komut queue'ya geri eklenemedi (dolu): {command_bytes}"
                            )
                    else:
                        esp32_logger.warning(
                            f"Komut maksimum retry sayısına ulaştı, atıldı: {command_bytes}"
                        )
            except queue.Empty:
                break
            except Exception as e:
                esp32_logger.error(f"Komut queue işleme hatası: {e}", exc_info=True)
                break

        if processed > 0:
            esp32_logger.info(f"Queue'dan {processed} komut gönderildi")

    def _monitor_loop(self):
        """
        Durum izleme döngüsü

        Exception handling ile korumalı - loop crash etmez.
        Reconnection mekanizması ile bağlantı kopmalarını handle eder.
        """
        consecutive_errors = 0
        max_consecutive_errors = 10

        while self._monitor_running:
            try:
                if self.is_connected:
                    self._read_status_messages()
                    # Queue'daki bekleyen komutları işle (periyodik olarak)
                    if not self._command_queue.empty():
                        self._process_command_queue()
                    consecutive_errors = 0  # Başarılı okuma - hata sayacını sıfırla
                elif self._reconnect_enabled:
                    # Bağlantı yoksa reconnection dene
                    if consecutive_errors == 0:  # İlk hatada reconnection dene
                        esp32_logger.info(
                            "Monitor loop: Bağlantı yok, reconnection deneniyor"
                        )
                        self.reconnect()
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        esp32_logger.warning(
                            f"Monitor loop: {max_consecutive_errors} ardışık hata, reconnection duraklatılıyor"
                        )
                        # Exponential backoff ile bekleme (30 saniye yerine artan süre)
                        wait_time = min(
                            30 * (2 ** (consecutive_errors - max_consecutive_errors)),
                            300,
                        )  # Max 5 dakika
                        esp32_logger.info(
                            f"Monitor loop: {wait_time:.1f} saniye bekleniyor"
                        )
                        time.sleep(wait_time)
                        consecutive_errors = 0  # Sayaç sıfırla ve tekrar dene
            except Exception as e:
                # Loop crash etmemeli - hata logla ve devam et
                consecutive_errors += 1
                esp32_logger.error(f"Monitor loop error: {e}", exc_info=True)
                # Kısa bir bekleme sonrası devam et
                time.sleep(0.5)
            else:
                time.sleep(0.1)  # 100ms bekleme

    def get_status(self, max_age_seconds: float = 10.0) -> Optional[Dict[str, Any]]:
        """
        Son durum bilgisini al

        Args:
            max_age_seconds: Maksimum veri yaşı (saniye). Bu süreden eski veri None döndürülür.
                            ESP32 7.5 saniyede bir gönderiyor, 10 saniye güvenli bir eşik.

        Returns:
            Durum dict'i veya None (veri çok eskiyse veya yoksa)
        """
        with self.status_lock:
            if not self.last_status:
                return None

            # Timestamp kontrolü - çok eski veri None döndürülür
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
                # Timestamp yoksa veya hatalıysa, veriyi döndür ama uyarı ver

            return self.last_status.copy()

    def get_status_sync(self, timeout: float = 2.0) -> Optional[Dict[str, Any]]:
        """
        Status komutu gönder ve yanıt bekle (senkron - improved timeout handling)

        Args:
            timeout: Timeout süresi (saniye)

        Returns:
            Durum dict'i veya None (timeout veya bağlantı hatası)
        """
        # Bağlantı kontrolü
        if (
            not self.is_connected
            or not self.serial_connection
            or not self.serial_connection.is_open
        ):
            esp32_logger.warning("get_status_sync: ESP32 bağlantısı yok")
            return None

        if not self.send_status_request():
            esp32_logger.warning("get_status_sync: Status komutu gönderilemedi")
            return None

        start_time = time.time()
        check_interval = 0.05  # 50ms check interval (daha responsive)
        last_check_time = start_time

        while time.time() - start_time < timeout:
            # Bağlantı durumunu kontrol et (her 0.5 saniyede bir)
            if time.time() - last_check_time > 0.5:
                if not self.serial_connection or not self.serial_connection.is_open:
                    esp32_logger.warning("get_status_sync: Bağlantı kopmuş")
                    self.is_connected = False
                    return None
                last_check_time = time.time()

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


# Singleton instance (thread-safe)
_esp32_bridge_instance: Optional[ESP32Bridge] = None
_bridge_lock = threading.Lock()


def get_esp32_bridge() -> ESP32Bridge:
    """
    ESP32 bridge singleton instance'ı al (thread-safe)

    Double-check locking pattern kullanarak thread-safe singleton sağlar.

    Returns:
        ESP32Bridge instance

    Raises:
        RuntimeError: ESP32 bağlantısı kurulamazsa
    """
    global _esp32_bridge_instance

    # Pytest ortamında gerçek seri bağlantı açma
    if os.getenv("PYTEST_CURRENT_TEST") is not None:
        mock_bridge = ESP32Bridge(port="/dev/null", baudrate=BAUDRATE)
        mock_bridge.is_connected = True
        return mock_bridge

    # İlk kontrol (lock almadan - performans için)
    if _esp32_bridge_instance is not None:
        return _esp32_bridge_instance

    # İkinci kontrol (lock ile - thread-safety için)
    with _bridge_lock:
        if _esp32_bridge_instance is None:
            instance = ESP32Bridge()
            if not instance.connect():
                # Bağlantı başarısız - instance oluşturma
                esp32_logger.error("ESP32 bağlantısı kurulamadı")
                raise RuntimeError("ESP32 bağlantısı kurulamadı")
            _esp32_bridge_instance = instance
            esp32_logger.info("ESP32 bridge singleton instance oluşturuldu")

    return _esp32_bridge_instance
