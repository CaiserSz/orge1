# Retry Logic Dokümantasyonu

**Oluşturulma Tarihi:** 2025-12-10 18:30:00
**Son Güncelleme:** 2025-12-10 18:30:00
**Version:** 1.0.0

---

## Genel Bakış

ESP32-RPi iletişimi için retry logic mekanizması implement edilmiştir. Sistem, exponential backoff ve farklı retry stratejileri ile hata durumlarında otomatik retry yapar.

---

## Retry Modülü (`esp32/retry.py`)

### RetryStrategy Enum

Retry stratejileri:

- **LINEAR**: Sabit gecikme (constant delay)
- **EXPONENTIAL**: Exponential backoff (varsayılan)
- **FIBONACCI**: Fibonacci backoff

### RetryConfig Sınıfı

Retry konfigürasyonu:

```python
config = RetryConfig(
    max_retries=3,          # Maksimum retry sayısı
    initial_delay=0.1,      # İlk gecikme (saniye)
    max_delay=5.0,          # Maksimum gecikme (saniye)
    strategy=RetryStrategy.EXPONENTIAL,  # Retry stratejisi
    multiplier=2.0,         # Exponential backoff çarpanı
)
```

### Retry Delay Hesaplama

#### Exponential Backoff

```
delay = initial_delay * (multiplier ^ attempt)
delay = min(delay, max_delay)
```

**Örnek:**
- initial_delay = 0.1s
- multiplier = 2.0
- max_delay = 1.0s

| Attempt | Delay (s) |
|---------|-----------|
| 0       | 0.1       |
| 1       | 0.2       |
| 2       | 0.4       |
| 3       | 0.8       |
| 4       | 1.0 (max) |

#### Fibonacci Backoff

```
delay = initial_delay * fibonacci(attempt + 1)
delay = min(delay, max_delay)
```

**Örnek:**
- initial_delay = 0.1s
- max_delay = 5.0s

| Attempt | Fibonacci | Delay (s) |
|---------|-----------|-----------|
| 0       | 1         | 0.1       |
| 1       | 1         | 0.1       |
| 2       | 2         | 0.2       |
| 3       | 3         | 0.3       |
| 4       | 5         | 0.5       |
| 5       | 8         | 0.8       |

---

## ESP32 Bridge Entegrasyonu

### send_authorization()

Authorization komutu gönderme retry logic'i:

```python
def send_authorization(
    self,
    wait_for_ack: bool = True,
    timeout: float = 1.0,
    max_retries: int = 1
) -> bool:
    # Exponential backoff retry
    # Delay: 0.1s, 0.2s, 0.4s, ...
```

### send_current_set()

Current set komutu gönderme retry logic'i:

```python
def send_current_set(
    self,
    amperage: int,
    wait_for_ack: bool = True,
    timeout: float = 1.0,
    max_retries: int = 1
) -> bool:
    # Exponential backoff retry
    # Delay: 0.1s, 0.2s, 0.4s, ...
```

---

## Varsayılan Retry Konfigürasyonları

### DEFAULT_RETRY_CONFIG

```python
RetryConfig(
    max_retries=3,
    initial_delay=0.1,
    max_delay=5.0,
    strategy=RetryStrategy.EXPONENTIAL,
    multiplier=2.0,
)
```

### QUICK_RETRY_CONFIG

```python
RetryConfig(
    max_retries=2,
    initial_delay=0.05,
    max_delay=1.0,
    strategy=RetryStrategy.EXPONENTIAL,
    multiplier=2.0,
)
```

### SLOW_RETRY_CONFIG

```python
RetryConfig(
    max_retries=5,
    initial_delay=0.5,
    max_delay=10.0,
    strategy=RetryStrategy.EXPONENTIAL,
    multiplier=2.0,
)
```

---

## Kullanım Örnekleri

### Decorator Kullanımı

```python
from esp32.retry import retry_with_backoff, RetryConfig, RetryStrategy

@retry_with_backoff(
    config=RetryConfig(
        max_retries=3,
        initial_delay=0.1,
        strategy=RetryStrategy.EXPONENTIAL,
    )
)
def my_function():
    # Function implementation
    pass
```

### Fonksiyon Kullanımı

```python
from esp32.retry import retry_function, RetryConfig

def my_function():
    # Function implementation
    pass

result = retry_function(
    lambda: my_function(),
    config=RetryConfig(max_retries=3)
)
```

### Callback Kullanımı

```python
def on_retry(attempt, exception):
    print(f"Retry attempt {attempt}: {exception}")

@retry_with_backoff(
    config=RetryConfig(max_retries=3),
    on_retry=on_retry
)
def my_function():
    pass
```

---

## İyileştirmeler

### Öncesi

- Sabit 0.1s gecikme
- Basit retry mekanizması
- Farklı stratejiler yok

### Sonrası

- Exponential backoff retry
- Farklı retry stratejileri (LINEAR, EXPONENTIAL, FIBONACCI)
- Yapılandırılabilir retry konfigürasyonları
- Merkezi retry modülü
- Daha iyi hata yönetimi

---

## Test Senaryoları

### Senaryo 1: Başarılı İlk Deneme

```
Attempt 0: Success ✅
No retry needed
```

### Senaryo 2: İkinci Denemede Başarılı

```
Attempt 0: Failed ❌
Delay: 0.1s
Attempt 1: Success ✅
Total time: ~0.1s
```

### Senaryo 3: Üçüncü Denemede Başarılı

```
Attempt 0: Failed ❌
Delay: 0.1s
Attempt 1: Failed ❌
Delay: 0.2s
Attempt 2: Success ✅
Total time: ~0.3s
```

### Senaryo 4: Tüm Denemeler Başarısız

```
Attempt 0: Failed ❌
Delay: 0.1s
Attempt 1: Failed ❌
Delay: 0.2s
Attempt 2: Failed ❌
Delay: 0.4s
Attempt 3: Failed ❌
Exception raised
Total time: ~0.7s
```

---

## Sorun Giderme

### Retry Çalışmıyor

1. Retry modülü import edilebiliyor mu kontrol edin:
   ```python
   from esp32.retry import RetryConfig
   ```

2. Retry config doğru mu kontrol edin:
   ```python
   config = RetryConfig(max_retries=3)
   print(config.max_retries)  # 3 olmalı
   ```

### Gecikme Çok Uzun

1. `max_delay` parametresini azaltın
2. `initial_delay` parametresini azaltın
3. `multiplier` parametresini azaltın

### Gecikme Çok Kısa

1. `max_delay` parametresini artırın
2. `initial_delay` parametresini artırın
3. `multiplier` parametresini artırın

---

## Referanslar

- [Exponential Backoff](https://en.wikipedia.org/wiki/Exponential_backoff)
- [Retry Pattern](https://docs.microsoft.com/en-us/azure/architecture/patterns/retry)

---

**Son Güncelleme:** 2025-12-10 18:30:00

