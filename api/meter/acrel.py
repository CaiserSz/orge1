"""
Acrel ADL400/T317 Modbus Meter Implementation
Created: 2025-12-12 18:54:25
Last Modified: 2025-12-14 03:58:00
Version: 1.0.3
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
                def _is_nonzero(value: Optional[float]) -> bool:
                    if value is None:
                        return False
                    try:
                        return abs(float(value)) > 0.001
                    except (TypeError, ValueError):
                        return False

                # V/I türetimi (kW): sadece PF mevcutsa aktif güce çevirebiliyoruz
                p_vi = None
                if pf_total is not None and all(
                    v is not None for v in (va, vb, vc, ia, ib, ic)
                ):
                    try:
                        apparent_kw = ((va * ia) + (vb * ib) + (vc * ic)) / 1000.0
                        p_vi = float(apparent_kw) * float(pf_total)
                    except Exception:
                        p_vi = None

                # Register bazlı değerler
                p_reg = p_0818
                phase_candidates = [p_l1, p_l2, p_0818]
                phase_values = [float(v) for v in phase_candidates if v is not None]
                phase_count = len(phase_values)
                p_sum = sum(phase_values) if phase_values else None

                # Öncelik: (1) register toplamı veya faz toplamı p_vi'ya yakınsa onu kullan
                #          (2) aksi halde p_vi (varsa) ile under-reporting'i engelle
                #          (3) p_vi yoksa faz toplamı (en az 2 faz) veya register değerine düş
                p_total = None
                if p_vi is not None and _is_nonzero(p_vi):
                    best_val = None
                    best_rel_err = None

                    for candidate in (p_reg, p_sum if phase_count >= 2 else None):
                        if not _is_nonzero(candidate):
                            continue
                        rel_err = abs(float(candidate) - float(p_vi)) / max(
                            abs(float(p_vi)), 0.001
                        )
                        if best_rel_err is None or rel_err < best_rel_err:
                            best_rel_err = rel_err
                            best_val = float(candidate)

                    if (
                        best_val is not None
                        and best_rel_err is not None
                        and best_rel_err <= 0.15
                    ):
                        p_total = best_val
                    else:
                        p_total = float(p_vi)
                else:
                    if p_sum is not None and _is_nonzero(p_sum) and phase_count >= 2:
                        p_total = float(p_sum)
                    elif _is_nonzero(p_reg):
                        p_total = float(p_reg)
                    else:
                        p_total = None

                # 0x0818 bazı kurulumlarda total olabilir. L3 alanını, total'e oranla ayırt etmeye çalış.
                p_l3 = None
                if p_0818 is not None and p_total is not None:
                    try:
                        if abs(float(p_0818)) <= abs(float(p_total)) * 0.8:
                            p_l3 = p_0818
                    except Exception:
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
                        # Açıklık için alias (bazı UI'lar energy_kwh'ı "total mı import mu?" karıştırabiliyor)
                        "energy_total_kwh": float(e_total),
                        "energy_import_kwh": (
                            float(e_fwd) if e_fwd is not None else None
                        ),
                        "energy_export_kwh": (
                            float(e_rev) if e_rev is not None else None
                        ),
                        # Register referansı (saha doğrulaması için)
                        "registers": {
                            "power_kw_l1": "0x0814 (float32 kW)",
                            "power_kw_l2": "0x0816 (float32 kW)",
                            "power_kw_total_or_l3": "0x0818 (float32 kW, sahada total/L3 değişebiliyor)",
                            "energy_total_kwh": "0x0842 (uint32, scale=0.1 kWh)",
                            "energy_import_kwh": "0x084C (uint32, scale=0.1 kWh)",
                            "energy_export_kwh": "0x0856 (uint32, scale=0.1 kWh)",
                            "pf_total": "0x0832 (float32)",
                            "frequency_hz": "0x0834 (float32)",
                        },
                    },
                )

                return reading
            except Exception as e:
                system_logger.warning(f"Acrel meter read error: {e}", exc_info=True)
                return None

    def reset_energy_counter(self) -> bool:
        # Not implemented for Acrel
        return False
