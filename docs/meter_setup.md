# ABB Meter RS485 Kurulumu ve Yapılandırması

**Oluşturulma Tarihi:** 2025-12-09 02:50:00
**Son Güncelleme:** 2025-12-09 02:50:00
**Version:** 1.0.0

---

## 🔌 Donanım Bağlantıları

### RS485 Çevirici (MAX13487) Bağlantıları

**Raspberry Pi GPIO Pinleri:**
- **GPIO 12 (Pin 32)** → UART5_TXD (ALT3) → MAX13487 Pin 4 (DI) - TX
- **GPIO 13 (Pin 33)** → UART5_RXD (ALT3) ← MAX13487 Pin 1 (RO) - RX
- **GND** → MAX13487 GND

**Pin Mapping:**
| Pin No | BCM GPIO | Fonksiyon | ALT Fonksiyon |
|--------|----------|-----------|---------------|
| 32 | GPIO12 | PWM0 | ALT3 → UART5_TXD ✔ |
| 33 | GPIO13 | PWM1 | ALT3 → UART5_RXD ✔ |

**MAX13487 → ABB Meter:**
- **MAX13487 Pin 6 (A)** → ABB Meter A
- **MAX13487 Pin 7 (B)** → ABB Meter B
- **GND** → ABB Meter GND

**NOT:** TX-RX bağlantıları doğrulanmalı. Eğer veri okunamazsa ters çevrilmeli.

---

## ⚙️ Raspberry Pi Yapılandırması

### 1. UART5'i Etkinleştirme

Raspberry Pi'de GPIO 12 ve GPIO 13'i UART5 olarak kullanmak için:

```bash
sudo nano /boot/firmware/config.txt
```

Dosyanın sonuna şu satırı ekleyin:

```
dtoverlay=uart5,txd5_pin=12,rxd5_pin=13
```

**NOT:** GPIO12 ve GPIO13 varsayılan olarak UART5'e map edilmiş olabilir, ancak açıkça belirtmek daha iyidir.

**ÖNEMLİ:** Debian 13 (Trixie) için config dosyası `/boot/firmware/config.txt` konumundadır.

### 2. Sistem Yeniden Başlatma

Yapılandırma değişikliklerinin etkili olması için:

```bash
sudo reboot
```

### 3. UART5 Cihaz Dosyasını Kontrol Etme

Reboot sonrası UART5 `/dev/ttyAMA4` olarak görünmelidir:

```bash
ls -la /dev/ttyAMA*
```

Beklenen çıktı:
```
crw-rw---- 1 root dialout 204, 68 Dec  9 02:50 /dev/ttyAMA4
```

### 4. Kullanıcı İzinleri

`dialout` grubuna eklenmek için:

```bash
sudo usermod -aG dialout $USER
```

Yeni oturum açmak veya:
```bash
newgrp dialout
```

---

## 📡 Modbus RTU Protokol Bilgileri

### ABB Meter Model Bilgileri

**Model:** ABB B23 112-100
**Özellikler:**
- **Voltaj:** 3x220/380V veya 3x240/415V
- **Akım Aralığı:** 0.25-5(65)A
- **Frekans:** 50 or 60 Hz
- **Doğruluk Sınıfı:** kWh Cl. B (1)
- **Impulse Rate:** 1000 imp/kW

**NOT:** Register adresleri ve protokol detayları AC istasyonu açıldığında meter dokümantasyonundan alınacak.

### ABB Meter Ayarları

**Genel Modbus RTU Ayarları:**
- **Baudrate:** 9600 veya 19200 (meter modeline göre - AC istasyonu açıldığında kontrol edilecek)
- **Parity:** EVEN (çoğu ABB meter)
- **Data Bits:** 8
- **Stop Bits:** 1
- **Slave ID:** 1 (meter yapılandırmasına göre değişebilir - AC istasyonu açıldığında kontrol edilecek)

### Register Adresleri

**ÖNEMLİ:** Gerçek register adresleri ABB meter modeline ve dokümantasyonuna göre değişir.
`meter/read_meter.py` dosyasındaki `ABB_REGISTERS` dictionary'si örnek değerler içerir.

