# Todo Sistemi Şablonları

**Oluşturulma Tarihi:** 2025-12-10
**Amaç:** Başka projelerde kullanılmak üzere todo sistemi şablonları

---

## 📁 Dosya Yapısı

```
todo/
├── master.md           # Genel bilgiler ve kurallar
├── master_next.md      # Bekleyen görevler (öncelik sırasına göre)
├── master_live.md      # Aktif görevler
├── master_done.md      # Tamamlanan görevler
└── START_HERE.md       # Başlangıç rehberi
```

---

## 📄 master.md Şablonu

```markdown
# Todo Sistemi - Genel Bilgiler ve Info Noktaları

**Oluşturulma Tarihi:** [TARİH]
**Son Güncelleme:** [TARİH]
**Version:** 1.0.0

---

## Todo Sistemi Açıklaması

Bu klasör proje yönetimi için kullanılan todo sistemini içerir.

### Dosya Yapısı

- **START_HERE.md** - ⚡ Projeye devam etmek için başlangıç noktası (ÖNCE BUNU OKU!)
- **master.md** (bu dosya) - Genel bilgiler, kurallar ve info noktaları
- **master_next.md** - Sonraki yapılacaklar listesi
- **master_live.md** - Şu anda aktif olarak yapılan işler
- **master_done.md** - Tamamlanan işler (tarih ve detaylarla)

### Kullanım Kuralları

1. **master_live.md**: Şu anda aktif olarak çalışılan maksimum 2-3 görev olmalı
2. **master_next.md**: Öncelik sırasına göre sıralanmış görevler
3. **master_done.md**: Tamamlanan görevler tarih ve detaylarla kaydedilir
4. **master.md**: Sistem kuralları, önemli notlar ve genel bilgiler

### Görev Formatı

Her görev şu formatta olmalıdır:
```markdown
- [ ] **Görev:** [Görev başlığı]
  - Açıklama: [Detaylı açıklama]
  - Öncelik: [0-8 arası sayı]
  - Tahmini Süre: [X saat/gün]
  - Bağımlılıklar: [Diğer görevler]
  - Durum: 📋 Bekliyor / 🔄 Devam Ediyor / ✅ Tamamlandı
```

### Görev Durumları

- **📋 Bekliyor**: Henüz başlanmamış
- **🔄 Devam Ediyor**: Aktif olarak çalışılıyor
- **✅ Tamamlandı**: Tamamlandı
- **🚫 Blokajlı**: Başka bir göreve bağımlı
- **❌ İptal Edildi**: İptal edildi

### Öncelik Sistemi

- **Öncelik 0:** Acil (Refactoring, Standart İhlalleri, Kritik Hatalar)
- **Öncelik 1:** Yüksek (Kritik Özellikler, Performans Sorunları)
- **Öncelik 2:** Yüksek (Önemli Özellikler)
- **Öncelik 3-8:** Orta/Düşük (İyileştirmeler, Dokümantasyon)

---

## Önemli Info Noktaları

### Proje Bilgileri
- **Proje Adı:** [PROJE ADI]
- **Çalışma Dizini:** [ÇALIŞMA DİZİNİ]
- **GitHub Repository:** [REPOSITORY URL]

### Teknik Stack
- **Backend:** [TEKNOLOJİ]
- **Frontend:** [TEKNOLOJİ]
- **Database:** [VERİTABANI]
- **Diğer:** [DİĞER TEKNOLOJİLER]

### Kritik Kurallar
- Tüm dosya isimleri İngilizce olmalı
- Virtual environment kullanılmalı (eğer Python projesi ise)
- Her değişiklik sonrası testler çalıştırılmalı
- Git commit/push sürekli yapılmalı
- Kod standardı korunmalı

---

## Güncelleme Notları

### [TARİH]
- Todo sistemi oluşturuldu
- Dosya yapısı ve kurallar tanımlandı
```

---

## 📄 master_next.md Şablonu

