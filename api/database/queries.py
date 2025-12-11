"""
Database Queries Aggregate Module
Created: 2025-12-10 21:09:49
Last Modified: 2025-12-10 21:09:49
Version: 2.0.0
Description: Query mixin bileşenlerini birleştiren agregasyon modülü.
"""

from api.database.event_queries import EventQueryMixin
from api.database.maintenance_queries import MaintenanceQueryMixin
from api.database.session_queries import SessionQueryMixin


class DatabaseQueryMixin(SessionQueryMixin, EventQueryMixin, MaintenanceQueryMixin):
    """Database sınıfı için tüm query mixin'lerini birleştirir."""

    pass
