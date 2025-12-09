"""
ABB Meter RS485 Okuma Modülü
Created: 2025-12-09 02:50:00
Last Modified: 2025-12-09 02:50:00
Version: 1.0.0
Description: ABB meter'dan RS485 üzerinden Modbus RTU protokolü ile veri okuma
"""

import serial
import time
import struct
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

# RS485/UART5 Konfigürasyonu
# GPIO 12 (TX) -> MAX13487 Pin 4 (DI)
# GPIO 13 (RX) <- MAX13487 Pin 1 (RO)
# UART5 -> /dev/ttyAMA4 (dtoverlay=uart5 sonrası)

UART5_DEVICE = "/dev/ttyAMA4"  # UART5 cihaz dosyası
DEFAULT_BAUDRATE = 9600  # ABB meter için tipik baudrate (model'e göre değişebilir)
DEFAULT_SLAVE_ID = 1  # Modbus slave ID (meter'a göre ayarlanmalı)
DEFAULT_TIMEOUT = 1.0  # Timeout (saniye)

# Modbus RTU Function Codes
MODBUS_READ_HOLDING_REGISTERS = 0x03
MODBUS_READ_INPUT_REGISTERS = 0x04
MODBUS_READ_COILS = 0x01
MODBUS_READ_DISCRETE_INPUTS = 0x02

# ABB Meter Register Adresleri
# Model: ABB B23 112-100
# NOT: Gerçek register adresleri meter dokümantasyonundan alınmalı
# Şu anki değerler örnek/placeholder - AC istasyonu açıldığında güncellenecek

ABB_METER_MODEL = "ABB B23 112-100"
ABB_METER_SPECS = {
    "voltage": "3x220/380V veya 3x240/415V",
    "current_range": "0.25-5(65)A",
    "frequency": "50 or 60 Hz",
    "accuracy_class": "kWh Cl. B (1)",
    "impulse_rate": "1000 imp/kW"
}

# ABB Meter Register Adresleri (örnek - gerçek adresler meter modeline göre değişir)
# Bu adresler ABB meter dokümantasyonundan alınmalı
# AC istasyonu açıldığında meter dokümantasyonu kontrol edilecek
ABB_REGISTERS = {
    "voltage_l1": 0x0000,  # L1 voltajı (V) - ÖRNEK
    "voltage_l2": 0x0001,  # L2 voltajı (V) - ÖRNEK
    "voltage_l3": 0x0002,  # L3 voltajı (V) - ÖRNEK
    "current_l1": 0x0003,  # L1 akımı (A) - ÖRNEK
    "current_l2": 0x0004,  # L2 akımı (A) - ÖRNEK
    "current_l3": 0x0005,  # L3 akımı (A) - ÖRNEK
    "power_active": 0x0006,  # Aktif güç (W) - ÖRNEK
    "power_reactive": 0x0007,  # Reaktif güç (VAR) - ÖRNEK
    "power_apparent": 0x0008,  # Görünür güç (VA) - ÖRNEK
    "energy_active": 0x0009,  # Aktif enerji (kWh) - ÖRNEK
    "energy_reactive": 0x000A,  # Reaktif enerji (kVARh) - ÖRNEK
    "frequency": 0x000B,  # Frekans (Hz) - ÖRNEK
}


