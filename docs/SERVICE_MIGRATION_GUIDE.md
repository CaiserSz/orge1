# Servis Migrasyon Rehberi

**Oluşturulma Tarihi:** 2025-12-10 01:15:00
**Son Güncelleme:** 2025-12-10 01:15:00
**Version:** 1.0.0

---

## 🔄 Manuel Servisten Systemd Service'e Geçiş

### Önceki Durum
- API servisi manuel olarak `nohup` ile başlatılıyordu
- Otomatik restart yoktu
- Process management yoktu
- Monitoring yoktu

### Yeni Durum
- API servisi systemd ile yönetiliyor
- Otomatik restart (Restart=always)
- Process management
- Log yönetimi (journalctl)
- Sistem açılışında otomatik başlatma

---

## 📋 Servis Yönetimi Komutları

### Servis Durumu Kontrolü
```bash
sudo systemctl status charger-api.service
```

### Servisi Başlatma
```bash
sudo systemctl start charger-api.service
```

### Servisi Durdurma
```bash
sudo systemctl stop charger-api.service
```

### Servisi Yeniden Başlatma
```bash
sudo systemctl restart charger-api.service
```

### Servisi Otomatik Başlatma (Enable)
```bash
sudo systemctl enable charger-api.service
```

### Servisi Otomatik Başlatmayı Kaldırma (Disable)
```bash
sudo systemctl disable charger-api.service
```

### Servis Loglarını Görüntüleme
```bash
# Son loglar
sudo journalctl -u charger-api.service -n 50

# Canlı log takibi
sudo journalctl -u charger-api.service -f

# Belirli bir tarihten itibaren
sudo journalctl -u charger-api.service --since "1 hour ago"

# Bugünkü loglar
sudo journalctl -u charger-api.service --since today
```

---

## 🔍 Health Check ve Monitoring

### Health Check Endpoint
```bash
curl http://localhost:8000/api/health
```

### Health Monitor Script'i
```bash
# Manuel çalıştırma
python3 scripts/api_health_monitor.py

# Arka planda çalıştırma
nohup python3 scripts/api_health_monitor.py > /dev/null 2>&1 &

# Systemd service olarak çalıştırma (opsiyonel)
# scripts/api-health-monitor.service dosyası oluşturulabilir
```

---

## 🛠️ Sorun Giderme

### Servis Başlamıyorsa
1. Logları kontrol edin:
   ```bash
   sudo journalctl -u charger-api.service -n 100
   ```

2. Service dosyasını kontrol edin:
   ```bash
   sudo systemctl cat charger-api.service
   ```

3. Port kullanımını kontrol edin:
   ```bash
   sudo netstat -tulpn | grep 8000
   ```

### Servis Çöküyorsa
1. Logları inceleyin:
   ```bash
   sudo journalctl -u charger-api.service --since "10 minutes ago"
   ```

2. Health check yapın:
   ```bash
   curl http://localhost:8000/api/health
   ```

3. Servisi restart edin:
   ```bash
   sudo systemctl restart charger-api.service
   ```

### Port Çakışması
Eğer port 8000 kullanılıyorsa:
1. Kullanan process'i bulun:
   ```bash
   sudo lsof -i :8000
   ```

2. Process'i durdurun veya port'u değiştirin

---

## 📊 Monitoring Önerileri

### 1. Health Check Monitoring
- Health monitor script'i düzenli çalıştırın
- Başarısız kontrolleri loglayın
- Eşik değerleri aşılırsa alert gönderin

### 2. Log Monitoring
- ERROR ve CRITICAL logları izleyin
- Anormal durumları tespit edin
- Log rotation yapılandırın

### 3. Resource Monitoring
- CPU, RAM, Disk kullanımını izleyin
- Eşik değerleri aşılırsa uyarın
- Performance metriklerini toplayın

---

## ✅ Doğrulama Checklist

- [ ] Servis başlatıldı mı?
  ```bash
  sudo systemctl status charger-api.service
  ```

- [ ] API erişilebilir mi?
  ```bash
  curl http://localhost:8000/api/health
  ```

- [ ] Loglar çalışıyor mu?
  ```bash
  sudo journalctl -u charger-api.service -n 10
  ```

- [ ] Otomatik başlatma aktif mi?
  ```bash
  sudo systemctl is-enabled charger-api.service
  ```

- [ ] Process çalışıyor mu?
  ```bash
  ps aux | grep uvicorn
  ```

---

## 🔄 Geri Dönüş (Rollback)

Eğer systemd service ile sorun yaşarsanız:

1. Servisi durdurun:
   ```bash
   sudo systemctl stop charger-api.service
   sudo systemctl disable charger-api.service
   ```

2. Manuel başlatın (geçici çözüm):
   ```bash
   cd /home/basar/charger
   source env/bin/activate
   nohup uvicorn api.main:app --host 0.0.0.0 --port 8000 > /tmp/api.log 2>&1 &
   ```

3. Sorunları çözün ve tekrar systemd service'i kullanın

---

## 📝 Notlar

- `charger.service` OCPP servisi için kullanılıyor
- `charger-api.service` API servisi için kullanılıyor
- Her iki servis bağımsız çalışıyor
- Health monitor script'i opsiyonel olarak eklenebilir

