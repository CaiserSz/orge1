"""
Meter Interface
Created: 2025-12-10 07:00:00
Last Modified: 2025-12-10 07:00:00
Version: 1.0.0
Description: Energy meter interface tanımları
"""

from abc import ABC, abstractmethod
import threading
from typing import Optional
from dataclasses import dataclass

from api.config import config


@dataclass
class MeterReading:
    """
    Meter okuma sonucu

    Attributes:
        timestamp: Okuma zamanı (Unix timestamp)
        energy_kwh: Toplam enerji (kWh)
        power_kw: Anlık güç (kW)
        voltage_v: Voltaj (V)
        current_a: Akım (A)
        frequency_hz: Frekans (Hz) - opsiyonel
        is_valid: Okuma geçerli mi?
    """

    timestamp: float
    energy_kwh: float
    power_kw: float
    voltage_v: float
    current_a: float
    frequency_hz: Optional[float] = None
    is_valid: bool = True


class MeterInterface(ABC):
    """
    Energy meter interface

    Bu interface, farklı meter tipleri (Modbus, MQTT, vb.) için
    ortak bir abstraction sağlar.
    """

    @abstractmethod
    def connect(self) -> bool:
        """
        Meter'a bağlan

        Returns:
            Başarı durumu
        """
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """
        Meter bağlantısını kes

        Returns:
            Başarı durumu
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """
        Meter bağlantısı aktif mi?

        Returns:
            Bağlantı durumu
        """
        pass

    @abstractmethod
    def read_energy(self) -> Optional[float]:
        """
        Toplam enerji okuma (kWh)

        Returns:
            Toplam enerji (kWh) veya None
        """
        pass

    @abstractmethod
    def read_power(self) -> Optional[float]:
        """
        Anlık güç okuma (kW)

        Returns:
            Anlık güç (kW) veya None
        """
        pass

    @abstractmethod
    def read_voltage(self) -> Optional[float]:
        """
        Voltaj okuma (V)

        Returns:
            Voltaj (V) veya None
        """
        pass

    @abstractmethod
    def read_current(self) -> Optional[float]:
        """
        Akım okuma (A)

        Returns:
            Akım (A) veya None
        """
        pass

    @abstractmethod
    def read_all(self) -> Optional[MeterReading]:
        """
        Tüm meter değerlerini oku

        Returns:
            MeterReading objesi veya None
        """
        pass

    @abstractmethod
    def reset_energy_counter(self) -> bool:
        """
        Enerji sayacını sıfırla (opsiyonel)

        Returns:
            Başarı durumu
        """
        pass


# Singleton instance
_meter_instance: Optional[MeterInterface] = None
_meter_lock = threading.Lock()


def get_meter() -> MeterInterface:
    """
    Meter singleton instance'ı döndür

    Returns:
        MeterInterface instance
    """
    global _meter_instance

    if _meter_instance is not None:
        return _meter_instance

    with _meter_lock:
        if _meter_instance is not None:
            return _meter_instance

        meter_type = getattr(config, "METER_TYPE", "mock") or "mock"
        meter_type = str(meter_type).lower()

        if meter_type == "abb":
            from api.meter.modbus import ModbusMeter

            _meter_instance = ModbusMeter(
                port=getattr(config, "METER_PORT", "/dev/ttyAMA5"),
                baudrate=getattr(config, "METER_BAUDRATE", 9600),
                slave_id=getattr(config, "METER_SLAVE_ID", 1),
                timeout=getattr(config, "METER_TIMEOUT", 1.0),
            )
        elif meter_type == "acrel":
            from api.meter.acrel import AcrelModbusMeter

            _meter_instance = AcrelModbusMeter(
                port=getattr(config, "METER_PORT", "/dev/ttyAMA5"),
                baudrate=getattr(config, "METER_BAUDRATE", 9600),
                slave_id=getattr(config, "METER_SLAVE_ID", 1),
                timeout=getattr(config, "METER_TIMEOUT", 1.0),
            )
        else:
            from api.meter.mock import MockMeter

            _meter_instance = MockMeter()

        # Not: connect() denemesi burada yapılmaz. (Side-effect istemiyoruz)
        # Bağlanma denemesi startup aşamasında (SessionManager) veya endpoint içinde yapılabilir.

    return _meter_instance
