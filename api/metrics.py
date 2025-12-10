"""
Prometheus Metrics Module
Created: 2025-12-10
Last Modified: 2025-12-10 18:00:00
Version: 1.0.0
Description: Prometheus metrics export for monitoring and alerting
"""

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from fastapi import Response
from typing import Optional
from esp32.bridge import ESP32Bridge
from api.event_detector import EventDetector

# Request metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)

# ESP32 metrics
esp32_connected = Gauge(
    "esp32_connected",
    "ESP32 connection status (1=connected, 0=disconnected)",
)

esp32_reconnect_attempts = Counter(
    "esp32_reconnect_attempts_total",
    "Total ESP32 reconnection attempts",
)

esp32_status_age_seconds = Gauge(
    "esp32_status_age_seconds",
    "Age of last ESP32 status update in seconds",
)

# System metrics
system_memory_usage_percent = Gauge(
    "system_memory_usage_percent",
    "System memory usage percentage",
)

system_cpu_usage_percent = Gauge(
    "system_cpu_usage_percent",
    "System CPU usage percentage",
)

system_disk_usage_percent = Gauge(
    "system_disk_usage_percent",
    "System disk usage percentage",
)

system_cpu_temperature_celsius = Gauge(
    "system_cpu_temperature_celsius",
    "CPU temperature in Celsius",
)

# API metrics
api_active_sessions = Gauge(
    "api_active_sessions",
    "Number of active charging sessions",
)

api_total_sessions = Counter(
    "api_total_sessions",
    "Total number of charging sessions",
    ["status"],
)

# Event detector metrics
event_detector_monitoring = Gauge(
    "event_detector_monitoring",
    "Event detector monitoring status (1=monitoring, 0=stopped)",
)

event_detector_events_total = Counter(
    "event_detector_events_total",
    "Total events detected",
    ["event_type"],
)

# Application info
app_info = Info(
    "app",
    "Application information",
)


def update_esp32_metrics(bridge: Optional[ESP32Bridge]) -> None:
    """Update ESP32-related metrics"""
    if bridge:
        esp32_connected.set(1 if bridge.is_connected else 0)

        if hasattr(bridge, "_reconnect_attempts"):
            # Reconnect attempts counter'ı sadece artırılır, set edilmez
            pass

        if bridge.is_connected:
            status_data = bridge.get_status(max_age_seconds=60.0)
            if status_data and hasattr(status_data, "timestamp"):
                import time

                age = time.time() - status_data.timestamp
                esp32_status_age_seconds.set(age)
            else:
                esp32_status_age_seconds.set(-1)  # No status available
    else:
        esp32_connected.set(0)
        esp32_status_age_seconds.set(-1)


def update_system_metrics() -> None:
    """Update system-related metrics"""
    try:
        import psutil

        # Memory usage
        memory = psutil.virtual_memory()
        system_memory_usage_percent.set(memory.percent)

        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        system_cpu_usage_percent.set(cpu_percent)

        # Disk usage
        disk = psutil.disk_usage("/")
        disk_percent = (disk.used / disk.total) * 100
        system_disk_usage_percent.set(disk_percent)

        # CPU temperature (Raspberry Pi)
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp_millidegree = int(f.read().strip())
                temp_celsius = temp_millidegree / 1000.0
                system_cpu_temperature_celsius.set(temp_celsius)
        except (OSError, ValueError, FileNotFoundError):
            # Try psutil sensors
            try:
                temps = psutil.sensors_temperatures()
                if "cpu_thermal" in temps:
                    system_cpu_temperature_celsius.set(temps["cpu_thermal"][0].current)
                elif "coretemp" in temps:
                    system_cpu_temperature_celsius.set(temps["coretemp"][0].current)
            except (AttributeError, KeyError, IndexError):
                pass
    except ImportError:
        # psutil not available
        pass
    except Exception:
        # Metrics collection error - don't fail
        pass


def update_session_metrics() -> None:
    """Update session-related metrics"""
    try:
        from api.session import get_session_manager

        session_manager = get_session_manager()
        if session_manager:
            active_sessions = len(
                [
                    s
                    for s in session_manager.get_all_sessions()
                    if s.status == "CHARGING"
                ]
            )
            api_active_sessions.set(active_sessions)
    except Exception:
        # Session metrics collection error - don't fail
        pass


def update_event_detector_metrics(event_detector: Optional[EventDetector]) -> None:
    """Update event detector-related metrics"""
    if event_detector:
        event_detector_monitoring.set(1 if event_detector.is_monitoring else 0)
    else:
        event_detector_monitoring.set(0)


def update_all_metrics(
    bridge: Optional[ESP32Bridge] = None,
    event_detector: Optional[EventDetector] = None,
) -> None:
    """Update all metrics"""
    update_esp32_metrics(bridge)
    update_system_metrics()
    update_session_metrics()
    update_event_detector_metrics(event_detector)


def get_metrics_response() -> Response:
    """Get Prometheus metrics response"""
    update_all_metrics()
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
