# Aktif Görevler (Şu Anda Yapılanlar)

**Son Güncelleme:** 2025-12-09 16:10:00

---

## Aktif Görevler

### 🔄 Event Detection Modülü (Yüksek Öncelik)

**Görev ID:** TASK-006  
**Başlangıç Tarihi:** 2025-12-09 16:10:00  
**Durum:** 📋 Bekliyor  
**Öncelik:** Yüksek

#### Açıklama
State transition detection ve event classification modülü oluşturulması gerekiyor. Logging sistemi kuruldu, şimdi event detection eklenmeli.

#### Alt Görevler
- [ ] Event detector modülü oluştur (`api/event_detector.py`)
- [ ] State transition detection implementasyonu
- [ ] Event type classification (kablo takılma, araç bağlantı, şarj başlatma/durdurma)
- [ ] Event logging entegrasyonu
- [ ] Unit testler yazılması

#### Tahmini Süre
2-3 gün

#### Bağımlılıklar
- Logging sistemi ✅ (Tamamlandı)
- ESP32 bridge modülü ✅ (Mevcut)

#### Notlar
- Event'ler state transition'lara göre tespit edilecek
- Event'ler structured logging ile loglanacak
- Event types: CABLE_CONNECTED, EV_CONNECTED, CHARGE_STARTED, CHARGE_STOPPED, CABLE_DISCONNECTED

---

## Notlar

- Aktif görevler buraya eklenecek
- Maksimum 2-3 aktif görev olmalı
- Her görev tamamlandığında `master_done.md`'ye taşınacak

