# Database Deep Dive Analizi - Session Management

**Oluşturulma Tarihi:** 2025-12-10 06:00:00
**Son Güncelleme:** 2025-12-10 06:00:00
**Version:** 1.0.0
**Analiz Kapsamı:** Database şeması, normalizasyon, query patterns, scalability

---

## 📊 Executive Summary

**Genel Durum:** 🟡 Yetersiz - İyileştirme Gerekli
**Database Şeması:** 🔴 Kritik Sorunlar Var
**Normalizasyon:** 🔴 Denormalized (JSON blobs)
**Query Performance:** 🟡 İyileştirme Gerekli
**Scalability:** 🔴 Büyük Ölçekte Sorunlu
**Data Integrity:** 🟡 Check Constraints Yok

**Genel Skor:** 5.5/10

---

## 🔍 Mevcut Database Şeması Analizi

### Mevcut Şema

```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    start_time TEXT NOT NULL,              -- ISO format string
    end_time TEXT,                         -- ISO format string (NULL if active)
    start_state INTEGER NOT NULL,
    end_state INTEGER,
    status TEXT NOT NULL,
    events TEXT NOT NULL,                   -- JSON array (denormalized)
    metadata TEXT NOT NULL,                 -- JSON object (denormalized)
    created_at TEXT NOT NULL,              -- ISO format string
    updated_at TEXT NOT NULL               -- ISO format string
)
```

### Index'ler

```sql
CREATE INDEX idx_sessions_start_time ON sessions(start_time DESC)
CREATE INDEX idx_sessions_status ON sessions(status)
CREATE INDEX idx_sessions_end_time ON sessions(end_time DESC)
```

---

## 🔴 Kritik Database Sorunları

### 1. Denormalizasyon Sorunları

#### 🔴 Kritik: Events JSON Blob

**Mevcut Durum:**
- Tüm event'ler JSON array olarak `events` TEXT alanında saklanıyor
- Her event ~200 bytes (ortalama)
- 100 event = ~20 KB
- 1000 event = ~200 KB

**Sorunlar:**
- ❌ **Query yapılamıyor:** Event type'a göre filtreleme yapılamaz
- ❌ **Index yapılamıyor:** Event'ler üzerinde index oluşturulamaz
- ❌ **Analytics yapılamıyor:** Event bazlı analiz yapılamaz
- ❌ **Update overhead:** Tek bir event eklemek için tüm events JSON'ı güncelleniyor
- ❌ **Memory overhead:** Tüm event'ler her sorguda parse ediliyor
- ❌ **Scalability sorunu:** Büyük session'larda JSON boyutu çok artıyor

**Örnek Senaryo:**
```python
# 10 saatlik bir session'da ~3600 event olabilir (her 10 saniyede bir event)
# 3600 event × 200 bytes = 720 KB JSON
# Her sorguda 720 KB JSON parse ediliyor!
```

**Çözüm: Normalized Events Table**
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
    event_data TEXT,                       -- JSON (additional data)
    created_at INTEGER NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
)

CREATE INDEX idx_session_events_session_id ON session_events(session_id)
CREATE INDEX idx_session_events_event_type ON session_events(event_type)
CREATE INDEX idx_session_events_timestamp ON session_events(event_timestamp DESC)
CREATE INDEX idx_session_events_session_timestamp ON session_events(session_id, event_timestamp DESC)
```

**Avantajlar:**
- ✅ Event type'a göre filtreleme yapılabilir
- ✅ Event bazlı analytics yapılabilir
- ✅ Index'ler kullanılabilir
- ✅ Incremental update (tek event ekleme)
- ✅ Selective loading (sadece gerekli event'ler)

#### 🔴 Kritik: Metadata JSON Blob

**Mevcut Durum:**
- Metadata JSON object olarak saklanıyor
- İçeriği belirsiz (herhangi bir key-value pair)

**Sorunlar:**
- ❌ **Query yapılamıyor:** Metadata key'lerine göre filtreleme yapılamaz
- ❌ **Schema yok:** Metadata yapısı belirsiz
- ❌ **Index yapılamıyor:** Metadata üzerinde index oluşturulamaz

**Çözüm Seçenekleri:**

**Seçenek 1: Normalized Metadata Table**
```sql
CREATE TABLE session_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    metadata_key TEXT NOT NULL,
    metadata_value TEXT,
    value_type TEXT,                       -- 'string', 'number', 'boolean', 'json'
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
    UNIQUE(session_id, metadata_key)
)

