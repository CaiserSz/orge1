"""
OCPP 1.6J Adapter (Phase-1)

Created: 2025-12-21 20:12
Last Modified: 2025-12-22 14:05
Version: 0.3.0
Description:
  OCPP 1.6J (v16) station adapter used as a fallback transport for Phase-1.
  This module is intentionally importable from `ocpp/main.py` without relying on
  `ocpp.*` package imports (to avoid python-ocpp name shadowing issues).
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import uuid
from typing import Any

import websockets
from states import StationIdentity, basic_auth_header, ssl_if_needed, utc_now_iso


class Ocpp16Adapter:
    """OCPP 1.6J (v16) station adapter (fallback). Phase-1 keeps it minimal."""

    def __init__(self, cfg: Any):
        self.cfg = cfg
        # Optional (non-secret) metadata for BootNotification.
        # Some CSMS setups may enforce stricter policy checks than just vendor/model.
        self._boot_serial_number = (os.getenv("OCPP_V16_SERIAL_NUMBER") or "").strip()
        self._boot_firmware_version = (
            os.getenv("OCPP_V16_FIRMWARE_VERSION") or ""
        ).strip()
        self.identity = StationIdentity(
            station_name=cfg.station_name,
            vendor_name=cfg.vendor_name,
            model=cfg.model,
            firmware_version="ocpp-phase1",
        )

    async def run(self) -> None:
        from ocpp.routing import on
        from ocpp.v16 import ChargePoint, call, call_result, enums

        url = self.cfg.ocpp16_url
        headers = {
            "Authorization": basic_auth_header(
                self.cfg.station_name, self.cfg.station_password
            )
        }

        class _LoggingChargePoint(ChargePoint):
            def __init__(self, *args: Any, **kwargs: Any):
                super().__init__(*args, **kwargs)
                self._tx_lock = asyncio.Lock()
                self._active_transaction_id: int | None = None
                self._active_id_tag: str | None = None
                self._meter: int = 0

            async def _send_start_transaction(self, *, id_tag: str, connector_id: int):
                # Simulated start: we only need CSMS to respond with an integer txId.
                try:
                    async with self._tx_lock:
                        if self._active_transaction_id is not None:
                            print(
                                "[OCPP] v16 StartTransaction skipped; already active "
                                f"txId={self._active_transaction_id}"
                            )
                            return
                        self._active_id_tag = id_tag
                        self._meter += 1
                        meter_start = self._meter

                    print(
                        "[OCPP] v16 StartTransaction sending "
                        f"connector_id={connector_id} id_tag={id_tag!r} meter_start={meter_start}"
                    )
                    resp = await self.call(
                        call.StartTransaction(
                            connector_id=connector_id,
                            id_tag=id_tag,
                            meter_start=meter_start,
                            timestamp=utc_now_iso(),
                        ),
                        suppress=False,
                        unique_id=str(uuid.uuid4()),
                    )
                    tx_id = int(getattr(resp, "transaction_id", 0) or 0)
                    async with self._tx_lock:
                        self._active_transaction_id = tx_id if tx_id > 0 else None
                    print(f"[OCPP] v16 StartTransaction response txId={tx_id}")
                except Exception as e:  # pragma: no cover
                    print(
                        f"[OCPP] v16 StartTransaction failed error_type={type(e).__name__} error={e}"
                    )

            async def _send_stop_transaction(self, *, transaction_id: int):
                # Simulated stop to complete the smoke-test chain.
                try:
                    async with self._tx_lock:
                        self._meter += 1
                        meter_stop = self._meter
                        id_tag = self._active_id_tag

                    print(
                        "[OCPP] v16 StopTransaction sending "
                        f"txId={transaction_id} meter_stop={meter_stop} id_tag={id_tag!r}"
                    )
                    await self.call(
                        call.StopTransaction(
                            transaction_id=transaction_id,
                            meter_stop=meter_stop,
                            timestamp=utc_now_iso(),
                            id_tag=id_tag,
                            reason="Remote",
                        ),
                        suppress=False,
                        unique_id=str(uuid.uuid4()),
                    )
                    async with self._tx_lock:
                        self._active_transaction_id = None
                        self._active_id_tag = None
                    print(f"[OCPP] v16 StopTransaction completed txId={transaction_id}")
                except Exception as e:  # pragma: no cover
                    print(
                        f"[OCPP] v16 StopTransaction failed error_type={type(e).__name__} error={e}"
                    )

            async def route_message(self, raw_msg):
                # Log only the action (secret-free) to debug CSMS policy closes.
                try:
                    msg = json.loads(raw_msg)
                    if isinstance(msg, list) and len(msg) >= 3:
                        msg_type = msg[0]
                        action = msg[2] if msg_type == 2 else None
                        if action:
                            print(f"[OCPP] v16 RX action={action}")
                except Exception:
                    pass
                return await super().route_message(raw_msg)

            @on("RemoteStartTransaction")
            async def on_remote_start_transaction(  # noqa: N802
                self,
                id_tag=None,
                connector_id=None,
                charging_profile=None,
                **_kwargs,
            ):
                print(
                    "[OCPP] v16 RemoteStartTransaction received "
                    f"connector_id={connector_id!r} id_tag={id_tag!r}"
                )
                cid = int(connector_id or 1)
                tag = str(id_tag or "TEST001")
                # Don't block the call-result; send StartTransaction after acknowledging.
                asyncio.create_task(
                    self._send_start_transaction(id_tag=tag, connector_id=cid)
                )
                return call_result.RemoteStartTransaction(
                    status=enums.RemoteStartStopStatus.accepted
                )

            @on("RemoteStopTransaction")
            async def on_remote_stop_transaction(  # noqa: N802
                self,
                transaction_id=None,
                **_kwargs,
            ):
                print(
                    "[OCPP] v16 RemoteStopTransaction received "
                    f"transaction_id={transaction_id!r}"
                )
                try:
                    tx_id = int(transaction_id or 0)
                except Exception:
                    tx_id = 0
                if tx_id > 0:
                    asyncio.create_task(
                        self._send_stop_transaction(transaction_id=tx_id)
                    )
                return call_result.RemoteStopTransaction(
                    status=enums.RemoteStartStopStatus.accepted
                )

            @on("GetConfiguration")
            async def on_get_configuration(self, key=None, **_kwargs):  # noqa: N802
                # Minimal: return no known keys; report requested keys as unknown.
                unknown = []
                if isinstance(key, list):
                    unknown = key
                elif isinstance(key, str) and key:
                    unknown = [key]
                print(f"[OCPP] v16 GetConfiguration received keys={unknown!r}")
                return call_result.GetConfiguration(
                    configuration_key=[], unknown_key=unknown
                )

            @on("ChangeConfiguration")
            async def on_change_configuration(  # noqa: N802
                self, key=None, value=None, **_kwargs
            ):
                print(
                    "[OCPP] v16 ChangeConfiguration received "
                    f"key={key!r} value={value!r}"
                )
                return call_result.ChangeConfiguration(
                    status=enums.ConfigurationStatus.rejected
                )

        attempt = 0
        while True:
            try:
                async with websockets.connect(
                    url,
                    subprotocols=["ocpp1.6"],
                    additional_headers=headers,
                    ssl=ssl_if_needed(url),
                    open_timeout=10,
                    # Keepalive:
                    # - We already send OCPP Heartbeat at a short interval (CSMS provides 10s).
                    # - Some CSMS/proxies can be strict about WS ping frames; disable them to
                    #   avoid spurious policy closes (1008) while still keeping the channel alive.
                    ping_interval=None,
                    ping_timeout=None,
                    close_timeout=5,
                ) as ws:
                    print(f"[OCPP] v16 connected ws_subprotocol={ws.subprotocol!r}")
                    cp = _LoggingChargePoint(self.cfg.station_name, ws)
                    runner = asyncio.create_task(cp.start())
                    try:
                        boot = await cp.call(
                            call.BootNotification(
                                charge_point_model=self.identity.model,
                                charge_point_vendor=self.identity.vendor_name,
                                charge_point_serial_number=(
                                    self._boot_serial_number
                                    if self._boot_serial_number
                                    else None
                                ),
                                firmware_version=(
                                    self._boot_firmware_version
                                    if self._boot_firmware_version
                                    else None
                                ),
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
