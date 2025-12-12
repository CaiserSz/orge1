"""
Modbus Meter Implementation (ABB/RS485)
Created: 2025-12-10 07:00:00
Last Modified: 2025-12-12 21:04:36
Version: 1.1.0
Description: ABB meter (Modbus RTU/RS485) okuyucusu için MeterInterface wrapper
"""

import threading
import time
from typing import Optional

from api.logging_config import system_logger
from api.meter.interface import MeterInterface, MeterReading


def _u32_from_regs(reg0: int, reg1: int) -> int:
    """2x16-bit register -> unsigned 32-bit."""
    return (int(reg0) << 16) | int(reg1)


def _s32_from_regs(reg0: int, reg1: int) -> int:
    """2x16-bit register -> signed 32-bit."""
    value = _u32_from_regs(reg0, reg1)
    if value & 0x80000000:
        return value - 0x100000000
    return value


class ModbusMeter(MeterInterface):
    """
    ABB meter (Modbus RTU/RS485) implementation.

    Notlar:
    - Okuma işlemleri `meter/read_meter.py` içindeki `ABBMeterReader` üzerinden yapılır.
    - Fiziksel bağlantı yoksa connect/read işlemleri False/None döner (sistem çalışmaya devam eder).
    """

    def __init__(
        self,
        port: str = "/dev/ttyAMA5",
        baudrate: int = 9600,
        slave_id: int = 1,
        timeout: float = 1.0,
    ):
        """
        Modbus meter başlatıcı

        Args:
            port: Serial port (RTU), örn: /dev/ttyAMA5
            baudrate: Baudrate (RTU için), örn: 9600
            slave_id: Modbus slave ID (1-247)
            timeout: Serial timeout (saniye)
        """
        self.port = port
        self.baudrate = baudrate
        self.slave_id = slave_id
        self.timeout = timeout

        self._lock = threading.RLock()
        self._reader = None

    def connect(self) -> bool:
        """Meter'a bağlan"""
        with self._lock:
            try:
                if self._reader is None:
                    from meter.read_meter import ABBMeterReader

                    self._reader = ABBMeterReader(
                        device=self.port,
                        baudrate=self.baudrate,
                        slave_id=self.slave_id,
                        timeout=self.timeout,
                    )

                ok = bool(self._reader.connect())
                if ok:
                    system_logger.info(
                        "Meter bağlantısı kuruldu",
                        extra={
                            "meter_type": "abb",
                            "port": self.port,
                            "baudrate": self.baudrate,
                            "slave_id": self.slave_id,
                        },
                    )
                return ok
            except Exception as e:
                system_logger.warning(
                    f"Meter bağlantısı kurulamadı: {e}",
                    exc_info=True,
                    extra={
                        "meter_type": "abb",
                        "port": self.port,
                        "baudrate": self.baudrate,
                        "slave_id": self.slave_id,
                    },
                )
                return False

    def disconnect(self) -> bool:
        """Meter bağlantısını kes"""
        with self._lock:
            try:
                if self._reader is not None:
                    self._reader.disconnect()
            except Exception as e:
                system_logger.warning(f"Meter disconnect hatası: {e}", exc_info=True)
            return True

    def is_connected(self) -> bool:
        """Meter bağlantısı aktif mi?"""
        with self._lock:
            if self._reader is None:
                return False
            return bool(getattr(self._reader, "is_connected", False))

    def read_energy(self) -> Optional[float]:
        """
        Toplam enerji okuma (kWh)

        Returns:
            Toplam enerji (kWh) veya None
        """
        reading = self.read_all()
        if not reading or not reading.is_valid:
            return None
        return reading.energy_kwh

    def read_power(self) -> Optional[float]:
        """
        Anlık güç okuma (kW)

        Returns:
            Anlık güç (kW) veya None
        """
        reading = self.read_all()
        if not reading or not reading.is_valid:
            return None
        return reading.power_kw

    def read_voltage(self) -> Optional[float]:
        """
        Voltaj okuma (V)

        Returns:
            Voltaj (V) veya None
        """
        reading = self.read_all()
        if not reading or not reading.is_valid:
            return None
        return reading.voltage_v

    def read_current(self) -> Optional[float]:
        """
        Akım okuma (A)

        Returns:
            Akım (A) veya None
        """
        reading = self.read_all()
        if not reading or not reading.is_valid:
            return None
        return reading.current_a

    def read_all(self) -> Optional[MeterReading]:
        """
        Tüm meter değerlerini oku

        Returns:
            MeterReading objesi veya None
        """
        with self._lock:
            if not self.is_connected():
                if not self.connect():
                    return None

            if self._reader is None:
                return None

            try:
                data = self._reader.read_meter_data()
            except Exception as e:
                system_logger.warning(f"Meter okuma hatası: {e}", exc_info=True)
                return None

            if not data:
                return None

            energy_kwh = data.get("energy_active_kwh")
            power_w = data.get("power_active_w")

            # Faz bazlı veriler
            voltage_l1 = data.get("voltage_l1")
            voltage_l2 = data.get("voltage_l2")
            voltage_l3 = data.get("voltage_l3")
            current_l1 = data.get("current_l1")
            current_l2 = data.get("current_l2")
            current_l3 = data.get("current_l3")
            power_l1_w = data.get("power_l1_w")
            power_l2_w = data.get("power_l2_w")
            power_l3_w = data.get("power_l3_w")

            # Toplam/temel değerler (fazlardan seçme)
            voltage_v = voltage_l1 or voltage_l2 or voltage_l3
            current_a = current_l1 or current_l2 or current_l3
            frequency_hz = None
            power_factor = None

            # Ek değerler (ABB manual): FC 0x03 holding registers
            # - Power factor: 0x1016 (Signed, *1000)
            # - Frequency: 0x1046 (Unsigned, mHz)
            try:
                pf_regs = self._reader.read_holding_registers(0x1016, 2)
                if pf_regs and len(pf_regs) == 2:
                    power_factor = _s32_from_regs(pf_regs[0], pf_regs[1]) / 1000.0
            except Exception:
                power_factor = None

            try:
                freq_regs = self._reader.read_holding_registers(0x1046, 2)
                if freq_regs and len(freq_regs) == 2:
                    frequency_hz = _u32_from_regs(freq_regs[0], freq_regs[1]) / 1000.0
            except Exception:
                frequency_hz = None

            if (
                energy_kwh is None
                or power_w is None
                or voltage_v is None
                or current_a is None
            ):
                return None

            reading = MeterReading(
                timestamp=time.time(),
                energy_kwh=float(energy_kwh),
                power_kw=float(power_w) / 1000.0,
                voltage_v=float(voltage_v),
                current_a=float(current_a),
                frequency_hz=float(frequency_hz) if frequency_hz is not None else None,
                is_valid=True,
            )

            # Opsiyonel alanlar (router getattr ile okuyor)
            try:
                setattr(reading, "power_w", float(power_w))
            except Exception:
                pass
            try:
                if power_factor is not None:
                    setattr(reading, "power_factor", float(power_factor))
            except Exception:
                pass

            # Faz bazlı değerleri ekle (varsa)
            phase_values = {
                "voltage_v": {
                    "l1": voltage_l1,
                    "l2": voltage_l2,
                    "l3": voltage_l3,
                },
                "current_a": {
                    "l1": current_l1,
                    "l2": current_l2,
                    "l3": current_l3,
                },
                "power_w": {
                    "l1": power_l1_w,
                    "l2": power_l2_w,
                    "l3": power_l3_w,
                },
                "power_kw": {
                    "l1": (
                        float(power_l1_w) / 1000.0 if power_l1_w is not None else None
                    ),
                    "l2": (
                        float(power_l2_w) / 1000.0 if power_l2_w is not None else None
                    ),
                    "l3": (
                        float(power_l3_w) / 1000.0 if power_l3_w is not None else None
                    ),
                },
            }
            setattr(reading, "phase_values", phase_values)

            totals = {
                "power_w": float(power_w),
                "power_kw": float(power_w) / 1000.0,
                "energy_kwh": float(energy_kwh),
            }
            setattr(reading, "totals", totals)

            return reading

    def reset_energy_counter(self) -> bool:
        """
        Enerji sayacını sıfırla

        Returns:
            Başarı durumu
        """
        return False