CREATE INDEX idx_session_metadata_session_id ON session_metadata(session_id)
CREATE INDEX idx_session_metadata_key ON session_metadata(metadata_key)
CREATE INDEX idx_session_metadata_session_key ON session_metadata(session_id, metadata_key)
```

**Seçenek 2: Structured Metadata Columns**
```sql
-- Eğer metadata yapısı biliniyorsa, ayrı kolonlar olarak saklanabilir
ALTER TABLE sessions ADD COLUMN energy_kwh REAL;
ALTER TABLE sessions ADD COLUMN max_current INTEGER;
ALTER TABLE sessions ADD COLUMN min_current INTEGER;
-- vb.
```

### 2. Timestamp Sorunları

#### 🔴 Kritik: TEXT Timestamps

**Sorunlar:**
- ❌ String karşılaştırması (yavaş)
- ❌ Tarih aralığı sorguları zor
- ❌ Index kullanımı verimsiz
- ❌ Timezone sorunları
- ❌ Date functions kullanılamıyor

**Çözüm: INTEGER (Unix Timestamp)**
```sql
-- Unix timestamp kullanımı
start_time INTEGER NOT NULL,              -- Unix timestamp
end_time INTEGER,                          -- Unix timestamp
created_at INTEGER NOT NULL,
updated_at INTEGER NOT NULL
```

**Avantajlar:**
- ✅ Hızlı karşılaştırma
- ✅ Tarih aralığı sorguları kolay
- ✅ Index kullanımı verimli
- ✅ Date functions kullanılabilir
- ✅ Timezone conversion kolay

### 3. Eksik Hesaplanmış Alanlar

#### 🟡 Orta: Session Summary Alanları

**Sorun:**
- Session summary için her sorguda hesaplama yapılıyor
- `duration_seconds`, `event_count` gibi alanlar runtime'da hesaplanıyor

**Çözüm: Materialized Columns**
```sql
CREATE TABLE sessions (
    ...
    duration_seconds INTEGER,             -- Hesaplanmış alan
    event_count INTEGER DEFAULT 0,        -- Hesaplanmış alan
    total_energy_kwh REAL,                -- Hesaplanmış alan (gelecek)
    avg_current REAL,                     -- Hesaplanmış alan (gelecek)
    max_current INTEGER,                   -- Hesaplanmış alan (gelecek)
    min_current INTEGER                   -- Hesaplanmış alan (gelecek)
)
```

**Avantajlar:**
- ✅ Sorgu performansı artar
- ✅ Analytics sorguları hızlanır
- ✅ Summary generation hızlanır

### 4. Index Stratejisi Sorunları

#### 🟡 Orta: Eksik Composite Index'ler

**Mevcut Index'ler:**
- `idx_sessions_start_time` - Tek kolon
- `idx_sessions_status` - Tek kolon
- `idx_sessions_end_time` - Tek kolon

**Sorunlar:**
- ❌ Composite index'ler yok
- ❌ Sık kullanılan sorgu kombinasyonları için optimize edilmemiş

**Sık Kullanılan Sorgular:**
```sql
-- Status + start_time kombinasyonu
SELECT * FROM sessions WHERE status = ? ORDER BY start_time DESC

-- Status + end_time kombinasyonu
SELECT * FROM sessions WHERE status = ? AND end_time IS NOT NULL ORDER BY end_time DESC

-- Tarih aralığı sorguları
SELECT * FROM sessions WHERE start_time >= ? AND start_time <= ?
```

**Çözüm: Composite Index'ler**
```sql
CREATE INDEX idx_sessions_status_start_time
ON sessions(status, start_time DESC)

