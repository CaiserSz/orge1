"""
API Error Handling Tests
Created: 2025-12-09 23:10:00
Last Modified: 2025-12-10 09:00:00
Version: 1.0.0
Description: API error handling testleri
"""

import sys
from unittest.mock import patch
from pathlib import Path
from fastapi.testclient import TestClient

# Proje root'unu path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.main import app


class TestAPIErrorHandling:
    """API error handling testleri"""

    def setup_method(self):
        """Her test öncesi test client oluştur"""
        self.client = TestClient(app)

    def test_global_exception_handler(self):
        """Global exception handler testi"""
        # Exception'ı endpoint içinde oluştur
        with patch("api.main.get_bridge", side_effect=Exception("Test exception")):
            response = self.client.get("/api/status")

            # Exception handler çalışmalı - 500 veya başka bir hata kodu
            assert response.status_code >= 500

    def test_invalid_endpoint(self):
        """Geçersiz endpoint"""
        response = self.client.get("/api/invalid")

        assert response.status_code == 404

    def test_invalid_method(self):
        """Geçersiz HTTP method"""
        response = self.client.delete("/api/status")

        assert response.status_code == 405  # Method not allowed
