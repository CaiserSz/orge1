"""
Acrel ADL400/T317 Modbus Meter Implementation
Created: 2025-12-12 18:54:25
Last Modified: 2025-12-13 20:47:00
Version: 1.0.1
Description: Acrel three-phase meter (ADL400/T317) Modbus RTU reader
"""

import struct
import threading
import time
from typing import Optional, Tuple

from pymodbus.client import ModbusSerialClient

from api.logging_config import system_logger
from api.meter.interface import MeterInterface, MeterReading


def _to_float(regs: Tuple[int, int]) -> Optional[float]:
    try:
        return struct.unpack(">f", struct.pack(">HH", regs[0], regs[1]))[0]
    except Exception:
        return None


def _to_uint32(regs: Tuple[int, int, int, int]) -> Optional[int]:
    try:
        return struct.unpack(
            ">I", struct.pack(">HHHH", regs[0], regs[1], regs[2], regs[3])
        )[0]
    except Exception:
        return None


class AcrelModbusMeter(MeterInterface):
    """
    Acrel ADL400/T317 Modbus RTU meter.

    Varsayılan bağlantı: 9600 baud, Even parity, 8N1, slave id configurable (default 1).
    """

    def __init__(
        self,
        port: str = "/dev/ttyAMA5",
        baudrate: int = 9600,
        slave_id: int = 1,
        timeout: float = 1.0,
    ):
        self.port = port
        self.baudrate = baudrate
        self.slave_id = slave_id
        self.timeout = timeout
        self._lock = threading.RLock()
        self._client: Optional[ModbusSerialClient] = None

    def connect(self) -> bool:
        with self._lock:
            try:
                if self._client is None:
                    self._client = ModbusSerialClient(
                        port=self.port,
                        baudrate=self.baudrate,
                        parity="E",
                        stopbits=1,
                        bytesize=8,
                        timeout=self.timeout,
                    )
                return bool(self._client.connect())
            except Exception as e:
                system_logger.warning(f"Acrel meter connect error: {e}", exc_info=True)
                return False

    def disconnect(self) -> bool:
        with self._lock:
            try:
                if self._client:
                    self._client.close()
                self._client = None
            except Exception as e:
                system_logger.warning(
                    f"Acrel meter disconnect error: {e}", exc_info=True
                )
            return True

    def is_connected(self) -> bool:
        with self._lock:
            return bool(self._client and self._client.connected)

    def _read_regs(self, address: int, count: int) -> Optional[Tuple[int, ...]]:
        if not self.is_connected() and not self.connect():
            return None
        assert self._client
        rr = self._client.read_holding_registers(
            address, count=count, device_id=self.slave_id
        )
        if rr.isError():
            return None
        return tuple(rr.registers)

    def _read_float(self, address: int) -> Optional[float]:
        regs = self._read_regs(address, 2)
        if not regs:
            return None
        return _to_float(regs)

    def _read_uint32_scaled(self, address: int, scale: float = 1.0) -> Optional[float]:
        """
        Acrel ADL400/T317 enerji register'ları 2 word (32-bit) döndürüyor; 4 word değil.
        """
        regs = self._read_regs(address, 2)
        if not regs:
            return None
        # 2 word -> 32-bit big-endian
        try:
            val = struct.unpack(">I", struct.pack(">HH", regs[0], regs[1]))[0]
        except Exception:
            return None
        return val * scale

    def read_energy(self) -> Optional[float]:
        reading = self.read_all()
        return reading.energy_kwh if reading and reading.is_valid else None

    def read_power(self) -> Optional[float]:
        reading = self.read_all()
        return reading.power_kw if reading and reading.is_valid else None

    def read_voltage(self) -> Optional[float]:
        reading = self.read_all()
        return reading.voltage_v if reading and reading.is_valid else None

    def read_current(self) -> Optional[float]:
        reading = self.read_all()
        return reading.current_a if reading and reading.is_valid else None

    def read_all(self) -> Optional[MeterReading]:
        with self._lock:
            if not self.is_connected() and not self.connect():
                return None
            try:
                # Primary side floats (after CT/PT ratio)
                va = self._read_float(0x0800)
                vb = self._read_float(0x0802)
                vc = self._read_float(0x0804)
                ia = self._read_float(0x080C)
                ib = self._read_float(0x080E)
                ic = self._read_float(0x0810)

                # Power registers (kW) - saha testinde 0x0818'in L3 olabildiği görüldü.
                # Total power'ı mümkünse faz toplamı veya V/I türetimi ile normalize ediyoruz.
                p_l1 = self._read_float(0x0814)
                p_l2 = self._read_float(0x0816)
                p_0818 = self._read_float(0x0818)
                pf_total = self._read_float(0x0832)
                freq = self._read_float(0x0834)

                # Active energy (kWh) primary side, resolution 0.1 kWh (2-word registers)
                e_total = self._read_uint32_scaled(0x0842, 0.1)
                e_fwd = self._read_uint32_scaled(0x084C, 0.1)
                e_rev = self._read_uint32_scaled(0x0856, 0.1)

                # Total power decide
                pf_safe = float(pf_total) if pf_total is not None else 1.0
                p_vi = None
                if all(v is not None for v in (va, vb, vc, ia, ib, ic)):
                    try:
                        p_vi = ((va * ia) + (vb * ib) + (vc * ic)) / 1000.0
                        p_vi = p_vi * pf_safe
                    except Exception:
                        p_vi = None

                p_sum = (
                    (p_l1 or 0.0) + (p_l2 or 0.0) + (p_0818 or 0.0)
                    if any(v is not None for v in (p_l1, p_l2, p_0818))
                    else None
                )

                p_total = None
                p_l3 = None
                if p_vi is not None and p_0818 is not None and p_sum is not None:
                    # V/I türetimine daha yakın olanı seç
                    err_reg = abs(p_0818 - p_vi)
                    err_sum = abs(p_sum - p_vi)
                    if err_sum <= err_reg:
                        p_total = p_sum
                        p_l3 = p_0818
                    else:
                        p_total = p_0818
                        p_l3 = None
                elif p_sum is not None and p_sum > 0:
                    p_total = p_sum
                    p_l3 = p_0818
                else:
                    p_total = p_0818
                    p_l3 = None

                if p_total is None or e_total is None:
                    return None

                voltage_v = va or vb or vc
                current_a = ia or ib or ic

                reading = MeterReading(
                    timestamp=time.time(),
                    energy_kwh=float(e_total),
                    power_kw=float(p_total),
                    voltage_v=float(voltage_v) if voltage_v is not None else 0.0,
                    current_a=float(current_a) if current_a is not None else 0.0,
                    frequency_hz=float(freq) if freq is not None else None,
                    is_valid=True,
                )

                # Optional fields
                setattr(reading, "power_w", float(p_total) * 1000.0)
                if pf_total is not None:
                    setattr(reading, "power_factor", float(pf_total))
                setattr(
                    reading,
                    "phase_values",
                    {
                        "voltage_v": {"l1": va, "l2": vb, "l3": vc},
                        "current_a": {"l1": ia, "l2": ib, "l3": ic},
                        "power_kw": {
                            "l1": p_l1,
                            "l2": p_l2,
                            "l3": p_l3,
                            "total": float(p_total),
                        },
                    },
                )
                setattr(
                    reading,
                    "totals",
                    {
                        "power_kw": float(p_total),
                        "energy_kwh": float(e_total),
                        "energy_import_kwh": (
                            float(e_fwd) if e_fwd is not None else None
                        ),
                        "energy_export_kwh": (
                            float(e_rev) if e_rev is not None else None
                        ),
                    },
                )

                return reading
            except Exception as e:
                system_logger.warning(f"Acrel meter read error: {e}", exc_info=True)
                return None

    def reset_energy_counter(self) -> bool:
        # Not implemented for Acrel
        return False