CREATE INDEX idx_sessions_status_end_time
ON sessions(status, end_time DESC)

CREATE INDEX idx_sessions_start_time_range
ON sessions(start_time DESC, end_time DESC)
```

### 5. Veri Bütünlüğü Sorunları

#### 🟡 Orta: Check Constraints Yok

**Sorunlar:**
- ❌ Status değerleri kontrol edilmiyor
- ❌ State değerleri kontrol edilmiyor
- ❌ Data integrity garantisi yok

**Çözüm: Check Constraints**
```sql
CREATE TABLE sessions (
    ...
    status TEXT NOT NULL CHECK(status IN ('ACTIVE', 'COMPLETED', 'CANCELLED', 'FAULTED')),
    start_state INTEGER NOT NULL CHECK(start_state >= 0 AND start_state <= 8),
    end_state INTEGER CHECK(end_state IS NULL OR (end_state >= 0 AND end_state <= 8)),
    duration_seconds INTEGER CHECK(duration_seconds IS NULL OR duration_seconds >= 0),
    event_count INTEGER DEFAULT 0 CHECK(event_count >= 0)
)
```

### 6. Foreign Key Relationships Yok

#### 🟡 Orta: Referential Integrity Yok

**Sorun:**
- `session_events` tablosu oluşturulursa foreign key yok
- Cascade delete yok
- Referential integrity garantisi yok

**Çözüm:**
```sql
-- Foreign key constraints
CREATE TABLE session_events (
    ...
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
)

-- SQLite'de foreign keys aktif et
PRAGMA foreign_keys=ON;
```

### 7. Connection Management Sorunları

#### 🔴 Kritik: Her Operasyonda Yeni Connection

**Sorun:**
- Her database operasyonunda yeni connection açılıyor/kapatılıyor
- Yüksek overhead
- SQLite WAL mode avantajları kullanılmıyor

**Çözüm: Persistent Connection + WAL Mode**
```python
class Database:
    def __init__(self):
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA cache_size=10000")
        self.conn.execute("PRAGMA foreign_keys=ON")

    def _get_connection(self):
        return self.conn  # Aynı connection
```

---

## 📋 Önerilen İyileştirilmiş Database Şeması

### Normalized Schema (Önerilen)

```sql
-- Ana sessions tablosu
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    start_time INTEGER NOT NULL,              -- Unix timestamp
    end_time INTEGER,                          -- Unix timestamp (NULL if active)
    start_state INTEGER NOT NULL CHECK(start_state >= 0 AND start_state <= 8),
    end_state INTEGER CHECK(end_state IS NULL OR (end_state >= 0 AND end_state <= 8)),
    status TEXT NOT NULL CHECK(status IN ('ACTIVE', 'COMPLETED', 'CANCELLED', 'FAULTED')),

    -- Hesaplanmış alanlar (materialized)
    duration_seconds INTEGER CHECK(duration_seconds IS NULL OR duration_seconds >= 0),
    event_count INTEGER DEFAULT 0 CHECK(event_count >= 0),

    -- Gelecek için hazırlık (meter entegrasyonu)
    total_energy_kwh REAL CHECK(total_energy_kwh IS NULL OR total_energy_kwh >= 0),
    avg_current REAL CHECK(avg_current IS NULL OR avg_current >= 0),
    max_current INTEGER CHECK(max_current IS NULL OR max_current >= 0),
    min_current INTEGER CHECK(min_current IS NULL OR min_current >= 0),

    -- Metadata (JSON - geçici, normalize edilebilir)
    metadata TEXT NOT NULL DEFAULT '{}',      -- JSON (backward compatibility)

    -- Audit fields
    created_at INTEGER NOT NULL,              -- Unix timestamp
    updated_at INTEGER NOT NULL                -- Unix timestamp
)

-- Events tablosu (normalized)
CREATE TABLE session_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_timestamp INTEGER NOT NULL,
    from_state INTEGER,
    to_state INTEGER,
    from_state_name TEXT,
    to_state_name TEXT,
    event_data TEXT,                          -- JSON (additional data)
    created_at INTEGER NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
)