**Örnek Register Adresleri (ABB meter'a göre güncellenmeli):**
- Voltaj (L1, L2, L3): 0x0000-0x0002
- Akım (L1, L2, L3): 0x0003-0x0005
- Aktif Güç: 0x0006
- Reaktif Güç: 0x0007
- Görünür Güç: 0x0008
- Aktif Enerji: 0x0009
- Reaktif Enerji: 0x000A
- Frekans: 0x000B

---

## 🧪 Test ve Doğrulama

### 1. UART5 Bağlantı Testi

```bash
# UART5'in mevcut olduğunu kontrol et
ls -la /dev/ttyAMA4

# Serial port bilgilerini kontrol et
dmesg | grep ttyAMA4
```

### 2. Meter Okuma Testi

```bash
cd /home/basar/charger
source env/bin/activate
python3 meter/read_meter.py
```

**Beklenen Çıktı:**
```
ABB Meter RS485 Test
==================================================

1. Bağlantı testi: /dev/ttyAMA4
✅ Meter bağlantısı başarılı!

2. Meter verilerini okuma...
✅ Meter verileri okundu:
{
  "timestamp": "2025-12-09T02:50:00",
  "slave_id": 1,
  "device": "/dev/ttyAMA4",
  "voltage_l1": 230.5,
  "voltage_l2": 231.2,
  ...
}
```

### 3. Manuel Serial Port Testi

```bash
# Serial port'u dinle (hex dump)
sudo cat /dev/ttyAMA4 | hexdump -C

# Veya minicom ile
sudo minicom -D /dev/ttyAMA4 -b 9600
```

---

## 🔍 Araştırma Bulguları (2025-12-09)

### Önemli Tespitler

1. **GPIO Pin Fonksiyonu:**
   - GPIO12 ve GPIO13 pinlerinin **ALT3** fonksiyonunda olması gerekiyor
   - Şu anki durum: Pinler "alt4" görünüyor ve "UNCLAIMED" durumunda
   - Bu durum UART5'in tam olarak aktif olmadığını gösterebilir

2. **RS485 Sonlandırma Dirençleri:**
   - RS485 hattının her iki ucunda **120Ω** sonlandırma dirençleri kullanılmalı
   - Bu dirençler sinyal yansımalarını önler ve daha kararlı iletişim sağlar
   - Özellikle uzun mesafelerde kritik öneme sahip

3. **MAX13487 DE/RE Kontrol Pinleri:**
   - MAX13487 çevirici DE (Driver Enable) ve RE (Receiver Enable) pinleri var
   - Bu pinler RTS sinyali ile kontrol edilmeli
   - RTS=HIGH → TX modu (veri gönderme)
   - RTS=LOW → RX modu (veri alma)
   - RTS sinyalinin veri paketleriyle senkronize olması kritik

4. **RTS Sinyali Senkronizasyonu:**
   - Modbus RTU protokolünde RTS sinyalinin doğru zamanlaması çok önemli
   - RTS HIGH → Veri gönder → RTS LOW → Veri bekle
   - RTS geçişleri arasında kısa bekleme süreleri gerekebilir (1-5ms)

5. **Topraklama ve Parazit:**
   - RS485 iletişiminde cihazlar arasında ortak bir toprak hattı olmalı
   - Topraklama eksikliği veya parazitler iletişim sorunlarına yol açabilir
   - MAX13487 ve meter arasında GND bağlantısı kontrol edilmeli

6. **ABB Meter B23 112-100:**
   - Spesifik Modbus RTU dokümantasyonu bulunamadı
   - Meter üzerindeki ayarlar veya dokümantasyon kontrol edilmeli
   - Genellikle ABB meter'lar 9600 baudrate, EVEN parity kullanır
   - Slave ID genellikle 1-247 aralığında (çoğunlukla 1)

### Önerilen Çözümler

1. **GPIO Pin Fonksiyonunu Düzelt:**
   - Pinlerin ALT3 fonksiyonuna geçmesi için config.txt'yi kontrol et
   - Alternatif olarak UART0 (GPIO14/15) kullanılabilir

2. **RS485 Sonlandırma Dirençleri:**
   - Hattın her iki ucuna 120Ω direnç ekle
   - Özellikle meter ve MAX13487 arasında

3. **RTS Kontrolünü İyileştir:**
   - RTS geçişlerinde yeterli bekleme süreleri kullan
   - Veri gönderme/alma arasında net ayrım yap

4. **Alternatif Test:**
   - Meter'i başka bir RS485 cihazla test et
   - MAX13487'i başka bir UART ile test et
   - Bu şekilde sorunun kaynağını izole edebiliriz

---

## 🔧 Sorun Giderme

### Sorun 1: `/dev/ttyAMA4` görünmüyor

**Çözüm:**
1. `/boot/firmware/config.txt` dosyasında `dtoverlay=uart5` olduğundan emin olun
2. Sistem reboot edildi mi kontrol edin
3. `dmesg | grep uart5` ile kernel mesajlarını kontrol edin

### Sorun 2: Permission denied hatası

**Çözüm:**
```bash
sudo usermod -aG dialout $USER
newgrp dialout
```

### Sorun 3: Veri okunamıyor

**Kontrol Listesi:**
- ✅ UART5 aktif mi? (`dtoverlay=uart5`) → `/dev/ttyAMA5` mevcut
- ✅ Cihaz dosyası mevcut mu? (`/dev/ttyAMA5`) → Mevcut
- ✅ RS485 bağlantıları doğru mu? (TX-RX çapraz kontrol) → **TEST EDİLMELİ**
- ✅ Baudrate doğru mu? (9600, 19200, 4800) → **TEST EDİLDİ, HİÇBİRİNDE ÇALIŞMADI**
- ✅ Parity doğru mu? (EVEN) → **EVEN kullanılıyor, NO/NONE denemeli**
- ✅ Slave ID doğru mu? (meter yapılandırmasına göre) → **1, 2, 3, 247 test edildi**
- ✅ Register adresleri doğru mu? (ABB meter dokümantasyonu) → **0x0000 test edildi**
- ✅ RTS kontrolü aktif mi? (MAX13487 için) → **Eklendi**
- ✅ Meter açık ve çalışıyor mu? → **KONTROL EDİLMELİ**
- ✅ MAX13487 çevirici doğru çalışıyor mu? → **KONTROL EDİLMELİ**

**Test Sonuçları (2025-12-09):**
- Tüm baudrate kombinasyonları test edildi: ❌ Response yok
- Tüm slave ID kombinasyonları test edildi: ❌ Response yok
- RTS kontrolü eklendi: ✅ Kod güncellendi
- `/dev/ttyAMA5` aktif: ✅ Mevcut ve erişilebilir

**Sonraki Adımlar:**
1. Meter'in açık ve çalışır durumda olduğunu doğrula
2. RS485 TX-RX bağlantılarını ters çevir ve tekrar test et
3. Parity ayarını NO/NONE olarak değiştir ve test et
4. MAX13487 çeviricinin doğru çalıştığını kontrol et (LED'ler, voltaj seviyeleri)
5. GPIO12/13 pinlerinin fiziksel bağlantılarını kontrol et
6. Meter dokümantasyonundan gerçek Modbus ayarlarını al

### Sorun 4: TX-RX Bağlantısı Belirsiz

**Test:**
1. TX ve RX bağlantılarını ters çevirin
2. Tekrar test edin
3. Hangi bağlantıda veri alınıyorsa o doğrudur

---

## 📝 Kod Kullanımı

### Python'da Kullanım

```python
from meter.read_meter import ABBMeterReader

# Meter reader oluştur
reader = ABBMeterReader(
    device="/dev/ttyAMA4",
    baudrate=9600,
    slave_id=1,
    timeout=1.0
)

# Bağlan
if reader.connect():
    # Meter verilerini oku
    data = reader.read_meter_data()
    if data:
        print(f"Voltaj L1: {data['voltage_l1']}V")
        print(f"Akım L1: {data['current_l1']}A")
        print(f"Aktif Güç: {data['power_active_w']}W")
        print(f"Aktif Enerji: {data['energy_active_kwh']}kWh")

    # Bağlantıyı kapat
    reader.disconnect()
```

### API Entegrasyonu

`api/main.py` dosyasına meter endpoint'leri eklenebilir:

```python
from meter.read_meter import get_meter_reader

@app.get("/api/meter/status")
async def get_meter_status():
    reader = get_meter_reader()
    data = reader.read_meter_data()
    return APIResponse(success=True, data=data)
```

---

## 📚 Kaynaklar ve Referanslar

- **Modbus RTU Protokol:** Modbus.org dokümantasyonu
- **ABB Meter Dokümantasyonu:** Meter modeline özel dokümantasyon
- **Raspberry Pi UART:** Raspberry Pi Foundation dokümantasyonu
- **MAX13487 Datasheet:** RS485 çevirici teknik dokümantasyonu

---

## ✅ Kurulum Kontrol Listesi

- [ ] `/boot/firmware/config.txt` dosyasına `dtoverlay=uart5` eklendi
- [ ] Sistem reboot edildi
- [ ] `/dev/ttyAMA4` cihaz dosyası mevcut
- [ ] Kullanıcı `dialout` grubuna eklendi
- [ ] RS485 bağlantıları doğrulandı
- [ ] Meter baudrate ve slave ID ayarlandı
- [ ] Register adresleri ABB meter dokümantasyonundan alındı
- [ ] Test okuma başarılı

---

**Son Güncelleme:** 2025-12-09 02:50:00
**Sonraki Adım:** Meter dokümantasyonundan gerçek register adreslerini al ve `meter/read_meter.py` dosyasını güncelle

