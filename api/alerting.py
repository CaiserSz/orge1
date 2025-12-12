"""
Alerting Module
Created: 2025-12-10
Last Modified: 2025-12-13 02:05:00
Version: 1.1.0
Description: Alerting rules and notification system for monitoring
"""

from typing import Dict, List, Optional

from api.alerting_models import Alert, AlertRule, AlertSeverity
from api.logging_config import system_logger

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from esp32.bridge import ESP32Bridge
    from api.event_detector import EventDetector

__all__ = ["AlertManager", "get_alert_manager", "Alert", "AlertRule", "AlertSeverity"]


class AlertManager:
    """Alert manager for monitoring and alerting"""

    def __init__(self):
        self.rules: List[AlertRule] = []
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.max_history_size = 1000

        # Initialize default alert rules
        self._initialize_default_rules()

    def _initialize_default_rules(self) -> None:
        """Initialize default alert rules"""

        # ESP32 connection alert
        self.add_rule(
            AlertRule(
                name="esp32_disconnected",
                severity=AlertSeverity.CRITICAL,
                check_function=lambda bridge=None, event_detector=None: self._check_esp32_connection(
                    bridge=bridge, event_detector=event_detector
                ),
            )
        )

        # ESP32 status stale alert
        self.add_rule(
            AlertRule(
                name="esp32_status_stale",
                severity=AlertSeverity.WARNING,
                check_function=lambda bridge=None, event_detector=None: self._check_esp32_status_age(
                    bridge=bridge, event_detector=event_detector
                ),
            )
        )

        # High memory usage alert
        self.add_rule(
            AlertRule(
                name="high_memory_usage",
                severity=AlertSeverity.WARNING,
                check_function=lambda bridge=None, event_detector=None: self._check_memory_usage(
                    bridge=bridge, event_detector=event_detector
                ),
            )
        )

        # High CPU usage alert
        self.add_rule(
            AlertRule(
                name="high_cpu_usage",
                severity=AlertSeverity.WARNING,
                check_function=lambda bridge=None, event_detector=None: self._check_cpu_usage(
                    bridge=bridge, event_detector=event_detector
                ),
            )
        )

        # High disk usage alert
        self.add_rule(
            AlertRule(
                name="high_disk_usage",
                severity=AlertSeverity.WARNING,
                check_function=lambda bridge=None, event_detector=None: self._check_disk_usage(
                    bridge=bridge, event_detector=event_detector
                ),
            )
        )

        # High CPU temperature alert
        self.add_rule(
            AlertRule(
                name="high_cpu_temperature",
                severity=AlertSeverity.CRITICAL,
                check_function=lambda bridge=None, event_detector=None: self._check_cpu_temperature(
                    bridge=bridge, event_detector=event_detector
                ),
            )
        )

        # Event detector stopped alert
        self.add_rule(
            AlertRule(
                name="event_detector_stopped",
                severity=AlertSeverity.WARNING,
                check_function=lambda bridge=None, event_detector=None: self._check_event_detector(
                    bridge=bridge, event_detector=event_detector
                ),
            )
        )

    def add_rule(self, rule: AlertRule) -> None:
        """Add alert rule"""
        self.rules.append(rule)

    def remove_rule(self, name: str) -> None:
        """Remove alert rule"""
        self.rules = [r for r in self.rules if r.name != name]
        if name in self.active_alerts:
            del self.active_alerts[name]

    def evaluate_all(
        self,
        bridge: Optional["ESP32Bridge"] = None,
        event_detector: Optional["EventDetector"] = None,
    ) -> List[Alert]:
        """Evaluate all alert rules"""
        new_alerts = []

        for rule in self.rules:
            alert = rule.evaluate(bridge=bridge, event_detector=event_detector)
            if alert:
                # Check if alert is new or changed
                if rule.name not in self.active_alerts:
                    # New alert
                    self.active_alerts[rule.name] = alert
                    self.alert_history.append(alert)
                    new_alerts.append(alert)

                    # Log alert
                    log_level = {
                        AlertSeverity.INFO: system_logger.info,
                        AlertSeverity.WARNING: system_logger.warning,
                        AlertSeverity.CRITICAL: system_logger.error,
                    }
                    log_func = log_level.get(alert.severity, system_logger.warning)
                    log_func(f"Alert triggered: {alert.name} - {alert.message}")
                else:
                    # Alert already active - check if severity changed
                    old_alert = self.active_alerts[rule.name]
                    if old_alert.severity != alert.severity:
                        self.active_alerts[rule.name] = alert
                        self.alert_history.append(alert)
                        new_alerts.append(alert)
            else:
                # Alert resolved
                if rule.name in self.active_alerts:
                    old_alert = self.active_alerts[rule.name]
                    del self.active_alerts[rule.name]
                    system_logger.info(f"Alert resolved: {rule.name}")

        # Trim alert history
        if len(self.alert_history) > self.max_history_size:
            self.alert_history = self.alert_history[-self.max_history_size :]

        return new_alerts

    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        return list(self.active_alerts.values())

    def get_alert_history(
        self,
        limit: int = 100,
        severity: Optional[AlertSeverity] = None,
    ) -> List[Alert]:
        """Get alert history"""
        history = self.alert_history[-limit:]
        if severity:
            history = [a for a in history if a.severity == severity]
        return history

    # Alert check functions

    def _check_esp32_connection(
        self, bridge=None, event_detector=None
    ) -> Optional[Alert]:
        """Check ESP32 connection status"""
        if bridge and not bridge.is_connected:
            return Alert(
                name="esp32_disconnected",
                severity=AlertSeverity.CRITICAL,
                message="ESP32 is disconnected",
            )
        return None

    def _check_esp32_status_age(
        self, bridge=None, event_detector=None
    ) -> Optional[Alert]:
        """Check ESP32 status age"""
        if bridge and bridge.is_connected:
            status_data = bridge.get_status(max_age_seconds=60.0)
            if status_data and hasattr(status_data, "timestamp"):
                import time

                age = time.time() - status_data.timestamp
                if age > 30:  # 30 seconds threshold
                    return Alert(
                        name="esp32_status_stale",
                        severity=AlertSeverity.WARNING,
                        message=f"ESP32 status is stale (age: {age:.1f}s)",
                        metadata={"age_seconds": age},
                    )
        return None

    def _check_memory_usage(self, bridge=None, event_detector=None) -> Optional[Alert]:
        """Check memory usage"""
        try:
            import psutil

            memory = psutil.virtual_memory()
            usage = memory.percent
            if usage > 90:
                return Alert(
                    name="high_memory_usage",
                    severity=AlertSeverity.CRITICAL,
                    message=f"Memory usage is critical ({usage:.1f}%)",
                    metadata={"usage_percent": usage},
                )
            elif usage > 80:
                return Alert(
                    name="high_memory_usage",
                    severity=AlertSeverity.WARNING,
                    message=f"Memory usage is high ({usage:.1f}%)",
                    metadata={"usage_percent": usage},
                )
        except ImportError:
            pass
        return None

    def _check_cpu_usage(self, bridge=None, event_detector=None) -> Optional[Alert]:
        """Check CPU usage"""
        try:
            import psutil

            usage = psutil.cpu_percent(interval=0.1)
            if usage > 90:
                return Alert(
                    name="high_cpu_usage",
                    severity=AlertSeverity.CRITICAL,
                    message=f"CPU usage is critical ({usage:.1f}%)",
                    metadata={"usage_percent": usage},
                )
            elif usage > 80:
                return Alert(
                    name="high_cpu_usage",
                    severity=AlertSeverity.WARNING,
                    message=f"CPU usage is high ({usage:.1f}%)",
                    metadata={"usage_percent": usage},
                )
        except ImportError:
            pass
        return None

    def _check_disk_usage(self, bridge=None, event_detector=None) -> Optional[Alert]:
        """Check disk usage"""
        try:
            import psutil

            disk = psutil.disk_usage("/")
            usage = (disk.used / disk.total) * 100
            if usage > 95:
                return Alert(
                    name="high_disk_usage",
                    severity=AlertSeverity.CRITICAL,
                    message=f"Disk usage is critical ({usage:.1f}%)",
                    metadata={"usage_percent": usage},
                )
            elif usage > 85:
                return Alert(
                    name="high_disk_usage",
                    severity=AlertSeverity.WARNING,
                    message=f"Disk usage is high ({usage:.1f}%)",
                    metadata={"usage_percent": usage},
                )
        except ImportError:
            pass
        return None

    def _check_cpu_temperature(
        self, bridge=None, event_detector=None
    ) -> Optional[Alert]:
        """Check CPU temperature"""
        try:
            temp = None
            # Raspberry Pi: /sys/class/thermal/thermal_zone0/temp
            try:
                with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                    temp_millidegree = int(f.read().strip())
                    temp = temp_millidegree / 1000.0
            except (OSError, ValueError, FileNotFoundError):
                # Try psutil sensors
                try:
                    import psutil

                    temps = psutil.sensors_temperatures()
                    if "cpu_thermal" in temps:
                        temp = temps["cpu_thermal"][0].current
                    elif "coretemp" in temps:
                        temp = temps["coretemp"][0].current
                except (ImportError, AttributeError, KeyError, IndexError):
                    pass

            if temp is not None:
                if temp > 80:
                    return Alert(
                        name="high_cpu_temperature",
                        severity=AlertSeverity.CRITICAL,
                        message=f"CPU temperature is critical ({temp:.1f}°C)",
                        metadata={"temperature_celsius": temp},
                    )
                elif temp > 70:
                    return Alert(
                        name="high_cpu_temperature",
                        severity=AlertSeverity.WARNING,
                        message=f"CPU temperature is high ({temp:.1f}°C)",
                        metadata={"temperature_celsius": temp},
                    )
        except Exception:
            pass
        return None

    def _check_event_detector(
        self, bridge=None, event_detector=None
    ) -> Optional[Alert]:
        """Check event detector status"""
        if event_detector and not event_detector.is_monitoring:
            return Alert(
                name="event_detector_stopped",
                severity=AlertSeverity.WARNING,
                message="Event detector is stopped",
            )
        return None


# Global alert manager instance
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get global alert manager instance"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager
