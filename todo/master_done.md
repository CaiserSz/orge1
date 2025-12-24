# Tamamlanan Görevler

**Oluşturulma Tarihi:** 2025-12-08 18:20:00
**Son Güncelleme:** 2025-12-24 15:00:00

---

## Tamamlanan Görevler Listesi

### 2025-12-24

#### ✅ Admin UI validation UX fix (400 + açıklayıcı mesaj)
- **Görev:** Eksik/yanlış profil alanlarında “Internal server error (500)” yerine kullanıcıyı doğru bilgilendir
- **Açıklama:**
  - Admin profil kaydında eksik/yanlış alanlar artık `HTTP 400` + `detail` ile dönüyor.
  - URL doğrulaması eklendi: `ocpp201_url` ve `ocpp16_url` → `/{station_name}` ile bitmeli.
  - UI tarafında 500 gibi durumlarda da `message` alanı varsa gösterim iyileştirildi.
- **Test/Doğrulama:** `./env/bin/pytest -q tests/test_auth.py` → ✅
- **Commit:** `c946873`

### 2025-12-22

#### ✅ Backup automation (systemd) + git hijyeni
- **Görev:** `backup.service` systemd unit tutarlılığı (unit mevcut değil / user farklı)
- **Açıklama:** `backup.service` + `backup.timer` cihazda kuruldu ve timer enable edildi. Repo template `User/Group=basar` olacak şekilde düzeltildi. Backup artefact’ları (`backups/`) git’ten çıkarıldı ve `.gitignore` ile ignore edildi.
- **Test/Doğrulama:**
  - `systemctl status backup.timer` → ✅ active (waiting)
  - `sudo systemctl start backup.service` → ✅ SUCCESS (db+config+manifest üretildi)

#### ✅ Ngrok boot order iyileştirmesi (network-online)
- **Görev:** Ngrok DNS/bağlantı hataları (geçmiş) - resolver yapılandırması kontrolü
- **Açıklama:** Geçmiş “lookup … network is unreachable” hatasının kök nedeni boot’ta network-online olmadan ngrok’un başlamasıydı. `ngrok.service` için drop-in ile `Wants/After=network-online.target` eklendi.
- **Test/Doğrulama:**
  - `systemctl status ngrok` → ✅ active
  - `curl http://localhost:4040/api/tunnels` → ✅ response (local inspect)

#### ✅ CSMS ↔ Station canonical test komutu ayrımı (SSOT)
- **Görev:** CSMS “canonical” test komutunu Station repo ile uyumlu hale getir (veya SSOT’ta ayrımı netleştir)
- **Açıklama:** CSMS repo komutları ile Station repo kanıt komutları SSOT’ta ayrıştırıldı.
- **SSOT:** `docs/csms/CSMS_CONNECTION_PARAMETERS.md` → “Canonical test / kanıt komutu”

#### ✅ `meter/read_meter.py` unit test kapsamı
- **Görev:** `meter/read_meter.py` için unit test kapsamı ekle (helper + CRC + request/response parse)
- **Açıklama:** Donanım/serial açmadan test edilebilecek saf helper ve Modbus frame/parse mantığı için testler eklendi.
- **Test/Doğrulama:**
  - `python3 -m py_compile tests/test_api_endpoints.py` → ✅
  - `./env/bin/pytest -q tests/test_api_endpoints.py` → ✅

#### ✅ `tests/test_api_endpoints.py` kompaktlaştırma (satır limiti)
- **Görev:** `tests/test_api_endpoints.py` kompaktlaştırma (satır sayısı uyarı eşiği yakın)
- **Açıklama:** Tekrarlı maxcurrent testleri `pytest.mark.parametrize` ile sadeleştirildi; dosya 500 limitinin altına indirildi.
- **Test/Doğrulama:**
  - `python3 -m py_compile tests/test_api_endpoints.py` → ✅
  - `./env/bin/pytest -q tests/test_api_endpoints.py` → ✅