```markdown
# Sonraki Yapılacaklar

**Son Güncelleme:** [TARİH]

---

## Öncelikli Görevler

### Öncelik 0: Acil Görevler

#### [ ] **Görev:** [Görev başlığı]
  - Açıklama: [Detaylı açıklama]
  - Öncelik: 0 (Acil)
  - Tahmini Süre: [Süre]
  - Bağımlılıklar: [Diğer görevler]
  - Durum: 📋 Bekliyor

### Öncelik 1: Yüksek Öncelikli Görevler

#### [ ] **Görev:** [Görev başlığı]
  - Açıklama: [Detaylı açıklama]
  - Öncelik: 1 (Yüksek)
  - Tahmini Süre: [Süre]
  - Bağımlılıklar: [Diğer görevler]
  - Durum: 📋 Bekliyor

### Öncelik 2: Önemli Görevler

#### [ ] **Görev:** [Görev başlığı]
  - Açıklama: [Detaylı açıklama]
  - Öncelik: 2 (Önemli)
  - Tahmini Süre: [Süre]
  - Bağımlılıklar: [Diğer görevler]
  - Durum: 📋 Bekliyor

### Öncelik 3-8: Orta/Düşük Öncelikli Görevler

#### [ ] **Görev:** [Görev başlığı]
  - Açıklama: [Detaylı açıklama]
  - Öncelik: [3-8]
  - Tahmini Süre: [Süre]
  - Bağımlılıklar: [Diğer görevler]
  - Durum: 📋 Bekliyor

---

## Ertelenen Görevler

#### [ ] **Görev:** [Görev başlığı]
  - Açıklama: [Detaylı açıklama]
  - Öncelik: [Öncelik]
  - Ertelenme Nedeni: [Neden ertelendi]
  - Durum: ⏸️ Ertelendi

---

## Notlar

- Görevler öncelik sırasına göre listelenmelidir
- Her görev tamamlandığında master_done.md'ye taşınmalıdır
- Aktif görevler master_live.md'ye taşınmalıdır
```

---

## 📄 master_live.md Şablonu

```markdown
# Aktif Görevler (Şu Anda Yapılanlar)

**Son Güncelleme:** [TARİH]

---

## Aktif Görevler

### ⚡ [Görev Başlığı]
- **Görev:** [Görev başlığı]
- **Açıklama:** [Detaylı açıklama]
- **Öncelik:** [Öncelik] ([Açıklama])
- **Tahmini Süre:** [Süre]
- **Durum:** 🔄 Devam Ediyor
- **Başlangıç:** [TARİH]
- **Detaylar:** [İlgili dokümantasyon linki]
- **İmplementasyon:**
  - [ ] Alt görev 1
  - [ ] Alt görev 2
  - [ ] Alt görev 3
- **Durum:** 🔄 Devam Ediyor

---

## Notlar

- Aktif görevler buraya eklenecek
- Maksimum 2-3 aktif görev olmalı
- Her görev tamamlandığında `master_done.md`'ye taşınacak
```

---

## 📄 master_done.md Şablonu

```markdown
# Tamamlanan Görevler

**Oluşturulma Tarihi:** [TARİH]
**Son Güncelleme:** [TARİH]

---

## Tamamlanan Görevler Listesi

### [TARİH]

#### ✅ [Görev Başlığı] ([SAAT])
- **Görev:** [Görev başlığı]
- **Detaylar:**
  - ✅ Yapılan işlem 1
  - ✅ Yapılan işlem 2
  - ✅ Yapılan işlem 3
- **Dosyalar:**
  - `dosya1.py` - Açıklama
  - `dosya2.py` - Açıklama
- **Durum:** ✅ Tamamlandı

---

## İstatistikler

- **Toplam Tamamlanan Görev:** [SAYI]
- **Bu Ay Tamamlanan:** [SAYI]
- **Bu Hafta Tamamlanan:** [SAYI]
```

---

## 📄 START_HERE.md Şablonu

```markdown
# 🚀 PROJEYE DEVAM ETMEK İÇİN BAŞLANGIÇ NOKTASI

**Bu dosya AI asistanları ve geliştiriciler için hazırlanmıştır.**

---

## ⚡ Hızlı Başlangıç (30 Saniye)

### 1. Durum Kontrolü
```bash
# Projenin mevcut durumunu öğren
cat todo/master_live.md

