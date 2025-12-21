"""
OCPP 2.0.1 (v201) --once Evidence Runner (Phase-1)

Created: 2025-12-21 20:22
Last Modified: 2025-12-21 20:22
Version: 0.1.0
Description:
  Implements the OCPP 2.0.1 path for `ocpp/main.py --once` JSON evidence output.
  This module must remain secret-free (no password output) and should not print.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import uuid
from typing import Any

from once_v201_station import make_once_v201_station_cp
from states import serial_number_for_station_name, utc_now_iso


async def run_once_v201(*, ws: Any, cfg: Any, ctx: Any) -> None:
    """
    Execute a single v201 connect + evidence sequence.

    The caller provides:
      - `ws`: an active websocket connection
      - `cfg`: runtime config (duck-typed)
      - `ctx`: once context providing `send`, `send_safe`, `notes`, `messages`, `inbound`
    """
    from ocpp.v201 import ChargePoint, call, call_result
    from ocpp.v201 import datatypes as dt
    from ocpp.v201 import enums

    StationCP = make_once_v201_station_cp(
        ChargePoint=ChargePoint,
        cfg=cfg,
        inbound=ctx.inbound,
        utc_now_iso=utc_now_iso,
        dt=dt,
        call_result=call_result,
        enums=enums,
    )

    cp: Any = StationCP(cfg.station_name, ws)
    runner = asyncio.create_task(cp.start())
    try:
        await ctx.send(
            cp,
            call.BootNotification(
                charging_station=dt.ChargingStationType(
                    vendor_name=cfg.vendor_name,
                    model=cfg.model,
                    serial_number=serial_number_for_station_name(cfg.station_name),
                    firmware_version="ocpp-phase1",
                ),
                reason=enums.BootReasonEnumType.power_up,
            ),
            "BootNotification",
        )
        await ctx.send(
            cp,
            call.StatusNotification(
                timestamp=utc_now_iso(),
                connector_status=enums.ConnectorStatusEnumType.available,
                evse_id=1,
                connector_id=1,
            ),
            "StatusNotification",
        )
        # Phase-1.x minimum evidence: always emit at least one Heartbeat early.
        await ctx.send(cp, call.Heartbeat(), "Heartbeat")

        # Phase-1.x PoC evidence (enabled via --poc + --once).
        if cfg.poc_mode:
            # Phase-1.4 (A/B/C) Runbook:
            # A) Wait for inbound RequestStartTransaction → send TransactionEvent(Started) (RemoteStart)
            # B) Wait for inbound SetChargingProfile → record summary
            # C) Wait for inbound RequestStopTransaction → send TransactionEvent(Ended) (Remote/RemoteStop)
            if bool(getattr(cfg, "poc_runbook_enabled", False)):
                start_wait_s = int(getattr(cfg, "poc_remote_start_wait_seconds", 120))
                profile_wait_s = int(getattr(cfg, "poc_runbook_wait_profile_seconds", 120))
                stop_wait_s = int(getattr(cfg, "poc_runbook_wait_stop_seconds", 120))
                ctx.notes.append(
                    "phase14: runbook enabled "
                    f"start_wait_s={start_wait_s} profile_wait_s={profile_wait_s} stop_wait_s={stop_wait_s}"
                )

                # A) Wait for RequestStartTransaction inbound
                try:
                    await asyncio.wait_for(cp._remote_start_event.wait(), timeout=start_wait_s)
                except asyncio.TimeoutError:
                    ctx.callerror = True
                    ctx.protocol_timeout = True
                    ctx.notes.append("phase14: timeout waiting for RequestStartTransaction")
                    raise

                remote_start_id = cp._remote_start_id
                remote_start_seen_utc = cp._remote_start_seen_utc
                remote_start_evse_id = cp._remote_start_evse_id or 1
                remote_start_id_token = cp._remote_start_id_token

                tx_id = (cfg.poc_transaction_id or "").strip()
                if not tx_id:
                    tx_id = f"RS_{remote_start_id}" if remote_start_id else uuid.uuid4().hex
                tx_id = tx_id[:36]

                started_ts = utc_now_iso()
                started_req = call.TransactionEvent(
                    event_type=enums.TransactionEventEnumType.started,
                    timestamp=started_ts,
                    trigger_reason=enums.TriggerReasonEnumType.remote_start,
                    seq_no=1,
                    transaction_info=dt.TransactionType(transaction_id=tx_id),
                    evse=dt.EVSEType(id=int(remote_start_evse_id), connector_id=1),
                    id_token=remote_start_id_token,
                )
                await ctx.send_safe(cp, started_req, "TransactionEvent(Started)")
                ctx.notes.append(
                    "phase14: started_trigger_reason=RemoteStart "
                    f"tx_id={tx_id} remote_start_id={remote_start_id} "
                    f"seen_utc={remote_start_seen_utc}"
                )

                # B) Wait for SetChargingProfile inbound (required for runbook)
                try:
                    await asyncio.wait_for(
                        cp._set_charging_profile_event.wait(), timeout=profile_wait_s
                    )
                except asyncio.TimeoutError:
                    ctx.callerror = True
                    ctx.protocol_timeout = True
                    ctx.notes.append("phase14: timeout waiting for SetChargingProfile")
                    raise

                if cp._last_profile_summary is not None:
                    ctx.notes.append(
                        "phase14: set_charging_profile_summary="
                        + json.dumps(
                            cp._last_profile_summary, ensure_ascii=False, sort_keys=True
                        )
                    )

                # C) Wait for RequestStopTransaction inbound (required for runbook)
                try:
                    await asyncio.wait_for(cp._remote_stop_event.wait(), timeout=stop_wait_s)
                except asyncio.TimeoutError:
                    ctx.callerror = True
                    ctx.protocol_timeout = True
                    ctx.notes.append("phase14: timeout waiting for RequestStopTransaction")
                    raise

                remote_stop_seen_utc = cp._remote_stop_seen_utc
                remote_stop_tx_id = cp._remote_stop_transaction_id
                ctx.notes.append(
                    "phase14: stop_source=remote inbound=RequestStopTransaction "
                    f"inbound_tx_id={remote_stop_tx_id} seen_utc={remote_stop_seen_utc}"
                )

                ended_ts = utc_now_iso()
                ended_req = call.TransactionEvent(
                    event_type=enums.TransactionEventEnumType.ended,
                    timestamp=ended_ts,
                    trigger_reason=enums.TriggerReasonEnumType.remote_stop,
                    seq_no=2,
                    transaction_info=dt.TransactionType(
                        transaction_id=tx_id, stopped_reason=enums.ReasonEnumType.remote
                    ),
                    evse=dt.EVSEType(id=int(remote_start_evse_id), connector_id=1),
                    id_token=remote_start_id_token,
                )
                await ctx.send_safe(cp, ended_req, "TransactionEvent(Ended)")
                ctx.notes.append(
                    "phase14: ended_stopped_reason=Remote "
                    "trigger_reason=RemoteStop seq_no_end=2"
                )

                await ctx.send(cp, call.Heartbeat(), "Heartbeat")
                return

            # Phase-1.4 (A) Remote Start only evidence: wait for inbound RequestStartTransaction.
            if bool(getattr(cfg, "poc_remote_start_enabled", False)):
                wait_s = int(getattr(cfg, "poc_remote_start_wait_seconds", 120))
                ctx.notes.append(
                    f"phase14: waiting_for=RequestStartTransaction timeout_seconds={wait_s}"
                )
                try:
                    await asyncio.wait_for(cp._remote_start_event.wait(), timeout=wait_s)
                except asyncio.TimeoutError:
                    ctx.callerror = True
                    ctx.notes.append("phase14: timeout waiting for RequestStartTransaction")
                    raise

                # Build TransactionEvent(Started) driven by RemoteStart.
                remote_start_id = cp._remote_start_id
                remote_start_seen_utc = cp._remote_start_seen_utc
                remote_start_evse_id = cp._remote_start_evse_id or 1
                remote_start_id_token = cp._remote_start_id_token

                tx_id = (cfg.poc_transaction_id or "").strip()
                if not tx_id:
                    tx_id = f"RS_{remote_start_id}" if remote_start_id else uuid.uuid4().hex
                tx_id = tx_id[:36]

                started_ts = utc_now_iso()
                started_req = call.TransactionEvent(
                    event_type=enums.TransactionEventEnumType.started,
                    timestamp=started_ts,
                    trigger_reason=enums.TriggerReasonEnumType.remote_start,
                    seq_no=1,
                    transaction_info=dt.TransactionType(transaction_id=tx_id),
                    evse=dt.EVSEType(id=int(remote_start_evse_id), connector_id=1),
                    id_token=remote_start_id_token,
                )
                await ctx.send_safe(cp, started_req, "TransactionEvent(Started)")
                ctx.notes.append(
                    "phase14: started_trigger_reason=RemoteStart "
                    f"tx_id={tx_id} remote_start_id={remote_start_id} "
                    f"seen_utc={remote_start_seen_utc}"
                )
                # Minimal Phase-1.4(A): finish after Started evidence.
                await ctx.send(cp, call.Heartbeat(), "Heartbeat")
                return

            seq_no = 1
            # Keep transactionId short (CSMS/lib constraints vary); stable for this run.
            tx_id = (cfg.poc_transaction_id or uuid.uuid4().hex).strip()
            if not tx_id:
                tx_id = uuid.uuid4().hex
            tx_id = tx_id[:36]

            id_token = dt.IdTokenType(
                id_token=cfg.id_token,
                type=enums.IdTokenEnumType.central,
            )

            # Authorize(TEST001)
            auth_req = call.Authorize(id_token=id_token)
            auth_res = await ctx.send_safe(cp, auth_req, "Authorize")
            auth_summary = ctx.response_summary(auth_res)
            # Some CSMS policies may omit id_token_info in responses.
            auth_has_id_token_info = bool(getattr(auth_res, "id_token_info", None) is not None)
            auth_summary["id_token_info_present"] = auth_has_id_token_info
            if auth_has_id_token_info:
                iti = getattr(auth_res, "id_token_info", None)
                if isinstance(iti, dict):
                    auth_summary["id_token_status"] = iti.get("status")
                else:
                    auth_summary["id_token_status"] = getattr(iti, "status", None)
            # Replace the last Authorize entry with enriched summary.
            if ctx.messages and ctx.messages[-1].get("action") == "Authorize":
                ctx.messages[-1]["response_summary"] = auth_summary

            # TransactionEvent Started
            started_ts = utc_now_iso()
            started_req = call.TransactionEvent(
                event_type=enums.TransactionEventEnumType.started,
                timestamp=started_ts,
                trigger_reason=enums.TriggerReasonEnumType.authorized,
                seq_no=seq_no,
                transaction_info=dt.TransactionType(transaction_id=tx_id),
                evse=dt.EVSEType(id=1, connector_id=1),
                id_token=id_token,
            )
            await ctx.send_safe(cp, started_req, "TransactionEvent(Started)")
            seq_no += 1

            # MeterValues (3 samples, monotonic kWh)
            energy_values: list[float] = []
            base_kwh = 1000.0
            for i in range(3):
                if i > 0:
                    await asyncio.sleep(5)
                kwh = base_kwh + (i + 1) * 0.01
                energy_values.append(kwh)

                mv_ts = utc_now_iso()
                mv_req = call.MeterValues(
                    evse_id=1,
                    meter_value=[
                        dt.MeterValueType(
                            timestamp=mv_ts,
                            sampled_value=[
                                dt.SampledValueType(
                                    value=kwh,
                                    context=enums.ReadingContextEnumType.sample_periodic,
                                    measurand=enums.MeasurandEnumType.energy_active_import_register,
                                    unit_of_measure=dt.UnitOfMeasureType(unit="kWh"),
                                )
                            ],
                        )
                    ],
                )
                await ctx.send_safe(cp, mv_req, f"MeterValues[{i+1}]")

                # Optional: TransactionEvent Updated after 2nd sample
                if i == 1:
                    upd_ts = utc_now_iso()
                    upd_req = call.TransactionEvent(
                        event_type=enums.TransactionEventEnumType.updated,
                        timestamp=upd_ts,
                        trigger_reason=enums.TriggerReasonEnumType.meter_value_periodic,
                        seq_no=seq_no,
                        transaction_info=dt.TransactionType(
                            transaction_id=tx_id,
                            charging_state=enums.ChargingStateEnumType.charging,
                        ),
                        evse=dt.EVSEType(id=1, connector_id=1),
                        id_token=id_token,
                        meter_value=mv_req.meter_value,
                    )
                    await ctx.send_safe(cp, upd_req, "TransactionEvent(Updated)")
                    seq_no += 1

            # TransactionEvent Ended (final meter + stoppedReason)
            # Phase-1.3: map stoppedReason to stop source signal
            remote_stop_seen = bool(
                getattr(cp, "_remote_stop_event", None) and cp._remote_stop_event.is_set()
            )
            remote_stop_tx_id = getattr(cp, "_remote_stop_transaction_id", None)
            remote_stop_seen_utc = getattr(cp, "_remote_stop_seen_utc", None)

            stop_source_cfg = (cfg.poc_stop_source or "auto").strip().lower()
            if stop_source_cfg not in {"auto", "evdisconnected", "local"}:
                stop_source_cfg = "auto"

            # Optional wait window to allow inbound RequestStopTransaction.
            if (
                not remote_stop_seen
                and stop_source_cfg == "auto"
                and int(getattr(cfg, "poc_remote_stop_wait_seconds", 0)) > 0
            ):
                wait_s = int(getattr(cfg, "poc_remote_stop_wait_seconds", 0))
                try:
                    await asyncio.wait_for(cp._remote_stop_event.wait(), timeout=wait_s)
                except asyncio.TimeoutError:
                    pass
                remote_stop_seen = cp._remote_stop_event.is_set()
                remote_stop_tx_id = getattr(cp, "_remote_stop_transaction_id", None)
                remote_stop_seen_utc = getattr(cp, "_remote_stop_seen_utc", None)

            if remote_stop_seen:
                ended_stopped_reason = enums.ReasonEnumType.remote
                ended_trigger_reason = enums.TriggerReasonEnumType.remote_stop
                ctx.notes.append(
                    "phase13: stop_source=remote "
                    f"inbound=RequestStopTransaction tx_id={remote_stop_tx_id} "
                    f"seen_utc={remote_stop_seen_utc}"
                )
            elif stop_source_cfg == "local":
                ended_stopped_reason = enums.ReasonEnumType.local
                ended_trigger_reason = enums.TriggerReasonEnumType.stop_authorized
                ctx.notes.append("phase13: stop_source=local (simulated)")
            else:
                ended_stopped_reason = enums.ReasonEnumType.ev_disconnected
                ended_trigger_reason = enums.TriggerReasonEnumType.ev_departed
                ctx.notes.append("phase13: stop_source=evdisconnected (default)")

            ended_ts = utc_now_iso()
            final_kwh = energy_values[-1] if energy_values else base_kwh
            ended_req = call.TransactionEvent(
                event_type=enums.TransactionEventEnumType.ended,
                timestamp=ended_ts,
                trigger_reason=ended_trigger_reason,
                seq_no=seq_no,
                transaction_info=dt.TransactionType(
                    transaction_id=tx_id,
                    stopped_reason=ended_stopped_reason,
                ),
                evse=dt.EVSEType(id=1, connector_id=1),
                id_token=id_token,
                meter_value=[
                    dt.MeterValueType(
                        timestamp=ended_ts,
                        sampled_value=[
                            dt.SampledValueType(
                                value=final_kwh,
                                context=enums.ReadingContextEnumType.transaction_end,
                                measurand=enums.MeasurandEnumType.energy_active_import_register,
                                unit_of_measure=dt.UnitOfMeasureType(unit="kWh"),
                            )
                        ],
                    )
                ],
            )
            await ctx.send_safe(cp, ended_req, "TransactionEvent(Ended)")

            # Local validations (evidence for Phase-1.2)
            monotonic_energy_ok = all(
                energy_values[i] < energy_values[i + 1] for i in range(len(energy_values) - 1)
            )
            ctx.notes.append(
                f"phase12: transaction_id={tx_id} seq_no_start=1 seq_no_end={seq_no}"
            )
            ctx.notes.append(
                f"phase12: meter_kwh={energy_values} monotonic_ok={monotonic_energy_ok}"
            )
            ctx.notes.append(
                f"phase13: ended_stopped_reason={ended_stopped_reason.value} "
                f"trigger_reason={ended_trigger_reason.value}"
            )

        await ctx.send(cp, call.Heartbeat(), "Heartbeat")
    finally:
        runner.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await runner


