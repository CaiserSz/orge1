"""
API Error Handling Tests
Created: 2025-12-09 23:10:00
Last Modified: 2025-12-10 09:00:00
Version: 1.0.0
Description: API error handling testleri
"""

from api.main import app
from api.routers import dependencies


class TestAPIErrorHandling:
    """API error handling testleri"""

    def test_global_exception_handler(self, client):
        """Global exception handler testi"""
        app.dependency_overrides[dependencies.get_bridge] = lambda: (
            _ for _ in ()
        ).throw(Exception("Test exception"))
        response = client.get("/api/status")
        app.dependency_overrides.pop(dependencies.get_bridge, None)

        assert response.status_code >= 500

    def test_invalid_endpoint(self, client):
        """Geçersiz endpoint"""
        response = client.get("/api/invalid")

        assert response.status_code == 404

    def test_invalid_method(self, client):
        """Geçersiz HTTP method"""
        response = client.delete("/api/status")

        assert response.status_code == 405  # Method not allowed
