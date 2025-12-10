# AI Çalışma Disiplini Kurulum Rehberi

**Oluşturulma Tarihi:** 2025-12-10
**Amaç:** Bu rehber, mevcut projedeki AI çalışma disiplinini başka bir projede nasıl uygulayacağınızı açıklar.

---

## 📚 Hazırlanan Dosyalar

Bu klasörde şu dosyalar hazırlanmıştır:

1. **`QUICK_SETUP_PROMPT.md`** ⭐ **BAŞLANGIÇ İÇİN BUNU KULLANIN**
   - Kısa ve direkt kullanılabilir prompt
   - AI agent'a direkt verilebilir
   - Adım adım kurulum talimatları

2. **`AI_WORKFLOW_SETUP_PROMPT.md`**
   - Detaylı açıklamalı prompt
   - Her adım için açıklamalar içerir
   - Daha fazla bilgi gerektiğinde kullanılabilir

3. **`TODO_SYSTEM_TEMPLATES.md`**
   - Tüm dosya şablonları
   - Manuel kurulum için kullanılabilir
   - Şablonları kopyalayıp düzenleyebilirsiniz

4. **`AI_WORKFLOW_SETUP_README.md`** (bu dosya)
   - Genel kullanım rehberi
   - Hızlı başlangıç talimatları

---

## 🚀 Hızlı Başlangıç

### Yöntem 1: AI Agent ile Otomatik Kurulum (Önerilen)

1. **`QUICK_SETUP_PROMPT.md`** dosyasını açın
2. İçeriğini kopyalayın
3. Yeni projenizde AI agent'a verin
4. Agent dosyaları oluşturduktan sonra kontrol edin
5. Projenize özel bilgileri ekleyin

### Yöntem 2: Manuel Kurulum

1. **`TODO_SYSTEM_TEMPLATES.md`** dosyasını açın
2. Her şablonu kopyalayın
3. `todo/` klasörü oluşturun
4. Her dosyayı oluşturup şablonları yapıştırın
5. Projenize özel bilgileri ekleyin

---

## 📋 Todo Sistemi Yapısı

```
todo/
├── master.md           # Genel bilgiler ve kurallar
├── master_next.md      # Bekleyen görevler (öncelik sırasına göre)
├── master_live.md      # Aktif görevler (maksimum 2-3)
├── master_done.md      # Tamamlanan görevler
└── START_HERE.md       # Başlangıç rehberi
```

---

## 🎯 Temel Kullanım

### 1. Projeye Devam Etme

AI agent'a "projeye devam et" dediğinizde:

1. `START_HERE.md` dosyasını okur
2. `master_live.md` dosyasını kontrol eder (aktif görev var mı?)
3. `master_next.md` dosyasından en yüksek öncelikli görevi seçer
4. Görevi `master_live.md`'ye taşır
5. Çalışmaya başlar
6. Görev tamamlandığında `master_done.md`'ye taşır

### 2. Yeni Görev Ekleme

Yeni bir görev eklemek için:

1. `master_next.md` dosyasını açın
2. Uygun öncelik bölümüne görevi ekleyin
3. Görev formatına uygun şekilde yazın

### 3. Görev Yönetimi

- **Aktif Görev:** `master_live.md` dosyasına taşıyın
- **Tamamlanan Görev:** `master_done.md` dosyasına taşıyın
- **Ertelenen Görev:** `master_next.md` dosyasında "Ertelenen Görevler" bölümüne ekleyin

---

## 📊 Öncelik Sistemi

- **Öncelik 0:** Acil (Refactoring, Standart İhlalleri, Kritik Hatalar)
- **Öncelik 1:** Yüksek (Kritik Özellikler, Performans Sorunları)
- **Öncelik 2:** Yüksek (Önemli Özellikler)
- **Öncelik 3-8:** Orta/Düşük (İyileştirmeler, Dokümantasyon)

---

## 🔴 Kritik Kurallar

### Test ve Teyit Zorunluluğu
- Test edilmemiş hiçbir şey kullanıcıya verilmemeli
- Her implementasyon sonrası testler yapılmalı
- Browser ile kullanılan özellikler için manuel browser testi zorunlu

