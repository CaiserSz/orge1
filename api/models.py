"""
API Request/Response Models
Created: 2025-12-10
Last Modified: 2025-12-10 02:25:00
Version: 1.0.0
Description: Pydantic models for API requests and responses
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ChargeStartRequest(BaseModel):
    """Şarj başlatma isteği"""

    user_id: Optional[str] = Field(
        None,
        description="Kullanıcı ID (mobil uygulamadan gönderilir, session tracking için)",
    )


class ChargeStopRequest(BaseModel):
    """Şarj durdurma isteği"""

    user_id: Optional[str] = Field(
        None,
        description="Kullanıcı ID (mobil uygulamadan gönderilir, session tracking için)",
    )


class CurrentSetRequest(BaseModel):
    """Akım ayarlama isteği"""

    amperage: int = Field(
        ...,
        ge=6,
        le=32,
        description="Akım değeri (6-32 amper aralığında herhangi bir tam sayı)",
    )


class APIResponse(BaseModel):
    """Genel API yanıt modeli"""

    success: bool
    message: str
    data: Optional[Any] = None  # Dict, List veya başka herhangi bir tip olabilir
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
