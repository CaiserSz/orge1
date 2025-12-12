"""
Test Router
Created: 2025-12-10
Last Modified: 2025-12-12 01:08:00
Version: 1.0.1
Description: Test endpoints
"""

import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse, FileResponse, Response

from api.config import config

router = APIRouter(tags=["Test"])


@router.get("/api/test/key")
async def get_test_api_key():
    """
    Test sayfası için API key'i döndürür

    NOT:
    - Bu endpoint test sayfası için gereklidir.
    - Production ortamında güvenlik nedeniyle kapalıdır (404 döndürür).
    """
    # Production ortamında test endpoint'ini kapat
    if os.getenv("ENVIRONMENT", "").lower() == "production":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )

    # Test sayfası için API key gerekli - Ngrok üzerinden erişim için aktif
    try:
        api_key = config.get_secret_api_key()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key not configured",
        )

    return {
        "api_key": api_key,
        "user_id": config.get_user_id() or "",
        "note": "This endpoint is for testing purposes only.",
    }


@router.get("/test", response_class=HTMLResponse)
async def api_test_page():
    """
    API test sayfası

    Dışarıdan API'leri test etmek için web arayüzü
    """
    test_page_path = Path(__file__).parent.parent.parent / "api_test.html"
    if test_page_path.exists():
        # Tarayıcı/Ngrok cache kaynaklı "eski JS" problemlerini engelle
        headers = {
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        }
        return FileResponse(test_page_path, headers=headers)
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Test page not found"
        )


@router.get("/favicon.ico")
async def favicon():
    """Avoid noisy 404 in browser console for favicon requests."""
    return Response(status_code=204)