### Tespitlerin Todo Sistemine Eklenmesi
- Çalışma sırasında tespit edilen her şey `master_next.md`'ye eklenmeli
- Refactoring ihtiyaçları, iyileştirme fırsatları eklenmeli
- Görevler öncelik sırasına göre eklenmeli

### Proaktif Çalışma
- Eksik testleri tespit edip yazmalı
- Dokümantasyon eksikliklerini tamamlamalı
- Code quality iyileştirmeleri yapmalı
- Standart ihlallerini tespit edip düzeltmeli

---

## 📝 Görev Formatı

Her görev şu formatta olmalıdır:

```markdown
- [ ] **Görev:** [Görev başlığı]
  - Açıklama: [Detaylı açıklama]
  - Öncelik: [0-8 arası sayı]
  - Tahmini Süre: [Süre]
  - Bağımlılıklar: [Diğer görevler]
  - Durum: 📋 Bekliyor / 🔄 Devam Ediyor / ✅ Tamamlandı
```

---

## 🔧 Özelleştirme

### Projeye Özel Bilgiler Ekleme

1. **master.md** dosyasını açın
2. "Proje Bilgileri" bölümünü düzenleyin:
   - Proje adı
   - Çalışma dizini
   - Repository URL
3. "Teknik Stack" bölümünü düzenleyin:
   - Backend teknolojileri
   - Frontend teknolojileri
   - Database
   - Diğer teknolojiler

### Özel Kurallar Ekleme

1. **master.md** dosyasını açın
2. "Kritik Kurallar" bölümüne projenize özel kurallar ekleyin
3. **START_HERE.md** dosyasına da önemli kuralları ekleyin

---

## ✅ Kontrol Listesi

Kurulum sonrası kontrol edin:

- [ ] `todo/` klasörü oluşturuldu mu?
- [ ] Tüm dosyalar oluşturuldu mu?
- [ ] Proje bilgileri eklendi mi?
- [ ] Teknik stack bilgileri eklendi mi?
- [ ] İlk görevler eklendi mi?
- [ ] Kurallar tanımlandı mı?
- [ ] Git repository bağlantısı yapıldı mı?

---

## 🆘 Sorun Giderme

### Dosyalar Oluşturulmadı

- AI agent'a prompt'u tekrar verin
- Manuel olarak `TODO_SYSTEM_TEMPLATES.md` dosyasındaki şablonları kullanın

### Görevler Düzenlenmiyor

- Dosya formatını kontrol edin
- Görev formatına uygun şekilde yazıldığından emin olun

### Öncelik Sistemi Çalışmıyor

- Öncelik numaralarını kontrol edin (0-8 arası)
- Öncelik sırasının doğru olduğundan emin olun

---

## 📚 Ek Kaynaklar

- **Mevcut Proje Örneği:** `/home/basar/charger/todo/` klasörüne bakınız
- **Detaylı Şablonlar:** `TODO_SYSTEM_TEMPLATES.md` dosyasına bakınız
- **Detaylı Prompt:** `AI_WORKFLOW_SETUP_PROMPT.md` dosyasına bakınız

---

## 💡 İpuçları

1. **Küçük Başlayın:** İlk başta basit görevlerle başlayın
2. **Düzenli Güncelleyin:** Todo dosyalarını düzenli olarak güncelleyin
3. **Checkpoint Kullanın:** Önemli adımlarda checkpoint oluşturun
4. **Proaktif Olun:** Tespit edilen durumları hemen ekleyin
5. **Dokümante Edin:** Her önemli değişikliği dokümante edin

---

## 🎯 Sonraki Adımlar

1. ✅ Todo sistemi kuruldu
2. ⏭️ İlk görevleri ekleyin
3. ⏭️ Projeye özel kuralları ekleyin
4. ⏭️ AI agent'a "projeye devam et" deyin
5. ⏭️ Çalışmaya başlayın!

---

**Son Güncelleme:** 2025-12-10

**🎯 Başlamak için: `QUICK_SETUP_PROMPT.md` dosyasını açın ve prompt'u kopyalayın!**

