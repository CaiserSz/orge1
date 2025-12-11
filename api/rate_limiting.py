"""
Rate Limiting Module
Created: 2025-12-10 13:00:00
Last Modified: 2025-12-10 13:00:00
Version: 1.0.0
Description: Rate limiting implementation using slowapi for DDoS and brute force protection
"""

from typing import Optional

from fastapi import Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from api.config import config
from api.logging_config import system_logger


def get_client_identifier(request: Request) -> str:
    """
    Rate limiting için client identifier oluştur

    Öncelik sırası:
    1. X-API-Key header'ı varsa (API key-based rate limiting)
    2. IP adresi (IP-based rate limiting)

    Args:
        request: FastAPI Request objesi

    Returns:
        str: Client identifier (API key veya IP adresi)
    """
    # API key varsa, API key-based rate limiting kullan
    api_key = request.headers.get("X-API-Key")
    if api_key:
        # API key'in hash'ini kullan (güvenlik için)
        import hashlib

        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        return f"api_key:{api_key_hash}"

    # API key yoksa, IP-based rate limiting kullan
    return get_remote_address(request)


class _DummyLimiter:
    """Rate limit devre dışı iken decorator'ları no-op yapar."""

    @staticmethod
    def limit(_limit: Optional[str] = None):
        def decorator(func):
            return func

        return decorator


def _build_limiter() -> Limiter:
    if not config.RATE_LIMIT_ENABLED:
        system_logger.info("Rate limiting devre dışı (RATE_LIMIT_ENABLED=false)")
        return _DummyLimiter()  # type: ignore[return-value]

    return Limiter(
        key_func=get_client_identifier,
        default_limits=["100/minute"],  # Varsayılan limit: 100 istek/dakika
        storage_uri="memory://",  # In-memory storage (production'da Redis kullanılabilir)
    )


# Rate limiter instance oluştur
limiter = _build_limiter()


def get_rate_limit_config() -> dict:
    """
    Rate limit konfigürasyonunu config modülünden al

    Returns:
        dict: Rate limit konfigürasyonu
    """
    return {
        "default_limit": config.RATE_LIMIT_DEFAULT,
        "ip_limit": config.RATE_LIMIT_IP,  # IP-based: 60/dakika
        "api_key_limit": config.RATE_LIMIT_API_KEY,  # API key-based: 200/dakika
        "charge_limit": config.RATE_LIMIT_CHARGE,  # Charge endpoint'leri: 10/dakika
        "status_limit": config.RATE_LIMIT_STATUS,  # Status endpoint'leri: 30/dakika
    }


# Rate limit konfigürasyonunu yükle
rate_limit_config = get_rate_limit_config()


def get_ip_rate_limit() -> str:
    """
    IP-based rate limit string'i döndür

    Returns:
        str: Rate limit string (örn: "60/minute")
    """
    return rate_limit_config["ip_limit"]


def get_api_key_rate_limit() -> str:
    """
    API key-based rate limit string'i döndür

    Returns:
        str: Rate limit string (örn: "200/minute")
    """
    return rate_limit_config["api_key_limit"]


def get_charge_rate_limit() -> str:
    """
    Charge endpoint'leri için rate limit string'i döndür

    Returns:
        str: Rate limit string (örn: "10/minute")
    """
    return rate_limit_config["charge_limit"]


def get_status_rate_limit() -> str:
    """
    Status endpoint'leri için rate limit string'i döndür

    Returns:
        str: Rate limit string (örn: "30/minute")
    """
    return rate_limit_config["status_limit"]


def setup_rate_limiting(app):
    """
    Rate limiting'i FastAPI uygulamasına ekle

    Args:
        app: FastAPI uygulama instance'ı
    """
    # Limiter'ı app state'ine ekle
    app.state.limiter = limiter

    # Rate limit exceeded exception handler'ı ekle
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    system_logger.info(
        "Rate limiting aktif edildi",
        extra={
            "default_limit": rate_limit_config["default_limit"],
            "ip_limit": rate_limit_config["ip_limit"],
            "api_key_limit": rate_limit_config["api_key_limit"],
            "charge_limit": rate_limit_config["charge_limit"],
            "status_limit": rate_limit_config["status_limit"],
        },
    )


# Rate limit decorator'ları (kolay kullanım için)
def ip_rate_limit(limit: Optional[str] = None):
    """
    IP-based rate limit decorator

    Args:
        limit: Rate limit string (örn: "60/minute"). None ise varsayılan IP limit kullanılır.

    Returns:
        Decorator function
    """
    if limit is None:
        limit = get_ip_rate_limit()
    return limiter.limit(limit)


def api_key_rate_limit(limit: Optional[str] = None):
    """
    API key-based rate limit decorator

    Args:
        limit: Rate limit string (örn: "200/minute"). None ise varsayılan API key limit kullanılır.

    Returns:
        Decorator function
    """
    if limit is None:
        limit = get_api_key_rate_limit()
    return limiter.limit(limit)


def charge_rate_limit(limit: Optional[str] = None):
    """
    Charge endpoint'leri için rate limit decorator

    Args:
        limit: Rate limit string (örn: "10/minute"). None ise varsayılan charge limit kullanılır.

    Returns:
        Decorator function
    """
    if limit is None:
        limit = get_charge_rate_limit()
    return limiter.limit(limit)


def status_rate_limit(limit: Optional[str] = None):
    """
    Status endpoint'leri için rate limit decorator

    Args:
        limit: Rate limit string (örn: "30/minute"). None ise varsayılan status limit kullanılır.

    Returns:
        Decorator function
    """
    if limit is None:
        limit = get_status_rate_limit()
    return limiter.limit(limit)
