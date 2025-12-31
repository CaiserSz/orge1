# Acrel ADL400/T317 ↔ Raspberry Pi (RPi) Meter Entegrasyonu (RS485 / Modbus RTU)

**Oluşturulma Tarihi:** 2025-12-09 02:50:00
**Son Güncelleme:** 2025-12-31 13:57:00 +03
**Version:** 1.2.0

---

## 🎯 Hızlı Özet (Acrel T317/ADL400 MID — Saha Doğrulandı)

Bu doküman, **Acrel T317/ADL400 MID** üç-faz enerji sayacının Raspberry Pi ile **RS485 / Modbus RTU** üzerinden okunması için gerekli ayarları ve proje içi entegrasyon noktalarını tek yerde toplar. (ABB B23 notları da “legacy” olarak içeride tutulur.)

- **Saha (çalışan) seri ayarları:**
  - Port: `/dev/ttyAMA5` (örnek: UART5 + MAX13487)
  - Baudrate: **9600**
  - Parity: **EVEN** (8E1)
  - Slave ID: **111**
  - Function Code: **0x03** (Holding Registers)
- **Eğer config/env kullanıyorsanız, örnek eşleme:**

```bash
METER_TYPE=acrel
METER_PORT=/dev/ttyAMA5
METER_BAUDRATE=9600
METER_SLAVE_ID=111
METER_TIMEOUT=1.0
METER_AUTO_CONNECT=true
```

- **Önemli not (Modbus RTU):** Sayaç **kendiliğinden** sürekli veri akıtmaz; iletişim **request/response**’dur. Bu nedenle `cat /dev/ttyAMA5` ile “hiç veri yok” görmeniz normal olabilir. Doğrulama için master olarak sorgu göndermek gerekir (aşağıdaki test adımlarına bakın).

## 🧩 Repo‑Bağımsız (Her RPi) Kopyala‑Çalıştır Testi

Bu bölüm **dosya yolu / repo yapısı bağımsızdır**. ORGE2 AI’nin farklı bir projede aynı sayaç ayarlarıyla neden çalışmadığını anlaması için tasarlanmıştır.

### 1) Seri portu ve cihazı doğrula

```bash
# Portları listele (USB-RS485 ve UART adayları)
ls -la /dev/serial/by-id /dev/serial0 /dev/ttyUSB* /dev/ttyAMA* /dev/ttyS* 2>/dev/null || true

# Tak-çıkar sonrası kernel loglarından port ismi yakala
dmesg | grep -iE 'tty(USB|AMA|S)' | tail -n 50
```

> İpucu: USB-RS485 adaptör ile genelde `/dev/ttyUSB0` gelir. UART ile genelde `/dev/ttyAMA*` veya `/dev/serial0` gelir.

### 2) Python bağımlılıklarını kur

```bash
python3 -m pip install --upgrade pip
python3 -m pip install pymodbus==3.6.7 pyserial==3.5
```

> Not: Farklı pymodbus sürümlerinde parametre adı `device_id` yerine `unit` olabilir. Aşağıdaki örnek pymodbus 3.x içindir.

### 3) Minimal register okuma script’i (Acrel ADL400/T317)

Aşağıdaki script’i **herhangi bir klasörde** çalıştırabilirsiniz (repo gerektirmez). Tek yapmanız gereken `PORT` ve `SLAVE_ID` değerlerini kendi ortamınıza göre set etmektir.

