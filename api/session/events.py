"""
Session Events Module
Created: 2025-12-10 20:40:00
Last Modified: 2025-12-13 18:00:00
Version: 1.1.1
Description: Session event handling metodları - Event operations mixin
"""

import os
import sys
from typing import Any, Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from api.event_detector import EventType
from api.logging_config import system_logger
from api.session.events_lifecycle import SessionLifecycleMixin


class SessionEventMixin(SessionLifecycleMixin):
    """
    Session event handling metodları mixin
    Bu mixin SessionManager sınıfına event handling metodlarını ekler
    """

    def _on_event(self, event_type: EventType, event_data: Dict[str, Any]):
        """
        Event Detector'dan gelen event'leri işle

        Args:
            event_type: Event type
            event_data: Event data dict'i
        """
        try:
            # charge_start event'ini dinle ve user_id'yi sakla
            if event_type == EventType.CHARGE_START_REQUESTED:
                user_id = event_data.get("user_id")
                if user_id:
                    with self.pending_user_id_lock:
                        self.pending_user_id = user_id

            # Session başlatma event'leri
            if event_type == EventType.CHARGE_STARTED:
                # Resume kontrolü: Eğer aktif session varsa ve son state PAUSED ise,
                # yeni session oluşturma, mevcut session'a event ekle
                if self.current_session:
                    # Son event'i kontrol et - CHARGE_PAUSED var mı?
                    last_event_type = None
                    if self.current_session.events:
                        last_event = self.current_session.events[-1]
                        last_event_type = last_event.get("event_type")

                    # Eğer son event CHARGE_PAUSED ise, bu resume durumudur
                    if last_event_type == EventType.CHARGE_PAUSED.value:
                        # Resume: Mevcut session'a CHARGE_STARTED event'i ekle
                        self.current_session.add_event(event_type, event_data)
                        # Metrikleri güncelle (real-time)
                        self._update_session_metrics(event_data)
                        # user_id'yi event_data'dan çıkar
                        user_id = event_data.get("user_id") or event_data.get(
                            "data", {}
                        ).get("user_id")
                        # Normalized event tablosuna kaydet
                        self._save_event_to_table(event_type, event_data, user_id)
                        # Database'e kaydet
                        self.db.update_session(
                            session_id=self.current_session.session_id,
                            events=self.current_session.events,
                            metadata=self.current_session.metadata,
                        )
                        system_logger.info(
                            f"Resume event'i mevcut session'a eklendi: {self.current_session.session_id}"
                        )
                        self._log_session_snapshot(
                            session_id=self.current_session.session_id,
                            event_label=event_type.value,
                            summary="Session resume event işlendi",
                            event_data=event_data,
                        )
                    else:
                        # Yeni session başlat (normal CHARGE_STARTED)
                        self._start_session(event_data)
                else:
                    # Aktif session yok, yeni session başlat
                    self._start_session(event_data)

            # Session sonlandırma event'leri
            elif event_type in [
                EventType.CHARGE_STOPPED,
                EventType.CABLE_DISCONNECTED,
            ]:
                self._end_session(event_type, event_data)

            # Aktif session'a event ekle
            elif self.current_session:
                self.current_session.add_event(event_type, event_data)
                # Metrikleri güncelle (real-time)
                self._update_session_metrics(event_data)
                # user_id'yi event_data'dan çıkar
                user_id = event_data.get("user_id") or event_data.get("data", {}).get(
                    "user_id"
                )
                # Normalized event tablosuna kaydet
                self._save_event_to_table(event_type, event_data, user_id)
                # Database'e kaydet (backward compatibility için events JSON'ı da koru)
                self.db.update_session(
                    session_id=self.current_session.session_id,
                    events=self.current_session.events,
                    metadata=self.current_session.metadata,
                )
                self._log_session_snapshot(
                    session_id=self.current_session.session_id,
                    event_label=event_type.value,
                    summary="Session event işlendi",
                    event_data=event_data,
                )

            # Fault durumunda session'ı fault olarak işaretle
            elif event_type == EventType.FAULT_DETECTED:
                self._handle_fault(event_data)

        except Exception as e:
            system_logger.error(
                f"Session manager event handling error: {e}", exc_info=True
            )
