# Sorun Giderme - AC Charger

**Oluşturulma Tarihi:** 2025-12-09 22:40:00
**Son Güncelleme:** 2025-12-09 22:40:00
**Version:** 1.0.0

---

## ESP32-RPi USB Bağlantı Kontrolü ve İzleme (2025-12-08 15:53:47)
- **Sorun Tespiti:** Herhangi bir sorun olduğunda ESP32 ve RPi arasında fiziksel bir sorun var mı diye bakmak için istenildiği zaman RPi'den USB'yi kullanabilecek herhangi bir şey var mı diye kontrol edilmelidir
- **USB Temizleme:** Gerekirse USB'yi temizleyip 115200 baudrate ile izleme yapılmalıdır
- **İzleme Süresi:** ESP32'den rutin bilgi formatı geliyor mu kontrolü için 10-15 saniye izleme yapılmalıdır
- **Baudrate:** 115200
- **Kontrol Mekanizması:** USB bağlantısını kontrol etmek, USB'yi temizlemek ve izleme yapmak için gerekli araçlar kullanılmalıdır
- **Beklenen Davranış:** ESP32'den her 5 saniyede bir `<STAT;...>` formatında durum bilgileri gelmelidir
- **Durum Değerlendirme Kriteri:** Rutin bilgiler gelmeye devam ettikçe ESP32'nin durumunun aktif ve sorunsuz olduğu kabul edilmelidir

_(Bu bölüm çalışmalar ilerledikçe güncellenecek)_

---

### WiFi Failover Sistemi (2025-12-08 19:20:00)

**Genel Bakış:**
WiFi failover sistemi, sistemin otomatik olarak 4 farklı WiFi ağına bağlanmasını ve internet erişimi kontrolü yapmasını sağlar. Internet erişimi 20 saniye boyunca olmazsa, sistem otomatik olarak bir sonraki WiFi ağına geçer.

**WiFi Ağları ve Öncelik Sırası:**
- **Öncelik 10:** ORGE_ARGE (12345678)
- **Öncelik 9:** ORGE_DEPO (1234554321)
- **Öncelik 8:** ORGE_EV (1234554321)
- **Öncelik 7:** ERTAC (12345678)

**Sistem Bileşenleri:**
- NetworkManager konfigürasyonu (otomatik bağlanma, öncelik sırası)
- WiFi Failover Monitor Script (`scripts/wifi_failover_monitor.py`)
- Systemd servisi (`scripts/wifi-failover-monitor.service`)

**Internet Kontrol Parametreleri:**
- Kontrol aralığı: 5 saniye
- Failover threshold: 20 saniye internet erişimi yoksa
- Kontrol URL'leri: `8.8.8.8`, `1.1.1.1`, `google.com`

Detaylı kurulum için: `WIFI_FAILOVER_SETUP.md` (konsolide edilecek)

## Hatalardan Çıkarılan Dersler

_(Bu bölüm karşılaşılan hatalar ve çözümleri ile güncellenecek)_

---

