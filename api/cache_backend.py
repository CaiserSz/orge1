"""
Cache Backend Utilities
Created: 2025-12-13 01:40:00
Last Modified: 2025-12-13 01:40:00
Version: 1.0.0
Description: Cache backend implementasyonları ve yardımcı fonksiyonlar.
"""

from __future__ import annotations

import json
import time
from typing import Any, Optional

from api.config import config
from api.logging_config import system_logger

_memory_cache: dict[str, dict[str, Any]] = {}
_cache_backend: Optional["CacheBackend"] = None

__all__ = [
    "CacheBackend",
    "MemoryCacheBackend",
    "RedisCacheBackend",
    "get_cache_backend",
    "invalidate_cache",
    "get_cache_stats",
]


class CacheBackend:
    """Cache backend interface"""

    def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError

    def set(self, key: str, value: Any, ttl: int) -> None:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError

    def clear(self) -> None:
        raise NotImplementedError


class MemoryCacheBackend(CacheBackend):
    """In-memory cache backend"""

    def __init__(self) -> None:
        self._cache: dict[str, dict[str, Any]] = _memory_cache

    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None

        cache_entry = self._cache[key]
        if time.time() > cache_entry["expires_at"]:
            del self._cache[key]
            return None

        return cache_entry["value"]

    def set(self, key: str, value: Any, ttl: int) -> None:
        self._cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl,
            "created_at": time.time(),
        }

    def delete(self, key: str) -> None:
        if key in self._cache:
            del self._cache[key]

    def clear(self) -> None:
        self._cache.clear()

    def cleanup_expired(self) -> None:
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

    def __init__(self, redis_url: Optional[str] = None) -> None:
        try:
            import redis

            redis_url = redis_url or config.REDIS_URL
            self._client = redis.from_url(redis_url, decode_responses=True)
            self._client.ping()
            system_logger.info(f"Redis cache backend bağlandı: {redis_url}")
        except ImportError:
            raise ImportError(
                "Redis backend için 'redis' paketi gerekli. 'pip install redis' ile yükleyin."
            )
        except Exception as exc:  # pragma: no cover - network errors
            system_logger.error(f"Redis bağlantı hatası: {exc}")
            raise

    def get(self, key: str) -> Optional[Any]:
        try:
            value = self._client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception as exc:
            system_logger.error(f"Redis get error: {exc}")
            return None

    def set(self, key: str, value: Any, ttl: int) -> None:
        try:
            value_json = json.dumps(value)
            self._client.setex(key, ttl, value_json)
        except Exception as exc:
            system_logger.error(f"Redis set error: {exc}")

    def delete(self, key: str) -> None:
        try:
            self._client.delete(key)
        except Exception as exc:
            system_logger.error(f"Redis delete error: {exc}")

    def clear(self) -> None:
        try:
            self._client.flushdb()
        except Exception as exc:
            system_logger.error(f"Redis clear error: {exc}")


def get_cache_backend() -> CacheBackend:
    """Cache backend instance'ı al"""
    global _cache_backend

    if _cache_backend is None:
        backend_name = config.CACHE_BACKEND.lower()
        if backend_name == "redis":
            try:
                _cache_backend = RedisCacheBackend()
            except Exception as exc:  # pragma: no cover
                system_logger.warning(
                    f"Redis backend başlatılamadı, memory backend kullanılıyor: {exc}"
                )
                _cache_backend = MemoryCacheBackend()
        else:
            _cache_backend = MemoryCacheBackend()

    if isinstance(_cache_backend, MemoryCacheBackend):
        _cache_backend.cleanup_expired()

    return _cache_backend


def invalidate_cache(pattern: Optional[str] = None) -> None:
    """Cache'i invalidate et"""
    cache_backend = get_cache_backend()

    if pattern:
        if isinstance(cache_backend, RedisCacheBackend):
            try:
                keys = cache_backend._client.keys(pattern)
                if keys:
                    cache_backend._client.delete(*keys)
            except Exception as exc:
                system_logger.error(f"Cache invalidation error: {exc}")
        elif isinstance(cache_backend, MemoryCacheBackend):
            keys_to_delete = [
                key for key in cache_backend._cache.keys() if pattern in key
            ]
            for key in keys_to_delete:
                cache_backend.delete(key)
        return

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
    if isinstance(cache_backend, RedisCacheBackend):
        try:
            info = cache_backend._client.info("memory")
            return {
                "backend": "redis",
                "used_memory": info.get("used_memory_human", "N/A"),
                "keys": cache_backend._client.dbsize(),
            }
        except Exception as exc:
            system_logger.error(f"Redis stats error: {exc}")
            return {"backend": "redis", "error": str(exc)}

    return {"backend": "unknown"}
