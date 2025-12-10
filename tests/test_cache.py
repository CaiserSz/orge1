"""
Cache Module Testleri
Created: 2025-12-10 14:10:00
Last Modified: 2025-12-10 14:10:00
Version: 1.0.0
Description: Cache modülü için testler
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.cache import (
    MemoryCacheBackend,
    get_cache_backend,
    generate_cache_key,
    get_cache_stats,
)


class TestMemoryCacheBackend:
    """Memory cache backend testleri"""

    def test_cache_set_get(self):
        """Cache'e değer kaydetme ve alma testi"""
        cache = MemoryCacheBackend()

        # Değer kaydet
        cache.set("test_key", {"data": "test"}, ttl=60)

        # Değer al
        value = cache.get("test_key")
        assert value == {"data": "test"}

    def test_cache_expiration(self):
        """Cache expiration testi"""
        cache = MemoryCacheBackend()

        # Kısa TTL ile değer kaydet
        cache.set("test_key", {"data": "test"}, ttl=1)

        # Hemen al (hala geçerli olmalı)
        value = cache.get("test_key")
        assert value == {"data": "test"}

        # 2 saniye bekle
        time.sleep(2)

        # Tekrar al (expired olmalı)
        value = cache.get("test_key")
        assert value is None

    def test_cache_delete(self):
        """Cache silme testi"""
        cache = MemoryCacheBackend()

        # Değer kaydet
        cache.set("test_key", {"data": "test"}, ttl=60)

        # Değer al
        value = cache.get("test_key")
        assert value == {"data": "test"}

        # Sil
        cache.delete("test_key")

        # Tekrar al (None olmalı)
        value = cache.get("test_key")
        assert value is None

    def test_cache_clear(self):
        """Cache temizleme testi"""
        cache = MemoryCacheBackend()

        # Birden fazla değer kaydet
        cache.set("key1", {"data": "test1"}, ttl=60)
        cache.set("key2", {"data": "test2"}, ttl=60)

        # Değerleri al
        assert cache.get("key1") == {"data": "test1"}
        assert cache.get("key2") == {"data": "test2"}

        # Temizle
        cache.clear()

        # Değerler None olmalı
        assert cache.get("key1") is None
        assert cache.get("key2") is None


class TestCacheKeyGeneration:
    """Cache key generation testleri"""

    def test_generate_cache_key(self):
        """Cache key oluşturma testi"""
        path = "/api/status"
        query_params = {"limit": 10, "offset": 0}

        key1 = generate_cache_key(path, query_params)
        key2 = generate_cache_key(path, query_params)

        # Aynı parametrelerle aynı key oluşturulmalı
        assert key1 == key2

    def test_generate_cache_key_different_params(self):
        """Farklı parametrelerle farklı key oluşturma testi"""
        path = "/api/status"
        query_params1 = {"limit": 10}
        query_params2 = {"limit": 20}

        key1 = generate_cache_key(path, query_params1)
        key2 = generate_cache_key(path, query_params2)

        # Farklı parametrelerle farklı key oluşturulmalı
        assert key1 != key2

    def test_generate_cache_key_with_user_id(self):
        """User ID ile cache key oluşturma testi"""
        path = "/api/sessions"
        query_params = {}

        key1 = generate_cache_key(path, query_params, user_id="user1")
        key2 = generate_cache_key(path, query_params, user_id="user2")

        # Farklı user ID'lerle farklı key oluşturulmalı
        assert key1 != key2


class TestCacheFunctions:
    """Cache fonksiyon testleri"""

    def test_get_cache_backend(self):
        """Cache backend instance alma testi"""
        backend = get_cache_backend()
        assert backend is not None
        assert isinstance(backend, MemoryCacheBackend)

    def test_get_cache_stats(self):
        """Cache istatistikleri alma testi"""
        stats = get_cache_stats()
        assert "backend" in stats
        assert stats["backend"] == "memory"
