# ABB Meter RS485 Araştırma Notları

**Oluşturulma Tarihi:** 2025-12-09 04:25:00  
**Son Güncelleme:** 2025-12-09 04:25:00  
**Version:** 1.0.0

---

## 🔍 Web Araştırması Bulguları

### 1. GPIO Pin Fonksiyonu Sorunu

**Sorun:**
- GPIO12 ve GPIO13 pinleri "alt4" fonksiyonunda görünüyor
- Pinler "UNCLAIMED" durumunda
- UART5 için "ALT3" fonksiyonu gerekiyor

**Kaynak:** Raspberry Pi forumları ve Modbus RTU troubleshooting kaynakları

**Çözüm Önerileri:**
- Config.txt'de pin mapping'i kontrol et
- Alternatif olarak UART0 (GPIO14/15) kullanılabilir
- Pin fonksiyonunu doğrulamak için `gpio readall` veya `/sys/kernel/debug/pinctrl/` kullan

---

### 2. RS485 Sonlandırma Dirençleri

**Önemli Bulgu:**
- RS485 hattının her iki ucunda **120Ω** sonlandırma dirençleri kullanılmalı
- Bu dirençler sinyal yansımalarını önler
- Özellikle uzun mesafelerde kritik öneme sahip

**Kaynak:** Modbus RTU protokol dokümantasyonu ve RS485 best practices

**Uygulama:**
- Meter ve MAX13487 arasındaki hatta sonlandırma direnci ekle
- Hattın her iki ucunda 120Ω direnç kullan

---

### 3. MAX13487 DE/RE Kontrol Pinleri

**Önemli Bulgu:**
- MAX13487 çevirici DE (Driver Enable) ve RE (Receiver Enable) pinleri var
- Bu pinler RTS sinyali ile kontrol edilmeli
- RTS=HIGH → TX modu (veri gönderme)
- RTS=LOW → RX modu (veri alma)

**Kaynak:** MAX13487 datasheet ve RS485 transceiver dokümantasyonu

**Uygulama:**
- RTS sinyalinin veri paketleriyle senkronize olması kritik
- RTS geçişlerinde yeterli bekleme süreleri kullan (5ms önerilir)
- Veri gönderme/alma arasında net ayrım yap

---

### 4. RTS Sinyali Senkronizasyonu

**Sorun:**
- Modbus RTU protokolünde RTS sinyalinin doğru zamanlaması çok önemli
- RTS HIGH → Veri gönder → RTS LOW → Veri bekle
- RTS geçişleri arasında kısa bekleme süreleri gerekebilir

**Kaynak:** CODESYS forumları ve Modbus RTU troubleshooting

**Uygulama:**
- RTS HIGH → 5ms bekle → Veri gönder → 2ms bekle → RTS LOW → 5ms bekle → Veri oku
- Bu zamanlamalar MAX13487'in stabil çalışması için kritik

---

### 5. Topraklama ve Parazit

**Önemli Bulgu:**
- RS485 iletişiminde cihazlar arasında ortak bir toprak hattı olmalı
- Topraklama eksikliği veya parazitler iletişim sorunlarına yol açabilir
- MAX13487 ve meter arasında GND bağlantısı kontrol edilmeli

**Kaynak:** RS485 protokol dokümantasyonu ve elektrik mühendisliği kaynakları

**Uygulama:**
- Tüm cihazlar arasında ortak GND bağlantısı sağla
- Parazit kaynaklarını izole et
- Shield kullanımı önerilir (uzun mesafelerde)

---

### 6. ABB Meter B23 112-100

**Durum:**
- Spesifik Modbus RTU dokümantasyonu bulunamadı
- Meter üzerindeki ayarlar veya dokümantasyon kontrol edilmeli

**Genel ABB Meter Ayarları:**
- Baudrate: Genellikle 9600 veya 19200
- Parity: Genellikle EVEN (bazı modellerde NONE)
- Stop Bits: 1
- Data Bits: 8
- Slave ID: Genellikle 1-247 aralığında (çoğunlukla 1)

**Kaynak:** ABB meter genel dokümantasyonu ve Modbus RTU standartları

---

## 📚 Referans Kaynaklar

1. **Raspberry Pi UART Konfigürasyonu:**
   - Raspberry Pi Foundation dokümantasyonu
   - GPIO pin mapping ve UART overlay dokümantasyonu

2. **Modbus RTU Protokolü:**
   - Modbus.org resmi dokümantasyonu
   - Modbus RTU troubleshooting guide

3. **RS485 İletişimi:**
   - RS485 protokol dokümantasyonu
   - MAX13487 datasheet

4. **Forum ve Topluluk Kaynakları:**
   - CODESYS forumları
   - Raspberry Pi forumları
   - Home Assistant topluluğu
   - Stack Overflow Modbus RTU soruları

---

## 🔄 Sonraki Adımlar

1. **GPIO Pin Fonksiyonunu Düzelt:**
   - Pinlerin ALT3 fonksiyonuna geçmesi için config.txt'yi kontrol et
   - Alternatif olarak UART0 (GPIO14/15) kullanılabilir

2. **RS485 Sonlandırma Dirençleri:**
   - Hattın her iki ucuna 120Ω direnç ekle
   - Özellikle meter ve MAX13487 arasında

3. **RTS Kontrolünü İyileştir:**
   - RTS geçişlerinde yeterli bekleme süreleri kullan (5ms)
   - Veri gönderme/alma arasında net ayrım yap

4. **Alternatif Test:**
   - Meter'i başka bir RS485 cihazla test et
   - MAX13487'i başka bir UART ile test et
   - Bu şekilde sorunun kaynağını izole edebiliriz

5. **Meter Dokümantasyonu:**
   - Meter üzerindeki ayarları kontrol et
   - Meter dokümantasyonunu incele
   - Üretici desteğinden yardım al

---

**Son Güncelleme:** 2025-12-09 04:25:00

