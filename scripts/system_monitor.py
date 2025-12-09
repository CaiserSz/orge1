#!/usr/bin/env python3
"""
System Monitor Script
Oluşturulma Tarihi: 2025-12-10 01:30:00
Son Güncelleme: 2025-12-10 01:30:00
Version: 1.0.0
Açıklama: Sistem metriklerini toplar, alerting yapar ve monitoring sağlar
"""

import sys
import os
import time
import json
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Logging yapılandırması
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "monitor.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Yapılandırma
API_URL = "http://localhost:8000/api/health"
CHECK_INTERVAL = 30  # saniye
ALERT_THRESHOLDS = {
    "api_response_time_ms": 100,  # ms
    "error_rate_percent": 5,  # %
    "memory_usage_percent": 80,  # %
    "cpu_usage_percent": 80,  # %
    "esp32_disconnected_seconds": 30,  # saniye
    "thread_count": 10
}


def get_system_metrics() -> Dict[str, Any]:
    """Sistem metriklerini topla"""
    metrics = {}

    try:
        # CPU ve Memory kullanımı
        import psutil
        process = psutil.Process()
        metrics["cpu_percent"] = process.cpu_percent(interval=1)
        metrics["memory_mb"] = process.memory_info().rss / 1024 / 1024
        metrics["memory_percent"] = process.memory_percent()
        metrics["thread_count"] = process.num_threads()

        # Sistem genel metrikleri
        metrics["system_cpu_percent"] = psutil.cpu_percent(interval=1)
        metrics["system_memory_percent"] = psutil.virtual_memory().percent
        metrics["system_load_avg"] = os.getloadavg()

    except ImportError:
        logger.warning("psutil bulunamadı, sistem metrikleri toplanamıyor")
        metrics["cpu_percent"] = None
        metrics["memory_mb"] = None
        metrics["memory_percent"] = None
        metrics["thread_count"] = None

    return metrics


def check_api_health() -> Optional[Dict[str, Any]]:
    """API health check endpoint'ini çağır"""
    try:
        import urllib.request
        import urllib.error

        start_time = time.time()
        req = urllib.request.Request(API_URL)
        req.add_header('User-Agent', 'System-Monitor/1.0')

        with urllib.request.urlopen(req, timeout=5) as response:
            response_time_ms = (time.time() - start_time) * 1000
            if response.status == 200:
                data = json.loads(response.read().decode())
                health_data = data.get("data", {})
                health_data["response_time_ms"] = response_time_ms
                return health_data
            else:
                logger.warning(f"API health check HTTP {response.status}")
                return None
    except urllib.error.URLError as e:
        logger.error(f"API health check connection error: {e}")
        return None
    except Exception as e:
        logger.error(f"API health check error: {e}")
        return None


def check_alerts(health_data: Dict[str, Any], system_metrics: Dict[str, Any]) -> list:
    """Alert koşullarını kontrol et"""
    alerts = []

    # API response time
    response_time = health_data.get("response_time_ms")
    if response_time and response_time > ALERT_THRESHOLDS["api_response_time_ms"]:
        alerts.append({
            "level": "warning",
            "message": f"API response time yüksek: {response_time:.1f}ms > {ALERT_THRESHOLDS['api_response_time_ms']}ms"
        })

    # Memory usage
    memory_percent = system_metrics.get("memory_percent")
    if memory_percent and memory_percent > ALERT_THRESHOLDS["memory_usage_percent"]:
        alerts.append({
            "level": "warning",
            "message": f"Memory kullanımı yüksek: {memory_percent:.1f}% > {ALERT_THRESHOLDS['memory_usage_percent']}%"
        })

    # CPU usage
    cpu_percent = system_metrics.get("cpu_percent")
    if cpu_percent and cpu_percent > ALERT_THRESHOLDS["cpu_usage_percent"]:
        alerts.append({
            "level": "warning",
            "message": f"CPU kullanımı yüksek: {cpu_percent:.1f}% > {ALERT_THRESHOLDS['cpu_usage_percent']}%"
        })

    # ESP32 connection
    esp32_connected = health_data.get("esp32_connected")
    if not esp32_connected:
        alerts.append({
            "level": "error",
            "message": "ESP32 bağlantısı yok"
        })

    # Thread count
    thread_count = health_data.get("threads") or system_metrics.get("thread_count")
    if thread_count and thread_count > ALERT_THRESHOLDS["thread_count"]:
        alerts.append({
            "level": "warning",
            "message": f"Thread sayısı yüksek: {thread_count} > {ALERT_THRESHOLDS['thread_count']}"
        })

    return alerts


def log_metrics(health_data: Dict[str, Any], system_metrics: Dict[str, Any], alerts: list):
    """Metrikleri logla"""
    timestamp = datetime.now().isoformat()

    log_entry = {
        "timestamp": timestamp,
        "health": health_data,
        "system": system_metrics,
        "alerts": alerts
    }

    logger.info(f"Metrics: {json.dumps(log_entry, indent=2)}")

    # Alert'leri ayrıca logla
    for alert in alerts:
        if alert["level"] == "error":
            logger.error(f"ALERT: {alert['message']}")
        elif alert["level"] == "warning":
            logger.warning(f"ALERT: {alert['message']}")


def main():
    """Ana monitoring döngüsü"""
    logger.info("System Monitor başlatıldı")
    logger.info(f"API URL: {API_URL}")
    logger.info(f"Check Interval: {CHECK_INTERVAL} saniye")
    logger.info(f"Alert Thresholds: {ALERT_THRESHOLDS}")

    while True:
        try:
            # Metrikleri topla
            system_metrics = get_system_metrics()
            health_data = check_api_health()

            if health_data:
                # Alert'leri kontrol et
                alerts = check_alerts(health_data, system_metrics)

                # Metrikleri logla
                log_metrics(health_data, system_metrics, alerts)
            else:
                logger.error("API health check başarısız")

            # Bekleme
            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            logger.info("Monitoring durduruldu (KeyboardInterrupt)")
            break
        except Exception as e:
            logger.error(f"Monitoring döngüsünde hata: {e}", exc_info=True)
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()

