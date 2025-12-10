"""
Custom API Exceptions
Created: 2025-12-10
Last Modified: 2025-12-10
Version: 1.0.0
Description: Custom exception classes for API error handling
"""

from typing import Optional


class APIException(Exception):
    """Base API exception"""
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    message: str = "Internal server error"

    def __init__(self, message: Optional[str] = None, error_code: Optional[str] = None):
        self.message = message or self.message
        self.error_code = error_code or self.error_code
        super().__init__(self.message)


class ESP32ConnectionError(APIException):
    """ESP32 bağlantı hatası"""
    status_code = 503
    error_code = "ESP32_CONNECTION_ERROR"
    message = "ESP32 bağlantısı yok"

    def __init__(self, message: Optional[str] = None):
        super().__init__(message or self.message)


class InvalidStateError(APIException):
    """Geçersiz durum hatası"""
    status_code = 400
    error_code = "INVALID_STATE"
    message = "Geçersiz durum"

    def __init__(self, message: Optional[str] = None, current_state: Optional[str] = None):
        if current_state:
            self.message = f"{self.message}: {current_state}"
        super().__init__(message or self.message)


class CommandSendError(APIException):
    """Komut gönderme hatası"""
    status_code = 504
    error_code = "COMMAND_SEND_ERROR"
    message = "ESP32'ye komut gönderilemedi"

    def __init__(self, message: Optional[str] = None):
        super().__init__(message or self.message)


class ValidationError(APIException):
    """Validasyon hatası"""
    status_code = 400
    error_code = "VALIDATION_ERROR"
    message = "Geçersiz istek"

    def __init__(self, message: Optional[str] = None):
        super().__init__(message or self.message)


class AuthorizationError(APIException):
    """Yetkilendirme hatası"""
    status_code = 401
    error_code = "AUTHORIZATION_ERROR"
    message = "Yetkilendirme hatası"

    def __init__(self, message: Optional[str] = None):
        super().__init__(message or self.message)

