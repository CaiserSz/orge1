# Otomatik Şarj Başlatma Analizi

**Tarih:** 2025-12-10  
**Sorun:** Araç bağlandığında otomatik olarak şarj başlıyor

---

## Log Analizi

Loglardan görülen sıralama:
1. `13:04:16` - **EV_CONNECTED** event'i (CABLE_DETECT → EV_CONNECTED)
2. `13:05:17` - **STATE_CHANGED** event'i (IDLE → EV_CONNECTED)
3. `13:05:24` - **charge_start** event'i (Manuel API çağrısı)
4. `13:05:32` - **STATE_CHANGED** event'i (IDLE → CHARGING) - **OTOMATIK BAŞLADI**

---

## ESP32 Firmware Davranışı

ESP32 firmware kodunda (`Commercial_08122025.ino`):

### EV_CONNECTED State (Satır 687-701)
```cpp
case EV_CONNECTED: //3
    ledIslemleri(6);//MAVİ
    PPBAK ();
    if(onayStatus==ONAY_STAT_IZIN_VERILDI){
      sarjStatus=SARJA_HAZIR;  // ← Authorization varsa READY state'ine geç
    }
    // ...
break;
```

### SARJA_HAZIR State (Satır 703-721)
```cpp
case SARJA_HAZIR: //4
   if(LOCKFLAG==0) {
    lock(LOCK_PULSE_MS);
    delay (50);
    LOCKFLAG=1;
    relayDriver(1);  // ← Relay açılıyor
    RelayFlag=1;
    // ...
  }
   // ...
   if(cpStatus==CP_STAT_CHARGING) sarjStatus=SARJ_STAT_SARJ_BASLADI;  // ← Otomatik şarj başlıyor
break;
```

### Authorization Komutu (Satır 954-971)
```cpp
case KOMUT_AUTH: // 1
  if (val == 1) {
    if (sarjStatus!=SARJ_STAT_IDLE){
    authEnabled = true;
    onayStatus = ONAY_STAT_IZIN_VERILDI;  // ← Authorization veriliyor
    // ...
    }
  }
break;
```

---

## Sorunun Kök Nedeni

**ESP32 firmware davranışı:**
1. Araç bağlandığında → `EV_CONNECTED` state'ine geçiyor
2. Eğer `onayStatus==ONAY_STAT_IZIN_VERILDI` ise → `SARJA_HAZIR` state'ine geçiyor
3. `SARJA_HAZIR` state'inde relay açılıyor ve araç şarj başlatıyorsa → `SARJ_STAT_SARJ_BASLADI` state'ine geçiyor

**Sorun:** ESP32 firmware'de `onayStatus` değeri bir şekilde `ONAY_STAT_IZIN_VERILDI` olarak ayarlanmış olabilir. Bu durumda:
- Araç bağlandığında otomatik olarak `SARJA_HAZIR` state'ine geçiyor
- Relay açılıyor ve şarj başlıyor

---

## Olası Nedenler

1. **Önceki test'ten kalan authorization:** Daha önceki bir test'te authorization verilmiş ve temizlenmemiş olabilir
2. **RFID kart okuma:** ESP32 firmware'de RFID kart okuma mekanizması var (satır 627-640). Eğer geçerli bir kart okunmuşsa `onayStatus` otomatik olarak `ONAY_STAT_IZIN_VERILDI` olarak ayarlanıyor
3. **State persistence:** ESP32 firmware'de state değerleri EEPROM'da saklanıyor olabilir

---

## Çözüm Önerileri

### 1. Authorization Temizleme (Kısa Vadeli)
ESP32 firmware'de authorization'ı temizlemek için:
- `charge_stop` komutu gönderildiğinde ESP32 firmware `onayStatus` değerini `ONAY_STAT_BEKLENIYOR` olarak ayarlamalı
- Veya RPi tarafından explicit olarak authorization temizleme komutu gönderilmeli

### 2. State Kontrolü (Orta Vadeli)
RPi tarafında `EV_CONNECTED` event'i geldiğinde:
- `onayStatus` değerini kontrol et
- Eğer `ONAY_STAT_IZIN_VERILDI` ise, kullanıcıdan onay bekle
- Kullanıcı onayı olmadan şarj başlatma

### 3. Firmware Güncelleme (Uzun Vadeli)
ESP32 firmware'de:
- `EV_CONNECTED` state'inde otomatik authorization kontrolü kaldırılmalı
- Authorization sadece explicit API komutu ile verilmeli
- State persistence kontrol edilmeli

---

## Mevcut Durum

**RPi tarafında:** Otomatik şarj başlatma kodu yok. Tüm şarj başlatmalar manuel API çağrısı ile yapılıyor.

**ESP32 firmware tarafında:** `EV_CONNECTED` state'inde `onayStatus==ONAY_STAT_IZIN_VERILDI` kontrolü var ve bu durumda otomatik olarak `SARJA_HAZIR` state'ine geçiyor.

---

## Sonuç

Sorun ESP32 firmware davranışından kaynaklanıyor. RPi tarafında otomatik şarj başlatma kodu yok. ESP32 firmware'de `onayStatus` değeri bir şekilde `ONAY_STAT_IZIN_VERILDI` olarak ayarlanmış ve bu durumda araç bağlandığında otomatik olarak şarj başlıyor.

**Önerilen çözüm:** ESP32 firmware'de authorization temizleme mekanizması kontrol edilmeli ve `charge_stop` komutu gönderildiğinde `onayStatus` değeri temizlenmeli.