#### ✅ `tests/test_integration.py` kompaktlaştırma (satır limiti payı)
- **Görev:** `tests/test_integration.py` kompaktlaştırma (satır sayısı uyarı eşiği yakın)
- **Açıklama:** Tekrarlı test blokları sadeleştirildi (loop/parametrize), OCPP test helper’ları ortaklaştırıldı (`_utc_now`, BasicAuth helper, ortak cfg). Ayrıca v201 `TransactionEvent` içinden `transaction_id` extraction dict/obj uyumlu yapıldı. Dosya 485 → 433 satıra indirildi.
- **Test/Doğrulama:**
  - `python3 -m py_compile tests/test_integration.py` → ✅
  - `./env/bin/pytest -q tests/test_integration.py` → ✅

#### ✅ DB EventQuery deadlock fix + test kapsamı
- **Görev:** `api/database/event_queries.py` path’lerinde takılma (deadlock) ve event row parse hatasını düzelt + test ekle
- **Açıklama:**
  - `migrate_events_to_table()` → `create_event()` iç içe çağrısında `Lock` reentrant olmadığı için deadlock oluyordu; `RLock` ile düzeltildi.
  - `event_row_to_dict()` içinde `sqlite3.Row.get()` hatası giderildi (safe access).
  - `migrate_user_id_column()` yeni DB init sırasında `session_events` yokken gereksiz warning üretmesin diye table-exists check eklendi.
  - `tests/test_database_optimization.py` içine EventQueryMixin senaryoları eklendi.
- **Test/Doğrulama:**
  - `python3 -m py_compile api/database/core.py api/database/models.py api/database/migrations.py` → ✅
  - `./env/bin/pytest -q tests/test_database_optimization.py` → ✅ (9 passed)

#### ✅ OCPP daemon 3dk run (env/venv uyumu) + shutdown fix
- **Görev:** OCPP daemon’u `.env` ile çalıştır + venv-in-repo dependency-check yanlış pozitifi ve shutdown cancel fallback bug’ını düzelt
- **Açıklama:**
  - `.env` içinden `OCPP_STATION_PASSWORD` ile daemon çalıştırma doğrulandı (secret loglanmadan).
  - `ocpp/main.py` dependency-check yanlış pozitifi düzeltildi: venv `./env/` repo içinde olsa bile conflict sayılmıyor; sadece proje içi `./ocpp/` shadow ederse fail ediyor.
  - SIGTERM/SIGINT shutdown sırasında cancel kaynaklı yanlış v16 fallback tetiklenmesi engellendi.
- **Kanıt:**
  - Log: `/tmp/ocpp_daemon_orge_ac_001.log` (BootNotification=Accepted, Status=Available, Heartbeat 60s, clean shutdown)

#### ✅ Standart uyarılarını sırayla temizleme (satır limiti payı açma)
- **Görev:** `standards_auto_check` uyarılarını dosya bazlı kompaktlaştırma ile kapat
- **Açıklama (özet):**
  - `api/logging_config.py`: 407 → 358
  - `api/event_detector.py`: 414 → 390
  - `api/config.py`: 416 → 318
  - `api/database/session_queries.py`: 404 → 387
  - `api/routers/sessions.py`: 417 → 350
  - `tests/test_integration.py`: 433 → 393
  - `tests/test_event_detector.py`: 467 → 314
  - `tests/test_protocol_rules.py`: 410+ → 399
  - `tests/test_api_endpoints.py`: 464 → 391
- **Test/Doğrulama:**
  - Dosya bazlı `py_compile` + ilgili pytest dosyaları → ✅
  - `./env/bin/python scripts/standards_auto_check.py` → ✅ “Tüm dosyalar standartlara uygun”
  - `./env/bin/python scripts/code_quality_auto_check.py` → ✅ (Black/Ruff temiz)

