"""
ABB Meter RS485 Okuma Modülü
Created: 2025-12-09 02:50:00
Last Modified: 2025-12-22 06:01:00
Version: 1.1.0
Description: ABB meter'dan RS485 üzerinden Modbus RTU protokolü ile veri okuma
"""

import logging
import struct
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import serial

# RS485/UART5 Konfigürasyonu
# GPIO 12 (TX) -> MAX13487 Pin 4 (DI)
# GPIO 13 (RX) <- MAX13487 Pin 1 (RO)
# UART5 -> /dev/ttyAMA5 (dtoverlay=uart5 sonrası)

UART5_DEVICE = "/dev/ttyAMA5"  # UART5 cihaz dosyası (dtoverlay=uart5 sonrası)
DEFAULT_BAUDRATE = 2400  # Sahadaki ayar (meter üzerinden set edildi)
DEFAULT_SLAVE_ID = 1  # Modbus slave ID (meter'a göre ayarlanmalı)
DEFAULT_TIMEOUT = 1.0  # Timeout (saniye)

# Modbus RTU Function Codes
MODBUS_READ_HOLDING_REGISTERS = 0x03
MODBUS_READ_INPUT_REGISTERS = 0x04
MODBUS_READ_COILS = 0x01
MODBUS_READ_DISCRETE_INPUTS = 0x02

# ABB Meter Register Adresleri
# Model: ABB B23 112-100
# Kaynak: ABB B23/B24 User Manual (Modbus register map)

ABB_METER_MODEL = "ABB B23 112-100"
ABB_METER_SPECS = {
    "voltage": "3x220/380V veya 3x240/415V",
    "current_range": "0.25-5(65)A",
    "frequency": "50 or 60 Hz",
    "accuracy_class": "kWh Cl. B (1)",
    "impulse_rate": "1000 imp/kW",
}

ABB_REGISTERS = {
    # Voltage (V) - 2 register (32-bit)
    "voltage_l1": 0x1002,
    "voltage_l2": 0x1004,
    "voltage_l3": 0x1006,
    # Current (mA) - 2 register (32-bit)
    "current_l1": 0x1010,
    "current_l2": 0x1012,
    "current_l3": 0x1014,
    # Active power (W) - 2 register (32-bit signed)
    "power_active_total": 0x102E,
    "power_active_l1": 0x1030,
    "power_active_l2": 0x1032,
    "power_active_l3": 0x1034,
    # Active energy import - 4 register (resolution: 0.01 kWh)
    "energy_active_import": 0x5000,
}


def _u32_from_2regs(reg0: int, reg1: int) -> int:
    """2x16-bit register -> unsigned 32-bit."""
    return (int(reg0) << 16) | int(reg1)


def _s32_from_2regs(reg0: int, reg1: int) -> int:
    """2x16-bit register -> signed 32-bit."""
    value = _u32_from_2regs(reg0, reg1)
    if value & 0x80000000:
        return value - 0x100000000
    return value


def _u64_from_4regs(regs: List[int]) -> int:
    """4x16-bit register -> unsigned 64-bit (big-endian register order)."""
    if len(regs) != 4:
        raise ValueError(f"Expected 4 registers, got {len(regs)}")
    r0, r1, r2, r3 = (int(x) for x in regs)
    return (r0 << 48) | (r1 << 32) | (r2 << 16) | r3


