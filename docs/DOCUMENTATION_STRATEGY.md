# Dokümantasyon Stratejisi - Single Source of Truth & Multi-Expert

**Oluşturulma Tarihi:** 2025-12-12 10:00:00
**Son Güncelleme:** 2025-12-12 10:00:00
**Version:** 1.0.0
**Durum:** ✅ Aktif

---

## 🎯 Strateji Prensipleri

### Single Source of Truth (Tek Kaynak Gerçeklik)

**KRİTİK KURAL:** Her bilgi sadece bir yerde bulunmalıdır. Tekrar yasaktır.

**Prensipler:**
1. ✅ Her konu için tek bir ana kaynak dosya belirlenir
2. ✅ Diğer dosyalar sadece referans verir (link ile)
3. ✅ Bilgi güncellendiğinde sadece ana kaynak güncellenir
4. ✅ Tekrar eden bilgiler kaldırılır ve referans ile değiştirilir

### Multi-Expert Stratejisi

**KRİTİK KURAL:** Birden fazla expert agent (uzman AI asistanı) aynı anda farklı uzmanlık alanlarında çalışabilmeli, çakışma olmamalıdır.

**Uzmanlık Alanları:**
- 🔒 **Security Expert** - Güvenlik açıkları, attack vectors, güvenlik best practices
- ⚡ **Performance Expert** - Performans bottleneck'leri, optimizasyon fırsatları
- 🏗️ **Architecture Expert** - Mimari desenler, scalability, maintainability
- ✨ **Code Quality Expert** - Kod kalitesi, standartlar, best practices
- 🚀 **DevOps Expert** - CI/CD, deployment, monitoring, infrastructure
- 🧪 **Testing Expert** - Test coverage, test stratejisi, quality assurance

**Prensipler:**
1. ✅ Her expert agent kendi uzmanlık alanına göre görev seçer
2. ✅ Görev başlatmadan önce `todo/master_live.md` kontrol edilir (çakışma önleme)
3. ✅ Görev başlatırken `todo/master_live.md`'ye eklenir (uzmanlık alanı belirtilir)
4. ✅ Görev tamamlandığında `todo/master_done.md`'ye taşınır
5. ✅ Expert agent'lar birbirlerinin görevlerine müdahale etmez
6. ✅ Durum senkronizasyonu için Git kullanılır
7. ✅ Görevler uzmanlık alanına göre önceliklendirilir

### Tutarlı Format ve Bakış Açısı

**KRİTİK KURAL:** Tüm dokümantasyon aynı format ve bakış açısıyla yazılmalıdır.

**Standartlar:**
1. ✅ Başlık formatı: `# Başlık - Alt Başlık`
2. ✅ Tarih formatı: `YYYY-MM-DD HH:MM:SS`
3. ✅ Versiyon formatı: `MAJOR.MINOR.PATCH`
4. ✅ Durum göstergesi: `✅ Aktif`, `🔄 Devam Ediyor`, `❌ Pasif`
5. ✅ Türkçe iletişim (kullanıcı ile)

---

## 📚 Dokümantasyon Haritası (Single Source of Truth)

### Ana Kaynak Dosyalar

#### 1. Kurallar ve Prensipler
**Tek Kaynak:** `.cursorrules`
- Tüm proje kuralları
- Agent çalışma prensipleri
- Test ve teyit kuralları
- Verimlilik kuralları
- **Referans:** Diğer tüm dosyalar buraya referans verir

#### 2. Proje Bilgileri
**Tek Kaynak:** `project_info_20251208_145614.md`
- Proje amacı ve genel bilgiler
- Donanım altyapısı
- Sistem bilgileri
- Versiyon geçmişi
- **Referans:** README.md, diğer dokümantasyonlar

#### 3. Başlangıç ve Durum
**Tek Kaynak:** `todo/START_HERE.md`
- Hızlı başlangıç rehberi
- Kritik kurallar özeti
- Durum kontrolü
- **Referans:** Tüm agent'lar buradan başlar

