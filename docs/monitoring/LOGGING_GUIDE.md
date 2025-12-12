# Logging Guide

**Oluşturulma Tarihi:** 2025-12-12 05:55:00
**Son Güncelleme:** 2025-12-12 05:55:00
**Version:** 1.0.0

---

## Amaç

Bu rehber, Charger projesindeki tüm log akışlarını (API, ESP32, session, incident) nasıl ürettiğimizi ve nasıl analiz edebileceğimizi açıklar. Amaç, herhangi bir hata anında sürecin fotoğrafını çıkarabilmek ve incident kök nedenini dakikalar içinde bulmaktır.

---

## Log Dosyaları

| Dosya | Açıklama | Format |
| --- | --- | --- |
| `logs/api.log` | FastAPI istek/metrik logları, correlation_id içerir | JSON satır |
| `logs/esp32.log` | ESP32 komut/ACK/status logları | JSON satır |
| `logs/system.log` | Genel sistem event’leri ve uyarılar | JSON satır |
| `logs/session.log` | Her session akışı için snapshot ve metrik kayıtları | JSON satır |
| `logs/incident.log` | Incident odaklı kayıtlar (ACK timeout, EV power uyarısı vb.) | JSON satır (WARN+) |

Tüm loglar 10 MB + 5 yedek olacak şekilde rotate edilir. Üretimde ek olarak syslog, Loki veya ELK gibi merkezi loglayıcıya yönlendirilmesi tavsiye edilir.

---

## Correlation ID & Context

- `APILoggingMiddleware`, her HTTP isteği için `X-Request-ID` üretir ve response header’ına yazar.
- `api/logging_config.py` contextvar tabanlı `correlation_id`, `session_id`, `user_id` alanlarını otomatik olarak JSON formatter’a ekler.
- Session tarafında `_log_session_snapshot` yardımıyla aynı ID tüm snapshot’larda bulunur; JSON aramasıyla komple akış çıkarılabilir.

---

## Session Snapshot Akışı

`api/session/events.py` ve `api/session/manager.py` kritik anlarda snapshot yazar:

1. **SESSION_STARTED** – user_id, başlangıç state’i, meter bilgisi.
2. **Event işleme** – her state değişimi için status payload, CP/PP voltajı ve akım.
3. **Fault / DB hatası** – incident loguna da düşer.
4. **SESSION_ENDED** – final metrikler (`duration_seconds`, `energy_kwh`, akım/voltaj istatistikleri).

Snapshot örneği:

```json
{
  "timestamp": "2025-12-12T05:52:01.123456",
  "level": "INFO",
  "logger": "session",
  "message": "Session event işlendi",
  "session_id": "5c5f...",
  "event_type": "CHARGE_STARTED",
  "status": {"STATE": 5, "CABLE": 16, "MAX": 32},
  "user_id": "demo-user"
}
```

---

## Incident Logging

`incident.log` kritik sorunlarda iki kaynağı birleştirir:

- **ESP32Bridge**
  - ACK timeout, seri port kopması, EV “external equipment not providing power” uyarısı, CHARGING state’inde uzun süre akım çekilmeme (default 120 s) gibi durumlar throttle edilerek loglanır.
- **EventDetector**
  - Status içindeki WARNING/MESSAGE alanlarında “external equipment … power” kalıbı geçtiğinde incident üretir.

Her incident, `incident_title`, `severity`, `status` gibi alanlarla merkezi izleme sistemine forward edilebilir.

---

## Session Log Export Script

Yeni script: `scripts/session_log_export.py`

```bash
# JSON (pretty) çıktı
python3 scripts/session_log_export.py <SESSION_ID> --pretty > session.json

# CSV çıktı
python3 scripts/session_log_export.py <SESSION_ID> --format csv --output session.csv
```

Çıktı içeriği:
- `db_session`: `data/sessions.db` içindeki ana kayıt
- `db_event`: `session_events` tablosundaki event satırları
- `log_snapshot`: `logs/session.log` içindeki tüm snapshot’lar

DB veya log dosyası bulunamazsa script uyarı vermeden ilgili alanları boş döndürür (JSON raporda `None` olarak).

---

## Üretim Tavsiyeleri

1. **Rotasyon / Retention**
   - Varsayılan 10 MB × 5 log, yaklaşık 24 saatlik snapshot saklar. Üretimde `logrotate` veya merkezi loglayıcıyla 30 günlük retention önerilir.
2. **Merkezi İzleme**
   - `incident.log` dosyası WARN seviyesinde olduğu için Promtail/Fluent Bit aracılığıyla Slack/E-mail uyarılarına bağlanabilir.
3. **Ham Log Analizi**
   - Incident gerçekleştiğinde `session_log_export.py` ile ilgili session kimliğini dışa aktarın ve raporu incident kaydına ekleyin.
4. **Güvenlik**
   - Loglar kullanıcı API key hash’lerini (ilk 16 karakter) içerir; tam API key hiçbir logda tutulmaz.

---

## Referanslar

- `api/logging_config.py` – Logger tanımları, context filter, helper fonksiyonlar
- `api/main.py` – Correlation ID middleware
- `api/session/events.py` – Snapshot üretimi
- `esp32/bridge.py` – ESP32 incident tespiti
- `api/event_detector.py` – State transition ve power warning tespiti
