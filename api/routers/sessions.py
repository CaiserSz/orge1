"""
Session API Router
Created: 2025-12-10 03:15:00
Last Modified: 2025-12-10 03:15:00
Version: 1.0.0
Description: Session yönetimi için REST API endpoint'leri
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from api.cache import cache_response
from api.logging_config import system_logger
from api.session import SessionStatus, get_session_manager

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])


@router.get("/current")
@cache_response(ttl=10, key_prefix="session_current")  # 10 saniye cache
async def get_current_session():
    """
    Aktif session'ı döndür

    Returns:
        Aktif session dict'i veya null
    """
    try:
        session_manager = get_session_manager()
        current_session = session_manager.get_current_session()

        if current_session:
            return {"success": True, "session": current_session}
        else:
            return {"success": True, "session": None, "message": "Aktif session yok"}
    except Exception as e:
        system_logger.error(f"Current session get error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Session bilgisi alınamadı: {str(e)}",
        )


@router.get("/users/{user_id}/current")
@cache_response(ttl=10, key_prefix="user_current_session")  # 10 saniye cache
async def get_user_current_session(user_id: str):
    """
    Belirli bir kullanıcının aktif session'ını döndür

    Args:
        user_id: User ID

    Returns:
        Aktif session dict'i veya null
    """
    try:
        session_manager = get_session_manager()
        current_session = session_manager.get_current_session()

        # Aktif session varsa ve user_id eşleşiyorsa döndür
        if current_session and current_session.get("user_id") == user_id:
            return {"success": True, "session": current_session}
        else:
            return {
                "success": True,
                "session": None,
                "message": f"User {user_id} için aktif session yok",
            }
    except Exception as e:
        system_logger.error(f"User current session get error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Session bilgisi alınamadı: {str(e)}",
        )


@router.get("/{session_id}")
@cache_response(
    ttl=300, key_prefix="session_detail"
)  # 5 dakika cache (session detayları nadiren değişir)
async def get_session(session_id: str):
    """
    Belirli bir session'ı döndür

    Args:
        session_id: Session UUID

    Returns:
        Session dict'i
    """
    try:
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)

        if session:
            return {"success": True, "session": session}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session bulunamadı: {session_id}",
            )
    except HTTPException:
        raise
    except Exception as e:
        system_logger.error(f"Session get error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Session bilgisi alınamadı: {str(e)}",
        )


@router.get("/{session_id}/metrics")
@cache_response(ttl=60, key_prefix="session_metrics")  # 1 dakika cache
async def get_session_metrics(session_id: str):
    """
    Belirli bir session'ın metriklerini döndür

    Args:
        session_id: Session UUID

    Returns:
        Session metrikleri dict'i
    """
    try:
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session bulunamadı: {session_id}",
            )

        # Metrikleri session dict'inden çıkar
        metrics = {
            "session_id": session_id,
            "duration_seconds": session.get("duration_seconds"),
            "charging_duration_seconds": session.get("charging_duration_seconds"),
            "idle_duration_seconds": session.get("idle_duration_seconds"),
            "total_energy_kwh": session.get("total_energy_kwh"),
            "start_energy_kwh": session.get("start_energy_kwh"),
            "end_energy_kwh": session.get("end_energy_kwh"),
            "max_power_kw": session.get("max_power_kw"),
            "avg_power_kw": session.get("avg_power_kw"),
            "min_power_kw": session.get("min_power_kw"),
            "max_current_a": session.get("max_current_a"),
            "avg_current_a": session.get("avg_current_a"),
            "min_current_a": session.get("min_current_a"),
            "set_current_a": session.get("set_current_a"),
            "max_voltage_v": session.get("max_voltage_v"),
            "avg_voltage_v": session.get("avg_voltage_v"),
            "min_voltage_v": session.get("min_voltage_v"),
            "event_count": session.get("event_count"),
        }

        return {"success": True, "metrics": metrics}
    except HTTPException:
        raise
    except Exception as e:
        system_logger.error(f"Session metrics get error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Session metrikleri alınamadı: {str(e)}",
        )


@router.get("")
@cache_response(
    ttl=30, key_prefix="sessions_list", exclude_query_params=["offset"]
)  # 30 saniye cache, offset hariç
async def get_sessions(
    limit: int = Query(
        100, ge=1, le=1000, description="Maksimum döndürülecek session sayısı"
    ),
    offset: int = Query(0, ge=0, description="Başlangıç offset'i"),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Session durumu filtresi (ACTIVE, COMPLETED, CANCELLED, FAULTED)",
    ),
    user_id: Optional[str] = Query(
        None, description="User ID filtresi (belirli bir kullanıcının session'ları)"
    ),
):
    """
    Session listesini döndür

    Args:
        limit: Maksimum döndürülecek session sayısı
        offset: Başlangıç offset'i
        status_filter: Session durumu filtresi
        user_id: User ID filtresi (belirli bir kullanıcının session'ları)

    Returns:
        Session listesi
    """
    try:
        session_manager = get_session_manager()

        # Status filtresi
        session_status = None
        if status_filter:
            try:
                session_status = SessionStatus(status_filter.upper())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Geçersiz status filtresi: {status_filter}. Geçerli değerler: ACTIVE, COMPLETED, CANCELLED, FAULTED",
                )

        sessions = session_manager.get_sessions(
            limit=limit, offset=offset, status=session_status, user_id=user_id
        )

        total_count = session_manager.get_session_count(
            status=session_status, user_id=user_id
        )

        return {
            "success": True,
            "sessions": sessions,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total_count,
        }
    except HTTPException:
        raise
    except Exception as e:
        system_logger.error(f"Sessions list get error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Session listesi alınamadı: {str(e)}",
        )


@router.get("/users/{user_id}/current")
@cache_response(ttl=10, key_prefix="user_current_session")  # 10 saniye cache
async def get_user_current_session(user_id: str):
    """
    Belirli bir kullanıcının aktif session'ını döndür

    Args:
        user_id: User ID

    Returns:
        Aktif session dict'i veya null
    """
    try:
        session_manager = get_session_manager()
        current_session = session_manager.get_current_session()

        # Aktif session varsa ve user_id eşleşiyorsa döndür
        if current_session and current_session.get("user_id") == user_id:
            return {"success": True, "session": current_session}
        else:
            return {
                "success": True,
                "session": None,
                "message": f"User {user_id} için aktif session yok",
            }
    except Exception as e:
        system_logger.error(f"User current session get error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Session bilgisi alınamadı: {str(e)}",
        )


@router.get("/users/{user_id}/sessions")
@cache_response(
    ttl=30, key_prefix="user_sessions", exclude_query_params=["offset"]
)  # 30 saniye cache, offset hariç
async def get_user_sessions(
    user_id: str,
    limit: int = Query(
        100, ge=1, le=1000, description="Maksimum döndürülecek session sayısı"
    ),
    offset: int = Query(0, ge=0, description="Başlangıç offset'i"),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Session durumu filtresi (ACTIVE, COMPLETED, CANCELLED, FAULTED)",
    ),
):
    """
    Belirli bir kullanıcının geçmiş session'larını döndür

    **Not:** Varsayılan olarak sadece geçmiş session'ları (ACTIVE hariç) döndürür.
    Aktif session'ı görmek için `/api/sessions/users/{user_id}/current` endpoint'ini kullanın.

    Args:
        user_id: User ID
        limit: Maksimum döndürülecek session sayısı
        offset: Başlangıç offset'i
        status_filter: Session durumu filtresi (ACTIVE, COMPLETED, CANCELLED, FAULTED)
                      Belirtilmezse ACTIVE hariç tüm geçmiş session'lar döndürülür

    Returns:
        User'ın geçmiş session listesi (ACTIVE hariç)
    """
    try:
        session_manager = get_session_manager()

        # Status filtresi
        # Varsayılan olarak ACTIVE hariç tüm session'ları göster (sadece geçmiş session'lar)
        session_status = None
        if status_filter:
            try:
                session_status = SessionStatus(status_filter.upper())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Geçersiz status filtresi: {status_filter}. Geçerli değerler: ACTIVE, COMPLETED, CANCELLED, FAULTED",
                )

        # Status filtresi yoksa ACTIVE hariç tüm session'ları al
        if not status_filter:
            # Tüm session'ları al (ACTIVE dahil)
            all_sessions = session_manager.get_sessions(
                limit=limit * 2,  # ACTIVE session'ları filtrelemek için daha fazla al
                offset=offset,
                status=None,
                user_id=user_id,
            )
            # ACTIVE session'ları filtrele
            sessions = [
                s for s in all_sessions if s.get("status") != SessionStatus.ACTIVE.value
            ]
            # Limit'e uygun şekilde kes
            sessions = sessions[:limit]

            # Total count: ACTIVE hariç tüm session sayısı
            total_count = session_manager.get_session_count(
                status=None, user_id=user_id
            )
            active_count = session_manager.get_session_count(
                status=SessionStatus.ACTIVE, user_id=user_id
            )
            total_count = total_count - active_count
        else:
            # Status filtresi varsa normal filtreleme
            sessions = session_manager.get_sessions(
                limit=limit, offset=offset, status=session_status, user_id=user_id
            )
            total_count = session_manager.get_session_count(
                status=session_status, user_id=user_id
            )

        return {
            "success": True,
            "user_id": user_id,
            "sessions": sessions,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total_count,
        }
    except HTTPException:
        raise
    except Exception as e:
        system_logger.error(f"User sessions get error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User session listesi alınamadı: {str(e)}",
        )


@router.get("/count/stats")
@cache_response(ttl=60, key_prefix="session_stats")  # 1 dakika cache
async def get_session_stats():
    """
    Session istatistiklerini döndür

    Returns:
        Session istatistikleri
    """
    try:
        session_manager = get_session_manager()

        total = session_manager.get_session_count()
        active = session_manager.get_session_count(SessionStatus.ACTIVE)
        completed = session_manager.get_session_count(SessionStatus.COMPLETED)
        cancelled = session_manager.get_session_count(SessionStatus.CANCELLED)
        faulted = session_manager.get_session_count(SessionStatus.FAULTED)

        return {
            "success": True,
            "stats": {
                "total": total,
                "active": active,
                "completed": completed,
                "cancelled": cancelled,
                "faulted": faulted,
            },
        }
    except Exception as e:
        system_logger.error(f"Session stats get error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Session istatistikleri alınamadı: {str(e)}",
        )
