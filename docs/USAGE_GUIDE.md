# 📖 Dosya Kullanım Rehberi

**Oluşturulma Tarihi:** 2025-12-10
**Amaç:** Hangi dosyayı ne zaman kullanacağınızı açıklar

---

## 🎯 Hızlı Cevap

### ✅ Sadece QUICK_SETUP_PROMPT.md Yeterli!

**AI Agent'a sadece `QUICK_SETUP_PROMPT.md` içindeki prompt'u verin.** Agent otomatik olarak tüm dosyaları oluşturacaktır.

### 📚 Diğer Dosyalar Ne İçin?

Diğer dosyalar **referans ve manuel kurulum** için hazırlanmıştır:

---

## 📋 Dosya Kullanım Senaryoları

### Senaryo 1: Otomatik Kurulum (Önerilen) ⭐

**Kullanılacak Dosya:** `QUICK_SETUP_PROMPT.md`

**Adımlar:**
1. `QUICK_SETUP_PROMPT.md` dosyasını açın
2. İçindeki prompt'u kopyalayın
3. Yeni projenizde AI agent'a verin
4. Agent otomatik olarak tüm dosyaları oluşturur
5. Projenize özel bilgileri ekleyin

**Sonuç:** ✅ Todo sistemi otomatik kurulur

---

### Senaryo 2: Manuel Kurulum

**Kullanılacak Dosya:** `TODO_SYSTEM_TEMPLATES.md`

**Ne Zaman Kullanılır:**
- AI agent kullanmıyorsanız
- Kontrolü sizde tutmak istiyorsanız
- Agent dosyaları oluşturmadıysa

**Adımlar:**
1. `TODO_SYSTEM_TEMPLATES.md` dosyasını açın
2. Her şablonu kopyalayın
3. `todo/` klasörü oluşturun
4. Her dosyayı oluşturup şablonları yapıştırın
5. Projenize özel bilgileri ekleyin

**Sonuç:** ✅ Manuel olarak todo sistemi kurulur

---

### Senaryo 3: Detaylı Bilgi İhtiyacı

**Kullanılacak Dosyalar:**
- `AI_WORKFLOW_SETUP_PROMPT.md` (daha detaylı prompt)
- `AI_WORKFLOW_SETUP_README.md` (genel rehber)

**Ne Zaman Kullanılır:**
- Daha fazla açıklama gerekiyorsa
- Kuralları daha detaylı anlamak istiyorsanız
- Referans dokümantasyon gerekiyorsa

**Adımlar:**
1. Bu dosyaları okuyun
2. QUICK_SETUP_PROMPT.md'deki prompt'u genişletin
3. Veya manuel kurulum yaparken referans olarak kullanın

**Sonuç:** ✅ Daha detaylı bilgi edinilir

---

## 🔄 Karşılaştırma Tablosu

| Dosya | Ne İçin? | Ne Zaman? | Zorunlu mu? |
|-------|----------|-----------|-------------|
| **QUICK_SETUP_PROMPT.md** | AI agent'a verilecek prompt | Otomatik kurulum için | ✅ **EVET** (otomatik kurulum için) |
| **TODO_SYSTEM_TEMPLATES.md** | Manuel kurulum şablonları | Manuel kurulum için | ❌ Hayır (isteğe bağlı) |
| **AI_WORKFLOW_SETUP_PROMPT.md** | Detaylı açıklamalı prompt | Daha fazla bilgi gerektiğinde | ❌ Hayır (isteğe bağlı) |
| **AI_WORKFLOW_SETUP_README.md** | Genel kullanım rehberi | Referans dokümantasyon | ❌ Hayır (isteğe bağlı) |

---

## 💡 Önerilen Kullanım

### En Hızlı Yol (Önerilen):

```
1. QUICK_SETUP_PROMPT.md → Prompt'u kopyala
2. AI Agent'a ver
3. ✅ Tamam!
```

### Daha Kontrollü Yol:

