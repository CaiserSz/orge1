"""
Status Service
Created: 2025-12-10 15:30:00
Last Modified: 2025-12-10 15:30:00
Version: 1.0.0
Description: Status business logic service layer
"""

from typing import Dict, Any, Optional

from esp32.bridge import ESP32Bridge


class StatusService:
    """
    Status business logic service

    Status işlemlerinin business logic'ini içerir.
    Router'lar sadece HTTP handling yapar, business logic burada.
    """

    def __init__(self, bridge: ESP32Bridge):
        """
        StatusService başlatıcı

        Args:
            bridge: ESP32Bridge instance
        """
        self.bridge = bridge

    def get_status(self) -> Optional[Dict[str, Any]]:
        """
        ESP32 durum bilgisini al

        Returns:
            Status dict veya None
        """
        if not self.bridge or not self.bridge.is_connected:
            return None

        return self.bridge.get_status()
