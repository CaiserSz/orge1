# API Kullanım Örnekleri - Curl Komutları

**Oluşturulma Tarihi:** 2025-12-08 18:15:00  
**Son Güncelleme:** 2025-12-08 18:15:00  
**Version:** 1.0.0

---

## 🌐 Base URL

**Dışarıdan Erişim:** `https://lixhium.ngrok.app`  
**Local Erişim:** `http://localhost:8000`

---

## 📋 API Endpoint'leri

### 1. Sistem Sağlık Kontrolü

```bash
# Health check
curl https://lixhium.ngrok.app/api/health

# JSON formatında
curl -s https://lixhium.ngrok.app/api/health | python3 -m json.tool
```

**Örnek Yanıt:**
```json
{
    "success": true,
    "message": "System health check",
    "data": {
        "api": "healthy",
        "esp32_connected": true,
        "esp32_status": "available"
    },
    "timestamp": "2025-12-08T18:13:36.900908"
}
```

---

### 2. ESP32 Durum Bilgisi

```bash
# Durum bilgisi al
curl https://lixhium.ngrok.app/api/status

# JSON formatında
curl -s https://lixhium.ngrok.app/api/status | python3 -m json.tool
```

**Örnek Yanıt:**
```json
{
    "success": true,
    "message": "Status retrieved successfully",
    "data": {
        "CP": 0,
        "CPV": 3931,
        "PP": 0,
        "PPV": 2457,
        "RL": 0,
        "LOCK": 0,
        "MOTOR": 0,
        "PWM": 255,
        "MAX": 12,
        "CABLE": 0,
        "AUTH": 0,
        "STATE": 1,
        "PB": 0,
        "STOP": 0,
        "timestamp": "2025-12-08T18:13:35.757458"
    },
    "timestamp": "2025-12-08T18:13:40.442055"
}
```

**Parametre Açıklamaları:**
- `CP`: Control Pilot durumu
- `CPV`: Control Pilot voltajı
- `PP`: Proximity Pilot durumu
- `PPV`: Proximity Pilot voltajı
- `RL`: Relay durumu (0=kapalı, 1=açık)
- `LOCK`: Kilit durumu (0=kilitsiz, 1=kilitli)
- `MOTOR`: Motor durumu
- `PWM`: PWM değeri
- `MAX`: Maksimum akım (amper)
- `CABLE`: Kablo akımı
- `AUTH`: Yetkilendirme durumu (0=yok, 1=var)
- `STATE`: Şarj durumu
- `PB`: Power Board durumu
- `STOP`: Durdurma isteği (0=yok, 1=var)

---

### 3. Maksimum Akım Ayarlama

```bash
# Akım ayarla (örnek: 16A)
curl -X POST https://lixhium.ngrok.app/api/maxcurrent \
  -H "Content-Type: application/json" \
  -d '{"amperage": 16}'

# JSON formatında
curl -s -X POST https://lixhium.ngrok.app/api/maxcurrent \
  -H "Content-Type: application/json" \
  -d '{"amperage": 16}' | python3 -m json.tool
```

**Geçerli Aralık:** 6-32 amper (herhangi bir tam sayı)

**Örnek Değerler:**
- 6A: `{"amperage": 6}`
- 10A: `{"amperage": 10}`
- 12A: `{"amperage": 12}`
- 13A: `{"amperage": 13}`
- 16A: `{"amperage": 16}`
- 20A: `{"amperage": 20}`
- 25A: `{"amperage": 25}`
- 32A: `{"amperage": 32}`

**Örnek Başarılı Yanıt:**
```json
{
    "success": true,
    "message": "Akım ayarlandı: 16A",
    "data": {
        "amperage": 16,
        "command": "current_set"
    },
    "timestamp": "2025-12-08T18:15:00.000000"
}
```

**Örnek Hata Yanıtı (Şarj Aktifken):**
```json
{
    "detail": "Şarj aktifken akım değiştirilemez (State: 1)"
}
```

