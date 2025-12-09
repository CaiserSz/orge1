# Yedekleme ve Geri Dönüş Standartları

**Oluşturulma Tarihi:** 2025-12-09 22:30:00
**Son Güncelleme:** 2025-12-09 22:30:00
**Version:** 1.0.0
**Durum:** ✅ Aktif

---

## 🎯 Amaç

Bu dokümantasyon, projede yedekleme, geri dönüş ve refactoring güvenlik prosedürlerini standartlaştırarak:
- Veri kaybını önlemek
- Güvenli refactoring yapmak
- Hızlı geri dönüş sağlamak
- İlerleme kaybını önlemek

için oluşturulmuştur.

---

## 🔄 Git Yedekleme ve Geri Dönüş Stratejisi

### Git Branch Stratejisi

#### Ana Branch'ler
- **`main`**: Production-ready kod
  - Her zaman deployable olmalı
  - Protected branch (PR gerektirir)
  - Version tag'leri ile işaretlenir

#### Destekleyici Branch'ler
- **`feature/*`**: Yeni özellikler
  - Branch from: `main`
  - Merge to: `main` (PR ile)
  - Naming: `feature/description`

- **`fix/*`**: Bug düzeltmeleri
  - Branch from: `main`
  - Merge to: `main` (PR ile)
  - Naming: `fix/description`

- **`refactor/*`**: Refactoring işlemleri
  - Branch from: `main`
  - Merge to: `main` (PR ile)
  - Naming: `refactor/description`

- **`hotfix/*`**: Kritik production düzeltmeleri
  - Branch from: `main`
  - Merge to: `main` (PR ile)
  - Naming: `hotfix/description`

### Git Commit Stratejisi

#### Commit Öncesi Kontroller
1. ✅ Kod çalışıyor mu? (syntax, import hataları)
2. ✅ Testler geçiyor mu? (`pytest`)
3. ✅ Standartlara uygun mu? (boyut, satır sayısı)
4. ✅ Dokümantasyon güncel mi?
5. ✅ Commit mesajı doğru formatta mı?

#### Commit Mesaj Formatı
```
type(scope): subject

[optional body]

[optional footer]
```

**Types:**
- `feat`: Yeni özellik
- `fix`: Bug düzeltme
- `docs`: Dokümantasyon değişiklikleri
- `refactor`: Refactoring
- `test`: Test değişiklikleri
- `chore`: Bakım görevleri

**Kurallar:**
- İlk satır ≤ 72 karakter
- Imperative mood kullan ("Add" not "Added")
- Sonunda nokta yok
- İlgili issue/PR referansı varsa footer'da belirt

---

## 💾 Yedekleme Standartları

### Refactoring Öncesi Yedekleme

#### Zorunlu Yedekleme Durumları

1. **Büyük Refactoring İşlemleri**
   - Dosya bölme/birleştirme
   - Modül yeniden yapılandırma
   - API değişiklikleri
   - Database schema değişiklikleri

2. **Kritik Dosya Değişiklikleri**
   - `api/main.py` gibi ana dosyalar
   - `project_info_20251208_145614.md` gibi ana dokümantasyon
   - Configuration dosyaları
   - Service dosyaları

3. **Çoklu Dosya Değişiklikleri**
   - 5+ dosya aynı anda değiştiriliyorsa
   - Cross-file dependencies değişiyorsa
   - Import yapısı değişiyorsa

#### Yedekleme Yöntemleri

##### 1. Git Branch (Önerilen)
```bash
# Refactoring öncesi branch oluştur
git checkout -b refactor/description
git add .
git commit -m "refactor(scope): Backup before refactoring"

# Refactoring yap
# ...

# Test et ve commit
git add .
git commit -m "refactor(scope): Refactoring completed"

# Geri dönüş gerekirse
git checkout main
git branch -D refactor/description
```

##### 2. Git Tag (Büyük Değişiklikler İçin)
```bash
# Refactoring öncesi tag oluştur
git tag -a v1.9.0-pre-refactor -m "Pre-refactoring backup"

# Refactoring yap
# ...

# Geri dönüş gerekirse
git checkout v1.9.0-pre-refactor
```

##### 3. Dosya Yedekleme (Küçük Değişiklikler İçin)
```bash
# Dosyayı yedekle
cp api/main.py api/main.py.backup

# Değişiklik yap
# ...

# Geri dönüş gerekirse
cp api/main.py.backup api/main.py
```

