# AI Çalışma Akışı ve Otonom Proje Yönetimi

**Oluşturulma Tarihi:** 2025-12-08 18:35:00  
**Son Güncelleme:** 2025-12-08 18:35:00  
**Version:** 1.0.0

---

## 🎯 Amaç

Bu dokümantasyon, AI asistanlarının (şimdi veya gelecekte) projeye devam ettiğinde:
1. Nerede kaldığını anlaması
2. Bekleyen görevleri aktif hale getirmesi
3. Proaktif çalışması
4. Projeyi ilerletmesi

için hazırlanmıştır.

---

## 📋 Çalışma Akışı

### 1. Projeye Başlarken (İlk Adımlar)

#### Adım 1: Durum Tespiti (Verimli Okuma)
```bash
# Bu dosyaları SIRAYLA ve VERİMLİ oku:
1. todo/START_HERE.md         # Özet ve kritik kurallar (İLK OKUNACAK)
2. todo/checkpoint.md         # Son checkpoint (nerede kaldık?)
3. todo/master_live.md        # Aktif görevler (varsa)
4. todo/master_next.md        # Bekleyen görevler (öncelikli)

# Bu dosyalar SADECE İHTİYAÇ HALİNDE okunmalıdır:
- todo/project_state.md       # Detaylı durum gerektiğinde
- todo/master_done.md         # Tamamlanan görevler gerektiğinde
- todo/expert_recommendations.md  # Öneriler gerektiğinde
```

#### Adım 2: Durum Analizi
- Son yapılan işleri kontrol et (`project_state.md`)
- Aktif görevleri kontrol et (`master_live.md`)
- Bekleyen görevleri kontrol et (`master_next.md`)
- Blokajları ve riskleri kontrol et (`project_state.md`)

#### Adım 3: Görev Seçimi
- Öncelik sırasına göre görev seç
- Bağımlılıkları kontrol et
- Görevi `master_live.md`'ye taşı

---

## 🔄 Otonom Çalışma Kuralları

### Kural 1: Görev Aktarımı
```
master_next.md (Bekleyen)
    ↓ [Görev başlatıldığında]
master_live.md (Aktif)
    ↓ [Görev tamamlandığında]
master_done.md (Tamamlandı)
```

### Kural 2: Görev Başlatma Kriterleri
Bir görevi aktif hale getirmek için:
1. ✅ Öncelikli olmalı (Yüksek/Kritik)
2. ✅ Bağımlılıkları tamamlanmış olmalı
3. ✅ Aktif görev sayısı 2-3'ü geçmemeli
4. ✅ Gerekli kaynaklar mevcut olmalı

### Kural 3: Proaktif ama Odaklı Çalışma
AI asistanı şunları yapmalı:
- ✅ Bekleyen görevleri kontrol et (görev seçimi için)
- ✅ Blokajları tespit et ve çöz (görev tamamlanamazsa)
- ✅ Eksik dokümantasyonu tamamla (görev tamamlandığında)
- ✅ Test coverage'ı artır (görev kapsamında)
- ✅ Code quality iyileştir (görev kapsamında)
- ✅ Güvenlik açıklarını tespit et (görev kapsamında)

**ÖNEMLİ:** Görev sırasında tespit edilen diğer konular `master_next.md`'ye eklenmeli, hemen ele alınmamalıdır. Odak kaybetmemelidir.

### Kural 4: Checkpoint Sistemi
Her önemli adımda:
1. `project_state.md` dosyasını güncelle
2. Yapılan işleri `master_done.md`'ye ekle
3. Git commit yap (anlamlı commit mesajı ile)
4. GitHub'a push et

---

## 📝 Görev Yönetimi Adımları

### Görev Başlatma
```markdown
1. master_next.md'den görevi seç
2. Görevi master_live.md'ye kopyala
3. master_next.md'den görevi sil veya [ ] işaretini kaldır
4. master_live.md'de görevi [IN_PROGRESS] olarak işaretle
5. project_state.md'yi güncelle (Devam Eden İşler bölümüne ekle)
```

### Görev Tamamlama
```markdown
1. Görevi master_live.md'den master_done.md'ye taşı
2. Tamamlanma tarihi ve detayları ekle
3. master_live.md'yi temizle
4. project_state.md'yi güncelle:
   - Tamamlanan İşler bölümüne ekle
   - Son Yapılan İşlemler bölümüne ekle
   - İlerleme Metrikleri'ni güncelle
5. Git commit ve push
```

### Yeni Görev Ekleme
```markdown
1. master_next.md'ye görevi ekle
2. Öncelik, tahmini süre, bağımlılıklar belirt
3. project_state.md'yi güncelle (Bekleyen İşler bölümüne ekle)
```

---

## 🎯 Proaktif Çalışma Senaryoları

### Senaryo 1: Yeni Görev Yok
**Durum:** `master_live.md` boş, `master_next.md`'de görevler var

**Aksiyon:**
1. `master_next.md`'den en yüksek öncelikli görevi seç
2. Bağımlılıkları kontrol et
3. Görevi aktif hale getir (`master_live.md`)
4. Görevi başlat ve tamamla

### Senaryo 2: Aktif Görev Var
**Durum:** `master_live.md`'de görev var

**Aksiyon:**
1. Aktif görevi kontrol et
2. Görevi tamamla veya devam et
3. Blokaj varsa çöz veya dokümante et
4. Tamamlandıysa `master_done.md`'ye taşı

### Senaryo 3: Blokaj Var
**Durum:** Görev başka bir şeye bağımlı