**ÖNEMLİ:** Akım ayarlama sadece aktif şarj başlamadan yapılabilir. Şarj esnasında akım değiştirilemez (güvenlik nedeniyle).

---

### 4. Kullanılabilir Akım Aralığı

```bash
# Kullanılabilir akım aralığını öğren
curl https://lixhium.ngrok.app/api/current/available

# JSON formatında
curl -s https://lixhium.ngrok.app/api/current/available | python3 -m json.tool
```

**Örnek Yanıt:**
```json
{
    "success": true,
    "message": "Kullanılabilir akım aralığı",
    "data": {
        "range": "6-32 amper",
        "min": 6,
        "max": 32,
        "unit": "amper",
        "note": "6-32 aralığında herhangi bir tam sayı değer kullanılabilir",
        "recommended": 16,
        "common_values": [6, 10, 13, 16, 20, 25, 32]
    },
    "timestamp": "2025-12-08T18:15:00.000000"
}
```

---

### 5. Şarj Başlatma

```bash
# Şarj başlat
curl -X POST https://lixhium.ngrok.app/api/charge/start \
  -H "Content-Type: application/json" \
  -d '{}'

# JSON formatında
curl -s -X POST https://lixhium.ngrok.app/api/charge/start \
  -H "Content-Type: application/json" \
  -d '{}' | python3 -m json.tool
```

---

### 6. Şarj Durdurma

```bash
# Şarj durdur
curl -X POST https://lixhium.ngrok.app/api/charge/stop \
  -H "Content-Type: application/json" \
  -d '{}'

# JSON formatında
curl -s -X POST https://lixhium.ngrok.app/api/charge/stop \
  -H "Content-Type: application/json" \
  -d '{}' | python3 -m json.tool
```

---

## 🔄 Örnek Kullanım Senaryoları

### Senaryo 1: Durum Kontrolü ve Akım Ayarlama

```bash
# 1. Durum kontrolü
curl -s https://lixhium.ngrok.app/api/status | python3 -m json.tool

# 2. Eğer STATE=0 ise (şarj aktif değil), akım ayarla
curl -s -X POST https://lixhium.ngrok.app/api/maxcurrent \
  -H "Content-Type: application/json" \
  -d '{"amperage": 16}' | python3 -m json.tool

# 3. Durumu tekrar kontrol et (MAX değerinin değiştiğini gör)
curl -s https://lixhium.ngrok.app/api/status | python3 -m json.tool
```

### Senaryo 2: Farklı Akım Değerleri Test Etme

```bash
# 10A ayarla
curl -s -X POST https://lixhium.ngrok.app/api/maxcurrent \
  -H "Content-Type: application/json" \
  -d '{"amperage": 10}' | python3 -m json.tool

# 20A ayarla
curl -s -X POST https://lixhium.ngrok.app/api/maxcurrent \
  -H "Content-Type: application/json" \
  -d '{"amperage": 20}' | python3 -m json.tool

# 25A ayarla
curl -s -X POST https://lixhium.ngrok.app/api/maxcurrent \
  -H "Content-Type: application/json" \
  -d '{"amperage": 25}' | python3 -m json.tool
```

---

## 🚨 Hata Durumları

### ESP32 Bağlantısı Yok
```json
{
    "detail": "ESP32 bağlantısı yok"
}
```

### Şarj Aktifken Akım Değiştirme
```json
{
    "detail": "Şarj aktifken akım değiştirilemez (State: 1)"
}
```

### Geçersiz Akım Değeri
```json
{
    "detail": [
        {
            "loc": ["body", "amperage"],
            "msg": "ensure this value is greater than or equal to 6",
            "type": "value_error.number.not_ge"
        }
    ]
}
```

---

## 📝 Notlar

- Tüm endpoint'ler JSON formatında yanıt döner
- `python3 -m json.tool` ile JSON formatını güzelleştirebilirsiniz
- API dokümantasyonu: `https://lixhium.ngrok.app/docs`
- ReDoc: `https://lixhium.ngrok.app/redoc`

---

**Son Güncelleme:** 2025-12-08 18:15:00