```python
import struct

from pymodbus.client import ModbusSerialClient


def _to_float(regs: list[int]) -> float:
    return struct.unpack(">f", struct.pack(">HH", regs[0], regs[1]))[0]


def _to_u32(regs: list[int]) -> int:
    return struct.unpack(">I", struct.pack(">HH", regs[0], regs[1]))[0]


def _read_holding(client: ModbusSerialClient, unit: int, address: int, count: int) -> list[int]:
    rr = client.read_holding_registers(address, count=count, device_id=unit)
    if rr.isError():
        raise RuntimeError(f"modbus_error: {rr}")
    return list(rr.registers)


def main() -> None:
    # SAHADA ÇALIŞAN AYARLAR (gerekiyorsa değiştirin)
    port = "/dev/ttyUSB0"  # örn: /dev/ttyUSB0 veya /dev/ttyAMA5 veya /dev/serial0
    slave_id = 111

    client = ModbusSerialClient(
        port=port,
        baudrate=9600,
        parity="E",
        stopbits=1,
        bytesize=8,
        timeout=1.0,
    )
    if not client.connect():
        raise SystemExit(f"connect_failed: {port}")

    try:
        # Voltajlar (float32, V)
        va = _to_float(_read_holding(client, slave_id, 0x0800, 2))
        vb = _to_float(_read_holding(client, slave_id, 0x0802, 2))
        vc = _to_float(_read_holding(client, slave_id, 0x0804, 2))

        # Akımlar (float32, A)
        ia = _to_float(_read_holding(client, slave_id, 0x080C, 2))
        ib = _to_float(_read_holding(client, slave_id, 0x080E, 2))
        ic = _to_float(_read_holding(client, slave_id, 0x0810, 2))

        # Güç (float32, kW)
        p_l1 = _to_float(_read_holding(client, slave_id, 0x0814, 2))
        p_l2 = _to_float(_read_holding(client, slave_id, 0x0816, 2))
        p_0818 = _to_float(_read_holding(client, slave_id, 0x0818, 2))

        # PF ve Hz (float32)
        pf_total = _to_float(_read_holding(client, slave_id, 0x0832, 2))
        freq_hz = _to_float(_read_holding(client, slave_id, 0x0834, 2))

        # Enerji (uint32, scale=0.1 kWh)
        e_total_kwh = _to_u32(_read_holding(client, slave_id, 0x0842, 2)) * 0.1
        e_import_kwh = _to_u32(_read_holding(client, slave_id, 0x084C, 2)) * 0.1
        e_export_kwh = _to_u32(_read_holding(client, slave_id, 0x0856, 2)) * 0.1

        print("OK")
        print(f"V: L1={va:.2f} L2={vb:.2f} L3={vc:.2f}")
        print(f"I: L1={ia:.3f} L2={ib:.3f} L3={ic:.3f}")
        print(f"P(kW): L1={p_l1:.3f} L2={p_l2:.3f} 0x0818={p_0818:.3f}")
        print(f"PF={pf_total:.3f} Hz={freq_hz:.2f}")
        print(f"E(kWh): total={e_total_kwh:.1f} import={e_import_kwh:.1f} export={e_export_kwh:.1f}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
```

### 4) Bu test çalışmıyorsa en sık 5 sebep

- **Slave ID yanlış:** Sahada 1 değil **111**.
- **Parity yanlış:** EVEN yerine NONE/ODD set edilmiş olabilir.
- **Port yanlış:** `/dev/ttyUSB0` vs `/dev/ttyAMA5` karışır.
- **A/B ters:** RS485 A↔B swap ile düzelebilir.
- **Port “busy”:** Başka bir proses seri portu açık tutuyor olabilir.

### ✅ Canlı Okuma Örneği (2025-12-31 13:56:56 +03)

Bu örnek çıktı, bu RPi’de çalışan `charger-api` üzerinden `GET /api/meter/reading` çağrısından alınmıştır:

