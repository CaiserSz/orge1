# ESP32 Loglama ve Session Yönetimi Değerlendirmesi

**Değerlendirme Tarihi:** 2025-12-09 02:20:00  
**Versiyon:** 1.0.0  
**Durum:** Mevcut durum analizi ve öneriler

---

## 📊 Mevcut Durum Analizi

### ✅ Mevcut Özellikler

1. **ESP32 Bridge Monitoring:**
   - ✅ ESP32'den gelen status mesajları parse ediliyor
   - ✅ Status mesajları `last_status` değişkeninde tutuluyor
   - ✅ Thread-based monitoring mekanizması var
   - ✅ Status mesajları her 7.5 saniyede bir ESP32'den geliyor

2. **Mevcut Loglama:**
   - ⚠️ Sadece `print()` ile konsola yazılıyor
   - ⚠️ Dosyaya loglama yok
   - ⚠️ Structured logging yok
   - ⚠️ Log rotation yok

3. **Session Yönetimi:**
   - ❌ Session tracking yok
   - ❌ Session ID yok
   - ❌ Session başlangıç/bitiş zamanları yok
   - ❌ Session summary yok

### ❌ Eksik Özellikler

1. **Loglama:**
   - ❌ ESP32 mesajları loglanmıyor
   - ❌ State transition'lar loglanmıyor
   - ❌ API komutları loglanmıyor
   - ❌ Hata mesajları loglanmıyor
   - ❌ Structured logging yok

2. **Session Yönetimi:**
   - ❌ Session tanımı yok
   - ❌ Session başlangıç tespiti yok
   - ❌ Session bitiş tespiti yok
   - ❌ Session verileri saklanmıyor
   - ❌ Session summary oluşturulmuyor

3. **Event Tracking:**
   - ❌ Kablo takılma event'i takip edilmiyor
   - ❌ Araç bağlantı event'i takip edilmiyor
   - ❌ Şarj başlatma event'i takip edilmiyor
   - ❌ Şarj durdurma event'i takip edilmiyor
   - ❌ Şarj duraklatma event'i takip edilmiyor
   - ❌ Şarj devam ettirme event'i takip edilmiyor
   - ❌ Kablo çıkarma event'i takip edilmiyor

---

## 🎯 Önerilen Çözüm Mimarisi

### 1. Session Tanımı

**Session:** Bir şarj döngüsünün tamamı
- **Başlangıç:** Kablo takılma (STATE=2: CABLE_DETECT)
- **Bitiş:** Kablo çıkarma (STATE=1: IDLE) veya hata durumu

**Session Fazları:**
1. **CABLE_DETECTED** (STATE=2) - Kablo takıldı
2. **EV_CONNECTED** (STATE=3) - Araç bağlandı
3. **READY** (STATE=4) - Şarja hazır
4. **CHARGING** (STATE=5) - Şarj aktif
5. **PAUSED** (STATE=6) - Şarj duraklatıldı
6. **STOPPED** (STATE=7) - Şarj durduruldu
7. **COMPLETED** (STATE=1) - Session tamamlandı (kablo çıkarıldı)
8. **FAULT** (STATE=8) - Hata durumu

### 2. Loglama Sistemi

**Log Seviyeleri:**
- **DEBUG:** Detaylı bilgiler (her status mesajı)
- **INFO:** Önemli event'ler (state transition, komutlar)
- **WARNING:** Uyarılar (timeout, retry)
- **ERROR:** Hatalar (bağlantı kopması, parse hatası)

**Log Formatları:**
- **Structured JSON:** Machine-readable format
- **Human-readable:** Kolay okunabilir format
- **CSV:** Analiz için

**Log Kategorileri:**
- `esp32_status` - ESP32 status mesajları
- `esp32_command` - ESP32'ye gönderilen komutlar
- `api_request` - API istekleri
- `session_event` - Session event'leri
- `state_transition` - State geçişleri
- `error` - Hata mesajları

### 3. Session Yönetimi

**Session Veri Modeli:**
```python
{
    "session_id": "uuid",
    "start_time": "2025-12-09T02:15:00",
    "end_time": "2025-12-09T03:45:00",
    "duration_seconds": 5400,
    "events": [
        {
            "timestamp": "2025-12-09T02:15:00",
            "event_type": "CABLE_DETECTED",
            "state": 2,
            "data": {...}
        },
        ...
    ],
    "summary": {
        "total_energy_kwh": 12.5,
        "max_current_a": 8,
        "average_current_a": 7.5,
        "state_durations": {
            "CABLE_DETECTED": 30,
            "EV_CONNECTED": 60,
            "CHARGING": 5200,
            "PAUSED": 110
        },
        "state_transitions": 8,
        "errors": []
    }
}
```

