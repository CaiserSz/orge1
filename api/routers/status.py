"""
Status Router
Created: 2025-12-10
Last Modified: 2025-12-10 02:20:00
Version: 1.0.0
Description: Status and health check endpoints
"""

import threading
from fastapi import APIRouter, HTTPException, status, Depends, Request
from esp32.bridge import ESP32Bridge
from api.routers.dependencies import get_bridge
from api.models import APIResponse
from api.event_detector import get_event_detector
from api.rate_limiting import status_rate_limit

router = APIRouter(prefix="/api", tags=["Status"])


@router.get("/health")
async def health_check(bridge: ESP32Bridge = Depends(get_bridge)):
    """
    Sistem sağlık kontrolü (Detaylı)

    Sistemin genel sağlık durumunu kontrol eder:
    - API servisi durumu
    - ESP32 bağlantı durumu
    - Event detector durumu
    - Thread sayısı
    - Memory kullanımı (yaklaşık)
    """
    import os

    health_data = {
        "api": "healthy",
        "esp32_connected": False,
        "esp32_status": None,
        "event_detector": None,
        "threads": threading.active_count(),
        "memory_mb": None,
    }

    # ESP32 durumu
    if bridge:
        health_data["esp32_connected"] = bridge.is_connected
        if bridge.is_connected:
            status_data = bridge.get_status(max_age_seconds=15.0)
            health_data["esp32_status"] = "available" if status_data else "no_status"
        else:
            health_data["esp32_status"] = "disconnected"
            # Reconnection durumu bilgisi
            if hasattr(bridge, "_reconnect_attempts"):
                health_data["reconnect_attempts"] = bridge._reconnect_attempts

    # Event detector durumu
    try:
        event_detector = get_event_detector(get_bridge)
        if event_detector:
            health_data["event_detector"] = {
                "monitoring": event_detector.is_monitoring,
                "thread_alive": (
                    event_detector._monitor_thread.is_alive()
                    if event_detector._monitor_thread
                    else False
                ),
            }
    except Exception as e:
        health_data["event_detector"] = {"error": str(e)}

    # Process ve sistem metrikleri (/proc kullanarak - psutil gerektirmez)
    try:
        pid = os.getpid()

        # Process memory kullanımı
        try:
            with open(f"/proc/{pid}/status", "r") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        memory_kb = int(line.split()[1])
                        health_data["memory_mb"] = round(memory_kb / 1024, 2)
                        break
        except (OSError, ValueError, FileNotFoundError):
            pass

        # Process CPU kullanımı (basit hesaplama)
        try:
            # /proc/stat ve /proc/[pid]/stat kullanarak CPU% hesapla
            with open("/proc/stat", "r") as f:
                cpu_line = f.readline()
                cpu_fields = cpu_line.split()
                total_jiffies = sum(int(x) for x in cpu_fields[1:])

            with open(f"/proc/{pid}/stat", "r") as f:
                proc_stat = f.read().split()
                # utime + stime (14 ve 15. alanlar, 0-indexed: 13 ve 14)
                proc_utime = int(proc_stat[13])
                proc_stime = int(proc_stat[14])
                proc_total = proc_utime + proc_stime

            # Basit CPU% hesaplama (yaklaşık)
            # Not: Bu gerçek zamanlı değil, process'in toplam CPU kullanımı
            # Gerçek zamanlı için psutil veya daha karmaşık hesaplama gerekir
            # Ancak health check için yaklaşık değer yeterli
            health_data["cpu_percent"] = None  # Gerçek zamanlı CPU% için psutil gerekli
            health_data["cpu_note"] = "Real-time CPU% requires psutil module"
        except (OSError, ValueError, FileNotFoundError, IndexError):
            pass

        # Sistem genel metrikleri
        try:
            # Sistem memory kullanımı
            with open("/proc/meminfo", "r") as f:
                meminfo = {}
                for line in f:
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

        # Load average
        try:
            load_avg = os.getloadavg()
            health_data["load_average"] = {
                "1min": round(load_avg[0], 2),
                "5min": round(load_avg[1], 2),
                "15min": round(load_avg[2], 2),
            }
        except (OSError, AttributeError):
            pass

        # psutil varsa daha detaylı bilgi ekle
        try:
            import psutil

            process = psutil.Process(pid)
            health_data["cpu_percent"] = round(
                process.cpu_percent(interval=0.1), 2
            )  # Kısa interval
            health_data["memory_percent"] = round(process.memory_percent(), 2)
            health_data["system_cpu_percent"] = round(
                psutil.cpu_percent(interval=0.1), 2
            )
            # psutil varsa cpu_note'u kaldır
            health_data.pop("cpu_note", None)
        except ImportError:
            pass  # psutil yoksa devam et
        except Exception:
            pass  # psutil hatası varsa sessizce geç

        # CPU sıcaklığı (Raspberry Pi ve diğer sistemler için)
        try:
            cpu_temp_celsius = None

            # Raspberry Pi: /sys/class/thermal/thermal_zone0/temp (millidegree)
            try:
                with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                    temp_millidegree = int(f.read().strip())
                    cpu_temp_celsius = round(temp_millidegree / 1000.0, 2)
            except (OSError, ValueError, FileNotFoundError):
                # psutil ile CPU sıcaklığı (Linux, alternatif yöntem)
                try:
                    import psutil

                    if hasattr(psutil, "sensors_temperatures"):
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

                # Sıcaklık durumu (Raspberry Pi için eşik değerleri)
                if cpu_temp_celsius > 80:
                    health_data["cpu_temperature_status"] = "critical"
                elif cpu_temp_celsius > 70:
                    health_data["cpu_temperature_status"] = "high"
                elif cpu_temp_celsius > 60:
                    health_data["cpu_temperature_status"] = "warm"
                else:
                    health_data["cpu_temperature_status"] = "normal"
        except Exception:
            pass  # CPU sıcaklığı alınamadı
    except Exception as e:
        # Metrik toplama hatası - kritik değil, devam et
        health_data["metrics_error"] = str(e)

    # Genel sağlık durumu
    is_healthy = (
        health_data["api"] == "healthy"
        and health_data["esp32_connected"]
        and health_data["esp32_status"] == "available"
    )

    return APIResponse(success=True, message="System health check", data=health_data)


@router.get("/status")
@status_rate_limit()  # Status endpoint'leri için rate limit (30/dakika)
async def get_status(request: Request, bridge: ESP32Bridge = Depends(get_bridge)):
    """
    ESP32 durum bilgisini al

    ESP32'den son durum bilgisini döndürür.
    ESP32 her 7.5 saniyede bir otomatik olarak durum gönderir.

    Stale data kontrolü: 10 saniyeden eski veri None döndürülür ve yeni veri istenir.
    """
    if not bridge or not bridge.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ESP32 bağlantısı yok",
        )

    # Önce cache'den kontrol et (stale data kontrolü ile)
    status_data = bridge.get_status(max_age_seconds=10.0)

    if not status_data:
        # Cache'de veri yok veya çok eski - yeni veri iste
        status_data = bridge.get_status_sync(timeout=2.0)

    if not status_data:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="ESP32'den durum bilgisi alınamadı (timeout veya stale data)",
        )

    return APIResponse(
        success=True, message="Status retrieved successfully", data=status_data
    )