```json
{
  "success": true,
  "message": "Meter okuması başarıyla alındı",
  "data": {
    "voltage_v": 223.65185546875,
    "current_a": 0.13836954534053802,
    "power_w": 28.41185801342855,
    "power_kw": 0.028411858013428548,
    "energy_kwh": 106.9,
    "frequency_hz": 50.0,
    "power_factor": 0.9424657821655273,
    "timestamp": 1767178616.0200868,
    "phase_values": {
      "voltage_v": {
        "l1": 223.65185546875,
        "l2": 217.8680419921875,
        "l3": 218.396728515625
      },
      "current_a": {
        "l1": 0.0,
        "l2": 0.13836954534053802,
        "l3": 0.0
      },
      "power_kw": {
        "l1": 0.0,
        "l2": 0.014144806191325188,
        "l3": 0.0,
        "total": 0.028411858013428548
      }
    },
    "totals": {
      "power_kw": 0.028411858013428548,
      "energy_kwh": 106.9,
      "energy_total_kwh": 106.9,
      "energy_import_kwh": 106.60000000000001,
      "energy_export_kwh": 0.30000000000000004,
      "registers": {
        "power_kw_l1": "0x0814 (float32 kW)",
        "power_kw_l2": "0x0816 (float32 kW)",
        "power_kw_total_or_l3": "0x0818 (float32 kW, sahada total/L3 değişebiliyor)",
        "energy_total_kwh": "0x0842 (uint32, scale=0.1 kWh)",
        "energy_import_kwh": "0x084C (uint32, scale=0.1 kWh)",
        "energy_export_kwh": "0x0856 (uint32, scale=0.1 kWh)",
        "pf_total": "0x0832 (float32)",
        "frequency_hz": "0x0834 (float32)"
      }
    }
  }
}
```

## 🔌 Donanım Bağlantıları

### RS485 Çevirici (MAX13487) Bağlantıları

**Raspberry Pi GPIO Pinleri:**

- **GPIO 12 (Pin 32)** → UART5_TXD (ALT3) → MAX13487 Pin 4 (DI) - TX
- **GPIO 13 (Pin 33)** → UART5_RXD (ALT3) ← MAX13487 Pin 1 (RO) - RX
- **GND** → MAX13487 GND

**Pin Mapping:**

| Pin No | BCM GPIO | Fonksiyon | ALT Fonksiyon        |
| ------ | -------- | --------- | -------------------- |
| 32     | GPIO12   | PWM0      | ALT3 → UART5_TXD ✔   |
| 33     | GPIO13   | PWM1      | ALT3 → UART5_RXD ✔   |

**MAX13487 → Meter (ABB/Acrel):**

- **MAX13487 Pin 6 (A)** → Meter A
- **MAX13487 Pin 7 (B)** → Meter B
- **GND** → Meter GND

**NOT:** RS485 A/B bağlantıları doğrulanmalı. Eğer veri okunamazsa A/B yer değişimi denenmeli.

---

## ⚙️ Raspberry Pi Yapılandırması

### 1. UART5'i Etkinleştirme

Raspberry Pi'de GPIO 12 ve GPIO 13'i UART5 olarak kullanmak için:

```bash
sudo nano /boot/firmware/config.txt
```

Dosyanın sonuna şu satırı ekleyin:

```text
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

Reboot sonrası UART5 bu sistemde `/dev/ttyAMA5` olarak görünmektedir:

```bash
ls -la /dev/ttyAMA*
```

Beklenen çıktı:

```text
crw-rw---- 1 root dialout ... /dev/ttyAMA5
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

### Acrel T317/ADL400 MID Ayarları (Aktif)

**Saha (çalışan) Modbus RTU ayarları:**

- **Port:** `/dev/ttyAMA5`
- **Baudrate:** **9600**
- **Parity:** **EVEN** (8E1)
- **Stop Bits:** 1
- **Slave ID:** **111**
- **Function Code:** **0x03 (Read Holding Registers)**

**Proje içi driver:** `api/meter/acrel.py` (`AcrelModbusMeter`)

#### Acrel Register Referansı (Projede Kullanılan)

> Not: Register semantiklerinin (total/import/export) üretici register-map dokümanı ile %100 teyidi ayrıca yapılmalıdır. Proje içinde debug kolaylığı için register referansları response içine de eklenir (`totals.registers`).

- **Voltaj (float32, V):** `0x0800`, `0x0802`, `0x0804`
- **Akım (float32, A):** `0x080C`, `0x080E`, `0x0810`
- **Güç (float32, kW):** `0x0814`, `0x0816`, `0x0818`
  - Not: `0x0818` sahada **total** veya **L3** olabildiği gözlemlendi; driver total gücü faz toplamı/V-I türetimi ile normalize eder.
