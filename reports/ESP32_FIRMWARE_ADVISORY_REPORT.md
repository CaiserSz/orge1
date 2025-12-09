# ESP32 Firmware Tavsiye Raporu

**Tarih:** 2025-12-10 00:35:00  
**Rapor Tipi:** Tavsiye ve Risk Değerlendirmesi  
**Sorumluluk:** ESP32 Firmware Geliştirici  
**RPi Tarafı:** Bu rapor ESP32 firmware geliştiricisine sunulmak üzere hazırlanmıştır

---

## 🎯 Amaç

Bu rapor, ESP32 firmware ve RPi Python API arasındaki tutarsızlıklar, mantık hataları ve riskleri tespit etmek ve ESP32 firmware geliştiricisine tavsiyeler sunmak amacıyla hazırlanmıştır.

**ÖNEMLİ:** RPi tarafı bu sorunları tespit etmiş ve geçici çözümler (defense in depth) uygulamıştır. Ancak kök neden ESP32 firmware'de olduğu için kalıcı çözüm ESP32 firmware tarafında yapılmalıdır.

---

## 🔴 KRİTİK SORUNLAR

### Sorun #1: Authorization Komutu Ters Mantık

**Lokasyon:** `esp32/Commercial_08122025.ino:956`

**Mevcut Kod:**
```cpp
case KOMUT_AUTH: // 1
  if (val == 1) {
    if (sarjStatus!=SARJ_STAT_IDLE){  // ❌ TERS MANTIK
    authEnabled = true;
    onayStatus = ONAY_STAT_IZIN_VERILDI;
```

**Sorun:**
- Authorization komutu sadece **IDLE DEĞİLSE** çalışıyor
- Bu **ters mantık**! Authorization normalde IDLE, CABLE_DETECT, EV_CONNECTED veya READY state'lerinde verilmeli
- Şu anki kod: Şarj aktifken (STATE=5+) authorization veriyor, IDLE'dayken vermiyor!

