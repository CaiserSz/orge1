# Health Check Metrikleri Dokümantasyonu

**Oluşturulma Tarihi:** 2025-12-10 01:30:00
**Son Güncelleme:** 2025-12-10 01:30:00
**Version:** 1.0.0

---

## 📊 Health Check Metrikleri

`/api/health` endpoint'i artık detaylı sistem metrikleri sağlıyor:

### Mevcut Metrikler

#### 1. API Durumu
- `api`: "healthy" (API servisi durumu)

#### 2. ESP32 Bağlantı Durumu
- `esp32_connected`: Boolean (ESP32 bağlantı durumu)
- `esp32_status`: "available" | "no_status" | "disconnected"
- `reconnect_attempts`: Integer (opsiyonel, reconnection deneme sayısı)

#### 3. Event Detector Durumu
- `event_detector.monitoring`: Boolean (monitoring aktif mi?)
- `event_detector.thread_alive`: Boolean (monitor thread çalışıyor mu?)

#### 4. Process Metrikleri
- `threads`: Integer (aktif thread sayısı)
- `memory_mb`: Float (process memory kullanımı, MB)
- `cpu_percent`: Float | null (process CPU kullanımı %, psutil gerektirir)
- `memory_percent`: Float | null (process memory kullanımı %, psutil gerektirir)

#### 5. Sistem Metrikleri
- `system_memory_percent`: Float (sistem genel memory kullanımı %)
- `system_memory_total_mb`: Float (toplam sistem memory, MB)
- `system_memory_available_mb`: Float (kullanılabilir sistem memory, MB)
- `system_cpu_percent`: Float | null (sistem genel CPU kullanımı %, psutil gerektirir)
- `load_average`: Object
  - `1min`: Float (1 dakikalık load average)
  - `5min`: Float (5 dakikalık load average)
  - `15min`: Float (15 dakikalık load average)

---

## 🔧 Teknik Detaylar

### Metrik Toplama Yöntemleri

#### 1. /proc Dosya Sistemi (Varsayılan)

**Avantajlar:**
- Ekstra dependency gerektirmez
- Hafif ve hızlı
- Linux sistemlerde standart

**Kullanılan Dosyalar:**
- `/proc/[pid]/status` - Process memory bilgisi
- `/proc/meminfo` - Sistem memory bilgisi
- `/proc/loadavg` - Load average bilgisi

**Sınırlamalar:**
- Gerçek zamanlı CPU% hesaplama zor
- Sadece Linux'ta çalışır

#### 2. psutil Modülü (Opsiyonel)

**Avantajlar:**
- Gerçek zamanlı CPU% hesaplama
- Cross-platform desteği
- Daha detaylı metrikler

**Kurulum:**
```bash
pip install psutil
```

**Kullanım:**
- psutil varsa otomatik kullanılır
- Yoksa /proc yöntemi kullanılır
- Graceful degradation

---

## 📈 Örnek Response

### psutil Olmadan (Varsayılan)

```json
{
  "success": true,
  "message": "System health check",
  "data": {
    "api": "healthy",
    "esp32_connected": true,
    "esp32_status": "available",
    "event_detector": {
      "monitoring": true,
      "thread_alive": true
    },
    "threads": 4,
    "memory_mb": 46.74,
    "cpu_percent": null,
    "cpu_note": "Real-time CPU% requires psutil module",
    "system_memory_percent": 34.2,
    "system_memory_total_mb": 3796.74,
    "system_memory_available_mb": 2498.32,
    "load_average": {
      "1min": 0.73,
      "5min": 0.79,
      "15min": 0.67
    }
  },
  "timestamp": "2025-12-10T01:28:00.860412"
}
```

### psutil ile (Opsiyonel)

```json
{
  "success": true,
  "message": "System health check",
  "data": {
    "api": "healthy",
    "esp32_connected": true,
    "esp32_status": "available",
    "event_detector": {
      "monitoring": true,
      "thread_alive": true
    },
    "threads": 4,
    "memory_mb": 46.74,
    "memory_percent": 1.2,
    "cpu_percent": 2.7,
    "system_memory_percent": 34.2,
    "system_memory_total_mb": 3796.74,
    "system_memory_available_mb": 2498.32,
    "system_cpu_percent": 5.3,
    "load_average": {
      "1min": 0.73,
      "5min": 0.79,
      "15min": 0.67
    }
  },
  "timestamp": "2025-12-10T01:28:00.860412"
}
```

