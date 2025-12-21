"""
OCPP 2.0.1 (v201) Station ChargePoint Class (Phase-1)

Created: 2025-12-21 20:14
Last Modified: 2025-12-21 20:14
Version: 0.1.0
Description:
  Factory for the v201 StationCP used by `Ocpp201Adapter`.
  Kept in a separate module to reduce `ocpp/handlers.py` file size while
  preserving behavior.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, Callable, Type

from ocpp.routing import on


def make_v201_station_cp(
    *,
    ChargePoint: Any,
    cfg: Any,
    call: Any,
    call_result: Any,
    datatypes: Any,
    enums: Any,
    utc_now_iso: Callable[[], str],
) -> Type[Any]:
    """
    Return a ChargePoint subclass implementing Phase-1 inbound handlers.

    Notes:
      - `cfg` is captured by closure to keep the implementation close to the
        original in `ocpp/handlers.py`.
      - Keep this function import-time light; python-ocpp objects are provided
        by the caller (already imported inside adapter runtime).
    """

    class StationCP(ChargePoint):
        # CSMS may send inventory/model queries; accept them in Phase-1 to avoid breaking the flow.
        @on("GetBaseReport")
        def on_get_base_report(self, request_id: int, report_base: str, **kwargs):
            return call_result.GetBaseReport(
                status=enums.GenericDeviceModelStatusEnumType.accepted
            )

        @on("GetReport")
        def on_get_report(self, request_id: int, **kwargs):
            return call_result.GetReport(
                status=enums.GenericDeviceModelStatusEnumType.accepted
            )

        @on("GetLog")
        def on_get_log(self, request_id: int, **kwargs):
            return call_result.GetLog(status=enums.LogStatusEnumType.rejected)

        @on("GetVariables")
        def on_get_variables(self, get_variable_data, **kwargs):
            results = []

            def _component(obj):
                if isinstance(obj, datatypes.ComponentType):
                    return obj
                if isinstance(obj, dict):
                    evse = obj.get("evse")
                    evse_obj = None
                    if isinstance(evse, dict):
                        evse_obj = datatypes.EVSEType(
                            id=evse.get("id"),
                            connector_id=evse.get("connector_id"),
                        )
                    return datatypes.ComponentType(
                        name=obj.get("name"),
                        instance=obj.get("instance"),
                        evse=evse_obj,
                    )
                return datatypes.ComponentType(name="Unknown")

            def _variable(obj):
                if isinstance(obj, datatypes.VariableType):
                    return obj
                if isinstance(obj, dict):
                    return datatypes.VariableType(
                        name=obj.get("name"), instance=obj.get("instance")
                    )
                return datatypes.VariableType(name="Unknown")

            for item in get_variable_data:
                if isinstance(item, dict):
                    comp = _component(item.get("component"))
                    var = _variable(item.get("variable"))
                    attr_type = item.get("attribute_type")
                else:
                    comp = _component(getattr(item, "component", None))
                    var = _variable(getattr(item, "variable", None))
                    attr_type = getattr(item, "attribute_type", None)

                results.append(
                    datatypes.GetVariableResultType(
                        attribute_status=enums.GetVariableStatusEnumType.unknown_variable,
                        component=comp,
                        variable=var,
                        attribute_type=attr_type,
                    )
                )

            return call_result.GetVariables(get_variable_result=results)

        @on("RequestStartTransaction")
        async def on_request_start_transaction(
            self,
            id_token: datatypes.IdTokenType,
            remote_start_id: int,
            evse_id: int | None = None,
            **kwargs,
        ):
            # Phase-1.4: accept UI Remote Start and emit a Started TransactionEvent.
            tx_id = str(getattr(cfg, "poc_transaction_id", "") or "").strip()
            if not tx_id:
                tx_id = f"RS_{remote_start_id}"
            tx_id = tx_id[:36]

            evse = datatypes.EVSEType(id=int(evse_id or 1), connector_id=1)

            print(
                "[OCPP] v201 RequestStartTransaction received "
                f"remote_start_id={remote_start_id} evse_id={getattr(evse, 'id', None)} tx_id={tx_id}"
            )

            async def _emit_started() -> None:
                try:
                    await self.call(
                        call.TransactionEvent(
                            event_type=enums.TransactionEventEnumType.started,
                            timestamp=utc_now_iso(),
                            trigger_reason=enums.TriggerReasonEnumType.remote_start,
                            seq_no=1,
                            transaction_info=datatypes.TransactionType(
                                transaction_id=tx_id
                            ),
                            evse=evse,
                            id_token=id_token,
                        ),
                        suppress=False,
                        unique_id=str(uuid.uuid4()),
                    )
                    print(
                        "[OCPP] v201 TransactionEvent(Started) remote_start "
                        f"tx_id={tx_id} utc={utc_now_iso()}"
                    )
                except Exception as exc:
                    print(
                        "[OCPP] v201 TransactionEvent(Started) remote_start failed "
                        f"tx_id={tx_id} error={exc}"
                    )

            asyncio.create_task(_emit_started())

            return call_result.RequestStartTransaction(
                status=enums.RequestStartStopStatusEnumType.accepted,
                transaction_id=tx_id,
            )

        @on("RequestStopTransaction")
        async def on_request_stop_transaction(self, transaction_id: str, **kwargs):
            # Phase-1.4 UI Remote Stop: accept the request and optionally emit Ended.
            print(
                "[OCPP] v201 RequestStopTransaction received "
                f"transaction_id={transaction_id} utc={utc_now_iso()}"
            )

            async def _emit_ended() -> None:
                try:
                    await self.call(
                        call.TransactionEvent(
                            event_type=enums.TransactionEventEnumType.ended,
                            timestamp=utc_now_iso(),
                            trigger_reason=enums.TriggerReasonEnumType.remote_stop,
                            seq_no=2,
                            transaction_info=datatypes.TransactionType(
                                transaction_id=transaction_id,
                                stopped_reason=enums.ReasonEnumType.remote,
                            ),
                        ),
                        suppress=False,
                        unique_id=str(uuid.uuid4()),
                    )
                    print(
                        "[OCPP] v201 TransactionEvent(Ended) remote_stop "
                        f"tx_id={transaction_id} utc={utc_now_iso()}"
                    )
                except Exception as exc:
                    print(
                        "[OCPP] v201 TransactionEvent(Ended) remote_stop failed "
                        f"tx_id={transaction_id} error={exc}"
                    )

            asyncio.create_task(_emit_ended())

            return call_result.RequestStopTransaction(
                status=enums.RequestStartStopStatusEnumType.accepted
            )

    return StationCP
