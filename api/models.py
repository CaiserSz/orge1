"""
API Data Models
Created: 2025-12-08
Last Modified: 2025-12-08
Version: 1.0.0
Description: API için veri modelleri
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class StationInfo(BaseModel):
    """Şarj istasyonu bilgileri modeli"""
    station_id: str = Field(..., description="İstasyon ID (benzersiz)")
    name: str = Field(..., description="İstasyon adı")
    location: Optional[str] = Field(None, description="Konum bilgisi")
    address: Optional[str] = Field(None, description="Adres")
    max_power_kw: Optional[float] = Field(None, ge=0, description="Maksimum güç (kW)")
    connector_type: Optional[str] = Field(None, description="Bağlantı tipi (Type2, CCS, CHAdeMO, vb.)")
    max_current_amp: Optional[int] = Field(None, ge=6, le=32, description="Maksimum akım (6-32A)")
    status: Optional[str] = Field("active", description="Durum (active, inactive, maintenance)")
    description: Optional[str] = Field(None, description="Açıklama")
    latitude: Optional[float] = Field(None, description="Enlem")
    longitude: Optional[float] = Field(None, description="Boylam")
    created_at: Optional[str] = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: Optional[str] = Field(default_factory=lambda: datetime.now().isoformat())


class StationUpdate(BaseModel):
    """Şarj istasyonu güncelleme modeli"""
    name: Optional[str] = None
    location: Optional[str] = None
    address: Optional[str] = None
    max_power_kw: Optional[float] = Field(None, ge=0)
    connector_type: Optional[str] = None
    max_current_amp: Optional[int] = Field(None, ge=6, le=32)
    status: Optional[str] = None
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

