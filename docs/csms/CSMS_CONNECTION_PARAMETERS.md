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

