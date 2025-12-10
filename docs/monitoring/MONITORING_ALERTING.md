# Monitoring ve Alerting Dokümantasyonu

**Oluşturulma Tarihi:** 2025-12-10 18:00:00  
**Son Güncelleme:** 2025-12-10 18:00:00  
**Version:** 1.0.0

---

## Genel Bakış

Charger API projesi için Prometheus/Grafana entegrasyonu ve alerting sistemi implement edilmiştir. Sistem, metrikleri Prometheus formatında export eder ve otomatik alerting mekanizması sağlar.

---

## Prometheus Metrics

### Metrics Endpoint

**Endpoint:** `GET /api/metrics`

Prometheus tarafından scrape edilebilir metrics endpoint'i. Tüm sistem metriklerini Prometheus formatında döndürür.

**Örnek Kullanım:**
```bash
curl http://localhost:8000/api/metrics
```

### Export Edilen Metrikler

#### HTTP Request Metrikleri

- `http_requests_total` (Counter): Toplam HTTP istek sayısı
  - Labels: `method`, `endpoint`, `status_code`
  
- `http_request_duration_seconds` (Histogram): HTTP istek süresi (saniye)
  - Labels: `method`, `endpoint`
  - Buckets: [0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]

#### ESP32 Metrikleri

- `esp32_connected` (Gauge): ESP32 bağlantı durumu (1=bağlı, 0=bağlı değil)
- `esp32_reconnect_attempts_total` (Counter): Toplam ESP32 yeniden bağlanma denemesi
- `esp32_status_age_seconds` (Gauge): Son ESP32 status güncellemesinin yaşı (saniye)

#### Sistem Metrikleri

- `system_memory_usage_percent` (Gauge): Sistem bellek kullanım yüzdesi
- `system_cpu_usage_percent` (Gauge): Sistem CPU kullanım yüzdesi
- `system_disk_usage_percent` (Gauge): Sistem disk kullanım yüzdesi
- `system_cpu_temperature_celsius` (Gauge): CPU sıcaklığı (Celsius)

#### API Metrikleri

- `api_active_sessions` (Gauge): Aktif şarj session sayısı
- `api_total_sessions` (Counter): Toplam session sayısı
  - Labels: `status`

#### Event Detector Metrikleri

- `event_detector_monitoring` (Gauge): Event detector monitoring durumu (1=monitoring, 0=durduruldu)
- `event_detector_events_total` (Counter): Toplam tespit edilen event sayısı
  - Labels: `event_type`

#### Application Info

- `app_info` (Info): Uygulama bilgileri
  - `version`: Uygulama versiyonu
  - `name`: Uygulama adı

---

## Alerting Sistemi

### Alert Endpoint

**Endpoint:** `GET /api/alerts`

Sistemdeki aktif alert'leri döndürür.

**Örnek Kullanım:**
```bash
curl http://localhost:8000/api/alerts
```

**Response Formatı:**
```json
{
  "success": true,
  "message": "Active alerts: 2",
  "data": {
    "active_alerts": [
      {
        "name": "esp32_disconnected",
        "severity": "critical",
        "message": "ESP32 is disconnected",
        "timestamp": "2025-12-10T18:00:00",
        "metadata": {}
      }
    ],
    "count": 1
  }
}
```

### Alert Severity Levels

- **INFO**: Bilgilendirme amaçlı alert'ler
- **WARNING**: Uyarı seviyesi alert'ler (sistem çalışmaya devam ediyor)
- **CRITICAL**: Kritik seviye alert'ler (acil müdahale gerekli)

### Varsayılan Alert Rules

#### 1. ESP32 Disconnected (CRITICAL)

**Kural:** ESP32 bağlantısı kopmuşsa alert tetiklenir.

**Threshold:** `bridge.is_connected == False`

**Severity:** CRITICAL

#### 2. ESP32 Status Stale (WARNING)

**Kural:** ESP32 status güncellemesi 30 saniyeden eskiyse alert tetiklenir.

**Threshold:** `status_age > 30 seconds`

**Severity:** WARNING

#### 3. High Memory Usage (WARNING/CRITICAL)

**Kural:** Sistem bellek kullanımı yüksekse alert tetiklenir.

**Thresholds:**
- WARNING: `memory_usage > 80%`
- CRITICAL: `memory_usage > 90%`

**Severity:** WARNING → CRITICAL

#### 4. High CPU Usage (WARNING/CRITICAL)

**Kural:** Sistem CPU kullanımı yüksekse alert tetiklenir.

**Thresholds:**
- WARNING: `cpu_usage > 80%`
- CRITICAL: `cpu_usage > 90%`

**Severity:** WARNING → CRITICAL

#### 5. High Disk Usage (WARNING/CRITICAL)

**Kural:** Sistem disk kullanımı yüksekse alert tetiklenir.