#### ✅ Standart uyarı eşiği yakın dosyaları kompaktlaştırma (satır limiti payı)
- **Görev:** Satır limiti 500’e yaklaşan dosyaları (yeni dosya oluşturmadan) güvenli aralığa çek
- **Açıklama:**
  - `meter/read_meter.py`: 497 → 410 (docstring kısaltma + ortak register okuma helper’ı)
  - `api/event_detector.py`: 477 → 414 (docstring/tekrar sadeleştirme + state name map sabitleme)
  - `tests/test_protocol_rules.py`: 473 → 410 (parametrize/helper ile tekrar azaltma)
- **Test/Doğrulama:**
  - `./env/bin/python -m py_compile meter/read_meter.py api/event_detector.py tests/test_protocol_rules.py` → ✅
  - `./env/bin/pytest -q tests/test_api_endpoints.py` → ✅
  - `./env/bin/pytest -q tests/test_event_detector.py` → ✅
  - `./env/bin/pytest -q tests/test_protocol_rules.py` → ✅

#### ✅ Admin OCPP Profile UI + systemd OCPP runner template
- **Görev:** OCPP 2.0.1 / 1.6j için “tek ekran” profil yönetimi + systemd üzerinden start/stop/log
- **Açıklama:**
  - `/admin` altında HTTP Basic ile korunan ayrı admin sayfası eklendi (default: `admin/admin123`, UI’dan değiştirilebilir).
  - DB tabloları: `admin_users` (hash+salt), `ocpp_station_profiles` (secret-free profil; password `.env`’de).
  - systemd template: `ocpp-station@.service` + instance drop-in (`ocpp-station@<profile>.service.d/override.conf`) üretimi.
  - Servis yönetimi: sync/start/stop/restart/status/logs endpoint’leri (admin UI butonları).
- **Dosyalar:** `api/routers/test.py`, `api/main.py`, `api/database/schema_mixin.py`, `api/database/maintenance_queries.py`, `tests/test_auth.py`
- **Test/Doğrulama:**
  - `curl` ile `/admin` 401/200 doğrulandı (BasicAuth).
  - Browser (manuel): `/admin` sayfası açıldı, profile listesi ve “Status” aksiyonu doğrulandı.
  - `./env/bin/pytest -q tests/test_auth.py` → ✅
  - systemd smoke: `ocpp-station@ORGE_AC_001_V16_TEST` sync + start + stop → ✅ (parola `.env` üzerinden resolve edildi)
- **Commit:** `d9a44ab`

### 2025-12-21

#### ✅ OCPP daemon prod-hardening (security hariç) — runbook + shutdown
- **Görev:** OCPP daemon için systemd servis kurulumu + update/rollback runbook dokümante et
- **Açıklama:** `docs/deployment.md` içine `ocpp-station.service` örneği + `/etc/ocpp_station.env` + update/rollback + `--once` smoke check eklendi.

- **Görev:** `docs/deployment.md` içindeki açık secret değerlerini redakte et (NGROK_API_KEY)
- **Açıklama:** Dokümandaki açık secret value kaldırıldı (secret’lar dokümana yazılmaz).

- **Görev:** OCPP daemon için systemd-friendly graceful shutdown (SIGTERM) ekle
- **Açıklama:** Systemd stop/restart sırasında SIGTERM ile temiz kapanış akışı iyileştirildi.

#### ✅ Meter parse unit testleri (donanım yok)
- **Görev:** `api/meter/modbus.py` ve `api/meter/acrel.py` için saf parse/convert unit testleri ekle
- **Açıklama:** Donanım erişimi olmadan test edilebilecek register decode/convert path’leri kapsandı.

#### ✅ OCPP Remote Ops inbound handler testleri
- **Görev:** UI Remote Ops inbound handler’ları için otomatik test ekle (Remote Start/Stop)
- **Açıklama:** Local CSMS ws server ile RemoteStart/RemoteStop end-to-end kanıtı testle kalıcılaştırıldı.