**Aksiyon:**
1. Blokajı `project_state.md`'ye ekle
2. Bağımlılığı çöz veya bekleyen görevi önceliklendir
3. Alternatif görev seç (bağımlılığı olmayan)

### Senaryo 4: Test Eksik
**Durum:** Yeni kod eklendi ama test yok

**Aksiyon:**
1. İlgili test dosyası var mı kontrol et
2. Varsa sadece o test dosyasını çalıştır (`pytest tests/test_ilgili_dosya.py`)
3. Yeni kod için testler yaz (görev kapsamında)
4. **ÖNEMLİ:** Test zamanlaması kurallarına uy ([`.cursorrules`](../.cursorrules) dosyasına bakınız)

### Senaryo 5: Dokümantasyon Eksik
**Durum:** Yeni özellik eklendi ama dokümante edilmemiş

**Aksiyon:**
1. `project_info_20251208_145614.md`'yi güncelle
2. API dokümantasyonunu güncelle
3. README'yi güncelle (varsa)
4. Code comments ekle

---

## 🔍 Durum Kontrol Checklist

Her çalışma oturumunda kontrol et (Verimli):

- [ ] `START_HERE.md` okundu mu? (özet)
- [ ] `checkpoint.md` okundu mu? (son checkpoint)
- [ ] `master_live.md` kontrol edildi mi? (aktif görevler)
- [ ] `master_next.md` kontrol edildi mi? (öncelikli görevler)
- [ ] Görev seçildi mi ve başlatıldı mı?
- [ ] Görev tamamlandığında Git commit yapıldı mı?
- [ ] GitHub'a push edildi mi?

**NOT:** `project_state.md` sadece detaylı durum gerektiğinde okunmalıdır.

---

## 📊 Görev Önceliklendirme

### Öncelik Sırası
1. **Kritik** - Sistemin çalışması için gerekli
2. **Yüksek** - Önemli özellikler veya iyileştirmeler
3. **Orta** - İyi olur ama acil değil
4. **Düşük** - Gelecekte yapılabilir

### Öncelik Belirleme Kriterleri
- **Kritik:** Test altyapısı, logging, güvenlik
- **Yüksek:** API testleri, code quality, CI/CD
- **Orta:** Monitoring, dokümantasyon iyileştirme
- **Düşük:** Nice-to-have özellikler

---

## 🚀 Hızlı Başlangıç Komutları

### Durum Kontrolü
```bash
# Proje durumunu kontrol et
cat todo/project_state.md | head -50

# Aktif görevleri kontrol et
cat todo/master_live.md

# Bekleyen görevleri kontrol et
cat todo/master_next.md | grep -A 5 "\[ \]"
```

### Görev Başlatma
```bash
# 1. master_next.md'yi oku
# 2. Görevi seç
# 3. master_live.md'ye ekle
# 4. Çalışmaya başla
```

### Görev Tamamlama
```bash
# 1. Görevi master_done.md'ye taşı
# 2. project_state.md'yi güncelle
# 3. Git commit ve push
git add todo/
git commit -m "Görev tamamlandı: [Görev adı]"
git push origin main
```

---

## 📝 Örnek Çalışma Akışı

### Örnek 1: Test Altyapısı Kurulumu

```markdown
1. [Durum Tespiti]
   - project_state.md okundu
   - Test altyapısı eksik tespit edildi
   - Öncelik: Kritik

2. [Görev Başlatma]
   - master_next.md'den "Test Altyapısı Kurulumu" görevi seçildi
   - master_live.md'ye eklendi
   - project_state.md güncellendi

3. [Çalışma]
   - pytest kuruldu
   - Test yapısı oluşturuldu (tests/ klasörü)
   - İlk testler yazıldı
   - Test coverage %30'a çıktı

4. [Tamamlama]
   - master_done.md'ye taşındı
   - project_state.md güncellendi
   - Git commit ve push yapıldı
```

---

## 🎓 Best Practices

### 1. Küçük Adımlar
- Büyük görevleri küçük parçalara böl
- Her parçayı tamamla ve commit et
- İlerlemeyi dokümante et

### 2. Dokümantasyon
- Her önemli değişiklikte dokümantasyonu güncelle
- Commit mesajlarında ne yapıldığını açıkla
- Kod comments ekle

### 3. Test
- Yeni kod için test yaz
- Mevcut kod için test coverage artır
- Testler başarısız olursa düzelt

### 4. Code Quality
- Linting hatalarını düzelt
- Code formatting uygula
- Type hints ekle

### 5. Git Workflow
- Anlamlı commit mesajları kullan
- Küçük ve sık commit yap
- Her commit'te push et

---

## 🔄 Sürekli İyileştirme

### Her Çalışma Sonrası
1. Ne öğrenildi?
2. Ne iyileştirilebilir?
3. Sonraki adımlar neler?
4. Blokajlar var mı?

### Haftalık Değerlendirme
1. İlerleme metrikleri kontrol et
2. Tamamlanan görevleri gözden geçir
3. Yeni görevler ekle
4. Öncelikleri gözden geçir

---

## 📞 Yardım ve Destek

### Sorun Çözme
1. `project_state.md`'deki blokajları kontrol et
2. `expert_recommendations.md`'deki önerilere bak
3. `project_info_20251208_145614.md`'deki bilgilere bak
4. Git history'yi kontrol et

### Yeni AI Asistanı İçin
1. Bu dosyayı oku
2. `project_state.md`'yi oku
3. `master_live.md` ve `master_next.md`'yi kontrol et
4. En yüksek öncelikli görevi seç ve başlat

---

**Son Güncelleme:** 2025-12-08 18:35:00

