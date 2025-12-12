"""
Logging Setup Helpers
Created: 2025-12-13 01:50:00
Last Modified: 2025-12-13 01:50:00
Version: 1.0.0
Description: Logger oluşturma ve JSON formatter yardımcıları.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Callable, Dict, Optional

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

API_LOG_FILE = LOG_DIR / "api.log"
ESP32_LOG_FILE = LOG_DIR / "esp32.log"
SYSTEM_LOG_FILE = LOG_DIR / "system.log"
SESSION_LOG_FILE = LOG_DIR / "session.log"
INCIDENT_LOG_FILE = LOG_DIR / "incident.log"

MAX_BYTES = 10 * 1024 * 1024  # 10MB
BACKUP_COUNT = 5  # 5 backup files

__all__ = [
    "API_LOG_FILE",
    "ESP32_LOG_FILE",
    "SYSTEM_LOG_FILE",
    "SESSION_LOG_FILE",
    "INCIDENT_LOG_FILE",
    "MAX_BYTES",
    "BACKUP_COUNT",
    "JSONFormatter",
    "setup_logger",
]


class JSONFormatter(logging.Formatter):
    """JSON formatında log mesajları oluşturan formatter."""

    def __init__(
        self, context_getter: Optional[Callable[[], Dict[str, Any]]] = None
    ) -> None:
        super().__init__()
        self._context_getter = context_getter or (lambda: {})

    def format(self, record: logging.LogRecord) -> str:
        """Log kaydını JSON formatına dönüştür."""
        from datetime import datetime
        import json

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

            context_fields = self._context_getter() or {}
            if context_fields:
                log_data.update(context_fields)

            if record.exc_info:
                log_data["exception"] = self.formatException(record.exc_info)

            if hasattr(record, "extra_fields"):
                safe_fields = {}
                for key, value in record.extra_fields.items():
                    try:
                        json.dumps(value)
                        safe_fields[key] = value
                    except (TypeError, ValueError):
                        safe_fields[key] = str(value)
                log_data.update(safe_fields)

            return json.dumps(log_data, ensure_ascii=False)
        except Exception as exc:  # pragma: no cover - fallback path
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
                    "error": f"JSON serialization failed: {exc}",
                },
                ensure_ascii=False,
            )


def setup_logger(
    name: str,
    log_file: Path,
    level: int = logging.INFO,
    max_bytes: int = MAX_BYTES,
    backup_count: int = BACKUP_COUNT,
    context_getter: Optional[Callable[[], Dict[str, Any]]] = None,
) -> logging.Logger:
    """Logger oluştur ve yapılandır."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.handlers:
        return logger

    json_formatter = JSONFormatter(context_getter=context_getter)

    try:
        file_handler = RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(json_formatter)
        logger.addHandler(file_handler)
    except (OSError, PermissionError) as exc:
        logger.warning(f"File logging failed for {log_file}: {exc}, using console only")

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger

