"""
Station Information Storage
Created: 2025-12-08
Last Modified: 2025-12-08
Version: 1.0.0
Description: Şarj istasyonu bilgilerini saklama ve yönetim modülü
"""

import json
import os
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

# Veri dosyası yolu
DATA_FILE = Path(__file__).parent.parent / "data" / "stations.json"


def ensure_data_dir():
    """Veri dizinini oluştur"""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_stations() -> Dict[str, dict]:
    """Tüm istasyon bilgilerini yükle"""
    ensure_data_dir()
    if not DATA_FILE.exists():
        return {}
    
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Stations yükleme hatası: {e}")
        return {}


def save_stations(stations: Dict[str, dict]):
    """İstasyon bilgilerini kaydet"""
    ensure_data_dir()
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(stations, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Stations kaydetme hatası: {e}")
        return False


def get_station(station_id: str) -> Optional[dict]:
    """Belirli bir istasyon bilgisini al"""
    stations = load_stations()
    return stations.get(station_id)


def get_all_stations() -> List[dict]:
    """Tüm istasyonları listele"""
    stations = load_stations()
    return list(stations.values())


def create_station(station_data: dict) -> bool:
    """Yeni istasyon oluştur"""
    stations = load_stations()
    station_id = station_data.get('station_id')
    
    if not station_id:
        return False
    
    if station_id in stations:
        return False  # Zaten var
    
    station_data['created_at'] = datetime.now().isoformat()
    station_data['updated_at'] = datetime.now().isoformat()
    stations[station_id] = station_data
    
    return save_stations(stations)


def update_station(station_id: str, update_data: dict) -> bool:
    """İstasyon bilgilerini güncelle"""
    stations = load_stations()
    
    if station_id not in stations:
        return False
    
    # Mevcut veriyi al
    station = stations[station_id]
    
    # Güncelleme verilerini uygula
    for key, value in update_data.items():
        if value is not None:
            station[key] = value
    
    station['updated_at'] = datetime.now().isoformat()
    stations[station_id] = station
    
    return save_stations(stations)


def delete_station(station_id: str) -> bool:
    """İstasyon sil"""
    stations = load_stations()
    
    if station_id not in stations:
        return False
    
    del stations[station_id]
    return save_stations(stations)

