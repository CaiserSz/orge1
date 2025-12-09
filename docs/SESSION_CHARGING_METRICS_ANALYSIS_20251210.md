# Session Charging Metrics Analizi ve İyileştirme Planı

**Oluşturulma Tarihi:** 2025-12-10 06:30:00  
**Son Güncelleme:** 2025-12-10 06:30:00  
**Version:** 1.0.0  
**Analiz Kapsamı:** Şarj metrikleri, enerji takibi, güç analizi

---

## 📊 Executive Summary

**Mevcut Durum:** 🔴 Eksik - Kritik Metrikler Yok  
**Gerekli Metrikler:** 🟡 Kısmen Mevcut  
**Database Şeması:** 🔴 Metrikler İçin Hazır Değil  
**Hesaplama Mantığı:** 🔴 Yok  

**Genel Skor:** 3.0/10

---

## 🔍 Mevcut Durum Analizi

### Mevcut Database Şeması

```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    start_time TEXT NOT NULL,
    end_time TEXT,
    start_state INTEGER NOT NULL,
    end_state INTEGER,
    status TEXT NOT NULL,
    events TEXT NOT NULL,
    metadata TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
```

**Eksik Metrikler:**
- ❌ Süre (duration_seconds) - Runtime'da hesaplanıyor, saklanmıyor
- ❌ Tüketilen enerji (total_energy_kwh)
- ❌ Maksimum güç (max_power_kw)
- ❌ Ortalama güç (avg_power_kw)
- ❌ Minimum güç (min_power_kw)
- ❌ Maksimum akım (max_current_a)
- ❌ Ortalama akım (avg_current_a)
- ❌ Minimum akım (min_current_a)
- ❌ Başlangıç enerji (start_energy_kwh)
- ❌ Bitiş enerji (end_energy_kwh)

### ESP32 Status Mesajı Analizi

**Mevcut Status Formatı:**
```
<STAT;ID=X;CP=X;CPV=X;PP=X;PPV=X;RL=X;LOCK=X;MOTOR=X;PWM=X;MAX=X;CABLE=X;AUTH=X;STATE=X;PB=X;STOP=X;>
```

**Mevcut Bilgiler:**
- ✅ `STATE` - Charging state (0-8)
- ✅ `MAX` - Maximum current (A)
- ✅ `CURRENT` - Current current (A) - Event'lerde mevcut
- ✅ `CPV` - Charging Point Voltage (V) - Muhtemelen mevcut
- ✅ `PPV` - Pilot Point Voltage (V) - Muhtemelen mevcut

**Eksik Bilgiler:**
- ❌ Enerji (kWh) - Meter entegrasyonu yok
- ❌ Güç (kW) - Hesaplanabilir ama hesaplanmıyor
- ❌ Toplam enerji tüketimi

---

## 🎯 Gerekli Şarj Metrikleri

### 1. Temel Metrikler (Zorunlu)

#### Süre Metrikleri
- **duration_seconds** (INTEGER) - Toplam şarj süresi (saniye)
- **charging_duration_seconds** (INTEGER) - Aktif şarj süresi (saniye)
- **idle_duration_seconds** (INTEGER) - Bekleme süresi (saniye)

#### Enerji Metrikleri
- **total_energy_kwh** (REAL) - Toplam tüketilen enerji (kWh)
- **start_energy_kwh** (REAL) - Başlangıç enerji seviyesi (kWh) - Meter'den
- **end_energy_kwh** (REAL) - Bitiş enerji seviyesi (kWh) - Meter'den

#### Güç Metrikleri
- **max_power_kw** (REAL) - Maksimum güç (kW)
- **avg_power_kw** (REAL) - Ortalama güç (kW)
- **min_power_kw** (REAL) - Minimum güç (kW)

#### Akım Metrikleri
- **max_current_a** (REAL) - Maksimum akım (A)
- **avg_current_a** (REAL) - Ortalama akım (A)
- **min_current_a** (REAL) - Minimum akım (A)
- **set_current_a** (REAL) - Ayarlanan maksimum akım (A)

