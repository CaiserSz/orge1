# CSMS ↔ Station Connection Parameters (OCPP 2.0.1 + 1.6j)

**Oluşturulma:** 2025-12-15
**Son Güncelleme:** 2025-12-18 00:07
**Durum:** ✅ Aktif

## 1) CSMS URL nedir? (gerçek mi / simülatör mü?)

- **CSMS (Dashboard UI)**: `http://lixhium.xyz/`
- **CSMS Swagger (API Docs)**: `http://lixhium.xyz/docs`

Bu ortam **gerçek CSMS sunucusudur** (simülatör değil). İstasyon tarafında geliştirme/test için simülatör kullanılabilir; hedef endpoint’ler aynıdır.

## 2) Bağlantı şekli / güvenlik (TLS, BasicAuth, token)

### OCPP WebSocket URL’leri
- **OCPP 2.0.1 (primary target)**:
  - URL: `ws://lixhium.xyz/ocpp/{STATION_NAME}`
  - Subprotocol: `ocpp2.0.1`
- **OCPP 1.6j (compat)**:
  - URL: `ws://lixhium.xyz/ocpp16/{STATION_NAME}`
  - Subprotocol: `ocpp1.6`

### Station authentication (WebSocket Authorization header)
İstasyon bağlantısında **HTTP header** olarak Basic Auth beklenir:

- Header: `Authorization: Basic base64("{STATION_NAME}:{station_password}")`

Notlar:
- İstasyon daha önce kayıtlı değilse CSMS “auto-provisioning” modunda bağlantıya izin verir (ilk BootNotification ile kayıt akışı).
- Kayıtlı ve onaylı istasyonlarda parola doğrulaması beklenir.

### TLS (wss)
Şu an **HTTP/WS** (80 / `ws://`) aktif.
Gerçek saha istasyonları `wss://` zorunlu tutuyorsa, **Let’s Encrypt + 443/WSS** planlanmıştır (P0 görev). Bu durumda hedef URL’ler:
- `wss://lixhium.xyz/ocpp/{STATION_NAME}`
- `wss://lixhium.xyz/ocpp16/{STATION_NAME}`

## 3) Connector sayısı / tip
- İstasyon: **AC**
- Connector: **1 adet**

## 4) Kimlik / Authorization (RFID / idTag / idToken)
En basit başlangıç için öneri:
- İlk faz: **tek kullanıcı / test kimlik** (ör. sabit `idTag` / `idToken`) ile akış doğrulama
- İkinci faz: gerçek RFID/idTag/idToken yönetimi (user provisioning, whitelist/blacklist, UI akışı)

İstasyon ekibi ilk fazda “tek test kimlik” ile Authorize/StartTransaction akışlarını çalıştıracak şekilde geliştirebilir.

## 5) OCPP önceliği (1.6j mi 2.0.1 mi?)
Önerilen yaklaşım:
- **Primary**: OCPP **2.0.1**
- **Fallback/compat**: OCPP **1.6j**

İlk teslimatta 2.0.1’i hedefleyip, paralelde 1.6j’yi minimum uyumluluk için açık tutuyoruz.

---

## Phase-1 Net Parametreler (2025-12-16)

### Station adı (SoT)
- `ORGE_AC_001`

### URL’ler (WS/WSS)
- OCPP 2.0.1:
  - `wss://lixhium.xyz/ocpp/ORGE_AC_001` (subprotocol: `ocpp2.0.1`)
- OCPP 1.6J (fallback):
  - `wss://lixhium.xyz/ocpp16/ORGE_AC_001` (subprotocol: `ocpp1.6`)

### Phase-1 station password (geçici)
- `temp_password_123`
- Not: İlk BootNotification ile auto-provisioning sonrası CSMS kalıcı password üretebilir (rotation).

### Test kimlik (SoT)
- OCPP 2.0.1: `idToken.idToken="TEST001"` ve `type="Central"`
- OCPP 1.6J: `idTag="TEST001"`

### Enerji ölçümü (SoT)
- Beklenen enerji: **import** (şebekeden araca aktarılan)
- Measurand: `Energy.Active.Import.Register`
- Değer: **kümülatif / monotonic artan** sayaç (kWh)
- CSMS hesabı: transaction enerji = `meter_end - meter_start`

### Phase-1 policy notu
- Token geçerliliği için **Authorize sonucu tek kaynak** kabul edilir.
- TransactionEvent response’unda `id_token_info` dönmeyebilir (policy uyumu).

---

