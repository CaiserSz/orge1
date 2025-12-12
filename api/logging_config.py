"""
Logging Configuration Module
Created: 2025-12-09 15:40:00
Last Modified: 2025-12-13 01:55:00
Version: 1.2.0
Description: Structured logging + context propagation for AC Charger API
"""

import contextvars
import logging
import sys
import threading
from typing import Any, Dict, Optional

from api.logging_setup import (
    API_LOG_FILE,
    ESP32_LOG_FILE,
    INCIDENT_LOG_FILE,
    JSONFormatter,
    SESSION_LOG_FILE,
    SYSTEM_LOG_FILE,
    setup_logger,
)

__all__ = [
    "api_logger",
    "esp32_logger",
    "system_logger",
    "session_logger",
    "incident_logger",
    "get_logging_context",
    "push_logging_context",
    "reset_logging_context",
    "clear_logging_context",
    "bind_session_context",
    "log_api_request",
    "log_esp32_message",
    "log_event",
    "thread_safe_log",
    "log_session_snapshot",
    "log_incident",
    "JSONFormatter",
    "setup_logger",
]

_logging_context: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar(
    "logging_context", default={}
)


def get_logging_context() -> Dict[str, Any]:
    """Aktif logging context'inin kopyasını döndür."""
    ctx = _logging_context.get({})
    return dict(ctx) if ctx else {}


def push_logging_context(**kwargs: Any) -> contextvars.Token:
    """Logging context'ine alan ekle (ör. correlation_id, session_id)."""
    ctx = get_logging_context()
    cleaned = {k: v for k, v in kwargs.items() if v is not None}
    ctx.update(cleaned)
    return _logging_context.set(ctx)


def reset_logging_context(token: contextvars.Token) -> None:
    """ContextVar'ı önceki değerine döndür."""
    _logging_context.reset(token)


def clear_logging_context() -> None:
    """Tüm logging context alanlarını temizle."""
    _logging_context.set({})


def bind_session_context(
    session_id: Optional[str] = None, **kwargs: Any
) -> contextvars.Token:
    """Session bazlı alanları context'e ekle ve token döndür."""
    cleaned = {"session_id": session_id}
    cleaned.update(kwargs)
    filtered = {k: v for k, v in cleaned.items() if v is not None}
    return push_logging_context(**filtered)


# Ana logger'lar
api_logger = setup_logger("api", API_LOG_FILE, context_getter=get_logging_context)
esp32_logger = setup_logger(
    "esp32", ESP32_LOG_FILE, context_getter=get_logging_context
)
system_logger = setup_logger(
    "system", SYSTEM_LOG_FILE, context_getter=get_logging_context
)
session_logger = setup_logger(
    "session", SESSION_LOG_FILE, context_getter=get_logging_context
)
incident_logger = setup_logger(
    "incident",
    INCIDENT_LOG_FILE,
    level=logging.WARNING,
    context_getter=get_logging_context,
)