-- Metadata tablosu (normalized - opsiyonel)
CREATE TABLE session_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    metadata_key TEXT NOT NULL,
    metadata_value TEXT,
    value_type TEXT CHECK(value_type IN ('string', 'number', 'boolean', 'json')),
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
    UNIQUE(session_id, metadata_key)
)

-- Index'ler
-- Sessions table indexes
CREATE INDEX idx_sessions_start_time ON sessions(start_time DESC)
CREATE INDEX idx_sessions_status ON sessions(status)
CREATE INDEX idx_sessions_end_time ON sessions(end_time DESC)
CREATE INDEX idx_sessions_status_start_time ON sessions(status, start_time DESC)
CREATE INDEX idx_sessions_status_end_time ON sessions(status, end_time DESC)
CREATE INDEX idx_sessions_active ON sessions(start_time DESC)
    WHERE status = 'ACTIVE' AND end_time IS NULL
CREATE INDEX idx_sessions_start_time_range ON sessions(start_time DESC, end_time DESC)

-- Session events indexes
CREATE INDEX idx_session_events_session_id ON session_events(session_id)
CREATE INDEX idx_session_events_event_type ON session_events(event_type)
CREATE INDEX idx_session_events_timestamp ON session_events(event_timestamp DESC)
CREATE INDEX idx_session_events_session_timestamp ON session_events(session_id, event_timestamp DESC)
CREATE INDEX idx_session_events_session_type ON session_events(session_id, event_type)

-- Session metadata indexes
CREATE INDEX idx_session_metadata_session_id ON session_metadata(session_id)
CREATE INDEX idx_session_metadata_key ON session_metadata(metadata_key)
CREATE INDEX idx_session_metadata_session_key ON session_metadata(session_id, metadata_key)

-- SQLite optimizasyonları
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=10000;
PRAGMA foreign_keys=ON;
PRAGMA temp_store=MEMORY;
```

### Şema Karşılaştırması

| Özellik | Mevcut Şema | Önerilen Şema |
|---------|-------------|---------------|
| **Normalizasyon** | Denormalized (JSON blobs) | Normalized (ayrı tablolar) |
| **Events Storage** | JSON array (TEXT) | Normalized table |
| **Metadata Storage** | JSON object (TEXT) | Normalized table (opsiyonel) |
| **Timestamps** | TEXT (ISO format) | INTEGER (Unix timestamp) |
| **Hesaplanmış Alanlar** | Runtime hesaplama | Materialized columns |
| **Index Stratejisi** | Tek kolon index'ler | Composite index'ler |
| **Query Performance** | Yavaş (JSON parse) | Hızlı (index kullanımı) |
| **Scalability** | Sorunlu (büyük JSON) | İyi (normalized) |
| **Analytics** | Zor (JSON parse) | Kolay (SQL queries) |

---

## 🔍 Query Pattern Analizi

### Mevcut Query Patterns

#### 1. Session Listesi Sorguları
```sql
-- Mevcut: Status filtresi + tarih sıralaması
SELECT * FROM sessions
WHERE status = ?
ORDER BY start_time DESC
LIMIT ? OFFSET ?
```

**Sorun:**
- Composite index yok
- TEXT sıralama yavaş

**İyileştirme:**
```sql
-- Composite index ile optimize
CREATE INDEX idx_sessions_status_start_time ON sessions(status, start_time DESC)
```

#### 2. Aktif Session Sorgusu
```sql
-- Mevcut: Status + end_time kontrolü
SELECT * FROM sessions
WHERE status = 'ACTIVE' AND end_time IS NULL
ORDER BY start_time DESC
LIMIT 1
```

**Sorun:**
- Partial index yok
- TEXT karşılaştırması yavaş

**İyileştirme:**
```sql
-- Partial index ile optimize
CREATE INDEX idx_sessions_active ON sessions(start_time DESC)
WHERE status = 'ACTIVE' AND end_time IS NULL
```

#### 3. Tarih Aralığı Sorguları
```sql
-- Mevcut: Tarih aralığı (gelecekte gerekebilir)
SELECT * FROM sessions
WHERE start_time >= ? AND start_time <= ?
ORDER BY start_time DESC
```

**Sorun:**
- TEXT karşılaştırması zor
- Index kullanımı verimsiz

**İyileştirme:**
```sql
-- INTEGER timestamp ile optimize
SELECT * FROM sessions
WHERE start_time >= ? AND start_time <= ?
ORDER BY start_time DESC
```

#### 4. Event Bazlı Sorgular (Mevcut: Yapılamıyor)

**İstenen Sorgular:**
```sql
-- Hangi session'larda CHARGE_STARTED event'i var?
-- Mevcut: Yapılamıyor (JSON içinde arama gerekir)