#### ✅ RPi Undervoltage (yazılımsal) — kanıt + runbook + monitoring
- **Görev:** RPi “Undervoltage detected” olaylarını kök neden analizi + kalıcı çözüm (yazılımsal)
- **Açıklama:** Kanıt toplandı, runbook ve monitoring eklendi. Hardware aksiyon ayrı görev olarak bırakıldı.

### 2025-12-19

#### ✅ Secret/Config hijyeni (repo)
- **Görev:** `.env` dosyasını git’ten çıkar (tracked → untracked) ve repo’dan secret sızıntısını durdur
- **Açıklama:** `.env` git geçmişi riskine karşı tracked olmaktan çıkarıldı; secret’lar repo dışında tutuluyor.

- **Görev:** `.env.example` yok; `CONTRIBUTING.md` içindeki yönergeyi düzelt veya secret‑free şablon stratejisi belirle
- **Açıklama:** Dokümandaki `.env.example` varsayımı düzeltildi / secret-free strateji netleştirildi.

### 2025-12-18

#### ✅ OCPP Phase‑1.3 Remote Stop Mapping Kanıtı (20:23:33)
- **Görev:** CSMS inbound `RequestStopTransaction` ile Remote stop kaynağını yakala ve `TransactionEvent(Ended)` mapping’ini üret
- **Açıklama:** Phase‑1.3 kapsamında stoppedReason mapping tamamlandı. CSMS’ten gelen `RequestStopTransaction(transactionId=REMOTE_TX_001)` inbound call görüldü; Ended event’inde `stoppedReason=Remote`, `triggerReason=RemoteStop` üretildi.
- **Kanıt (UTC):**
  - `run_started_utc`: 2025-12-18T20:23:17Z
  - `run_finished_utc`: 2025-12-18T20:23:33Z
  - `callerror=false`, `protocol_timeout=false`
  - inbound: `RequestStopTransaction` (unique_id: 4627e557-14c1-4add-b921-6fb70d00328a)
  - Started unique_id: 209ac0cb-e22e-49fe-b1bc-8ecc1f59db83
  - Ended unique_id: e9b00b35-df30-4ed5-914d-ce9b3442c3b7
- **Komut (secret redacted):**
  - `./env/bin/python ocpp/main.py --primary 201 --once --poc --poc-remote-stop-wait-seconds 120 --poc-transaction-id REMOTE_TX_001 --ocpp201-url wss://lixhium.xyz/ocpp/ORGE_AC_001 --ocpp16-url wss://lixhium.xyz/ocpp16/ORGE_AC_001 --station-name ORGE_AC_001 --station-password ****** --id-token TEST001`

#### ✅ OCPP Phase‑1.4 Runbook A/B/C Kanıtı (22:13:22)
- **Görev:** CSMS-controlled lifecycle kanıtı: A=RequestStartTransaction, B=SetChargingProfile, C=RequestStopTransaction
- **Açıklama:** Tek `--once` koşumunda CSMS’ten gelen inbound call’lar ile Station TransactionEvent Started/Ended üretip mapping’leri doğruladı. A/B/C eksiksiz görüldü.
- **Kanıt (UTC):**
  - `run_started_utc`: 2025-12-18T22:13:08Z
  - `run_finished_utc`: 2025-12-18T22:13:22Z
  - `callerror=false`, `protocol_timeout=false`
  - inbound: `RequestStartTransaction`, `SetChargingProfile`, `RequestStopTransaction`
  - Started unique_id: 59d52948-bbd5-4da4-814d-4c4a60b56e54
  - Ended unique_id: 98bd64dc-130e-4da4-a79c-4937c00bf347
  - build commit: cceed2e
- **Komut (secret redacted):**
  - `./env/bin/python ocpp/main.py --primary 201 --once --poc --poc-runbook --poc-remote-start-wait-seconds 180 --poc-runbook-wait-profile-seconds 180 --poc-runbook-wait-stop-seconds 180 --poc-transaction-id REMOTE_TX_001 --ocpp201-url wss://lixhium.xyz/ocpp/ORGE_AC_001 --ocpp16-url wss://lixhium.xyz/ocpp16/ORGE_AC_001 --station-name ORGE_AC_001 --station-password ******`

