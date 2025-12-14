# 🚀 PROJEYE DEVAM ETMEK İÇİN BAŞLANGIÇ NOKTASI

**Bu dosya AI asistanları ve geliştiriciler için hazırlanmıştır.**

---

## ⚡ Hızlı Başlangıç (30 Saniye)

### 1. Durum Kontrolü
```bash
# Projenin mevcut durumunu öğren
cat todo/checkpoint.md

# Aktif görevleri kontrol et
cat todo/master_live.md

# Bekleyen görevleri hızlı tarama (ilk 20 açık madde)
grep -n "^- \\[ \\]" todo/master_next.md | head -n 20
```

### 2. Çalışma Akışı
```bash
# Detaylı çalışma akışını oku
cat todo/ai_workflow.md
```

### 3. Başla!
En yüksek öncelikli görevi seç ve çalışmaya başla.

---

## 📋 Okuma Sırası (Önemli!)

### Minimum (Token Verimli)
1. **`checkpoint.md`** - Nerede kaldık? (30 saniye)

### Görev Seçimi Gerekirse
2. **`master_live.md`** - Aktif görev var mı? (30 saniye)
3. **`master_next.md`** - En yüksek öncelikli bekleyen işler (2 dakika)

### Sadece Gerekirse (Derinleşme)
4. **`project_state.md`** - Genel durum, riskler, blokajlar (2 dakika)
5. **`ai_workflow.md`** - Çalışma prensipleri / test zamanlaması (referans)
6. **`docs/workspace_index.md`** - Dosya/klasör haritası (referans)
7. **`docs/ANALYSIS_IGNORE_LIST.md`** - Ertelenmiş konular (tekrar önleme)

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
4. `project_state.md`'yi güncelle

---

## 🔍 Durum Kontrol Checklist

- [ ] `checkpoint.md` okundu mu?
- [ ] `project_state.md` okundu mu? (gerekirse)
- [ ] Aktif görevler kontrol edildi mi?
- [ ] Bekleyen görevler kontrol edildi mi?
- [ ] Blokajlar tespit edildi mi?
- [ ] Sonraki görev seçildi mi?

---

## 📊 Proje Özeti (Single Source of Truth)

- **Nerede kaldık?**: `todo/checkpoint.md`
- **Genel durum & riskler**: `todo/project_state.md`
- **Aktif işler**: `todo/master_live.md`
- **Sıradaki işler**: `todo/master_next.md`
- **Çalışma kuralları**: `.cursorrules` ve `todo/ai_workflow.md`
- **Dokümantasyon haritası**: `docs/workspace_index.md`

---

## 🚨 Kritik Bilgiler

- **Çalışma Dizini:** `/home/basar/charger`
- **Git Repository:** `git@github.com:CaiserSz/orge1.git`
- **Virtual Environment:** `env/` (aktif olmalı)
- **API Port:** 8000
- **API URL:** `https://lixhium.ngrok.app`

---

## 💡 İpuçları

1. **Küçük Adımlar:** Büyük görevleri parçalara böl
2. **Sık Commit:** Her önemli değişiklikte commit yap
3. **Dokümantasyon:** Her değişiklikte dokümantasyonu güncelle
4. **Test:** Yeni kod için test yaz
5. **Code Quality:** Linting ve formatting uygula

---

## 🔴 KRİTİK KURALLAR (Özet)

**Detaylı kurallar için `.cursorrules` dosyasına bakınız. Burada sadece özet verilmiştir:**

**Test ve Teyit Zorunluluğu:**
- Detaylı kurallar için [`.cursorrules`](../.cursorrules) dosyasındaki "KRİTİK KURAL: Test ve Teyit Zorunluluğu" bölümüne bakınız
- **Özet:** Kullanıcıya teslim etmeden önce MUTLAKA test edip teyit et
- **Özet:** Her dosya editinden sonra SADECE o dosyanın syntax kontrolü yapılmalıdır
- **Özet:** Tüm test suite'i SADECE görev tamamlandığında, commit öncesi veya teslim öncesi çalıştırılmalıdır
- **Özet (Verimlilik):** Her adımda tam suite çalıştırma; sadece ilgili testleri çalıştır (dokümantasyon-only değişikliklerde pytest gerekmez)

**Verimlilik ve Odak:**
- Gereksiz dosya okuma yapma
- Gereksiz test çalıştırma yapma
- Odak kaybetme - bir göreve başladığında tamamla
- Mantıklı ilerle - her işlem öncesi "Bu mantıklı mı?" sorusunu sor

---

**Tespitlerin Todo Sistemine Eklenmesi:**
- Çalışma sırasında tespit edilen her şey `todo/master_next.md`'ye eklenmelidir
- Mevcut görevle ilgili değilse hemen ele alınmamalı, sadece eklenmelidir
- Detaylar için `.cursorrules` dosyasına bakınız

---

**Yedekleme ve Geri Dönüş:**
- Büyük refactoring öncesi Git branch veya tag oluştur
- Detaylar için `.cursorrules` ve `docs/standards/BACKUP_ROLLBACK_STANDARDS.md` dosyalarına bakınız

---

**Workspace Yönetimi:**
- Workspace metriklerine uy (dosya sayısı, boyut sınırları)
- Temizlik kurallarına uy (geçici dosyalar, cache, log dosyaları)
- Detaylar için `.cursorrules` ve `docs/standards/WORKSPACE_MANAGEMENT_STANDARDS.md` dosyalarına bakınız

---

## ✅ Projeye Devam Etme

**"projeye devam et" demeniz yeterlidir!**

Agent otomatik olarak:
1. ✅ Durum tespiti yapacak (`checkpoint.md`; gerekirse `project_state.md`)
2. ✅ Aktif görevleri kontrol edecek (`master_live.md`)
3. ✅ Bekleyen görevleri seçecek (`master_next.md`)
4. ✅ Sorunsuz bir şekilde devam edecek

**Detaylı Rehber:** `todo/PROJECT_CONTINUATION_GUIDE.md`

---

## 🆘 Yardım

- **Durum:** `todo/project_state.md`
- **Çalışma Akışı:** `todo/ai_workflow.md`
- **Öneriler:** `todo/expert_recommendations.md`
- **Proje Bilgileri:** `project_info_20251208_145614.md`
- **Devam Etme Rehberi:** `todo/PROJECT_CONTINUATION_GUIDE.md` ⭐ YENİ

---

**Son Güncelleme:** 2025-12-12 23:55:00

**🎯 Şimdi başla: `cat todo/checkpoint.md`**

