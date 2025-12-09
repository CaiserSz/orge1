"""
ESP32-RPi Bridge Module
Created: 2025-12-08
Last Modified: 2025-12-08
Version: 1.0.0
Description: ESP32 ile USB seri port üzerinden iletişim modülü
"""

import serial
import serial.tools.list_ports
import json
import re
import time
import threading
from typing import Optional, Dict, Any
from datetime import datetime
import sys
import os

# Logging modülünü import et
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from api.logging_config import esp32_logger, log_esp32_message

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
        self.is_connected = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_running = False
        
    def _load_protocol(self) -> Dict[str, Any]:
        """Protokol tanımlarını yükle"""
        try:
            import os
            protocol_path = os.path.join(os.path.dirname(__file__), 'protocol.json')
            with open(protocol_path, 'r', encoding='utf-8') as f:
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
            if any(keyword in port.description.lower() for keyword in ['usb', 'serial', 'cp210', 'ch340', 'ftdi']):
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
                stopbits=serial.STOPBITS_ONE
            )
            
            # Bağlantıyı test et
            time.sleep(0.5)  # Port'un hazır olması için bekle
            self.is_connected = True
            
            # Durum izleme thread'ini başlat
            self._start_monitoring()
            
            esp32_logger.info(f"ESP32'ye bağlandı: {port}")
            log_esp32_message("connection", "tx", {"port": port, "baudrate": self.baudrate})
            return True
            
        except Exception as e:
            esp32_logger.error(f"ESP32 bağlantı hatası: {e}", exc_info=True)
            self.is_connected = False
            return False
    
    def disconnect(self):
        """ESP32 bağlantısını kapat"""
        self._stop_monitoring()
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
        self.is_connected = False
        esp32_logger.info("ESP32 bağlantısı kapatıldı")
        log_esp32_message("disconnection", "tx")
    
    def _send_command_bytes(self, command_bytes: list) -> bool:
        """
        ESP32'ye byte array komutu gönder
        
        Args:
            command_bytes: 5 byte'lık komut dizisi
            
        Returns:
            Başarı durumu
        """
        if not self.is_connected or not self.serial_connection or not self.serial_connection.is_open:
            esp32_logger.warning("ESP32 bağlantısı yok")
            return False
        
        try:
            if len(command_bytes) != 5:
                esp32_logger.error(f"Geçersiz komut uzunluğu: {len(command_bytes)} (beklenen: 5)")
                return False
            
            self.serial_connection.write(bytes(command_bytes))
            self.serial_connection.flush()
            return True
            
        except Exception as e:
            esp32_logger.error(f"Komut gönderme hatası: {e}", exc_info=True)
            return False
    
    def send_status_request(self) -> bool:
        """Status komutu gönder"""
        cmd = self.protocol_data.get('commands', {}).get('status', {})
        byte_array = cmd.get('byte_array', [65, 0, 44, 0, 16])
        result = self._send_command_bytes(byte_array)
        if result:
            log_esp32_message("status_request", "tx", data={"command": "status_request", "bytes": byte_array})
        return result
    
    def send_authorization(self) -> bool:
        """Authorization komutu gönder (şarj başlatma)"""
        cmd = self.protocol_data.get('commands', {}).get('authorization', {})
        byte_array = cmd.get('byte_array', [65, 1, 44, 1, 16])
        result = self._send_command_bytes(byte_array)
        if result:
            log_esp32_message("authorization", "tx", data={"command": "authorization", "bytes": byte_array})
        return result
    
    def send_current_set(self, amperage: int) -> bool:
        """
        Akım set komutu gönder
        
        Args:
            amperage: Amper değeri (6-32 aralığında herhangi bir tam sayı)
        
        Returns:
            Başarı durumu
        """
        # 6-32 amper aralığında herhangi bir değer geçerlidir
        if not (6 <= amperage <= 32):
            esp32_logger.warning(f"Geçersiz akım değeri: {amperage} (geçerli aralık: 6-32A)")
            return False
        
        # Komut formatı: 41 [KOMUT=0x02] 2C [DEĞER=amperage] 10
        # Değer doğrudan amper cinsinden hex formatında gönderilir
        command_bytes = [0x41, 0x02, 0x2C, amperage, 0x10]
        result = self._send_command_bytes(command_bytes)
        if result:
            log_esp32_message("current_set", "tx", data={"command": "current_set", "amperage": amperage, "bytes": command_bytes})
        return result
    
    def send_charge_stop(self) -> bool:
        """Şarj durdurma komutu gönder"""
        cmd = self.protocol_data.get('commands', {}).get('charge_stop', {})
        byte_array = cmd.get('byte_array', [65, 4, 44, 7, 16])
        result = self._send_command_bytes(byte_array)
        if result:
            log_esp32_message("charge_stop", "tx", data={"command": "charge_stop", "bytes": byte_array})
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
        pattern = r'<STAT;(.*?)>'
        match = re.search(pattern, message)
        if not match:
            return None
        
        status_data = {}
        fields = match.group(1).split(';')
        
        for field in fields:
            if '=' in field:
                key, value = field.split('=', 1)
                # Sayısal değerleri dönüştür
                try:
                    if '.' in value:
                        status_data[key] = float(value)
                    else:
                        status_data[key] = int(value)
                except ValueError:
                    status_data[key] = value
        
        status_data['timestamp'] = datetime.now().isoformat()
        return status_data
    
    def _read_status_messages(self):
        """Seri porttan durum mesajlarını oku"""
        if not self.serial_connection or not self.serial_connection.is_open:
            return
        
        try:
            # Mevcut buffer'ı temizle
            self.serial_connection.reset_input_buffer()
            
            # Status mesajı bekle (timeout: 1 saniye)
            line = self.serial_connection.readline().decode('utf-8', errors='ignore').strip()
            
            if line and '<STAT;' in line:
                status = self._parse_status_message(line)
                if status:
                    with self.status_lock:
                        self.last_status = status
                    esp32_logger.debug(f"Status güncellendi: {status.get('STATE', 'N/A')}")
                    log_esp32_message("status", "rx", data=status)
        
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
    
    def _monitor_loop(self):
        """
        Durum izleme döngüsü
        
        Exception handling ile korumalı - loop crash etmez.
        """
        while self._monitor_running:
            try:
                if self.is_connected:
                    self._read_status_messages()
            except Exception as e:
                # Loop crash etmemeli - hata logla ve devam et
                esp32_logger.error(f"Monitor loop error: {e}", exc_info=True)
                # Kısa bir bekleme sonrası devam et
                time.sleep(0.5)
            else:
                time.sleep(0.1)  # 100ms bekleme
    
    def get_status(self) -> Optional[Dict[str, Any]]:
        """
        Son durum bilgisini al
        
        Returns:
            Durum dict'i veya None
        """
        with self.status_lock:
            return self.last_status.copy() if self.last_status else None
    
    def get_status_sync(self, timeout: float = 2.0) -> Optional[Dict[str, Any]]:
        """
        Status komutu gönder ve yanıt bekle (senkron)
        
        Args:
            timeout: Timeout süresi (saniye)
        
        Returns:
            Durum dict'i veya None
        """
        if not self.send_status_request():
            return None
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.get_status()
            if status:
                return status
            time.sleep(0.1)
        
        return None


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

