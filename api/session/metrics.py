"""
Session Metrics Calculator
Created: 2025-12-10 07:25:00
Last Modified: 2025-12-10 07:25:00
Version: 1.0.0
Description: Session metriklerini hesaplayan sınıf
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import sys
import os

# Logging modülünü import et
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from api.event_detector import ESP32State


def calculate_power(
    current_a: Optional[float], voltage_v: Optional[float]
) -> Optional[float]:
    """
    Güç hesaplama: P = V × I

    Args:
        current_a: Akım (Amper)
        voltage_v: Voltaj (Volt)

    Returns:
        Güç (kW) veya None
    """
    if current_a is None or voltage_v is None:
        return None

    power_w = current_a * voltage_v  # Watt
    power_kw = power_w / 1000.0  # Kilowatt
    return round(power_kw, 3)


def calculate_energy(
    power_kw: Optional[float], duration_hours: float
) -> Optional[float]:
    """
    Enerji hesaplama: E = P × t

    Args:
        power_kw: Güç (kW)
        duration_hours: Süre (saat)

    Returns:
        Enerji (kWh) veya None
    """
    if power_kw is None or duration_hours is None:
        return None

    energy_kwh = power_kw * duration_hours
    return round(energy_kwh, 3)


class SessionMetricsCalculator:
    """
    Session metriklerini hesaplayan sınıf

    Event'lerden metrik çıkarır ve hesaplar.
    """

    def __init__(self):
        """Metrics calculator başlatıcı"""
        self.currents: List[float] = []
        self.voltages: List[float] = []
        self.powers: List[float] = []
        self.charging_start_time: Optional[datetime] = None
        self.set_current: Optional[float] = None

    def add_event(self, event: Dict[str, Any]):
        """
        Event ekle ve metrikleri güncelle

        Args:
            event: Event dict'i
        """
        status = event.get("data", {}).get("status", {})
        if not status:
            return

        # Akım bilgilerini çıkar
        current_a = status.get("CABLE")  # Cable current (gerçek akım)
        if current_a is None:
            current_a = status.get("CURRENT")  # Fallback

        # Voltaj bilgilerini çıkar
        voltage_v = status.get("CPV")  # Control Pilot Voltage
        if voltage_v is None:
            voltage_v = status.get("PPV")  # Pilot Point Voltage (fallback)

        # Set current (MAX)
        if self.set_current is None:
            max_current = status.get("MAX")
            if max_current is not None:
                self.set_current = float(max_current)

        # Akım ekle
        if current_a is not None:
            self.currents.append(float(current_a))

        # Voltaj ekle
        if voltage_v is not None:
            self.voltages.append(float(voltage_v))

        # Güç hesapla ve ekle
        if current_a is not None and voltage_v is not None:
            power_kw = calculate_power(current_a, voltage_v)
            if power_kw is not None:
                self.powers.append(power_kw)

        # Charging state kontrolü
        to_state = event.get("data", {}).get("to_state")
        if to_state == ESP32State.CHARGING.value:
            if self.charging_start_time is None:
                timestamp_str = event.get("timestamp")
                if timestamp_str:
                    try:
                        self.charging_start_time = datetime.fromisoformat(timestamp_str)
                    except (ValueError, TypeError):
                        pass

    def calculate_metrics(
        self, start_time: datetime, end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Tüm metrikleri hesapla

        Args:
            start_time: Session başlangıç zamanı
            end_time: Session bitiş zamanı (opsiyonel)

        Returns:
            Metrikler dict'i
        """
        metrics = {}

        # Süre metrikleri
        if end_time:
            duration = (end_time - start_time).total_seconds()
            metrics["duration_seconds"] = int(duration)

            if self.charging_start_time:
                charging_duration = (
                    end_time - self.charging_start_time
                ).total_seconds()
                metrics["charging_duration_seconds"] = int(charging_duration)
                metrics["idle_duration_seconds"] = int(duration - charging_duration)
            else:
                # Charging start time yoksa, tüm süre idle olarak kabul et
                metrics["charging_duration_seconds"] = 0
                metrics["idle_duration_seconds"] = int(duration)

        # Akım metrikleri
        if self.currents:
            metrics["max_current_a"] = round(max(self.currents), 2)
            metrics["avg_current_a"] = round(sum(self.currents) / len(self.currents), 2)
            metrics["min_current_a"] = round(min(self.currents), 2)

        # Set current
        if self.set_current is not None:
            metrics["set_current_a"] = float(self.set_current)

        # Voltaj metrikleri
        if self.voltages:
            metrics["max_voltage_v"] = round(max(self.voltages), 2)
            metrics["avg_voltage_v"] = round(sum(self.voltages) / len(self.voltages), 2)
            metrics["min_voltage_v"] = round(min(self.voltages), 2)

        # Güç metrikleri
        if self.powers:
            metrics["max_power_kw"] = round(max(self.powers), 3)
            metrics["avg_power_kw"] = round(sum(self.powers) / len(self.powers), 3)
            metrics["min_power_kw"] = round(min(self.powers), 3)

        # Enerji hesaplama (güç × süre)
        if metrics.get("avg_power_kw") and metrics.get("charging_duration_seconds"):
            duration_hours = metrics["charging_duration_seconds"] / 3600.0
            total_energy = calculate_energy(metrics["avg_power_kw"], duration_hours)
            if total_energy is not None:
                metrics["total_energy_kwh"] = round(total_energy, 3)

        return metrics
