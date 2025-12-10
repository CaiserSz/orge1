# Error Recovery Dokümantasyonu

**Oluşturulma Tarihi:** 2025-12-10 18:45:00
**Son Güncelleme:** 2025-12-10 18:45:00
**Version:** 1.0.0

---

## Genel Bakış

ESP32-RPi iletişimi için error recovery mekanizması iyileştirilmiştir. Sistem, connection error recovery, timeout handling ve exponential backoff retry ile hata durumlarını otomatik olarak handle eder.

---

## Connection Error Recovery

### reconnect() Fonksiyonu

ESP32 bağlantısını yeniden kurma mekanizması exponential backoff retry kullanır:

```python
def reconnect(
    self,
    max_retries: Optional[int] = None,
    retry_delay: Optional[float] = None
) -> bool:
    # Exponential backoff retry
    # Delay: 5s, 10s, 20s, 30s (max)
```

**Özellikler:**
- Exponential backoff retry (RetryConfig kullanılıyor)
- Maksimum 30 saniye bekleme
- Yapılandırılabilir retry sayısı ve delay
- Bağlantı durumu tracking

**Retry Delay Hesaplama:**
- Initial delay: 5 saniye (varsayılan)
- Multiplier: 2.0
- Max delay: 30 saniye

| Attempt | Delay (s) |
|---------|-----------|
| 1       | 5.0       |
| 2       | 10.0      |
| 3       | 20.0      |
| 4       | 30.0 (max)|

---

## Timeout Handling İyileştirmesi

### get_status_sync() Fonksiyonu

Status komutu gönderme ve yanıt bekleme fonksiyonu iyileştirildi:

**Öncesi:**
- Sabit 0.1s check interval
- Bağlantı durumu kontrolü yok
- Timeout sonrası sadece None döndürme

**Sonrası:**
- 0.05s check interval (daha responsive)
- Periyodik bağlantı durumu kontrolü (her 0.5 saniyede bir)
- Bağlantı kopması durumunda erken çıkış
- Detaylı logging

**İyileştirmeler:**
- Daha hızlı response (50ms check interval)
- Bağlantı durumu monitoring
- Erken hata tespiti
- Daha iyi error handling

### _wait_for_ack() Fonksiyonu

ACK bekleme fonksiyonu zaten iyi durumda, ancak timeout handling dokümante edildi.

---

## Serial Port Error Recovery

### _read_status_messages() Fonksiyonu

Serial port okuma fonksiyonunda error recovery iyileştirildi:

**Hata Türleri:**

1. **Device Disconnected**
   - Otomatik reconnection denenir
   - Exponential backoff retry kullanılır

2. **Multiple Access**
   - Otomatik reconnection denenir
   - Exponential backoff retry kullanılır

3. **Device or Resource Busy**
   - Otomatik reconnection denenir
   - Exponential backoff retry kullanılır

4. **Timeout**
   - Bağlantı durumu kontrol edilir
   - Bağlantı kopmuşsa reconnection denenir

5. **Bilinmeyen Hatalar**
   - Bağlantı durumu kontrol edilir
   - Bağlantı kopmuşsa reconnection denenir

---

## Monitor Loop Error Recovery

### _monitor_loop() Fonksiyonu

Monitor loop'ta error recovery iyileştirildi:

**Öncesi:**
- Sabit 30 saniye bekleme
- Ardışık hata sayısı takibi

**Sonrası:**
- Exponential backoff bekleme (30s, 60s, 120s, ... max 300s)
- Ardışık hata sayısı takibi
- Daha akıllı recovery mekanizması

**Bekleme Süresi Hesaplama:**
```
wait_time = min(30 * (2 ^ (consecutive_errors - max_consecutive_errors)), 300)
```

| Consecutive Errors | Wait Time (s) |
|-------------------|---------------|
| 10                | 30            |
| 11                | 60            |
| 12                | 120           |
| 13                | 240           |
| 14+               | 300 (max)     |

---

## Error Recovery Senaryoları

### Senaryo 1: Bağlantı Kopması

```
1. Serial port hatası tespit edilir
2. is_connected = False
3. reconnect() çağrılır (exponential backoff)
4. Bağlantı kurulursa → Normal çalışmaya devam
5. Bağlantı kurulamazsa → Monitor loop'ta tekrar denenir
```

### Senaryo 2: Timeout Hatası

```
1. Timeout hatası tespit edilir
2. Bağlantı durumu kontrol edilir
3. Bağlantı açıksa → Uyarı verilir, devam edilir
4. Bağlantı kapalıysa → reconnect() çağrılır
```

### Senaryo 3: Ardışık Hatalar

```
1. Ardışık hata sayısı artar
2. Max consecutive errors'a ulaşırsa
3. Exponential backoff ile bekleme (30s → 60s → 120s → ...)
4. Bekleme sonrası tekrar deneme
```

---

## İyileştirmeler

### Öncesi

- Sabit retry delay (5 saniye)
- Basit error recovery
- Timeout handling eksik
- Monitor loop'ta sabit bekleme

### Sonrası

- Exponential backoff retry
- Gelişmiş error recovery (farklı hata türleri için)
- İyileştirilmiş timeout handling
- Monitor loop'ta exponential backoff bekleme
- Bağlantı durumu monitoring
- Daha responsive error detection

---

## Kullanım Örnekleri

### Manuel Reconnection

```python
bridge = ESP32Bridge()
if not bridge.is_connected:
    success = bridge.reconnect(max_retries=5, retry_delay=2.0)
    if success:
        print("Bağlantı başarılı")
    else:
        print("Bağlantı başarısız")
```

### Status Sync (Timeout Handling)

```python
bridge = ESP32Bridge()
status = bridge.get_status_sync(timeout=3.0)
if status:
    print(f"Status: {status['STATE_NAME']}")
else:
    print("Status alınamadı (timeout veya bağlantı hatası)")
```

---

## Sorun Giderme

### Reconnection Çalışmıyor

1. `_reconnect_enabled` kontrol edin:
   ```python
   bridge._reconnect_enabled = True
   ```

2. Retry modülü import edilebiliyor mu kontrol edin:
   ```python
   from esp32.retry import RetryConfig
   ```

### Timeout Çok Sık Oluyor

1. `timeout` parametresini artırın
2. ESP32 bağlantısını kontrol edin
3. Serial port durumunu kontrol edin

### Monitor Loop Çok Sık Hata Veriyor

1. Serial port bağlantısını kontrol edin
2. ESP32 firmware'inin çalıştığını kontrol edin
3. Baudrate ayarını kontrol edin (115200)

---

## Referanslar

- [Retry Logic Dokümantasyonu](RETRY_LOGIC.md)
- [ESP32 Bridge Dokümantasyonu](../architecture.md)

---

**Son Güncelleme:** 2025-12-10 18:45:00

