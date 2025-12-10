# Diğer Proje İçin Kısa Prompt

**Kullanım:** Bu prompt'u diğer projedeki AI agent'a direkt verebilirsin.

---

## 🎯 Görev: Standartlar ve Otomasyon Sistemi Kurulumu

Referans projede (`/home/basar/charger`) başarıyla uygulanan **standartlar ve otomasyon sistemini** bu projeye kur.

### 📋 Yapılacaklar

1. **Standart Dokümantasyonları Oluştur** (`docs/standards/`)
   - `/home/basar/charger/docs/standards/` klasöründeki tüm `.md` dosyalarını oku
   - Bu projeye uyarla ve `docs/standards/` klasörüne kopyala
   - Proje kök dizini, klasör yapısı ve dosya yollarını güncelle

2. **Otomasyon Script'lerini Oluştur** (`scripts/`)
   - `/home/basar/charger/scripts/` klasöründeki `*_auto_*.py` dosyalarını oku
   - Bu projeye uyarla ve `scripts/` klasörüne kopyala
   - `PROJECT_ROOT` ve klasör yollarını güncelle
   - Script'leri çalıştırılabilir yap (`chmod +x`)

3. **`.cursorrules` Dosyasını Güncelle**
   - `/home/basar/charger/.cursorrules` dosyasını oku
   - Şu kritik kuralları ekle:
     - **KRİTİK KURAL: Kod ve Dokümantasyon Boyut Standartları**
     - **KRİTİK KURAL: Tespitlerin Todo Sistemine Eklenmesi**
     - **KRİTİK KURAL: Yedekleme ve Geri Dönüş Standartları**
     - **KRİTİK KURAL: Workspace Yönetimi Standartları**
   - Proje kök dizini ve dosya yollarını güncelle

4. **Pre-commit Hook Kur** (`.git/hooks/pre-commit`)
   - `/home/basar/charger/.git/hooks/pre-commit` dosyasını oku
   - Bu projeye uyarla ve `.git/hooks/pre-commit` dosyasına kopyala
   - Script yollarını güncelle
   - Çalıştırılabilir yap (`chmod +x`)

5. **Test Et**
   - Tüm script'leri çalıştır ve çalıştığını doğrula
   - Pre-commit hook'u test et (test commit yap)
   - Standartları doğrula

### 🔍 Referans Dosyalar

**Standart Dokümantasyonları:**
- `/home/basar/charger/docs/standards/CODE_DOCUMENTATION_STANDARDS.md`
- `/home/basar/charger/docs/standards/BACKUP_ROLLBACK_STANDARDS.md`
- `/home/basar/charger/docs/standards/WORKSPACE_MANAGEMENT_STANDARDS.md`
- `/home/basar/charger/docs/standards/TODO_AUTOMATION_STANDARDS.md`
- `/home/basar/charger/docs/standards/AUTOMATION_COMPLETE.md`

**Otomasyon Script'leri:**
- `/home/basar/charger/scripts/todo_auto_check.py`
- `/home/basar/charger/scripts/todo_auto_update.py`
- `/home/basar/charger/scripts/workspace_auto_check.py`
- `/home/basar/charger/scripts/standards_auto_check.py`
- `/home/basar/charger/scripts/code_quality_auto_check.py`

**Konfigürasyon:**
- `/home/basar/charger/.cursorrules`
- `/home/basar/charger/.git/hooks/pre-commit`

### ⚠️ Önemli Notlar

- **Proje-spesifik uyarlamalar yap:** Sadece kopyala-yapıştır yapma!
- **Proje kök dizinini güncelle:** `/home/basar/charger` → bu projenin kök dizini
- **Klasör yapısını güncelle:** Referans projedeki klasörler bu projede farklı olabilir
- **Standartları ayarla:** Projenin ihtiyaçlarına göre standartları güncelle

### ✅ Başarı Kriterleri

- [ ] Tüm standart dokümantasyonlar mevcut ve güncellenmiş
- [ ] Tüm otomasyon script'leri mevcut ve çalışıyor
- [ ] `.cursorrules` güncellenmiş ve kritik kurallar eklenmiş
- [ ] Pre-commit hook kurulmuş ve çalışıyor
- [ ] Tüm testler geçiyor

**Detaylı talimatlar için:** `/home/basar/charger/docs/STANDARDS_MIGRATION_PROMPT.md` dosyasına bak.

---

**Hazır! Bu prompt'u diğer projedeki agent'a verebilirsin.** 🚀

