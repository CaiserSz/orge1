# Response Caching Implementasyonu

**Oluşturulma Tarihi:** 2025-12-10 14:00:00
**Son Güncelleme:** 2025-12-10 14:30:00
**Version:** 1.0.0

---

## Genel Bakış

API response caching implementasyonu, performans iyileştirmesi için eklenmiştir. Cache modülü hem in-memory hem de Redis backend desteği sunar.

---

## Özellikler

### Cache Backend'ler

1. **Memory Cache (Varsayılan)**
   - In-memory cache storage
   - TTL (Time To Live) desteği
   - Otomatik expiration cleanup
   - Production için uygun (küçük-orta ölçekli uygulamalar)

2. **Redis Cache (Opsiyonel)**
   - Redis backend desteği
   - Distributed cache
   - Production için önerilen (büyük ölçekli uygulamalar)

### Cache Stratejisi

- **TTL (Time To Live):** Her endpoint için özelleştirilebilir cache süresi
- **Cache Key Generation:** Path, query params ve user ID'ye göre unique key oluşturma
- **Cache Invalidation:** Pattern-based invalidation desteği
- **Cache Headers:** Response header'larında cache durumu bilgisi (X-Cache, X-Cache-Key)

---

## Kullanım

### Environment Variables

```bash
# Cache backend seçimi (memory veya redis)
CACHE_BACKEND=memory  # Varsayılan: memory

# Cache TTL (saniye cinsinden)
CACHE_TTL=300  # Varsayılan: 5 dakika

# Redis URL (Redis backend kullanılıyorsa)
REDIS_URL=redis://localhost:6379/0
```

### Decorator Kullanımı

```python
from api.cache import cache_response

@router.get("/api/status")
@cache_response(ttl=5, key_prefix="status")
async def get_status(request: Request):
    # ...
    return APIResponse(...)
```

### Cache Invalidation

```python
from api.cache import invalidate_cache

# Belirli pattern'i invalidate et
invalidate_cache("status:*")

# Tüm cache'i temizle
invalidate_cache()
```

---

## Implementasyon Detayları

### Cache'lenen Endpoint'ler

1. **GET /api/status** - 5 saniye cache
2. **GET /api/health** - 30 saniye cache
3. **GET /api/station/info** - 1 saat cache
4. **GET /api/current/available** - 1 saat cache
5. **GET /api/sessions/current** - 10 saniye cache
6. **GET /api/sessions/{session_id}** - 5 dakika cache
7. **GET /api/sessions/{session_id}/metrics** - 1 dakika cache
8. **GET /api/sessions** - 30 saniye cache (offset hariç)
9. **GET /api/sessions/users/{user_id}/sessions** - 30 saniye cache (offset hariç)
10. **GET /api/sessions/count/stats** - 1 dakika cache

### Cache Invalidation Noktaları

1. **POST /api/charge/start** - Status ve session cache'lerini invalidate eder
2. **POST /api/charge/stop** - Status, session ve list cache'lerini invalidate eder
3. **POST /api/maxcurrent** - Status cache'ini invalidate eder
4. **POST /api/station/info** - Station info cache'ini invalidate eder

---

## Testler

Cache modülü için testler `tests/test_cache.py` dosyasında bulunmaktadır:

- Memory cache backend testleri
- Cache expiration testleri
- Cache key generation testleri
- Cache functions testleri

**Test Çalıştırma:**
```bash
pytest tests/test_cache.py -v
```

---

## Performans İyileştirmeleri

### Beklenen İyileştirmeler

1. **Response Time:** Cache hit durumunda %80-90 azalma
2. **Database Load:** Session listesi sorgularında %60-70 azalma
3. **ESP32 Load:** Status endpoint'lerinde %50-60 azalma

### Cache Hit Rate Hedefleri

- Status endpoint: %70-80
- Session endpoints: %50-60
- Station info: %90-95

---

## Gelecek İyileştirmeler

1. **Cache Warming:** Uygulama başlangıcında kritik endpoint'leri cache'leme
2. **Cache Statistics:** Cache hit/miss oranları ve performans metrikleri
3. **Cache Compression:** Büyük response'lar için compression desteği
4. **Distributed Cache:** Redis cluster desteği

---

## Notlar

- Cache decorator sadece GET endpoint'leri için kullanılmalıdır
- POST/PUT/DELETE endpoint'leri cache invalidation yapmalıdır
- User-specific cache için user_id cache key'e dahil edilir
- Cache TTL değerleri endpoint'in veri değişim sıklığına göre ayarlanmalıdır

