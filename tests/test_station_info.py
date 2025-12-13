"""
Station Info Module Tests
Created: 2025-12-09 23:15:00
Last Modified: 2025-12-13 13:12:00
Version: 1.1.0
Description: Station info modülü için unit testler
"""

import pytest
import sys
import json
import tempfile
from unittest.mock import Mock, patch, mock_open
from pathlib import Path

# Proje root'unu path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.station_info import save_station_info, get_station_info, ensure_data_dir, DATA_FILE


class TestStationInfo:
    """Station Info modülü testleri"""

    def setup_method(self):
        """Her test öncesi"""
        # Test için geçici dosya kullan
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = Path(self.temp_dir) / "station_info.json"

    def test_save_station_info_success(self):
        """Station info kaydetme - başarılı"""
        with patch('api.station_info.DATA_FILE', self.temp_file):
            station_data = {
                "station_id": "TEST-001",
                "name": "Test Station",
                "location": "Test Location"
            }

            result = save_station_info(station_data)

            assert result is True
            assert self.temp_file.exists()

            # Dosya içeriğini kontrol et
            with open(self.temp_file, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)

            assert saved_data["station_id"] == "TEST-001"
            assert "updated_at" in saved_data
            assert "created_at" in saved_data

    def test_save_station_info_with_existing_created_at(self):
        """Station info kaydetme - mevcut created_at korunuyor"""
        with patch('api.station_info.DATA_FILE', self.temp_file):
            station_data = {
                "station_id": "TEST-001",
                "created_at": "2025-12-01T00:00:00"
            }

            save_station_info(station_data)
            save_station_info(station_data)  # İkinci kayıt

            with open(self.temp_file, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)

            assert saved_data["created_at"] == "2025-12-01T00:00:00"

    def test_save_station_info_file_error(self):
        """Station info kaydetme - dosya hatası"""
        # ensure_data_dir içinde exception oluşursa, save_station_info False döndürmeli
        with patch('api.station_info.ensure_data_dir', side_effect=OSError("Permission denied")):
            station_data = {"station_id": "TEST-001"}

            result = save_station_info(station_data)

            assert result is False

    def test_save_station_info_json_write_error(self):
        """Station info kaydetme - JSON yazma hatası"""
        test_file = Path(self.temp_dir) / "write_error.json"
        with patch('api.station_info.DATA_FILE', test_file):
            with patch('builtins.open', side_effect=IOError("Write error")):
                station_data = {"station_id": "TEST-001"}

                result = save_station_info(station_data)

                assert result is False

    def test_get_station_info_file_not_exists(self):
        """Station info alma - dosya yok"""
        non_existent_file = Path(self.temp_dir) / "nonexistent" / "file.json"
        with patch('api.station_info.DATA_FILE', non_existent_file):
            result = get_station_info()

            assert result is None

    def test_get_station_info_success(self):
        """Station info alma - başarılı"""
        # Önce dosyayı oluştur
        test_data = {
            "station_id": "TEST-001",
            "name": "Test Station"
        }

        with open(self.temp_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)

        with patch('api.station_info.DATA_FILE', self.temp_file):
            result = get_station_info()

            assert result is not None
            assert result["station_id"] == "TEST-001"
            assert result["name"] == "Test Station"

    def test_get_station_info_json_decode_error(self):
        """Station info alma - JSON decode hatası"""
        # Geçersiz JSON dosyası oluştur
        with open(self.temp_file, 'w', encoding='utf-8') as f:
            f.write("invalid json content")

        with patch('api.station_info.DATA_FILE', self.temp_file):
            result = get_station_info()

            assert result is None

    def test_get_station_info_file_read_error(self):
        """Station info alma - dosya okuma hatası"""
        test_file = Path(self.temp_dir) / "read_error.json"
        test_file.touch()  # Dosyayı oluştur

        with patch('api.station_info.DATA_FILE', test_file):
            with patch('builtins.open', side_effect=PermissionError("Permission denied")):
                result = get_station_info()

                assert result is None

    def test_ensure_data_dir(self):
        """Data dizini oluşturma"""
        temp_data_file = Path(self.temp_dir) / "subdir" / "station_info.json"

        with patch('api.station_info.DATA_FILE', temp_data_file):
            ensure_data_dir()

            assert temp_data_file.parent.exists()

    def test_save_and_get_roundtrip(self):
        """Save ve get roundtrip testi"""
        with patch('api.station_info.DATA_FILE', self.temp_file):
            original_data = {
                "station_id": "TEST-001",
                "name": "Test Station",
                "location": "Test Location",
                "max_current": 32
            }

            # Kaydet
            save_result = save_station_info(original_data)
            assert save_result is True

            # Al
            retrieved_data = get_station_info()
            assert retrieved_data is not None
            assert retrieved_data["station_id"] == original_data["station_id"]
            assert retrieved_data["name"] == original_data["name"]
            assert retrieved_data["location"] == original_data["location"]
            assert retrieved_data["max_current"] == original_data["max_current"]
            assert "updated_at" in retrieved_data
            assert "created_at" in retrieved_data

    def test_save_station_info_normalizes_price_per_kwh(self):
        """price_per_kwh string gelirse float'a normalize edilmeli"""
        with patch('api.station_info.DATA_FILE', self.temp_file):
            station_data = {
                "station_id": "TEST-001",
                "name": "Test Station",
                "price_per_kwh": "7.50",
            }

            result = save_station_info(station_data)
            assert result is True

            with open(self.temp_file, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)

            assert saved_data["price_per_kwh"] == 7.5

    def test_save_station_info_normalizes_price_per_kwh_comma(self):
        """price_per_kwh virgüllü string (4,05) gelirse float'a normalize edilmeli"""
        with patch('api.station_info.DATA_FILE', self.temp_file):
            station_data = {
                "station_id": "TEST-001",
                "name": "Test Station",
                "price_per_kwh": "4,05",
            }

            result = save_station_info(station_data)
            assert result is True

            with open(self.temp_file, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)

            assert saved_data["price_per_kwh"] == 4.05

