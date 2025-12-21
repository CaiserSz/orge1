# Backup Strategy Documentation

**Oluşturulma Tarihi:** 2025-12-10 17:00:00
**Son Güncelleme:** 2025-12-22 00:10:00
**Versiyon:** 1.1.0

---

## Genel Bakış

Charger API projesi için kapsamlı backup stratejisi. Database, configuration ve data dosyalarının otomatik yedeklenmesi sağlanır.

---

## Backup Kapsamı

### 1. Database Backup

**Dosya:** `data/sessions.db`
**Backup Format:** SQLite database (compressed .gz)
**Backup Frequency:** Günlük (02:00 AM)
**Retention:** 7 gün

**Özellikler:**
- SQLite VACUUM INTO kullanarak temiz backup oluşturur
- WAL dosyaları dahil edilmez (clean backup)
- Gzip ile sıkıştırılır
- Timestamp ile isimlendirilir: `sessions_db_YYYYMMDD_HHMMSS.db.gz`

### 2. Configuration Backup

**Dosyalar:**
- `.env` - Environment variables
- `data/station_info.json` - Station information

**Backup Format:** Tar.gz archive
**Backup Frequency:** Günlük (02:00 AM)
**Retention:** 7 gün

**Özellikler:**
- Tüm configuration dosyaları tek bir archive'de
- Timestamp ile isimlendirilir: `config_YYYYMMDD_HHMMSS.tar.gz`

### 3. Backup Manifest

Her backup işlemi sonrası manifest dosyası oluşturulur:
- Backup timestamp
- Backup dosya yolları
- Backup durumu

**Format:** JSON
**Dosya:** `manifest_YYYYMMDD_HHMMSS.json`

---

## Backup Manager Script

### Kullanım

```bash
# Tüm backup'ları oluştur
python3 scripts/backup_manager.py

# Sadece database backup
python3 scripts/backup_manager.py --database-only

# Sadece configuration backup
python3 scripts/backup_manager.py --config-only

# Backup listesi
python3 scripts/backup_manager.py --list

# Eski backup'ları temizle (7 günden eski)
python3 scripts/backup_manager.py --cleanup 7

# Sıkıştırma olmadan backup
python3 scripts/backup_manager.py --no-compress
```

### Parametreler

- `--backup-dir`: Backup dizini (varsayılan: `backups/`)
- `--no-compress`: Database backup'ları sıkıştırma
- `--cleanup DAYS`: Belirtilen günden eski backup'ları sil
- `--list`: Tüm backup dosyalarını listele
- `--database-only`: Sadece database backup
- `--config-only`: Sadece configuration backup

---

## Automated Backup Setup

### Systemd Timer Kullanımı

1. **Service ve Timer dosyalarını kopyala:**

```bash
sudo cp scripts/backup.service /etc/systemd/system/
sudo cp scripts/backup.timer /etc/systemd/system/
```

Not:
- `scripts/backup.service` içinde `User/Group` projenin ana kullanıcı hesabına uygun olmalıdır (bu repo için: `basar`).
- Backup artefact’ları (`backups/`) git’e girmemelidir (`.gitignore` içinde ignore edilir).

2. **Timer'ı aktif et:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable backup.timer
sudo systemctl start backup.timer
```

3. **Timer durumunu kontrol et:**

```bash
sudo systemctl status backup.timer
sudo systemctl list-timers backup.timer
```

4. **Manuel backup çalıştır:**

```bash
sudo systemctl start backup.service
```

### Cron Job Alternatifi

Eğer systemd timer kullanmak istemiyorsanız, cron job kullanabilirsiniz:

```bash
# Crontab düzenle
crontab -e

# Günlük 02:00'da backup çalıştır
0 2 * * * cd /home/basar/charger && /home/basar/charger/env/bin/python3 /home/basar/charger/scripts/backup_manager.py >> /home/basar/charger/logs/backup.log 2>&1
```

---

## Backup Restore

### Database Restore

```bash
# Compressed backup'ı aç
gunzip backups/sessions_db_YYYYMMDD_HHMMSS.db.gz

# Database'i restore et
cp backups/sessions_db_YYYYMMDD_HHMMSS.db data/sessions.db

# Veya SQLite ile restore
sqlite3 data/sessions.db < backups/sessions_db_YYYYMMDD_HHMMSS.db
```

### Configuration Restore

```bash
# Archive'ı aç
tar -xzf backups/config_YYYYMMDD_HHMMSS.tar.gz

# Dosyaları restore et
cp .env.backup .env
cp station_info.json.backup data/station_info.json
```

---

## Backup Monitoring

### Log Kontrolü

Backup işlemleri system log'larına yazılır:

```bash
# Systemd service log'ları
sudo journalctl -u backup.service -f

# Son backup log'ları
sudo journalctl -u backup.service --since "1 hour ago"
```

### Backup Durumu Kontrolü

```bash
# Backup dosyalarını listele
python3 scripts/backup_manager.py --list

# Backup dizinini kontrol et
ls -lh backups/
```

---

## Best Practices

1. **Regular Testing:**
   - Backup'ları düzenli olarak test edin
   - Restore işlemini test edin

2. **Offsite Backup:**
   - Kritik backup'ları uzak bir yere kopyalayın
   - Cloud storage kullanabilirsiniz

3. **Backup Verification:**
   - Backup dosyalarının bütünlüğünü kontrol edin
   - Database backup'larını test edin

4. **Retention Policy:**
   - 7 günlük retention policy uygulanır
   - Kritik backup'ları daha uzun süre saklayın

5. **Monitoring:**
   - Backup başarısızlıklarını izleyin
   - Alerting mekanizması kurun

---

## Troubleshooting

### Backup Başarısız Olursa

1. **Log'ları kontrol et:**
   ```bash
   sudo journalctl -u backup.service -n 50
   ```

2. **Manuel backup çalıştır:**
   ```bash
   python3 scripts/backup_manager.py
   ```

3. **Disk alanını kontrol et:**
   ```bash
   df -h
   ```

4. **Backup dizini izinlerini kontrol et:**
   ```bash
   ls -ld backups/
   ```

### Database Backup Sorunları

- SQLite WAL dosyaları varsa, database'i kapatın
- Database lock hatası alırsanız, API servisini durdurun

### Configuration Backup Sorunları

- `.env` dosyası yoksa, backup atlanır (warning log'lanır)
- `station_info.json` yoksa, backup atlanır (warning log'lanır)

---

## İlgili Dosyalar

- `scripts/backup_manager.py` - Backup manager script
- `scripts/backup.service` - Systemd service dosyası
- `scripts/backup.timer` - Systemd timer dosyası
- `backups/` - Backup dizini
- `data/sessions.db` - SQLite database
- `.env` - Environment variables
- `data/station_info.json` - Station information

---

## Gelecek İyileştirmeler

- [ ] Cloud storage entegrasyonu (S3, Google Cloud Storage)
- [ ] Incremental backup desteği
- [ ] Backup encryption
- [ ] Backup verification otomasyonu
- [ ] Email/SMS alerting
- [ ] Backup metrics ve monitoring dashboard

---

**Son Güncelleme:** 2025-12-10 17:00:00

