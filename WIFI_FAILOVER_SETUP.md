# WiFi Failover Sistemi Kurulumu

**Oluşturulma Tarihi:** 2025-12-08 19:20:00  
**Son Güncelleme:** 2025-12-08 19:20:00  
**Version:** 1.0.0

---

## Genel Bakış

WiFi failover sistemi, sistemin otomatik olarak 4 farklı WiFi ağına bağlanmasını ve internet erişimi kontrolü yapmasını sağlar. Internet erişimi 20 saniye boyunca olmazsa, sistem otomatik olarak bir sonraki WiFi ağına geçer.

---

## WiFi Ağları ve Öncelik Sırası

| Öncelik | SSID | Şifre | Açıklama |
|---------|------|-------|----------|
| 10 (En Yüksek) | ORGE_ARGE | 12345678 | Birincil ağ |
| 9 | ORGE_DEPO | 1234554321 | Yedek ağ 1 |
| 8 | ORGE_EV | 1234554321 | Yedek ağ 2 |
| 7 (En Düşük) | ERTAC | 12345678 | Yedek ağ 3 |

---

## Sistem Bileşenleri

### 1. NetworkManager Konfigürasyonu

Tüm WiFi ağları NetworkManager ile tanımlanmıştır ve otomatik bağlanma aktif edilmiştir. Öncelik sırası `connection.autoconnect-priority` parametresi ile belirlenir.

**Mevcut Bağlantılar:**
- `ORGE_ARGE` (Priority: 10)
- `ORGE_DEPO` (Priority: 9)
- `ORGE_EV` (Priority: 8)
- `ERTAC` (Priority: 7)

### 2. WiFi Failover Monitor Script

**Dosya:** `/home/basar/charger/scripts/wifi_failover_monitor.py`

**Özellikler:**
- Aktif WiFi bağlantısını izler
- Internet erişimini kontrol eder (5 saniyede bir)
- 20 saniye boyunca internet erişimi yoksa failover yapar
- Otomatik olarak bir sonraki WiFi ağına geçer
- Tüm ağlar denendikten sonra başa döner

**Internet Kontrol Parametreleri:**
- Kontrol aralığı: 5 saniye
- Timeout süresi: 20 saniye
- Kontrol edilen hostlar: `8.8.8.8`, `1.1.1.1`, `google.com`
- Ping sayısı: 2
- Ping timeout: 3 saniye

### 3. Systemd Servisi

**Dosya:** `/etc/systemd/system/wifi-failover-monitor.service`

**Özellikler:**
- Sistem açılışında otomatik başlar
- Hata durumunda otomatik yeniden başlar
- Loglar: `/var/log/wifi_failover.log` ve systemd journal

---

## Kurulum Komutları

### WiFi Bağlantılarını Oluşturma

```bash
# ORGE_ARGE (Priority: 10)
sudo nmcli connection add type wifi con-name "ORGE_ARGE" ifname wlan0 ssid "ORGE_ARGE" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "12345678" connection.autoconnect yes connection.autoconnect-priority 10

# ORGE_DEPO (Priority: 9)
sudo nmcli connection add type wifi con-name "ORGE_DEPO" ifname wlan0 ssid "ORGE_DEPO" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "1234554321" connection.autoconnect yes connection.autoconnect-priority 9

# ORGE_EV (Priority: 8)
sudo nmcli connection add type wifi con-name "ORGE_EV" ifname wlan0 ssid "ORGE_EV" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "1234554321" connection.autoconnect yes connection.autoconnect-priority 8

# ERTAC (Priority: 7)
sudo nmcli connection add type wifi con-name "ERTAC" ifname wlan0 ssid "ERTAC" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "12345678" connection.autoconnect yes connection.autoconnect-priority 7
```

### Servis Kurulumu

```bash
# Servis dosyasını kopyala
sudo cp /home/basar/charger/scripts/wifi-failover-monitor.service /etc/systemd/system/

# Systemd'yi yeniden yükle
sudo systemctl daemon-reload

# Servisi aktifleştir (otomatik başlatma)
sudo systemctl enable wifi-failover-monitor.service

# Servisi başlat
sudo systemctl start wifi-failover-monitor.service
```

---

## Kullanım

### Servis Yönetimi

```bash
# Servis durumunu kontrol et
sudo systemctl status wifi-failover-monitor.service

# Servisi başlat
sudo systemctl start wifi-failover-monitor.service

# Servisi durdur
sudo systemctl stop wifi-failover-monitor.service

# Servisi yeniden başlat
sudo systemctl restart wifi-failover-monitor.service

# Logları görüntüle
sudo journalctl -u wifi-failover-monitor.service -f

# Log dosyasını görüntüle
tail -f /var/log/wifi_failover.log
```

### WiFi Bağlantılarını Yönetme

