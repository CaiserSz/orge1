# ESP32 Firmware Müdahale Politikası

**Tarih:** 2025-12-10
**Durum:** Aktif

---

## Temel Prensip

**ESP32 firmware'e müdahale edilmeyecek.**

Üretici sadece belirli komutları göndermemizi istiyor. Firmware davranışı ve state machine yönetimi tamamen ESP32 firmware'in sorumluluğundadır.

---

## RPi Tarafı Sorumlulukları

### ✅ Yapılacaklar

1. **Komut Gönderme:**
   - `authorization` komutu (şarj başlatma izni)
   - `charge_stop` komutu (şarj durdurma)
   - `current_set` komutu (akım ayarlama)
   - `lock/unlock` komutları (kilitleme/açma)

2. **State İzleme:**
   - ESP32'den gelen state değişikliklerini izlemek
   - Event'leri loglamak ve kaydetmek
   - Session yönetimi yapmak

3. **API Sağlama:**
   - REST API endpoint'leri sunmak
   - Kullanıcı arayüzü sağlamak
   - Güvenlik ve rate limiting

### ❌ Yapılmayacaklar

1. **Firmware Davranışı Kontrolü:**
   - ESP32 firmware'in state machine mantığını değiştirmek
   - Firmware'in otomatik davranışlarını engellemek
   - Firmware'in authorization kontrolünü override etmek

2. **Firmware Müdahalesi:**
   - Firmware kodunu değiştirmek
   - Firmware'in iç mantığını manipüle etmek
   - Firmware'in state transition'larını zorlamak

---

## ESP32 Firmware Davranışları

### Normal Davranışlar (Üretici Sorumluluğu)

1. **Otomatik Şarj Başlatma:**
   - ESP32 firmware `EV_CONNECTED` state'inde `onayStatus==ONAY_STAT_IZIN_VERILDI` kontrolü yapabilir
   - Bu durumda otomatik olarak `SARJA_HAZIR` state'ine geçebilir
   - Bu davranış ESP32 firmware'in normal mantığıdır

2. **State Machine Yönetimi:**
   - ESP32 firmware kendi içinde state machine yönetir
   - State transition'lar firmware'in kontrolündedir
   - RPi tarafı sadece komut gönderir, state'i kontrol edemez

3. **Authorization Yönetimi:**
   - ESP32 firmware `onayStatus` değerini kendi içinde yönetir
   - RFID kart okuma, authorization kontrolü firmware'in sorumluluğundadır
   - RPi tarafı sadece `authorization` komutu gönderir

---

## Bilinen Davranışlar

### Otomatik Şarj Başlatma

**Durum:** ESP32 firmware `EV_CONNECTED` state'inde `onayStatus==ONAY_STAT_IZIN_VERILDI` kontrolü yapıyor ve otomatik olarak şarj başlatıyor.

**Açıklama:**
- Bu davranış ESP32 firmware'in normal mantığıdır
- RPi tarafından kontrol edilemez
- Üreticinin firmware tasarımıdır

**RPi Tarafı Aksiyonu:**
- Sadece state değişikliklerini izlemek ve loglamak
- Kullanıcıya durumu bildirmek
- Şarjı durdurmak için `charge_stop` komutu göndermek

---

## API Endpoint'leri

RPi tarafından sağlanan endpoint'ler:

1. **POST /api/charge/start**
   - ESP32'ye `authorization` komutu gönderir
   - Sadece `EV_CONNECTED` state'inde çalışır
   - Firmware'in davranışını kontrol etmez

2. **POST /api/charge/stop**
   - ESP32'ye `charge_stop` komutu gönderir
   - Şarjı durdurmak için kullanılır
   - Firmware'in state transition'ını kontrol etmez

3. **POST /api/maxcurrent**
   - ESP32'ye `current_set` komutu gönderir
   - Akım değerini ayarlar
   - Firmware'in akım kontrolünü override etmez

---

## Sonuç

**RPi tarafı sadece komut gönderir, firmware davranışını kontrol edemez.**

ESP32 firmware'in otomatik davranışları (otomatik şarj başlatma, state transition'lar vb.) üreticinin sorumluluğundadır ve normal davranışlar olarak kabul edilir.

RPi tarafının görevi:
- Komutları göndermek
- State değişikliklerini izlemek
- API sağlamak
- Kullanıcı arayüzü sunmak

**Firmware davranışı üreticinin sorumluluğundadır.**

