# Todo Sistemi - Genel Bilgiler ve Info Noktaları

**Oluşturulma Tarihi:** 2025-12-08 18:20:00  
**Son Güncelleme:** 2025-12-08 18:20:00  
**Version:** 1.0.0

---

## Todo Sistemi Açıklaması

Bu klasör proje yönetimi için kullanılan todo sistemini içerir.

### Dosya Yapısı

- **START_HERE.md** - ⚡ Projeye devam etmek için başlangıç noktası (ÖNCE BUNU OKU!)
- **master.md** (bu dosya) - Genel bilgiler, kurallar ve info noktaları
- **checkpoint.md** - Nerede kaldık? Hızlı durum kontrolü
- **project_state.md** - Detaylı proje durumu ve ilerleme takibi
- **ai_workflow.md** - AI asistanları için çalışma akışı ve kurallar
- **master_next.md** - Sonraki yapılacaklar listesi
- **master_live.md** - Şu anda aktif olarak yapılan işler
- **master_done.md** - Tamamlanan işler (tarih ve detaylarla)
- **expert_recommendations.md** - Kıdemli uzman önerileri ve best practices

### Kullanım Kuralları

1. **master_live.md**: Şu anda aktif olarak çalışılan maksimum 2-3 görev olmalı
2. **master_next.md**: Öncelik sırasına göre sıralanmış görevler
3. **master_done.md**: Tamamlanan görevler tarih ve detaylarla kaydedilir
4. **master.md**: Sistem kuralları, önemli notlar ve genel bilgiler

### Görev Formatı

Her görev şu formatta olmalıdır:
```
- [ ] Görev başlığı
  - Açıklama: Detaylı açıklama
  - Öncelik: Yüksek/Orta/Düşük
  - Tahmini Süre: X saat/gün
  - Bağımlılıklar: Diğer görevler
  - Notlar: Önemli notlar
```

### Görev Durumları

- **TODO**: Henüz başlanmamış
- **IN_PROGRESS**: Aktif olarak çalışılıyor
- **DONE**: Tamamlandı
- **BLOCKED**: Başka bir göreve bağımlı
- **CANCELLED**: İptal edildi

---

## Önemli Info Noktaları

### Proje Bilgileri
- **Proje Adı:** AC Charger
- **Çalışma Dizini:** `/home/basar/charger`
- **GitHub Repository:** https://github.com/CaiserSz/orge1.git

### Teknik Stack
- **Backend:** Python (FastAPI)
- **Microcontroller:** ESP32 (Arduino CLI)
- **Platform:** Raspberry Pi
- **API Framework:** FastAPI
- **Serial Communication:** pyserial

### Kritik Kurallar
- Tüm dosya isimleri İngilizce olmalı
- Virtual environment (env) kullanılmalı
- Her değişiklik sonrası testler çalıştırılmalı
- Git commit/push sürekli yapılmalı
- Kod standardı korunmalı

### İletişim Protokolü
- **Baudrate:** 115200
- **Format:** Binary Hex (`41 [KOMUT] 2C [DEĞER] 10`)
- **Paket Uzunluğu:** 5 byte
- **Status Update:** Her 5 saniyede bir

### API Endpoints
- Base URL: `https://lixhium.ngrok.app`
- Docs: `https://lixhium.ngrok.app/docs`
- Port: 8000

---

## Güncelleme Notları

### 2025-12-08 18:20:00
- Todo sistemi oluşturuldu
- Dosya yapısı ve kurallar tanımlandı

