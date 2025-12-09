# Meter Entegrasyonu Hazırlık Dokümantasyonu

**Oluşturulma Tarihi:** 2025-12-10 07:00:00
**Son Güncelleme:** 2025-12-10 07:00:00
**Version:** 1.0.0
**Açıklama:** Meter entegrasyonu için hazırlık ve abstraction layer

---

## 📊 Özet

**Durum:** ✅ Hazırlık Tamamlandı
**Meter Durumu:** 🟡 Şu An Yok (Mock Implementation)
**Hazırlık Seviyesi:** ✅ Tam Hazır

Meter entegrasyonu için gerekli altyapı hazırlandı. Meter olmasa bile sistem çalışmaya devam edecek (fallback mekanizması).

---

## 🏗️ Mimari Tasarım

### Abstraction Layer

```
api/meter/
├── __init__.py          # Public API export
├── interface.py         # MeterInterface (ABC) ve MeterReading
├── mock.py             # MockMeter (meter yokken kullanılır)
└── modbus.py           # ModbusMeter (gelecek implementasyon)
```

### Interface Tasarımı

```python
class MeterInterface(ABC):
    """Energy meter interface"""

    def connect() -> bool
    def disconnect() -> bool
    def is_connected() -> bool
    def read_energy() -> Optional[float]      # kWh
    def read_power() -> Optional[float]       # kW
    def read_voltage() -> Optional[float]     # V
    def read_current() -> Optional[float]     # A
    def read_all() -> Optional[MeterReading]  # Tüm değerler
    def reset_energy_counter() -> bool
```

### MeterReading Data Class

```python
@dataclass
class MeterReading:
    timestamp: float           # Unix timestamp
    energy_kwh: float         # Toplam enerji (kWh)
    power_kw: float           # Anlık güç (kW)
    voltage_v: float          # Voltaj (V)
    current_a: float          # Akım (A)
    frequency_hz: Optional[float]  # Frekans (Hz)
    is_valid: bool            # Okuma geçerli mi?
```

---

## 🔧 Implementasyon Detayları

### 1. MockMeter (Mevcut)

**Kullanım:** Meter yokken kullanılır

**Özellikler:**
- Tüm değerler `None` döner (meter yok anlamında)
- Sistem çalışmaya devam eder
- Fallback mekanizması: Hesaplanmış enerji kullanılır

**Kod:**
```python
from api.meter import get_meter

meter = get_meter()  # MockMeter instance döner
energy = meter.read_energy()  # None döner
```

### 2. ModbusMeter (Gelecek)

**Kullanım:** Modbus RTU/TCP meter entegrasyonu için

**Özellikler:**
- Modbus RTU (Serial) desteği
- Modbus TCP (Ethernet) desteği
- Register mapping yapılandırılabilir

**Placeholder Kod:**
```python
from api.meter.modbus import ModbusMeter

meter = ModbusMeter(port="/dev/ttyUSB0", baudrate=9600, slave_id=1)
meter.connect()
energy = meter.read_energy()
```

**TODO:**
- [ ] pymodbus kütüphanesi entegrasyonu
- [ ] Register mapping yapılandırması
- [ ] Error handling
- [ ] Reconnection logic
- [ ] Test suite

---

## 🔌 SessionManager Entegrasyonu

### Session Başlangıcında

```python
# Meter'dan başlangıç enerji seviyesini oku
if self.meter and self.meter.is_connected():
    meter_reading = self.meter.read_all()
    if meter_reading and meter_reading.is_valid:
        session.metadata["start_energy_kwh"] = meter_reading.energy_kwh
        session.metadata["meter_available"] = True
else:
    session.metadata["meter_available"] = False
```

### Session Bitişinde

```python
# Meter'dan bitiş enerji seviyesini oku
if self.meter and self.meter.is_connected():
    meter_reading = self.meter.read_all()
    if meter_reading and meter_reading.is_valid:
        end_energy = meter_reading.energy_kwh
        start_energy = session.metadata.get("start_energy_kwh")

        if start_energy is not None:
            # Gerçek enerji tüketimi = bitiş - başlangıç
            total_energy = end_energy - start_energy
            session.metadata["total_energy_kwh"] = max(0, total_energy)
            session.metadata["energy_source"] = "meter"
else:
    session.metadata["energy_source"] = "calculated"  # Fallback
```

---

## 📊 Fallback Mekanizması

### Enerji Hesaplama Stratejisi

**Öncelik Sırası:**

1. **Meter'dan Okuma** (En Doğru)
   - `energy_source = "meter"`
   - `total_energy_kwh = end_energy_kwh - start_energy_kwh`

2. **Hesaplanmış Enerji** (Fallback)
   - `energy_source = "calculated"`
   - `total_energy_kwh = avg_power_kw × duration_hours`

3. **Bilinmiyor** (Son Çare)
   - `energy_source = "unknown"`
   - `total_energy_kwh = None`

### Kod Örneği

