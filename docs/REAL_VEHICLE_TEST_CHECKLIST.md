# Gerçek Araç Testi Kontrol Listesi

**Oluşturulma Tarihi:** 2025-12-10 12:05:00
**Son Güncelleme:** 2025-12-10 12:05:00
**Versiyon:** 1.0.0

## Özet

Bu dokümantasyon, API'nin gerçek bir elektrikli araç ile test edilebilmesi için gerekli tüm kontrolleri ve adımları içerir.

---

## ✅ Sistem Durumu Kontrolü

### 1. ESP32 Bridge Bağlantısı
- ✅ **Durum:** ESP32 bridge bağlı ve çalışıyor
- ✅ **Port:** Otomatik bulunuyor (`/dev/ttyUSB0`)
- ✅ **Baudrate:** 115200
- ✅ **Monitor Thread:** Çalışıyor

### 2. API Servisi
- ✅ **Durum:** API servisi çalışıyor
- ✅ **Endpoints:** 23 endpoint aktif
- ✅ **Health Check:** `/api/health` endpoint'i çalışıyor
- ✅ **Status Endpoint:** `/api/status` endpoint'i çalışıyor

### 3. Authentication
- ⚠️ **SECRET_API_KEY:** Tanımlı değil (`.env` dosyasında olmalı)
- ✅ **API Key Header:** `X-API-Key` header'ı kullanılıyor
- ✅ **Rate Limiting:** Aktif (charge endpoint'leri için 10/dakika)

### 4. Service Layer
- ✅ **ChargeService:** Implement edilmiş
- ✅ **CurrentService:** Implement edilmiş
- ✅ **StatusService:** Implement edilmiş

### 5. Error Handling
- ✅ **ESP32 Bağlantı Kontrolü:** Var
- ✅ **State Validation:** Var (EV_CONNECTED kontrolü)
- ✅ **Race Condition Önleme:** Var (final state check)
- ✅ **Error Logging:** Var

---

## 🔧 Gerçek Araç Testi İçin Gereksinimler

### Zorunlu Gereksinimler

1. **SECRET_API_KEY Tanımlanmalı**
   ```bash
   # .env dosyasına eklenmeli:
   SECRET_API_KEY=your-secret-api-key-here
   ```

2. **ESP32 Bağlı Olmalı**
   - ✅ Şu anda bağlı: `/dev/ttyUSB0`
   - Port otomatik bulunuyor veya `ESP32_PORT` environment variable ile belirtilebilir

3. **Araç Bağlı Olmalı**
   - ESP32 STATE değeri `3` (EV_CONNECTED) olmalı
   - Bu durumda şarj başlatılabilir

4. **API Servisi Çalışıyor Olmalı**
   ```bash
   # Servisi başlatmak için:
   cd /home/basar/charger
   source env/bin/activate
   uvicorn api.main:app --host 0.0.0.0 --port 8000
   ```

### Test Senaryosu

#### 1. Durum Kontrolü
```bash
# Status endpoint'inden ESP32 durumunu kontrol et
curl -X GET "http://localhost:8000/api/status"
```

**Beklenen Response:**
```json
{
  "success": true,
  "message": "Status retrieved successfully",
  "data": {
    "STATE": 3,  // EV_CONNECTED
    "CP": 1,
    "PP": 1,
    "MAX": 32,
    "AUTH": 0,
    ...
  }
}
```

#### 2. Şarj Başlatma
```bash
# API key ile şarj başlatma
curl -X POST "http://localhost:8000/api/charge/start" \
  -H "X-API-Key: your-secret-api-key" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Beklenen Response:**
```json
{
  "success": true,
  "message": "Şarj başlatma komutu gönderildi",
  "data": {
    "command": "authorization"
  }
}
```

**Önemli Notlar:**
- Sadece `STATE=3` (EV_CONNECTED) durumunda çalışır
- Diğer state'lerde hata döndürülür:
  - `STATE=1` (IDLE): "Kablo takılı değil"
  - `STATE=2` (CABLE_DETECT): "Araç bağlı değil"
  - `STATE=4` (READY): "Authorization zaten verilmiş"
  - `STATE>=5` (CHARGING/PAUSED/STOPPED): "Şarj zaten aktif"

#### 3. Akım Ayarlama
```bash
# Maksimum akım ayarlama (6-32 amper arası)
curl -X POST "http://localhost:8000/api/maxcurrent" \
  -H "X-API-Key: your-secret-api-key" \
  -H "Content-Type: application/json" \
  -d '{"amperage": 16}'
```

**Önemli Notlar:**
- Şarj aktifken (STATE >= 5) akım değiştirilemez
- Geçerli aralık: 6-32 amper

#### 4. Şarj Durdurma
```bash
# Şarj durdurma
curl -X POST "http://localhost:8000/api/charge/stop" \
  -H "X-API-Key: your-secret-api-key" \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## 🌐 Web Arayüzü ile Test

### Test Sayfası
- **URL:** `http://localhost:8000/test`
- **API Key Endpoint:** `http://localhost:8000/api/test/key`

Test sayfası (`api_test.html`) şu özellikleri içerir:
- ✅ Status kontrolü
- ✅ Şarj başlatma/durdurma
- ✅ Akım ayarlama
- ✅ Gerçek zamanlı durum gösterimi

---

## ⚠️ Dikkat Edilmesi Gerekenler

### 1. State Kontrolü
- Şarj başlatma sadece `EV_CONNECTED` (STATE=3) durumunda çalışır
- State kontrolü iki kez yapılır (race condition önleme):
  1. İlk kontrol: Komut gönderilmeden önce
  2. Final kontrol: Komut gönderilmeden hemen önce

### 2. ESP32 Bağlantısı
- ESP32 bağlantısı koparsa, otomatik reconnect denemesi yapılır
- Maksimum 3 deneme, her deneme arasında 5 saniye bekleme

### 3. Error Handling
- ESP32 bağlantısı yoksa: `503 Service Unavailable`
- Geçersiz state: `400 Bad Request` veya `503 Service Unavailable`
- Komut gönderilemezse: `500 Internal Server Error`

### 4. Rate Limiting
- Charge endpoint'leri: 10 istek/dakika
- Status endpoint'i: 30 istek/dakika
- Rate limit aşılırsa: `429 Too Many Requests`

---

## 📊 Test Sonuçları ve Loglama

### Log Dosyaları
- **System Logs:** `logs/system.log`
- **ESP32 Logs:** `logs/esp32.log`
- **Event Logs:** `logs/events.log`

### Log Formatı
```json
{
  "timestamp": "2025-12-10T12:00:00",
  "level": "INFO",
  "logger": "system",
  "message": "Charge start successful",
  "extra": {
    "endpoint": "/api/charge/start",
    "user_id": "test-user",
    "current_state": 3,
    "state_name": "EV_CONNECTED"
  }
}
```

---

## ✅ Hazırlık Kontrol Listesi

Gerçek araç testi öncesi kontrol edilmesi gerekenler:

- [ ] SECRET_API_KEY `.env` dosyasında tanımlı
- [ ] ESP32 bağlı ve çalışıyor (`/api/health` kontrolü)
- [ ] API servisi çalışıyor (`/api/status` kontrolü)
- [ ] Araç bağlı ve STATE=3 (EV_CONNECTED)
- [ ] Test sayfası erişilebilir (`/test`)
- [ ] Log dosyaları yazılabilir durumda
- [ ] Rate limiting ayarları uygun

---

## 🚀 Hızlı Başlangıç

```bash
# 1. Environment variable'ları kontrol et
cat .env | grep SECRET_API_KEY

# 2. API servisini başlat
cd /home/basar/charger
source env/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8000

# 3. Başka bir terminal'de status kontrolü
curl http://localhost:8000/api/status

# 4. Web arayüzünden test et
# Browser'da: http://localhost:8000/test
```

---

## 📝 Notlar

- API servisi başlatıldığında otomatik olarak ESP32 bridge bağlantısı kurulur
- Event detector otomatik olarak başlatılır ve state değişikliklerini izler
- Session manager otomatik olarak başlatılır ve şarj oturumlarını takip eder
- Tüm kritik işlemler loglanır (audit trail)

---

**Son Güncelleme:** 2025-12-10 12:05:00

