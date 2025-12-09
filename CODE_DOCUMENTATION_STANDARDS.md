# Kod ve Dokümantasyon Standartları

**Oluşturulma Tarihi:** 2025-12-09 22:00:00  
**Son Güncelleme:** 2025-12-09 22:00:00  
**Version:** 1.0.0  
**Durum:** ✅ Aktif

---

## 🎯 Amaç

Bu dokümantasyon, projede kod ve dokümantasyon dosyalarının boyut, satır sayısı ve karmaşıklık sınırlamalarını standartlaştırarak:
- Okunabilirlik sorunlarını önlemek
- Analiz ve inceleme süreçlerini kolaylaştırmak
- Bakım ve geliştirme verimliliğini artırmak
- Kod kalitesini ve tutarlılığını sağlamak

için oluşturulmuştur.

---

## 📏 Kod Dosyaları Standartları

### Python Dosyaları (.py)

#### Satır Sayısı Sınırlamaları

| Dosya Tipi | İdeal | Uyarı Eşiği | Maksimum | Aksiyon |
|------------|-------|--------------|----------|---------|
| **Modül Dosyası** | 100-300 | 400 | 500 | Refactor gerekli |
| **API Endpoint Dosyası** | 150-400 | 500 | 600 | Router'a böl |
| **Test Dosyası** | 100-300 | 400 | 500 | Test suite'e böl |
| **Utility/Helper** | 50-200 | 300 | 400 | Fonksiyonlara böl |
| **Configuration** | 50-150 | 200 | 300 | Bölümlere ayır |

#### Dosya Boyutu Sınırlamaları

| Dosya Tipi | İdeal | Uyarı Eşiği | Maksimum |
|------------|-------|-------------|----------|
| **Python Dosyası** | < 20 KB | 30 KB | 50 KB |

#### Fonksiyon/Metod Sınırlamaları

| Metrik | İdeal | Uyarı Eşiği | Maksimum |
|--------|-------|--------------|----------|
| **Satır Sayısı** | 10-30 | 50 | 100 |
| **Cyclomatic Complexity** | 1-5 | 10 | 15 |
| **Parametre Sayısı** | 0-3 | 5 | 7 |

#### Sınıf (Class) Sınırlamaları

| Metrik | İdeal | Uyarı Eşiği | Maksimum |
|--------|-------|-------------|----------|
| **Satır Sayısı** | 50-200 | 300 | 500 |
| **Metod Sayısı** | 3-10 | 15 | 20 |
| **Özellik Sayısı** | 2-10 | 15 | 25 |

---

## 📚 Dokümantasyon Standartları

### Markdown Dosyaları (.md)

#### Satır Sayısı Sınırlamaları

| Dosya Tipi | İdeal | Uyarı Eşiği | Maksimum | Aksiyon |
|------------|-------|-------------|----------|---------|
| **Ana Dokümantasyon** | 300-800 | 1000 | 1200 | Bölümlere ayır |
| **Teknik Dokümantasyon** | 200-600 | 800 | 1000 | Alt başlıklara böl |
| **API Dokümantasyonu** | 100-400 | 600 | 800 | Endpoint'lere göre böl |
| **Tutorial/Guide** | 200-500 | 700 | 900 | Adımlara göre böl |
| **Audit/Report** | 300-700 | 900 | 1100 | Bölümlere ayır |
| **README** | 50-200 | 300 | 400 | Özet ve linkler |

#### Dosya Boyutu Sınırlamaları

| Dosya Tipi | İdeal | Uyarı Eşiği | Maksimum |
|------------|-------|-------------|----------|
| **Markdown Dosyası** | < 50 KB | 80 KB | 100 KB |

#### Bölüm (Section) Sınırlamaları

| Metrik | İdeal | Uyarı Eşiği | Maksimum |
|--------|-------|-------------|----------|
| **Bölüm Satır Sayısı** | 50-200 | 300 | 400 |
| **Alt Bölüm Sayısı** | 3-8 | 12 | 15 |

---

## 🔍 Mevcut Durum Analizi

### Python Dosyaları Durumu

| Dosya | Satır | Durum | Aksiyon |
|-------|-------|-------|---------|
| `api/main.py` | 591 | ⚠️ Uyarı | Router'lara bölünmeli |
| `esp32/bridge.py` | ~369 | ✅ İyi | - |
| `api/logging_config.py` | ~335 | ✅ İyi | - |
| `meter/read_meter.py` | ~496 | ⚠️ Uyarı | Modüllere bölünebilir |

### Dokümantasyon Durumu

| Dosya | Satır | Durum | Aksiyon |
|-------|-------|-------|---------|
| `project_info_20251208_145614.md` | 1245 | 🔴 Maksimum Aşıldı | Bölümlere ayırılmalı |
| `MULTI_EXPERT_ANALYSIS.md` | 1115 | ⚠️ Uyarı | Bölümlere ayırılabilir |
| `DEEPDIVE_ANALYSIS_REPORT.md` | 714 | ✅ İyi | - |
| `WORKSPACE_INDEX.md` | 658 | ⚠️ Uyarı | Bölümlere ayırılabilir |

---

## ✅ Uygulama Kuralları

### Kod Dosyaları İçin

#### 1. Yeni Dosya Oluştururken
- ✅ Dosya boyutunu ve satır sayısını kontrol et
- ✅ İdeal sınırlar içinde tutmaya çalış
- ✅ Uyarı eşiğini aşmamaya dikkat et
- ✅ Maksimum sınırı ASLA aşma

#### 2. Mevcut Dosyaları Güncellerken
- ✅ Satır sayısını kontrol et
- ✅ Uyarı eşiğine yaklaşıyorsa refactor planla
- ✅ Maksimum sınırı aşmışsa hemen refactor yap