#### 4. Sistem Mimarisi
**Tek Kaynak:** `docs/architecture.md`
- Sistem mimarisi
- Modül yapısı
- Veri akışı
- Görev dağılımı
- **Referans:** project_info_20251208_145614.md, README.md

#### 5. API Referansı
**Tek Kaynak:** `docs/api_reference.md`
- Tüm API endpoint'leri
- Request/response formatları
- Örnekler
- **Referans:** README.md, docs/api_examples.md

#### 6. Deployment ve Kurulum
**Tek Kaynak:** `docs/deployment.md`
- Kurulum adımları
- Yapılandırma
- Servis yönetimi
- **Referans:** README.md

#### 7. Sorun Giderme
**Tek Kaynak:** `docs/troubleshooting.md`
- Sorun giderme rehberi
- Log analizi
- Hata kodları
- **Referans:** README.md

---

## 🔄 Multi-Expert Çalışma Kuralları

### Görev Başlatma Protokolü

**Adım 1: Durum Kontrolü**
```bash
# Expert agent görev başlatmadan önce:
1. todo/master_live.md okunur (aktif görevler kontrol edilir)
2. todo/master_next.md okunur (bekleyen görevler kontrol edilir)
3. Git pull yapılır (en güncel durum alınır)
```

**Adım 2: Görev Seçimi (Uzmanlık Bazlı)**
```bash
# Expert agent görev seçerken:
1. Kendi uzmanlık alanına göre master_next.md'den uygun görevi seçer
   - Security Expert: Güvenlik, authentication, rate limiting görevleri
   - Performance Expert: Optimizasyon, async operations görevleri
   - Architecture Expert: Mimari desenler, refactoring görevleri
   - Code Quality Expert: Standartlar, linting, code quality görevleri
   - DevOps Expert: CI/CD, deployment, monitoring görevleri
   - Testing Expert: Test coverage, test stratejisi görevleri
2. master_live.md'de aynı görev yoksa devam eder
3. master_live.md'ye görevi ekler (durum: IN_PROGRESS, uzmanlık alanı belirtilir)
4. Git commit yapar (görev başlatıldı, uzmanlık alanı belirtilir)
```

**Adım 3: Çalışma**
```bash
# Expert agent çalışırken:
1. Görevle ilgili dosyaları okur/düzenler
2. Değişiklikleri commit eder (küçük commit'ler)
3. master_live.md'yi günceller (ilerleme durumu)
```

**Adım 4: Tamamlama**
```bash
# Expert agent görev tamamladığında:
1. Görevi master_live.md'den master_done.md'ye taşır
2. project_state.md'yi günceller
3. checkpoint.md'yi günceller
4. Git commit ve push yapar
```

### Çakışma Önleme Kuralları

**KRİTİK:** Expert agent'lar birbirlerinin görevlerine müdahale etmemelidir.

**Kurallar:**
1. ✅ Görev başlatmadan önce `master_live.md` kontrol edilir
2. ✅ Aynı görev `master_live.md`'de varsa, başka görev seçilir (kendi uzmanlık alanından)
3. ✅ Farklı uzmanlık alanlarındaki görevler paralel çalışabilir
4. ✅ Görev dosyaları düzenlenirken Git pull yapılır
5. ✅ Conflict durumunda expert agent bekler veya kendi uzmanlık alanından alternatif görev seçer
6. ✅ Görev tamamlanmadan başka göreve geçilmez
7. ✅ Görev açıklamasında uzmanlık alanı belirtilir (örn: "[Security Expert] API Authentication")

### Durum Senkronizasyonu