-- Hangi session'larda FAULT_DETECTED event'i var?
-- Mevcut: Yapılamıyor

-- Event timeline sorgusu
-- Mevcut: Yapılamıyor
```

**İyileştirme:**
```sql
-- Normalized events table ile
SELECT DISTINCT session_id
FROM session_events
WHERE event_type = 'CHARGE_STARTED'

SELECT s.*
FROM sessions s
JOIN session_events e ON s.session_id = e.session_id
WHERE e.event_type = 'FAULT_DETECTED'
```

---

## 📊 Performans Analizi

### Mevcut Performans Sorunları

#### 1. JSON Parse Overhead

**Sorun:**
- Her `get_session()` çağrısında JSON parse ediliyor
- Büyük event listelerinde yavaş

**Örnek:**
```python
# 1000 event'li bir session
events_json = "..." # ~200 KB
events = json.loads(events_json)  # ~10-20ms overhead
```

**İyileştirme:**
```python
# Normalized table ile
# Sadece gerekli event'ler yüklenir
SELECT * FROM session_events
WHERE session_id = ?
ORDER BY event_timestamp DESC
LIMIT 100
# ~1-2ms
```

#### 2. Update Overhead

**Sorun:**
- Tek bir event eklemek için tüm events JSON'ı güncelleniyor
- Büyük JSON'lar için yavaş

**Örnek:**
```python
# 1000 event'li session'a yeni event ekleme
events.append(new_event)  # Memory'de
json.dumps(events)  # ~200 KB JSON serialize
UPDATE sessions SET events = ? WHERE session_id = ?  # ~200 KB write
```

**İyileştirme:**
```sql
-- Normalized table ile
INSERT INTO session_events (session_id, event_type, ...)
VALUES (?, ?, ...)
-- ~1ms
```

#### 3. Query Performance

**Mevcut Durum:**
- Event type'a göre filtreleme yapılamıyor
- Full table scan gerekebilir

**İyileştirme:**
- Normalized table + index ile hızlı sorgular

---

## 🎯 Migration Stratejisi

### Adım 1: Yeni Şema Oluştur

```python
# Migration script
def migrate_to_normalized_schema():
    # 1. Yeni tabloları oluştur
    # 2. Mevcut verileri migrate et
    # 3. Eski tabloyu yedekle
    # 4. Yeni tabloyu aktif et
```

### Adım 2: Veri Migration

```python
def migrate_events_to_table():
    # Mevcut sessions tablosundan events JSON'ını parse et
    # Her event'i session_events tablosuna ekle
    for session in old_sessions:
        events = json.loads(session['events'])
        for event in events:
            insert_into_session_events(session['session_id'], event)