```bash
# Tüm WiFi bağlantılarını listele
nmcli connection show | grep wifi

# Belirli bir bağlantının detaylarını görüntüle
nmcli connection show "ORGE_ARGE"

# WiFi bağlantısını aktifleştir
sudo nmcli connection up "ORGE_ARGE"

# WiFi bağlantısını deaktifleştir
sudo nmcli connection down "ORGE_ARGE"

# WiFi bağlantısını sil
sudo nmcli connection delete "ORGE_ARGE"
```

---

## Çalışma Mantığı

1. **Sistem Başlangıcı:**
   - NetworkManager en yüksek öncelikli ağa (ORGE_ARGE) otomatik bağlanır
   - WiFi Failover Monitor servisi başlar

2. **Normal Çalışma:**
   - Monitor script her 5 saniyede bir internet erişimini kontrol eder
   - Internet erişimi varsa, mevcut bağlantı korunur

3. **Internet Erişimi Yok:**
   - 20 saniye boyunca internet erişimi yoksa failover tetiklenir
   - Sistem bir sonraki öncelikli WiFi ağına geçer
   - Bağlantı başarılı olursa internet kontrolü devam eder
   - Bağlantı başarısız olursa bir sonraki ağa geçer

4. **Tüm Ağlar Denendi:**
   - Tüm ağlar denendikten sonra sistem başa döner (ORGE_ARGE)
   - Döngü devam eder

---

## Loglar

### Systemd Journal

```bash
# Son 50 satır
sudo journalctl -u wifi-failover-monitor.service -n 50

# Canlı log takibi
sudo journalctl -u wifi-failover-monitor.service -f

# Belirli bir tarihten itibaren
sudo journalctl -u wifi-failover-monitor.service --since "2025-12-08 19:00:00"
```

### Log Dosyası

```bash
# Son 50 satır
tail -n 50 /var/log/wifi_failover.log

# Canlı log takibi
tail -f /var/log/wifi_failover.log

# Hata loglarını filtrele
grep ERROR /var/log/wifi_failover.log
```

---

## Sorun Giderme

### WiFi Bağlantısı Kurulmuyor

1. WiFi interface'ini kontrol et:
   ```bash
   ip addr show wlan0
   nmcli device status
   ```

2. WiFi ağlarını tarama:
   ```bash
   sudo nmcli device wifi list
   ```

3. NetworkManager durumunu kontrol et:
   ```bash
   sudo systemctl status NetworkManager
   ```

### Internet Kontrolü Çalışmıyor

1. Ping testi yap:
   ```bash
   ping -c 3 8.8.8.8
   ping -c 3 google.com
   ```

2. DNS çözümlemesini kontrol et:
   ```bash
   cat /etc/resolv.conf
   nslookup google.com
   ```

3. Monitor script'i manuel çalıştır:
   ```bash
   sudo python3 /home/basar/charger/scripts/wifi_failover_monitor.py
   ```

### Servis Başlamıyor

1. Servis durumunu kontrol et:
   ```bash
   sudo systemctl status wifi-failover-monitor.service
   ```

2. Servis loglarını kontrol et:
   ```bash
   sudo journalctl -u wifi-failover-monitor.service -n 100
   ```

3. Script'i manuel çalıştır:
   ```bash
   sudo python3 /home/basar/charger/scripts/wifi_failover_monitor.py
   ```

---

## Yapılandırma Değişiklikleri

### Internet Kontrol Parametrelerini Değiştirme

`/home/basar/charger/scripts/wifi_failover_monitor.py` dosyasında:

```python
INTERNET_CHECK_TIMEOUT = 20  # saniye (20 saniye)
INTERNET_CHECK_INTERVAL = 5  # saniye (5 saniyede bir kontrol)
INTERNET_CHECK_HOSTS = ["8.8.8.8", "1.1.1.1", "google.com"]
PING_COUNT = 2
PING_TIMEOUT = 3
```

Değişiklikten sonra servisi yeniden başlat:
```bash
sudo systemctl restart wifi-failover-monitor.service
```

### WiFi Ağı Ekleme/Çıkarma

Yeni bir WiFi ağı eklemek için:

```bash
sudo nmcli connection add type wifi con-name "YENI_AG" ifname wlan0 ssid "YENI_SSID" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "SIFRE" connection.autoconnect yes connection.autoconnect-priority 6
```

Script'teki `WIFI_NETWORKS` listesine de ekle:
```python
WIFI_NETWORKS = [
    ("ORGE_ARGE", 10),
    ("ORGE_DEPO", 9),
    ("ORGE_EV", 8),
    ("ERTAC", 7),
    ("YENI_AG", 6),  # Yeni ağ
]
```

---

## Güvenlik Notları

- WiFi şifreleri NetworkManager konfigürasyonlarında saklanır
- Konfigürasyon dosyaları root yetkisi gerektirir
- Log dosyası `/var/log/wifi_failover.log` root yetkisi ile yazılır
- Servis root kullanıcısı olarak çalışır

---

**Son Güncelleme:** 2025-12-08 19:20:00


