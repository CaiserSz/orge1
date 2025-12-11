"""
ABB Meter RS485 Tarama ve Test Scripti
Created: 2025-12-09 04:23:00
Last Modified: 2025-12-09 04:23:00
Version: 1.0.0
Description: Farklı baudrate ve slave ID kombinasyonlarını test eder
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from meter.read_meter import ABBMeterReader
import time
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

print("ABB Meter RS485 Tarama Testi")
print("=" * 60)

# Test edilecek kombinasyonlar
BAUDRATES = [9600, 19200, 4800]
SLAVE_IDS = [1, 2, 3, 247]  # 247 genellikle broadcast adresi
DEVICES = ["/dev/ttyAMA5", "/dev/ttyAMA4"]

found = False

for device in DEVICES:
    print(f"\n🔍 Cihaz: {device}")
    print("-" * 60)

    for baudrate in BAUDRATES:
        print(f"\n  📡 Baudrate: {baudrate}")

        for slave_id in SLAVE_IDS:
            print(f"    🔢 Slave ID: {slave_id}", end=" ... ")

            try:
                reader = ABBMeterReader(
                    device=device, baudrate=baudrate, slave_id=slave_id, timeout=0.5
                )

                if reader.connect():
                    # Basit bir register okuma denemesi
                    result = reader.read_input_registers(0x0000, 1)

                    if result is not None:
                        print(f"✅ BAŞARILI! Response: {result}")
                        print("\n🎯 BULUNAN AYARLAR:")
                        print(f"   Device: {device}")
                        print(f"   Baudrate: {baudrate}")
                        print(f"   Slave ID: {slave_id}")
                        found = True
                        reader.disconnect()
                        break
                    else:
                        print("❌")
                    reader.disconnect()
                else:
                    print("❌ (Bağlantı hatası)")

            except Exception as e:
                print(f"❌ (Hata: {e})")

            time.sleep(0.1)  # Kısa bekleme

        if found:
            break

    if found:
        break

if not found:
    print("\n❌ Hiçbir kombinasyonda meter bulunamadı!")
    print("\nKontrol edilmesi gerekenler:")
    print("  1. RS485 bağlantıları doğru mu? (TX-RX çapraz kontrol)")
    print("  2. Meter açık ve çalışıyor mu?")
    print("  3. MAX13487 çevirici doğru çalışıyor mu?")
    print("  4. GPIO12/13 pinleri doğru bağlı mı?")
    print("  5. Meter'in Modbus ayarları nedir? (baudrate, slave ID, parity)")
    print("  6. Register adresleri doğru mu? (0x0000 yerine başka adres deneyin)")