- **Power factor (float32):** `0x0832`
- **Frekans (float32, Hz):** `0x0834`
- **Enerji (uint32, scale=0.1 kWh):**
  - **Total:** `0x0842`
  - **Import:** `0x084C`
  - **Export:** `0x0856`

### ABB Meter Model Bilgileri (Legacy)

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

- **Baudrate:** **2400** (sahada doğrulandı)
- **Parity:** EVEN (sahada doğrulandı)
- **Data Bits:** 8
- **Stop Bits:** 1
- **Slave ID:** 1 (sahada doğrulandı)
- **Function Code:** **0x03 (Read Holding Registers)** (sahada doğrulandı)

### Register Adresleri

**ABB:** `meter/read_meter.py` içindeki `ABB_REGISTERS` ABB B23 112-100 için sahada çalışan adresleri içerir.  
**Acrel:** `api/meter/acrel.py` içinde kullanılan register’lar yukarıda listelenmiştir.

**Kritik Register'lar (holding registers):**

- Voltaj L1/L2/L3: `0x1002`, `0x1004`, `0x1006` (2 register)
- Akım L1/L2/L3: `0x1010`, `0x1012`, `0x1014` (2 register)
- Aktif güç total: `0x102E` (2 register, signed)
- Aktif enerji import: `0x5000` (4 register, 0.01 kWh çözünürlük)

---

## 🧪 Test ve Doğrulama

### 1. UART5 Bağlantı Testi

```bash
# UART5'in mevcut olduğunu kontrol et
ls -la /dev/ttyAMA5

# Serial port bilgilerini kontrol et
dmesg | grep ttyAMA5
```

### 2. Meter Okuma Testi (Repo bağımsız öneri)

Öncelikle bu dokümanın üst kısmındaki **“Repo‑Bağımsız Kopyala‑Çalıştır Testi”** script’i ile register okumasını doğrulayın.

### 3. (Opsiyonel) HTTP Endpoint ile Okuma Testi

Eğer kendi sisteminizde meter okumasını servis eden bir HTTP endpoint varsa, benzer şekilde test edin:

```bash
curl -sS --max-time 5 http://localhost:8000/api/meter/reading
curl -sS --max-time 5 http://localhost:8000/api/meter/status
```

**Beklenen:** `success=true` ve `data.totals.energy_import_kwh` gibi alanların dolu gelmesi.

### 4. Legacy: ABB Reader Script (ABB B23 için)

```bash
python3 meter/read_meter.py
```

### 5. “Pasif Dinleme” Notu (Modbus RTU)

Modbus RTU iletişimi **request/response**’dur. Sayaç, master sorgusu olmadan “stream” etmez. Bu nedenle `cat /dev/ttyAMA5` ile veri beklemek çoğu durumda yanıltıcıdır. Doğrulama için yukarıdaki **API** veya **driver test** adımlarını kullanın.

---

## 🗂️ Tarihçe (ABB bring‑up notları — 2025-12-09)

### Önemli Tespitler

1. **GPIO Pin Fonksiyonu (o günkü gözlem):**
   - GPIO12 ve GPIO13 pinlerinin **ALT3** fonksiyonunda olması gerekiyor
   - O günkü gözlem: Pinler "alt4" görünüyor ve "UNCLAIMED" durumundaydı
   - Bu durum UART5 overlay/config'in tam aktif olmadığını gösterebilir

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

## 🔧 Sorun Giderme (Acrel ADL400/T317 — Diğer RPi’de Çalışmıyorsa)

### 0) Modbus RTU “sessiz” görünebilir (normal)

- Modbus RTU **request/response**’dur. Sayaç, master sorgusu olmadan “push” etmez.
- Bu yüzden “dinleyerek” (`cat`) veri beklemek yerine **register okuma** ile test edin.

### 1) Sahada çalışan ayarlar birebir mi?

