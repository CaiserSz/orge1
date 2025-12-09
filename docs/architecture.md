# Sistem Mimarisi - AC Charger

**Oluşturulma Tarihi:** 2025-12-09 22:40:00
**Son Güncelleme:** 2025-12-09 22:40:00
**Version:** 1.0.0

---

## Sistem Mimarisi ve Görev Dağılımı (2025-12-08 16:02:06)

#### Görev Ayrımı
- **ESP32:** Fiziksel tarafın sorumluluğu ESP32'nindir
- **Raspberry Pi:** Bilgi alır ve OCPP, API veya web servislerini besler

#### OCPP Desteği (2025-12-08 16:31:39)
- **OCPP Versiyonları:** RPi hem OCPP 2.0.1 hem de OCPP 1.6J destekli olarak CSMS (Central System Management System) ile haberleşebilecektir
- **Çift Versiyon Desteği:** Sistem her iki OCPP versiyonunu da destekleyecek şekilde tasarlanacaktır
- **CSMS Entegrasyonu:** Merkezi sistem yönetimi ile haberleşme OCPP protokolü üzerinden yapılacaktır

#### API ve Endpoint'ler (2025-12-08 16:31:39)

**API Geliştirme:** RPi'de ESP32'ye gönderilen komutlar için ve ESP32'den durum bilgisi alınabilmesi için API ve endpoint'ler hazırlanacaktır

**OCPP Bağımsızlığı:** Bu API sayesinde OCPP'den bağımsız olarak da istasyon testler için kullanılabilecektir

**Test Erişimi:** API üzerinden direkt olarak ESP32 komutları gönderilebilir ve durum bilgileri alınabilir

**Kullanım Senaryoları:**
  - OCPP üzerinden normal operasyon
  - API üzerinden test ve debug işlemleri
  - OCPP olmadan direkt kontrol ve izleme

#### REST API Implementasyonu (2025-12-08 18:15:00)

**API Framework:** FastAPI (Python)
- **Port:** 8000
- **Base URL:** `https://lixhium.ngrok.app` (dışarıdan erişim)
- **Local URL:** `http://localhost:8000`
- **Dokümantasyon:** `https://lixhium.ngrok.app/docs` (Swagger UI)
- **ReDoc:** `https://lixhium.ngrok.app/redoc`

**API Endpoint'leri:**

