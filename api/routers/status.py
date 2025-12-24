"""
Status Router
Created: 2025-12-10
Last Modified: 2025-12-24 21:45:16
Version: 1.2.5
Description: Status and health check endpoints
"""

import json
from collections import deque
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from api.auth import verify_api_key
from api.cache import CacheInvalidator, cache_response
from api.event_detector import ESP32State, get_event_detector
from api.logging_setup import ESP32_LOG_FILE
from api.metrics import get_metrics_response, update_all_metrics
from api.models import APIResponse
from api.rate_limiting import api_key_rate_limit, status_rate_limit
from api.routers.dependencies import get_bridge
from api.services.health_service import build_health_response
from api.services.status_service import StatusService
from api.station_info import get_station_info
from esp32.bridge import ESP32Bridge

router = APIRouter(prefix="/api", tags=["Status"])


def _tail_lines(path, max_lines: int) -> list[str]:
    """Dosyanın son N satırını oku (en yeni satırlar)."""
    buf: deque[str] = deque(maxlen=max_lines)
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            buf.append(line.rstrip("\n"))
    return list(buf)


def _read_lines_from_cursor(
    path, cursor: int, max_lines: int
) -> tuple[list[str], int, bool]:
    """
    Verilen byte offset (cursor) sonrası satırları oku.

    Returns:
      - lines: okunan satırlar (max_lines ile sınırlı)
      - next_cursor: okuma sonrası yeni byte offset (sonraki çağrıda kullanılabilir)
      - has_more: dosyada okunmamış veri kaldı mı?
    """
    cursor = max(0, int(cursor))
    lines: list[str] = []

    with path.open("rb") as f:
        try:
            f.seek(cursor)
        except Exception:
            f.seek(0)
            cursor = 0

        while len(lines) < max_lines:
            bline = f.readline()
            if not bline:
                break
            line = bline.decode("utf-8", errors="replace").rstrip("\r\n")
            if line:
                lines.append(line)

        next_cursor = f.tell()

    size = int(path.stat().st_size)
    has_more = next_cursor < size
    return lines, next_cursor, has_more


@router.get("/health")
@cache_response(ttl=30, key_prefix="health")
async def health_check(request: Request, bridge: ESP32Bridge = Depends(get_bridge)):
    return build_health_response(bridge, get_bridge)


@router.get("/status")
@status_rate_limit()  # Status endpoint'leri için rate limit (30/dakika)
@cache_response(
    ttl=5, key_prefix="status"
)  # 5 saniye cache (ESP32 7.5 saniyede bir gönderiyor)
async def get_status(request: Request, bridge: ESP32Bridge = Depends(get_bridge)):
    """
    ESP32 durum bilgisini al

    ESP32'den son durum bilgisini döndürür.
    ESP32 her 7.5 saniyede bir otomatik olarak durum gönderir.

    Stale data kontrolü: 10 saniyeden eski veri None döndürülür ve yeni veri istenir.
    """
    # Service layer kullan
    StatusService(bridge)

    if not bridge or not bridge.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ESP32 bağlantısı yok",
        )

    # Önce cache'den kontrol et (stale data kontrolü ile)
    status_data = bridge.get_status(max_age_seconds=10.0)

    if not status_data:
        # Cache'de veri yok veya çok eski - yeni veri iste
        status_data = bridge.get_status_sync(timeout=2.0)

    if not status_data:
        # Bağlantı bu aşamada kopmuşsa 503 döndür (bağlantı hatası)
        if not bridge.is_connected:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="ESP32 bağlantısı yok",
            )

        # Bağlantı var ama status alınamıyorsa timeout olarak değerlendir
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="ESP32'den durum bilgisi alınamadı (timeout veya stale data)",
        )

    # IDLE + kablo yokken MAX değeri standart (station_info.max_current_amp, varsayılan 32A) olmalı.
    # Şarj bitip kablo çıkarıldıktan sonra kullanıcı ayarı (örn. 16A) otomatik resetlenir.
    try:
        state = status_data.get("STATE")
        cable = status_data.get("CABLE")
        current_max = status_data.get("MAX")
        station_info = get_station_info() or {}
        desired_max = int(station_info.get("max_current_amp") or 32)
        desired_max = max(6, min(32, desired_max))

        if (
            state == ESP32State.IDLE.value
            and cable == 0
            and current_max is not None
            and int(current_max) != desired_max
        ):
            if bridge.send_current_set(desired_max):
                status_data["MAX"] = desired_max
                CacheInvalidator.invalidate_status()
    except Exception:
        # Non-critical; status read akışını bozma
        pass

    # RL/LOCK telemetry açıklaması (firmware/hardware'a bağlı olabilir)
    try:
        rl_raw = status_data.get("RL")
        lock_raw = status_data.get("LOCK")
        rl_val = int(rl_raw) if rl_raw is not None else None
        lock_val = int(lock_raw) if lock_raw is not None else None

        telemetry = {
            "relay_feedback_raw": rl_val,
            "lock_raw": lock_val,
            "relay_feedback": (bool(rl_val) if rl_val is not None else None),
            "lock_engaged": (bool(lock_val) if lock_val is not None else None),
            "note": (
                "RL/LOCK alanları firmware ve donanım bağlantısına bağlıdır. "
                "Donanımda lock/relay feedback yoksa 0 görünmesi normal olabilir."
            ),
        }
        status_data["telemetry"] = telemetry

        warnings = []
        state_val = status_data.get("STATE")
        if state_val in (ESP32State.CHARGING.value, ESP32State.PAUSED.value):
            if rl_val == 0:
                warnings.append("relay_feedback_off_or_unavailable")
            if lock_val == 0:
                warnings.append("lock_feedback_off_or_unavailable")
        if warnings:
            status_data["warnings"] = warnings
    except Exception:
        # Non-critical; status read akışını bozma
        pass

    return APIResponse(
        success=True, message="Status retrieved successfully", data=status_data
    )