```
1. QUICK_SETUP_PROMPT.md → Prompt'u oku
2. TODO_SYSTEM_TEMPLATES.md → Şablonları kontrol et
3. AI Agent'a prompt'u ver
4. Oluşturulan dosyaları şablonlarla karşılaştır
5. ✅ Kontrol edildi!
```

### Manuel Kurulum:

```
1. TODO_SYSTEM_TEMPLATES.md → Şablonları kopyala
2. todo/ klasörü oluştur
3. Her dosyayı oluştur ve şablonları yapıştır
4. Projenize özel bilgileri ekle
5. ✅ Manuel kurulum tamamlandı!
```

---

## ❓ Sık Sorulan Sorular

### S: Sadece QUICK_SETUP_PROMPT.md yeterli mi?

**C:** ✅ **Evet!** AI agent'a sadece bu dosyadaki prompt'u verin. Agent otomatik olarak tüm dosyaları oluşturacaktır.

### S: Diğer dosyaları da vermem gerekir mi?

**C:** ❌ **Hayır!** Diğer dosyalar referans ve manuel kurulum için. AI agent'a sadece prompt yeterli.

### S: Agent dosyaları oluşturmadıysa ne yapmalıyım?

**C:** `TODO_SYSTEM_TEMPLATES.md` dosyasındaki şablonları kullanarak manuel olarak oluşturabilirsiniz.

### S: Daha detaylı bilgi istiyorsam?

**C:** `AI_WORKFLOW_SETUP_PROMPT.md` ve `AI_WORKFLOW_SETUP_README.md` dosyalarını okuyun.

### S: Prompt'u özelleştirebilir miyim?

**C:** ✅ **Evet!** Prompt'u projenize göre düzenleyebilirsiniz. `TODO_SYSTEM_TEMPLATES.md` ve `CURSORRULES_TEMPLATE.md` dosyalarındaki şablonları referans olarak kullanabilirsiniz.

### S: .cursorrules dosyası da oluşturulacak mı?

**C:** ✅ **Evet!** `QUICK_SETUP_PROMPT.md` içindeki prompt `.cursorrules` dosyasını da oluşturur. Bu dosya AI agent'ın çalışma kurallarını belirler ve çok önemlidir.

---

## 🎯 Özet

### ✅ Yapılacaklar:

1. **`QUICK_SETUP_PROMPT.md`** dosyasını açın
2. İçindeki prompt'u kopyalayın
3. Yeni projenizde AI agent'a verin
4. Agent dosyaları oluşturduktan sonra kontrol edin:
   - ✅ `todo/` klasörü ve dosyaları
   - ✅ `.cursorrules` dosyası
5. Projenize özel bilgileri ekleyin:
   - Proje adı
   - Çalışma dizini
   - Repository URL
   - Projeye özel kurallar

### ❌ Yapılmayacaklar:

- ❌ Tüm dosyaları AI agent'a vermeyin (gereksiz)
- ❌ Prompt'u değiştirmeden kullanmayın (projenize özel bilgileri ekleyin)
- ❌ Agent dosyaları oluşturduktan sonra kontrol etmeyi unutmayın
- ❌ `.cursorrules` dosyasını atlamayın (çok önemli!)

---

## 📝 Notlar

- **QUICK_SETUP_PROMPT.md** → Ana dosya (mutlaka kullanın) - Todo sistemi + .cursorrules
- **CURSORRULES_TEMPLATE.md** → .cursorrules şablonu (referans)
- **CURSORRULES_SETUP_PROMPT.md** → Sadece .cursorrules için prompt (isteğe bağlı)
- **TODO_SYSTEM_TEMPLATES.md** → Referans şablonlar (isteğe bağlı)
- **AI_WORKFLOW_SETUP_PROMPT.md** → Detaylı açıklamalar (isteğe bağlı)
- **AI_WORKFLOW_SETUP_README.md** → Genel rehber (isteğe bağlı)

---

**Son Güncelleme:** 2025-12-10

**🎯 Başlamak için: `QUICK_SETUP_PROMPT.md` dosyasını açın ve prompt'u kopyalayın!**