#### Voltaj Metrikleri
- **max_voltage_v** (REAL) - Maksimum voltaj (V)
- **avg_voltage_v** (REAL) - Ortalama voltaj (V)
- **min_voltage_v** (REAL) - Minimum voltaj (V)

### 2. İleri Seviye Metrikler (Gelecek)

#### Verimlilik Metrikleri
- **efficiency_percent** (REAL) - Şarj verimliliği (%)
- **energy_loss_kwh** (REAL) - Enerji kaybı (kWh)

#### Trend Metrikleri
- **power_trend** (TEXT) - Güç trendi ('increasing', 'decreasing', 'stable')
- **temperature_max_c** (REAL) - Maksimum sıcaklık (°C)
- **temperature_avg_c** (REAL) - Ortalama sıcaklık (°C)

---

## 📋 Önerilen Database Şeması (Güncellenmiş)

### Sessions Tablosu (Güncellenmiş)

```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    start_time INTEGER NOT NULL,              -- Unix timestamp
    end_time INTEGER,                          -- Unix timestamp
    start_state INTEGER NOT NULL CHECK(start_state >= 0 AND start_state <= 8),
    end_state INTEGER CHECK(end_state IS NULL OR (end_state >= 0 AND end_state <= 8)),
    status TEXT NOT NULL CHECK(status IN ('ACTIVE', 'COMPLETED', 'CANCELLED', 'FAULTED')),
    
    -- Süre metrikleri
    duration_seconds INTEGER CHECK(duration_seconds IS NULL OR duration_seconds >= 0),
    charging_duration_seconds INTEGER CHECK(charging_duration_seconds IS NULL OR charging_duration_seconds >= 0),
    idle_duration_seconds INTEGER CHECK(idle_duration_seconds IS NULL OR idle_duration_seconds >= 0),
    
    -- Enerji metrikleri
    total_energy_kwh REAL CHECK(total_energy_kwh IS NULL OR total_energy_kwh >= 0),
    start_energy_kwh REAL CHECK(start_energy_kwh IS NULL OR start_energy_kwh >= 0),
    end_energy_kwh REAL CHECK(end_energy_kwh IS NULL OR end_energy_kwh >= 0),
    
    -- Güç metrikleri
    max_power_kw REAL CHECK(max_power_kw IS NULL OR max_power_kw >= 0),
    avg_power_kw REAL CHECK(avg_power_kw IS NULL OR avg_power_kw >= 0),
    min_power_kw REAL CHECK(min_power_kw IS NULL OR min_power_kw >= 0),
    
    -- Akım metrikleri
    max_current_a REAL CHECK(max_current_a IS NULL OR max_current_a >= 0),
    avg_current_a REAL CHECK(avg_current_a IS NULL OR avg_current_a >= 0),
    min_current_a REAL CHECK(min_current_a IS NULL OR min_current_a >= 0),
    set_current_a REAL CHECK(set_current_a IS NULL OR set_current_a >= 0),
    
    -- Voltaj metrikleri
    max_voltage_v REAL CHECK(max_voltage_v IS NULL OR max_voltage_v >= 0),
    avg_voltage_v REAL CHECK(avg_voltage_v IS NULL OR avg_voltage_v >= 0),
    min_voltage_v REAL CHECK(min_voltage_v IS NULL OR min_voltage_v >= 0),
    
    -- Event ve metadata
    event_count INTEGER DEFAULT 0 CHECK(event_count >= 0),
    events TEXT NOT NULL DEFAULT '[]',         -- JSON (backward compatibility)
    metadata TEXT NOT NULL DEFAULT '{}',      -- JSON
    
    -- Audit fields
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
)
```

### Session Events Tablosu (Güncellenmiş)

```sql
CREATE TABLE session_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_timestamp INTEGER NOT NULL,
    from_state INTEGER,
    to_state INTEGER,
    from_state_name TEXT,
    to_state_name TEXT,
    
    -- Metrikler (her event'te)
    current_a REAL,                            -- Akım (A)
    voltage_v REAL,                            -- Voltaj (V)
    power_kw REAL,                             -- Güç (kW) - calculated
    energy_kwh REAL,                           -- Enerji (kWh) - cumulative
    
    -- Status bilgileri
    status_data TEXT,                          -- JSON (full status)
    
    -- Additional data
    event_data TEXT,                           -- JSON (additional data)
    created_at INTEGER NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
)
```