### 2025-12-14

#### ✅ `/api/station/status` realtime_power_kw doğruluğu (03:30:00)
- **Görev:** CHARGING durumunda `realtime_power_kw` alanının meter verisiyle tutarlı dönmesini sağlamak
- **Açıklama:** EV şarjı aktifken meter bağlantısı geçici düşmüş/yeniden bağlanmış olsa bile `/api/station/status` endpoint’i `realtime_power_kw` alanını mümkünse meter ölçümünden üretmelidir. Sadece `is_connected()` kontrolü yüzünden ölçüm kaçırılıp PWM/Max fallback’ına düşülmesi, 3‑faz kurulumlarda ciddi under‑reporting’e neden olabiliyordu.
- **İmplementasyon:**
  - `api/routers/station.py`: Meter ölçümü için `is_connected()` şartı kaldırıldı; best-effort `connect()` + `read_all()` ile power okuma güçlendirildi (fallback: `reading.totals.power_kw`).
  - `tests/test_api_main_endpoints.py`: Meter önceliğini doğrulayan yeni test eklendi.
- **Test/Doğrulama:**
  - `./env/bin/python -m py_compile api/routers/station.py` → ✅
  - `./env/bin/python -m py_compile tests/test_api_main_endpoints.py` → ✅
  - `./env/bin/pytest tests/test_api_main_endpoints.py` → ✅
  - `./env/bin/pytest` → ✅ 546 passed, 4 skipped

#### ✅ RL/LOCK telemetri açıklaması ve uyarılar (03:50:00)
- **Görev:** `/api/status` içinde RL/LOCK alanlarını daha anlaşılır hale getirmek
- **Açıklama:** Sahada şarj esnasında `RL=0` ve `LOCK=0` görülebiliyor. Donanımda lock/relay feedback yoksa bu normaldir; bekleniyorsa firmware mapping/telemetry eksik olabilir. Bu belirsizliği azaltmak için status payload’a açıklama ve soft uyarı eklendi.
- **İmplementasyon:**
  - `api/routers/status.py`: `data.telemetry` bloğu eklendi (`relay_feedback`, `lock_engaged`, `note`). CHARGING/PAUSED iken RL/LOCK=0 ise `data.warnings` altında uyarı kodları eklenir.
  - `tests/test_api_endpoints.py`: Status response içinde `telemetry` bloğunu doğrulayan assertion eklendi.
- **Test/Doğrulama:**
  - `python3 -m py_compile api/routers/status.py` → ✅
  - `python3 -m py_compile tests/test_api_endpoints.py` → ✅
  - `./env/bin/pytest tests/test_api_endpoints.py` → ✅ 12 passed

#### ✅ 3‑Faz Total Power + Mobile Energy Tutarlılığı (00:22:00)
- **Görev:** Meter total güç (kW) ve mobil payload enerji/power tutarlılığını düzeltmek
- **Açıklama:** Gerçek EV testinde faz değerleri 3‑faz ~10 kW iken API tarafında `power_kw` ve `totals.power_kw` alanları tek faz (~3.4 kW) gibi dönüyordu. Ayrıca session başlangıcında saklanan enerji değeri bazı sayaçlarda “total” üzerinden yazıldığı için mobil tarafta import register ile delta tutarsızlaşıp `session.energy_kwh` null kalabiliyordu.
- **İmplementasyon:**
  - `api/meter/modbus.py` (ABB): Faz güçleri varsa toplam güç fazların toplamından normalize edilip `reading.power_kw`, `totals.power_kw` ve `phase_values.power_kw.total` alanlarına yansıtıldı.
  - `api/meter/acrel.py` (Acrel): Total güç seçimi under‑reporting’i önleyecek şekilde (PF + V/I türetimi ile) yeniden düzenlendi.
  - `api/session/events_lifecycle.py`: Session start/end enerji kaydı için mümkünse `totals.energy_import_kwh` tercih edilecek şekilde güncellendi (fallback: `energy_kwh`).
  - `api/logging_setup.py`: Varsayılan log rotation yedek sayısı workspace log boyutu limitine uyum için 5 → 3 düşürüldü; eski `api.log.4` temizlendi.
