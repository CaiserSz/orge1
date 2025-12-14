"""
Response Caching Module
Created: 2025-12-10 14:00:00
Last Modified: 2025-12-13 01:45:00
Version: 1.1.0
Description: API response caching için modül - In-memory cache ve Redis desteği
"""

import hashlib
import json
import os
from functools import wraps
from typing import Any, Callable, Optional

from fastapi import Request
from starlette.responses import JSONResponse, Response

from api.cache_backend import (
    CacheBackend,
    MemoryCacheBackend,
    RedisCacheBackend,
    get_cache_backend,
    get_cache_stats,
    invalidate_cache,
)
from api.config import config
from api.logging_config import system_logger

# Cache TTL (Time To Live) - saniye cinsinden
CACHE_TTL = config.CACHE_TTL  # Varsayılan: 5 dakika

__all__ = [
    "CacheBackend",
    "MemoryCacheBackend",
    "RedisCacheBackend",
    "cache_response",
    "CacheInvalidator",
    "generate_cache_key",
    "get_cache_backend",
    "invalidate_cache",
    "get_cache_stats",
]


def generate_cache_key(
    path: str, query_params: dict[str, Any], user_id: Optional[str] = None
) -> str:
    """
    Cache key oluştur

    Args:
        path: Request path
        query_params: Query parametreleri
        user_id: User ID (opsiyonel, user-specific cache için)

    Returns:
        Cache key (hash)
    """
    # Query parametrelerini sıralı hale getir
    sorted_params = sorted(query_params.items())
    params_str = json.dumps(sorted_params, sort_keys=True)

    # Cache key oluştur
    key_data = f"{path}:{params_str}"
    if user_id:
        key_data = f"{user_id}:{key_data}"

    # Hash oluştur
    return hashlib.md5(key_data.encode()).hexdigest()


def cache_response(
    ttl: int = CACHE_TTL,
    key_prefix: Optional[str] = None,
    vary_on_headers: Optional[list[str]] = None,
    exclude_query_params: Optional[list[str]] = None,
) -> Callable[[Callable], Callable]:
    """
    Response caching decorator

    Args:
        ttl: Cache TTL (saniye)
        key_prefix: Cache key prefix
        vary_on_headers: Cache key'e dahil edilecek header'lar
        exclude_query_params: Cache key'den hariç tutulacak query parametreleri

    Returns:
        Decorated function
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Test ortamında cache'i bypass et
            # Not: Bazı testler cache davranışını özellikle doğrulamak isteyebilir.
            # Bu durumda `PYTEST_ENABLE_CACHE=1` ile bypass devre dışı bırakılabilir.
            if (
                os.getenv("PYTEST_CURRENT_TEST") is not None
                and os.getenv("PYTEST_ENABLE_CACHE") != "1"
            ):
                return await func(*args, **kwargs)
            # Request objesini bul
            request: Optional[Request] = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                for key, value in kwargs.items():
                    if isinstance(value, Request):
                        request = value
                        break

            if not request:
                # Request objesi yoksa cache kullanma
                return await func(*args, **kwargs)

            # Cache key oluştur
            path = request.url.path
            query_params = dict(request.query_params)

            # Hariç tutulacak query parametreleri çıkar
            if exclude_query_params:
                for param in exclude_query_params:
                    query_params.pop(param, None)

            # User ID'yi al (API key'den veya header'dan)
            user_id = None
            api_key = request.headers.get("X-API-Key")
            if api_key:
                # API key'den user ID çıkar (basit bir yaklaşım)
                # Gerçek implementasyonda auth middleware'den alınmalı
                user_id = config.get_user_id()

            # Header'ları ekle (vary_on_headers varsa)
            if vary_on_headers:
                header_values = {
                    h: request.headers.get(h, "")
                    for h in vary_on_headers
                    if request.headers.get(h)
                }
                query_params.update(header_values)

            cache_key = generate_cache_key(path, query_params, user_id)
            if key_prefix:
                cache_key = f"{key_prefix}:{cache_key}"

            # Cache'den kontrol et
            cache_backend = get_cache_backend()
            cached_response = cache_backend.get(cache_key)

            if cached_response is not None:
                system_logger.debug(f"Cache hit: {cache_key}")
                # HTTP cache headers (client tarafında değişiklik yapmadan bandwidth azaltma)
                body = json.dumps(
                    cached_response, ensure_ascii=False, sort_keys=True
                ).encode("utf-8")
                etag = hashlib.md5(body).hexdigest()
                etag_value = f'"{etag}"'

                headers = {
                    "X-Cache": "HIT",
                    "X-Cache-Key": cache_key,
                    # Shared cache riskini azalt: user bazlı veriler olabilir (X-API-Key ile farklılaşır)
                    "Cache-Control": f"private, max-age={ttl}",
                    "Vary": "X-API-Key",
                    "ETag": etag_value,
                }

                if request.headers.get("if-none-match") == etag_value:
                    return Response(status_code=304, headers=headers)

                return JSONResponse(content=cached_response, headers=headers)

            # Cache miss - fonksiyonu çalıştır
            system_logger.debug(f"Cache miss: {cache_key}")
            response = await func(*args, **kwargs)

            # Response'u cache'le
            response_data = None
            if isinstance(response, JSONResponse):
                response_body = response.body
                try:
                    response_data = json.loads(response_body.decode())
                except Exception as e:
                    system_logger.error(f"Cache response parse error: {e}")
            else:
                # APIResponse (Pydantic model) veya diğer response tipleri
                try:
                    if hasattr(response, "model_dump"):
                        # Pydantic v2
                        response_data = response.model_dump()
                    elif hasattr(response, "dict"):
                        # Pydantic v1
                        response_data = response.dict()
                    elif isinstance(response, dict):
                        response_data = response
                    else:
                        # Diğer tipler için JSON serialization dene
                        response_data = json.loads(json.dumps(response, default=str))
                except Exception as e:
                    system_logger.debug(f"Cache response extract skipped: {e}")

            if response_data:
                try:
                    cache_backend.set(cache_key, response_data, ttl)
                    # Response header'larına cache bilgisi ekle
                    if isinstance(response, JSONResponse):
                        response.headers["X-Cache"] = "MISS"
                        response.headers["X-Cache-Key"] = cache_key
                        response.headers["Cache-Control"] = f"private, max-age={ttl}"
                        response.headers["Vary"] = "X-API-Key"

                        body = json.dumps(
                            response_data, ensure_ascii=False, sort_keys=True
                        ).encode("utf-8")
                        etag = hashlib.md5(body).hexdigest()
                        response.headers["ETag"] = f'"{etag}"'
                except Exception as e:
                    system_logger.error(f"Cache set error: {e}")

            return response

        return wrapper

    return decorator


class CacheInvalidator:
    """
    Cache invalidation helper class

    Cache invalidation pattern'lerini merkezileştirir ve standardize eder.
    """

    @staticmethod
    def invalidate_status() -> None:
        """Status cache'lerini invalidate et"""
        invalidate_cache("status:*")

    @staticmethod
    def invalidate_session() -> None:
        """Session cache'lerini invalidate et"""
        invalidate_cache("session_current:*")
        invalidate_cache("sessions_list:*")
        invalidate_cache("user_current_session:*")
        invalidate_cache("session_detail:*")
        invalidate_cache("session_metrics:*")
        invalidate_cache("user_sessions:*")
        invalidate_cache("session_stats:*")

    @staticmethod
    def invalidate_all() -> None:
        """Tüm cache'leri invalidate et"""
        CacheInvalidator.invalidate_status()
        CacheInvalidator.invalidate_session()
        invalidate_cache("*")
