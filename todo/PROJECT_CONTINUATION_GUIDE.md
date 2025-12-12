# Projeye Devam Etme Rehberi - Agent İçin

**Oluşturulma Tarihi:** 2025-12-09 23:00:00  
**Son Güncelleme:** 2025-12-09 23:00:00  
**Version:** 1.0.0  
**Durum:** ✅ Aktif

---

## 🎯 Amaç

Bu rehber, kullanıcı "projeye devam et" veya benzeri bir komut verdiğinde Agent'ın:
1. Projenin durumunu hızlıca anlaması
2. Nerede kaldığını tespit etmesi
3. Bekleyen görevleri aktif hale getirmesi
4. Sorunsuz bir şekilde devam etmesi

için hazırlanmıştır.

---

## ✅ Sistem Durumu: HAZIR

**Evet, "projeye devam et" demeniz yeterlidir!**

Agent şu adımları otomatik olarak takip edecektir:

---

## 📋 Agent'ın İzleyeceği Adımlar

### Adım 1: Durum Tespiti (ZORUNLU - Verimli Okuma)

**ÖNEMLİ:** Gereksiz dosya okuma yapma! Sadece gerekli bilgileri oku.

Agent şu dosyaları **sırayla ve verimli** okuyacaktır:

1. **`todo/START_HERE.md`** ⭐ İLK OKUNACAK (Sadece özet - ~2 dakika)
   - Hızlı başlangıç rehberi
   - Kritik kurallar özeti
   - Okuma sırası

2. **`todo/checkpoint.md`** 📍 Nerede Kaldık? (Sadece son checkpoint - ~30 saniye)
   - Son checkpoint bilgisi
   - Son tamamlanan iş
   - Sonraki yapılacaklar

3. **`todo/master_live.md`** 🔄 Aktif Görevler (Sadece aktif görevler - ~1 dakika)
   - Şu anda yapılan görevler varsa
   - Görev detayları ve ilerleme durumu

4. **`todo/master_next.md`** 📋 Bekleyen Görevler (Sadece öncelikli görevler - ~2 dakika)
   - En yüksek öncelikli görevler
   - Bağımlılıklar
   - Tahmini süreler

**NOT:** `todo/project_state.md` dosyası sadece detaylı durum gerektiğinde okunmalıdır. Her seferinde okunması gereksiz token harcamasıdır.

### Adım 2: Görev Seçimi

Agent şu mantıkla görev seçecektir:

1. **Aktif Görev Kontrolü (`master_live.md`):**
   - ✅ Aktif görev var mı kontrol et
   - ✅ Aktif görevin durumunu kontrol et:
     - **"Devam Ediyor"** → Aktif görevle devam et
     - **"Bekliyor"** veya **"Hazırlanıyor"** → Öncelik karşılaştırması yap

2. **Öncelik Karşılaştırması:**
   - ✅ Aktif görevin önceliğini kontrol et
   - ✅ `master_next.md`'deki en yüksek öncelikli görevi kontrol et
   - ✅ **Eğer `master_next.md`'deki görev daha yüksek öncelikli ise (Öncelik 0 > Öncelik 1):**
     - Aktif görevi `master_next.md`'ye geri taşı (durum: Bekliyor)
     - Yüksek öncelikli görevi `master_live.md`'ye taşı
     - Yüksek öncelikli görevle devam et
   - ✅ **Eğer aktif görev daha yüksek öncelikli ise:**
     - Aktif görevle devam et

3. **Aktif Görev Yoksa:**
   - ✅ `master_next.md`'den en yüksek öncelikli görevi seçer
   - ✅ Bağımlılıkları kontrol eder
   - ✅ Görevi `master_live.md`'ye taşır
   - ✅ `project_state.md`'yi günceller

**Öncelik Sırası (Sayısal - Küçük = Yüksek Öncelik):**
- **Öncelik 0** (Acil) > **Öncelik 1** (Yüksek) > **Öncelik 2** (Yüksek) > **Öncelik 3-8** (Orta/Düşük)

### Adım 3: Çalışma

Agent şu kurallara uygun çalışacaktır:

1. **`todo/ai_workflow.md`** dosyasındaki kurallara uyar
2. **Proaktif ama odaklı çalışır:**
   - Blokajları çözer (görev tamamlanamazsa)
   - Eksik testleri yazar (görev kapsamında)
   - Dokümantasyonu günceller (görev tamamlandığında)
   - Standartlara uygunluğu kontrol eder (görev tamamlandığında)

3. **Kritik kurallara uyar:**
   - Test zamanlaması kurallarına uyar ([`.cursorrules`](../.cursorrules) dosyasına bakınız)
   - Browser test zorunluluğu (sadece browser özellikleri için)
   - External erişim test zorunluluğu (sadece external özellikler için)
   - Tespitlerin todo sistemine eklenmesi (görev sırasında tespit edilenler eklenir, hemen ele alınmaz)
   - Yedekleme ve geri dönüş standartları (refactoring öncesi)
   - Workspace yönetimi standartları (commit öncesi kontrol)

### Adım 4: Tamamlama

Görev tamamlandığında:

1. ✅ Görevi `master_done.md`'ye taşır
2. ✅ `project_state.md`'yi günceller
3. ✅ `checkpoint.md`'yi günceller
4. ✅ Git commit ve push yapar

