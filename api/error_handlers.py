"""
Error Handlers
Created: 2025-12-10 16:00:00
Last Modified: 2025-12-10 16:00:00
Version: 1.0.0
Description: Common error handling decorators and utilities for API endpoints
"""

from functools import wraps
from typing import Callable
from fastapi import HTTPException, status

from api.exceptions import (
    ESP32ConnectionError,
    InvalidStateError,
    CommandSendError,
    ValidationError,
    APIException,
)


def handle_api_errors(func: Callable) -> Callable:
    """
    Common error handler decorator for API endpoints

    Bu decorator, API endpoint'lerinde tekrarlanan error handling pattern'ini
    merkezi bir yerde toplar. Tüm hataları uygun HTTP exception'lara dönüştürür.

    Usage:
        @router.post("/endpoint")
        @handle_api_errors
        async def my_endpoint(...):
            ...

    Raises:
        HTTPException: Uygun HTTP status code ile
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ESP32ConnectionError as e:
            # ESP32 bağlantı hataları → 503 Service Unavailable
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(e),
            )
        except InvalidStateError as e:
            # Geçersiz state hataları → 400 Bad Request veya 503 Service Unavailable
            # State None durumunda 503, geçersiz state durumunda 400
            error_msg = str(e)
            if (
                "STATE değeri alınamadı" in error_msg
                or "STATE değeri None" in error_msg
            ):
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=error_msg,
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_msg,
                )
        except CommandSendError as e:
            # Komut gönderme hataları → 504 Gateway Timeout
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=str(e),
            )
        except ValidationError as e:
            # Validasyon hataları → 400 Bad Request
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        except APIException as e:
            # Diğer API exception'ları → Custom status code
            raise HTTPException(
                status_code=e.status_code,
                detail=str(e),
            )
        except ValueError as e:
            # Business logic hataları (ValueError) → Uygun HTTP exception'a dönüştür
            error_msg = str(e)

            # ESP32 bağlantı hataları
            if (
                "ESP32 bağlantısı yok" in error_msg
                or "ESP32 durum bilgisi" in error_msg
                or "ESP32 STATE değeri" in error_msg
                or "STATE değeri alınamadı" in error_msg
            ):
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=error_msg,
                )

            # Geçersiz state hataları
            if (
                "Geçersiz STATE değeri" in error_msg
                or "State:" in error_msg
                or "Şarj başlatılamaz" in error_msg
                or "Akım ayarlanamaz" in error_msg
                or "State değişti" in error_msg
            ):
                # State None durumunda 503, geçersiz state durumunda 400
                if (
                    "STATE değeri alınamadı" in error_msg
                    or "STATE değeri None" in error_msg
                ):
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=error_msg,
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=error_msg,
                    )

            # Diğer ValueError'lar → 400 Bad Request
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg,
            )
        except Exception as e:
            # Beklenmeyen hatalar → 500 Internal Server Error
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error: {str(e)}",
            )

    return wrapper
