# State Mantık Analizi ve Hatalar

**Tarih:** 2025-12-09 02:15:00

---

## 🔍 Tespit Edilen Mantık Hataları

### 1. Start Charge Endpoint - YANLIŞ STATE KONTROLÜ

**Mevcut Kod:**
```python
if state >= 2:  # State >= 2 aktif şarj anlamına gelir
    raise HTTPException(...)
```

**Problem:**
- STATE=2 (CABLE_DETECT) durumunda şarj başlatılamıyor ❌
- STATE=3 (EV_CONNECTED) durumunda şarj başlatılamıyor ❌
- STATE=4 (SARJA_HAZIR) durumunda şarj başlatılamıyor ❌

**ESP32 Kod Analizi:**
```cpp
case KOMUT_AUTH: // 1
  if (val == 1) {
    if (sarjStatus!=SARJ_STAT_IDLE){  // STATE != 1 ise izin ver
      authEnabled = true;
      ...
    }
  }
```

**Doğru Mantık:**
ESP32 koduna göre, authorization komutu STATE != 1 durumlarında (yani STATE=2,3,4,5,6,7,8) gönderilebilir. Ancak mantıklı olan:
- ✅ STATE=1 (IDLE): Şarj başlatılabilir
- ✅ STATE=2 (CABLE_DETECT): Şarj başlatılabilir (kablo takıldı)
- ✅ STATE=3 (EV_CONNECTED): Şarj başlatılabilir (araç bağlı)
- ✅ STATE=4 (SARJA_HAZIR): Şarj başlatılabilir (hazır)
- ❌ STATE=5 (SARJ_BASLADI): Şarj zaten başladı
- ❌ STATE=6 (SARJ_DURAKLATILDI): Şarj duraklatıldı
- ❌ STATE=7 (SARJ_BITIR): Şarj bitirildi
- ❌ STATE=8 (FAULT_HARD): Hata durumu

**Düzeltme:**
```python
# Şarj başlatılabilir durumlar: STATE=1,2,3,4
# Şarj başlatılamaz durumlar: STATE=5,6,7,8
if state >= 5:  # STATE >= 5 aktif şarj veya hata durumu
    raise HTTPException(...)
```

---

### 2. Set Current Endpoint - YANLIŞ STATE KONTROLÜ

**Mevcut Kod:**
```python
if state >= 2:  # State >= 2 aktif şarj anlamına gelir
    raise HTTPException(...)
```

**Problem:**
- STATE=2 (CABLE_DETECT) durumunda akım ayarlanamıyor ❌
- STATE=3 (EV_CONNECTED) durumunda akım ayarlanamıyor ❌
- STATE=4 (SARJA_HAZIR) durumunda akım ayarlanamıyor ❌

**ESP32 Kod Analizi:**
```cpp
case KOMUT_SET_MAX_AMP: //2
  if (sarjStatus=SARJ_STAT_IDLE){  // ⚠️ BUG: Assignment operator kullanılmış!
    if (val >= 6 && val <= DEFAULT_MAX_CURRENT) {
      maxCurrent = val;
      ...
    }
  }
```

**ESP32 Kodunda Bug:**
ESP32 kodunda `if (sarjStatus=SARJ_STAT_IDLE)` satırında assignment operator (`=`) kullanılmış, comparison operator (`==`) olmalı. Bu bir bug!

**Doğru Mantık:**
Güvenlik açısından, akım ayarlama sadece şarj başlamadan önce yapılabilir olmalı:
- ✅ STATE=1 (IDLE): Akım ayarlanabilir
- ✅ STATE=2 (CABLE_DETECT): Akım ayarlanabilir (şarj başlamadı)
- ✅ STATE=3 (EV_CONNECTED): Akım ayarlanabilir (şarj başlamadı)
- ✅ STATE=4 (SARJA_HAZIR): Akım ayarlanabilir (şarj başlamadı)
- ❌ STATE=5 (SARJ_BASLADI): Akım ayarlanamaz (şarj aktif)
- ❌ STATE=6 (SARJ_DURAKLATILDI): Akım ayarlanamaz (şarj duraklatıldı)
- ❌ STATE=7 (SARJ_BITIR): Akım ayarlanamaz
- ❌ STATE=8 (FAULT_HARD): Akım ayarlanamaz

**Düzeltme:**
```python
# Akım ayarlanabilir durumlar: STATE=1,2,3,4
# Akım ayarlanamaz durumlar: STATE=5,6,7,8
if state >= 5:  # STATE >= 5 aktif şarj veya hata durumu
    raise HTTPException(...)
```

---

## 📊 State Değerleri Tablosu

| STATE | Adı | Şarj Başlatılabilir? | Akım Ayarlanabilir? | Açıklama |
|-------|-----|---------------------|---------------------|----------|
| 1 | IDLE | ✅ | ✅ | Boşta |
| 2 | CABLE_DETECT | ✅ | ✅ | Kablo algılandı |
| 3 | EV_CONNECTED | ✅ | ✅ | Araç bağlı |
| 4 | SARJA_HAZIR | ✅ | ✅ | Şarja hazır |
| 5 | SARJ_BASLADI | ❌ | ❌ | Şarj başladı |
| 6 | SARJ_DURAKLATILDI | ❌ | ❌ | Şarj duraklatıldı |
| 7 | SARJ_BITIR | ❌ | ❌ | Şarj bitirildi |
| 8 | FAULT_HARD | ❌ | ❌ | Hata |

---

## ✅ Düzeltme Önerileri

### API Kod Düzeltmesi

**Start Charge:**
```python
# Şarj başlatılabilir durumlar: STATE=1,2,3,4
# Şarj başlatılamaz durumlar: STATE=5,6,7,8
if state >= 5:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Şarj başlatılamaz (State: {state}). Şarj zaten aktif veya hata durumunda."
    )
```

**Set Current:**
```python
# Akım ayarlanabilir durumlar: STATE=1,2,3,4
# Akım ayarlanamaz durumlar: STATE=5,6,7,8
if state >= 5:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Şarj aktifken akım değiştirilemez (State: {state})"
    )
```

---

## 🐛 ESP32 Kodunda Tespit Edilen Bug

**Satır 974:**
```cpp
if (sarjStatus=SARJ_STAT_IDLE){  // ⚠️ YANLIŞ: Assignment operator
```

**Düzeltme:**
```cpp
if (sarjStatus==SARJ_STAT_IDLE){  // ✅ DOĞRU: Comparison operator
```

Bu bug nedeniyle ESP32'de akım ayarlama her zaman çalışıyor olabilir (her zaman true döner).

---

## 📝 Test Sonuçları

Test çalıştırıldığında:
- ✅ STATE=1: Her iki endpoint de çalışıyor
- ❌ STATE=2: Her iki endpoint de reddediliyor (YANLIŞ)
- ❌ STATE=3: Her iki endpoint de reddediliyor (YANLIŞ)
- ❌ STATE=4: Her iki endpoint de reddediliyor (YANLIŞ)
- ✅ STATE=5: Her iki endpoint de reddediliyor (DOĞRU)

---

**Son Güncelleme:** 2025-12-09 02:15:00

