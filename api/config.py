"""
Configuration Management Module
Created: 2025-12-10 15:50:00
Last Modified: 2025-12-22 06:23:57
Version: 1.0.2
Description: Merkezi configuration management - Environment variable yönetimi ve validation
"""

import os
import sys
from pathlib import Path
from typing import List, Optional

from api.logging_config import system_logger


class Config:
    """Merkezi configuration yönetimi (env load + validation)."""

    # API Configuration
    SECRET_API_KEY: Optional[str] = None
    TEST_API_USER_ID: Optional[str] = None
    DEBUG: bool = False

    # CORS Configuration
    CORS_ALLOWED_ORIGINS: str = "*"
    CORS_ALLOWED_METHODS: str = "GET,POST,PUT,DELETE,OPTIONS"
    CORS_ALLOWED_HEADERS: str = "Content-Type,Authorization,X-API-Key"

    # Cache Configuration
    CACHE_BACKEND: str = "memory"  # memory, redis
    CACHE_TTL: int = 300  # 5 dakika (saniye)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Rate Limiting Configuration
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_IP: str = "60/minute"
    RATE_LIMIT_API_KEY: str = "200/minute"
    RATE_LIMIT_CHARGE: str = "10/minute"
    RATE_LIMIT_STATUS: str = "30/minute"

    # Database Configuration
    DATABASE_PATH: Optional[str] = None  # None ise varsayılan kullanılır

    # ESP32 Configuration
    ESP32_PORT: Optional[str] = None  # None ise otomatik bulunur
    ESP32_BAUDRATE: int = 115200

    # Meter Configuration
    # Not: Varsayılan olarak ABB (Modbus/RS485) kullanılır. Fiziksel meter yoksa sistem çalışmaya devam eder.
    METER_TYPE: str = "abb"  # mock, abb, acrel
    METER_PORT: str = "/dev/ttyAMA5"
    METER_BAUDRATE: int = 2400
    METER_SLAVE_ID: int = 1
    METER_TIMEOUT: float = 1.0
    METER_AUTO_CONNECT: bool = True

    # Charging state validation (PAUSED -> CHARGING "resume" doğrulama)
    # Not: Bazı araçlar "paused" UI durumundayken pilot/state kısa süreli CHARGING'e dönebiliyor.
    # Bu durumda gerçek enerji akışı (meter power) üzerinden doğrulama yapılmadan "resume" kabul edilmemelidir.
    RESUME_VALIDATION_ENABLED: bool = True
    RESUME_MIN_POWER_KW: float = 1.0
    RESUME_DEBOUNCE_SECONDS: float = 10.0
    RESUME_SAMPLE_INTERVAL_SECONDS: float = 1.0
    RESUME_REQUIRED_CONSECUTIVE_SAMPLES: int = 3
    RESUME_SUPPRESS_COOLDOWN_SECONDS: float = 30.0

    @classmethod
    def load(cls) -> None:
        """Environment variable'ları yükle ve validate et."""

        def _env_bool(name: str, default: bool) -> bool:
            raw = os.getenv(name, "true" if default else "false")
            return str(raw).lower() == "true"

        def _env_int(name: str, default: int) -> int:
            raw = os.getenv(name, str(default))
            try:
                return int(raw)
            except ValueError:
                system_logger.warning(
                    f"Geçersiz {name} değeri: {os.getenv(name)}, varsayılan kullanılıyor: {default}"
                )
                return default

        def _env_float(name: str, default: float) -> float:
            raw = os.getenv(name, str(default))
            try:
                return float(raw)
            except ValueError:
                system_logger.warning(
                    f"Geçersiz {name}: {os.getenv(name)}, varsayılan kullanılıyor: {default}"
                )
                return default

        # API Configuration
        # SECRET_API_KEY veya X-API-Key environment variable'ından al
        # X-API-Key öncelikli (karışıklığı önlemek için)
        cls.SECRET_API_KEY = os.getenv("X-API-Key") or os.getenv("SECRET_API_KEY")
        cls.TEST_API_USER_ID = os.getenv("TEST_API_USER_ID")
        cls.DEBUG = _env_bool("DEBUG", False)

        # CORS Configuration
        cls.CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "*")
        cls.CORS_ALLOWED_METHODS = os.getenv(
            "CORS_ALLOWED_METHODS", "GET,POST,PUT,DELETE,OPTIONS"
        )
        cls.CORS_ALLOWED_HEADERS = os.getenv(
            "CORS_ALLOWED_HEADERS", "Content-Type,Authorization,X-API-Key"
        )

        # Cache Configuration
        cls.CACHE_BACKEND = os.getenv("CACHE_BACKEND", "memory").lower()
        cls.CACHE_TTL = _env_int("CACHE_TTL", 300)
        cls.REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        # Rate Limiting Configuration
        cls.RATE_LIMIT_ENABLED = _env_bool("RATE_LIMIT_ENABLED", True)
        cls.RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "100/minute")
        cls.RATE_LIMIT_IP = os.getenv("RATE_LIMIT_IP", "60/minute")
        cls.RATE_LIMIT_API_KEY = os.getenv("RATE_LIMIT_API_KEY", "200/minute")
        cls.RATE_LIMIT_CHARGE = os.getenv("RATE_LIMIT_CHARGE", "10/minute")
        cls.RATE_LIMIT_STATUS = os.getenv("RATE_LIMIT_STATUS", "30/minute")

        # Test ortamı otomatik tespiti (pytest çalışırken rate limit ve meter erişimi devre dışı)
        # Not: PYTEST_CURRENT_TEST her zaman import/collection aşamasında set olmayabilir.
        is_pytest = os.getenv("PYTEST_CURRENT_TEST") is not None or any(
            "pytest" in arg for arg in sys.argv
        )

        if is_pytest:
            cls.RATE_LIMIT_ENABLED = False

        # Ek test modu bayrağı: PYTEST_DISABLE_RATE_LIMIT=1|true ise her durumda kapat
        if os.getenv("PYTEST_DISABLE_RATE_LIMIT", "").lower() in ("1", "true", "yes"):
            cls.RATE_LIMIT_ENABLED = False

        # Database Configuration
        cls.DATABASE_PATH = os.getenv("DATABASE_PATH")

        # ESP32 Configuration
        cls.ESP32_PORT = os.getenv("ESP32_PORT")
        cls.ESP32_BAUDRATE = _env_int("ESP32_BAUDRATE", 115200)

        # Meter Configuration
        cls.METER_TYPE = os.getenv("METER_TYPE", "abb").lower()
        cls.METER_PORT = os.getenv("METER_PORT", "/dev/ttyAMA5")
        cls.METER_AUTO_CONNECT = _env_bool("METER_AUTO_CONNECT", True)
        cls.METER_BAUDRATE = _env_int("METER_BAUDRATE", 2400)
        cls.METER_SLAVE_ID = _env_int("METER_SLAVE_ID", 1)
        cls.METER_TIMEOUT = _env_float("METER_TIMEOUT", 1.0)

        # Resume validation configuration
        cls.RESUME_VALIDATION_ENABLED = _env_bool("RESUME_VALIDATION_ENABLED", True)
        cls.RESUME_MIN_POWER_KW = _env_float("RESUME_MIN_POWER_KW", 1.0)
        cls.RESUME_DEBOUNCE_SECONDS = _env_float("RESUME_DEBOUNCE_SECONDS", 10.0)
        cls.RESUME_SAMPLE_INTERVAL_SECONDS = _env_float(
            "RESUME_SAMPLE_INTERVAL_SECONDS", 1.0
        )
        cls.RESUME_REQUIRED_CONSECUTIVE_SAMPLES = _env_int(
            "RESUME_REQUIRED_CONSECUTIVE_SAMPLES", 3
        )
        cls.RESUME_SUPPRESS_COOLDOWN_SECONDS = _env_float(
            "RESUME_SUPPRESS_COOLDOWN_SECONDS", 30.0
        )

        # Pytest sırasında fiziksel meter erişimi denenmemeli
        if is_pytest:
            cls.METER_TYPE = "mock"

        # Validation
        cls.validate()

    @classmethod
    def validate(cls) -> None:
        """Configuration değerlerini validate et."""
        # Cache backend validation
        if cls.CACHE_BACKEND not in ("memory", "redis"):
            raise ValueError(
                f"Geçersiz CACHE_BACKEND: {cls.CACHE_BACKEND} (geçerli: memory, redis)"
            )

        # Cache TTL validation
        if cls.CACHE_TTL < 0:
            raise ValueError(
                f"Geçersiz CACHE_TTL: {cls.CACHE_TTL} (0 veya pozitif olmalı)"
            )

        # Rate limit format validation (basit kontrol)
        if cls.RATE_LIMIT_ENABLED:
            rate_limits = [
                cls.RATE_LIMIT_DEFAULT,
                cls.RATE_LIMIT_IP,
                cls.RATE_LIMIT_API_KEY,
                cls.RATE_LIMIT_CHARGE,
                cls.RATE_LIMIT_STATUS,
            ]
            for limit in rate_limits:
                if "/" not in limit:
                    raise ValueError(
                        f"Geçersiz rate limit formatı: {limit} (format: 'number/period', örn: '100/minute')"
                    )

        # ESP32 baudrate validation
        valid_baudrates = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]
        if cls.ESP32_BAUDRATE not in valid_baudrates:
            system_logger.warning(
                f"ESP32_BAUDRATE standart değil: {cls.ESP32_BAUDRATE} (standart: {valid_baudrates})"
            )

        # Meter validation (invalid config sistemin çalışmasını engellememeli)
        valid_meter_types = {"mock", "abb", "acrel"}
        if cls.METER_TYPE not in valid_meter_types:
            system_logger.warning(
                f"Geçersiz METER_TYPE: {cls.METER_TYPE} (geçerli: {sorted(valid_meter_types)}). 'mock' kullanılacak."
            )
            cls.METER_TYPE = "mock"

        if cls.METER_BAUDRATE <= 0:
            system_logger.warning(
                f"Geçersiz METER_BAUDRATE: {cls.METER_BAUDRATE}. Varsayılan 9600 kullanılacak."
            )
            cls.METER_BAUDRATE = 9600

        if cls.METER_SLAVE_ID <= 0 or cls.METER_SLAVE_ID > 247:
            system_logger.warning(
                f"Geçersiz METER_SLAVE_ID: {cls.METER_SLAVE_ID}. Varsayılan 1 kullanılacak."
            )
            cls.METER_SLAVE_ID = 1

        if cls.METER_TIMEOUT <= 0:
            system_logger.warning(
                f"Geçersiz METER_TIMEOUT: {cls.METER_TIMEOUT}. Varsayılan 1.0 kullanılacak."
            )
            cls.METER_TIMEOUT = 1.0

        # Resume validation bounds
        if cls.RESUME_MIN_POWER_KW < 0:
            system_logger.warning(
                f"Geçersiz RESUME_MIN_POWER_KW: {cls.RESUME_MIN_POWER_KW}. Varsayılan 1.0 kullanılacak."
            )
            cls.RESUME_MIN_POWER_KW = 1.0
        if cls.RESUME_DEBOUNCE_SECONDS < 0:
            system_logger.warning(
                f"Geçersiz RESUME_DEBOUNCE_SECONDS: {cls.RESUME_DEBOUNCE_SECONDS}. Varsayılan 10.0 kullanılacak."
            )
            cls.RESUME_DEBOUNCE_SECONDS = 10.0
        if cls.RESUME_SAMPLE_INTERVAL_SECONDS <= 0:
            system_logger.warning(
                f"Geçersiz RESUME_SAMPLE_INTERVAL_SECONDS: {cls.RESUME_SAMPLE_INTERVAL_SECONDS}. Varsayılan 1.0 kullanılacak."
            )
            cls.RESUME_SAMPLE_INTERVAL_SECONDS = 1.0
        if cls.RESUME_REQUIRED_CONSECUTIVE_SAMPLES <= 0:
            system_logger.warning(
                f"Geçersiz RESUME_REQUIRED_CONSECUTIVE_SAMPLES: {cls.RESUME_REQUIRED_CONSECUTIVE_SAMPLES}. Varsayılan 3 kullanılacak."
            )
            cls.RESUME_REQUIRED_CONSECUTIVE_SAMPLES = 3
        if cls.RESUME_SUPPRESS_COOLDOWN_SECONDS < 0:
            system_logger.warning(
                f"Geçersiz RESUME_SUPPRESS_COOLDOWN_SECONDS: {cls.RESUME_SUPPRESS_COOLDOWN_SECONDS}. Varsayılan 30.0 kullanılacak."
            )
            cls.RESUME_SUPPRESS_COOLDOWN_SECONDS = 30.0

    @classmethod
    def get_secret_api_key(cls) -> str:
        """SECRET_API_KEY'i al (yoksa ValueError)."""
        # Ortam değişkenlerini her çağrıda dikkate al:
        # - X-API-Key veya SECRET_API_KEY set edildiyse bunlar önceliklidir
        # - SECRET_API_KEY explicit olarak boş string ise bu bir hata olarak kabul edilir
        env_secret = os.getenv("SECRET_API_KEY")
        env_x_api = os.getenv("X-API-Key")

        # Explicit boş string → test senaryolarında hata bekleniyor
        if env_secret is not None and env_secret == "":
            raise ValueError("SECRET_API_KEY environment variable tanımlı değil")

        key = env_x_api or env_secret or cls.SECRET_API_KEY

        if not key:
            raise ValueError("SECRET_API_KEY environment variable tanımlı değil")

        # Config içindeki değeri güncel tut
        cls.SECRET_API_KEY = key
        return key

    @classmethod
    def get_user_id(cls) -> Optional[str]:
        """TEST_API_USER_ID'yi al."""
        return cls.TEST_API_USER_ID

    @classmethod
    def get_database_path(cls) -> str:
        """Database path'i al (yoksa varsayılan yaratılır)."""
        if cls.DATABASE_PATH:
            return cls.DATABASE_PATH

        # Varsayılan database yolu: data/sessions.db
        data_dir = Path(__file__).parent.parent / "data"
        data_dir.mkdir(exist_ok=True)
        return str(data_dir / "sessions.db")

    @classmethod
    def get_cors_origins(cls) -> List[str]:
        """CORS origins listesini al."""
        if cls.CORS_ALLOWED_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in cls.CORS_ALLOWED_ORIGINS.split(",")]

    @classmethod
    def get_cors_methods(cls) -> List[str]:
        """CORS methods listesini al."""
        return [method.strip() for method in cls.CORS_ALLOWED_METHODS.split(",")]

    @classmethod
    def get_cors_headers(cls) -> List[str]:
        """CORS headers listesini al."""
        return [header.strip() for header in cls.CORS_ALLOWED_HEADERS.split(",")]


# Global config instance
config = Config()

# Startup'ta configuration'ı yükle
config.load()