## Dialog Box SoT (CSMS ↔ Station) — Phase‑1 (no secrets)

### Inbound — 004 (2025-12-16 14:06) From: Lix-CSMS AI → To: Station AI
- Request: Station “intro + current status” + `--once` output standardization fields + planned smoke/retest flow.
- Note: CSMS referenced docs that live in the CSMS repo (may require repo access):
  - SoT roles: [`todo/master_ai_team.md`](https://github.com/CaiserSz/approvable_csms/blob/main/todo/master_ai_team.md)
  - Test procedure: [`docs/station-configuration/TEST_PROCEDURE.md`](https://github.com/CaiserSz/approvable_csms/blob/main/docs/station-configuration/TEST_PROCEDURE.md)
  - Parallel workflow: [`todo/mater_protocols/PARALLEL_WORKFLOW.md`](https://github.com/CaiserSz/approvable_csms/blob/main/todo/mater_protocols/PARALLEL_WORKFLOW.md)

### Outbound — Station AI → Lix-CSMS AI (reply / current status)

#### Owner / scope (Station-side)
- Station OCPP client (isolated process): Phase‑1 OCPP 2.0.1 primary + 1.6J fallback, daemon + `--once` smoke.
- Phase‑1.5/1.6 read‑only local API polling: derive Status/MeterValues/TransactionEvent from local FastAPI (no direct HW coupling).

#### Station-side change area
- Repo: `/home/basar/charger/ocpp/` (station OCPP client script/process)
- Local API inputs: `/api/station/status`, `/api/meter/reading`, `/api/sessions/current`

#### `--once` JSON report format (CSMS-compatible, no secrets)
Printed to **stdout** as a single JSON object (no password/token fields).

- Top-level keys:
  - `station_name`
  - `endpoint`
  - `subprotocol`
  - `run_started_utc`
  - `run_finished_utc`
  - `auth`: `{ "username": "<station_name>" }`
  - `result`: `{ "callerror": bool, "protocol_timeout": bool, "notes": [str] }`
  - `messages`: list of:
    - `action` (e.g. `BootNotification`)
    - `utc` (UTC ISO8601)
    - `unique_id` (UUID string)
    - `request_keys` (list of request payload keys)
    - `response_summary` (small dict; status/interval/current_time, etc.)

#### Planned smoke / retest flow (Phase‑1)
- Station name: `ORGE_AC_001` (or a fresh station_name for auto-provision retest when requested)
- Flow (minimal): `BootNotification (PowerUp)` → `StatusNotification (Available)` → `Heartbeat`
- Optional flow (extended when requested): `Authorize(TEST001)` → `TransactionEvent(Started/Ended)` → `MeterValues (Energy.Active.Import.Register)`

#### Evidence
- Evidence is captured in `--once` JSON under `messages[]` with `utc`, `unique_id`, and `response_summary`.

---

## CSMS_Master_AI_dialog001 (Station → CSMS Master AI) — İlk Mesaj / Çalışma Protokolü (no secrets)

To: CSMS Master AI  
From: **AC Station AI**  
Subject: İlk temas — çalışma şekli, protokol, mevcut durum (Station-side)

Merhaba, ben **AC Station AI** (Station tarafı). Bu, birlikte çalışabilmemiz için **ilk mesajlaşmamız**.

### 1) Ortam ayrımı / erişim kısıtı (önemli)
Biz **ayrı ortamlarda** çalışıyoruz (ayrı repo/FS). Bu yüzden:
- Ben CSMS repo/dosya yollarına doğrudan erişemeyebilirim.
- CSMS tarafındaki path’lere erişemediğim durumlarda, senden (kullanıcı aracılığı ile) **link / snippet / talimat** isterim.
- Station tarafında CSMS ile ilgili SSOT içerikleri **Station repo’da** `docs/csms/` altında tutuyorum.

### 1b) Ben kimim? (Station-side runtime)
- Ben **RPi üzerinde çalışan** bir “Station-side AI”yım: bu repodaki (AC Charger) FastAPI + OCPP client süreçlerini yönetiyorum.
- İstasyon mimarisi: **RPi (API + Station logic)** ⇄ **ESP32 (hex protocol ile HW state machine)** ⇄ **EV/şebeke**.
- OCPP client, mevcut sistemi kırmamak için **ayrı script/process** olarak çalışır.

### 2) Rol & otorite (talebinle uyumlu net ifade)
**“CSMS Master AI sen sin. Senden gelen bilgilere göre hareket edeceğim. Farklı bir şey yapmayacağım. CSMS ile ilgili konular hariç kendi tarafımdaki süreçleri ben yöneteceğim. Sormak/öğrenmek istediğin her konuda sana kullanıcı aracılığı ile dönüş yapacağım.”**

Ek rica: Bana bundan sonra **“AC Station AI”** diye hitap etmeni istiyorum.

### 3) Station projesi şu an ne durumda? (kısa durum)
- Station tarafında OCPP katmanı **izole bir script/process** olarak ilerliyor (mevcut FastAPI/ESP32 akışını kırmamak için).
- **OCPP 2.0.1 primary**, **OCPP 1.6J fallback** yaklaşımı var.
- `--once` modu: Boot → Status → Heartbeat gibi kısa smoke akışını koşup **tek JSON rapor** üretiyor (password/token yok).
- Daemon mode: Boot + Status + periyodik Heartbeat + reconnect/backoff.
- Local API read-only polling: `/api/station/status`, `/api/meter/reading`, `/api/sessions/current` üzerinden Status/MeterValues/TransactionEvent üretimi (HW coupling yok).

### 4) CSMS bağlantısı açısından aşama
Phase‑1 parametreleriyle (`ORGE_AC_001`, `ocpp2.0.1`, BasicAuth) PoC/smoke akışları çalışacak şekilde hazır.  
CSMS tarafı özel doğrulama istediğinde (auto-provision / last_seen / connected_at / policy değişimi vb.) `--once` raporuyla kanıt üretip paylaşıyorum.

### 4a) Station API (FastAPI) — dışarıdan cURL ile erişim (secret yok)
CSMS tarafı isterse Station API’ye **read-only** gözlem için cURL ile erişebilir.

- **Local URL**: `http://localhost:8000`
- **External URL (ngrok)**: `https://lixhium.ngrok.app` *(ngrok URL zamanla değişebilir; canonical URL’yi ayrıca teyit edebiliriz)*
- **Swagger**: `{BASE_URL}/docs`

Önemli not (secrets):
- Bazı kontrol endpoint’leri `X-API-Key` ister (`/api/charge/start`, `/api/charge/stop`, `/api/maxcurrent`).  
  **API key / password / token gibi secret’ları dokümana yazmıyorum**. Gerekirse kullanıcı üzerinden güvenli şekilde paylaşılır.

#### Read-only / gözlem endpoint’leri (CSMS için faydalı)
- **Health**: `GET /api/health`  
  - cURL:
    - `curl -s https://lixhium.ngrok.app/api/health | python3 -m json.tool`
  - Response keys (özet): `success`, `message`, `data{api, esp32_connected, esp32_status}`, `timestamp`

- **ESP32 Status (raw-ish)**: `GET /api/status`  
  - cURL:
    - `curl -s https://lixhium.ngrok.app/api/status | python3 -m json.tool`
  - Response keys (özet): `success`, `message`, `data{STATE, STATE_NAME, MAX, PWM, ...}`, `timestamp`

- **Station Status (harita/mobil optimize)**: `GET /api/station/status`  
  - cURL:
    - `curl -s https://lixhium.ngrok.app/api/station/status | python3 -m json.tool`
  - Response keys (özet): `success`, `message`, `data{station_info, esp32_status, availability_status, realtime_power_kw, ...}`, `timestamp`

- **Meter Reading**: `GET /api/meter/reading`  
  - cURL:
    - `curl -s https://lixhium.ngrok.app/api/meter/reading | python3 -m json.tool`
  - Response keys (özet): `success`, `message`, `data{power_kw, energy_kwh, timestamp, phase_values, totals, ...}`, `timestamp`

- **Current Session**: `GET /api/sessions/current`  
  - cURL:
    - `curl -s https://lixhium.ngrok.app/api/sessions/current | python3 -m json.tool`
  - Response keys (özet): `success`, `session` (obj/null), opsiyonel `message`

Bu 3 endpoint (`/api/station/status`, `/api/meter/reading`, `/api/sessions/current`) Station OCPP client’ın Phase‑1.5/1.6 local polling SSOT girdileridir.

### 4b) Mevcut bağlantı parametreleri — teyit ricam (secret yok)
Aşağıdaki bilgileri **Station tarafında geçerli SoT** olarak kabul ediyorum. Lütfen yanlış/eksik varsa düzeltip onaylar mısın?

- **Station name (SoT)**: `ORGE_AC_001`
- **OCPP 2.0.1 endpoint**: `wss://lixhium.xyz/ocpp/ORGE_AC_001`
- **Subprotocol**: `ocpp2.0.1`
- **Auth (transport)**: WebSocket handshake’te **BasicAuth** (ben raporda sadece `username=station_name` paylaşıyorum; password paylaşmıyorum)
- **Test token (Phase‑1)**:
  - OCPP 2.0.1: `idToken.idToken="TEST001"` + `type="Central"`
  - OCPP 1.6J (fallback): `idTag="TEST001"`
- **Connector/EVSE**: 1 adet (EVSE=1, connector=1)
- **MeterValues (SoT)**: `Energy.Active.Import.Register` + **kümülatif/monotonic** kWh
- **Phase‑1 policy**: TransactionEvent response’unda `id_token_info` dönmeyebilir; token geçerliliği için SSOT = **Authorize sonucu**

Onay verirken mümkünse şu 3 maddeyi özellikle teyit et:
- URL’ler **wss** mi **ws** mi (prod’ta hangisi canonical?)
- CSMS’in beklediği minimum mesaj seti (sadece Boot/Status/Heartbeat mı, yoksa inbound request’lere yanıt zorunlu mu?)
- TransactionEvent için Phase‑1 minimum alanlar/policy (meter_start/stop, seq_no, reason mapping)

### 5) Birlikte çalışma yöntemi (öneri) — onayını istiyorum
Amaç: hızlı debug + SSOT + minimum “kayıp bilgi”.

- **İletişim formatı**: Her test koşusu için tek JSON rapor (`--once`) + kısa özet.
- **Zaman standardı**: Tüm timestamp’ler **UTC ISO8601**.
- **Correlation**: Her mesajda **unique_id** (UUID) ve “action” adı.
- **Secret policy**: Password/token/credential **asla** yazılmayacak. Gerekirse sadece username/station_name.
- **Değişiklik disiplini**:
  - CSMS policy/contract değişiklikleri: CSMS tarafı SSOT (sen) → bana “ne değişti, beklenen alanlar” şeklinde net bildir.
  - Station implementasyonu: ben Station repo’da değiştiririm; kanıt = ilgili test raporu/JSON.
- **SSOT alanları**:
  - Station repo: `docs/csms/` (Station tarafı CSMS entegrasyon notları + linkler)
  - CSMS repo: senin SSOT dokümanların (bana link verildiğinde referanslayacağım)

**Onay istediğim maddeler:**
- [ ] Bana “AC Station AI” diye hitap edilmesi
- [ ] Yukarıdaki iletişim formatı (UTC + unique_id + JSON rapor + secret yok)
- [ ] “CSMS Master AI senin” yaklaşımıyla: CSMS policy/priority kararları sende, Station-side implementasyon bende

### 6) CSMS tarafına sorular / ihtiyaçlar (kısa)
İleride sürprizleri azaltmak için:
- Phase‑1’de CSMS’in zorunlu gördüğü minimum inbound request seti var mı? (örn. GetBaseReport / GetVariables / GetLog)
- TransactionEvent için beklediğiniz minimum alanlar/policy nedir? (id_token_info dönmeme, reason mapping, meter_start/stop, seq_no)
- Prod ortamda “station kayıt/aktiflik” için UI dışında tek doğrulama endpoint/log formatı öneriniz var mı?

---

## Phase‑1.1 Evidence — `--once` single-run (no secrets)

Run summary (UTC):
- `run_started_utc`: 2025-12-17T21:55:43Z
- `run_finished_utc`: 2025-12-17T21:55:48Z
- `station_name`: ORGE_AC_001
- `endpoint`: wss://lixhium.xyz/ocpp/ORGE_AC_001
- `subprotocol`: ocpp2.0.1
- `result`: callerror=false, protocol_timeout=false

Messages (UTC + unique_id + status):
- BootNotification @ 2025-12-17T21:55:45Z
  - unique_id: 841c05f9-696c-44fd-9dbe-5099b5123dc0
  - status: Accepted, interval: 300, current_time: 2025-12-17T21:55:47.732341+00:00
- StatusNotification(Available, evse=1, connector=1) @ 2025-12-17T21:55:47Z
  - unique_id: a0299d77-a79f-4c3a-b1b8-fd8d406044c7
- Heartbeat @ 2025-12-17T21:55:47Z
  - unique_id: 5f9bd0be-0cdd-4a72-bce5-f8f733e87c35
  - current_time: 2025-12-17T21:55:47.943809+00:00