**Git Workflow:**
1. ✅ Her görev başlangıcında: `git pull`
2. ✅ Her değişiklikte: `git commit` (küçük commit'ler)
3. ✅ Görev tamamlandığında: `git push`
4. ✅ Conflict durumunda: `git pull --rebase` veya alternatif görev

---

## 📋 Dokümantasyon Güncelleme Kuralları

### Güncelleme Sırası

**KRİTİK:** Bilgi güncellendiğinde sadece ana kaynak güncellenir.

**Örnek Senaryo:**
1. API endpoint'i değişti
2. ✅ `docs/api_reference.md` güncellenir (tek kaynak)
3. ✅ `README.md` sadece referans verir (link ile)
4. ❌ `README.md`'de endpoint detayları tekrar edilmez

### Referans Kullanımı

**Doğru Kullanım:**
```markdown
## API Endpoints
Detaylı bilgiler için [API Referansı](docs/api_reference.md) dosyasına bakınız.
```

**Yanlış Kullanım:**
```markdown
## API Endpoints
- GET /api/health - Sistem sağlık kontrolü
- GET /api/status - ESP32 durum bilgisi
... (tekrar eden bilgiler)
```

---

## 🔍 Tekrar Tespiti ve Temizleme

### Tekrar Tespit Kriterleri

**Tekrar Sayılan Durumlar:**
1. ❌ Aynı bilgi 2+ dosyada bulunuyorsa
2. ❌ Aynı kural 2+ dosyada tanımlanmışsa
3. ❌ Aynı örnek 2+ dosyada verilmişse
4. ❌ Aynı link listesi 2+ dosyada varsa

**Tekrar Sayılmayan Durumlar:**
1. ✅ Özet bilgi (detaylar ana kaynakta)
2. ✅ Referans linki (ana kaynağa yönlendirme)
3. ✅ Kısa açıklama (detaylar ana kaynakta)

### Temizleme Adımları

1. ✅ Tekrar eden bilgi tespit edilir
2. ✅ Ana kaynak belirlenir
3. ✅ Tekrar eden bilgi kaldırılır
4. ✅ Referans linki eklenir
5. ✅ Git commit yapılır

---

## 📊 Dokümantasyon İndeksi

### Ana Dokümantasyon Dosyaları

| Dosya | Amaç | Tek Kaynak | Referans Veren |
|-------|------|------------|----------------|
| `.cursorrules` | Tüm kurallar | ✅ | Tüm dosyalar |
| `project_info_20251208_145614.md` | Proje bilgileri | ✅ | README.md, diğerleri |
| `todo/START_HERE.md` | Başlangıç | ✅ | Tüm agent'lar |
| `docs/architecture.md` | Mimari | ✅ | project_info, README |
| `docs/api_reference.md` | API referansı | ✅ | README, api_examples |
| `docs/deployment.md` | Kurulum | ✅ | README |
| `docs/troubleshooting.md` | Sorun giderme | ✅ | README |

### Referans Dosyalar

| Dosya | Amaç | Ana Kaynak |
|-------|------|------------|
| `README.md` | Proje özeti | project_info, architecture, api_reference |
| `docs/api_examples.md` | API örnekleri | api_reference |
| `todo/checkpoint.md` | Checkpoint | START_HERE |
| `todo/project_state.md` | Proje durumu | START_HERE |

---

## ✅ Kontrol Checklist

### Her Dokümantasyon Güncellemesinde

- [ ] Ana kaynak dosya belirlendi mi?
- [ ] Tekrar eden bilgi var mı? (varsa kaldırıldı mı?)
- [ ] Referans linki eklendi mi?
- [ ] Format tutarlı mı? (başlık, tarih, versiyon)
- [ ] Git commit yapıldı mı?

### Her Görev Başlangıcında (Expert Agent)

- [ ] `master_live.md` kontrol edildi mi?
- [ ] Git pull yapıldı mı?
- [ ] Görev `master_live.md`'ye eklendi mi?
- [ ] Git commit yapıldı mı?

### Her Görev Tamamlandığında (Expert Agent)

- [ ] Görev `master_done.md`'ye taşındı mı?
- [ ] `project_state.md` güncellendi mi?
- [ ] `checkpoint.md` güncellendi mi?
- [ ] Git commit ve push yapıldı mı?

---

## 🎯 Sonuç

Bu strateji ile:
- ✅ Tekrar eden bilgiler kaldırılır
- ✅ Tutarlı dokümantasyon sağlanır
- ✅ Multi-expert çalışma desteklenir (farklı uzmanlık alanlarında paralel çalışma)
- ✅ Çakışmalar önlenir
- ✅ Verimli çalışma sağlanır

**Son Güncelleme:** 2025-12-12 10:00:00