```bash
# Eğer config/env kullanıyorsanız ilgili anahtarları arayın (isimler projeye göre değişebilir)
# Örn (charger repo): grep -nE '^METER_' .env
grep -RIn --line-number 'METER_(TYPE|PORT|BAUDRATE|SLAVE_ID|TIMEOUT)' . 2>/dev/null | head -n 50
```

**Acrel için beklenen minimum set:**

- `METER_TYPE=acrel`
- `METER_PORT=/dev/ttyAMA5` (veya sizdeki doğru port)
- `METER_BAUDRATE=9600`
- `METER_SLAVE_ID=111`
- `METER_TIMEOUT=1.0`

> En sık hata: `METER_SLAVE_ID`’yi 1 bırakmak (Acrel sahada 111).

### 2) Port var mı? (UART5 overlay)

```bash
ls -la /dev/ttyAMA* /dev/serial* /dev/ttyUSB* 2>/dev/null || true
grep -n 'dtoverlay=uart5' /boot/firmware/config.txt 2>/dev/null || true
```

Bu projede UART5 için sahada kullanılan satır:

```text
dtoverlay=uart5,txd5_pin=12,rxd5_pin=13
```

### 3) Permission denied

```bash
groups
sudo usermod -aG dialout $USER
newgrp dialout
```

### 4) Port “busy” mi? (tek proses kuralı)

`/dev/ttyAMA5` aynı anda iki farklı proses tarafından açılmamalıdır.

```bash
sudo fuser -v /dev/ttyAMA5 2>/dev/null || true
systemctl is-active charger-api.service || true
```

- Eğer `charger-api` çalışıyorsa, test için **önce API üzerinden** (`/api/meter/reading`) doğrulayın.
- Direkt driver testi yapacaksanız `charger-api`’yi durdurmanız gerekebilir (operasyon planına göre).

### 5) Fiziksel katman (RS485) kontrolleri

- **A/B tersliği:** Veri gelmiyorsa A ↔ B swap deneyin.
- **Ortak GND:** RPi ↔ transceiver ↔ meter arasında ortak referans olmalı.
- **Sonlandırma (opsiyonel):** Uzun hatlarda 120Ω terminasyon gerekebilir.

### 6) Tek seferlik driver testi (Acrel)

> Bu test için portun başka proses tarafından kullanılmadığından emin olun (bkz. adım 4).

```bash
# Repo bağımsız driver testi için üstteki "Kopyala-Çalıştır Testi" script'ini kullanın.
true
```

### 7) Loglardan ipucu al

```bash
tail -n 200 logs/system.log | grep -iE 'meter|acrel' || true
```

---

## 📝 Proje İçindeki Entegrasyon Noktaları (SSOT)

- **Config/env:** `api/config.py` + `.env` içindeki `METER_*` değişkenleri
- **Driver seçimi:** `api/meter/interface.py:get_meter()` → `METER_TYPE=acrel` ise `AcrelModbusMeter`
- **Acrel driver:** `api/meter/acrel.py` (register/scale mantığı burada)
- **API endpoint:** `api/routers/meter.py`
  - `GET /api/meter/status`
  - `GET /api/meter/reading`
- **Bağımlılıklar:** `requirements.txt` → `pymodbus==3.6.7`, `pyserial>=3.5`

---

## ✅ Kurulum Kontrol Listesi (Acrel)

- [ ] Meter cihaz ayarları: **9600**, **EVEN**, **Slave ID=111** (sahadaki Acrel)
- [ ] RS485 hat: A/B doğru (gerekirse swap), ortak GND var
- [ ] RPi: `/boot/firmware/config.txt` içinde `dtoverlay=uart5,txd5_pin=12,rxd5_pin=13`
- [ ] Reboot sonrası `/dev/ttyAMA5` mevcut
- [ ] Kullanıcı `dialout` grubunda
- [ ] `.env` içinde `METER_TYPE=acrel` ve doğru `METER_*` set edildi
- [ ] `charger-api` restart sonrası `curl http://localhost:8000/api/meter/reading` okuma veriyor