@router.get("/metrics")
async def metrics(bridge: ESP32Bridge = Depends(get_bridge)):
    """
    Prometheus metrics endpoint

    Prometheus tarafından scrape edilebilir metrics endpoint'i.
    Tüm sistem metriklerini Prometheus formatında döndürür.
    """
    event_detector = get_event_detector(get_bridge)
    update_all_metrics(bridge=bridge, event_detector=event_detector)
    return get_metrics_response()


@router.get("/logs/esp32")
@api_key_rate_limit()  # Log endpoint'i abuse edilmemeli; API key zorunlu + rate limit
def get_esp32_logs(
    request: Request,
    cursor: Optional[int] = Query(
        None,
        ge=0,
        description="Opsiyonel cursor (byte offset). Verilirse sadece bu offset sonrası eklenen satırlar döner.",
    ),
    lines: int = Query(200, ge=1, le=2000),
    direction: Optional[str] = Query(
        None,
        description="Opsiyonel filtre: rx veya tx",
    ),
    message_type: Optional[str] = Query(
        None,
        description="Opsiyonel filtre: status, ack, authorization, current_set, charge_stop, ...",
    ),
    fmt: str = Query(
        "json",
        description="Çıktı formatı: json veya raw",
    ),
    api_key: str = Depends(verify_api_key),
) -> APIResponse:
    """
    ESP32 structured loglarını oku (logs/esp32.log).

    Notlar:
    - Serial portu kullanan servisi durdurmaya gerek yoktur; okuma file log üzerinden yapılır.
    - Varsayılan çıktı JSON satırlarının parse edilmiş halidir (fmt=json).
    - fmt=raw ile ham satırlar döndürülür.
    - cursor verilirse: sadece cursor sonrası gelen yeni satırlar döner; response içindeki next_cursor
      ile polling yaparak "son eklenenleri sırayla" izleyebilirsin.
    """
    _ = api_key  # API key doğrulaması için dependency (kullanılmıyor)
    _ = request  # Rate limiting decorator için request argümanı gerekli (kullanılmıyor)

    fmt_norm = (fmt or "").strip().lower()
    if fmt_norm not in ("json", "raw"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="fmt parametresi 'json' veya 'raw' olmalıdır",
        )

    direction_norm = None
    if direction is not None:
        direction_norm = (direction or "").strip().lower()
        if direction_norm not in ("rx", "tx"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="direction parametresi 'rx' veya 'tx' olmalıdır",
            )

    message_type_norm = None
    if message_type is not None:
        message_type_norm = (message_type or "").strip().lower()
        if not message_type_norm:
            message_type_norm = None

    if not ESP32_LOG_FILE.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ESP32 log dosyası bulunamadı (logs/esp32.log)",
        )

    file_size = int(ESP32_LOG_FILE.stat().st_size)
    cursor_reset = False
    has_more = False
    mode = "tail"

    if cursor is not None and int(cursor) > file_size:
        # Cursor artık geçerli değil (log rotate/truncate). Güvenli fallback: tail mode.
        cursor_reset = True
        cursor = None

    if cursor is None:
        raw_lines = _tail_lines(ESP32_LOG_FILE, max_lines=lines)
        next_cursor = file_size
    else:
        raw_lines, next_cursor, has_more = _read_lines_from_cursor(
            ESP32_LOG_FILE, cursor=int(cursor), max_lines=lines
        )
        mode = "cursor"

    # JSON line parse + opsiyonel filtreleme
    items: list[dict[str, Any]] = []
    for raw in raw_lines:
        parsed: Optional[dict[str, Any]] = None
        parse_error: Optional[str] = None
        try:
            loaded = json.loads(raw)
            if isinstance(loaded, dict):
                parsed = loaded
            else:
                parse_error = "parsed_json_not_object"
        except Exception as exc:
            parse_error = f"{type(exc).__name__}: {exc}"

        items.append({"raw": raw, "parsed": parsed, "parse_error": parse_error})

    def _match(item: dict[str, Any]) -> bool:
        if direction_norm is None and message_type_norm is None:
            return True
        parsed_item = item.get("parsed")
        if not isinstance(parsed_item, dict):
            return False
        if direction_norm is not None:
            if (str(parsed_item.get("direction") or "").lower()) != direction_norm:
                return False
        if message_type_norm is not None:
            if (
                str(parsed_item.get("message_type") or "").lower()
            ) != message_type_norm:
                return False
        return True

    filtered = [it for it in items if _match(it)]

    if fmt_norm == "raw":
        entries: list[Any] = [it["raw"] for it in filtered]
    else:
        entries = []
        for it in filtered:
            if isinstance(it.get("parsed"), dict):
                entries.append(it["parsed"])
            else:
                entries.append(
                    {"raw": it.get("raw", ""), "parse_error": it.get("parse_error")}
                )

    return APIResponse(
        success=True,
        message="ESP32 logları başarıyla okundu",
        data={
            "file": "esp32.log",
            "mode": mode,
            "cursor": cursor,
            "next_cursor": next_cursor,
            "cursor_reset": cursor_reset,
            "has_more": has_more,
            "file_size_bytes": file_size,
            "lines_requested": lines,
            "count": len(entries),
            "format": fmt_norm,
            "direction": direction_norm,
            "message_type": message_type_norm,
            "entries": entries,
        },
    )


@router.get("/alerts")
@cache_response(ttl=10, key_prefix="alerts")  # 10 saniye cache
async def get_alerts(bridge: ESP32Bridge = Depends(get_bridge)):
    """
    Active alerts endpoint

    Sistemdeki aktif alert'leri döndürür.
    """
    from api.alerting import get_alert_manager
    from api.metrics import update_all_metrics

    event_detector = get_event_detector(get_bridge)
    update_all_metrics(bridge=bridge, event_detector=event_detector)

    alert_manager = get_alert_manager()
    alert_manager.evaluate_all(bridge=bridge, event_detector=event_detector)

    active_alerts = alert_manager.get_active_alerts()

    alerts_data = [
        {
            "name": alert.name,
            "severity": alert.severity.value,
            "message": alert.message,
            "timestamp": alert.timestamp.isoformat(),
            "metadata": alert.metadata,
        }
        for alert in active_alerts
    ]

    return APIResponse(
        success=True,
        message=f"Active alerts: {len(active_alerts)}",
        data={
            "active_alerts": alerts_data,
            "count": len(active_alerts),
        },
    )
