"""
Common Dependencies for API Routers
Created: 2025-12-10
Last Modified: 2025-12-10 02:20:00
Version: 1.0.0
Description: Common dependencies for API routers
"""

from fastapi import Depends

from esp32.bridge import ESP32Bridge, get_esp32_bridge


def get_bridge() -> ESP32Bridge:
    """
    ESP32 bridge instance'ı dependency injection için

    Returns:
        ESP32Bridge instance
    """
    return get_esp32_bridge()

