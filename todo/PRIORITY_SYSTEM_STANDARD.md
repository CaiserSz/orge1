# Öncelik Sistemi Standardı

**Oluşturulma Tarihi:** 2025-12-10 09:35:00
**Son Güncelleme:** 2025-12-10 09:35:00
**Version:** 1.0.0

---

## 🎯 Amaç

Bu dokümantasyon, proje genelinde tutarlı bir öncelik sistemi sağlamak için oluşturulmuştur.

---

## 📊 Öncelik Seviyeleri

### Öncelik 0: Acil (Kritik Sorunlar)
- **Açıklama:** Hemen çözülmesi gereken kritik sorunlar
- **Kriterler:**
  - Standart ihlalleri (dosya boyutu limit aşımı)
  - Kritik güvenlik açıkları
  - Sistem çökmesine neden olabilecek hatalar
  - Veri kaybına neden olabilecek sorunlar
- **Örnekler:**
  - Dosya boyutu maksimum sınırı aştı (638 satır > 600 limit)
  - Kritik güvenlik açığı tespit edildi
  - Database corruption riski

### Öncelik 1-2: Yüksek (Kritik Özellikler)
- **Açıklama:** Projenin temel işlevselliği için kritik özellikler
- **Kriterler:**
  - Core functionality için gerekli
  - Kullanıcı deneyimini doğrudan etkileyen
  - Sistemin çalışması için zorunlu
- **Örnekler:**
  - Event Detection modülü
  - Session Management modülü
  - API endpoint'leri
  - Database entegrasyonu

### Öncelik 3-5: Orta (Önemli Özellikler)
- **Açıklama:** Projenin işlevselliğini artıran önemli özellikler
- **Kriterler:**
  - Kullanıcı deneyimini iyileştiren
  - Sistem performansını artıran
  - İş mantığı için önemli ama kritik olmayan
- **Örnekler:**
  - Session Summary Generation
  - Test Coverage Artırma
  - Code Quality Tools
  - Workspace Temizliği

### Öncelik 6-8: Düşük/Opsiyonel (İyileştirmeler)
- **Açıklama:** İsteğe bağlı iyileştirmeler ve optimizasyonlar
- **Kriterler:**
  - Nice-to-have özellikler
  - Gelecek faz için planlanan
  - Performans optimizasyonları
  - Kod kalitesi iyileştirmeleri
- **Örnekler:**
  - CI/CD Pipeline
  - Session Analytics
  - Advanced Monitoring
  - Code Refactoring (opsiyonel)

---

## 📋 Öncelik Belirleme Kriterleri

### 1. Etki Analizi
- **Yüksek Etki:** Öncelik 0-2
- **Orta Etki:** Öncelik 3-5
- **Düşük Etki:** Öncelik 6-8

### 2. Aciliyet Analizi
- **Acil:** Öncelik 0
- **Yüksek:** Öncelik 1-2
- **Orta:** Öncelik 3-5
- **Düşük:** Öncelik 6-8

### 3. Bağımlılık Analizi
- **Bağımlılık Yok:** Öncelik belirlemede etkili değil
- **Bağımlılık Var:** Bağımlılık tamamlandıktan sonra öncelik artabilir

---

## 🔄 Öncelik Güncelleme Kuralları

1. **Standart İhlali:** Öncelik 0'a yükseltilir
2. **Kritik Sorun:** Öncelik 0'a yükseltilir
3. **Bağımlılık Tamamlandı:** Öncelik artırılabilir
4. **Zaman Aşımı:** Öncelik artırılabilir

---

## 📝 Görev Formatı

```markdown
#### Öncelik X: [Görev Başlığı] ([Kategori])
- [ ] **Görev:** [Görev açıklaması]
  - Açıklama: [Detaylı açıklama]
  - Öncelik: X ([Acil/Yüksek/Orta/Düşük])
  - Tahmini Süre: [Süre]
  - Durum: [Durum]
  - Bağımlılıklar: [Bağımlılıklar]
```

---

**Son Güncelleme:** 2025-12-10 09:35:00

