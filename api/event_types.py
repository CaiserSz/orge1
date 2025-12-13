"""
Event Type Definitions
Created: 2025-12-13 02:00:00
Last Modified: 2025-12-13 02:00:00
Version: 1.0.0
Description: ESP32 state ve event enum tanımları.
"""

from enum import Enum

__all__ = ["ESP32State", "EventType"]


class ESP32State(Enum):
    """ESP32 state değerleri"""

    HARDFAULT_END = 0
    IDLE = 1
    CABLE_DETECT = 2
    EV_CONNECTED = 3
    READY = 4
    CHARGING = 5
    PAUSED = 6
    STOPPED = 7
    FAULT_HARD = 8


class EventType(Enum):
    """Event type'ları"""

    CABLE_CONNECTED = "CABLE_CONNECTED"
    EV_CONNECTED = "EV_CONNECTED"
    CHARGE_READY = "CHARGE_READY"
    CHARGE_STARTED = "CHARGE_STARTED"
    CHARGE_PAUSED = "CHARGE_PAUSED"
    CHARGE_STOPPED = "CHARGE_STOPPED"
    CHARGE_START_REQUESTED = "CHARGE_START_REQUESTED"
    CABLE_DISCONNECTED = "CABLE_DISCONNECTED"
    FAULT_DETECTED = "FAULT_DETECTED"
    STATE_CHANGED = "STATE_CHANGED"
