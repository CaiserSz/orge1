"""
OCPP 1.6J Adapter (Phase-1)

Created: 2025-12-21 20:12
Last Modified: 2025-12-21 20:12
Version: 0.1.0
Description:
  OCPP 1.6J (v16) station adapter used as a fallback transport for Phase-1.
  This module is intentionally importable from `ocpp/main.py` without relying on
  `ocpp.*` package imports (to avoid python-ocpp name shadowing issues).
"""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from typing import Any

import websockets
from states import StationIdentity, basic_auth_header, ssl_if_needed, utc_now_iso


class Ocpp16Adapter:
    """OCPP 1.6J (v16) station adapter (fallback). Phase-1 keeps it minimal."""

    def __init__(self, cfg: Any):
        self.cfg = cfg
        self.identity = StationIdentity(
            station_name=cfg.station_name,
            vendor_name=cfg.vendor_name,
            model=cfg.model,
            firmware_version="ocpp-phase1",
        )

    async def run(self) -> None:
        from ocpp.v16 import ChargePoint, call

        url = self.cfg.ocpp16_url
        headers = {
            "Authorization": basic_auth_header(
                self.cfg.station_name, self.cfg.station_password
            )
        }

        attempt = 0
        while True:
            try:
                async with websockets.connect(
                    url,
                    subprotocols=["ocpp1.6"],
                    additional_headers=headers,
                    ssl=ssl_if_needed(url),
                    open_timeout=10,
                    # Keepalive: helps prevent idle disconnects.
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=5,
                ) as ws:
                    cp = ChargePoint(self.cfg.station_name, ws)
                    runner = asyncio.create_task(cp.start())
                    try:
                        boot = await cp.call(
                            call.BootNotification(
                                charge_point_model=self.identity.model,
                                charge_point_vendor=self.identity.vendor_name,
                            ),
                            suppress=False,
                            unique_id=str(uuid.uuid4()),
                        )
                        print(
                            f"[OCPP] v16 BootNotification status={boot.status} interval={boot.interval}"
                        )

                        await cp.call(
                            call.StatusNotification(
                                connector_id=1,
                                error_code="NoError",
                                status="Available",
                                timestamp=utc_now_iso(),
                            ),
                            suppress=False,
                            unique_id=str(uuid.uuid4()),
                        )
                        print("[OCPP] v16 StatusNotification(Available) sent")

                        hb_interval = int(
                            getattr(self.cfg, "heartbeat_override_seconds", 0) or 0
                        )
                        if hb_interval <= 0:
                            hb_interval = int(getattr(boot, "interval", None) or 300)
                        hb_interval = max(10, hb_interval)

                        if self.cfg.poc_mode:
                            print(
                                "[OCPP/PoC] OCPP 1.6J PoC not implemented yet "
                                "(Phase-1 priority is 2.0.1)."
                            )
                            return

                        if self.cfg.once_mode:
                            hb = await cp.call(
                                call.Heartbeat(),
                                suppress=False,
                                unique_id=str(uuid.uuid4()),
                            )
                            print(
                                f"[OCPP] v16 Heartbeat current_time={hb.current_time}"
                            )
                            return

                        print(f"[OCPP] v16 daemon heartbeat_interval={hb_interval}s")
                        while True:
                            await asyncio.sleep(hb_interval)
                            hb = await cp.call(
                                call.Heartbeat(),
                                suppress=False,
                                unique_id=str(uuid.uuid4()),
                            )
                            print(
                                f"[OCPP] v16 Heartbeat current_time={hb.current_time}"
                            )
                    finally:
                        runner.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await runner

                # Normal websocket close: reset attempt and reconnect.
                attempt = 0
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                attempt += 1
                code = getattr(e, "code", None)
                reason = getattr(e, "reason", None)
                extra = ""
                if code is not None or reason is not None:
                    extra = f" code={code!r} reason={reason!r}"
                print(
                    f"[OCPP] v16 reconnect attempt={attempt} "
                    f"error_type={type(e).__name__} error={e}{extra}"
                )
                await asyncio.sleep(min(30.0, float(2 ** max(0, attempt))))