### Yedekleme Checklist

#### Refactoring Öncesi
- [ ] Mevcut durum commit edildi mi?
- [ ] Yeni branch oluşturuldu mu? (büyük refactoring için)
- [ ] Tag oluşturuldu mu? (kritik değişiklikler için)
- [ ] Dosya yedeklendi mi? (küçük değişiklikler için)
- [ ] Testler geçiyor mu? (mevcut durum)
- [ ] Dokümantasyon güncel mi?

#### Refactoring Sırasında
- [ ] Küçük adımlarla ilerleniyor mu?
- [ ] Her adımda test ediliyor mu?
- [ ] Commit'ler anlamlı mı?
- [ ] Hata durumunda geri dönüş planı var mı?

#### Refactoring Sonrası
- [ ] Tüm testler geçiyor mu?
- [ ] Dokümantasyon güncellendi mi?
- [ ] Yedek dosyalar temizlendi mi? (`.backup` dosyaları)
- [ ] Git history temiz mi?

---

## 🔙 Geri Dönüş (Rollback) Prosedürleri

### Git Geri Dönüş Yöntemleri

#### 1. Son Commit'i Geri Alma (Lokal)
```bash
# Son commit'i geri al (değişiklikler korunur)
git reset --soft HEAD~1

# Son commit'i geri al (değişiklikler silinir)
git reset --hard HEAD~1
```

#### 2. Belirli Commit'e Geri Dönme
```bash
# Commit hash'ini bul
git log --oneline

# Belirli commit'e geri dön
git checkout <commit-hash>

# Yeni branch oluştur (güvenli)
git checkout -b rollback/<commit-hash>
```

#### 3. Branch'e Geri Dönme
```bash
# Main branch'e geri dön
git checkout main

# Refactoring branch'ini sil
git branch -D refactor/description
```

#### 4. Tag'e Geri Dönme
```bash
# Tag'e geri dön
git checkout v1.9.0-pre-refactor

# Yeni branch oluştur
git checkout -b rollback/v1.9.0-pre-refactor
```

### Dosya Geri Dönüş Yöntemleri

#### 1. Yedek Dosyadan Geri Dönme
```bash
# Yedek dosyadan geri yükle
cp api/main.py.backup api/main.py

# Git'e ekle ve commit et
git add api/main.py
git commit -m "fix(api): Rollback to backup"
```

#### 2. Git'ten Dosya Geri Yükleme
```bash
# Belirli commit'ten dosya geri yükle
git checkout <commit-hash> -- api/main.py

# Commit et
git add api/main.py
git commit -m "fix(api): Rollback file from commit"
```

### Geri Dönüş Checklist

#### Geri Dönüş Öncesi
- [ ] Sorun tespit edildi mi?
- [ ] Geri dönüş nedeni dokümante edildi mi?
- [ ] Hangi commit/tag'e dönülecek belirlendi mi?
- [ ] Mevcut durum yedeklendi mi? (geri dönüş öncesi)

#### Geri Dönüş Sırasında
- [ ] Doğru commit/tag seçildi mi?
- [ ] Testler çalıştırıldı mı?
- [ ] Dokümantasyon güncellendi mi?

#### Geri Dönüş Sonrası
- [ ] Sistem çalışıyor mu?
- [ ] Testler geçiyor mu?
- [ ] Geri dönüş nedeni dokümante edildi mi?
- [ ] Sonraki adımlar planlandı mı?

---

## 📊 İlerleme Takibi ve Yedekleme

### Checkpoint Sistemi

#### Checkpoint Oluşturma
```bash
# Checkpoint oluştur (git tag)
git tag -a checkpoint-YYYYMMDD-HHMM -m "Checkpoint: [Açıklama]"

# Push et
git push origin checkpoint-YYYYMMDD-HHMM
```

#### Checkpoint Kullanımı
- Her önemli adımda checkpoint oluştur
- Büyük değişiklikler öncesi checkpoint
- Test geçişi sonrası checkpoint
- Dokümantasyon güncellemesi sonrası checkpoint

### İlerleme Dokümantasyonu

#### Her Çalışma Sonrası
1. ✅ `todo/project_state.md` güncelle
2. ✅ `todo/checkpoint.md` güncelle
3. ✅ `todo/master_done.md` güncelle
4. ✅ Git commit ve push

