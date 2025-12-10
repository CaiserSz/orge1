"""
Response Caching Module
Created: 2025-12-10 14:00:00
Last Modified: 2025-12-10 14:00:00
Version: 1.0.0
Description: API response caching için modül - In-memory cache ve Redis desteği
"""

import hashlib
import json
import time
from functools import wraps
from typing import Any, Callable, Optional

from fastapi import Request
from starlette.responses import JSONResponse

from api.config import config
from api.logging_config import system_logger

# Cache backend seçimi (config modülünden)
CACHE_BACKEND = config.CACHE_BACKEND.lower()  # memory, redis

# Cache TTL (Time To Live) - saniye cinsinden
CACHE_TTL = config.CACHE_TTL  # Varsayılan: 5 dakika

# In-memory cache storage
_memory_cache: dict[str, dict[str, Any]] = {}


class CacheBackend:
    """Cache backend interface"""

    def get(self, key: str) -> Optional[Any]:
        """Cache'den değer al"""
        raise NotImplementedError

    def set(self, key: str, value: Any, ttl: int) -> None:
        """Cache'e değer kaydet"""
        raise NotImplementedError

    def delete(self, key: str) -> None:
        """Cache'den değer sil"""
        raise NotImplementedError

    def clear(self) -> None:
        """Tüm cache'i temizle"""
        raise NotImplementedError


class MemoryCacheBackend(CacheBackend):
    """In-memory cache backend"""

    def __init__(self):
        self._cache: dict[str, dict[str, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        """Cache'den değer al"""
        if key not in self._cache:
            return None

        cache_entry = self._cache[key]
        # TTL kontrolü
        if time.time() > cache_entry["expires_at"]:
            del self._cache[key]
            return None

        return cache_entry["value"]

    def set(self, key: str, value: Any, ttl: int) -> None:
        """Cache'e değer kaydet"""
        self._cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl,
            "created_at": time.time(),
        }

    def delete(self, key: str) -> None:
        """Cache'den değer sil"""
        if key in self._cache:
            del self._cache[key]

    def clear(self) -> None:
        """Tüm cache'i temizle"""
        self._cache.clear()

    def cleanup_expired(self) -> None:
        """Süresi dolmuş cache entry'lerini temizle"""
        current_time = time.time()
        expired_keys = [
            key
            for key, entry in self._cache.items()
            if current_time > entry["expires_at"]
        ]
        for key in expired_keys:
            del self._cache[key]


class RedisCacheBackend(CacheBackend):
    """Redis cache backend"""

    def __init__(self, redis_url: Optional[str] = None):
        try:
            import redis

            redis_url = redis_url or config.REDIS_URL
            self._client = redis.from_url(redis_url, decode_responses=True)
            # Bağlantı testi
            self._client.ping()
            system_logger.info(f"Redis cache backend bağlandı: {redis_url}")
        except ImportError:
            raise ImportError(
                "Redis backend için 'redis' paketi gerekli. 'pip install redis' ile yükleyin."
            )
        except Exception as e:
            system_logger.error(f"Redis bağlantı hatası: {e}")
            raise

    def get(self, key: str) -> Optional[Any]:
        """Cache'den değer al"""
        try:
            value = self._client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception as e:
            system_logger.error(f"Redis get error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int) -> None:
        """Cache'e değer kaydet"""
        try:
            value_json = json.dumps(value)
            self._client.setex(key, ttl, value_json)
        except Exception as e:
            system_logger.error(f"Redis set error: {e}")

    def delete(self, key: str) -> None:
        """Cache'den değer sil"""
        try:
            self._client.delete(key)
        except Exception as e:
            system_logger.error(f"Redis delete error: {e}")

    def clear(self) -> None:
        """Tüm cache'i temizle"""
        try:
            self._client.flushdb()
        except Exception as e:
            system_logger.error(f"Redis clear error: {e}")


# Cache backend instance'ı oluştur
_cache_backend: Optional[CacheBackend] = None


def get_cache_backend() -> CacheBackend:
    """Cache backend instance'ı al"""
    global _cache_backend

    if _cache_backend is None:
        if CACHE_BACKEND == "redis":
            try:
                _cache_backend = RedisCacheBackend()
            except Exception as e:
                system_logger.warning(
                    f"Redis backend başlatılamadı, memory backend kullanılıyor: {e}"
                )
                _cache_backend = MemoryCacheBackend()
        else:
            _cache_backend = MemoryCacheBackend()

    # Memory cache için expired entry'leri temizle
    if isinstance(_cache_backend, MemoryCacheBackend):
        _cache_backend.cleanup_expired()

    return _cache_backend


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
):
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
                return JSONResponse(
                    content=cached_response,
                    headers={"X-Cache": "HIT", "X-Cache-Key": cache_key},
                )

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
                except Exception as e:
                    system_logger.error(f"Cache set error: {e}")

            return response

        return wrapper

    return decorator


def invalidate_cache(pattern: Optional[str] = None):
    """
    Cache'i invalidate et

    Args:
        pattern: Cache key pattern (opsiyonel, tüm cache'i temizlemek için None)
    """
    cache_backend = get_cache_backend()

    if pattern:
        # Pattern-based invalidation (Redis için)
        if isinstance(cache_backend, RedisCacheBackend):
            try:
                keys = cache_backend._client.keys(pattern)
                if keys:
                    cache_backend._client.delete(*keys)
            except Exception as e:
                system_logger.error(f"Cache invalidation error: {e}")
        else:
            # Memory cache için pattern matching
            keys_to_delete = [
                key for key in cache_backend._cache.keys() if pattern in key
            ]
            for key in keys_to_delete:
                cache_backend.delete(key)
    else:
        # Tüm cache'i temizle
        cache_backend.clear()


def get_cache_stats() -> dict[str, Any]:
    """Cache istatistiklerini al"""
    cache_backend = get_cache_backend()

    if isinstance(cache_backend, MemoryCacheBackend):
        return {
            "backend": "memory",
            "size": len(cache_backend._cache),
            "keys": list(cache_backend._cache.keys()),
        }
    elif isinstance(cache_backend, RedisCacheBackend):
        try:
            info = cache_backend._client.info("memory")
            return {
                "backend": "redis",
                "used_memory": info.get("used_memory_human", "N/A"),
                "keys": cache_backend._client.dbsize(),
            }
        except Exception as e:
            system_logger.error(f"Redis stats error: {e}")
            return {"backend": "redis", "error": str(e)}

    return {"backend": "unknown"}