- **Test/Doğrulama:**
  - `./env/bin/python -m py_compile api/meter/modbus.py` → ✅
  - `./env/bin/python -m py_compile api/meter/acrel.py` → ✅
  - `./env/bin/python -m py_compile api/session/events_lifecycle.py` → ✅
  - `./env/bin/pytest tests/test_mobile_api.py` → ✅ 3 passed

### 2025-12-13

#### ✅ Workspace Temizliği ve Log Rotasyonu (00:59:00)
- **Görev:** Workspace temizliği ve arşivleme
- **Açıklama:** Workspace boyutu 172 MB ölçülüyordu (env 94 MB, logs 37 MB). Eski log dosyaları (api.log.*) silindi, aktif loglar sıfırlandı ve standart script ile teyit edilerek workspace boyutu (env/logs hariç) 29.13 MB olarak doğrulandı.
- **Öncelik:** 0 (Acil) – Workspace standart ihlali şüphesi
- **Başlangıç:** 2025-12-13 00:45:00
- **Bitiş:** 2025-12-13 00:59:00
- **İmplementasyon:**
  - `logs/api.log.1`, `logs/api.log.2`, `logs/api.log.3` dosyaları silindi.
  - `logs/api.log`, `logs/system.log`, `logs/esp32.log`, `logs/session.log`, `logs/incident.log` dosyaları sıfırlandı (log rotasyonu sonrası yeni kayıtlar için hazır).
  - Genel boyut ölçümü `du -sh .` ile 135 MB olarak teyit edildi (önce 172 MB).
  - Workspace denetimi `python3 scripts/workspace_auto_check.py` ile yapıldı (env/logs hariç 29.13 MB, env 102.07 MB, logs 0.01 MB).
- **Test/Doğrulama:**
  - `python3 scripts/workspace_auto_check.py` (önce ve sonra) → ✅ tüm kontroller geçti, env boyutu uyarı seviyesinde raporlandı.
  - Manuel boyut ölçümü: `du -sh .`, `du -sh logs`.

#### ✅ Virtualenv Boyutu Küçültme (01:55:00)
- **Görev:** env/ klasörünü uyarı eşiği altına çek
- **Açıklama:** Test çalışmaları sonrası env boyutu tekrar 85MB seviyesine çıktı. __pycache__ ve .pyc temizliği ile env/logs hariç metrikler stabil hale getirildi.
- **İşlemler:**
  - `find env -type d -name '__pycache__' -delete`
  - `find env -name '*.pyc' -delete`
  - `python3 scripts/workspace_auto_check.py` → env 76.73 MB, logs 2.90 MB, toplam (env/logs hariç) 29.26 MB

#### ✅ API ve Test Standart Refactor Paketi (02:45:00)
- **Görev:** Standart uyarısı veren API modülleri ve test dosyalarını modüler yapıya kavuşacak şekilde bölmek
- **Kapsam:**
  - `api/cache.py` → Backend sınıfları `api/cache_backend.py` içine taşındı, dekoratör ve invalidator kodu sadeleştirildi.
  - `api/logging_config.py` → Logger kurulum mantığı `api/logging_setup.py` modülüne ayrıldı, context getter tabanlı JSON formatter eklendi.
  - `api/event_detector.py` → Enum tanımları `api/event_types.py` dosyasına taşınarak asıl dosya 378 satıra indirildi.
  - `api/alerting.py` → Model sınıfları `api/alerting_models.py` dosyasında toparlandı, `AlertManager` sadece yönetim mantığı barındırıyor.
  - `api/session/events.py` → Lifecycle ve logging yardımcıları `api/session/events_lifecycle.py` ve `api/session/events_logging.py` altına bölündü (125 satır).
  - `api/database/core.py` → Şema/optimizasyon kodu `api/database/schema_mixin.py` mixin'ine taşındı (181 satır).
  - `api/routers/status.py` → Health endpoint'i `api/services/health_service.py` üzerine alındı, router dosyası 128 satır.
