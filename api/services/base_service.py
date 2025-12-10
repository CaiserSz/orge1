"""
Base Service
Created: 2025-12-10
Last Modified: 2025-12-10
Version: 1.0.0
Description: Base service class for common service operations
"""

import logging
from typing import Optional

from api.config import config
from api.logging_config import log_event
from esp32.bridge import ESP32Bridge


class BaseService:
    """
    Base service class for common service operations

    Tüm service'lerin ortak işlemlerini içerir:
    - Bridge connection validation
    - User ID management
    - Event logging helpers
    """

    def __init__(self, bridge: ESP32Bridge):
        """
        BaseService başlatıcı

        Args:
            bridge: ESP32Bridge instance
        """
        self.bridge = bridge

    def _ensure_connected(self) -> None:
        """
        Bridge bağlantısını kontrol et

        Raises:
            ValueError: Bridge bağlı değilse
        """
        if not self.bridge or not self.bridge.is_connected:
            raise ValueError("ESP32 bağlantısı yok")

    def _get_user_id(self, user_id: Optional[str] = None) -> Optional[str]:
        """
        User ID'yi al veya config'den yükle

        Args:
            user_id: Optional user ID (varsa kullanılır)

        Returns:
            User ID veya None
        """
        if not user_id:
            return config.get_user_id()
        return user_id

    def _log_event(
        self,
        event_type: str,
        event_data: dict,
        level: int = logging.INFO,
    ) -> None:
        """
        Event logging helper

        Args:
            event_type: Event type string
            event_data: Event data dictionary
            level: Logging level (default: INFO)
        """
        log_event(event_type, event_data, level)

