"""
Test Router
Created: 2025-12-10
Last Modified: 2025-12-10 02:20:00
Version: 1.0.0
Description: Test endpoints
"""

import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse, FileResponse

router = APIRouter(tags=["Test"])


@router.get("/api/test/key")
async def get_test_api_key():
    """
    Test sayfası için API key'i döndürür

    NOT: Bu endpoint sadece test amaçlıdır. Production'da devre dışı bırakılmalıdır.
    """
    # Production'da bu endpoint'i devre dışı bırak
    environment = os.getenv("ENVIRONMENT", "production").lower()
    if environment == "production":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found"
        )

    # Test amaçlı - sadece development ortamında kullanılmalı
    api_key = os.getenv("SECRET_API_KEY", "")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key not configured"
        )

    return {
        "api_key": api_key,
        "user_id": os.getenv("TEST_API_USER_ID", ""),
        "note": "This endpoint is for testing purposes only. Disabled in production."
    }


@router.get("/test", response_class=HTMLResponse)
async def api_test_page():
    """
    API test sayfası

    Dışarıdan API'leri test etmek için web arayüzü
    """
    test_page_path = Path(__file__).parent.parent.parent / "api_test.html"
    if test_page_path.exists():
        return FileResponse(test_page_path)
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test page not found"
        )