class ABBMeterReader:
    """ABB Meter RS485 (Modbus RTU) okuyucu."""

    def __init__(
        self,
        device: str = UART5_DEVICE,
        baudrate: int = DEFAULT_BAUDRATE,
        slave_id: int = DEFAULT_SLAVE_ID,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        """Reader başlatıcı (device/baudrate/slave_id/timeout)."""
        self.device = device
        self.baudrate = baudrate
        self.slave_id = slave_id
        self.timeout = timeout
        self.serial_connection: Optional[serial.Serial] = None
        self.is_connected = False

        # Logging setup
        self.logger = logging.getLogger(__name__)

    def connect(self) -> bool:
        """RS485 seri port bağlantısını aç."""
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
                timeout=self.timeout,
            )

            # RS485 için RTS kontrolü (MAX13487 için kritik)
            # MAX13487: RTS=HIGH -> TX modu (DE/RE aktif), RTS=LOW -> RX modu
            # RTS sinyalinin veri paketleriyle senkronize olması kritik
            # pyserial otomatik olarak TX sırasında RTS'i HIGH yapar
            # Ancak Modbus RTU için manuel kontrol daha güvenilir

            time.sleep(0.1)  # Port'un hazır olması için bekle
            self.is_connected = True

            self.logger.info(
                f"ABB Meter'a bağlandı: {self.device} (baudrate: {self.baudrate})"
            )
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
        """RS485 seri port bağlantısını kapat."""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
        self.is_connected = False
        self.logger.info("ABB Meter bağlantısı kapatıldı")

    def _calculate_crc16(self, data: bytes) -> int:
        """Modbus RTU CRC16 hesapla."""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc

    def _build_modbus_request(
        self, function_code: int, start_address: int, quantity: int
    ) -> bytes:
        """Modbus RTU request paketi oluştur."""
        # Paket: [Slave ID] [Function Code] [Start Address High] [Start Address Low]
        #        [Quantity High] [Quantity Low] [CRC Low] [CRC High]
        request = struct.pack(
            ">BBHH", self.slave_id, function_code, start_address, quantity
        )

        # CRC hesapla ve ekle
        crc = self._calculate_crc16(request)
        request += struct.pack("<H", crc)  # Little-endian CRC

        return request

    def _parse_modbus_response(self, response: bytes) -> Optional[List[int]]:
        """Modbus RTU response parse et (register listesi veya None)."""
        if len(response) < 5:  # Minimum response uzunluğu
            return None

        # Response formatı: [Slave ID] [Function Code] [Byte Count] [Data...] [CRC Low] [CRC High]
        slave_id = response[0]
        function_code = response[1]

        if slave_id != self.slave_id:
            self.logger.warning(
                f"Slave ID uyuşmazlığı: beklenen {self.slave_id}, alınan {slave_id}"
            )
            return None

        if function_code & 0x80:  # Error response
            error_code = response[2]
            self.logger.error(
                f"Modbus hatası: function_code=0x{function_code:02X}, error=0x{error_code:02X}"
            )
            return None

        byte_count = response[2]
        data = response[3 : 3 + byte_count]
        crc_received = struct.unpack("<H", response[-2:])[0]

        # CRC kontrolü
        crc_calculated = self._calculate_crc16(response[:-2])
        if crc_received != crc_calculated:
            self.logger.error(
                f"CRC hatası: beklenen 0x{crc_calculated:04X}, alınan 0x{crc_received:04X}"
            )
            return None

        # Register değerlerini parse et (her register 2 byte)
        registers = []
        for i in range(0, len(data), 2):
            if i + 1 < len(data):
                value = struct.unpack(">H", data[i : i + 2])[0]  # Big-endian 16-bit
                registers.append(value)

        return registers

    def _send_modbus_request(self, request: bytes) -> Optional[bytes]:
        """Modbus RTU request gönderip response oku (exception response destekli)."""
        if (
            not self.is_connected
            or not self.serial_connection
            or not self.serial_connection.is_open
        ):
            self.logger.error("ABB Meter bağlantısı yok")
            return None

        try:
            # Buffer'ı temizle
            self.serial_connection.reset_input_buffer()
            self.serial_connection.reset_output_buffer()

            # RS485 TX moduna geç (RTS HIGH) - MAX13487 DE/RE aktif
            self.serial_connection.rts = True
            time.sleep(0.005)  # RTS stabilizasyonu

            # Request gönder
            self.serial_connection.write(request)
            self.serial_connection.flush()

            # RS485 RX moduna geç (RTS LOW)
            time.sleep(0.002)
            self.serial_connection.rts = False
            time.sleep(0.005)

            # Response header oku: [slave_id][function_code][byte_count|exception_code]
            header = self.serial_connection.read(3)
            if len(header) < 3:
                self.logger.error(f"Yetersiz response: {len(header)} byte")
                return None

            function_code = header[1]
            if function_code & 0x80:
                # Exception response: toplam 5 byte (3 header + 2 CRC)
                tail = self.serial_connection.read(2)
                return header + tail

            byte_count = header[2]
            tail = self.serial_connection.read(byte_count + 2)  # data + CRC
            return header + tail

        except Exception as e:
            self.logger.error(f"Request/response hatası: {e}")
            return None

    def _read_registers(
        self, function_code: int, start_address: int, quantity: int
    ) -> Optional[List[int]]:
        """Register oku (holding/input)."""
        try:
            request = self._build_modbus_request(function_code, start_address, quantity)
            response = self._send_modbus_request(request)
            if not response or len(response) < 5:
                return None

            return self._parse_modbus_response(response)
        except Exception as e:
            self.logger.error(f"Register okuma hatası: {e}")
            return None

    def read_holding_registers(
        self, start_address: int, quantity: int
    ) -> Optional[List[int]]:
        """Holding register'ları oku (Function Code 0x03)."""
        return self._read_registers(
            MODBUS_READ_HOLDING_REGISTERS, start_address, quantity
        )

    def read_input_registers(
        self, start_address: int, quantity: int
    ) -> Optional[List[int]]:
        """Input register'ları oku (Function Code 0x04)."""
        return self._read_registers(
            MODBUS_READ_INPUT_REGISTERS, start_address, quantity
        )

    def read_meter_data(self) -> Optional[Dict[str, Any]]:
        """ABB meter'dan temel verileri oku (dict) veya None döndür."""
        if not self.is_connected:
            if not self.connect():
                return None

        meter_data = {
            "timestamp": datetime.now().isoformat(),
            "slave_id": self.slave_id,
            "device": self.device,
        }

        try:
            # ABB B23 112-100: Bu cihaz 0x04 yerine 0x03 (holding registers) ile cevap veriyor.

            # Voltaj (V): 0x1002..0x1007 (2 register x 3 faz = 6 register)
            v_regs = self.read_holding_registers(ABB_REGISTERS["voltage_l1"], 6)
            if v_regs and len(v_regs) == 6:
                meter_data["voltage_l1"] = float(_u32_from_2regs(v_regs[0], v_regs[1]))
                meter_data["voltage_l2"] = float(_u32_from_2regs(v_regs[2], v_regs[3]))
                meter_data["voltage_l3"] = float(_u32_from_2regs(v_regs[4], v_regs[5]))

            # Akım (mA): 0x1010..0x1015 (2 register x 3 faz = 6 register)
            i_regs = self.read_holding_registers(ABB_REGISTERS["current_l1"], 6)
            if i_regs and len(i_regs) == 6:
                meter_data["current_l1"] = (
                    _u32_from_2regs(i_regs[0], i_regs[1]) / 1000.0
                )
                meter_data["current_l2"] = (
                    _u32_from_2regs(i_regs[2], i_regs[3]) / 1000.0
                )
                meter_data["current_l3"] = (
                    _u32_from_2regs(i_regs[4], i_regs[5]) / 1000.0
                )

            # Aktif güç (W): 0x102E..0x1035 (total + L1 + L2 + L3)
            p_regs = self.read_holding_registers(ABB_REGISTERS["power_active_total"], 8)
            if p_regs and len(p_regs) == 8:
                meter_data["power_active_w"] = float(
                    _s32_from_2regs(p_regs[0], p_regs[1])
                )
                meter_data["power_l1_w"] = float(_s32_from_2regs(p_regs[2], p_regs[3]))
                meter_data["power_l2_w"] = float(_s32_from_2regs(p_regs[4], p_regs[5]))
                meter_data["power_l3_w"] = float(_s32_from_2regs(p_regs[6], p_regs[7]))

            # Aktif enerji import (0.01 kWh resolution): 0x5000 (4 register)
            e_regs = self.read_holding_registers(
                ABB_REGISTERS["energy_active_import"], 4
            )
            if e_regs and len(e_regs) == 4:
                meter_data["energy_active_kwh"] = _u64_from_4regs(e_regs) / 100.0

            return meter_data

        except Exception as e:
            self.logger.error(f"Meter veri okuma hatası: {e}")
            return None

    def test_connection(self) -> bool:
        """Meter bağlantısını basit register okuması ile test et."""
        if not self.is_connected:
            if not self.connect():
                return False

        try:
            # Basit bir register okuma denemesi (voltage L1 register'ı)
            result = self.read_holding_registers(ABB_REGISTERS["voltage_l1"], 2)
            if result:
                self.logger.info(f"Meter bağlantı testi başarılı: {result}")
                return True
            else:
                self.logger.warning(
                    "Meter bağlantı testi başarısız: response alınamadı"
                )
                return False
        except Exception as e:
            self.logger.error(f"Meter bağlantı testi hatası: {e}")
            return False


_meter_reader_instance: Optional[ABBMeterReader] = None
_meter_lock = threading.Lock()


def get_meter_reader() -> ABBMeterReader:
    """Thread-safe ABBMeterReader singleton."""
    global _meter_reader_instance
    if _meter_reader_instance is None:
        with _meter_lock:
            if _meter_reader_instance is None:
                _meter_reader_instance = ABBMeterReader()
    return _meter_reader_instance


if __name__ == "__main__":
    # Basit manuel test
    import json

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    reader = ABBMeterReader()
    ok = reader.test_connection()
    print(f"meter_ok={ok}")
    if ok:
        print(json.dumps(reader.read_meter_data(), indent=2))
    reader.disconnect()
