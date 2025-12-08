# Dokümantasyon İndeksi

**Oluşturulma:** 2025-12-08 19:00:00  
**Son Güncelleme:** 2025-12-09 02:45:00  
**Versiyon:** 1.1.0  
**Açıklama:** Proje dokümantasyonlarının organizasyonu ve erişim rehberi

---

## ⚡ Hızlı Başlangıç

**Yeni bir AI asistanı veya geliştirici için öncelik sırası:**
1. `WORKSPACE_INDEX.md` - Workspace yapısı ve dosya açıklamaları (ÖNCE BUNU OKU!)
2. `todo/START_HERE.md` - Projeye devam etmek için başlangıç noktası
3. `project_info_20251208_145614.md` - Ana proje bilgileri ve teknik detaylar

---

## 📚 Dokümantasyon Yapısı

### 🗂️ Workspace ve Proje Yapısı

#### `WORKSPACE_INDEX.md` ⭐ YENİ
- **Amaç:** Workspace'teki tüm dosya ve klasörlerin hızlı referansı
- **İçerik:** 
  - Klasör yapısı ve açıklamaları
  - Tüm dosyaların ne/ne amaçla/ne zaman sorularına cevaplar
  - Dosya ilişkileri ve akış diyagramları
  - Hızlı referans ve kullanım önerileri
- **Ne Zaman:** 2025-12-09'da oluşturuldu
- **Kullanım:** Workspace'te dosya bulma, ilişkileri anlama, hızlı referans
- **Fayda:** Orta-uzun vadede workspace navigasyonu için çok faydalı

### 🎯 Ana Dokümantasyon

#### 1. Proje Bilgileri
- **Dosya:** `project_info_20251208_145614.md`
- **Amaç:** Tüm teknik detaylar, protokol bilgileri, önemli notlar ve dersler
- **İçerik:**
  - Proje genel bilgileri
  - ESP32-RPi iletişim protokolü
  - Komut tanımları ve hex kodları
  - Ngrok yapılandırması
  - API endpoint'leri
  - Önemli notlar ve çıkarımlar
  - Versiyon geçmişi

#### 2. API Örnekleri
- **Dosya:** `API_EXAMPLES.md`
- **Amaç:** Tüm API endpoint'leri için curl örnekleri ve kullanım rehberi
- **İçerik:**
  - Status endpoint örnekleri
  - Charge start/stop örnekleri
  - Max current ayarlama örnekleri
  - Station info endpoint örnekleri

#### 3. README
- **Dosya:** `README.md`
- **Amaç:** Proje genel bakışı ve hızlı başlangıç rehberi
- **İçerik:**
  - Proje tanımı
  - Hızlı başlangıç
  - Proje yapısı
  - Teknik detaylar
  - API endpoints
  - Dokümantasyon linkleri

---

### 📋 Proje Yönetimi Dokümantasyonu

#### 1. Başlangıç Noktası
- **Dosya:** `todo/START_HERE.md`
- **Amaç:** AI asistanları ve yeni geliştiriciler için başlangıç rehberi
- **Kullanım:** Yeni bir chat oturumunda "projeye devam et" dediğinizde ilk okunması gereken dosya

#### 2. Checkpoint
- **Dosya:** `todo/checkpoint.md`
- **Amaç:** Projenin mevcut durumunun hızlı özeti
- **İçerik:** Nerede kaldık, son yapılan işler

#### 3. Detaylı Durum
- **Dosya:** `todo/project_state.md`
- **Amaç:** Projenin detaylı durumu ve ilerleme raporu
- **İçerik:** Tamamlananlar, devam edenler, bekleyenler

#### 4. AI Çalışma Akışı
- **Dosya:** `todo/ai_workflow.md`
- **Amaç:** AI asistanları için çalışma kuralları ve akışı
- **İçerik:** Otonom çalışma kuralları, görev seçimi, tamamlama süreci

#### 5. Uzman Önerileri
- **Dosya:** `todo/expert_recommendations.md`
- **Amaç:** Best practices, test stratejileri, code quality önerileri
- **İçerik:** Kıdemli uzman perspektifinden öneriler

---

### ✅ Todo Sistemi

#### 1. Bekleyen Görevler
- **Dosya:** `todo/master_next.md`
- **Amaç:** Öncelik sırasına göre bekleyen görevler
- **Kullanım:** Yeni görev seçilirken buradan bakılır

#### 2. Aktif Görevler
- **Dosya:** `todo/master_live.md`
- **Amaç:** Şu anda çalışılan görevler (max 2-3)
- **Kullanım:** Aktif çalışma takibi

#### 3. Tamamlanan Görevler
- **Dosya:** `todo/master_done.md`
- **Amaç:** Tamamlanan görevlerin geçmişi
- **İçerik:** Tarih, görev detayları, sonuçlar

#### 4. Genel Bilgiler
- **Dosya:** `todo/master.md`
- **Amaç:** Todo sistemi kuralları ve genel bilgiler

---

## 🔍 Dokümantasyon Erişim Rehberi

### Yeni Başlayanlar İçin
1. `README.md` - Proje genel bakışı
2. `todo/START_HERE.md` - Başlangıç rehberi
3. `project_info_20251208_145614.md` - Teknik detaylar

### Geliştiriciler İçin
1. `API_EXAMPLES.md` - API kullanım örnekleri
2. `esp32/protocol.json` - Protokol tanımları
3. `esp32/bridge.py` - ESP32 iletişim modülü

### AI Asistanları İçin
1. `todo/START_HERE.md` - İlk okunması gereken
2. `todo/checkpoint.md` - Mevcut durum
3. `todo/master_next.md` - Bekleyen görevler
4. `todo/ai_workflow.md` - Çalışma kuralları

### Proje Yöneticileri İçin
1. `todo/project_state.md` - Detaylı durum raporu
2. `todo/master_done.md` - Tamamlanan görevler
3. `todo/expert_recommendations.md` - Öneriler

---

## 📝 Dokümantasyon Güncelleme Kuralları

1. **Her önemli değişiklik sonrası:**
   - `project_info_20251208_145614.md` güncellenmeli
   - İlgili dokümantasyon dosyası güncellenmeli

2. **API değişikliklerinde:**
   - `API_EXAMPLES.md` güncellenmeli
   - `project_info_20251208_145614.md` güncellenmeli

3. **Todo sistemi değişikliklerinde:**
   - İlgili todo dosyası güncellenmeli
   - `todo/project_state.md` güncellenmeli

4. **Yeni özellik eklerken:**
   - İlgili dokümantasyon oluşturulmalı
   - `README.md` güncellenmeli

---

## 🔗 Hızlı Linkler

- **Workspace Index:** `WORKSPACE_INDEX.md` ⭐ YENİ
- **Proje Bilgileri:** `project_info_20251208_145614.md`
- **API Örnekleri:** `API_EXAMPLES.md`
- **Başlangıç:** `todo/START_HERE.md`
- **Durum:** `todo/checkpoint.md`
- **Detaylı Durum:** `todo/project_state.md`

---

**Not:** Tüm dokümantasyon dosyaları İngilizce dosya isimleriyle saklanır, ancak içerik Türkçe olabilir.