---

## 🔧 Hesaplama Mantığı

### Güç Hesaplama

```python
def calculate_power(current_a: float, voltage_v: float) -> float:
    """
    Güç hesaplama: P = V × I
    
    Args:
        current_a: Akım (Amper)
        voltage_v: Voltaj (Volt)
    
    Returns:
        Güç (kW)
    """
    if current_a is None or voltage_v is None:
        return None
    
    power_w = current_a * voltage_v  # Watt
    power_kw = power_w / 1000.0      # Kilowatt
    return round(power_kw, 3)
```

### Enerji Hesaplama

```python
def calculate_energy(power_kw: float, duration_hours: float) -> float:
    """
    Enerji hesaplama: E = P × t
    
    Args:
        power_kw: Güç (kW)
        duration_hours: Süre (saat)
    
    Returns:
        Enerji (kWh)
    """
    if power_kw is None or duration_hours is None:
        return None
    
    energy_kwh = power_kw * duration_hours
    return round(energy_kwh, 3)
```

### Metriklerin Güncellenmesi

```python
class SessionMetricsCalculator:
    """Session metriklerini hesaplayan sınıf"""
    
    def __init__(self, session: ChargingSession):
        self.session = session
        self.currents = []
        self.voltages = []
        self.powers = []
        self.start_time = None
        self.charging_start_time = None
    
    def add_event(self, event: Dict[str, Any]):
        """Event ekle ve metrikleri güncelle"""
        status = event.get('status', {})
        current_a = status.get('CURRENT')
        voltage_v = status.get('CPV') or status.get('PPV')
        
        if current_a is not None:
            self.currents.append(current_a)
        
        if voltage_v is not None:
            self.voltages.append(voltage_v)
        
        if current_a is not None and voltage_v is not None:
            power_kw = calculate_power(current_a, voltage_v)
            self.powers.append(power_kw)
        
        # Charging state kontrolü
        if event.get('to_state') == ESP32State.CHARGING.value:
            self.charging_start_time = datetime.now()
    
    def calculate_metrics(self) -> Dict[str, Any]:
        """Tüm metrikleri hesapla"""
        metrics = {}
        
        # Süre metrikleri
        if self.session.end_time:
            duration = (self.session.end_time - self.session.start_time).total_seconds()
            metrics['duration_seconds'] = int(duration)
            
            if self.charging_start_time:
                charging_duration = (self.session.end_time - self.charging_start_time).total_seconds()
                metrics['charging_duration_seconds'] = int(charging_duration)
                metrics['idle_duration_seconds'] = int(duration - charging_duration)
        
        # Akım metrikleri
        if self.currents:
            metrics['max_current_a'] = max(self.currents)
            metrics['avg_current_a'] = sum(self.currents) / len(self.currents)
            metrics['min_current_a'] = min(self.currents)
        
        # Voltaj metrikleri
        if self.voltages:
            metrics['max_voltage_v'] = max(self.voltages)
            metrics['avg_voltage_v'] = sum(self.voltages) / len(self.voltages)
            metrics['min_voltage_v'] = min(self.voltages)
        
        # Güç metrikleri
        if self.powers:
            metrics['max_power_kw'] = max(self.powers)
            metrics['avg_power_kw'] = sum(self.powers) / len(self.powers)
            metrics['min_power_kw'] = min(self.powers)
        
        # Enerji hesaplama (güç × süre)
        if metrics.get('avg_power_kw') and metrics.get('charging_duration_seconds'):
            duration_hours = metrics['charging_duration_seconds'] / 3600.0
            metrics['total_energy_kwh'] = calculate_energy(
                metrics['avg_power_kw'], 
                duration_hours
            )
        
        return metrics
```

---

## 📊 Real-time Metrik Takibi

### Session Sırasında Metrik Güncelleme

