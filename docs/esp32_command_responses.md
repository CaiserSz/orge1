# ESP32 Komut Yanıtları (Command Responses)

**Oluşturulma:** 2025-12-10 18:45:00
**Son Güncelleme:** 2025-12-10 18:45:00
**Versiyon:** 1.0.0

## Özet

ESP32 firmware'ı (`Commercial_08122025.ino`) komutlara karşı ACK (acknowledgment) mesajları gönderiyor, ancak şu anda RPi bridge kodu (`esp32/bridge.py`) bu ACK mesajlarını okumuyor.

## ESP32'den Gönderilen ACK Mesajları

ESP32 firmware'ı komutları aldıktan sonra aşağıdaki ACK mesajlarını gönderiyor:

### 1. Status Request (`KOMUT_READ_STAT` - 0x00)
```
<ACK;CMD=READSTAT;STATUS=OK;>
```
- **Komut:** `41 00 2C 00 10`
- **Yanıt:** Status mesajı gönderilir (`sendStat()`) ve ACK döner
- **Durum:** ✅ ESP32 gönderiyor, ❌ Bridge okumuyor

### 2. Authorization (`KOMUT_AUTH` - 0x01)
```
<ACK;CMD=AUTH;STATUS=OK;>           // Başarılı
<ACK;CMD=AUTH;STATUS=CLEARED;>       // Temizlendi
<ACK;CMD=AUTH;STATUS=NOT CLEARED;>   // Temizlenemedi
```
- **Komut:** `41 01 2C 01 10`
- **Yanıt:** Komut durumuna göre farklı ACK mesajları
- **Durum:** ✅ ESP32 gönderiyor, ❌ Bridge okumuyor

### 3. Current Set (`KOMUT_SET_MAX_AMP` - 0x02)
```
<ACK;CMD=SETMAXAMP;STATUS=OK;>       // Başarılı (6-32A aralığında)
<ACK;CMD=SETMAXAMP;STATUS=ERR;>      // Hata (aralık dışı veya şarj aktifken)
```
- **Komut:** `41 02 2C [AMPERAGE] 10`
- **Yanıt:** Başarı/hata durumuna göre ACK
- **Durum:** ✅ ESP32 gönderiyor, ❌ Bridge okumuyor

### 4. Charge Stop (`KOMUT_STOP` - 0x04)
```
<ACK;CMD=STOP;STATUS=OK;>            // (GPIO UART için, şu anda devre dışı)
```
- **Komut:** `41 04 2C 07 10`
- **Yanıt:** GPIO UART için tanımlı ama şu anda USB Serial kullanılıyor
- **Durum:** ⚠️ GPIO UART'ta tanımlı ama aktif değil, USB Serial'de ACK yok

### 5. Lock/Unlock (`KOMUT_KILIT` - 0x03)
```
<ACK;CMD=UNLOCK;STATUS=OK;>          // Unlock başarılı
<ACK;CMD=LOCK;STATUS=OK;>            // Lock başarılı
```
- **Komut:** `41 03 2C [VAL] 10`
- **Yanıt:** Lock/unlock durumuna göre ACK
- **Durum:** ✅ ESP32 gönderiyor, ❌ Bridge okumuyor (bu komutu kullanmıyoruz)

### 6. Unknown Command
```
<ACK;CMD=UNKNOWN;STATUS=ERR;>
```
- **Yanıt:** Bilinmeyen komut için hata ACK'ı
- **Durum:** ✅ ESP32 gönderiyor, ❌ Bridge okumuyor

## Mevcut Durum

### Bridge Kodu (`esp32/bridge.py`)

Bridge kodu şu anda **sadece status mesajlarını** (`<STAT;...>`) okuyor:

```python
def _read_status_messages(self):
    # ...
    if line and "<STAT;" in line:
        status = self._parse_status_message(line)
        # ...
```

**ACK mesajları (`<ACK;...>`) okunmuyor ve parse edilmiyor.**

### Kullanılan Komutlar ve ACK Durumları

