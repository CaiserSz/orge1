"""
API Authentication Module
Created: 2025-12-09 17:15:00
Last Modified: 2025-12-09 17:20:00
Version: 1.0.0
Description: Basit API key authentication - Tek bir SECRET_API_KEY ile (.env dosyasından)

NOT: Bu basit bir implementasyondur. İleride geliştirilebilir:
- Multiple API keys
- API key rotation
- Rate limiting per API key
- API key expiration
- JWT token authentication
"""

from fastapi import HTTPException, status, Security
from fastapi.security import APIKeyHeader
from typing import Optional

from api.config import config

# API Key Header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_secret_api_key() -> str:
    """
    Config modülünden SECRET_API_KEY'i al

    Returns:
        str: API key değeri

    Raises:
        ValueError: SECRET_API_KEY tanımlı değilse
    """
    return config.get_secret_api_key()


def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """
    API key doğrulama

    Args:
        api_key: İstekten gelen API key (X-API-Key header)

    Returns:
        str: Doğrulanmış API key

    Raises:
        HTTPException: API key geçersiz veya eksikse
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Please provide X-API-Key header.",
        )

    secret_key = get_secret_api_key()

    if api_key != secret_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )

    return api_key