1. **GET /** - API root endpoint
   - API bilgilerini döndürür

2. **GET /api/health** - Sistem sağlık kontrolü
   - API ve ESP32 bağlantı durumunu kontrol eder

3. **GET /api/status** - ESP32 durum bilgisi
   - ESP32'den son durum bilgisini alır
   - ESP32 her 5 saniyede bir otomatik durum gönderir
   - Response: Status mesajı (CP, PP, Relay, Lock, Motor, PWM, Max Current, Cable Current, Auth, State, Power Board Status, Stop Requested)

4. **POST /api/charge/start** - Şarj başlatma
   - ESP32'ye authorization komutu gönderir
   - **ÖNEMLİ:** Sadece EV_CONNECTED (State=3) durumunda çalışır
   - Şarj izni verir ve şarjı başlatır
   - Request Body: `{}` (boş)
   - **State Gereksinimleri:**
     - ✅ State=3 (EV_CONNECTED): Authorization gönderilir
     - ❌ State=1 (IDLE): Kablo takılı değil, hata döndürülür
     - ❌ State=2 (CABLE_DETECT): Araç bağlı değil, hata döndürülür
     - ❌ State=4 (READY): Authorization zaten verilmiş, hata döndürülür
     - ❌ State>=5: Aktif şarj veya hata durumu, hata döndürülür

5. **POST /api/charge/stop** - Şarj durdurma
   - ESP32'ye charge stop komutu gönderir
   - Şarjı sonlandırır
   - Request Body: `{}` (boş)

6. **POST /api/maxcurrent** - Maksimum akım ayarlama
   - ESP32'ye maksimum akım değerini ayarlar
   - **ÖNEMLİ:** Sadece aktif şarj başlamadan yapılabilir
   - Request Body: `{"amperage": 16}` (6-32 amper aralığında herhangi bir tam sayı)
   - Güvenlik: Şarj aktifken akım değiştirilemez
   - **Not:** 6-32 amper aralığında herhangi bir tam sayı değer kullanılabilir (örn: 12, 15, 18, 22, vb.)

7. **GET /api/current/available** - Kullanılabilir akım aralığı
   - ESP32'de ayarlanabilir akım aralığını döndürür
   - Response: `{"range": "6-32 amper", "min": 6, "max": 32, "note": "6-32 aralığında herhangi bir tam sayı değer kullanılabilir"}`

**ESP32 Bridge Modülü:**
- **Dosya:** `esp32/bridge.py`
- **Fonksiyonlar:**
  - `connect()` - ESP32'ye bağlan
  - `send_status_request()` - Status komutu gönder
  - `send_authorization()` - Authorization komutu gönder
  - `send_current_set(amperage)` - Akım set komutu gönder
  - `send_charge_stop()` - Şarj durdurma komutu gönder
  - `get_status()` - Son durum bilgisini al
  - `get_status_sync(timeout)` - Status komutu gönder ve yanıt bekle

**Protokol Tanımları:**
- **Dosya:** `esp32/protocol.json`
- Tüm komut tanımları, byte array formatları ve protokol detayları JSON formatında

**Bağımlılıklar:**
- `pyserial` - USB seri port iletişimi
- `fastapi` - REST API framework
- `uvicorn` - ASGI server
- `pydantic` - Veri validasyonu

**API Çalıştırma:**
```bash
cd /home/basar/charger
source env/bin/activate
python api/main.py
```
veya
```bash
cd /home/basar/charger
source env/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

#### RPi'den ESP32'ye Gönderilebilecek Komutlar
RPi'den ESP32'ye sadece aşağıdaki komutlar gönderilebilir:

**Tam Komut Listesi (Hex Kod ve Byte Array Formatında):**

| # | Komut | Komut ID | Değer | Hex Kod Dizini | Byte Array (Python) | Byte Array (C/C++) | Açıklama |
|---|-------|----------|-------|----------------|---------------------|-------------------|----------|
| 1 | Status | 00 | 00 | `41 00 2C 00 10` | `[0x41, 0x00, 0x2C, 0x00, 0x10]` | `{0x41, 0x00, 0x2C, 0x00, 0x10}` | İstasyon durumu okuma |
| 2 | Authorization | 01 | 01 | `41 01 2C 01 10` | `[0x41, 0x01, 0x2C, 0x01, 0x10]` | `{0x41, 0x01, 0x2C, 0x01, 0x10}` | Şarj izni ver |
| 3 | Akım Set | 02 | 06 | `41 02 2C 06 10` | `[0x41, 0x02, 0x2C, 0x06, 0x10]` | `{0x41, 0x02, 0x2C, 0x06, 0x10}` | Maksimum akım: 6A |
| 4 | Akım Set | 02 | 0A | `41 02 2C 0A 10` | `[0x41, 0x02, 0x2C, 0x0A, 0x10]` | `{0x41, 0x02, 0x2C, 0x0A, 0x10}` | Maksimum akım: 10A |
| 5 | Akım Set | 02 | 0D | `41 02 2C 0D 10` | `[0x41, 0x02, 0x2C, 0x0D, 0x10]` | `{0x41, 0x02, 0x2C, 0x0D, 0x10}` | Maksimum akım: 13A |
| 6 | Akım Set | 02 | 10 | `41 02 2C 10 10` | `[0x41, 0x02, 0x2C, 0x10, 0x10]` | `{0x41, 0x02, 0x2C, 0x10, 0x10}` | Maksimum akım: 16A ⭐ |
| 7 | Akım Set | 02 | 14 | `41 02 2C 14 10` | `[0x41, 0x02, 0x2C, 0x14, 0x10]` | `{0x41, 0x02, 0x2C, 0x14, 0x10}` | Maksimum akım: 20A |
| 8 | Akım Set | 02 | 19 | `41 02 2C 19 10` | `[0x41, 0x02, 0x2C, 0x19, 0x10]` | `{0x41, 0x02, 0x2C, 0x19, 0x10}` | Maksimum akım: 25A |
| 9 | Akım Set | 02 | 20 | `41 02 2C 20 10` | `[0x41, 0x02, 0x2C, 0x20, 0x10]` | `{0x41, 0x02, 0x2C, 0x20, 0x10}` | Maksimum akım: 32A |
| 10 | State Machine | 04 | 07 | `41 04 2C 07 10` | `[0x41, 0x04, 0x2C, 0x07, 0x10]` | `{0x41, 0x04, 0x2C, 0x07, 0x10}` | Şarjı bitir |

**Önemli Notlar:**
- **Akım Değiştirme Güvenlik Kuralı:** Akım set komutları sadece aktif şarj başlamadan gönderilebilir. Şarj esnasında akım değiştirilemez (güvenlik nedeniyle).
- **Kritik Kural:** Başka komut RPi'den ESP32'ye gitmez.
- Tüm komutlar 5 byte uzunluğundadır.
- Protokol formatı: `41 [KOMUT] 2C [DEĞER] 10`

#### ESP32 Otonom Çalışma
- **State Machine:** ESP32 fiziksel tarafta gelen komutlara ve ev kullanıcısının davranışlarına göre state machine ile çalışır
- **Otonom Yürütme:** ESP32 süreci kendi içinde otonom olarak yürütür
- **Fiziksel Kontrol:** Fiziksel taraftaki tüm kontroller ESP32'nin sorumluluğundadır

---

### ESP32-RPi İletişim Protokolü (2025-12-08 15:43:20)
- **Baudrate:** 115200
- **Protokol Formatı:** Binary Hex Protokolü
- **Paket Yapısı:** 5 byte - `41 [KOMUT] 2C [DEĞER] 10`
  - Byte 1: `0x41` (Sabit başlangıç)
  - Byte 2: `[KOMUT]` (Komut kodu, 1 byte hex)
  - Byte 3: `0x2C` (Sabit ayırıcı)
  - Byte 4: `[DEĞER]` (Komut değeri, 1 byte hex)
  - Byte 5: `0x10` (Sabit bitiş)
- **Önemli:** Sadece belirtilen komutlar RPi'den ESP32'ye gönderilebilir

### ESP32 Durum Bilgileri (2025-12-08 15:50:36)
- **ESP32 Kodu:** `/home/basar/charger/esp32/Commercial_08122025.ino`
- **Durum Gönderme:** ESP32'den her 5 saniyede bir durum bilgileri gönderilmektedir
- **sendStat() Fonksiyonu:** `loop()` fonksiyonunda `millis() - lastStatTime >= 7500` kontrolü ile çağrılmaktadır
- **Gönderilen Bilgiler:** CP (Control Pilot), PP (Proximity Pilot), Relay, Lock, Motor, PWM, Max Current, Cable Current, Auth, State, Power Board Status, Stop Requested

### ESP32 Geliştirme Araçları (2025-12-08 15:00:11)
- ESP32 yükleme ve yönetimi için Arduino CLI kullanılacak
- PlatformIO kullanılmayacak

### Geliştirme Ortamı (2025-12-08 14:59:29)
- Proje geliştirme süreci (env) virtual environment ile yönetilecektir
- Terminal açıldığında otomatik olarak virtual ortamda açılacak ve kodlar orada yürütülecektir
- Poetry kullanılmayacak, bunun yerine Python virtual environment (env) kullanılacak

---

## Önemli Noktalar ve Hatırlanması Gerekenler

### Kritik Dosyalar (2025-12-08 14:57:30)
- `/home/basar/charger/project_info_20251208_145614.md` ve `/home/basar/charger/.cursorrules` dosyaları her zaman güncel tutulacaktır.
- Bu dosyalar proje süresince sürekli güncellenecek ve bakımı yapılacaktır.

### Todo Sistemi (2025-12-08 18:20:00)

**Todo Klasörü:** `/home/basar/charger/todo/`

**Dosyalar:**
- `START_HERE.md` - ⚡ Projeye devam etmek için başlangıç noktası (ÖNCE BUNU OKU!)
- `checkpoint.md` - Nerede kaldık? Hızlı durum kontrolü
- `project_state.md` - Detaylı proje durumu ve ilerleme takibi
- `ai_workflow.md` - AI asistanları için çalışma akışı ve kurallar
- `master.md` - Genel bilgiler, kurallar ve info noktaları
- `master_next.md` - Sonraki yapılacaklar listesi (öncelik sırasına göre)
- `master_live.md` - Şu anda aktif olarak yapılan işler (maksimum 2-3 görev)
- `master_done.md` - Tamamlanan işler (tarih ve detaylarla)
- `expert_recommendations.md` - Kıdemli uzman önerileri ve best practices

**Kullanım:** Proje yönetimi ve görev takibi için kullanılır

**Otonom Çalışma:** AI asistanları projeye devam ettiğinde `START_HERE.md` dosyasını okuyarak nerede kaldığını anlayabilir ve proaktif çalışabilir

**Güncelleme:** Görevler tamamlandıkça `master_done.md`'ye taşınır, aktif görevler `master_live.md`'ye eklenir, durum `project_state.md` ve `checkpoint.md`'de güncellenir

### Çalışma Dizini ve Kısıtlamalar (2025-12-08 15:17:41)
- **Çalışma Dizini:** /home/basar/charger
- Dosya, klasör, alt klasör, ikilik (binary) yaratacak durumlara izin verilmeyecektir
- Kod standardı tüm workspace ve projede korunacaktır
- Tüm geliştirme çalışmaları bu dizin içinde yapılacaktır

### Çalışma Prensipleri (2025-12-08 15:19:35)
- Varsayımlarla değil gerçek verilerle hareket edilecektir
- Sistemde birşey yapılması gerektiğinde erişilemez veya SSH gerekli gibi varsayılmayacaktır
- Direkt terminalden herşey yapılabilir durumdadır
- Tüm işlemler terminal üzerinden gerçek verilerle yapılacaktır

### ESP32-RPi USB Bağlantı Kontrolü ve İzleme (2025-12-08 15:53:47)
- **Sorun Tespiti:** Herhangi bir sorun olduğunda ESP32 ve RPi arasında fiziksel bir sorun var mı diye bakmak için istenildiği zaman RPi'den USB'yi kullanabilecek herhangi bir şey var mı diye kontrol edilmelidir
- **USB Temizleme:** Gerekirse USB'yi temizleyip 115200 baudrate ile izleme yapılmalıdır
- **İzleme Süresi:** ESP32'den rutin bilgi formatı geliyor mu kontrolü için 10-15 saniye izleme yapılmalıdır
- **Baudrate:** 115200
- **Kontrol Mekanizması:** USB bağlantısını kontrol etmek, USB'yi temizlemek ve izleme yapmak için gerekli araçlar kullanılmalıdır
- **Beklenen Davranış:** ESP32'den her 5 saniyede bir `<STAT;...>` formatında durum bilgileri gelmelidir
- **Durum Değerlendirme Kriteri:** Rutin bilgiler gelmeye devam ettikçe ESP32'nin durumunun aktif ve sorunsuz olduğu kabul edilmelidir

_(Bu bölüm çalışmalar ilerledikçe güncellenecek)_

---

## Proje Planlama ve Değerlendirme

### Mevcut Durum Analizi (2025-12-08 16:32:52)

#### Toplanan Bilgiler Özeti
1. **Proje Temeli:**
   - AC Charger geliştirme projesi
   - Raspberry Pi (SSH bağlı, tam yetkiler) + ESP32 (USB bağlantılı)
   - Çalışma dizini: `/home/basar/charger`

2. **Sistem Mimarisi:**
   - ESP32: Fiziksel tarafın sorumluluğu, otonom state machine ile çalışma
   - RPi: OCPP, API ve web servisleri, bilgi toplama ve yönetim

3. **İletişim Protokolü:**
   - Baudrate: 115200
   - Protokol: Binary Hex (`41 [KOMUT] 2C [DEĞER] 10`, 5 byte)
   - ESP32'den her 5 saniyede durum bilgisi (`<STAT;...>` formatında)

4. **Komutlar:**
   - 10 komut tanımlı (Status, Authorization, Akım Set x7, State Machine)
   - Tüm komutlar dokümante edildi (hex kod, byte array formatları)

5. **OCPP Desteği:**
   - OCPP 2.0.1 ve OCPP 1.6J desteği planlandı
   - CSMS entegrasyonu

6. **API ve Endpoint'ler:**
   - ESP32 komutları ve durum bilgileri için API geliştirilecek
   - OCPP bağımsız test erişimi

#### Mevcut Dosya Durumu
- ✅ `esp32/Commercial_08122025.ino` - ESP32 kodu mevcut (1438 satır)
- ⚠️ `esp32/bridge.py` - Boş (ESP32-RPi köprü modülü geliştirilmeli)
- ⚠️ `esp32/protocol.json` - Boş (Protokol tanımları eklenmeli)
- ⚠️ `ocpp/main.py` - Basit placeholder (OCPP implementasyonu gerekli)
- ⚠️ `ocpp/handlers.py` - Boş (OCPP handler'ları geliştirilmeli)
- ⚠️ `ocpp/states.py` - Boş (OCPP state yönetimi gerekli)
- ⚠️ `meter/read_meter.py` - Boş (Meter okuma modülü geliştirilmeli)

#### Geliştirme Öncelikleri

**Faz 1: Temel Altyapı (Kritik)**
1. ESP32-RPi Bridge Modülü (`esp32/bridge.py`)
   - USB seri port bağlantısı (115200 baudrate)
   - Komut gönderme fonksiyonları (10 komut)
   - Durum bilgisi okuma ve parse etme
   - Hata yönetimi ve bağlantı kontrolü

2. Protokol Tanımları (`esp32/protocol.json`)
   - Komut tanımları ve byte array formatları
   - Durum mesajı formatı ve parse kuralları
   - Hata kodları ve açıklamaları

**Faz 2: API Katmanı**
3. REST API Geliştirme
   - ESP32 komutları için endpoint'ler
   - Durum bilgisi endpoint'leri
   - Test ve debug endpoint'leri
   - API dokümantasyonu

**Faz 3: OCPP Entegrasyonu**
4. OCPP 1.6J Implementasyonu
   - WebSocket bağlantı yönetimi
   - Temel OCPP mesajları (Authorize, StartTransaction, StopTransaction, StatusNotification)
   - CSMS entegrasyonu

5. OCPP 2.0.1 Implementasyonu
   - OCPP 2.0.1 protokol desteği
   - Yeni özellikler ve mesajlar
   - Çift versiyon desteği

**Faz 4: Meter ve Monitoring**
6. Meter Okuma Modülü (`meter/read_meter.py`)
   - Enerji ölçüm cihazı entegrasyonu
   - Veri toplama ve işleme
   - Loglama

7. Monitoring ve Logging
   - Sistem durumu izleme
   - Hata loglama
   - Performans metrikleri

**Faz 5: Test ve Optimizasyon**
8. Test Suite
   - Unit testler
   - Entegrasyon testleri
   - ESP32-RPi iletişim testleri
   - OCPP protokol testleri

9. Dokümantasyon ve Deployment
   - API dokümantasyonu
   - Kurulum kılavuzu
   - Sistem mimarisi dokümantasyonu

#### Teknik Gereksinimler

**Python Kütüphaneleri:**
- `pyserial` - USB seri port iletişimi
- `fastapi` veya `flask` - REST API
- `websockets` - OCPP WebSocket bağlantıları
- `pydantic` - Veri validasyonu
- `python-ocpp` - OCPP protokol kütüphanesi (varsa)

**Geliştirme Araçları:**
- Python virtual environment (env)
- Git ve GitHub
- Arduino CLI (ESP32 için)

#### Riskler ve Dikkat Edilmesi Gerekenler
1. **USB Bağlantı Güvenilirliği:** USB bağlantısının kesilmesi durumunda hata yönetimi
2. **ESP32 Durum Takibi:** ESP32'den gelen durum mesajlarının sürekli izlenmesi
3. **OCPP Versiyon Uyumluluğu:** İki OCPP versiyonunun aynı anda desteklenmesi
4. **Güvenlik:** API endpoint'lerinin güvenliği ve yetkilendirme
5. **Akım Değiştirme Güvenliği:** Şarj esnasında akım değiştirme engellemesi

#### Sonraki Adımlar
1. ESP32-RPi bridge modülünün geliştirilmesi
2. Protokol tanımlarının JSON formatında hazırlanması
3. Temel API endpoint'lerinin oluşturulması
4. OCPP implementasyonuna başlanması

---

