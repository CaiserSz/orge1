#!/usr/bin/env python3
"""
WiFi Failover Monitor Script
Created: 2025-12-08 19:20:00
Last Modified: 2025-12-08 19:20:00
Version: 1.0.0
Description: WiFi bağlantısı ve internet erişimi kontrolü yapar, gerekirse failover yapar
"""

import subprocess
import time
import sys
import logging
from typing import Optional, List, Tuple

# Logging konfigürasyonu
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/wifi_failover.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# WiFi ağları priority sırasına göre (yüksekten düşüğe)
WIFI_NETWORKS = [
    ("ORGE_ARGE", 10),
    ("ORGE_DEPO", 9),
    ("ORGE_EV", 8),
    ("ERTAC", 7),
]

# Internet kontrol parametreleri
INTERNET_CHECK_TIMEOUT = 20  # saniye
INTERNET_CHECK_INTERVAL = 5  # saniye
INTERNET_CHECK_HOSTS = ["8.8.8.8", "1.1.1.1", "google.com"]
PING_COUNT = 2
PING_TIMEOUT = 3


def run_command(cmd: List[str], timeout: int = 10) -> Tuple[bool, str]:
    """
    Komut çalıştırır ve sonucu döndürür
    
    Args:
        cmd: Çalıştırılacak komut listesi
        timeout: Timeout süresi (saniye)
    
    Returns:
        (başarılı mı, çıktı)
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )
        return result.returncode == 0, result.stdout.strip()
    except subprocess.TimeoutExpired:
        logger.warning(f"Komut timeout: {' '.join(cmd)}")
        return False, "Timeout"
    except Exception as e:
        logger.error(f"Komut hatası: {e}")
        return False, str(e)


def get_current_wifi_connection() -> Optional[str]:
    """
    Şu anki aktif WiFi bağlantısını döndürür
    
    Returns:
        Bağlantı adı veya None
    """
    success, output = run_command(["nmcli", "-t", "-f", "NAME,DEVICE,TYPE", "connection", "show", "--active"])
    if not success:
        return None
    
    for line in output.split('\n'):
        if line and 'wifi' in line.lower():
            parts = line.split(':')
            if len(parts) >= 1:
                return parts[0]
    return None


def check_internet_access() -> bool:
    """
    Internet erişimini kontrol eder
    
    Returns:
        Internet erişimi var mı
    """
    for host in INTERNET_CHECK_HOSTS:
        # Ping kontrolü
        if host in ["8.8.8.8", "1.1.1.1"]:
            cmd = ["ping", "-c", str(PING_COUNT), "-W", str(PING_TIMEOUT), host]
        else:
            # DNS gerektiren hostlar için
            cmd = ["ping", "-c", str(PING_COUNT), "-W", str(PING_TIMEOUT), "-w", str(PING_TIMEOUT * PING_COUNT), host]
        
        success, _ = run_command(cmd, timeout=PING_TIMEOUT * PING_COUNT + 2)
        if success:
            logger.debug(f"Internet erişimi başarılı: {host}")
            return True
    
    logger.warning("Internet erişimi yok")
    return False


def get_next_wifi_network(current_network: Optional[str]) -> Optional[str]:
    """
    Mevcut ağdan sonraki WiFi ağını döndürür
    
    Args:
        current_network: Şu anki ağ adı
    
    Returns:
        Sonraki ağ adı veya None
    """
    if current_network is None:
        # İlk ağa bağlan
        return WIFI_NETWORKS[0][0]
    
    # Mevcut ağın priority'sini bul
    current_priority = None
    for name, priority in WIFI_NETWORKS:
        if name == current_network:
            current_priority = priority
            break
    
    if current_priority is None:
        # Mevcut ağ listede yok, ilk ağa dön
        return WIFI_NETWORKS[0][0]
    
    # Daha düşük priority'li ağı bul
    for name, priority in WIFI_NETWORKS:
        if priority < current_priority:
            return name
    
    # Tüm ağlar denendi, ilk ağa dön
    return WIFI_NETWORKS[0][0]


def connect_to_wifi(network_name: str) -> bool:
    """
    Belirtilen WiFi ağına bağlanır
    
    Args:
        network_name: Bağlanılacak ağ adı
    
    Returns:
        Bağlantı başarılı mı
    """
    logger.info(f"WiFi ağına bağlanılıyor: {network_name}")
    
    # Önce mevcut bağlantıyı kes
    current = get_current_wifi_connection()
    if current:
        logger.info(f"Mevcut bağlantı kesiliyor: {current}")
        run_command(["nmcli", "connection", "down", current])
        time.sleep(2)
    
    # Yeni bağlantıyı başlat
    success, output = run_command(["nmcli", "connection", "up", network_name], timeout=30)
    
    if success:
        logger.info(f"WiFi bağlantısı başarılı: {network_name}")
        # Bağlantının kurulması için bekle
        time.sleep(5)
        return True
    else:
        logger.error(f"WiFi bağlantısı başarısız: {network_name} - {output}")
        return False


def monitor_loop():
    """
    Ana monitoring döngüsü
    """
    logger.info("WiFi Failover Monitor başlatıldı")
    logger.info(f"WiFi ağları: {[name for name, _ in WIFI_NETWORKS]}")
    
    last_internet_check = 0
    consecutive_failures = 0
    current_network = None
    
    while True:
        try:
            # Mevcut WiFi bağlantısını kontrol et
            current = get_current_wifi_connection()
            
            if current != current_network:
                logger.info(f"WiFi bağlantısı değişti: {current_network} -> {current}")
                current_network = current
                consecutive_failures = 0
            
            # Internet erişimini kontrol et (belirli aralıklarla)
            now = time.time()
            if now - last_internet_check >= INTERNET_CHECK_INTERVAL:
                last_internet_check = now
                
                if check_internet_access():
                    consecutive_failures = 0
                    logger.debug("Internet erişimi aktif")
                else:
                    consecutive_failures += 1
                    logger.warning(f"Internet erişimi yok (ardışık hata: {consecutive_failures})")
                    
                    # Timeout süresini kontrol et
                    if consecutive_failures * INTERNET_CHECK_INTERVAL >= INTERNET_CHECK_TIMEOUT:
                        logger.warning(f"Internet erişimi {INTERNET_CHECK_TIMEOUT} saniye boyunca yok, failover başlatılıyor")
                        
                        # Sonraki ağa geç
                        next_network = get_next_wifi_network(current_network)
                        if next_network:
                            if connect_to_wifi(next_network):
                                consecutive_failures = 0
                                current_network = next_network
                            else:
                                logger.error(f"Bağlantı başarısız: {next_network}")
                        else:
                            logger.error("Bağlanılacak ağ bulunamadı")
            
            # Kısa bir bekleme
            time.sleep(2)
            
        except KeyboardInterrupt:
            logger.info("WiFi Failover Monitor durduruluyor")
            break
        except Exception as e:
            logger.error(f"Beklenmeyen hata: {e}", exc_info=True)
            time.sleep(5)


if __name__ == "__main__":
    monitor_loop()


