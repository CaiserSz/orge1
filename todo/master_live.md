# Aktif Görevler (Şu Anda Yapılanlar)

**Son Güncelleme:** 2025-12-21 20:45:00

---

## Aktif Görevler

- **OCPP Phase-1 (Station Client)** – 2025-12-16 (ocpp/phase1 branch)
  - Durum: 🔄 Devam ediyor
  - Kapsam: Tek transport + iki adapter (Primary: OCPP 2.0.1, Fallback: OCPP 1.6j)
  - CSMS: `lixhium.xyz` (BasicAuth + ocpp2.0.1 / ocpp1.6)
  - İlerleme: Daemon mode (Boot/Status/Heartbeat + reconnect) + local API read-only polling (station status + meter values + sessions→TransactionEvent) ✅
  - İlerleme: Phase‑1.4 Runbook (A/B/C) evidence ✅ + UI Remote Ops (daemon) Remote Start/Stop evidence ✅ (SSOT: `docs/csms/CSMS_CONNECTION_PARAMETERS.md`)
  - İlerleme: OCPP modüler refactor ✅ (tüm `ocpp/*.py` <= 500 satır; `main.py`/`handlers.py` bakım riski azaltıldı)
  - Not: Mevcut API/ESP32/session sistemi bozulmayacak; OCPP ayrı proses olarak ilerleyecek.

- Şu anda başka aktif görev yok. Son tamamlanan işler:
  0. **RL/LOCK telemetri açıklaması** – 2025-12-14 03:50 (`/api/status` telemetry + warnings)
  0. **/api/station/status realtime_power_kw doğrulama** – 2025-12-14 03:30 (`realtime_power_kw` meter ölçümü öncelikli)
  0. **3‑faz total power + mobile energy tutarlılığı** – 2025-12-14 02:55 (`/api/meter/reading`, mobile payload)
  1. **env/ boyutu temizliği** – 2025-12-13 01:55 (env 76.7 MB, `workspace_auto_check` ✅)
  2. **API & test standart refactor paketi** – 2025-12-13 02:45 (tüm uyarılar kaldırıldı)
  3. **Mobil şarj API & testleri** – 2025-12-13 03:20 (`/api/mobile/charging/*`, `tests/test_mobile_api.py`)

---

## Notlar

- Aktif görevler buraya eklenecek
- Maksimum 2-3 aktif görev olmalı
- Her görev tamamlandığında `master_done.md`'ye taşınacak