- **Test Dosyaları Bölünmesi:**
  - `tests/test_session_manager.py` → `tests/test_session_model.py` ve `tests/test_session_manager_integration.py` ile desteklendi (369 satır).
  - `tests/test_event_detector.py` → `tests/test_event_detector_integration.py` ile ayrıldı (368 satır).
  - `tests/test_command_dry_run.py` → Protokol kontrolleri `tests/test_command_protocol.py` dosyasına taşındı (388 satır).
  - `tests/test_protocol.py` → Kural ve edge case senaryoları `tests/test_protocol_rules.py` dosyasına taşındı (319 satır).
- **Doğrulama:** İlgili tüm pytest dosyaları ayrı ayrı çalıştırıldı; `scripts/standards_auto_check.py` sonuçları temiz.

#### ✅ Mobil Şarj API ve Testleri (03:20:00)
- **Görev:** Mobil uygulama için şarj durumu ve geçmiş oturum endpoint'leri sağlamak
- **Açıklama:** Mobil ekip, tek çağrıda cihaz durumu, aktif oturum ve maliyet bilgisini alabilecekleri bir API talep etti. `/form` üzerinden verilen 1 kWh fiyat bilgisi de maliyet hesaplamalarına dahil edildi.
- **İmplementasyon:**
  - `/api/mobile/charging/current` → cihaz bilgisi, ölçümler, aktif session özeti, trend ve aktif alert’leri tek payload’da döndürüyor.
  - `/api/mobile/charging/sessions` → tarih aralığı, kullanıcı ve status filtresiyle geçmiş oturumları listeliyor.
  - `/api/mobile/charging/sessions/{session_id}` → tamamlanmış oturumlar için detaylı rapor, maliyet hesabı ve snapshot listesi üretiyor.
  - Meter okuması, session manager ve alert manager verileri tek servis içinde birleştirildi; station formundaki `price_per_kwh` değeri otomatik çekiliyor.
  - Yeni `tests/test_mobile_api.py` paketi ile canlı durum, detay ve tarih filtresi senaryoları için üç adet entegrasyon testi eklendi.
- **Dosyalar:** `api/routers/mobile.py`, `api/main.py`, `tests/test_mobile_api.py`, `project_info_20251208_145614.md`
- **Testler:** `./env/bin/pytest tests/test_mobile_api.py` ve tam suite (`./env/bin/pytest`)

### 2025-12-12 ve Öncesi (Arşiv Özeti)

Bu bölüm, `todo/master_done.md` dosyasının **dokümantasyon boyut standardına (<=1200 satır)** uyması için özetlenmiştir.
Detaylı geçmiş için:
- `todo/checkpoint.md` (checkpoint kanıtları / süreç özeti)
- İlgili `docs/` raporları (audit, deep dive, deployment, troubleshooting)
- Git commit geçmişi

Öne çıkanlar (özet):
- ✅ Meter entegrasyonu (ABB) + sahada doğrulama; sonrasında Acrel meter ve `/test` UI stabilizasyonu çalışmaları
- ✅ Pytest suite stabilizasyonu (özellikle rate limiting/test env etkileşimi)
- ✅ `api/database/*` refactor ve erken dönem standart uyumu
- ✅ İlk kurulum/otomasyon/analiz çıktıları (todo + docs içinde SSOT)
- ✅ ESP32-RPi bridge modülü (`esp32/bridge.py`) + serial protokol iletişimi
- ✅ FastAPI temel uygulama + temel endpoint'ler + API dokümantasyonu