```python
def get_session_energy(session: Dict[str, Any]) -> Optional[float]:
    """Session enerjisini al (meter veya hesaplanmış)"""
    energy_source = session.get("metadata", {}).get("energy_source")

    if energy_source == "meter":
        # Meter'dan okunan gerçek enerji
        return session.get("metadata", {}).get("total_energy_kwh")
    elif energy_source == "calculated":
        # Hesaplanmış enerji
        avg_power = session.get("avg_power_kw")
        duration_hours = session.get("duration_seconds", 0) / 3600.0
        if avg_power and duration_hours:
            return avg_power * duration_hours
    else:
        # Bilinmiyor
        return None
```

---

## 🗄️ Database Şeması Hazırlığı

### Mevcut Şema (Meter Alanları Hazır)

```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    start_time INTEGER NOT NULL,
    end_time INTEGER,
    status TEXT NOT NULL,

    -- Meter bilgileri (metadata içinde saklanıyor, gelecekte kolon olabilir)
    -- start_energy_kwh REAL
    -- end_energy_kwh REAL
    -- total_energy_kwh REAL
    -- energy_source TEXT  -- 'meter', 'calculated', 'unknown'
    -- meter_available BOOLEAN

    metadata TEXT NOT NULL DEFAULT '{}',  -- JSON (meter bilgileri burada)
    ...
)
```

### Gelecek Şema (Meter Kolonları)

```sql
CREATE TABLE sessions (
    ...
    -- Meter bilgileri (normalized kolonlar)
    start_energy_kwh REAL,
    end_energy_kwh REAL,
    total_energy_kwh REAL,
    energy_source TEXT CHECK(energy_source IN ('meter', 'calculated', 'unknown')),
    meter_available BOOLEAN DEFAULT FALSE,
    ...
)
```

---

## 🔄 Meter Entegrasyonu Adımları (Gelecek)

### Adım 1: Meter Seçimi

**Desteklenen Meter Tipleri:**
- Modbus RTU (Serial)
- Modbus TCP (Ethernet)
- MQTT (gelecek)
- HTTP API (gelecek)

### Adım 2: ModbusMeter Implementasyonu

```python
# 1. pymodbus kütüphanesini yükle
pip install pymodbus

# 2. ModbusMeter'ı implement et
from pymodbus.client import ModbusSerialClient

class ModbusMeter(MeterInterface):
    def __init__(self, port, baudrate, slave_id):
        self.client = ModbusSerialClient(port=port, baudrate=baudrate)

    def read_energy(self):
        result = self.client.read_holding_registers(0x0000, 2, unit=self.slave_id)
        return decode_float32(result.registers)
```

### Adım 3: Yapılandırma

```python
# config.yaml veya environment variables
METER_TYPE = "modbus"  # veya "mock"
METER_PORT = "/dev/ttyUSB0"
METER_BAUDRATE = 9600
METER_SLAVE_ID = 1
```

### Adım 4: SessionManager'da Kullanım

```python
# Meter tipine göre instance oluştur
if config.METER_TYPE == "modbus":
    from api.meter.modbus import ModbusMeter
    meter = ModbusMeter(port=config.METER_PORT, ...)
elif config.METER_TYPE == "mock":
    from api.meter.mock import MockMeter
    meter = MockMeter()
```

---

## 📋 Test Senaryoları

### Senaryo 1: Meter Yok

```python
# MockMeter kullanılır
meter = get_meter()  # MockMeter
assert meter.read_energy() is None
assert session.metadata["meter_available"] == False
assert session.metadata["energy_source"] == "calculated"
```

### Senaryo 2: Meter Var (Başarılı)

```python
# ModbusMeter kullanılır
meter = ModbusMeter(...)
meter.connect()
assert meter.is_connected() == True
energy = meter.read_energy()
assert energy is not None
assert session.metadata["meter_available"] == True
assert session.metadata["energy_source"] == "meter"
```

### Senaryo 3: Meter Var (Bağlantı Hatası)

```python
# Meter bağlantı hatası
meter = ModbusMeter(...)
meter.connect()  # False döner
assert meter.is_connected() == False
assert session.metadata["meter_available"] == False
assert session.metadata["energy_source"] == "calculated"  # Fallback
```

---

## 🎯 Sonuç ve Öneriler

### Hazırlık Durumu

✅ **Tamamlandı:**
- Meter interface (MeterInterface)
- Mock implementation (MockMeter)
- Modbus placeholder (ModbusMeter)
- SessionManager entegrasyonu
- Fallback mekanizması

🟡 **Gelecek:**
- ModbusMeter implementasyonu
- Meter yapılandırması
- Test suite
- Error handling iyileştirmeleri

### Avantajlar

1. **Esneklik:** Meter tipi değişse bile interface aynı kalır
2. **Fallback:** Meter yokken sistem çalışmaya devam eder
3. **Test Edilebilirlik:** Mock meter ile test yapılabilir
4. **Genişletilebilirlik:** Yeni meter tipleri kolayca eklenebilir

### Kullanım Örneği

```python
# Meter kullanımı (otomatik fallback)
from api.meter import get_meter

meter = get_meter()  # MockMeter veya ModbusMeter

if meter.is_connected():
    reading = meter.read_all()
    if reading and reading.is_valid:
        energy_kwh = reading.energy_kwh
        power_kw = reading.power_kw
else:
    # Meter yok, hesaplanmış değerler kullan
    pass
```

---

**Son Güncelleme:** 2025-12-10 07:00:00