### Adım 5: Devam

Eğer daha fazla görev varsa:

1. ✅ Bir sonraki görevi seçer
2. ✅ Proaktif olarak eksiklikleri tespit eder
3. ✅ Test eksikliği, dokümantasyon eksikliği, code quality iyileştirmeleri yapar

---

## 🔍 Agent'ın Kontrol Edeceği Dosyalar

### Zorunlu Okuma (Sırayla - Verimli)

1. ✅ `todo/START_HERE.md` - İlk okunacak (özet)
2. ✅ `todo/checkpoint.md` - Nerede kaldık? (son checkpoint)
3. ✅ `todo/master_live.md` - Aktif görevler (varsa)
4. ✅ `todo/master_next.md` - Bekleyen görevler (öncelikli)

**NOT:** `todo/project_state.md` sadece detaylı durum gerektiğinde okunmalıdır.

### Referans Dosyalar (Sadece İhtiyaç Halinde)

- `.cursorrules` - Proje kuralları (detaylı kurallar için)
- `project_info_20251208_145614.md` - Proje bilgileri (proje hakkında bilgi gerektiğinde)
- Diğer dosyalar sadece spesifik ihtiyaç olduğunda okunmalıdır

---

## ✅ Sistem Kontrolü

### Mevcut Sistem Durumu

#### ✅ Hazır Olanlar
- ✅ `todo/START_HERE.md` - Hızlı başlangıç rehberi
- ✅ `todo/checkpoint.md` - Checkpoint sistemi
- ✅ `todo/project_state.md` - Proje durumu
- ✅ `todo/master_live.md` - Aktif görevler
- ✅ `todo/master_next.md` - Bekleyen görevler
- ✅ `todo/ai_workflow.md` - Çalışma akışı
- ✅ `.cursorrules` - Otonom proje yönetimi kuralları

#### ✅ Kurallar
- ✅ Test ve teyit zorunluluğu
- ✅ Browser test zorunluluğu
- ✅ External erişim test zorunluluğu
- ✅ Tespitlerin todo sistemine eklenmesi
- ✅ Yedekleme ve geri dönüş standartları
- ✅ Workspace yönetimi standartları
- ✅ Kod ve dokümantasyon boyut standartları

#### ✅ Standartlar
- ✅ Kod standartları
- ✅ Dokümantasyon standartları
- ✅ Yedekleme standartları
- ✅ Workspace yönetimi standartları

---

## 🎯 Kullanım Senaryosu

### Senaryo: Yeni Chat Oturumu

**Kullanıcı:** "projeye devam et"

**Agent'ın Yapacağılar:**

1. **Durum Tespiti (Otomatik - Verimli)**
   ```
   ✅ todo/START_HERE.md okunur (özet)
   ✅ todo/checkpoint.md okunur (son checkpoint)
   ✅ todo/master_live.md kontrol edilir (aktif görevler)
   ✅ todo/master_next.md kontrol edilir (öncelikli görevler)
   ⚠️ todo/project_state.md sadece detay gerektiğinde okunur
   ```

2. **Durum Özeti (Kullanıcıya Sunulur)**
   ```
   📍 Son Checkpoint: CP-20251209-005
   📊 Proje Durumu: Çok İyi (8.5/10)
   🔄 Aktif Görev: Event Detection Modülü (Bekliyor)
   📋 Sonraki Görev: Event Detection Modülü (Öncelik 1)
   ```

3. **Görev Seçimi (Otomatik)**
   ```
   ✅ Aktif görev yok
   ✅ master_next.md'den Event Detection Modülü seçilir
   ✅ master_live.md'ye taşınır
   ✅ project_state.md güncellenir
   ```

4. **Çalışmaya Başlama (Otomatik)**
   ```
   ✅ Görev başlatılır
   ✅ Gerekli dosyalar okunur
   ✅ Çalışmaya başlanır
   ```

---

## ✅ Sonuç

**Evet, "projeye devam et" demeniz yeterlidir!**

Agent:
- ✅ Projenin durumunu anlayacak
- ✅ Nerede kaldığını tespit edecek
- ✅ Bekleyen görevleri aktif hale getirecek
- ✅ Sorunsuz bir şekilde devam edecek
- ✅ Tüm kurallara ve standartlara uygun çalışacak

**Sistem Hazır ve Aktif!** 🚀

---

## 📝 Notlar

- Agent her zaman `todo/START_HERE.md` dosyasını ilk okumalıdır (özet için)
- Agent projenin ne olduğunu anlamak için `project_info_20251208_145614.md` dosyasını referans almalıdır (sadece proje hakkında bilgi gerektiğinde)
- Agent gelinen noktadan daha ileri gitmek için `master_next.md` dosyasındaki görevleri takip etmelidir
- Agent her zaman proaktif çalışmalıdır ancak odak kaybetmemelidir (eksiklikleri tespit edip `master_next.md`'ye eklemeli, hemen ele almamalı)
- Agent görevleri tamamladıkça todo sistemini güncellemelidir
- Agent gereksiz dosya okuma, gereksiz test çalıştırma veya gereksiz işlem yapmamalıdır

---

**Son Güncelleme:** 2025-12-09 23:00:00

