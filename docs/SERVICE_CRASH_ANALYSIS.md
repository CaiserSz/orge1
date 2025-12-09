# Servis Çökme Analizi ve Çözüm Raporu

**Oluşturulma Tarihi:** 2025-12-10 01:15:00
**Son Güncelleme:** 2025-12-10 01:15:00
**Version:** 1.0.0

---

## 🔴 Sorun Tespiti

### 1. Servis Yönetimi Sorunu

**Mevcut Durum:**
- `charger.service` sadece `ocpp/main.py` çalıştırıyor (basit bir loop)
- API servisi (`uvicorn api.main:app`) **manuel olarak başlatılmış** (nohup ile)
- API servisi **systemd tarafından yönetilmiyor**
- Servis çöktüğünde **otomatik restart yok**

**Kanıt:**
```bash
# charger.service sadece ocpp/main.py çalıştırıyor
ExecStart=/home/basar/env/bin/python /home/basar/charger/ocpp/main.py

# API servisi manuel başlatılmış
basar 165162 ... uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### 2. Çökme Nedeni Analizi

**Tespit Edilen Durumlar:**

1. **Servis Çökmesi (502 Bad Gateway):**
   - Tarih: 2025-12-10 01:10:00 - 01:12:00 arası
   - Süre: ~2 dakika
   - Neden: Manuel başlatılan servis çöktü, otomatik restart yok

2. **Sistem Kaynakları:**
   - RAM: 1.0Gi kullanılıyor / 3.7Gi toplam (✅ Normal)
   - Disk: 5.9G kullanılıyor / 15G toplam (✅ Normal)
   - CPU Load: 0.41 (✅ Normal)
   - **Kaynak yetersizliği yok**

3. **Log Analizi:**
   - System log'da test mock hataları var (test ortamından kalmış)
   - API log'da normal istekler var, kritik hata yok
   - Kernel log'da OOM veya segfault yok

### 3. Neden Oldu?

**Muhtemel Nedenler:**

1. **Manuel Başlatma:**
   - Servis `nohup` ile manuel başlatılmış
   - Process management yok
   - Çökme durumunda otomatik restart yok

2. **Process Çakışması:**
   - Eski process kill edilirken yeni process başlatılmış
   - Geçiş sırasında servis erişilemez olmuş

3. **Ngrok Timeout:**
   - Backend servis çöktüğünde ngrok 502 döndürmüş
   - Frontend sürekli 502 hatası almış

### 4. Tekrarlayacak mı?

**EVET, tekrarlayacak çünkü:**
- ✅ Servis hala manuel yönetiliyor
- ✅ Otomatik restart mekanizması yok
- ✅ Health check ve monitoring yok
- ✅ Process management yok

---

## ✅ Çözüm Planı

### 1. Systemd Service Oluşturma

**Hedef:** API servisini systemd ile yönetmek

**Avantajlar:**
- Otomatik restart (Restart=always)
- Process management
- Log yönetimi (journalctl)
- Sistem açılışında otomatik başlatma
- Health check ve monitoring

### 2. Health Check Endpoint

**Hedef:** Servis sağlığını kontrol etmek

**Özellikler:**
- `/api/health` endpoint'i zaten var
- Systemd service'te health check eklenebilir
- Monitoring script'i ile düzenli kontrol

### 3. Monitoring ve Alerting

**Hedef:** Servis durumunu izlemek ve sorunları erken tespit etmek

**Özellikler:**
- Health check script'i
- Log monitoring
- Alert mekanizması (opsiyonel)

### 4. Process Management İyileştirmesi

**Hedef:** Process çakışmalarını önlemek

**Özellikler:**
- Systemd ile tek process garantisi
- Graceful shutdown
- Process isolation

---

## 📋 Uygulama Adımları

### Adım 1: Systemd Service Dosyası Oluşturma
- `charger-api.service` dosyası oluşturulacak
- API servisi için özel service

### Adım 2: Mevcut Servisi Durdurma
- Manuel başlatılan servis durdurulacak
- Systemd service aktif edilecek

### Adım 3: Health Check ve Monitoring
- Health check script'i eklenecek
- Monitoring mekanizması kurulacak

### Adım 4: Test ve Doğrulama
- Servis başlatılacak
- Health check test edilecek
- Monitoring çalıştırılacak

---

## 🔍 Monitoring ve Alerting Önerileri

### 1. Health Check Script
- Her 30 saniyede bir `/api/health` kontrolü
- Başarısız olursa servisi restart et
- Log'a kaydet

### 2. Log Monitoring
- ERROR ve CRITICAL logları izle
- Anormal durumları tespit et
- Alert gönder (opsiyonel)

### 3. Resource Monitoring
- CPU, RAM, Disk kullanımını izle
- Eşik değerleri aşılırsa uyar
- Log'a kaydet

---

## 📊 Beklenen İyileştirmeler

### Öncesi:
- ❌ Manuel servis yönetimi
- ❌ Otomatik restart yok
- ❌ Monitoring yok
- ❌ Process çakışması riski

### Sonrası:
- ✅ Systemd ile otomatik yönetim
- ✅ Otomatik restart (Restart=always)
- ✅ Health check ve monitoring
- ✅ Process çakışması önlendi
- ✅ Log yönetimi (journalctl)
- ✅ Sistem açılışında otomatik başlatma

---

## 🎯 Sonuç

**Sorun:** API servisi manuel yönetiliyor, çöktüğünde otomatik restart yok.

**Çözüm:** Systemd service oluşturma, health check ve monitoring ekleme.

**Beklenen Sonuç:** Servis çökmesi durumunda otomatik restart, sürekli monitoring ve erken uyarı.

---

## 📝 Notlar

- Mevcut `charger.service` OCPP servisi için kullanılıyor
- API servisi için ayrı bir service (`charger-api.service`) oluşturulacak
- Her iki servis bağımsız çalışacak
- Monitoring script'i opsiyonel olarak eklenecek