**Thresholds:**
- WARNING: `disk_usage > 85%`
- CRITICAL: `disk_usage > 95%`

**Severity:** WARNING → CRITICAL

#### 6. High CPU Temperature (WARNING/CRITICAL)

**Kural:** CPU sıcaklığı yüksekse alert tetiklenir.

**Thresholds:**
- WARNING: `cpu_temperature > 70°C`
- CRITICAL: `cpu_temperature > 80°C`

**Severity:** WARNING → CRITICAL

#### 7. Event Detector Stopped (WARNING)

**Kural:** Event detector durdurulmuşsa alert tetiklenir.

**Threshold:** `event_detector.is_monitoring == False`

**Severity:** WARNING

---

## Prometheus Konfigürasyonu

### Prometheus scrape_config

Prometheus'un metrics endpoint'ini scrape etmesi için `prometheus.yml` dosyasına şu konfigürasyonu ekleyin:

```yaml
scrape_configs:
  - job_name: 'charger-api'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/metrics'
```

### Grafana Dashboard

Grafana'da dashboard oluşturmak için Prometheus veri kaynağını ekleyin ve aşağıdaki metrikleri kullanın:

**Örnek Query'ler:**

- ESP32 Bağlantı Durumu:
  ```
  esp32_connected
  ```

- HTTP Request Rate:
  ```
  rate(http_requests_total[5m])
  ```

- HTTP Request Duration (P95):
  ```
  histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
  ```

- Sistem Bellek Kullanımı:
  ```
  system_memory_usage_percent
  ```

- Sistem CPU Kullanımı:
  ```
  system_cpu_usage_percent
  ```

- Aktif Session Sayısı:
  ```
  api_active_sessions
  ```

---

## Alerting Mekanizması

### Periyodik Değerlendirme

Alert manager, uygulama başlatıldığında otomatik olarak başlatılır ve her 30 saniyede bir alert kurallarını değerlendirir.

### Alert History

Alert history, maksimum 1000 alert kaydı tutar. Eski kayıtlar otomatik olarak temizlenir.

### Alert Logging

Tüm alert'ler sistem loglarına kaydedilir:
- **INFO** alert'ler: `system_logger.info()`
- **WARNING** alert'ler: `system_logger.warning()`
- **CRITICAL** alert'ler: `system_logger.error()`

---

## Kullanım Örnekleri

### Metrics Endpoint'i Test Etme

```bash
# Metrics endpoint'ini kontrol et
curl http://localhost:8000/api/metrics

# Belirli bir metrik için filtreleme (Prometheus query)
curl "http://localhost:8000/api/metrics" | grep "esp32_connected"
```

### Alert Endpoint'i Test Etme

```bash
# Aktif alert'leri kontrol et
curl http://localhost:8000/api/alerts

# JSON formatında görüntüle
curl http://localhost:8000/api/alerts | jq
```

### Prometheus ile Entegrasyon

```bash
# Prometheus'u başlat (Docker)
docker run -d -p 9090:9090 \
  -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus

# Grafana'yı başlat (Docker)
docker run -d -p 3000:3000 grafana/grafana
```

---

## İyileştirme Fırsatları

### Gelecek Geliştirmeler

1. **Alertmanager Entegrasyonu**: Prometheus Alertmanager ile entegrasyon
2. **Notification Channels**: Email, Slack, PagerDuty gibi bildirim kanalları
3. **Custom Alert Rules**: Kullanıcı tanımlı alert kuralları
4. **Alert Suppression**: Alert bastırma mekanizması
5. **Alert Grouping**: Benzer alert'leri gruplama
6. **Alert Escalation**: Alert eskalasyon mekanizması

---

## Sorun Giderme

### Metrics Endpoint'i Çalışmıyor

1. Prometheus client kurulu mu kontrol edin:
   ```bash
   pip list | grep prometheus-client
   ```

2. Metrics modülü import edilebiliyor mu kontrol edin:
   ```bash
   python3 -c "from api.metrics import *; print('OK')"
   ```

### Alert'ler Tetiklenmiyor

1. Alert manager başlatıldı mı kontrol edin (log'larda "Alert manager başlatıldı" mesajı)
2. Periyodik değerlendirme çalışıyor mu kontrol edin (log'larda "Periyodik alert değerlendirme başlatıldı" mesajı)
3. Alert kuralları aktif mi kontrol edin (`/api/alerts` endpoint'inden)

### Prometheus Metrics Görünmüyor

1. Metrics endpoint'i erişilebilir mi kontrol edin:
   ```bash
   curl http://localhost:8000/api/metrics
   ```

2. Prometheus scrape konfigürasyonunu kontrol edin
3. Prometheus log'larını kontrol edin

---

## Referanslar

- [Prometheus Client Python Documentation](https://github.com/prometheus/client_python)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)

---

**Son Güncelleme:** 2025-12-10 18:00:00