```python
class SessionManager:
    def _on_event(self, event_type: EventType, event_data: Dict[str, Any]):
        """Event geldiğinde metrikleri güncelle"""
        if self.current_session:
            # Event ekle
            self.current_session.add_event(event_type, event_data)
            
            # Metrikleri güncelle
            self._update_session_metrics(event_data)
            
            # Database'e kaydet
            self.db.update_session(
                session_id=self.current_session.session_id,
                events=self.current_session.events,
                metrics=self.current_session.metrics  # Yeni alan
            )
    
    def _update_session_metrics(self, event_data: Dict[str, Any]):
        """Session metriklerini güncelle"""
        status = event_data.get('status', {})
        current_a = status.get('CURRENT')
        voltage_v = status.get('CPV') or status.get('PPV')
        
        if current_a is not None:
            # Maksimum akım güncelle
            if self.current_session.metrics.get('max_current_a', 0) < current_a:
                self.current_session.metrics['max_current_a'] = current_a
            
            # Minimum akım güncelle
            if self.current_session.metrics.get('min_current_a') is None:
                self.current_session.metrics['min_current_a'] = current_a
            elif self.current_session.metrics['min_current_a'] > current_a:
                self.current_session.metrics['min_current_a'] = current_a
        
        if voltage_v is not None:
            # Voltaj metrikleri güncelle
            if self.current_session.metrics.get('max_voltage_v', 0) < voltage_v:
                self.current_session.metrics['max_voltage_v'] = voltage_v
        
        # Güç hesapla ve güncelle
        if current_a is not None and voltage_v is not None:
            power_kw = calculate_power(current_a, voltage_v)
            if self.current_session.metrics.get('max_power_kw', 0) < power_kw:
                self.current_session.metrics['max_power_kw'] = power_kw
```

### Session Sonunda Final Metrikler

```python
def _end_session_internal(self, session, end_time, end_state, status):
    """Session sonlandırıldığında final metrikleri hesapla"""
    # Metrikleri hesapla
    calculator = SessionMetricsCalculator(session)
    for event in session.events:
        calculator.add_event(event)
    
    final_metrics = calculator.calculate_metrics()
    
    # Session'a ekle
    session.metrics.update(final_metrics)
    
    # Database'e kaydet
    self.db.update_session(
        session_id=session.session_id,
        end_time=end_time,
        end_state=end_state,
        status=status.value,
        **final_metrics  # Tüm metrikleri kaydet
    )
```

---

## 🎯 Implementation Plan

### Faz 1: Database Şema Güncellemesi (Öncelik 0)

1. **Database migration script**
   - Yeni kolonları ekle
   - Mevcut verileri migrate et
   - **Tahmini Süre:** 2-3 saat

2. **ChargingSession sınıfı güncelleme**
   - `metrics` dict'i ekle
   - Metrik hesaplama metodları ekle
   - **Tahmini Süre:** 1-2 saat

### Faz 2: Metrik Hesaplama Mantığı (Öncelik 1)

3. **SessionMetricsCalculator sınıfı**
   - Metrik hesaplama mantığı
   - Real-time güncelleme
   - **Tahmini Süre:** 2-3 saat

4. **SessionManager güncelleme**
   - Event'lerden metrik çıkarma
   - Real-time metrik güncelleme
   - Final metrik hesaplama
   - **Tahmini Süre:** 2-3 saat

### Faz 3: API Endpoint'leri (Öncelik 2)

5. **Metrics endpoint'leri**
   - `/api/sessions/{session_id}/metrics` - Session metrikleri
   - `/api/sessions/stats/energy` - Enerji istatistikleri
   - `/api/sessions/stats/power` - Güç istatistikleri
   - **Tahmini Süre:** 1-2 saat

### Faz 4: Meter Entegrasyonu (Gelecek)

6. **Energy meter entegrasyonu**
   - Meter'den enerji okuma
   - Başlangıç/bitiş enerji seviyeleri
   - **Tahmini Süre:** 2-3 gün

---

## 📋 Öncelikli Aksiyon Planı

### Acil (Öncelik 0-1)

