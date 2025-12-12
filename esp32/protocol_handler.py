"""
ESP32 Protocol Handler Module
Created: 2025-12-12 10:45:00
Last Modified: 2025-12-12 10:45:00
Version: 1.0.0
Description: ESP32 protokol işleme ve parsing modülü
"""

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, Optional

# Protocol constants
PROTOCOL_HEADER = 0x41
PROTOCOL_SEPARATOR = 0x2C
PROTOCOL_FOOTER = 0x10
BAUDRATE = 115200
STATUS_UPDATE_INTERVAL = 5  # seconds

# Status message format: <STAT;ID=X;CP=X;CPV=X;PP=X;PPV=X;RL=X;LOCK=X;MOTOR=X;PWM=X;MAX=X;CABLE=X;AUTH=X;STATE=X;PB=X;STOP=X;>


def load_protocol() -> Dict[str, Any]:
    """
    Protokol tanımlarını yükle

    Returns:
        Protokol tanımları dict'i
    """
    try:
        protocol_path = os.path.join(os.path.dirname(__file__), "protocol.json")
        with open(protocol_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from api.logging_config import esp32_logger

        esp32_logger.error(f"Protocol yükleme hatası: {e}", exc_info=True)
        return {}


def parse_status_message(message: str) -> Optional[Dict[str, Any]]:
    """
    ESP32'den gelen status mesajını parse et

    Args:
        message: Status mesajı string'i

    Returns:
        Parse edilmiş durum dict'i veya None
    """
    # Format: <STAT;ID=X;CP=X;CPV=X;PP=X;PPV=X;RL=X;LOCK=X;MOTOR=X;PWM=X;MAX=X;CABLE=X;AUTH=X;STATE=X;PB=X;STOP=X;>
    pattern = r"<STAT;(.*?)>"
    match = re.search(pattern, message)
    if not match:
        return None

    status_data = {}
    fields = match.group(1).split(";")

    for field in fields:
        # Whitespace temizle
        field = field.strip()
        if not field:
            continue
        if "=" in field:
            key, value = field.split("=", 1)
            key = key.strip()
            value = value.strip()
            # Sayısal değerleri dönüştür
            try:
                if "." in value:
                    status_data[key] = float(value)
                else:
                    status_data[key] = int(value)
            except ValueError:
                status_data[key] = value

    status_data["timestamp"] = datetime.now().isoformat()

    # STATE değerini STATE_NAME'e çevir
    if "STATE" in status_data:
        state_value = status_data["STATE"]
        # ESP32State enum mapping
        state_names = {
            0: "HARDFAULT_END",
            1: "IDLE",
            2: "CABLE_DETECT",
            3: "EV_CONNECTED",
            4: "READY",
            5: "CHARGING",
            6: "PAUSED",
            7: "STOPPED",
            8: "FAULT_HARD",
        }
        status_data["STATE_NAME"] = state_names.get(
            state_value, f"UNKNOWN_{state_value}"
        )

    return status_data


def parse_ack_message(message: str) -> Optional[Dict[str, Any]]:
    """
    ESP32'den gelen ACK mesajını parse et

    Args:
        message: ACK mesajı string'i

    Returns:
        Parse edilmiş ACK dict'i veya None
    """
    # Format: <ACK;CMD=[KOMUT];STATUS=[DURUM];[EK_BILGI];>
    pattern = r"<ACK;(.*?)>"
    match = re.search(pattern, message)
    if not match:
        return None

    ack_data = {}
    fields = match.group(1).split(";")

    for field in fields:
        # Whitespace temizle
        field = field.strip()
        if not field:
            continue
        if "=" in field:
            key, value = field.split("=", 1)
            key = key.strip()
            value = value.strip()
            ack_data[key] = value

    ack_data["timestamp"] = datetime.now().isoformat()
    return ack_data


def get_command_bytes(protocol_data: Dict[str, Any], command_name: str) -> list:
    """
    Protokol tanımlarından komut byte array'ini al

    Args:
        protocol_data: Protokol tanımları dict'i
        command_name: Komut adı (örn: "status", "authorization", "charge_stop")

    Returns:
        Komut byte array'i (varsayılan değerlerle)
    """
    cmd = protocol_data.get("commands", {}).get(command_name, {})
    default_bytes = {
        "status": [65, 0, 44, 0, 16],
        "authorization": [65, 1, 44, 1, 16],
        "charge_stop": [65, 4, 44, 7, 16],
    }
    return cmd.get("byte_array", default_bytes.get(command_name, [65, 0, 44, 0, 16]))
