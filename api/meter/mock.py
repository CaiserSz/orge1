"""
Mock Meter Implementation
Created: 2025-12-10 07:00:00
Last Modified: 2025-12-10 07:00:00
Version: 1.0.0
Description: Meter entegrasyonu olmadığında kullanılan mock implementation
"""

from typing import Optional
from api.meter.interface import MeterInterface, MeterReading
from api.logging_config import system_logger


class MockMeter(MeterInterface):
    """
    Mock meter implementation

    Meter entegrasyonu olmadığında kullanılır.
    Tüm değerler None döner (meter yok anlamında).
    """

    def __init__(self):
        """Mock meter başlatıcı"""
        self._connected = False
        self._start_energy = None
        self._last_reading_time = None

    def connect(self) -> bool:
        """Meter'a bağlan (mock)"""
        self._connected = True
        system_logger.debug("Mock meter connected (no actual meter)")
        return True

    def disconnect(self) -> bool:
        """Meter bağlantısını kes"""
        self._connected = False
        return True

    def is_connected(self) -> bool:
        """Meter bağlantısı aktif mi?"""
        return self._connected

    def read_energy(self) -> Optional[float]:
        """
        Toplam enerji okuma (kWh)

        Returns:
            None (meter yok)
        """
        return None

    def read_power(self) -> Optional[float]:
        """
        Anlık güç okuma (kW)

        Returns:
            None (meter yok)
        """
        return None

    def read_voltage(self) -> Optional[float]:
        """
        Voltaj okuma (V)

        Returns:
            None (meter yok)
        """
        return None

    def read_current(self) -> Optional[float]:
        """
        Akım okuma (A)

        Returns:
            None (meter yok)
        """
        return None

    def read_all(self) -> Optional[MeterReading]:
        """
        Tüm meter değerlerini oku

        Returns:
            None (meter yok)
        """
        return None

    def reset_energy_counter(self) -> bool:
        """
        Enerji sayacını sıfırla

        Returns:
            False (meter yok)
        """
        return False
