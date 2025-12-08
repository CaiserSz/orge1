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
│   └── main.py
├── esp32/                  # ESP32 Bridge ve Protokol
│   ├── bridge.py
│   ├── protocol.json
│   └── Commercial_08122025.ino
├── ocpp/                   # OCPP Implementasyonu (gelecek)
├── meter/                  # Meter Okuma Modülü (gelecek)
├── todo/                   # Proje Yönetimi ve Todo Sistemi
│   ├── START_HERE.md      # ⚡ BAŞLANGIÇ NOKTASI
│   ├── checkpoint.md       # Nerede kaldık?
│   ├── project_state.md   # Detaylı durum
│   ├── ai_workflow.md     # AI çalışma akışı
│   ├── master_next.md     # Bekleyen görevler
│   ├── master_live.md     # Aktif görevler
│   ├── master_done.md     # Tamamlanan görevler
│   └── expert_recommendations.md  # Best practices
├── logs/                   # Log dosyaları
├── env/                    # Python virtual environment
├── project_info_20251208_145614.md  # Proje bilgileri
├── .cursorrules            # Cursor AI kuralları
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
- **Health:** `https://lixhium.ngrok.app/api/health`
- **Status:** `https://lixhium.ngrok.app/api/status`

---

## 📚 Dokümantasyon

- **Proje Bilgileri:** `project_info_20251208_145614.md`
- **Todo Sistemi:** `todo/START_HERE.md`
- **AI Çalışma Akışı:** `todo/ai_workflow.md`
- **Uzman Önerileri:** `todo/expert_recommendations.md`

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

**Son Güncelleme:** 2025-12-08 18:40:00

