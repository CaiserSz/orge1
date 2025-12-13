"""
Health Service Helpers
Created: 2025-12-13 02:25:00
Last Modified: 2025-12-13 02:25:00
Version: 1.0.0
Description: Health check endpoint için sistem metriklerini toplayan yardımcılar.
"""

from __future__ import annotations

import os
import threading
from typing import Callable, Dict, Optional

from api.event_detector import get_event_detector
from api.models import APIResponse


def build_health_response(
    bridge,
    bridge_getter: Callable,
    threading_module=threading,
) -> APIResponse:
    is_pytest = os.getenv("PYTEST_CURRENT_TEST") is not None
    health_data: Dict[str, Optional[object]] = {
        "api": "healthy",
        "esp32_connected": False,
        "esp32_status": None,
        "event_detector": None,
        "threads": threading_module.active_count(),
        "memory_mb": None,
        "disk_percent": None,
        "disk_used_gb": None,
        "disk_total_gb": None,
        "network_ip": None,
        "network_ssid": None,
    }

    if bridge:
        health_data["esp32_connected"] = bridge.is_connected
        if bridge.is_connected:
            status_data = bridge.get_status(max_age_seconds=15.0)
            health_data["esp32_status"] = "available" if status_data else "no_status"
        else:
            health_data["esp32_status"] = "disconnected"
            if hasattr(bridge, "_reconnect_attempts"):
                health_data["reconnect_attempts"] = bridge._reconnect_attempts

    try:
        event_detector = get_event_detector(bridge_getter)
        if event_detector:
            health_data["event_detector"] = {
                "monitoring": event_detector.is_monitoring,
                "thread_alive": (
                    event_detector._monitor_thread.is_alive()
                    if event_detector._monitor_thread
                    else False
                ),
            }
    except Exception as exc:
        health_data["event_detector"] = {"error": str(exc)}

    try:
        pid = os.getpid()

        try:
            with open(f"/proc/{pid}/status", "r") as handler:
                for line in handler:
                    if line.startswith("VmRSS:"):
                        memory_kb = int(line.split()[1])
                        health_data["memory_mb"] = round(memory_kb / 1024, 2)
                        break
        except (OSError, ValueError, FileNotFoundError):
            pass

        try:
            # cpu note placeholder
            with open("/proc/stat", "r") as handler:
                cpu_line = handler.readline()
                cpu_fields = cpu_line.split()
                sum(int(x) for x in cpu_fields[1:])

            with open(f"/proc/{pid}/stat", "r") as handler:
                proc_stat = handler.read().split()
                proc_utime = int(proc_stat[13])
                proc_stime = int(proc_stat[14])
                proc_utime + proc_stime

            health_data["cpu_percent"] = None
            health_data["cpu_note"] = "Real-time CPU% requires psutil module"
        except (OSError, ValueError, FileNotFoundError, IndexError):
            pass

        try:
            with open("/proc/meminfo", "r") as handler:
                meminfo = {}
                for line in handler:
                    parts = line.split()
                    if len(parts) >= 2:
                        meminfo[parts[0].rstrip(":")] = int(parts[1])

                total_mem_kb = meminfo.get("MemTotal", 0)
                available_mem_kb = meminfo.get(
                    "MemAvailable", meminfo.get("MemFree", 0)
                )

                if total_mem_kb > 0:
                    used_mem_kb = total_mem_kb - available_mem_kb
                    health_data["system_memory_percent"] = round(
                        (used_mem_kb / total_mem_kb) * 100, 2
                    )
                    health_data["system_memory_total_mb"] = round(
                        total_mem_kb / 1024, 2
                    )
                    health_data["system_memory_available_mb"] = round(
                        available_mem_kb / 1024, 2
                    )
        except (OSError, ValueError, FileNotFoundError):
            pass

        try:
            load_avg = os.getloadavg()
            health_data["load_average"] = {
                "1min": round(load_avg[0], 2),
                "5min": round(load_avg[1], 2),
                "15min": round(load_avg[2], 2),
            }
        except (OSError, AttributeError):
            pass

        try:
            import psutil

            process = psutil.Process(pid)
            proc_cpu = process.cpu_percent(interval=None)
            sys_cpu = psutil.cpu_percent(interval=None)

            health_data["cpu_percent"] = round(proc_cpu, 2)
            health_data["memory_percent"] = round(process.memory_percent(), 2)
            health_data["system_cpu_percent"] = round(sys_cpu, 2)
            health_data.pop("cpu_note", None)
        except ImportError:
            pass
        except Exception:
            pass

        try:
            cpu_temp_celsius = None
            try:
                with open("/sys/class/thermal/thermal_zone0/temp", "r") as handler:
                    temp_millidegree = int(handler.read().strip())
                    cpu_temp_celsius = round(temp_millidegree / 1000.0, 2)
            except (OSError, ValueError, FileNotFoundError):
                try:
                    import psutil

                    temps = psutil.sensors_temperatures()
                    if "cpu_thermal" in temps:
                        cpu_temp_celsius = round(temps["cpu_thermal"][0].current, 2)
                    elif "coretemp" in temps:
                        cpu_temp_celsius = round(temps["coretemp"][0].current, 2)
                except (ImportError, AttributeError, KeyError, IndexError):
                    pass

            if cpu_temp_celsius is not None:
                health_data["cpu_temperature_celsius"] = cpu_temp_celsius
                health_data["cpu_temperature_fahrenheit"] = round(
                    cpu_temp_celsius * 9 / 5 + 32, 2
                )
                if cpu_temp_celsius > 80:
                    health_data["cpu_temperature_status"] = "critical"
                elif cpu_temp_celsius > 70:
                    health_data["cpu_temperature_status"] = "high"
                elif cpu_temp_celsius > 60:
                    health_data["cpu_temperature_status"] = "warm"
                else:
                    health_data["cpu_temperature_status"] = "normal"
        except Exception:
            pass

        try:
            import shutil

            disk_usage = shutil.disk_usage("/")
            disk_total_gb = round(disk_usage.total / (1024**3), 2)
            disk_used_gb = round(disk_usage.used / (1024**3), 2)
            disk_free_gb = round(disk_usage.free / (1024**3), 2)
            disk_percent = round((disk_usage.used / disk_usage.total) * 100, 2)

            health_data["disk_total_gb"] = disk_total_gb
            health_data["disk_used_gb"] = disk_used_gb
            health_data["disk_free_gb"] = disk_free_gb
            health_data["disk_percent"] = disk_percent
        except Exception:
            pass

        if not is_pytest:
            try:
                import re
                import socket
                import subprocess

                ip_address = None
                try:
                    for interface in ["wlan0", "eth0", "enp0s3", "ens33"]:
                        try:
                            result = subprocess.run(
                                ["ip", "addr", "show", interface],
                                capture_output=True,
                                text=True,
                                timeout=0.6,
                            )
                            if result.returncode == 0:
                                match = re.search(
                                    r"inet (\d+\.\d+\.\d+\.\d+)", result.stdout
                                )
                                if match:
                                    ip_address = match.group(1)
                                    break
                        except (subprocess.TimeoutExpired, FileNotFoundError):
                            continue

                    if not ip_address:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        try:
                            sock.connect(("8.8.8.8", 80))
                            ip_address = sock.getsockname()[0]
                        except Exception:
                            pass
                        finally:
                            sock.close()
                except Exception:
                    pass

                ssid = None
                signal = None

                try:
                    result = subprocess.run(
                        ["nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL", "dev", "wifi"],
                        capture_output=True,
                        text=True,
                        timeout=0.8,
                    )
                    if result.returncode == 0:
                        for line in result.stdout.strip().split("\n"):
                            parts = line.split(":")
                            if len(parts) >= 3 and parts[0] == "yes":
                                ssid = parts[1] or None
                                try:
                                    signal = int(parts[2])
                                except Exception:
                                    signal = None
                                break
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    pass

                if not ssid or signal is None:
                    try:
                        result = subprocess.run(
                            ["iwconfig"], capture_output=True, text=True, timeout=0.8
                        )
                        if result.returncode == 0:
                            match_ssid = re.search(r'ESSID:"([^"]+)"', result.stdout)
                            if match_ssid and not ssid:
                                ssid = match_ssid.group(1)
                            match_signal = re.search(
                                r"Signal level=(-?\d+) dBm", result.stdout
                            )
                            if match_signal and signal is None:
                                try:
                                    rssi = int(match_signal.group(1))
                                    signal = max(0, min(100, int((rssi + 100) * 2)))
                                except Exception:
                                    pass
                    except (subprocess.TimeoutExpired, FileNotFoundError):
                        pass

                health_data["network_ip"] = ip_address
                health_data["network_ssid"] = ssid
                health_data["network_signal"] = signal
            except Exception:
                pass
    except Exception as exc:
        health_data["metrics_error"] = str(exc)

    return APIResponse(success=True, message="System health check", data=health_data)