| Komut | Bridge Gönderiyor | ESP32 ACK Gönderiyor | Bridge ACK Okuyor |
|-------|------------------|---------------------|-------------------|
| Status Request | ✅ | ✅ | ❌ |
| Authorization | ✅ | ✅ | ❌ |
| Current Set | ✅ | ✅ | ❌ |
| Charge Stop | ✅ | ⚠️ (GPIO UART'ta) | ❌ |

## ACK Mesaj Formatı

Tüm ACK mesajları aşağıdaki formatta:

```
<ACK;CMD=[KOMUT_ADI];STATUS=[DURUM];[EK_BILGI];>
```

**Örnekler:**
- `<ACK;CMD=AUTH;STATUS=OK;>`
- `<ACK;CMD=SETMAXAMP;STATUS=ERR;>`
- `<ACK;CMD=READSTAT;STATUS=OK;>`

## Öneriler

### 1. ACK Mesajlarını Okuma Desteği Ekleme

Bridge koduna ACK mesajlarını okuma ve parse etme desteği eklenebilir:

```python
def _parse_ack_message(self, message: str) -> Optional[Dict[str, Any]]:
    """ACK mesajını parse et"""
    pattern = r"<ACK;(.*?)>"
    match = re.search(pattern, message)
    if not match:
        return None

    ack_data = {}
    fields = match.group(1).split(";")

    for field in fields:
        field = field.strip()
        if not field:
            continue
        if "=" in field:
            key, value = field.split("=", 1)
            ack_data[key.strip()] = value.strip()

    return ack_data
```

### 2. Komut Gönderme Sonrası ACK Bekleme

Komut gönderildikten sonra ACK mesajını bekleyip doğrulama yapılabilir:

```python
def send_authorization(self, timeout: float = 1.0) -> bool:
    """Authorization komutu gönder ve ACK bekle"""
    cmd = self.protocol_data.get("commands", {}).get("authorization", {})
    byte_array = cmd.get("byte_array", [65, 1, 44, 1, 16])

    if not self._send_command_bytes(byte_array):
        return False

    # ACK mesajını bekle
    start_time = time.time()
    while time.time() - start_time < timeout:
        # Serial porttan oku ve ACK ara
        if self.serial_connection.in_waiting > 0:
            line = self.serial_connection.readline().decode("utf-8", errors="ignore").strip()
            if "<ACK;CMD=AUTH;" in line:
                ack = self._parse_ack_message(line)
                if ack and ack.get("STATUS") == "OK":
                    return True
        time.sleep(0.01)

    return False  # Timeout
```

### 3. Protocol.json'a ACK Tanımları Ekleme

`protocol.json` dosyasına ACK mesaj formatları eklenebilir:

```json
{
  "ack_messages": {
    "format": "<ACK;CMD=[KOMUT];STATUS=[DURUM];[EK_BILGI];>",
    "commands": {
      "AUTH": {
        "success": "<ACK;CMD=AUTH;STATUS=OK;>",
        "cleared": "<ACK;CMD=AUTH;STATUS=CLEARED;>",
        "error": "<ACK;CMD=AUTH;STATUS=NOT CLEARED;>"
      },
      "SETMAXAMP": {
        "success": "<ACK;CMD=SETMAXAMP;STATUS=OK;>",
        "error": "<ACK;CMD=SETMAXAMP;STATUS=ERR;>"
      }
    }
  }
}
```

## Sonuç

- ✅ **ESP32 firmware ACK mesajları gönderiyor**
- ✅ **Bridge kodu ACK mesajlarını okuma desteği eklendi (2025-12-10)**
- ⚠️ **Charge Stop için ACK mesajı GPIO UART'ta tanımlı ama aktif değil**

## Implementasyon Durumu (2025-12-10)

### ✅ Tamamlanan Özellikler

1. **ACK Mesaj Parse Fonksiyonu**
   - `_parse_ack_message()` fonksiyonu eklendi
   - `<ACK;CMD=...;STATUS=...;>` formatındaki mesajları parse ediyor

2. **ACK Bekleme Fonksiyonu**
   - `_wait_for_ack()` fonksiyonu eklendi
   - Belirli bir komut için ACK mesajını bekliyor
   - Timeout desteği var (varsayılan: 1.0 saniye)

3. **Komut Fonksiyonları Güncellendi**
   - `send_authorization()`: `wait_for_ack=True` (varsayılan), ACK bekliyor
   - `send_current_set()`: `wait_for_ack=True` (varsayılan), ACK bekliyor
   - `send_charge_stop()`: `wait_for_ack=False` (varsayılan), ACK beklemiyor (çünkü ACK yok)

4. **Status Mesaj Okuma Güncellendi**
   - `_read_status_messages()` fonksiyonu ACK mesajlarını da okuyor ve logluyor

5. **Protocol.json Güncellendi**
   - `ack_messages` bölümü eklendi
   - Tüm ACK mesaj formatları tanımlandı

6. **Testler Eklendi**
   - `tests/test_ack_messages.py`: 20 test
   - ACK parse, wait, ve komut gönderme testleri

### Kullanım

```python
# ACK bekleyerek komut gönder (varsayılan)
bridge.send_authorization()  # ACK bekler, STATUS=OK veya CLEARED ise True döner
bridge.send_current_set(16)  # ACK bekler, STATUS=OK ise True döner

# ACK beklemeden komut gönder:
bridge.send_authorization(wait_for_ack=False)
bridge.send_current_set(16, wait_for_ack=False)

# Özel timeout ile:
bridge.send_authorization(wait_for_ack=True, timeout=2.0)
```

### Test Sonuçları

```
======================== 20 passed, 4 warnings in 1.51s ========================
```

Tüm ACK mesaj testleri başarıyla geçti!

