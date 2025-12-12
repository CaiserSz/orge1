"""
CORS Policy Tests
Created: 2025-12-10 13:10:00
Last Modified: 2025-12-11 19:58:00
Version: 1.0.1
Description: CORS policy functionality tests
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app, raise_server_exceptions=False)


def test_cors_preflight_request(client):
    """Test CORS preflight (OPTIONS) request"""
    response = client.options(
        "/api/status",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-API-Key",
        },
    )

    # Preflight request başarılı olmalı
    assert response.status_code == 200

    # CORS headers kontrolü
    assert "access-control-allow-origin" in response.headers
    assert "access-control-allow-methods" in response.headers
    assert "access-control-allow-headers" in response.headers


def test_cors_actual_request(client):
    """Test CORS actual request"""
    response = client.get(
        "/api/status",
        headers={
            "Origin": "https://example.com",
        },
    )

    # CORS headers kontrolü
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "*"


def test_cors_allowed_methods(client):
    """Test CORS allowed methods"""
    # GET request
    response = client.get("/api/status", headers={"Origin": "https://example.com"})
    assert response.status_code in [200, 503, 504]  # ESP32 bağlantısı yoksa 503/504

    # POST request
    response = client.post(
        "/api/charge/start",
        json={"user_id": "test"},
        headers={
            "Origin": "https://example.com",
            "X-API-Key": "test_key",
        },
    )
    # API key geçersiz olabilir veya ESP32 bağlantısı yok
    assert response.status_code in [200, 401, 503]


def test_cors_allowed_headers(client):
    """Test CORS allowed headers"""
    response = client.options(
        "/api/status",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-API-Key,Content-Type",
        },
    )

    assert response.status_code == 200
    assert "access-control-allow-headers" in response.headers


def test_cors_exposed_headers(client):
    """Test CORS exposed headers (rate limiting headers)"""
    response = client.get("/api/status", headers={"Origin": "https://example.com"})

    # Rate limiting headers expose edilmeli
    assert "access-control-expose-headers" in response.headers
    exposed_headers = response.headers["access-control-expose-headers"]
    assert "X-RateLimit-Limit" in exposed_headers or "*" in exposed_headers


def test_cors_credentials(client):
    """Test CORS credentials support"""
    response = client.options(
        "/api/status",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    # Credentials support kontrolü
    assert "access-control-allow-credentials" in response.headers


def test_cors_different_origins(client):
    """Test CORS with different origins"""
    origins = [
        "https://example.com",
        "https://test.example.com",
        "http://localhost:3000",
        "http://localhost:8080",
    ]

    for origin in origins:
        response = client.get("/api/status", headers={"Origin": origin})
        assert "access-control-allow-origin" in response.headers
        # Varsayılan olarak * kullanılıyor (tüm origin'lere izin)
        assert (
            response.headers["access-control-allow-origin"] == "*"
            or response.headers["access-control-allow-origin"] == origin
        )
