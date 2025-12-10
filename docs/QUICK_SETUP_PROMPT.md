# 🚀 Hızlı Kurulum - AI Çalışma Disiplini Prompt'u

**Kullanım:** Bu prompt'u yeni projenizde AI agent'a vererek todo sistemi ve çalışma disiplinini otomatik olarak kurabilirsiniz.

---

## 📋 AI Agent'a Verilecek Prompt

```
Merhaba! Projemde profesyonel bir AI çalışma disiplini kurmak istiyorum.
Aşağıdaki adımları takip ederek todo sistemi ve çalışma kurallarını oluştur:

## ADIM 1: Todo Klasörü Oluştur

Ana dizinde `todo/` klasörü oluştur.

## ADIM 2: Dosyaları Oluştur

`todo/` klasörü içerisine şu dosyaları oluştur:

1. **master.md** - Genel bilgiler, kurallar ve info noktaları
2. **master_next.md** - Yapılacak, bekleyen, ertelenen görevler (öncelik sırasına göre)
3. **master_live.md** - Şu anda yürütülen görevler
4. **master_done.md** - Tamamlanmış görevler
5. **START_HERE.md** - Projeye devam etmek için başlangıç noktası

## ADIM 3: master.md İçeriği

master.md dosyasına şu içeriği ekle:

- Proje bilgileri bölümü (proje adı, çalışma dizini, repository)
- Teknik stack bilgileri
- Kritik kurallar:
  * Kullanıcı ile Türkçe iletişim kurulacaktır
  * Tüm kodlar profesyonel standartlarda yazılacaktır
  * Her değişiklik sonrası testler çalıştırılacaktır
  * Git commit/push sürekli yapılacaktır
- Görev formatı standartları
- Öncelik sistemi (0: Acil, 1: Yüksek, 2: Önemli, 3-8: Orta/Düşük)
- Görev durumları (Bekliyor, Devam Ediyor, Tamamlandı, Blokajlı, İptal Edildi)

## ADIM 4: master_next.md İçeriği

master_next.md dosyasına şu yapıyı ekle:

- Öncelik 0: Acil Görevler bölümü
- Öncelik 1: Yüksek Öncelikli Görevler bölümü
- Öncelik 2: Önemli Görevler bölümü
- Öncelik 3-8: Orta/Düşük Öncelikli Görevler bölümü
- Ertelenen Görevler bölümü

Her görev şu formatta olmalı:
```markdown
- [ ] **Görev:** [Görev başlığı]
  - Açıklama: [Detaylı açıklama]
  - Öncelik: [0-8 arası sayı]
  - Tahmini Süre: [Süre]
  - Bağımlılıklar: [Diğer görevler]
  - Durum: 📋 Bekliyor
```

İlk görevler olarak şunları ekle:
- [ ] Proje yapısını analiz et ve dokümante et
- [ ] Mevcut kodları gözden geçir ve iyileştirme fırsatlarını tespit et
- [ ] Test altyapısını kur (eğer yoksa)
- [ ] README.md dosyasını güncelle

## ADIM 5: master_live.md İçeriği

master_live.md dosyasına şu yapıyı ekle:

- Aktif Görevler başlığı
- Maksimum 2-3 aktif görev olmalı
- Her görev için: başlık, açıklama, öncelik, durum, başlangıç tarihi, alt görevler

Görev formatı:
```markdown
### ⚡ [Görev Başlığı]
- **Görev:** [Görev başlığı]
- **Açıklama:** [Detaylı açıklama]
- **Öncelik:** [Öncelik]
- **Durum:** 🔄 Devam Ediyor
- **Başlangıç:** [TARİH]
- **İmplementasyon:**
  - [ ] Alt görev 1
  - [ ] Alt görev 2
```

## ADIM 6: master_done.md İçeriği

master_done.md dosyasına şu yapıyı ekle:

- Tamamlanan Görevler Listesi başlığı
- Tarih sırasına göre görevler
- Her görev için: başlık, tamamlanma tarihi, detaylar, yapılan değişiklikler

Görev formatı:
```markdown
#### ✅ [Görev Başlığı] ([SAAT])
- **Görev:** [Görev başlığı]
- **Detaylar:**
  - ✅ Yapılan işlem 1
  - ✅ Yapılan işlem 2
- **Dosyalar:**
  - `dosya1.py` - Açıklama
- **Durum:** ✅ Tamamlandı
```

## ADIM 7: START_HERE.md İçeriği

START_HERE.md dosyasına şu içeriği ekle:

- Hızlı Başlangıç bölümü (30 saniye)
- Okuma Sırası bölümü (hangi dosyaları sırayla okumalı)
- Hemen Yapılacaklar bölümü
- Durum Kontrol Checklist
- Kritik Kurallar özeti:
  * Test ve Teyit Zorunluluğu
  * Tespitlerin Todo Sistemine Eklenmesi
  * Projeye Devam Etme Kuralları

## ADIM 8: Çalışma Disiplini Kuralları

Aşağıdaki kuralları master.md dosyasına ekle:

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

### Todo Sistemi Kuralları:
- Aktif görevler maksimum 2-3 olmalı
- Görevler öncelik sırasına göre yönetilmeli
- Her görev tamamlandığında master_done.md'ye taşınmalı
- Tespit edilen tüm durumlar master_next.md'ye eklenmeli

### Proaktif Çalışma:
- Eksik testleri tespit edip yazmalı
- Dokümantasyon eksikliklerini tamamlamalı
- Code quality iyileştirmeleri yapmalı
- Standart ihlallerini tespit edip düzeltmeli

## ADIM 9: Git Yönetimi

- Her önemli değişiklikte commit yap
- Commit mesajları açıklayıcı olmalı
- Büyük değişikliklerden önce branch oluştur
- Testler geçtikten sonra push yap

## ADIM 10: Kontrol ve Onay

Her dosyayı oluşturduktan sonra:
1. İçeriğini göster
2. Kullanıcıdan onay al
3. Projeye özel bilgileri ekle (proje adı, dizin, repository vb.)

---

Lütfen bu adımları takip ederek todo sistemi ve çalışma disiplinini kur.
Her dosyayı oluşturduktan sonra içeriğini göster ve onay al.
```

---

## 📝 Kullanım Talimatları

1. **Yukarıdaki prompt'u kopyalayın**
2. **Yeni projenizde AI agent'a verin**
3. **Agent dosyaları oluşturduktan sonra kontrol edin**
4. **Projenize özel bilgileri ekleyin:**
   - Proje adı
   - Çalışma dizini
   - Repository URL
   - Teknik stack bilgileri

## 🔧 Özelleştirme İpuçları

- **Proje Adı:** Prompt'ta `[PROJE ADI]` yerine gerçek proje adınızı yazın
- **Çalışma Dizini:** `[ÇALIŞMA DİZİNİ]` yerine gerçek dizin yolunu yazın
- **Repository:** `[REPOSITORY URL]` yerine GitHub/GitLab URL'inizi yazın
- **Teknik Stack:** Projenize özel teknolojileri ekleyin

## ✅ Kontrol Listesi

Dosyalar oluşturulduktan sonra kontrol edin:

- [ ] `todo/` klasörü oluşturuldu mu?
- [ ] Tüm dosyalar oluşturuldu mu? (master.md, master_next.md, master_live.md, master_done.md, START_HERE.md)
- [ ] Proje bilgileri eklendi mi?
- [ ] İlk görevler eklendi mi?
- [ ] Kurallar tanımlandı mı?

---

**Son Güncelleme:** 2025-12-10

