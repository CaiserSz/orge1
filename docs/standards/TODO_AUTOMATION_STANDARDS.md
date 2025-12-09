# Todo Dosyaları Otomasyon Standartları

**Oluşturulma Tarihi:** 2025-12-10 02:20:00
**Son Güncelleme:** 2025-12-10 02:20:00
**Version:** 1.0.0
**Durum:** ✅ Aktif

---

## 🎯 Amaç

Todo dosyalarının otomatik kontrol ve güncellemesi için standartlar ve kurallar.

---

## 🔄 Otomatik Kontrol Mekanizması

### 1. Pre-commit Hook Kontrolü

**Dosya:** `.git/hooks/pre-commit`

**Kontrol Edilenler:**
- Dosya boyutu standartları
- Tamamlanan görevlerin durumu
- master_next.md tutarlılığı

**Aksiyon:**
- Uyarı verir ama commit'i engellemez (şimdilik)
- Detaylı rapor için `python3 scripts/todo_auto_check.py` çalıştırılmalı

### 2. Otomatik Güncelleme Script'i

**Dosya:** `scripts/todo_auto_update.py`

**Yapılanlar:**
- Tamamlanan görevlerin durumunu günceller
- Dosya boyutu standartlarına göre öncelikleri günceller
- Son güncelleme tarihlerini günceller

**Kullanım:**
```bash
python3 scripts/todo_auto_update.py
```

### 3. Kontrol Script'i

**Dosya:** `scripts/todo_auto_check.py`

**Kontrol Edilenler:**
- Dosya boyutu standartları
- Tamamlanan görevler
- master_next.md tutarlılığı

**Kullanım:**
```bash
# Sadece kontrol
python3 scripts/todo_auto_check.py

# Dry-run (değişiklik yapmadan kontrol)
python3 scripts/todo_auto_check.py --dry-run
```

---

## 📋 AI Agent Kuralları

### Kural 1: Her Görev Tamamlandığında

**Zorunlu Aksiyonlar:**
1. ✅ `master_next.md`'de görevin durumunu güncelle
2. ✅ `master_done.md`'ye görevi ekle
3. ✅ `master_live.md`'den görevi kaldır
4. ✅ `project_state.md`'yi güncelle
5. ✅ `checkpoint.md`'yi güncelle

**Otomatik Kontrol:**
```bash
python3 scripts/todo_auto_check.py
```

### Kural 2: Dosya Boyutu Standartları Kontrolü

**Zorunlu Aksiyonlar:**
1. ✅ Dosya boyutu kontrolü yap (`wc -l`)
2. ✅ Standartları aşıyorsa `master_next.md`'ye ekle
3. ✅ Önceliği doğru belirle (Acil/Orta/Düşük)

**Otomatik Kontrol:**
```bash
python3 scripts/todo_auto_check.py
```

### Kural 3: Her Commit Öncesi

**Zorunlu Aksiyonlar:**
1. ✅ Todo dosyaları tutarlılık kontrolü
2. ✅ Tamamlanan görevler kontrolü
3. ✅ Dosya boyutu standartları kontrolü

**Otomatik Kontrol:**
- Pre-commit hook otomatik çalışır
- Manuel kontrol: `python3 scripts/todo_auto_check.py`

---

## 🔍 Kontrol Kriterleri

### Dosya Boyutu Standartları

| Dosya Tipi | Uyarı Eşiği | Maksimum | Öncelik |
|------------|-------------|----------|---------|
| API Endpoint | 500 satır | 600 satır | Acil (Öncelik 0) |
| Modül | 400 satır | 500 satır | Orta |
| Test | 400 satır | 500 satır | Orta |

### Tamamlanan Görev Kontrolü

**Kontrol Edilenler:**
- Dosya varlığı (`api/event_detector.py` gibi)
- master_done.md'de kayıt
- master_next.md'de durum

**Aksiyon:**
- Dosya varsa ve master_done.md'de kayıtlıysa → master_next.md'de durum güncellenmeli

---

## 🛠️ Otomasyon Geliştirme Planı

### Faz 1: Temel Kontrol (Tamamlandı ✅)
- [x] `todo_auto_check.py` script'i oluşturuldu
- [x] Pre-commit hook'a kontrol eklendi
- [x] Dosya boyutu kontrolü eklendi

### Faz 2: Otomatik Güncelleme (Devam Ediyor 🔄)
- [x] `todo_auto_update.py` script'i oluşturuldu
- [ ] Otomatik güncelleme mekanizması geliştirilecek
- [ ] master_next.md otomatik güncelleme

### Faz 3: Proaktif Kontrol (Planlanıyor 📋)
- [ ] CI/CD pipeline'a entegrasyon
- [ ] Haftalık otomatik kontrol
- [ ] Email/notification sistemi

---

## 📝 Kullanım Örnekleri

### Örnek 1: Manuel Kontrol

```bash
# Todo dosyalarını kontrol et
python3 scripts/todo_auto_check.py

# Çıktı:
# ======================================================================
# TODO DOSYALARI OTOMATIK KONTROL RAPORU
# ======================================================================
# Tarih: 2025-12-10T02:20:00
#
# 🔴 DOSYA BOYUTU SORUNLARI:
#   - api/main.py: 638 satır (Limit: 600)
#     Öncelik: Acil (Öncelik 0)
#     Durum: 🔴 Maksimum sınır aşıldı
#     Aksiyon: Router'lara bölünmeli
```

### Örnek 2: Otomatik Güncelleme

```bash
# Todo dosyalarını otomatik güncelle
python3 scripts/todo_auto_update.py

# Çıktı:
# ✅ Todo dosyaları güncellendi:
#   - master_next.md güncellendi
```

### Örnek 3: Pre-commit Hook

```bash
# Commit yaparken otomatik kontrol
git commit -m "feat: Yeni özellik"

# Çıktı:
# Running pre-commit checks...
# Checking Python syntax...
# Checking for trailing whitespace...
# Checking todo files consistency...
# Pre-commit checks passed!
```

---

## ⚠️ Önemli Notlar

1. **Otomatik Güncelleme:** Şimdilik sadece kontrol yapılıyor, otomatik güncelleme geliştirilecek
2. **Commit Engelleme:** Pre-commit hook şimdilik sadece uyarı veriyor, commit'i engellemiyor
3. **Manuel Kontrol:** Her önemli değişiklikten sonra manuel kontrol yapılmalı

---

## 🔗 İlgili Dosyalar

- `scripts/todo_auto_check.py` - Kontrol script'i
- `scripts/todo_auto_update.py` - Güncelleme script'i
- `.git/hooks/pre-commit` - Pre-commit hook
- `todo/master_next.md` - Bekleyen görevler
- `todo/master_done.md` - Tamamlanan görevler

---

**Son Güncelleme:** 2025-12-10 02:20:00