#### Her Refactoring Sonrası
1. ✅ Refactoring detaylarını dokümante et
2. ✅ Değişiklikleri `CHANGELOG.md`'ye ekle
3. ✅ `project_info_20251208_145614.md` güncelle
4. ✅ `WORKSPACE_INDEX.md` güncelle

---

## 🛡️ Güvenlik Kuralları

### Asla Yapılmaması Gerekenler

1. ❌ **`main` branch'e direkt push**
   - Her zaman PR kullan
   - Code review yapılmalı

2. ❌ **Force push (`git push --force`)**
   - History'yi bozar
   - Sadece kendi branch'inde kullan (dikkatli)

3. ❌ **Yedekleme olmadan büyük değişiklik**
   - Her zaman yedekle
   - Branch veya tag kullan

4. ❌ **Commit mesajı olmadan commit**
   - Her commit anlamlı mesaj içermeli
   - Conventional commits formatı kullan

5. ❌ **Test etmeden commit**
   - Her commit öncesi test et
   - Syntax kontrolü yap

### Güvenli Çalışma Kuralları

1. ✅ **Küçük adımlarla ilerle**
   - Büyük değişiklikleri parçala
   - Her adımda commit et

2. ✅ **Sık commit yap**
   - Her mantıklı değişiklikte commit
   - Küçük commit'ler geri dönüşü kolaylaştırır

3. ✅ **Test et ve doğrula**
   - Her commit öncesi test
   - Syntax kontrolü
   - Standart kontrolü

4. ✅ **Dokümante et**
   - Her önemli değişiklikte dokümantasyon güncelle
   - Commit mesajında açıkla

---

## 📋 Örnek Senaryolar

### Senaryo 1: Büyük Refactoring (api/main.py Router'lara Bölme)

```bash
# 1. Mevcut durumu commit et
git add .
git commit -m "chore: Pre-refactoring checkpoint"

# 2. Refactoring branch oluştur
git checkout -b refactor/api-router-separation

# 3. Tag oluştur (güvenlik için)
git tag -a v1.9.0-pre-router-refactor -m "Pre-router refactoring"

# 4. Refactoring yap
# - api/routers/ klasörü oluştur
# - Endpoint'leri router'lara taşı
# - main.py'yi sadeleştir

# 5. Her adımda test et ve commit et
git add api/routers/
git commit -m "refactor(api): Create routers directory"

git add api/main.py
git commit -m "refactor(api): Move endpoints to routers"

# 6. Test et
pytest

# 7. Eğer sorun varsa geri dön
git checkout v1.9.0-pre-router-refactor

# 8. Sorun yoksa merge et
git checkout main
git merge refactor/api-router-separation

# 9. Push et
git push origin main
```

### Senaryo 2: Küçük Değişiklik (Dosya Yedekleme)

```bash
# 1. Dosyayı yedekle
cp api/logging_config.py api/logging_config.py.backup

# 2. Değişiklik yap
# ...

# 3. Test et
pytest

# 4. Sorun varsa geri yükle
cp api/logging_config.py.backup api/logging_config.py

# 5. Sorun yoksa commit et ve yedek dosyayı sil
git add api/logging_config.py
git commit -m "fix(logging): Fix thread safety issue"
rm api/logging_config.py.backup
```

### Senaryo 3: Geri Dönüş (Rollback)

```bash
# 1. Sorun tespit et
# Testler başarısız oldu

# 2. Son çalışan commit'i bul
git log --oneline

# 3. Geri dön
git checkout <working-commit-hash>

# 4. Yeni branch oluştur (güvenli)
git checkout -b rollback/fix-test-failure

# 5. Sorunu düzelt
# ...

# 6. Test et ve commit et
pytest
git add .
git commit -m "fix: Resolve test failures"

# 7. Merge et
git checkout main
git merge rollback/fix-test-failure
```

---

## 🔗 İlgili Dokümantasyon

- `.cursorrules` - Proje kuralları
- `CONTRIBUTING.md` - Git workflow
- `CODE_DOCUMENTATION_STANDARDS.md` - Kod standartları
- `todo/REFACTORING_PLAN.md` - Refactoring planı
- `todo/ai_workflow.md` - Çalışma akışı

---

## 📝 Notlar

- Bu standartlar proje boyunca uygulanacaktır
- Standartlar zamanla güncellenebilir (versiyon kontrolü ile)
- İstisnai durumlar dokümante edilmelidir
- Tüm geliştiriciler bu standartlara uymalıdır

---

**Son Güncelleme:** 2025-12-09 22:30:00