**Gerçek Dünya Etkisi:**
- RPi API'den `/api/charge/start` çağrıldığında ESP32 authorization'ı reddediyor (IDLE'dayken)
- Şarj başlatılamıyor
- Sistem kullanılamaz durumda

**RPi Tarafı Geçici Çözüm:**
- RPi API state kontrolü yapıyor (State 1-4 kontrolü)
- Ancak ESP32 firmware ters mantık nedeniyle komutu reddediyor
- **Sistem şu anda çalışmıyor**

**Önerilen Düzeltme:**
```cpp
case KOMUT_AUTH: // 1
  if (val == 1) {
    if (sarjStatus == SARJ_STAT_IDLE || 
        sarjStatus == SARJ_CABLE_DETECT || 
        sarjStatus == EV_CONNECTED || 
        sarjStatus == SARJA_HAZIR) {  // ✅ DOĞRU MANTIK
      authEnabled = true;
      onayStatus = ONAY_STAT_IZIN_VERILDI;
      LOCKFLAG=0; RelayFlag=0;
      stopRequested = false;
      SerialUSB.println("<ACK;CMD=AUTH;STATUS=OK;>");
    } else {
      SerialUSB.println("<ACK;CMD=AUTH;STATUS=ERR;STATE_INVALID;>");
    }
```

**Öncelik:** 🔴 **ACİL - Sistem Çalışmıyor**

---

### Sorun #2: Assignment Hatası - Authorization Clear

**Lokasyon:** `esp32/Commercial_08122025.ino:964`

**Mevcut Kod:**
```cpp
} else {
  if((sarjStatus=SARJ_STAT_SARJ_DURAKLATILDI)|| (SARJ_STAT_SARJ_BASLADI)){  // ❌ ASSIGNMENT
  authEnabled = false;
```

**Sorun:**
- `sarjStatus=SARJ_STAT_SARJ_DURAKLATILDI` → **Assignment** (== olmalı)
- Bu kod her zaman `true` döner çünkü assignment başarılı olur
- State kontrolü çalışmıyor!

**Gerçek Dünya Etkisi:**
- Authorization clear komutu her zaman çalışıyor (state kontrolü yok)
- Şarj durdurma komutu beklenmedik davranışlar sergileyebilir

**RPi Tarafı Geçici Çözüm:**
- RPi API state kontrolü yapıyor
- Ancak ESP32 firmware state kontrolü yapmıyor

**Önerilen Düzeltme:**
```cpp
} else {
  if((sarjStatus == SARJ_STAT_SARJ_DURAKLATILDI) || (sarjStatus == SARJ_STAT_SARJ_BASLADI)){  // ✅
  authEnabled = false;
  onayStatus = ONAY_STAT_IPTAL_ISTENDI;
  LOCKFLAG=0; RelayFlag=0;
  SerialUSB.println("<ACK;CMD=AUTH;STATUS=CLEARED;>");
  } else {
    SerialUSB.println("<ACK;CMD=AUTH;STATUS=NOT CLEARED;>");
  }
}
```

**Öncelik:** 🔴 **ACİL - Mantık Hatası**

---

### Sorun #3: Assignment Hatası - Current Set

**Lokasyon:** `esp32/Commercial_08122025.ino:974`

**Mevcut Kod:**
```cpp
case KOMUT_SET_MAX_AMP: //2
  if (sarjStatus=SARJ_STAT_IDLE){  // ❌ ASSIGNMENT
  if (val >= 6 && val <= DEFAULT_MAX_CURRENT) {
    maxCurrent = val;
```

**Sorun:**
- `sarjStatus=SARJ_STAT_IDLE` → **Assignment** (== olmalı)
- Bu kod her zaman `true` döner
- State kontrolü çalışmıyor!

**Gerçek Dünya Etkisi:**
- Akım ayarlama komutu her zaman çalışıyor (state kontrolü yok)
- Şarj aktifken bile akım değiştirilebilir (güvenlik riski!)
- RPi API'deki state kontrolü gereksiz görünüyor ama aslında kritik (ESP32 kontrol etmiyor)

**RPi Tarafı Geçici Çözüm:**
- RPi API state kontrolü yapıyor (State >= 5 kontrolü)
- Defense in depth sağlıyor
- Ancak ESP32 firmware'deki bug nedeniyle güvenlik riski var

**Önerilen Düzeltme:**
```cpp
case KOMUT_SET_MAX_AMP: //2
  if (sarjStatus == SARJ_STAT_IDLE || 
      sarjStatus == SARJ_CABLE_DETECT || 
      sarjStatus == EV_CONNECTED || 
      sarjStatus == SARJA_HAZIR) {  // ✅
    if (val >= 6 && val <= DEFAULT_MAX_CURRENT) {
      maxCurrent = val;
      SerialUSB.println("<ACK;CMD=SETMAXAMP;STATUS=OK;>");
    } else {
      SerialUSB.println("<ACK;CMD=SETMAXAMP;STATUS=ERR;>");
    }
  } else {
    SerialUSB.println("<ACK;CMD=SETMAXAMP;STATUS=ERR;STATE_INVALID;>");
  }
```

**Öncelik:** 🔴 **ACİL - Güvenlik Riski**

---

## 🟡 ORTA SEVİYE SORUNLAR

### Sorun #4: State Transition Mantık Hatası

**Lokasyon:** `esp32/Commercial_08122025.ino:755`

**Mevcut Kod:**
```cpp
case SARJ_STAT_SARJ_DURAKLATILDI: //6
  ...
  if(cpStatus==CP_STAT_CHARGING){
    sarjStatus=SARJA_HAZIR;  // ❌ MANTIK HATASI
  }
```

**Sorun:**
- PAUSED (6) state'inden CHARGING'e geçiş yapılırken SARJA_HAZIR (4) state'ine gidiliyor
- Bu mantıksız! PAUSED → CHARGING direkt geçiş olmalı
- SARJA_HAZIR'a geri dönmek gereksiz ve yanlış

**RPi Tarafı Etkisi:**
- RPi Event Detector bu transition'ı tanımıyor
- Event detection eksik
- Session management yanlış bilgi alabilir

**Önerilen Düzeltme:**
```cpp
case SARJ_STAT_SARJ_DURAKLATILDI: //6
  ...
  if(cpStatus==CP_STAT_CHARGING){
    sarjStatus=SARJ_STAT_SARJ_BASLADI;  // ✅ PAUSED → CHARGING direkt
  }
```

**Öncelik:** 🟡 **ORTA - Mantık Hatası**

---

## 📊 Risk Değerlendirmesi

### Kritik Riskler

1. **Sistem Çalışmıyor:** Authorization komutu ters mantık nedeniyle sistem kullanılamaz durumda
2. **Güvenlik Riski:** Current set komutu state kontrolü yapmıyor, şarj aktifken akım değiştirilebilir
3. **Mantık Hataları:** Assignment hataları nedeniyle state kontrolü çalışmıyor

### Orta Riskler

4. **Event Detection Eksik:** State transition mantık hatası nedeniyle event detection eksik
5. **Tutarsızlık:** ESP32 firmware ve RPi API arasında tutarsızlıklar var

---

## 🎯 RPi Tarafı Geçici Çözümler

RPi tarafı şu anda aşağıdaki geçici çözümleri uygulamıştır:

1. **State Validation:** Python API'de state kontrolü yapılıyor (defense in depth)
2. **Error Handling:** ESP32 firmware hatalarına karşı error handling mevcut
3. **Logging:** Tüm komutlar ve state değişiklikleri loglanıyor

**Ancak:** Bu çözümler ESP32 firmware'deki kök nedenleri çözmüyor. Kalıcı çözüm ESP32 firmware tarafında yapılmalıdır.

---

## 📋 Test Senaryoları

### Test Senaryosu #1: Authorization Komutu

**Beklenen Davranış:**
1. State = IDLE → Authorization ✅
2. State = CABLE_DETECT → Authorization ✅
3. State = EV_CONNECTED → Authorization ✅
4. State = READY → Authorization ✅
5. State = CHARGING → Authorization ❌
6. State = PAUSED → Authorization ❌

**Mevcut Davranış:**
1. State = IDLE → Authorization ❌ (Ters mantık!)
2. State = CHARGING → Authorization ✅ (Yanlış!)

### Test Senaryosu #2: Current Set Komutu

**Beklenen Davranış:**
1. State = IDLE → Current Set ✅
2. State = CABLE_DETECT → Current Set ✅
3. State = EV_CONNECTED → Current Set ✅
4. State = READY → Current Set ✅
5. State = CHARGING → Current Set ❌
6. State = PAUSED → Current Set ❌

**Mevcut Davranış:**
1. Her state → Current Set ✅ (Assignment hatası nedeniyle!)

---

## 🎯 Öneriler ve Tavsiyeler

### Acil Öncelikli Düzeltmeler

1. **Authorization Komutu Mantık Hatası:** Satır 956 - Sistem çalışmıyor
2. **Assignment Hataları:** Satır 964, 974 - State kontrolü çalışmıyor
3. **Current Set Güvenlik Riski:** Satır 974 - Güvenlik riski

### Orta Öncelikli Düzeltmeler

4. **State Transition Mantık Hatası:** Satır 755 - Mantık hatası

### Test Önerileri

- Tüm state transition'ları test edilmeli
- Authorization komutu tüm state'lerde test edilmeli
- Current set komutu tüm state'lerde test edilmeli
- State machine logic test edilmeli

---

## 📞 İletişim

Bu rapor ESP32 firmware geliştiricisine sunulmak üzere hazırlanmıştır. Sorular veya açıklamalar için RPi geliştirme ekibi ile iletişime geçilebilir.

---

**Rapor Tarihi:** 2025-12-10 00:35:00  
**Hazırlayan:** RPi Geliştirme Ekibi  
**Durum:** ESP32 Firmware Geliştiricisine Sunulmak Üzere Hazır

