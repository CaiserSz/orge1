# Test Dokümantasyonu

**Oluşturulma Tarihi:** 2025-12-10 10:55:00
**Son Güncelleme:** 2025-12-10 10:55:00
**Versiyon:** 1.0.0

## İçindekiler

1. [Genel Bakış](#genel-bakış)
2. [Test Yapısı](#test-yapısı)
3. [Test Standartları](#test-standartları)
4. [Mock Yapısı](#mock-yapısı)
5. [Test Senaryoları](#test-senaryoları)
6. [Test Çalıştırma](#test-çalıştırma)
7. [Test Coverage](#test-coverage)

## Genel Bakış

Bu dokümantasyon, Charger API projesinin test stratejisi, standartları ve senaryolarını açıklar.

### Test Kategorileri

1. **Unit Tests:** Tekil fonksiyon ve sınıf testleri
2. **Integration Tests:** Bileşenler arası entegrasyon testleri
3. **API Tests:** Endpoint testleri
4. **Edge Case Tests:** Sınır durumları ve hata senaryoları

## Test Yapısı

### Dosya Organizasyonu

```
tests/
├── conftest.py                    # Standart pytest fixture'ları
├── api/
│   ├── test_edge_cases.py          # API edge case testleri
│   ├── test_input_validation.py    # Input validation testleri
│   └── test_integration_scenarios.py # Integration senaryoları
├── esp32/
│   └── test_bridge_*.py            # ESP32 bridge testleri
├── event_detector/
│   └── test_*.py                   # Event detector testleri
└── test_*.py                       # Ana test dosyaları
```

### Test Dosyası İsimlendirme

- **Format:** `test_<modül>_<kategori>.py`
- **Örnekler:**
  - `test_api_endpoints.py` - API endpoint testleri
  - `test_api_edge_cases.py` - API edge case testleri
  - `test_integration_scenarios.py` - Integration senaryoları

## Test Standartları

### State Değerleri Standardizasyonu

**KRİTİK:** Tüm test dosyalarında ESP32State enum kullanılmalıdır.

#### ✅ Doğru Kullanım

```python
from api.event_detector import ESP32State

mock_bridge.get_status.return_value = {
    "STATE": ESP32State.EV_CONNECTED.value,
    "AUTH": 0,
    "CABLE": 0,
}
```

#### ❌ Yanlış Kullanım

```python
# Hardcoded state değerleri kullanılmamalı
mock_bridge.get_status.return_value = {
    "STATE": 3,  # ❌ ESP32State enum kullanılmalı
}
```

### Mock Yapısı Standardizasyonu

**KRİTİK:** Tüm test dosyalarında `conftest.py`'deki standart fixture'lar kullanılmalıdır.

#### Standart Fixture'lar

- `mock_esp32_bridge`: Standart ESP32 bridge mock'u
- `client`: Standart FastAPI test client
- `test_headers`: Standart test headers (API key içerir)
- `mock_status_*`: Farklı state'ler için mock status fixture'ları

#### ✅ Doğru Kullanım

```python
def test_example(client, mock_esp32_bridge, test_headers):
    """Test örneği"""
    response = client.post(
        "/api/charge/start",
        json={},
        headers=test_headers
    )
    assert response.status_code == 200
```

#### ❌ Yanlış Kullanım

```python
# Her test dosyasında ayrı mock bridge oluşturulmamalı
@pytest.fixture
def mock_bridge():
    # ❌ conftest.py'deki fixture kullanılmalı
    return Mock()
```

## Mock Yapısı

### conftest.py

`tests/conftest.py` dosyası tüm test dosyaları için standart fixture'ları sağlar.

#### mock_esp32_bridge Fixture

```python
@pytest.fixture
def mock_esp32_bridge():
    """
    Standart ESP32 bridge mock fixture

    Tüm test dosyalarında kullanılacak standart mock bridge.
    """
    mock_bridge = Mock(spec=ESP32Bridge)
    mock_bridge.is_connected = True
    mock_bridge.get_status = Mock(return_value={...})
    mock_bridge.get_status_sync = Mock(side_effect=mock_get_status_sync)
    mock_bridge.send_authorization = Mock(return_value=True)
    mock_bridge.send_charge_stop = Mock(return_value=True)
    mock_bridge.send_current_set = Mock(return_value=True)
    return mock_bridge
```

#### client Fixture

```python
@pytest.fixture
def client(mock_esp32_bridge):
    """
    Standart FastAPI test client fixture

    Mock bridge otomatik olarak inject edilir.
    """
    os.environ["SECRET_API_KEY"] = "test-api-key"
    with patch("api.routers.dependencies.get_bridge", return_value=mock_esp32_bridge):
        with patch("esp32.bridge.get_esp32_bridge", return_value=mock_esp32_bridge):
            yield TestClient(app)
```

### Mock Status Fixture'ları

Farklı state'ler için hazır mock status fixture'ları:

- `mock_status_idle`: IDLE state mock status
- `mock_status_cable_detect`: CABLE_DETECT state mock status
- `mock_status_ev_connected`: EV_CONNECTED state mock status
- `mock_status_ready`: READY state mock status
- `mock_status_charging`: CHARGING state mock status
- `mock_status_fault`: FAULT_HARD state mock status

## Test Senaryoları

### API Endpoint Testleri

#### Health Check

```python
def test_health_check(client):
    """Health check endpoint çalışıyor mu?"""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["success"] is True
```

#### Status Endpoint

```python
def test_status_endpoint(client, mock_esp32_bridge):
    """Status endpoint çalışıyor mu?"""
    response = client.get("/api/status")
    assert response.status_code == 200
    assert "STATE" in response.json()["data"]
```

#### Charge Start/Stop

```python
def test_start_charge(client, mock_esp32_bridge, test_headers):
    """Şarj başlatma endpoint'i"""
    # EV_CONNECTED state'e ayarla
    mock_esp32_bridge.get_status.return_value = {
        "STATE": ESP32State.EV_CONNECTED.value,
    }

    response = client.post(
        "/api/charge/start",
        json={},
        headers=test_headers
    )
    assert response.status_code == 200
```

#### Current Set

```python
def test_set_current(client, mock_esp32_bridge, test_headers):
    """Akım ayarlama endpoint'i"""
    mock_esp32_bridge.get_status.return_value = {
        "STATE": ESP32State.IDLE.value,
    }

    response = client.post(
        "/api/maxcurrent",
        json={"amperage": 16},
        headers=test_headers
    )
    assert response.status_code == 200
```

### Integration Test Senaryoları

#### Tam Şarj Akışı

```python
def test_full_charge_flow(client, mock_esp32_bridge, test_headers):
    """
    Tam şarj akışı testi:
    1. IDLE -> CABLE_DETECT
    2. CABLE_DETECT -> EV_CONNECTED
    3. EV_CONNECTED -> READY (authorization)
    4. READY -> CHARGING
    5. CHARGING -> STOPPED
    """
    # State geçişlerini test et
    ...
```

#### Hata Kurtarma Senaryoları

```python
def test_bridge_disconnected_recovery(client, mock_esp32_bridge):
    """Bridge bağlantısı kesildiğinde hata döndürülmeli"""
    mock_esp32_bridge.is_connected = False

    response = client.get("/api/health")
    assert response.json()["data"]["esp32_connected"] is False
```

### Edge Case Testleri

#### Geçersiz State Geçişleri

```python
def test_invalid_state_transition(client, mock_esp32_bridge, test_headers):
    """Geçersiz state geçişi reddedilmeli"""
    # IDLE durumunda şarj başlatılamaz
    mock_esp32_bridge.get_status.return_value = {
        "STATE": ESP32State.IDLE.value,
    }

    response = client.post(
        "/api/charge/start",
        json={},
        headers=test_headers
    )
    assert response.status_code == 400
```

#### Şarj Esnasında Akım Değiştirme

```python
def test_current_set_during_charge_fails(client, mock_esp32_bridge, test_headers):
    """Şarj esnasında akım değiştirme denemesi reddedilmeli"""
    mock_esp32_bridge.get_status.return_value = {
        "STATE": ESP32State.CHARGING.value,
    }

    response = client.post(
        "/api/maxcurrent",
        json={"amperage": 20},
        headers=test_headers
    )
    assert response.status_code == 400
```

## Test Çalıştırma

### Tüm Testleri Çalıştırma

```bash
cd /home/basar/charger
/home/basar/charger/env/bin/python3 -m pytest tests/ -v
```

### Belirli Test Dosyasını Çalıştırma

```bash
/home/basar/charger/env/bin/python3 -m pytest tests/test_api_endpoints.py -v
```

### Belirli Test Fonksiyonunu Çalıştırma

```bash
/home/basar/charger/env/bin/python3 -m pytest tests/test_api_endpoints.py::TestAPIEndpoints::test_health_check -v
```

### Test Coverage Raporu

```bash
/home/basar/charger/env/bin/python3 -m pytest tests/ --cov=api --cov-report=html
```

## Test Coverage

### Mevcut Coverage

- **API Endpoints:** %85+
- **ESP32 Bridge:** %80+
- **Event Detector:** %75+
- **Session Management:** %70+

### Coverage Hedefleri

- **Genel Coverage:** %80+
- **Kritik Modüller:** %90+
- **API Endpoints:** %95+

## Best Practices

### 1. Test İsimlendirme

- Test fonksiyonları `test_` ile başlamalı
- Açıklayıcı isimler kullanılmalı
- Test kategorisi belirtilmeli

### 2. Test Organizasyonu

- İlgili testler aynı class içinde gruplanmalı
- Her test tek bir senaryoyu test etmeli
- Test'ler birbirinden bağımsız olmalı

### 3. Mock Kullanımı

- Standart fixture'lar kullanılmalı
- Mock'lar test içinde değiştirilebilir olmalı
- Mock'lar gerçek davranışı simüle etmeli

### 4. Assertion'lar

- Açıklayıcı assertion mesajları kullanılmalı
- Her test en az bir assertion içermeli
- Edge case'ler test edilmeli

## Sorun Giderme

### Mock Bridge Inject Edilmiyor

**Sorun:** Mock bridge test içinde çalışmıyor.

**Çözüm:** `conftest.py`'deki `client` fixture'ının doğru patch'leri kullandığından emin olun.

### State Değerleri Çalışmıyor

**Sorun:** State değerleri test içinde çalışmıyor.

**Çözüm:** ESP32State enum kullanıldığından emin olun, hardcoded değerler kullanmayın.

### Test Timeout

**Sorun:** Test timeout veriyor.

**Çözüm:** Mock bridge'in `get_status_sync` fonksiyonunun doğru mock'landığından emin olun.

## Referanslar

- [Pytest Dokümantasyonu](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Mock Dokümantasyonu](https://docs.python.org/3/library/unittest.mock.html)

