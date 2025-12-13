"""
Station Information Storage (Simple)
Created: 2025-12-08
Last Modified: 2025-12-13 13:10
Version: 1.1.0
Description: Şarj istasyonu bilgilerini JSON olarak saklama (station_info.json)
"""

import json
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import logging

# Veri dosyası yolu
DATA_FILE = Path(__file__).parent.parent / "data" / "station_info.json"

# Logger setup
logger = logging.getLogger(__name__)

_FLOAT_FIELDS = {"max_power_kw", "latitude", "longitude", "price_per_kwh"}
_INT_FIELDS = {"max_current_amp"}


def _coerce_non_negative_float(value: Any) -> Optional[float]:
    """Best-effort float parse; negatif değerleri reddeder."""
    if isinstance(value, str):
        s = value.strip()
        # 4,05 gibi virgüllü girişleri kabul et
        if "," in s and "." not in s:
            s = s.replace(",", ".")
        value = s
    try:
        fval = float(value)
    except (TypeError, ValueError):
        return None
    if fval < 0:
        return None
    return fval


def _coerce_non_negative_int(value: Any) -> Optional[int]:
    """Best-effort int parse; negatif değerleri reddeder."""
    fval = _coerce_non_negative_float(value)
    if fval is None:
        return None
    return int(round(fval))


def normalize_station_info(station_data: Dict[str, Any]) -> None:
    """
    Station info alanlarını normalize et (in-place).

    - Numeric alanlar (float/int) parse edilir.
    - Parse edilemeyen veya negatif değerler None yapılır (alan korunur).
    """
    for key in list(station_data.keys()):
        if station_data.get(key) is None:
            continue

        if key in _FLOAT_FIELDS:
            parsed = _coerce_non_negative_float(station_data.get(key))
            station_data[key] = parsed
        elif key in _INT_FIELDS:
            parsed = _coerce_non_negative_int(station_data.get(key))
            station_data[key] = parsed


def ensure_data_dir() -> None:
    """Veri dizinini oluştur"""
    try:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Data directory oluşturma hatası: {e}", exc_info=True)
        raise


def save_station_info(station_data: Dict) -> bool:
    """İstasyon bilgilerini kaydet"""
    try:
        ensure_data_dir()
        normalize_station_info(station_data)
        station_data["updated_at"] = datetime.now().isoformat()
        if "created_at" not in station_data:
            station_data["created_at"] = datetime.now().isoformat()

        with open(DATA_FILE, "w", encoding="utf-8") as f:
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
        with open(DATA_FILE, "r", encoding="utf-8") as f:
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
