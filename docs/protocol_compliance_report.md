# Protokol Uyum Raporu

**Tarih:** 2025-12-10
**Durum:** ✅ PROTOKOLE UYUMLU

---

## Protokol Spesifikasyonu

**Protokol:** ESP32-RPi Binary Hex Protocol v1.0
**Format:** `41 [KOMUT] 2C [DEĞER] 10`
**Packet Size:** 5 byte
**Baudrate:** 115200

### Protokol Sabitleri
- **Header:** `0x41` (65)
- **Separator:** `0x2C` (44)
- **Footer:** `0x10` (16)

---

## Komut Kontrolü

### ✅ Status Komutu
- **Protokol:** `41 00 2C 00 10` → `[65, 0, 44, 0, 16]`
- **Kod:** `[65, 0, 44, 0, 16]`
- **Durum:** ✅ UYUMLU

### ✅ Authorization Komutu
- **Protokol:** `41 01 2C 01 10` → `[65, 1, 44, 1, 16]`
- **Kod:** `[65, 1, 44, 1, 16]`
- **Durum:** ✅ UYUMLU

### ✅ Charge Stop Komutu
- **Protokol:** `41 04 2C 07 10` → `[65, 4, 44, 7, 16]`
- **Kod:** `[65, 4, 44, 7, 16]`
- **Durum:** ✅ UYUMLU

### ✅ Current Set Komutu
- **Protokol Formatı:** `41 02 2C [DEĞER] 10` → `[0x41, 0x02, 0x2C, amperage, 0x10]`
- **Kod:** `[0x41, 0x02, 0x2C, amperage, 0x10]`
- **Durum:** ✅ UYUMLU
- **Örnek (16A):** `[65, 2, 44, 16, 16]` ✅

---

## Protokol Kuralları Kontrolü

### ✅ Kural 1: "only_defined_commands"
**Kural:** "Başka komut RPi'den ESP32'ye gitmez."

**Kontrol:**
- ✅ Sadece tanımlı komutlar gönderiliyor:
  - `status` (0x00)
  - `authorization` (0x01)
  - `current_set` (0x02)
  - `charge_stop` (0x04)
- ✅ Tanımsız komut gönderilmiyor
- ✅ Protokol dışı komut yok

**Durum:** ✅ UYUMLU

### ✅ Kural 2: "current_set_range"
**Kural:** "Akım set değeri 6-32 amper aralığında herhangi bir tam sayı olabilir. Değer doğrudan amper cinsinden hex formatında gönderilir."

**Kontrol:**
- ✅ Kodda aralık kontrolü var: `if not (6 <= amperage <= 32)`
- ✅ Değer doğrudan amper cinsinden gönderiliyor (hex dönüşümü yok)
- ✅ Örnek: 16A → `[0x41, 0x02, 0x2C, 16, 0x10]` (16 decimal olarak gönderiliyor)

**Durum:** ✅ UYUMLU

### ✅ Kural 3: "current_set_only_before_charging"
**Kural:** "Akım set komutları sadece aktif şarj başlamadan gönderilebilir. Şarj esnasında akım değiştirilemez (güvenlik nedeniyle)."

**Kontrol:**
- ✅ `CurrentService.set_current()` metodunda state kontrolü var
- ✅ `CHARGING` (state=5) durumunda akım ayarlanamaz
- ✅ Hata mesajı: "Akım ayarlanamaz (State: CHARGING). Şarj aktifken akım değiştirilemez."

**Durum:** ✅ UYUMLU

---

## Protokol Dosyası Yükleme

### ✅ Protocol.json Yükleme
- ✅ Bridge `__init__` metodunda `_load_protocol()` çağrılıyor
- ✅ `protocol.json` dosyası `esp32/` klasöründen yükleniyor
- ✅ Komutlar protokol dosyasından okunuyor (fallback değerlerle)

**Durum:** ✅ UYUMLU

---

## Byte Array Formatı

### ✅ Komut Gönderme Formatı
- ✅ Tüm komutlar 5 byte'lık array olarak gönderiliyor
- ✅ `_send_command_bytes()` metodu uzunluk kontrolü yapıyor
- ✅ Format: `[HEADER, KOMUT, SEPARATOR, DEĞER, FOOTER]`

**Durum:** ✅ UYUMLU

---

## Status Mesajı Parsing

### ✅ Status Mesajı Formatı
- **Protokol Formatı:** `<STAT;ID=X;CP=X;CPV=X;PP=X;PPV=X;RL=X;LOCK=X;MOTOR=X;PWM=X;MAX=X;CABLE=X;AUTH=X;STATE=X;PB=X;STOP=X;>`
- ✅ `_parse_status_message()` metodu regex ile parse ediyor
- ✅ Tüm alanlar doğru şekilde parse ediliyor

**Durum:** ✅ UYUMLU

---

## Sonuç

### ✅ TÜM PROTOKOL KURALLARINA UYUMLU

**Özet:**
1. ✅ Protokol formatı doğru (`41 [KOMUT] 2C [DEĞER] 10`)
2. ✅ Tüm komutlar protokole uygun
3. ✅ Protokol kurallarına uyuluyor
4. ✅ Sadece tanımlı komutlar gönderiliyor
5. ✅ Akım aralığı kontrolü yapılıyor
6. ✅ Şarj esnasında akım değiştirilemez kontrolü var
7. ✅ Status mesajı doğru parse ediliyor

**Durum:** ✅ **PROTOKOLE TAM UYUMLU**

---

**Not:** Protokol dosyası (`esp32/protocol.json`) tek kaynak olarak kullanılıyor ve tüm komutlar bu dosyadan yükleniyor. Hard-coded değerler sadece fallback olarak kullanılıyor.