class ABBMeterReader:
    """
    ABB Meter RS485 Modbus RTU okuyucu sınıfı
    """
    
    def __init__(self, 
                 device: str = UART5_DEVICE,
                 baudrate: int = DEFAULT_BAUDRATE,
                 slave_id: int = DEFAULT_SLAVE_ID,
                 timeout: float = DEFAULT_TIMEOUT):
        """
        ABB Meter Reader başlatıcı
        
        Args:
            device: Serial port cihaz dosyası (örn: /dev/ttyAMA4)
            baudrate: Baudrate (genellikle 9600 veya 19200)
            slave_id: Modbus slave ID (meter adresi)
            timeout: Timeout süresi (saniye)
        """
        self.device = device
        self.baudrate = baudrate
        self.slave_id = slave_id
        self.timeout = timeout
        self.serial_connection: Optional[serial.Serial] = None
        self.is_connected = False
        
        # Logging setup
        self.logger = logging.getLogger(__name__)
        
    def connect(self) -> bool:
        """
        RS485 seri port bağlantısını aç
        
        Returns:
            Başarı durumu
        """
        try:
            if self.serial_connection and self.serial_connection.is_open:
                self.disconnect()
            
            # RS485 için özel ayarlar
            self.serial_connection = serial.Serial(
                port=self.device,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_EVEN,  # Modbus RTU genellikle EVEN parity kullanır
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout
            )
            
            # RS485 için RTS kontrolü (MAX13487 için gerekli olabilir)
            # self.serial_connection.rts = True  # TX modu
            # self.serial_connection.dtr = False
            
            time.sleep(0.1)  # Port'un hazır olması için bekle
            self.is_connected = True
            
            self.logger.info(f"ABB Meter'a bağlandı: {self.device} (baudrate: {self.baudrate})")
            return True
            
        except serial.SerialException as e:
            self.logger.error(f"ABB Meter bağlantı hatası: {e}")
            self.is_connected = False
            return False
        except Exception as e:
            self.logger.error(f"Beklenmeyen hata: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """RS485 seri port bağlantısını kapat"""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
        self.is_connected = False
        self.logger.info("ABB Meter bağlantısı kapatıldı")
    
    def _calculate_crc16(self, data: bytes) -> int:
        """
        Modbus RTU CRC16 hesaplama
        
        Args:
            data: CRC hesaplanacak veri
            
        Returns:
            CRC16 değeri (2 byte)
        """
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc
    
    def _build_modbus_request(self, 
                              function_code: int,
                              start_address: int,
                              quantity: int) -> bytes:
        """
        Modbus RTU request paketi oluştur
        
        Args:
            function_code: Modbus function code
            start_address: Başlangıç register adresi
            quantity: Okunacak register sayısı
            
        Returns:
            Modbus RTU request paketi (bytes)
        """
        # Paket: [Slave ID] [Function Code] [Start Address High] [Start Address Low] 
        #        [Quantity High] [Quantity Low] [CRC Low] [CRC High]
        request = struct.pack('>BBHH', 
                             self.slave_id,
                             function_code,
                             start_address,
                             quantity)
        
        # CRC hesapla ve ekle
        crc = self._calculate_crc16(request)
        request += struct.pack('<H', crc)  # Little-endian CRC
        
        return request
    
    def _parse_modbus_response(self, response: bytes) -> Optional[List[int]]:
        """
        Modbus RTU response paketini parse et
        
        Args:
            response: Modbus RTU response paketi
            
        Returns:
            Register değerleri listesi veya None (hata durumunda)
        """
        if len(response) < 5:  # Minimum response uzunluğu
            return None
        
        # Response formatı: [Slave ID] [Function Code] [Byte Count] [Data...] [CRC Low] [CRC High]
        slave_id = response[0]
        function_code = response[1]
        
        if slave_id != self.slave_id:
            self.logger.warning(f"Slave ID uyuşmazlığı: beklenen {self.slave_id}, alınan {slave_id}")
            return None
        
        if function_code & 0x80:  # Error response
            error_code = response[2]
            self.logger.error(f"Modbus hatası: function_code=0x{function_code:02X}, error=0x{error_code:02X}")
            return None
        
        byte_count = response[2]
        data = response[3:3+byte_count]
        crc_received = struct.unpack('<H', response[-2:])[0]
        
        # CRC kontrolü
        crc_calculated = self._calculate_crc16(response[:-2])
        if crc_received != crc_calculated:
            self.logger.error(f"CRC hatası: beklenen 0x{crc_calculated:04X}, alınan 0x{crc_received:04X}")
            return None
        
        # Register değerlerini parse et (her register 2 byte)
        registers = []
        for i in range(0, len(data), 2):
            if i + 1 < len(data):
                value = struct.unpack('>H', data[i:i+2])[0]  # Big-endian 16-bit
                registers.append(value)
        
        return registers
    
    def read_holding_registers(self, 
                              start_address: int,
                              quantity: int) -> Optional[List[int]]:
        """
        Holding register'ları oku (Function Code 0x03)
        
        Args:
            start_address: Başlangıç register adresi
            quantity: Okunacak register sayısı
            
        Returns:
            Register değerleri listesi veya None (hata durumunda)
        """
        if not self.is_connected or not self.serial_connection or not self.serial_connection.is_open:
            self.logger.error("ABB Meter bağlantısı yok")
            return None
        
        try:
            # Request paketi oluştur
            request = self._build_modbus_request(
                MODBUS_READ_HOLDING_REGISTERS,
                start_address,
                quantity
            )
            
            # Buffer'ı temizle
            self.serial_connection.reset_input_buffer()
            self.serial_connection.reset_output_buffer()
            
            # Request gönder
            self.serial_connection.write(request)
            self.serial_connection.flush()
            
            # Response bekle
            time.sleep(0.05)  # Modbus RTU için tipik bekleme süresi
            
            # Response oku
            response = self.serial_connection.read(5 + quantity * 2 + 2)  # Min response + data + CRC
            
            if len(response) < 5:
                self.logger.error(f"Yetersiz response: {len(response)} byte")
                return None
            
            # Response parse et
            registers = self._parse_modbus_response(response)
            return registers
            
        except Exception as e:
            self.logger.error(f"Register okuma hatası: {e}")
            return None
    
    def read_input_registers(self,
                            start_address: int,
                            quantity: int) -> Optional[List[int]]:
        """
        Input register'ları oku (Function Code 0x04)
        
        Args:
            start_address: Başlangıç register adresi
            quantity: Okunacak register sayısı
            
        Returns:
            Register değerleri listesi veya None (hata durumunda)
        """
        if not self.is_connected or not self.serial_connection or not self.serial_connection.is_open:
            self.logger.error("ABB Meter bağlantısı yok")
            return None
        
        try:
            # Request paketi oluştur
            request = self._build_modbus_request(
                MODBUS_READ_INPUT_REGISTERS,
                start_address,
                quantity
            )
            
            # Buffer'ı temizle
            self.serial_connection.reset_input_buffer()
            self.serial_connection.reset_output_buffer()
            
            # Request gönder
            self.serial_connection.write(request)
            self.serial_connection.flush()
            
            # Response bekle
            time.sleep(0.05)
            
            # Response oku
            response = self.serial_connection.read(5 + quantity * 2 + 2)
            
            if len(response) < 5:
                self.logger.error(f"Yetersiz response: {len(response)} byte")
                return None
            
            # Response parse et
            registers = self._parse_modbus_response(response)
            return registers
            
        except Exception as e:
            self.logger.error(f"Input register okuma hatası: {e}")
            return None
    
    def read_meter_data(self) -> Optional[Dict[str, Any]]:
        """
        ABB meter'dan tüm önemli verileri oku
        
        Returns:
            Meter verileri dict'i veya None (hata durumunda)
        """
        if not self.is_connected:
            if not self.connect():
                return None
        
        meter_data = {
            "timestamp": datetime.now().isoformat(),
            "slave_id": self.slave_id,
            "device": self.device
        }
        
        try:
            # Örnek: Voltaj değerlerini oku (L1, L2, L3)
            # NOT: Gerçek register adresleri ABB meter dokümantasyonundan alınmalı
            voltage_registers = self.read_input_registers(ABB_REGISTERS["voltage_l1"], 3)
            if voltage_registers:
                meter_data["voltage_l1"] = voltage_registers[0] / 10.0 if len(voltage_registers) > 0 else None
                meter_data["voltage_l2"] = voltage_registers[1] / 10.0 if len(voltage_registers) > 1 else None
                meter_data["voltage_l3"] = voltage_registers[2] / 10.0 if len(voltage_registers) > 2 else None
            
            # Akım değerlerini oku
            current_registers = self.read_input_registers(ABB_REGISTERS["current_l1"], 3)
            if current_registers:
                meter_data["current_l1"] = current_registers[0] / 100.0 if len(current_registers) > 0 else None
                meter_data["current_l2"] = current_registers[1] / 100.0 if len(current_registers) > 1 else None
                meter_data["current_l3"] = current_registers[2] / 100.0 if len(current_registers) > 2 else None
            
            # Aktif güç oku
            power_registers = self.read_input_registers(ABB_REGISTERS["power_active"], 1)
            if power_registers:
                meter_data["power_active_w"] = power_registers[0] if len(power_registers) > 0 else None
            
            # Aktif enerji oku
            energy_registers = self.read_input_registers(ABB_REGISTERS["energy_active"], 1)
            if energy_registers:
                meter_data["energy_active_kwh"] = energy_registers[0] / 100.0 if len(energy_registers) > 0 else None
            
            # Frekans oku
            freq_registers = self.read_input_registers(ABB_REGISTERS["frequency"], 1)
            if freq_registers:
                meter_data["frequency_hz"] = freq_registers[0] / 100.0 if len(freq_registers) > 0 else None
            
            return meter_data
            
        except Exception as e:
            self.logger.error(f"Meter veri okuma hatası: {e}")
            return None
    
    def test_connection(self) -> bool:
        """
        Meter bağlantısını test et
        
        Returns:
            Başarı durumu
        """
        if not self.is_connected:
            if not self.connect():
                return False
        
        try:
            # Basit bir register okuma denemesi (genellikle 0x0000 adresi mevcuttur)
            result = self.read_input_registers(0x0000, 1)
            if result is not None:
                self.logger.info(f"Meter bağlantı testi başarılı: {result}")
                return True
            else:
                self.logger.warning("Meter bağlantı testi başarısız: response alınamadı")
                return False
        except Exception as e:
            self.logger.error(f"Meter bağlantı testi hatası: {e}")
            return False


# Singleton instance
_meter_reader_instance: Optional[ABBMeterReader] = None


def get_meter_reader() -> ABBMeterReader:
    """ABB Meter Reader singleton instance'ı al"""
    global _meter_reader_instance
    if _meter_reader_instance is None:
        _meter_reader_instance = ABBMeterReader()
    return _meter_reader_instance


if __name__ == "__main__":
    # Test script
    import sys
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    print("ABB Meter RS485 Test")
    print("=" * 50)
    
    reader = ABBMeterReader()
    
    # Bağlantı testi
    print(f"\n1. Bağlantı testi: {reader.device}")
    if reader.test_connection():
        print("✅ Meter bağlantısı başarılı!")
        
        # Meter verilerini oku
        print("\n2. Meter verilerini okuma...")
        data = reader.read_meter_data()
        if data:
            print("✅ Meter verileri okundu:")
            import json
            print(json.dumps(data, indent=2))
        else:
            print("❌ Meter verileri okunamadı")
    else:
        print("❌ Meter bağlantısı başarısız!")
        print("\nKontrol edilmesi gerekenler:")
        print(f"  - UART5 aktif mi? (dtoverlay=uart5)")
        print(f"  - Cihaz dosyası mevcut mu? ({reader.device})")
        print(f"  - RS485 bağlantıları doğru mu?")
        print(f"  - Baudrate doğru mu? ({reader.baudrate})")
        print(f"  - Slave ID doğru mu? ({reader.slave_id})")
        sys.exit(1)
    
    reader.disconnect()