#### 3. Refactoring Kriterleri
- 🔴 **Maksimum sınır aşıldı:** Acil refactor gerekli
- 🟡 **Uyarı eşiği aşıldı:** Yakın zamanda refactor planlanmalı
- 🟢 **İdeal sınırlar içinde:** Devam edilebilir

### Dokümantasyon İçin

#### 1. Yeni Dokümantasyon Oluştururken
- ✅ Dosya boyutunu ve satır sayısını kontrol et
- ✅ İdeal sınırlar içinde tutmaya çalış
- ✅ Uyarı eşiğini aşmamaya dikkat et
- ✅ Maksimum sınırı ASLA aşma

#### 2. Mevcut Dokümantasyonu Güncellerken
- ✅ Satır sayısını kontrol et
- ✅ Uyarı eşiğine yaklaşıyorsa bölümleme planla
- ✅ Maksimum sınırı aşmışsa hemen bölümlere ayır

#### 3. Bölümleme Kriterleri
- 🔴 **Maksimum sınır aşıldı:** Acil bölümleme gerekli
- 🟡 **Uyarı eşiği aşıldı:** Yakın zamanda bölümleme planlanmalı
- 🟢 **İdeal sınırlar içinde:** Devam edilebilir

---

## 🛠️ Refactoring Stratejileri

### Python Dosyaları İçin

#### 1. Modül Dosyası Bölme
```python
# ÖNCE: api/main.py (591 satır)
# SONRA:
# - api/main.py (200 satır) - FastAPI app setup
# - api/routers/charge.py (150 satır) - Charge endpoints
# - api/routers/status.py (100 satır) - Status endpoints
# - api/routers/meter.py (100 satır) - Meter endpoints
```

#### 2. Fonksiyon Bölme
```python
# ÖNCE: 100+ satırlık fonksiyon
# SONRA: Küçük, tek sorumluluklu fonksiyonlar
```

#### 3. Sınıf Bölme
```python
# ÖNCE: 500+ satırlık sınıf
# SONRA: Composition pattern ile küçük sınıflar
```

### Dokümantasyon İçin

#### 1. Ana Dokümantasyon Bölme
```
# ÖNCE: project_info_20251208_145614.md (1245 satır)
# SONRA:
# - project_info_20251208_145614.md (300 satır) - Genel bilgiler
# - docs/api_reference.md (300 satır) - API referansı
# - docs/architecture.md (300 satır) - Mimari
# - docs/deployment.md (200 satır) - Deployment
# - docs/troubleshooting.md (200 satır) - Sorun giderme
```

#### 2. Bölüm Başlıklarına Göre Bölme
- Her bölüm ayrı dosyaya
- Ana dosyada index ve linkler
- Cross-reference kullanımı

---

## 📊 Kontrol ve İzleme

### Otomatik Kontroller

#### Pre-commit Hook (Gelecek)
```bash
# Dosya boyutu kontrolü
# Satır sayısı kontrolü
# Karmaşıklık kontrolü
```

#### CI/CD Pipeline (Gelecek)
```yaml
# Automated checks:
# - File size limits
# - Line count limits
# - Complexity metrics
```

### Manuel Kontroller

#### Her Commit Öncesi
1. ✅ Dosya boyutunu kontrol et (`wc -l`, `du -h`)
2. ✅ Standartlara uygunluğu kontrol et
3. ✅ Gerekirse refactor yap

#### Haftalık Review
1. ✅ Tüm dosyaları tarayıcı ile kontrol et
2. ✅ Standartları aşan dosyaları tespit et
3. ✅ Refactor planı oluştur

---

## 🎯 Öncelikli Aksiyonlar

### Acil (Maksimum Sınır Aşıldı)

1. **`project_info_20251208_145614.md` (1245 satır)**
   - 🔴 **Durum:** Maksimum sınır (1200) aşıldı
   - **Aksiyon:** Bölümlere ayırılmalı
   - **Öncelik:** Yüksek
   - **Tahmini Süre:** 2-3 saat

### Önemli (Uyarı Eşiği Aşıldı)

2. **`api/main.py` (591 satır)**
   - 🟡 **Durum:** Uyarı eşiği (600) yakın
   - **Aksiyon:** Router'lara bölünmeli
   - **Öncelik:** Orta
   - **Tahmini Süre:** 3-4 saat

3. **`MULTI_EXPERT_ANALYSIS.md` (1115 satır)**
   - 🟡 **Durum:** Uyarı eşiği (1000) aşıldı
   - **Aksiyon:** Bölümlere ayırılabilir
   - **Öncelik:** Orta
   - **Tahmini Süre:** 1-2 saat

4. **`meter/read_meter.py` (~496 satır)**
   - 🟡 **Durum:** Uyarı eşiği (500) yakın
   - **Aksiyon:** Modüllere bölünebilir
   - **Öncelik:** Düşük
   - **Tahmini Süre:** 2-3 saat

---

## 📝 Notlar

- Bu standartlar proje boyunca uygulanacaktır
- Standartlar zamanla güncellenebilir (versiyon kontrolü ile)
- İstisnai durumlar dokümante edilmelidir
- Tüm geliştiriciler bu standartlara uymalıdır

---

## 🔗 İlgili Dokümantasyon

- `.cursorrules` - Proje kuralları
- `project_info_20251208_145614.md` - Proje bilgileri
- `CONTRIBUTING.md` - Katkıda bulunma rehberi
- `WORKSPACE_INDEX.md` - Workspace indeksi

---

**Son Güncelleme:** 2025-12-09 22:00:00

