"""
Station Information Storage (Simple)
Created: 2025-12-08
Last Modified: 2025-12-08
Version: 1.0.0
Description: Şarj istasyonu bilgilerini saklama (basit versiyon)
"""

import json
from typing import Optional, Dict
from datetime import datetime
from pathlib import Path
import logging

# Veri dosyası yolu
DATA_FILE = Path(__file__).parent.parent / "data" / "station_info.json"

# Logger setup
logger = logging.getLogger(__name__)


def ensure_data_dir():
    """Veri dizinini oluştur"""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)


def save_station_info(station_data: Dict) -> bool:
    """İstasyon bilgilerini kaydet"""
    ensure_data_dir()
    try:
        station_data['updated_at'] = datetime.now().isoformat()
        if 'created_at' not in station_data:
            station_data['created_at'] = datetime.now().isoformat()
        
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(station_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Station info kaydedildi: {DATA_FILE}")
        return True
    except Exception as e:
        logger.error(f"Station info kaydetme hatası: {e}", exc_info=True)
        return False


def get_station_info() -> Optional[Dict]:
    """İstasyon bilgilerini al"""
    ensure_data_dir()
    if not DATA_FILE.exists():
        return None
    
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.debug(f"Station info yüklendi: {DATA_FILE}")
            return data
    except FileNotFoundError:
        logger.debug(f"Station info dosyası bulunamadı: {DATA_FILE}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Station info JSON parse hatası: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Station info yükleme hatası: {e}", exc_info=True)
        return None

