# AI Çalışma Disiplini Kurulumu - Prompt

**Oluşturulma Tarihi:** 2025-12-10
**Amaç:** Bu prompt başka bir projede AI çalışma disiplinini kurmak için kullanılır

---

## 🎯 AI Agent'a Verilecek Prompt

Aşağıdaki prompt'u AI agent'a vererek projenizde todo sistemi ve çalışma disiplinini kurabilirsiniz:

---

```
Merhaba! Projemde profesyonel bir AI çalışma disiplini kurmak istiyorum.
Aşağıdaki adımları takip ederek todo sistemi ve çalışma kurallarını oluştur:

## 1. Todo Klasörü ve Dosya Yapısı Oluşturma

Ana dizinde `todo/` klasörü oluştur ve içerisine şu dosyaları ekle:

### Dosya Yapısı:
- `todo/master.md` - Genel bilgiler, kurallar ve info noktaları
- `todo/master_next.md` - Yapılacak, bekleyen, ertelenen görevler (öncelik sırasına göre)
- `todo/master_live.md` - Şu anda yürütülen görevler
- `todo/master_done.md` - Tamamlanmış görevler
- `todo/START_HERE.md` - Projeye devam etmek için başlangıç noktası

## 2. Dosya İçerikleri

Her dosyayı aşağıdaki şablonlara göre oluştur:

### master.md Şablonu:
- Proje bilgileri (ad, dizin, repository)
- Teknik stack bilgileri
- Kritik kurallar
- Görev formatı standartları
- Görev durumları (TODO, IN_PROGRESS, DONE, BLOCKED, CANCELLED)

### master_next.md Şablonu:
- Öncelik sırasına göre görevler (Öncelik 0: Acil, Öncelik 1: Yüksek, vb.)
- Her görev için: başlık, açıklama, öncelik, tahmini süre, bağımlılıklar
- Görevler checkbox formatında ([ ])

### master_live.md Şablonu:
- Şu anda aktif olarak çalışılan görevler (maksimum 2-3 görev)
- Her görev için: başlık, açıklama, öncelik, durum, başlangıç tarihi
- İlerleme takibi için alt görevler

### master_done.md Şablonu:
- Tamamlanan görevler tarih sırasına göre
- Her görev için: başlık, tamamlanma tarihi, detaylar, yapılan değişiklikler

### START_HERE.md Şablonu:
- Hızlı başlangıç rehberi (30 saniye)
- Okuma sırası (hangi dosyaları sırayla okumalı)
- Durum kontrol checklist
- Kritik kurallar özeti

## 3. Çalışma Disiplini Kuralları

Aşağıdaki kuralları `.cursorrules` dosyasına ekle veya `todo/master.md` dosyasına ekle:

### Genel Kurallar:
- Kullanıcı ile Türkçe iletişim kurulacaktır
- Tüm kodlar profesyonel standartlarda yazılacaktır
- Her değişiklik sonrası testler çalıştırılacaktır
- Tüm önemli değişiklikler dokümante edilecektir
- Git commit/push sürekli yapılacaktır

### Todo Sistemi Kuralları:
- Aktif görevler maksimum 2-3 olmalı
- Görevler öncelik sırasına göre yönetilmeli
- Her görev tamamlandığında master_done.md'ye taşınmalı
- Tespit edilen tüm durumlar master_next.md'ye eklenmeli

### Projeye Devam Etme Kuralları:
- "projeye devam et" komutu verildiğinde:
  1. START_HERE.md dosyasını oku
  2. master_live.md'yi kontrol et (aktif görev var mı?)
  3. master_next.md'den en yüksek öncelikli görevi seç
  4. Görevi master_live.md'ye taşı
  5. Çalışmaya başla
  6. Görev tamamlandığında master_done.md'ye taşı

### Test ve Teyit Kuralları:
- Test edilmemiş hiçbir şey kullanıcıya verilmemeli
- Her implementasyon sonrası testler yapılmalı
- Browser ile kullanılan özellikler için manuel browser testi zorunlu
- External erişim gereken özellikler için external test zorunlu

## 4. İlk Görevler

master_next.md dosyasına şu ilk görevleri ekle:

- [ ] Proje yapısını analiz et ve dokümante et
- [ ] Mevcut kodları gözden geçir ve iyileştirme fırsatlarını tespit et
- [ ] Test altyapısını kur (eğer yoksa)
- [ ] README.md dosyasını güncelle

## 5. Öncelik Sistemi

Öncelik sistemi şu şekilde olmalı:
- **Öncelik 0:** Acil (Refactoring, Standart İhlalleri, Kritik Hatalar)
- **Öncelik 1:** Yüksek (Kritik Özellikler, Performans Sorunları)
- **Öncelik 2:** Yüksek (Önemli Özellikler)
- **Öncelik 3-8:** Orta/Düşük (İyileştirmeler, Dokümantasyon)

## 6. Görev Formatı

Her görev şu formatta olmalı:

```markdown
- [ ] **Görev:** [Görev başlığı]
  - Açıklama: [Detaylı açıklama]
  - Öncelik: [0-8 arası sayı]
  - Tahmini Süre: [Süre]
  - Bağımlılıklar: [Diğer görevler]
  - Durum: 📋 Bekliyor / 🔄 Devam Ediyor / ✅ Tamamlandı
```

## 7. Checkpoint Sistemi

Her önemli adımda checkpoint oluştur:
- Görev tamamlandığında
- Büyük değişikliklerden önce
- Testler geçtiğinde

Checkpoint formatı: `CP-YYYYMMDD-HHMM`

## 8. Proaktif Çalışma

Agent şu konularda proaktif olmalı:
- Eksik testleri tespit edip yazmalı
- Dokümantasyon eksikliklerini tamamlamalı
- Code quality iyileştirmeleri yapmalı
- Standart ihlallerini tespit edip düzeltmeli
- Tespit edilen durumları master_next.md'ye eklemeli

## 9. Git Yönetimi

- Her önemli değişiklikte commit yap
- Commit mesajları açıklayıcı olmalı
- Büyük değişikliklerden önce branch oluştur
- Testler geçtikten sonra push yap

## 10. Dokümantasyon

- Her önemli değişiklik dokümante edilmeli
- Kod dosyalarına oluşturulma tarihi ve açıklama eklenmeli
- API değişiklikleri dokümante edilmeli
- Test senaryoları dokümante edilmeli

---

Lütfen bu adımları takip ederek todo sistemi ve çalışma disiplinini kur.
Her dosyayı oluşturduktan sonra içeriğini göster ve onay al.
```

---

## 📋 Kullanım Talimatları

1. **Yukarıdaki prompt'u kopyalayın**
2. **Yeni projenizde AI agent'a verin**
3. **Agent dosyaları oluşturduktan sonra kontrol edin**
4. **Projenize özel bilgileri ekleyin** (proje adı, dizin, repository vb.)

## 🔧 Özelleştirme

Prompt'u projenize göre özelleştirebilirsiniz:
- Proje adını değiştirin
- Teknik stack bilgilerini ekleyin
- Özel kurallar ekleyin
- İlk görevleri projenize göre düzenleyin

## 📝 Notlar

- Bu prompt genel bir şablondur
- Projenize özel kurallar ekleyebilirsiniz
- Todo sistemi zamanla geliştirilebilir
- Checkpoint sistemi proje ilerlemesini takip etmek için önemlidir

---

**Son Güncelleme:** 2025-12-10

