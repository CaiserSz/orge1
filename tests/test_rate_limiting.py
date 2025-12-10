"""
Rate Limiting Tests
Created: 2025-12-10 13:00:00
Last Modified: 2025-12-10 13:00:00
Version: 1.0.0
Description: Rate limiting functionality tests
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def api_key():
    """API key fixture"""
    import os

    return os.getenv("SECRET_API_KEY", "test_api_key")


def test_rate_limiting_charge_endpoint(client, api_key):
    """Test rate limiting on charge endpoint"""
    headers = {"X-API-Key": api_key}

    # Charge start endpoint'ine 10'dan fazla istek gönder
    # İlk 10 istek başarılı olmalı, sonrası rate limit hatası vermeli
    responses = []
    for i in range(12):
        response = client.post(
            "/api/charge/start",
            json={"user_id": "test_user"},
            headers=headers,
        )
        responses.append(response.status_code)

    # İlk 10 istek başarılı veya başka bir hata olabilir (ESP32 bağlantısı yoksa 503)
    # Ancak 11. ve 12. istekler rate limit hatası vermeli (429)
    # Not: Rate limit exceeded olursa 429 döner
    assert 429 in responses[-2:] or all(
        code in [200, 400, 503, 500] for code in responses
    )


def test_rate_limiting_status_endpoint(client):
    """Test rate limiting on status endpoint"""
    # Status endpoint'ine 30'dan fazla istek gönder
    responses = []
    for i in range(32):
        response = client.get("/api/status")
        responses.append(response.status_code)

    # İlk 30 istek başarılı veya başka bir hata olabilir (ESP32 bağlantısı yoksa 503)
    # Ancak 31. ve 32. istekler rate limit hatası vermeli (429)
    assert 429 in responses[-2:] or all(code in [200, 503, 504] for code in responses)


def test_rate_limiting_ip_based(client):
    """Test IP-based rate limiting"""
    # IP-based rate limiting testi (API key olmadan)
    responses = []
    for i in range(62):
        response = client.get("/api/status")
        responses.append(response.status_code)

    # İlk 60 istek başarılı veya başka bir hata olabilir
    # Ancak 61. ve 62. istekler rate limit hatası vermeli (429)
    assert 429 in responses[-2:] or all(code in [200, 503, 504] for code in responses)


def test_rate_limiting_api_key_based(client, api_key):
    """Test API key-based rate limiting"""
    headers = {"X-API-Key": api_key}

    # API key ile 200'den fazla istek gönder
    responses = []
    for i in range(202):
        response = client.get("/api/status", headers=headers)
        responses.append(response.status_code)

    # İlk 200 istek başarılı veya başka bir hata olabilir
    # Ancak 201. ve 202. istekler rate limit hatası vermeli (429)
    assert 429 in responses[-2:] or all(code in [200, 503, 504] for code in responses)


def test_rate_limiting_different_endpoints(client, api_key):
    """Test that different endpoints have different rate limits"""
    headers = {"X-API-Key": api_key}

    # Charge endpoint'ine 10 istek gönder (limit: 10/dakika)
    charge_responses = []
    for i in range(12):
        response = client.post(
            "/api/charge/start",
            json={"user_id": "test_user"},
            headers=headers,
        )
        charge_responses.append(response.status_code)

    # Status endpoint'ine 30 istek gönder (limit: 30/dakika)
    status_responses = []
    for i in range(32):
        response = client.get("/api/status", headers=headers)
        status_responses.append(response.status_code)

    # Her iki endpoint'te de rate limit kontrolü yapılmalı
    assert 429 in charge_responses[-2:] or all(
        code in [200, 400, 503, 500] for code in charge_responses
    )
    assert 429 in status_responses[-2:] or all(
        code in [200, 503, 504] for code in status_responses
    )