---

## 🎯 Kullanım Senaryoları

### 1. Monitoring Dashboard

Health check endpoint'i monitoring dashboard'ları için ideal:

```javascript
async function updateHealthMetrics() {
  const response = await fetch('/api/health');
  const data = await response.json();

  // CPU ve Memory grafikleri için kullan
  updateCPUChart(data.data.cpu_percent);
  updateMemoryChart(data.data.memory_percent);
  updateSystemMemoryChart(data.data.system_memory_percent);
}
```

### 2. Alerting

Metrikler alerting sistemleri için kullanılabilir:

```python
health = get_health_check()
if health['system_memory_percent'] > 80:
    send_alert("High memory usage")
if health['cpu_percent'] and health['cpu_percent'] > 80:
    send_alert("High CPU usage")
```

### 3. Performance Monitoring

Sistem performansını izlemek için:

```python
metrics = []
for _ in range(60):  # 1 dakika boyunca
    health = get_health_check()
    metrics.append({
        'cpu': health['cpu_percent'],
        'memory': health['memory_percent'],
        'timestamp': health['timestamp']
    })
    time.sleep(1)
```

---

## ⚡ Performans Etkisi

### Metrik Toplama Maliyeti

**/proc Yöntemi:**
- Çok hafif (< 1ms)
- Dosya okuma işlemleri minimal
- CPU% hesaplama yok (performans avantajı)

**psutil Yöntemi:**
- Biraz daha maliyetli (~10-50ms)
- CPU% hesaplama için interval gerekli (0.1s)
- Daha detaylı bilgi

### Öneriler

1. **Production'da:** psutil kullanmak önerilir (gerçek zamanlı CPU%)
2. **Development'ta:** /proc yöntemi yeterli
3. **High-frequency monitoring:** Cache mekanizması eklenebilir

---

## 🔍 Metrik Açıklamaları

### Memory Metrikleri

- **memory_mb**: Process'in kullandığı fiziksel memory (RSS)
- **memory_percent**: Process'in sistem memory'sine göre kullanım yüzdesi
- **system_memory_percent**: Sistem genel memory kullanım yüzdesi
- **system_memory_total_mb**: Toplam sistem memory
- **system_memory_available_mb**: Kullanılabilir sistem memory

### CPU Metrikleri

- **cpu_percent**: Process'in CPU kullanım yüzdesi (gerçek zamanlı)
- **system_cpu_percent**: Sistem genel CPU kullanım yüzdesi
- **load_average**: Sistem yük ortalaması (1min, 5min, 15min)

### Load Average Açıklaması

Load average, sistemin ne kadar meşgul olduğunu gösterir:
- **< 1.0**: Sistem boşta
- **1.0**: Sistem tam kapasitede
- **> 1.0**: Sistem aşırı yüklü (bekleme var)

---

## 🛠️ İyileştirme Önerileri

### 1. psutil Kurulumu (Önerilen)

```bash
cd /home/basar/charger
source env/bin/activate
pip install psutil
```

**Avantajlar:**
- Gerçek zamanlı CPU% metrikleri
- Daha detaylı sistem bilgisi
- Cross-platform desteği

### 2. Cache Mekanizması (Opsiyonel)

Yüksek frekanslı monitoring için cache eklenebilir:

```python
# 5 saniye cache
_last_health_check = None
_cache_duration = 5.0

if _last_health_check and (time.time() - _last_health_check['timestamp']) < _cache_duration:
    return _last_health_check['data']
```

### 3. Metrik Filtreleme (Opsiyonel)

İhtiyaca göre metrikleri filtrelemek:

```python
# Sadece kritik metrikler
minimal_health = {
    'api': health['api'],
    'esp32_connected': health['esp32_connected'],
    'system_memory_percent': health['system_memory_percent']
}
```

---

## 📝 Notlar

- Health check endpoint'i hafif tutulmalı (performans için)
- Metrik toplama hataları kritik değil (graceful degradation)
- psutil opsiyonel - yoksa sistem çalışmaya devam eder
- Load average Linux'ta standart, diğer sistemlerde farklı olabilir

---

## 🔗 İlgili Dokümantasyon

- **API Referansı:** `docs/api_reference.md`
- **Deep Dive Analizi:** `docs/DEEP_DIVE_ANALYSIS.md`
- **Monitoring Script:** `scripts/system_monitor.py`

