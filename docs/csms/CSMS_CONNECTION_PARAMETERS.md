# CSMS ↔ Station Connection Parameters (OCPP 2.0.1 + 1.6j)

**Oluşturulma:** 2025-12-15
**Son Güncelleme:** 2025-12-15 02:40
**Durum:** ✅ Aktif

## 1) CSMS URL nedir? (gerçek mi / simülatör mü?)

- **CSMS (Dashboard UI)**: `http://lixhium.xyz/`
- **CSMS Swagger (API Docs)**: `http://lixhium.xyz/docs`

Bu ortam **gerçek CSMS sunucusudur** (simülatör değil). İstasyon tarafında geliştirme/test için simülatör kullanılabilir; hedef endpoint’ler aynıdır.

## 2) Bağlantı şekli / güvenlik (TLS, BasicAuth, token)

### OCPP WebSocket URL’leri
- **OCPP 2.0.1 (primary target)**:
  - URL: `ws://lixhium.xyz/ocpp/{STATION_NAME}`
  - Subprotocol: `ocpp2.0.1`
- **OCPP 1.6j (compat)**:
  - URL: `ws://lixhium.xyz/ocpp16/{STATION_NAME}`
  - Subprotocol: `ocpp1.6`

### Station authentication (WebSocket Authorization header)
İstasyon bağlantısında **HTTP header** olarak Basic Auth beklenir:

- Header: `Authorization: Basic base64("{STATION_NAME}:{station_password}")`

Notlar:
- İstasyon daha önce kayıtlı değilse CSMS “auto-provisioning” modunda bağlantıya izin verir (ilk BootNotification ile kayıt akışı).
- Kayıtlı ve onaylı istasyonlarda parola doğrulaması beklenir.

### TLS (wss)
Şu an **HTTP/WS** (80 / `ws://`) aktif.
Gerçek saha istasyonları `wss://` zorunlu tutuyorsa, **Let’s Encrypt + 443/WSS** planlanmıştır (P0 görev). Bu durumda hedef URL’ler:
- `wss://lixhium.xyz/ocpp/{STATION_NAME}`
- `wss://lixhium.xyz/ocpp16/{STATION_NAME}`

## 3) Connector sayısı / tip
- İstasyon: **AC**
- Connector: **1 adet**

## 4) Kimlik / Authorization (RFID / idTag / idToken)
En basit başlangıç için öneri:
- İlk faz: **tek kullanıcı / test kimlik** (ör. sabit `idTag` / `idToken`) ile akış doğrulama
- İkinci faz: gerçek RFID/idTag/idToken yönetimi (user provisioning, whitelist/blacklist, UI akışı)

İstasyon ekibi ilk fazda “tek test kimlik” ile Authorize/StartTransaction akışlarını çalıştıracak şekilde geliştirebilir.

## 5) OCPP önceliği (1.6j mi 2.0.1 mi?)
Önerilen yaklaşım:
- **Primary**: OCPP **2.0.1**
- **Fallback/compat**: OCPP **1.6j**

İlk teslimatta 2.0.1’i hedefleyip, paralelde 1.6j’yi minimum uyumluluk için açık tutuyoruz.


