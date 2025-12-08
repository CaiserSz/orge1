# AC Charger Project

**Proje Tipi:** AC Charger (Elektrikli Araç Şarj İstasyonu)  
**Platform:** Raspberry Pi + ESP32  
**Dil:** Python (FastAPI) + Arduino (ESP32)  
**Repository:** https://github.com/CaiserSz/orge1.git

---

## 🚀 Hızlı Başlangıç

### Projeye Devam Etmek İçin

**AI Asistanları ve Geliştiriciler için:**

```bash
# 1. Projenin durumunu öğren
cat todo/START_HERE.md

# 2. Nerede kaldık?
cat todo/checkpoint.md

# 3. Detaylı durum
cat todo/project_state.md
```

**ÖNEMLİ:** Yeni bir chat oturumunda "projeye devam et" dediğinizde, AI asistanı otomatik olarak:
1. ✅ Projenin ne olduğunu anlayacak
2. ✅ Nerede kaldığını tespit edecek
3. ✅ Bekleyen görevleri görecek
4. ✅ En yüksek öncelikli görevi seçecek
5. ✅ Proaktif çalışarak projeyi ilerletecek

---

## 📁 Proje Yapısı

```
/home/basar/charger/
├── api/                    # REST API (FastAPI)
│   ├── main.py            # Ana API uygulaması
│   └── station_info.py    # İstasyon bilgileri yönetimi
├── esp32/                  # ESP32 Bridge ve Protokol
│   ├── bridge.py           # ESP32 seri iletişim modülü
│   ├── protocol.json       # Protokol tanımları
│   └── Commercial_08122025.ino  # ESP32 firmware
├── ocpp/                   # OCPP Implementasyonu (gelecek)
│   ├── main.py
│   ├── handlers.py
│   └── states.py
├── meter/                  # Meter Okuma Modülü (gelecek)
│   └── read_meter.py
├── data/                   # Veri dosyaları
│   └── station_info.json   # İstasyon bilgileri
├── logs/                   # Log dosyaları
│   ├── meter.log
│   └── system.log
├── todo/                   # Proje Yönetimi ve Todo Sistemi
│   ├── START_HERE.md      # ⚡ BAŞLANGIÇ NOKTASI
│   ├── checkpoint.md       # Nerede kaldık?
│   ├── project_state.md   # Detaylı durum
│   ├── ai_workflow.md     # AI çalışma akışı
│   ├── master.md          # Genel bilgiler ve kurallar
│   ├── master_next.md     # Bekleyen görevler
│   ├── master_live.md     # Aktif görevler
│   ├── master_done.md     # Tamamlanan görevler
│   └── expert_recommendations.md  # Best practices
├── env/                    # Python virtual environment (gitignore)
├── project_info_20251208_145614.md  # Ana proje dokümantasyonu
├── API_EXAMPLES.md         # API kullanım örnekleri
├── station_form.html       # İstasyon bilgileri formu
├── .cursorrules            # Cursor AI kuralları
├── .env                    # Ortam değişkenleri (gitignore)
├── requirements.txt        # Python bağımlılıkları
└── ngrok.yml              # Ngrok yapılandırması
```

---

## 🎯 Proje Durumu

**Mevcut Faz:** Faz 1 ✅ (Tamamlandı)  
**Sonraki Faz:** Faz 2 🔄 (API Test ve İyileştirme)  
**Genel İlerleme:** %32

### Tamamlananlar
- ✅ ESP32-RPi Bridge Modülü
- ✅ REST API (7 endpoint)
- ✅ Ngrok Yapılandırması
- ✅ Git Repository
- ✅ Todo Sistemi
- ✅ Proje Dokümantasyonu

### Devam Edenler
- Şu anda aktif görev yok

### Bekleyenler (Öncelik Sırasına Göre)
1. Test Altyapısı Kurulumu (Kritik)
2. Logging Sistemi Kurulumu (Kritik)
3. API Testleri Yazılması (Yüksek)
4. Code Quality Tools (Yüksek)
5. CI/CD Pipeline (Yüksek)

---

## 🔧 Teknik Detaylar

### Gereksinimler
- Python 3.13
- Raspberry Pi (SSH erişimi)
- ESP32 (USB bağlantılı)
- Virtual Environment (env/)

### Kurulum
```bash
cd /home/basar/charger
source env/bin/activate
pip install -r requirements.txt
```

### API Çalıştırma
```bash
cd /home/basar/charger
source env/bin/activate
python api/main.py
# veya
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### API Endpoints
- **Base URL:** `https://lixhium.ngrok.app`
- **Docs:** `https://lixhium.ngrok.app/docs`
- **Form:** `https://lixhium.ngrok.app/form`
- **Health:** `https://lixhium.ngrok.app/api/health`
- **Status:** `https://lixhium.ngrok.app/api/status`
- **Station Info:** `https://lixhium.ngrok.app/api/station/info`

Detaylı API örnekleri için `API_EXAMPLES.md` dosyasına bakınız.

---

## 📚 Dokümantasyon

### Ana Dokümantasyon
- **Proje Bilgileri:** `project_info_20251208_145614.md` - Tüm teknik detaylar, protokol bilgileri, önemli notlar
- **API Örnekleri:** `API_EXAMPLES.md` - Tüm API endpoint'leri için curl örnekleri

### Proje Yönetimi
- **Başlangıç:** `todo/START_HERE.md` - AI asistanları için başlangıç noktası
- **Checkpoint:** `todo/checkpoint.md` - Projenin mevcut durumu
- **Detaylı Durum:** `todo/project_state.md` - Detaylı proje durumu
- **AI Çalışma Akışı:** `todo/ai_workflow.md` - AI asistanları için çalışma kuralları
- **Uzman Önerileri:** `todo/expert_recommendations.md` - Best practices ve öneriler

### Todo Sistemi
- **Bekleyen Görevler:** `todo/master_next.md` - Öncelikli görevler
- **Aktif Görevler:** `todo/master_live.md` - Şu anda çalışılan görevler
- **Tamamlanan Görevler:** `todo/master_done.md` - Tamamlanan görevler geçmişi

---

## 🔗 İletişim Protokolü

- **Baudrate:** 115200
- **Format:** Binary Hex (`41 [KOMUT] 2C [DEĞER] 10`)
- **Paket Uzunluğu:** 5 byte
- **Status Update:** Her 5 saniyede bir

Detaylar için `project_info_20251208_145614.md` dosyasına bakınız.

---

## 🚨 Kritik Kurallar

1. Tüm dosya isimleri İngilizce olmalı
2. Virtual environment (env) kullanılmalı
3. Her değişiklik sonrası testler çalıştırılmalı
4. Git commit/push sürekli yapılmalı
5. Dokümantasyon güncel tutulmalı

---

## 📝 Lisans

Bu proje özel bir projedir.

---

**Son Güncelleme:** 2025-12-08 19:00:00

