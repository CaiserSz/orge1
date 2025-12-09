#!/usr/bin/env python3
"""
API Health Monitor Script
Oluşturulma Tarihi: 2025-12-10 01:15:00
Son Güncelleme: 2025-12-10 01:15:00
Version: 1.0.0
Açıklama: API servisinin sağlığını kontrol eder ve sorun durumunda restart eder
"""

import sys
import os
import time
import subprocess
import logging
from datetime import datetime
from pathlib import Path

# Logging yapılandırması
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "api_health_monitor.log"

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
MAX_FAILURES = 3  # 3 başarısız kontrol sonrası restart
SERVICE_NAME = "charger-api.service"


def check_api_health():
    """API sağlık kontrolü yapar"""
    try:
        import urllib.request
        import urllib.error

        req = urllib.request.Request(API_URL)
        req.add_header('User-Agent', 'API-Health-Monitor/1.0')

        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                return True, "OK"
            else:
                return False, f"HTTP {response.status}"
    except urllib.error.URLError as e:
        return False, f"Connection error: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def restart_service():
    """Systemd service'i restart eder"""
    try:
        result = subprocess.run(
            ["sudo", "systemctl", "restart", SERVICE_NAME],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            logger.info(f"Service {SERVICE_NAME} restarted successfully")
            return True
        else:
            logger.error(f"Failed to restart service: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error restarting service: {e}")
        return False


def check_service_status():
    """Service durumunu kontrol eder"""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", SERVICE_NAME],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Error checking service status: {e}")
        return False


def main():
    """Ana monitoring döngüsü"""
    logger.info("API Health Monitor başlatıldı")
    logger.info(f"API URL: {API_URL}")
    logger.info(f"Check Interval: {CHECK_INTERVAL} saniye")
    logger.info(f"Max Failures: {MAX_FAILURES}")

    failure_count = 0
    last_success_time = datetime.now()

    while True:
        try:
            # API health check
            is_healthy, message = check_api_health()

            if is_healthy:
                if failure_count > 0:
                    logger.info(f"API sağlığı düzeldi. Önceki hata sayısı: {failure_count}")
                failure_count = 0
                last_success_time = datetime.now()
            else:
                failure_count += 1
                logger.warning(f"API sağlık kontrolü başarısız ({failure_count}/{MAX_FAILURES}): {message}")

                # Service durumunu kontrol et
                if not check_service_status():
                    logger.error(f"Service {SERVICE_NAME} çalışmıyor! Restart ediliyor...")
                    restart_service()
                    failure_count = 0  # Restart sonrası sayacı sıfırla
                elif failure_count >= MAX_FAILURES:
                    logger.error(f"{MAX_FAILURES} ardışık başarısız kontrol! Service restart ediliyor...")
                    restart_service()
                    failure_count = 0  # Restart sonrası sayacı sıfırla

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

