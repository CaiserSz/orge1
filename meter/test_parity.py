"""
ABB Meter Parity Test Scripti
Created: 2025-12-09 04:24:00
Last Modified: 2025-12-09 04:24:00
Version: 1.0.0
Description: Farklı parity ayarlarını test eder
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from meter.read_meter import ABBMeterReader
import serial
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

print("ABB Meter Parity Testi")
print("=" * 60)

# Test edilecek parity ayarları
PARITY_OPTIONS = [
    ("EVEN", serial.PARITY_EVEN),
    ("ODD", serial.PARITY_ODD),
    ("NONE", serial.PARITY_NONE),
]

BAUDRATES = [9600, 19200]
SLAVE_IDS = [1, 2]

found = False

for baudrate in BAUDRATES:
    print(f"\n📡 Baudrate: {baudrate}")
    print("-" * 60)
    
    for parity_name, parity_value in PARITY_OPTIONS:
        print(f"\n  🔧 Parity: {parity_name}")
        
        for slave_id in SLAVE_IDS:
            print(f"    🔢 Slave ID: {slave_id}", end=" ... ")
            
            try:
                # Özel parity ile reader oluştur
                reader = ABBMeterReader(
                    device="/dev/ttyAMA5",
                    baudrate=baudrate,
                    slave_id=slave_id,
                    timeout=0.5
                )
                
                # Parity'yi değiştir
                if reader.connect():
                    # Serial connection'ı kapat ve yeniden aç
                    reader.disconnect()
                    
                    # Parity ile yeniden bağlan
                    reader.serial_connection = serial.Serial(
                        port=reader.device,
                        baudrate=reader.baudrate,
                        bytesize=serial.EIGHTBITS,
                        parity=parity_value,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=reader.timeout
                    )
                    reader.is_connected = True
                    time.sleep(0.1)
                    
                    # Test okuma
                    result = reader.read_input_registers(0x0000, 1)
                    
                    if result is not None:
                        print(f"✅ BAŞARILI! Response: {result}")
                        print(f"\n🎯 BULUNAN AYARLAR:")
                        print(f"   Baudrate: {baudrate}")
                        print(f"   Parity: {parity_name}")
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
            
            time.sleep(0.1)
        
        if found:
            break
    
    if found:
        break

if not found:
    print("\n❌ Hiçbir parity kombinasyonunda meter bulunamadı!")
    print("\nFiziksel kontroller yapılmalı:")
    print("  1. Meter açık ve çalışıyor mu?")
    print("  2. RS485 TX-RX bağlantıları ters çevrilmeli")
    print("  3. MAX13487 çevirici kontrol edilmeli")
    print("  4. GPIO12/13 fiziksel bağlantıları kontrol edilmeli")