# Bekleyen görevleri kontrol et
cat todo/master_next.md | grep -A 5 "\[ \]"
```

### 2. Çalışma Akışı
1. `master_live.md` dosyasını kontrol et (aktif görev var mı?)
2. `master_next.md` dosyasından en yüksek öncelikli görevi seç
3. Görevi `master_live.md`'ye taşı
4. Çalışmaya başla
5. Görev tamamlandığında `master_done.md`'ye taşı

### 3. Başla!
En yüksek öncelikli görevi seç ve çalışmaya başla.

---

## 📋 Okuma Sırası (Önemli!)

1. **`master.md`** - Genel bilgiler ve kurallar (2 dakika)
2. **`master_live.md`** - Aktif görevler (30 saniye)
3. **`master_next.md`** - Bekleyen görevler (2 dakika)
4. **`master_done.md`** - Tamamlanan görevler (referans)

---

## 🎯 Hemen Yapılacaklar

### Eğer Aktif Görev Yoksa:
1. `master_next.md`'yi aç
2. En yüksek öncelikli görevi seç
3. Görevi `master_live.md`'ye taşı
4. Çalışmaya başla

### Eğer Aktif Görev Varsa:
1. `master_live.md`'yi kontrol et
2. Aktif görevi tamamla
3. Görevi `master_done.md`'ye taşı
4. `master_next.md`'den yeni görev seç

---

## 🔍 Durum Kontrol Checklist

- [ ] `master.md` okundu mu?
- [ ] Aktif görevler kontrol edildi mi?
- [ ] Bekleyen görevler kontrol edildi mi?
- [ ] Sonraki görev seçildi mi?

---

## 📊 Proje Özeti

**Mevcut Durum:** [DURUM]
**Genel İlerleme:** [%]
**Son Görev:** [SON GÖREV]

---

## 🚨 Kritik Bilgiler

- **Çalışma Dizini:** [ÇALIŞMA DİZİNİ]
- **Git Repository:** [REPOSITORY URL]
- **Virtual Environment:** [ENV KONUMU] (aktif olmalı)

---

## 💡 İpuçları

1. **Küçük Adımlar:** Büyük görevleri parçalara böl
2. **Sık Commit:** Her önemli değişiklikte commit yap
3. **Dokümantasyon:** Her değişiklikte dokümantasyonu güncelle
4. **Test:** Yeni kod için test yaz
5. **Code Quality:** Linting ve formatting uygula

---

## 🔴 KRİTİK KURAL: Test ve Teyit Zorunluluğu

**ÖNEMLİ:** Agent, kullanıcıya teslim etmeden önce MUTLAKA test edip teyit etmelidir.

- ❌ **Test edilmemiş veya teyit edilmemiş hiçbir şey kullanıcıya verilmemelidir**
- ✅ Her implementasyon sonrası çalıştırılabilir testler yapılmalıdır
- ✅ API endpoint'leri test edilmeli ve çalıştığı doğrulanmalıdır
- ✅ Servis başlatma sonrası erişilebilirlik test edilmelidir
- ✅ Hata durumlarında kullanıcıya bilgi verilmemeli, önce düzeltilmelidir

**Test Adımları:**
1. Kod çalıştırılabilir mi? (syntax, import hataları)
2. Servis başlatılabiliyor mu?
3. Endpoint'ler erişilebilir mi?
4. Fonksiyonellik beklendiği gibi çalışıyor mu?
5. Hata durumları test edildi mi?
6. **Browser ile kullanılan özellikler için MANUEL BROWSER TESTİ ZORUNLUDUR**

---

## 🔴 KRİTİK KURAL: Tespitlerin Todo Sistemine Eklenmesi

**ÖNEMLİ:** Çalışmalar esnasında tespit edilen, gözden geçirilmesi gereken veya kontrol edilmesi gereken durumlar MUTLAKA `todo/master_next.md` dosyasına eklenmelidir.

**Kural:**
- ❌ **Hiçbir tespit gözden kaçırılmamalı veya atlanmamalıdır**
- ✅ Çalışma sırasında tespit edilen her şey `master_next.md`'ye eklenmelidir
- ✅ Mevcut çalışma dışı tespitler de eklenmelidir
- ✅ Refactoring ihtiyaçları, iyileştirme fırsatları, kontrol edilmesi gerekenler eklenmelidir
- ✅ Görevler öncelik sırasına göre eklenmelidir

---

## ✅ Projeye Devam Etme

**"projeye devam et" demeniz yeterlidir!**

Agent otomatik olarak:
1. ✅ Durum tespiti yapacak (`master_live.md`, `master_next.md`)
2. ✅ Aktif görevleri kontrol edecek (`master_live.md`)
3. ✅ Bekleyen görevleri seçecek (`master_next.md`)
4. ✅ Sorunsuz bir şekilde devam edecek

---

## 🆘 Yardım

- **Durum:** `todo/master.md`
- **Aktif Görevler:** `todo/master_live.md`
- **Bekleyen Görevler:** `todo/master_next.md`
- **Tamamlanan Görevler:** `todo/master_done.md`

---

**Son Güncelleme:** [TARİH]

**🎯 Şimdi başla: `cat todo/master_live.md`**
```

---

## 📝 Kullanım Notları

1. **Şablonları Kopyalayın:** Her şablonu kopyalayıp projenize göre düzenleyin
2. **Proje Bilgilerini Ekleyin:** Proje adı, dizin, repository gibi bilgileri ekleyin
3. **Kuralları Özelleştirin:** Projenize özel kurallar ekleyin
4. **İlk Görevleri Ekleyin:** master_next.md'ye ilk görevleri ekleyin

---

**Son Güncelleme:** 2025-12-10

