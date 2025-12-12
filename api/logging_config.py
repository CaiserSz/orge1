"""
Logging Configuration Module
Created: 2025-12-09 15:40:00
Last Modified: 2025-12-12 05:40:00
Version: 1.1.0
Description: Structured logging + context propagation for AC Charger API
"""

import contextvars
import json
import logging
import sys
import threading
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

# Log dosyaları için klasör
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Log dosya yolları
API_LOG_FILE = LOG_DIR / "api.log"
ESP32_LOG_FILE = LOG_DIR / "esp32.log"
SYSTEM_LOG_FILE = LOG_DIR / "system.log"
SESSION_LOG_FILE = LOG_DIR / "session.log"
INCIDENT_LOG_FILE = LOG_DIR / "incident.log"

# Log rotation ayarları
MAX_BYTES = 10 * 1024 * 1024  # 10MB
BACKUP_COUNT = 5  # 5 yedek dosya


class JSONFormatter(logging.Formatter):
    """
    JSON formatında log mesajları oluşturan formatter
    Thread-safe
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Log kaydını JSON formatına dönüştür

        Args:
            record: Log kaydı

        Returns:
            JSON formatında log mesajı
        """
        try:
            log_data: Dict[str, Any] = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            }

            # Aktif logging context (correlation_id, session_id, vb.)
            context_fields = get_logging_context()
            if context_fields:
                log_data.update(context_fields)

            # Exception bilgisi varsa ekle
            if record.exc_info:
                log_data["exception"] = self.formatException(record.exc_info)

            # Ekstra alanlar varsa ekle
            if hasattr(record, "extra_fields"):
                # Non-serializable objeleri string'e çevir
                safe_fields = {}
                for key, value in record.extra_fields.items():
                    try:
                        json.dumps(value)  # Test serialization
                        safe_fields[key] = value
                    except (TypeError, ValueError):
                        safe_fields[key] = str(value)
                log_data.update(safe_fields)

            return json.dumps(log_data, ensure_ascii=False)
        except Exception as e:
            # Fallback: basit JSON format
            return json.dumps(
                {
                    "timestamp": datetime.now().isoformat(),
                    "level": getattr(record, "levelname", "ERROR"),
                    "logger": getattr(record, "name", "unknown"),
                    "message": (
                        str(record.getMessage())
                        if hasattr(record, "getMessage")
                        else str(record)
                    ),
                    "error": f"JSON serialization failed: {e}",
                },
                ensure_ascii=False,
            )


def setup_logger(
    name: str,
    log_file: Path,
    level: int = logging.INFO,
    max_bytes: int = MAX_BYTES,
    backup_count: int = BACKUP_COUNT,
) -> logging.Logger:
    """
    Logger oluştur ve yapılandır

    Args:
        name: Logger adı
        log_file: Log dosyası yolu
        level: Log seviyesi
        max_bytes: Maksimum dosya boyutu (rotation için)
        backup_count: Yedek dosya sayısı

    Returns:
        Yapılandırılmış logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Zaten handler'lar varsa ekleme (duplicate önleme)
    if logger.handlers:
        return logger

    # JSON formatter
    json_formatter = JSONFormatter()

    # File handler (rotation ile)
    try:
        file_handler = RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(json_formatter)
        logger.addHandler(file_handler)
    except (OSError, PermissionError) as e:
        # Dosya yazma hatası - sadece console logging kullan
        logger.warning(f"File logging failed for {log_file}: {e}, using console only")

    # Console handler (geliştirme için)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    # Console için daha okunabilir format
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger


# Ana logger'lar
api_logger = setup_logger("api", API_LOG_FILE)
esp32_logger = setup_logger("esp32", ESP32_LOG_FILE)
system_logger = setup_logger("system", SYSTEM_LOG_FILE)
session_logger = setup_logger("session", SESSION_LOG_FILE)
incident_logger = setup_logger("incident", INCIDENT_LOG_FILE, level=logging.WARNING)

# ContextVar tabanlı logging context
_logging_context: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar(
    "logging_context", default={}
)


def get_logging_context() -> Dict[str, Any]:
    """Aktif logging context'inin kopyasını döndür."""
    ctx = _logging_context.get({})
    return dict(ctx) if ctx else {}


def push_logging_context(**kwargs: Any) -> contextvars.Token:
    """
    Logging context'ine alan ekle (ör. correlation_id, session_id).

    Returns:
        contextvars.Token: Reset için token
    """
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
