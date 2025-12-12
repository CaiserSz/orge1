# Analiz Ignore Listesi

**Oluşturulma Tarihi:** 2025-12-10 11:45:00
**Son Güncelleme:** 2025-12-10 11:45:00
**Versiyon:** 1.0.0

## Amaç

Bu dosya, gelecekteki analizlerde ignore edilecek konuları listeler. Bu konular user istediğinde yapılacak ve analizlerde raporlanmayacaktır.

---

## Ignore Edilecek Konular

### 1. API Key Rotation Mekanizması

**Durum:** ⏸️ ERTELENDİ - User İsteğine Bağlı

**Açıklama:**
- API key rotation mekanizması implementasyonu
- Multiple API keys desteği
- API key expiration mekanizması
- Graceful rotation
- Key revocation mekanizması

**Neden Ignore Edilecek:**
- User istediğinde yapılacak
- Mevcut API key sistemi yeterli
- Gelecekteki analizlerde raporlanmayacak

**İlgili Dosyalar:**
- `api/auth.py`
- `todo/master_next.md` (Ertelendi statüsünde)

---

### 2. API Key Logging İyileştirmesi

**Durum:** ⏸️ ERTELENDİ - User İsteğine Bağlı

**Açıklama:**
- API key'ler log'lara yazılıyor (kısaltılmış olsa da)
- Daha az bilgi loglanmalı
- API key'ler log'lara yazılmamalı (veya sadece hash yazılmalı)
- Audit trail için sadece key ID veya hash kullanılmalı

**Neden Ignore Edilecek:**
- User istediğinde yapılacak
- Mevcut logging yeterli (kısaltılmış key loglanıyor)
- Gelecekteki analizlerde raporlanmayacak

**İlgili Dosyalar:**
- `api/routers/charge.py`
- `api/routers/current.py`
- `todo/master_next.md` (Ertelendi statüsünde)

---

### 3. JWT/OAuth2 Authentication

**Durum:** ⏸️ ERTELENDİ - User İsteğine Bağlı

**Açıklama:**
- JWT token authentication
- OAuth2 authentication
- Mevcut API key sistemi yerine veya ek olarak

**Neden Ignore Edilecek:**
- User istediğinde yapılacak
- Mevcut API key sistemi yeterli
- Gelecekteki analizlerde raporlanmayacak

**İlgili Dosyalar:**
- `api/auth.py`
- `todo/master_next.md` (Ertelendi statüsünde)

---

## Analiz Kuralları

### Gelecekteki Analizlerde

1. **Bu konular analiz edilmeyecek**
2. **Bu konular raporlanmayacak**
3. **Bu konular önerilerde yer almayacak**
4. **Bu konular için yeni/tekrar todo açılmayacak** (master_next'de zaten varsa tekrar ekleme)

### Exception Durumları

- User açıkça bu konulardan birini isterse
- Kritik güvenlik açığı tespit edilirse (bu durumda user'a bildirilecek)

---

## Güncelleme Tarihçesi

- **2025-12-10 11:45:00** - İlk versiyon oluşturuldu
  - API Key Rotation Mekanizması eklendi
  - API Key Logging İyileştirmesi eklendi
  - JWT/OAuth2 Authentication eklendi

---

**Not:** Bu dosya, gelecekteki analizlerde referans olarak kullanılacaktır. Yeni ignore edilecek konular eklendiğinde bu dosya güncellenecektir.