1. **Database Şema Güncellemesi**
   - Metrik kolonlarını ekle
   - Migration script yaz
   - **Tahmini Süre:** 2-3 saat
   - **Etki:** Yüksek (metriklerin saklanması)

2. **Metrik Hesaplama Mantığı**
   - SessionMetricsCalculator sınıfı
   - Real-time güncelleme
   - **Tahmini Süre:** 2-3 saat
   - **Etki:** Yüksek (metriklerin hesaplanması)

### Yüksek Öncelik (Öncelik 2-3)

3. **SessionManager Metrik Entegrasyonu**
   - Event'lerden metrik çıkarma
   - Database'e kaydetme
   - **Tahmini Süre:** 2-3 saat
   - **Etki:** Yüksek (metriklerin kullanılması)

4. **API Endpoint'leri**
   - Metrics endpoint'leri
   - Statistics endpoint'leri
   - **Tahmini Süre:** 1-2 saat
   - **Etki:** Orta (API kullanımı)

---

## 🔍 Eksik Bilgiler ve Çözümler

### Enerji Bilgisi (kWh)

**Sorun:**
- ESP32'den enerji bilgisi gelmiyor
- Meter entegrasyonu yok

**Çözüm Seçenekleri:**

**Seçenek 1: Hesaplanmış Enerji (Geçici)**
```python
# Güç × süre ile hesapla
energy_kwh = avg_power_kw * (duration_hours)
```

**Seçenek 2: Meter Entegrasyonu (Gelecek)**
- Modbus meter entegrasyonu
- Başlangıç/bitiş enerji okuma
- Gerçek enerji tüketimi

**Seçenek 3: Hybrid Yaklaşım**
- Meter varsa meter'den oku
- Meter yoksa hesapla

### Voltaj Bilgisi

**Sorun:**
- CPV ve PPV bilgileri status'te var mı kontrol edilmeli
- Event'lerde voltaj bilgisi saklanmıyor

**Çözüm:**
- Status mesajından voltaj bilgisini çıkar
- Event'lere voltaj bilgisini ekle
- Metrik hesaplamalarında kullan

---

## 📊 Örnek Kullanım Senaryoları

### Senaryo 1: Session Sırasında Metrik Takibi

```python
# Session başladı
session = start_session(event_data)

# Her event'te metrikler güncelleniyor
on_event(CHARGE_STARTED, {'status': {'CURRENT': 16, 'CPV': 230}})
# → max_current_a = 16, max_voltage_v = 230, max_power_kw = 3.68

on_event(STATE_CHANGED, {'status': {'CURRENT': 20, 'CPV': 230}})
# → max_current_a = 20, max_power_kw = 4.60

# Session bitti
end_session()
# → Final metrikler hesaplanıyor ve kaydediliyor
```

### Senaryo 2: Session Sonrası Analiz

```python
# Session metriklerini al
session = get_session(session_id)

print(f"Süre: {session['duration_seconds']} saniye")
print(f"Tüketilen Enerji: {session['total_energy_kwh']} kWh")
print(f"Maksimum Güç: {session['max_power_kw']} kW")
print(f"Ortalama Güç: {session['avg_power_kw']} kW")
print(f"Maksimum Akım: {session['max_current_a']} A")
```

---

## 🎯 Sonuç ve Öneriler

### Kritik Eksiklikler

1. 🔴 **Database şemasında metrikler yok**
2. 🔴 **Metrik hesaplama mantığı yok**
3. 🔴 **Real-time metrik güncelleme yok**
4. 🔴 **Enerji bilgisi yok** (meter entegrasyonu gerekli)

### Önerilen Yaklaşım

**Faz 1: Temel Metrikler (1-2 gün)**
- Database şema güncellemesi
- Temel metrik hesaplama (süre, akım, güç)
- Real-time güncelleme

**Faz 2: İleri Metrikler (1-2 gün)**
- Enerji hesaplama (güç × süre)
- API endpoint'leri
- Statistics

**Faz 3: Meter Entegrasyonu (Gelecek)**
- Modbus meter entegrasyonu
- Gerçek enerji okuma
- Doğru enerji takibi

---

**Son Güncelleme:** 2025-12-10 06:30:00