---

## 🏗️ Teknik Öneriler

### 1. Logging Modülü (`api/logging.py`)

**Özellikler:**
- Structured logging (JSON format)
- Log rotation (günlük, haftalık)
- Log seviyesi kontrolü
- Farklı log kategorileri
- Thread-safe logging

**Kullanım:**
```python
from api.logging import get_logger

logger = get_logger('esp32_status')
logger.info("Status received", extra={"state": 5, "current": 8})
```

### 2. Session Manager (`api/session_manager.py`)

**Özellikler:**
- Session oluşturma ve yönetimi
- Event tracking
- State transition detection
- Session summary generation
- Session storage (JSON/DB)

**Kullanım:**
```python
from api.session_manager import SessionManager

session_manager = SessionManager()
session_manager.on_state_change(old_state=2, new_state=3)
session_manager.on_event("EV_CONNECTED", data={...})
session = session_manager.get_current_session()
summary = session_manager.get_session_summary(session_id)
```

### 3. Event Detector (`api/event_detector.py`)

**Özellikler:**
- State transition detection
- Event type classification
- Event data extraction
- Event timestamping

**Event Types:**
- `CABLE_DETECTED` - Kablo takıldı
- `EV_CONNECTED` - Araç bağlandı
- `CHARGE_STARTED` - Şarj başladı
- `CHARGE_PAUSED` - Şarj duraklatıldı
- `CHARGE_RESUMED` - Şarj devam ettirildi
- `CHARGE_STOPPED` - Şarj durduruldu
- `CABLE_REMOVED` - Kablo çıkarıldı
- `FAULT_DETECTED` - Hata tespit edildi

### 4. Session Storage (`data/sessions/`)

**Dosya Yapısı:**
```
data/
  sessions/
    2025-12-09/
      session_<uuid>.json
      session_<uuid>_summary.json
    index.json  # Tüm session'ların listesi
```

