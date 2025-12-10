"""
State Validation Utilities
Created: 2025-12-10 16:00:00
Last Modified: 2025-12-10 16:00:00
Version: 1.0.0
Description: Common state validation utilities for ESP32 state management
"""

from typing import Dict, Any, Optional, Tuple
from api.event_detector import ESP32State
from api.exceptions import InvalidStateError, ESP32ConnectionError
from api.logging_config import system_logger


def validate_state(
    status_data: Optional[Dict[str, Any]],
    endpoint: str,
    user_id: Optional[str] = None,
    allow_none: bool = False,
) -> Tuple[int, str]:
    """
    ESP32 state validation helper function

    Bu fonksiyon, ESP32 state validation logic'ini merkezi bir yerde toplar.
    Tüm service'lerde tekrarlanan state validation kodunu azaltır.

    Args:
        status_data: ESP32 status data dictionary (None olabilir)
        endpoint: Endpoint adı (logging için)
        user_id: User ID (logging için, optional)
        allow_none: STATE None durumunda hata fırlatma (False) veya sadece warning (True)

    Returns:
        Tuple[state_value, state_name]: State değeri ve state adı

    Raises:
        InvalidStateError: Geçersiz state durumunda
        ESP32ConnectionError: Status data None ise ve allow_none=False ise
    """
    # Status data kontrolü
    if not status_data:
        if allow_none:
            # STATE None durumunda sadece warning logla (akım ayarlama gibi durumlar için)
            system_logger.warning(
                f"{endpoint}: STATE None, işlem devam ediyor",
                extra={
                    "endpoint": endpoint,
                    "user_id": user_id,
                    "error_type": "STATE_NONE_WARNING",
                },
            )
            return None, "UNKNOWN"
        else:
            # Status data yoksa hata fırlat
            error_msg = "ESP32 durum bilgisi alınamadı"
            system_logger.error(
                f"{endpoint} failed: {error_msg}",
                extra={
                    "endpoint": endpoint,
                    "user_id": user_id,
                    "error_type": "ESP32_STATUS_ERROR",
                },
            )
            raise ESP32ConnectionError(error_msg)

    # STATE değerini al ve None kontrolü yap
    state = status_data.get("STATE")
    if state is None:
        if allow_none:
            # STATE None durumunda sadece warning logla
            system_logger.warning(
                f"{endpoint}: STATE None, işlem devam ediyor",
                extra={
                    "endpoint": endpoint,
                    "user_id": user_id,
                    "status_data": status_data,
                },
            )
            return None, "UNKNOWN"
        else:
            # STATE None ise hata fırlat
            error_msg = "ESP32 STATE değeri alınamadı (None)"
            system_logger.error(
                f"{endpoint} failed: {error_msg}",
                extra={
                    "endpoint": endpoint,
                    "user_id": user_id,
                    "error_type": "STATE_NONE_ERROR",
                    "status_data": status_data,
                },
            )
            raise InvalidStateError(error_msg)

    # State değerini ESP32State enum ile kontrol et ve validate et
    try:
        esp32_state = ESP32State(state)
        state_name = esp32_state.name
    except ValueError:
        # Geçersiz state değeri (ESP32State enum'unda yok)
        state_name = f"UNKNOWN_{state}"
        error_msg = f"Geçersiz STATE değeri: {state} (beklenen: 0-8 arası)"
        system_logger.error(
            f"{endpoint} failed: {error_msg}",
            extra={
                "endpoint": endpoint,
                "user_id": user_id,
                "error_type": "INVALID_STATE_VALUE",
                "invalid_state": state,
                "status_data": status_data,
            },
        )
        raise InvalidStateError(error_msg)

    return state, state_name


def check_state_for_charge_start(
    state: int,
    state_name: str,
    endpoint: str,
    user_id: Optional[str] = None,
) -> None:
    """
    Charge start için state kontrolü

    Sadece EV_CONNECTED (state=3) durumunda authorization gönderilebilir.

    Args:
        state: State değeri
        state_name: State adı
        endpoint: Endpoint adı (logging için)
        user_id: User ID (logging için, optional)

    Raises:
        InvalidStateError: Geçersiz state durumunda
    """
    if state != ESP32State.EV_CONNECTED.value:
        # State'e göre hata mesajı oluştur
        if state == ESP32State.IDLE.value:
            detail = "Şarj başlatılamaz (State: IDLE). Kablo takılı değil."
        elif state == ESP32State.CABLE_DETECT.value:
            detail = "Şarj başlatılamaz (State: CABLE_DETECT). Araç bağlı değil."
        elif state == ESP32State.READY.value:
            detail = "Şarj başlatılamaz (State: READY). Authorization zaten verilmiş."
        elif state >= ESP32State.CHARGING.value:
            detail = f"Şarj başlatılamaz (State: {state_name}). Şarj zaten aktif veya hata durumunda."
        else:
            detail = f"Şarj başlatılamaz (State: {state_name}). Sadece EV_CONNECTED durumunda authorization gönderilebilir."

        system_logger.warning(
            f"Charge start rejected: {detail}",
            extra={
                "endpoint": endpoint,
                "user_id": user_id,
                "current_state": state,
                "state_name": state_name,
                "error_type": "INVALID_STATE",
            },
        )
        raise InvalidStateError(detail)


def check_state_for_current_set(
    state: Optional[int],
    state_name: str,
    endpoint: str,
    user_id: Optional[str] = None,
) -> None:
    """
    Current set için state kontrolü

    Şarj aktifken (state >= CHARGING) akım değiştirilemez.

    Args:
        state: State değeri (None olabilir)
        state_name: State adı
        endpoint: Endpoint adı (logging için)
        user_id: User ID (logging için, optional)

    Raises:
        InvalidStateError: Geçersiz state durumunda
    """
    # State None ise kontrol yapma (akım ayarlama devam edebilir)
    if state is None:
        return

    if state >= ESP32State.CHARGING.value:
        detail = f"Akım ayarlanamaz (State: {state_name}). Şarj aktifken akım değiştirilemez."
        system_logger.warning(
            f"Current set rejected: {detail}",
            extra={
                "endpoint": endpoint,
                "user_id": user_id,
                "current_state": state,
                "state_name": state_name,
                "error_type": "INVALID_STATE",
            },
        )
        raise InvalidStateError(detail)


def check_state_changed(
    initial_state: Optional[int],
    final_state: Optional[int],
    endpoint: str,
    user_id: Optional[str] = None,
) -> None:
    """
    State değişikliği kontrolü (race condition önlemi)

    Komut gönderilmeden önce state değişmiş mi kontrol eder.

    Args:
        initial_state: İlk state değeri (None olabilir)
        final_state: Son state değeri (None olabilir)
        endpoint: Endpoint adı (logging için)
        user_id: User ID (logging için, optional)

    Raises:
        InvalidStateError: State değişmişse
    """
    # Initial state None ise kontrol yapma
    if initial_state is None:
        return

    # Final state None ise kontrol yapma (state bilgisi yok)
    if final_state is None:
        return

    # State değişmişse hata fırlat
    if final_state != initial_state:
        try:
            final_state_name = ESP32State(final_state).name
        except ValueError:
            final_state_name = f"UNKNOWN_{final_state}"

        error_msg = f"State değişti, işlem yapılamaz (State: {final_state_name})"
        system_logger.warning(
            f"{endpoint} rejected: {error_msg}",
            extra={
                "endpoint": endpoint,
                "user_id": user_id,
                "initial_state": initial_state,
                "final_state": final_state,
                "error_type": "STATE_CHANGED",
            },
        )
        raise InvalidStateError(error_msg)
