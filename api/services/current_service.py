"""
Current Service
Created: 2025-12-10 15:30:00
Last Modified: 2025-12-10
Version: 1.1.0
Description: Current control business logic service layer
"""

from datetime import datetime
from typing import Dict, Any, Optional
import hashlib

from api.logging_config import system_logger
from api.models import CurrentSetRequest
from api.cache import CacheInvalidator
from api.services.base_service import BaseService
from api.state_validation import (
    validate_state,
    check_state_for_current_set,
)


class CurrentService(BaseService):
    """
    Current control business logic service

    Current set işlemlerinin business logic'ini içerir.
    Router'lar sadece HTTP handling yapar, business logic burada.
    """

    def set_current(
        self,
        request_body: CurrentSetRequest,
        user_id: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Maksimum akım ayarlama business logic

        Args:
            request_body: Current set request body
            user_id: User ID (audit trail için, None ise config'den alınır)
            api_key: API key (audit trail için)

        Returns:
            Success response dict

        Raises:
            ValueError: Business logic hataları için
        """
        # Bridge bağlantısını kontrol et
        self._ensure_connected()

        # User ID'yi al (audit trail için)
        user_id = self._get_user_id(user_id)

        # Kritik işlemleri logla (akım ayarlama)
        if user_id:
            self._log_event(
                event_type="current_set",
                event_data={
                    "user_id": user_id,
                    "amperage": request_body.amperage,
                    "api_key_hash": (
                        hashlib.sha256(api_key.encode()).hexdigest()[:16]
                        if api_key
                        else None
                    ),
                    "timestamp": datetime.now().isoformat(),
                },
            )

        # Mevcut durumu kontrol et ve state validate et (STATE None durumunda devam edebilir)
        current_status = self.bridge.get_status()
        state, state_name = validate_state(
            current_status,
            endpoint="/api/maxcurrent",
            user_id=user_id,
            allow_none=True,  # STATE None durumunda akım ayarlama devam edebilir
        )

        # State None değilse ve şarj aktifse akım değiştirilemez
        if state is not None:
            check_state_for_current_set(state, state_name, "/api/maxcurrent", user_id)

        # Akım ayarlama komutu gönder
        success = self.bridge.send_current_set(request_body.amperage)

        if not success:
            error_msg = "Akım ayarlama komutu gönderilemedi"
            system_logger.error(
                f"Current set failed: {error_msg}",
                extra={
                    "endpoint": "/api/maxcurrent",
                    "user_id": user_id,
                    "amperage": request_body.amperage,
                    "error_type": "COMMAND_SEND_ERROR",
                },
            )
            raise ValueError(error_msg)

        # Status cache'ini invalidate et (current değişti)
        CacheInvalidator.invalidate_status()

        return {
            "success": True,
            "message": f"Maksimum akım {request_body.amperage}A olarak ayarlandı",
            "data": {"amperage": request_body.amperage, "command": "current_set"},
        }
