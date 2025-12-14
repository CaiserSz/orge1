"""
Mobile Charging Router
Created: 2025-12-13 03:15:00
Last Modified: 2025-12-13 23:06:00
Version: 1.2.2
Description: Mobile uygulamalar için şarj durumu ve geçmiş oturum API'leri.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from api.alerting import get_alert_manager
from api.cache import CacheInvalidator, cache_response, invalidate_cache
from api.event_detector import ESP32State
from api.logging_config import system_logger
from api.meter import get_meter
from api.models import APIResponse
from api.routers.dependencies import get_bridge
from api.services.mobile_meter import (
    build_device_block,
    build_measurements,
    build_trend_block,
    collect_alerts,
    collect_meter_snapshot,
)
from api.services.mobile_sessions import (
    build_session_block,
    filter_sessions_by_date,
    now_iso,
    parse_datetime,
    serialize_session_detail,
    serialize_session_summary,
)
from api.session import SessionStatus, get_session_manager
from api.station_info import get_station_info
from esp32.bridge import ESP32Bridge

router = APIRouter(prefix="/api/mobile", tags=["Mobile"])

MAX_SESSION_FETCH = 500


@router.get("/charging/current")
@cache_response(ttl=5, key_prefix="mobile_charging_current")
async def get_mobile_charging_state(
    request: Request,
    bridge: ESP32Bridge = Depends(get_bridge),
) -> APIResponse:
    """Mobil uygulama için aktif şarj durumu payload'u."""
    try:
        station_info = get_station_info() or {}
        meter_snapshot = collect_meter_snapshot(get_meter)

        session_manager = get_session_manager()
        current_session = session_manager.get_current_session()

        # Ghost ACTIVE session temizliği (ESP32 IDLE + kablo yokken ACTIVE kalmamalı)
        try:
            status_data = bridge.get_status() or {}
            state = status_data.get("STATE")
            cable = status_data.get("CABLE")
            if (
                current_session
                and current_session.get("status") == SessionStatus.ACTIVE.value
                and state == ESP32State.IDLE.value
                and cable == 0
            ):
                session_id = current_session.get("session_id")
                if session_id:
                    now = datetime.now()
                    # DB'yi güncelle + memory'i temizle
                    try:
                        session_manager.db.update_session(
                            session_id=session_id,
                            end_time=now,
                            end_state=int(state),
                            status=SessionStatus.CANCELLED.value,
                        )
                    except Exception as exc:
                        system_logger.warning(
                            f"Ghost session auto-cancel failed: {exc}",
                            extra={"session_id": session_id},
                        )
                    try:
                        with session_manager.sessions_lock:
                            if (
                                session_manager.current_session
                                and session_manager.current_session.session_id
                                == session_id
                            ):
                                session_manager.current_session = None
                    except Exception:
                        pass

                    current_session = None
                    CacheInvalidator.invalidate_session()
                    invalidate_cache("mobile_charging_current:*")
                    invalidate_cache("mobile_sessions:*")
        except Exception:
            # Non-critical; normal akış devam eder
            pass

        measurements = build_measurements(meter_snapshot.get("reading"))
        session_block = build_session_block(
            current_session=current_session,
            station_info=station_info,
            measurements=measurements,
        )
        trend_block = build_trend_block(
            session_manager,
            measurements,
            max_fetch=MAX_SESSION_FETCH,
        )
        alerts_block = collect_alerts(get_alert_manager)

        data = {
            "device": build_device_block(station_info, meter_snapshot),
            "session": session_block,
            "measurements": measurements,
            "trend": trend_block,
            "alerts": alerts_block,
            "timestamp": now_iso(),
        }

        return APIResponse(success=True, message="Aktif şarj durumu alındı", data=data)
    except HTTPException:
        raise
    except Exception as exc:
        system_logger.error("Mobile charging state error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Mobil şarj durumu alınamadı",
        ) from exc


@router.get("/charging/sessions")
@cache_response(
    ttl=30,
    key_prefix="mobile_sessions",
    exclude_query_params=["offset", "from", "to", "user_id"],
)
async def list_mobile_sessions(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Session durumu filtresi (ACTIVE, COMPLETED, CANCELLED, FAULTED)",
    ),
    start_date: Optional[str] = Query(
        None, alias="from", description="ISO8601 formatında başlangıç tarihi"
    ),
    end_date: Optional[str] = Query(
        None, alias="to", description="ISO8601 formatında bitiş tarihi"
    ),
    user_id: Optional[str] = Query(
        None, description="Belirli bir kullanıcıya ait oturumları filtreler"
    ),
) -> APIResponse:
    """Mobil uygulama için geçmiş şarj oturumlarını döndür."""
    try:
        session_manager = get_session_manager()
        meter_snapshot = collect_meter_snapshot(get_meter)
        measurements = build_measurements(meter_snapshot.get("reading"))

        status_enum = None
        if status_filter:
            try:
                status_enum = SessionStatus(status_filter.upper())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Geçersiz status parametresi",
                ) from None

        raw_sessions = session_manager.get_sessions(
            limit=MAX_SESSION_FETCH,
            offset=0,
            status=status_enum,
            user_id=user_id,
        )

        filtered = filter_sessions_by_date(
            raw_sessions,
            start_date=parse_datetime(start_date),
            end_date=parse_datetime(end_date),
        )

        total_count = len(filtered)
        window = filtered[offset : offset + limit]

        price_per_kwh = (get_station_info() or {}).get("price_per_kwh")
        live_energy_import_kwh = (
            (measurements or {}).get("energy_kwh", {}).get("import")
            if measurements
            else None
        )
        items = [
            serialize_session_summary(
                s, price_per_kwh, live_energy_import_kwh=live_energy_import_kwh
            )
            for s in window
        ]

        return APIResponse(
            success=True,
            message="Oturum listesi alındı",
            data={
                "sessions": items,
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "total_count": total_count,
                    "has_more": (offset + limit) < total_count,
                },
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        system_logger.error("Mobile sessions list error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Oturum listesi alınamadı",
        ) from exc


@router.get("/charging/sessions/{session_id}")
@cache_response(ttl=60, key_prefix="mobile_session_detail")
async def get_mobile_session_detail(session_id: str) -> APIResponse:
    """Belirli bir şarj oturumunun ayrıntılı özetini döndür."""
    try:
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session bulunamadı: {session_id}",
            )

        station_info = get_station_info() or {}
        meter_snapshot = collect_meter_snapshot(get_meter)
        measurements = build_measurements(meter_snapshot.get("reading"))
        detail = serialize_session_detail(
            session, station_info, measurements=measurements
        )
        return APIResponse(success=True, message="Oturum detayları alındı", data=detail)
    except HTTPException:
        raise
    except Exception as exc:
        system_logger.error("Mobile session detail error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Oturum bilgisi alınamadı",
        ) from exc
