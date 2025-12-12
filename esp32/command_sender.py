"""
ESP32 Command Sender Module
Created: 2025-12-12 10:50:00
Last Modified: 2025-12-12 10:50:00
Version: 1.0.0
Description: ESP32 komut gönderme ve ACK handling modülü
"""

import queue
import threading
import time
from typing import Any, Dict, Optional

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from api.logging_config import esp32_logger, log_esp32_message
from esp32.retry import RetryConfig, RetryStrategy
from esp32.protocol_handler import get_command_bytes


class CommandSender:
    """
    ESP32 komut gönderme ve ACK handling sınıfı
    """

    def __init__(
        self,
        serial_connection,
        serial_lock: threading.Lock,
        ack_queue: queue.Queue,
        ack_buffer,
        protocol_data: Dict[str, Any],
        is_connected_ref,
        command_queue: queue.Queue,
    ):
        """
        Command sender başlatıcı

        Args:
            serial_connection: Serial port bağlantısı
            serial_lock: Serial port lock'u
            ack_queue: ACK mesajları için queue
            ack_buffer: ACK mesajları için ring buffer
            protocol_data: Protokol tanımları
            is_connected_ref: Bağlantı durumu referansı (callable)
            command_queue: Komut queue'su
        """
        self.serial_connection = serial_connection
        self._serial_lock = serial_lock
        self._ack_queue = ack_queue
        self._ack_buffer = ack_buffer
        self.protocol_data = protocol_data
        self._is_connected_ref = is_connected_ref
        self._command_queue = command_queue

    def send_command_bytes(
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
            not self._is_connected_ref()
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
        byte_array = get_command_bytes(self.protocol_data, "status")
        result = self.send_command_bytes(byte_array)
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
        byte_array = get_command_bytes(self.protocol_data, "authorization")

        for attempt in range(max_retries + 1):
            result = self.send_command_bytes(byte_array)
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
                    ack = self.wait_for_ack("AUTH", timeout=timeout)
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
            result = self.send_command_bytes(command_bytes)
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
                    ack = self.wait_for_ack("SETMAXAMP", timeout=timeout)
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
        byte_array = get_command_bytes(self.protocol_data, "charge_stop")
        result = self.send_command_bytes(byte_array)
        if result:
            log_esp32_message(
                "charge_stop",
                "tx",
                data={"command": "charge_stop", "bytes": byte_array},
            )
            # Charge stop için ACK mesajı yok (ESP32 firmware'da tanımlı değil)
            # Ancak wait_for_ack=True ise yine de bekle (ileride eklenebilir)
            if wait_for_ack:
                ack = self.wait_for_ack("STOP", timeout=timeout)
                if ack:
                    status = ack.get("STATUS", "")
                    return status == "OK"
                # ACK alınamadı ama komut gönderildi, True döndür
                return True
        return result

    def wait_for_ack(
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

    def process_command_queue(self):
        """
        Queue'daki bekleyen komutları gönder (bağlantı kurulunca çağrılır)
        """
        if not self._is_connected_ref():
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
                if self.send_command_bytes(command_bytes, queue_if_failed=False):
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
