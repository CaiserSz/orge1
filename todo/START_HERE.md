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

# Bekleyen görevleri kontrol et
cat todo/master_next.md | grep -A 5 "\[ \]"
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

1. **`checkpoint.md`** - Nerede kaldık? (30 saniye)
2. **`project_state.md`** - Detaylı durum (2 dakika)
3. **`ai_workflow.md`** - Nasıl çalışılır? (5 dakika)
4. **`master_next.md`** - Ne yapılacak? (2 dakika)
5. **`expert_recommendations.md`** - Best practices (referans)

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
- [ ] `project_state.md` okundu mu?
- [ ] Aktif görevler kontrol edildi mi?
- [ ] Bekleyen görevler kontrol edildi mi?
- [ ] Blokajlar tespit edildi mi?
- [ ] Sonraki görev seçildi mi?

---

## 📊 Proje Özeti

**Mevcut Faz:** Faz 1 ✅ (Tamamlandı)  
**Sonraki Faz:** Faz 2 🔄 (API Test ve İyileştirme)  
**Genel İlerleme:** %32  
**Son Görev:** REST API Implementasyonu ✅

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

**Browser Test Zorunluluğu:**
- Browser ile kullanılan özellikler (web sayfaları, HTML, JavaScript, CSS) için gerçek browser'dan manuel test yapılmalıdır
- Sadece curl veya API testi yeterli değildir
- Browser'dan görsel olarak kontrol edilmeli, JavaScript fonksiyonları çalıştırılmalı, UI/UX test edilmelidir
- Browser test edilmeden görev tamamlanmış sayılamaz

**External Erişim Test Zorunluluğu:**
- Dışarıdan erişilebilir özellikler için external erişim testi zorunludur
- Sadece localhost testi yeterli değildir
- Ngrok veya dışarıdan erişim URL'i üzerinden test edilmelidir
- External erişim test edilmeden görev tamamlanmış sayılamaz
- Test sonuçları (URL, response, status code) dokümante edilmelidir

**Kural İhlali:** Kullanıcıya test edilmemiş bir şey verilirse, hemen test edip düzeltilmelidir.

---

## 🆘 Yardım

- **Durum:** `todo/project_state.md`
- **Çalışma Akışı:** `todo/ai_workflow.md`
- **Öneriler:** `todo/expert_recommendations.md`
- **Proje Bilgileri:** `project_info_20251208_145614.md`

---

**Son Güncelleme:** 2025-12-08 18:35:00

**🎯 Şimdi başla: `cat todo/checkpoint.md`**

