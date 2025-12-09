# WiFi Bağlantı Sorunları ve Çözümleri

**Oluşturulma Tarihi:** 2025-12-08 19:10:00  
**Son Güncelleme:** 2025-12-08 19:10:00  
**Version:** 1.0.0

---

## Sorun Özeti

**Tarih:** 2025-12-08  
**Durum:** WiFi bağlantısı kurulamıyordu, yaklaşık 2 saat sorun yaşandı  
**Çözüm:** NetworkManager ile WiFi bağlantısı manuel olarak kuruldu

---

## Sistem Bilgileri

### İşletim Sistemi
- **OS:** Debian GNU/Linux 13 (Trixie)
- **Kernel:** Linux 6.12.47+rpt-rpi-v8 (Raspberry Pi kernel)
- **Architecture:** aarch64
- **Not:** RPi Lite değil, Debian tabanlı sistem

### Network Yönetimi
- **NetworkManager:** Aktif ve çalışıyor
- **wpa_supplicant:** Aktif ve çalışıyor
- **WiFi Interface:** wlan0 (BCM4345/6 chipset)

---

## Sorunun Kök Nedeni

1. **NetworkManager ve wpa_supplicant Çakışması:**
   - NetworkManager WiFi'yi yönetmeye çalışıyordu
   - wpa_supplicant konfigürasyonu (`/etc/wpa_supplicant/wpa_supplicant.conf`) vardı
   - Ancak NetworkManager WiFi bağlantısını otomatik olarak kurmuyordu

2. **WiFi Durumu:**
   - WiFi interface (wlan0) aktifti
   - Ancak "disconnected" durumundaydı
   - WiFi ağları görülebiliyordu (scan başarılı)
   - Fiziksel bağlantı sorunu yoktu

---

## Çözüm Adımları

### 1. WiFi Ağlarını Listeleme
```bash
sudo nmcli device wifi list
```

### 2. WiFi Bağlantısı Oluşturma
```bash
sudo nmcli connection add type wifi con-name "ORGE_ARGE" ifname wlan0 ssid "ORGE_ARGE" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "12345678"
```

### 3. WiFi Bağlantısını Aktifleştirme
```bash
sudo nmcli connection up "ORGE_ARGE"
```

### 4. Durum Kontrolü
```bash
nmcli device status
ip addr show wlan0
```

---

## Başarılı Bağlantı Bilgileri

**WiFi Ağı:** ORGE_ARGE  
**IP Adresi:** 10.248.244.15/24  
**Gateway:** 10.248.244.237  
**DNS:** 10.248.244.237  
**Durum:** ✅ Bağlı

---

## Önemli Notlar

### NetworkManager Kullanımı
- Debian 13'te NetworkManager varsayılan network yöneticisidir
- wpa_supplicant konfigürasyonu NetworkManager tarafından kullanılabilir
- Ancak NetworkManager kendi konfigürasyonunu tercih eder

### WiFi Konfigürasyonu
- NetworkManager ile WiFi bağlantıları `nmcli` komutu ile yönetilir
- Konfigürasyonlar `/etc/NetworkManager/system-connections/` altında saklanır
- wpa_supplicant konfigürasyonu (`/etc/wpa_supplicant/wpa_supplicant.conf`) NetworkManager tarafından kullanılabilir ama öncelik NetworkManager konfigürasyonundadır

### İşletim Sistemi Karışıklığı
- Sistem Debian 13 (Trixie) kullanıyor
- RPi Lite değil, Debian tabanlı bir sistem
- Ubuntu benzeri bir durum değil, direkt Debian
- Dosya isimleri ve yapılandırma Debian standartlarına uygun

---

## Gelecekteki Sorunlar İçin

### WiFi Bağlantısını Kontrol Etme
```bash
# WiFi durumunu kontrol et
nmcli device status

# WiFi ağlarını listele
sudo nmcli device wifi list

# WiFi bağlantılarını listele
nmcli connection show

# WiFi bağlantısını yeniden başlat
sudo nmcli connection down "ORGE_ARGE"
sudo nmcli connection up "ORGE_ARGE"
```

### WiFi Sorun Giderme
```bash
# NetworkManager durumunu kontrol et
sudo systemctl status NetworkManager

# WiFi interface durumunu kontrol et
ip addr show wlan0

# WiFi ağlarını tarama
sudo iw dev wlan0 scan

# WiFi blokajını kontrol et
rfkill list

# WiFi blokajını kaldırma (gerekirse)
sudo rfkill unblock wifi
```

### Otomatik Bağlantı İçin
WiFi bağlantısının otomatik olarak kurulması için:
1. NetworkManager konfigürasyonunu kontrol et
2. WiFi bağlantısının "auto-connect" özelliğinin aktif olduğundan emin ol
3. Gerekirse `nmcli connection modify "ORGE_ARGE" connection.autoconnect yes` komutunu kullan

---

## İlgili Dosyalar

- `/etc/wpa_supplicant/wpa_supplicant.conf` - wpa_supplicant konfigürasyonu
- `/etc/NetworkManager/system-connections/` - NetworkManager konfigürasyonları
- `/etc/netplan/` - Netplan konfigürasyonları (varsa)

---

**Son Güncelleme:** 2025-12-08 19:10:00