```

### Adım 3: Backward Compatibility

```python
# Geçiş döneminde hem eski hem yeni format desteklenebilir
# Eski format: events JSON
# Yeni format: session_events table
```

---

## 📋 Öncelikli Aksiyon Planı

### Acil (Öncelik 0-1)

1. **Database Şema Migration (TEXT → INTEGER)**
   - Timestamp alanlarını INTEGER'a çevir
   - Migration script yaz
   - **Tahmini Süre:** 2-3 saat
   - **Etki:** Yüksek (performans)

2. **Connection Management İyileştirmesi**
   - Persistent connection + WAL mode
   - **Tahmini Süre:** 1-2 saat
   - **Etki:** Yüksek (performans %30-50)

### Yüksek Öncelik (Öncelik 2-3)

3. **Events Normalization**
   - `session_events` tablosu oluştur
   - Events'i normalize et
   - Migration script yaz
   - **Tahmini Süre:** 3-4 saat
   - **Etki:** Çok Yüksek (query capability, performance)

4. **Composite Index'ler**
   - Status + start_time index
   - Status + end_time index
   - **Tahmini Süre:** 30 dakika
   - **Etki:** Orta-Yüksek (sorgu performansı)

### Orta Öncelik (Öncelik 4-5)

5. **Materialized Columns**
   - `duration_seconds`, `event_count` gibi alanlar
   - **Tahmini Süre:** 1-2 saat
   - **Etki:** Orta (summary performance)

6. **Check Constraints**
   - Status ve state değerleri için
   - **Tahmini Süre:** 1 saat
   - **Etki:** Orta (veri güvenliği)

7. **Metadata Normalization** (Opsiyonel)
   - `session_metadata` tablosu
   - **Tahmini Süre:** 2-3 saat
   - **Etki:** Orta (query capability)

---

## 🔧 İyileştirilmiş Database Modülü Tasarımı

### Connection Management

```python
class Database:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or self._get_default_path()
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._configure_database()
        self._initialize_schema()

    def _configure_database(self):
        """SQLite optimizasyonları"""
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA cache_size=10000")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA temp_store=MEMORY")

    def _get_connection(self):
        return self.conn  # Persistent connection
```

### Events Management

```python
def create_event(self, session_id: str, event_type: str, event_data: Dict):
    """Event oluştur (normalized)"""
    cursor = self.conn.cursor()
    cursor.execute(
        """
        INSERT INTO session_events
        (session_id, event_type, event_timestamp, from_state, to_state, event_data)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (session_id, event_type, int(time.time()), ...)
    )
    # Session event_count'u güncelle
    cursor.execute(
        "UPDATE sessions SET event_count = event_count + 1 WHERE session_id = ?",
        (session_id,)
    )
    self.conn.commit()
```

---

## 📊 Performans Metrikleri (Tahmini)

### Mevcut Durum
- **Session oluşturma:** ~5-10ms
- **Event ekleme:** ~10-15ms (tüm events JSON update)
- **Session sorgulama:** ~5-10ms (JSON parse overhead)
- **Event bazlı sorgu:** ❌ Yapılamıyor

### İyileştirme Sonrası (Tahmini)
- **Session oluşturma:** ~2-5ms (%50 iyileştirme)
- **Event ekleme:** ~1-2ms (%90 iyileştirme)
- **Session sorgulama:** ~2-5ms (%50 iyileştirme)
- **Event bazlı sorgu:** ~5-10ms (yeni capability)

---

## 🎯 Sonuç ve Öneriler

### Genel Değerlendirme

**Kritik Sorunlar:**
- 🔴 Denormalized schema (JSON blobs)
- 🔴 TEXT timestamps
- 🔴 Connection management
- 🔴 Event query capability yok

**İyileştirme Öncelikleri:**
1. **Events normalization** (En kritik)
2. **Timestamp migration** (Yüksek öncelik)
3. **Connection management** (Yüksek öncelik)
4. **Composite index'ler** (Orta öncelik)
5. **Materialized columns** (Orta öncelik)

### Önerilen Yaklaşım

**Faz 1: Temel İyileştirmeler (1-2 gün)**
- Timestamp migration
- Connection management
- Composite index'ler

**Faz 2: Normalization (2-3 gün)**
- Events table oluştur
- Migration script
- Backward compatibility

**Faz 3: Advanced Features (1-2 gün)**
- Materialized columns
- Metadata normalization (opsiyonel)
- Analytics queries

---

**Son Güncelleme:** 2025-12-10 06:00:00