def log_api_request(
    method: str,
    path: str,
    client_ip: Optional[str] = None,
    status_code: Optional[int] = None,
    response_time_ms: Optional[float] = None,
    user_id: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """
    API isteğini logla (Thread-safe)

    Args:
        method: HTTP metodu (GET, POST, vb.)
        path: İstek yolu
        client_ip: İstemci IP adresi
        status_code: HTTP durum kodu
        response_time_ms: Yanıt süresi (milisaniye)
        user_id: Kullanıcı ID (opsiyonel, audit trail için)
        **kwargs: Ekstra alanlar
    """
    try:
        with _log_lock:  # Thread-safe logging
            extra_fields = {
                "type": "api_request",
                "method": method,
                "path": path,
                **kwargs,
            }

            if client_ip:
                extra_fields["client_ip"] = client_ip
            if status_code:
                extra_fields["status_code"] = status_code
            if response_time_ms is not None:
                extra_fields["response_time_ms"] = response_time_ms
            if user_id:
                extra_fields["user_id"] = user_id

            # Log kaydına ekstra alanları ekle
            import inspect

            frame = inspect.currentframe().f_back
            record = logging.LogRecord(
                name=api_logger.name,
                level=logging.INFO,
                pathname=frame.f_code.co_filename if frame else "",
                lineno=frame.f_lineno if frame else 0,
                msg=f"{method} {path}",
                args=(),
                exc_info=None,
            )
            record.extra_fields = extra_fields
            api_logger.handle(record)
    except Exception as e:
        # Logging hatası API'yi etkilememeli
        # Fallback: basit console logging
        try:
            api_logger.error(f"Logging error in log_api_request: {e}", exc_info=True)
        except Exception:
            pass  # Son çare: sessizce geç


def log_esp32_message(
    message_type: str,
    direction: str,  # "tx" veya "rx"
    data: Optional[Any] = None,
    **kwargs: Any,
) -> None:
    """
    ESP32 mesajını logla (Thread-safe)

    Args:
        message_type: Mesaj tipi (status, command, error, vb.)
        direction: Mesaj yönü ("tx" veya "rx")
        data: Mesaj verisi
        **kwargs: Ekstra alanlar
    """
    try:
        with _log_lock:  # Thread-safe logging
            extra_fields = {
                "type": "esp32_message",
                "message_type": message_type,
                "direction": direction,
                **kwargs,
            }

            if data is not None:
                extra_fields["data"] = data

            import inspect

            frame = inspect.currentframe().f_back
            record = logging.LogRecord(
                name=esp32_logger.name,
                level=logging.INFO,
                pathname=frame.f_code.co_filename if frame else "",
                lineno=frame.f_lineno if frame else 0,
                msg=f"ESP32 {direction.upper()}: {message_type}",
                args=(),
                exc_info=None,
            )
            record.extra_fields = extra_fields
            esp32_logger.handle(record)
    except Exception as e:
        # Logging hatası uygulamayı etkilememeli
        try:
            esp32_logger.error(
                f"Logging error in log_esp32_message: {e}", exc_info=True
            )
        except Exception:
            pass  # Son çare: sessizce geç


def log_event(
    event_type: str,
    event_data: Optional[Dict[str, Any]] = None,
    level: int = logging.INFO,
    incident: bool = False,
    **kwargs: Any,
) -> None:
    """
    Genel event logla (Thread-safe)

    Args:
        event_type: Event tipi
        event_data: Event verisi
        level: Log seviyesi
        **kwargs: Ekstra alanlar
    """
    try:
        with _log_lock:  # Thread-safe logging
            extra_fields = {"type": "event", "event_type": event_type, **kwargs}

            if event_data:
                extra_fields["event_data"] = event_data

            import inspect

            frame = inspect.currentframe().f_back

            def _emit(logger: logging.Logger):
                record = logging.LogRecord(
                    name=logger.name,
                    level=level,
                    pathname=frame.f_code.co_filename if frame else "",
                    lineno=frame.f_lineno if frame else 0,
                    msg=f"Event: {event_type}",
                    args=(),
                    exc_info=None,
                )
                record.extra_fields = extra_fields
                logger.handle(record)

            _emit(system_logger)
            if incident:
                _emit(incident_logger)
    except Exception as e:
        # Logging hatası uygulamayı etkilememeli
        try:
            system_logger.error(f"Logging error in log_event: {e}", exc_info=True)
        except Exception:
            pass  # Son çare: sessizce geç


# Thread-safe logging için lock
_log_lock = threading.Lock()


def get_logger(name: str) -> logging.Logger:
    """
    Logger instance'ı al (convenience function)

    Args:
        name: Logger adı

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def thread_safe_log(
    logger: logging.Logger, level: int, message: str, **kwargs: Any
) -> None:
    """
    Thread-safe log yazma

    Args:
        logger: Logger instance
        level: Log seviyesi
        message: Log mesajı
        **kwargs: Ekstra alanlar
    """
    with _log_lock:
        if kwargs:
            record = logging.LogRecord(
                name=logger.name,
                level=level,
                pathname="",
                lineno=0,
                msg=message,
                args=(),
                exc_info=None,
            )
            record.extra_fields = kwargs
            logger.handle(record)
        else:
            logger.log(level, message)


def log_session_snapshot(
    session_id: str,
    event_type: str,
    summary: str,
    level: int = logging.INFO,
    **kwargs: Any,
) -> None:
    """
    Session özel log kaydı oluşturur (session.log). Opsiyonel ekstra alanları ekler.
    """
    with _log_lock:
        record = logging.LogRecord(
            name=session_logger.name,
            level=level,
            pathname="",
            lineno=0,
            msg=summary,
            args=(),
            exc_info=None,
        )
        record.extra_fields = {
            "session_id": session_id,
            "event_type": event_type,
            **kwargs,
        }
        session_logger.handle(record)


def log_incident(
    title: str,
    severity: str = "warning",
    description: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """
    Kritik incident'ları hem incident.log hem de system log'una yazar.
    """
    incident_payload = {
        "title": title,
        "severity": severity,
        "description": description,
        **kwargs,
    }
    log_event(
        event_type=f"INCIDENT:{title}",
        event_data=incident_payload,
        level=logging.WARNING,
        incident=True,
    )
