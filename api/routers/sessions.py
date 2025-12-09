"""
Session API Router
Created: 2025-12-10 03:15:00
Last Modified: 2025-12-10 03:15:00
Version: 1.0.0
Description: Session yönetimi için REST API endpoint'leri
"""

from fastapi import APIRouter, HTTPException, Query, status
from typing import Optional
from api.session_manager import get_session_manager, SessionStatus
from api.logging_config import system_logger

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])


@router.get("/current")
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


@router.get("/{session_id}")
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


@router.get("")
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
):
    """
    Session listesini döndür

    Args:
        limit: Maksimum döndürülecek session sayısı
        offset: Başlangıç offset'i
        status_filter: Session durumu filtresi

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
            limit=limit, offset=offset, status=session_status
        )

        total_count = session_manager.get_session_count(status=session_status)

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


@router.get("/count/stats")
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
