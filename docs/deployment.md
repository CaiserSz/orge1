# Deployment Kılavuzu - AC Charger

**Oluşturulma Tarihi:** 2025-12-09 22:40:00  
**Son Güncelleme:** 2025-12-09 22:40:00  
**Version:** 1.0.0

---

## Ngrok Yapılandırması ve Dışarıdan Erişim (2025-12-08 17:13:10)

#### Genel Bilgiler
- **Ngrok Versiyonu:** v3.34.0
- **Yapılandırma Dosyası:** `/home/basar/charger/ngrok.yml`
- **Servis Durumu:** ✅ Sistem servisi olarak kurulu ve aktif
- **Otomatik Başlatma:** ✅ Sistem açılışında otomatik başlatma aktif (enabled)

#### Yapılandırma Detayları

**HTTP/HTTPS Tunnel (API, Web ve CSMS):**
- **Public URL:** `https://lixhium.ngrok.app`
- **Local Address:** `http://localhost:8000`
- **Domain:** `lixhium.ngrok.app` (Reserved Domain)
- **Domain ID:** `rd_2xYXpwyNNgABarNketjeXYIKzQ4`
- **Desteklenen Protokoller:**
  - HTTP/HTTPS (REST API, Web UI)
  - WebSocket (OCPP/CSMS bağlantıları için)
- **Kullanım Alanları:**
  - REST API endpoint'leri
  - Web arayüzü
  - OCPP WebSocket bağlantıları (CSMS ile haberleşme)
- **Durum:** ✅ Aktif ve dışarıdan erişilebilir

**SSH Tunnel:**
- **Public URL:** Dinamik adres (servis yeniden başlatıldığında değişebilir)
- **Local Address:** `localhost:22` (SSH servisi)
- **Durum:** ✅ Aktif ve dışarıdan erişilebilir
- **Kullanım:** Dışarıdan SSH erişimi için

#### Kimlik Doğrulama
- **AUTHTOKEN:** `ngrok.yml` dosyasında tanımlı
- **NGROK_API_KEY:** `.env` dosyasında tanımlı (`32AHSFuAnr3dEqbISzXQj8LT2bT_89vhksjQHgjV3Z644eDk3`)
- **API Bağlantısı:** ✅ Ngrok API'ye başarıyla bağlanıldı

#### Servis Yönetimi Komutları
```bash
# Servis durumunu kontrol etme
sudo systemctl status ngrok

# Servisi başlatma
sudo systemctl start ngrok

# Servisi durdurma
sudo systemctl stop ngrok

# Servisi yeniden başlatma
sudo systemctl restart ngrok

# Servis loglarını görüntüleme
sudo journalctl -u ngrok -f
```

#### Ngrok Web Arayüzü
- **URL:** `http://localhost:4040`
- **Erişim:** Sadece localhost'tan erişilebilir
- **API Endpoint:** `http://localhost:4040/api/tunnels` (tunnel bilgilerini JSON formatında döner)

#### Dışarıdan Erişim

**1. API ve Web Erişimi:**
- **URL:** `https://lixhium.ngrok.app`
- **Hedef:** RPi'deki port 8000
- **Kullanım:** 
  - REST API endpoint'leri
  - Web arayüzü
  - HTTP/HTTPS servisleri

**2. CSMS (OCPP) WebSocket Bağlantısı:**
- **WebSocket URL:** `wss://lixhium.ngrok.app` (HTTP tunnel üzerinden WebSocket upgrade)
- **Hedef:** RPi'deki port 8000 (OCPP WebSocket servisi)
- **Kullanım:** 
  - OCPP 1.6J WebSocket bağlantıları
  - OCPP 2.0.1 WebSocket bağlantıları
  - CSMS (Central System Management System) ile haberleşme
- **Not:** HTTP tunnel WebSocket'i destekler, ayrı bir tunnel gerekmez

**3. SSH Erişimi:**
- **Adres:** `10.tcp.eu.ngrok.io:23953` (Statik Reserved TCP Address - ücretli)
- **Reserved Address ID:** `ra_36ZCqDzm6GZVPUSaZ6T7bF9E2No`
- **Hedef:** RPi SSH servisi (port 22)
- **Kullanım:** Dışarıdan SSH bağlantısı
- **Durum:** ✅ Statik adres kullanılıyor, servis yeniden başlatıldığında değişmez
- **SSH Komutu:**
  ```bash
  ssh -p 23953 basar@10.tcp.eu.ngrok.io
  ```
  veya
  ```bash
  ssh basar@10.tcp.eu.ngrok.io -p 23953
  ```

### Git Kurulumu ve İlk Push (2025-12-08 15:15:35)
- Git repository başarıyla başlatıldı ve ilk commit yapıldı
- Raspberry Pi'de SSH key oluşturuldu (ED25519, fingerprint: SHA256:XrA2Pz/9I8jHWvJV0h7IXHbNqXCl5ahlax1PNmpDz6Q)
- SSH key GitHub'a eklendi ve bağlantı başarıyla test edildi
- İlk push başarıyla tamamlandı (commit: 57be7e3)
- Branch: main, Remote: git@github.com:CaiserSz/orge1.git (SSH)

