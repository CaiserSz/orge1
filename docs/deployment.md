# Deployment Kılavuzu - AC Charger

**Oluşturulma Tarihi:** 2025-12-09 22:40:00
**Son Güncelleme:** 2025-12-21 23:00:00
**Version:** 1.1.4

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
- **NGROK_API_KEY:** `.env` dosyasında tanımlı (**secret**; repo/dokümana yazılmaz)
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

---

## Systemd Servisleri (Pilot/Prod - Security hariç) (2025-12-21)

Hedef: 5-6 pilot → 150 istasyona ölçeklerken “aynı SSD imajı + deterministik provisioning” ile
servislerin otomatik kalkması, otomatik toparlaması ve kolay güncellenebilmesi.

### Charger API (FastAPI)

- Template: `scripts/charger-api.service`
- Kurulum örneği:
  - `sudo cp /home/basar/charger/scripts/charger-api.service /etc/systemd/system/charger-api.service`
  - `sudo systemctl daemon-reload`
  - `sudo systemctl enable --now charger-api.service`
  - Log: `sudo journalctl -u charger-api -f`

### OCPP Station Daemon (OCPP 2.0.1 primary + 1.6J fallback)

Not: Station OCPP client (`ocpp/main.py`) Phase-1 tasarımında **API’den izole ayrı bir proses** olarak çalışır.
Bu sayede ESP32/yerel API servisinin çalışma düzeni bozulmadan CSMS ile “outbound WebSocket” bağlantısı yönetilir.

Önerilen kurulum (yeni unit’i cihaz üzerinde oluştur):

1) `sudo systemctl edit --force --full ocpp-station.service`
2) Aşağıdaki içeriği yapıştır:

```ini
[Unit]
Description=OCPP Station Daemon (ORGE)
After=network-online.target time-sync.target
Wants=network-online.target time-sync.target

[Service]
Type=simple
User=basar
Group=basar
WorkingDirectory=/home/basar/charger
Environment="PATH=/home/basar/charger/env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="PYTHONUNBUFFERED=1"
# Secrets kesinlikle repo içine girmez. Password sadece runtime env ile verilir.
EnvironmentFile=-/etc/ocpp_station.env

ExecStart=/home/basar/charger/env/bin/python -u /home/basar/charger/ocpp/main.py
# Not: CLI arg'ları env'i override eder; fleet provisioning için env tercih edilir.

Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ocpp-station

TimeoutStopSec=30
KillMode=mixed
KillSignal=SIGTERM

[Install]
WantedBy=multi-user.target
```

3) `sudo systemctl daemon-reload`
4) `sudo systemctl enable --now ocpp-station.service`
5) Log: `sudo journalctl -u ocpp-station -f`

`/etc/ocpp_station.env` örneği (dosya cihazda tutulur; git’e girmez):

```bash
# Zorunlu
OCPP_STATION_NAME='ORGE_AC_001'
OCPP_STATION_PASSWORD='***'

# Opsiyonel: override / saha ayarı (fleet için önerilen)
OCPP_PRIMARY='201'
OCPP_201_URL='wss://lixhium.xyz/ocpp/ORGE_AC_001'
OCPP_16_URL='wss://lixhium.xyz/ocpp16/ORGE_AC_001'
OCPP_HEARTBEAT_SECONDS='60'
```

### Update / Rollback (GitHub’dan çekme)

Öneri: Her SSD imajı bir “pinned” commit/tag ile çıkar; sahada güncelleme kontrollü yapılır.

- Update:
  - `cd /home/basar/charger && git fetch --all --tags`
  - `git checkout <tag|commit>`
  - (gerekirse) `./env/bin/pip install -r requirements.txt`
  - `sudo systemctl restart charger-api.service ocpp-station.service`
- Health check (CSMS’e dokunmadan smoke):
  - `sudo bash -lc 'set -a; source /etc/ocpp_station.env; set +a; cd /home/basar/charger; ./env/bin/python -u ocpp/main.py --once'`
  - Çıktı: stdout’a **tek JSON** (secret içermez; `messages[]` içinde Boot/Status/Heartbeat kanıtı). Exit code `0` başarı.

---

## Golden Image / SSD Provisioning Checklist (Security hariç) (2025-12-21)

Amaç: Yeni SSD imajı ile gelen RPi’lerde aynı adımlarla (deterministik) servislerin kalkması.

Önerilen minimum adımlar:

1) Paketler:
   - `sudo apt-get update`
   - `sudo apt-get install -y git python3-venv`

2) Repo:
   - `cd /home/basar`
   - `git clone git@github.com:CaiserSz/orge1.git charger`
   - `cd /home/basar/charger`
   - `git checkout <tag|commit>`  (fleet rollout için pin önerilir)

3) Python env:
   - `python3 -m venv env`
   - `./env/bin/pip install -r requirements.txt`

4) Station config (secret cihazda):
   - `/etc/ocpp_station.env` oluştur (örnek üstte)

5) Systemd:
   - `charger-api.service` kur + enable (template: `scripts/charger-api.service`)
   - `ocpp-station.service` kur + enable (örnek unit: bu doküman)

6) Smoke test:
   - `sudo bash -lc 'set -a; source /etc/ocpp_station.env; set +a; cd /home/basar/charger; ./env/bin/python -u ocpp/main.py --once'`
   - Beklenen: tek JSON + exit code `0`

7) Power sanity (RPi):
   - `vcgencmd get_throttled` → Beklenen: `throttled=0x0`
   - `journalctl -k --no-pager | grep -i undervoltage | tail -n 50` → Kayıt varsa PSU/kablo kontrolü gerekir
   - Detaylı runbook: `docs/troubleshooting.md` → “Raspberry Pi Undervoltage / Throttling”