**Session Dosyası Formatı:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "start_time": "2025-12-09T02:15:00",
  "end_time": "2025-12-09T03:45:00",
  "events": [...],
  "summary": {...}
}
```

---

## 📋 Implementation Plan

### Faz 1: Temel Loglama (1-2 gün)

1. **Logging Modülü Oluşturma:**
   - `api/logging.py` modülü
   - Structured logging (JSON)
   - Log rotation
   - Thread-safe

2. **ESP32 Bridge'e Loglama Entegrasyonu:**
   - Status mesajlarını logla
   - Komut gönderimlerini logla
   - Hataları logla

3. **API'ye Loglama Entegrasyonu:**
   - API isteklerini logla
   - API yanıtlarını logla
   - Hataları logla

### Faz 2: Event Detection (2-3 gün)

1. **Event Detector Oluşturma:**
   - State transition detection
   - Event type classification
   - Event data extraction

2. **ESP32 Bridge'e Event Detection Entegrasyonu:**
   - State değişikliklerini tespit et
   - Event'leri oluştur
   - Event'leri logla

### Faz 3: Session Management (3-4 gün)

1. **Session Manager Oluşturma:**
   - Session oluşturma
   - Event tracking
   - Session storage

2. **Session Summary Generation:**
   - Session özeti hesaplama
   - İstatistikler
   - Rapor oluşturma

3. **API Endpoint'leri:**
   - `GET /api/sessions` - Tüm session'ları listele
   - `GET /api/sessions/{session_id}` - Session detayı
   - `GET /api/sessions/{session_id}/summary` - Session özeti
   - `GET /api/sessions/current` - Aktif session

### Faz 4: İyileştirmeler (1-2 gün)

1. **Performance Optimization:**
   - Async logging
   - Batch processing
   - Compression

2. **Monitoring ve Alerting:**
   - Session duration monitoring
   - Error rate monitoring
   - Performance metrics

---

## 🎯 Öncelik Sırası

### 🔴 Yüksek Öncelik (Hemen)

1. **Temel Loglama:**
   - ESP32 mesajlarını logla
   - API isteklerini logla
   - Hataları logla

2. **Event Detection:**
   - State transition detection
   - Temel event'leri tespit et

### ⚠️ Orta Öncelik (1 hafta içinde)

3. **Session Management:**
   - Session oluşturma
   - Event tracking
   - Session storage

4. **Session Summary:**
   - Özet hesaplama
   - İstatistikler
   - Rapor oluşturma

### 📝 Düşük Öncelik (İleride)

5. **Advanced Features:**
   - Real-time monitoring dashboard
   - Alerting system
   - Analytics ve reporting

---

## 💡 Önerilen Yaklaşım

### 1. Minimal Viable Product (MVP)

**Hedef:** En kısa sürede çalışan bir sistem

**Özellikler:**
- ✅ Temel loglama (JSON format)
- ✅ State transition detection
- ✅ Session oluşturma ve bitirme
- ✅ Basit session summary

**Süre:** 2-3 gün

### 2. Full Featured System

**Hedef:** Production-ready sistem

**Özellikler:**
- ✅ Tüm özellikler
- ✅ Performance optimization
- ✅ Monitoring ve alerting
- ✅ Analytics

**Süre:** 1-2 hafta

---

## 🔍 Teknik Detaylar

### Log Format Örneği

**ESP32 Status Log:**
```json
{
  "timestamp": "2025-12-09T02:15:00.123456",
  "level": "INFO",
  "category": "esp32_status",
  "message": "Status received",
  "data": {
    "state": 5,
    "current": 8,
    "voltage": 230,
    "power": 1840
  }
}
```

**State Transition Log:**
```json
{
  "timestamp": "2025-12-09T02:15:05.123456",
  "level": "INFO",
  "category": "state_transition",
  "message": "State changed",
  "data": {
    "old_state": 3,
    "new_state": 5,
    "old_state_name": "EV_CONNECTED",
    "new_state_name": "CHARGING",
    "session_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**Session Event Log:**
```json
{
  "timestamp": "2025-12-09T02:15:05.123456",
  "level": "INFO",
  "category": "session_event",
  "message": "Charge started",
  "data": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "event_type": "CHARGE_STARTED",
    "state": 5,
    "max_current": 8
  }
}
```

### Session Summary Örneği

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "start_time": "2025-12-09T02:15:00",
  "end_time": "2025-12-09T03:45:00",
  "duration_seconds": 5400,
  "duration_formatted": "1h 30m",
  "events_count": 8,
  "state_transitions": [
    {
      "from": "CABLE_DETECTED",
      "to": "EV_CONNECTED",
      "timestamp": "2025-12-09T02:15:30",
      "duration_seconds": 30
    },
    ...
  ],
  "summary": {
    "total_energy_kwh": 12.5,
    "max_current_a": 8,
    "average_current_a": 7.5,
    "peak_power_w": 1840,
    "state_durations": {
      "CABLE_DETECTED": 30,
      "EV_CONNECTED": 60,
      "CHARGING": 5200,
      "PAUSED": 110
    },
    "state_percentages": {
      "CABLE_DETECTED": 0.6,
      "EV_CONNECTED": 1.1,
      "CHARGING": 96.3,
      "PAUSED": 2.0
    },
    "errors": [],
    "warnings": []
  }
}
```

---

## 🚀 Sonuç ve Öneriler

### Mevcut Durum

**Eksiklikler:**
- ❌ Loglama sistemi yok
- ❌ Session yönetimi yok
- ❌ Event tracking yok
- ❌ Session summary yok

**Etkiler:**
- 🔴 Şarj süreçleri takip edilemiyor
- 🔴 Hata analizi yapılamıyor
- 🔴 Performance analizi yapılamıyor
- 🔴 Kullanıcı deneyimi analizi yapılamıyor

### Önerilen Çözüm

**Yaklaşım:** Incremental implementation
1. Önce temel loglama (MVP)
2. Sonra event detection
3. Sonra session management
4. Son olarak advanced features

**Süre:** 1-2 hafta (tam özellikli sistem)

**Faydalar:**
- ✅ Şarj süreçleri tam takip edilebilir
- ✅ Hata analizi yapılabilir
- ✅ Performance analizi yapılabilir
- ✅ Kullanıcı deneyimi analizi yapılabilir
- ✅ Session summary ile raporlama mümkün

---

**Sonraki Adım:** MVP implementation başlatılabilir.

