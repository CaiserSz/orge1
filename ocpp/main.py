"""
OCPP Station Client Runner (Phase-1)

Created: 2025-12-16 01:20
Last Modified: 2025-12-21 20:35
Version: 0.6.0
Description:
  OCPP station client entrypoint for Raspberry Pi (Python runtime).
  - Primary: OCPP 2.0.1 (v201)
  - Fallback: OCPP 1.6J (v16)

IMPORTANT:
  - This process is intentionally isolated from the existing FastAPI/ESP32 runtime.
  - It must NOT open the ESP32 serial port or mutate the current running API.
  - It only connects outward to CSMS via WebSocket (ws/wss).
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import signal
import sys

from once_report import run_once_json
from runtime_config import OcppRuntimeConfig, build_config
from v16_adapter import Ocpp16Adapter


def _verify_python_ocpp_package() -> None:
    """
    Verify that the python-ocpp library is importable and not shadowed by local paths.

    Why:
    - Repo contains `/home/basar/charger/ocpp/` folder.
    - python-ocpp library is imported as `ocpp` (e.g. `ocpp.v201`, `ocpp.v16`).
    - Some environments may accidentally shadow the library, causing runtime import errors.

    This function is secret-free and raises a RuntimeError with an actionable message.
    """
    import importlib

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    try:
        ocpp_pkg = importlib.import_module("ocpp")
    except Exception as exc:
        raise RuntimeError(
            "Missing dependency: python-ocpp library is not importable. "
            "Ensure the venv is created and requirements are installed "
            "(`./env/bin/pip install -r requirements.txt`)."
        ) from exc

    pkg_file = getattr(ocpp_pkg, "__file__", None)
    if not pkg_file:
        raise RuntimeError(
            "Python package conflict: `import ocpp` resolved to a namespace package "
            "(no __file__). This can happen if local paths shadow the python-ocpp library. "
            "Fix: run the station via the venv and avoid adding the repo root ahead of "
            "site-packages on PYTHONPATH."
        )

    pkg_file_abs = os.path.abspath(str(pkg_file))
    if pkg_file_abs.startswith(repo_root + os.sep):
        raise RuntimeError(
            "Python package conflict: `import ocpp` resolved to the repo path "
            f"({pkg_file_abs}). Expected python-ocpp from site-packages. "
            "Fix: ensure python-ocpp is installed in the venv and do not create "
            "`ocpp/__init__.py` inside this repo."
        )

    for mod_name in ("ocpp.routing", "ocpp.v201", "ocpp.v16"):
        try:
            importlib.import_module(mod_name)
        except Exception as exc:
            raise RuntimeError(
                f"python-ocpp appears incomplete or shadowed: failed to import `{mod_name}`: {exc}"
            ) from exc


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="ocpp/main.py",
        description="OCPP station client runner (Phase-1, isolated process).",
    )

    p.add_argument(
        "--config-path",
        default=None,
        help="Optional JSON config file (secret-free defaults). Password must come from env/arg.",
    )
    p.add_argument(
        "--config-json",
        default=None,
        help="Optional JSON config string (secret-free defaults). Password must come from env/arg.",
    )

    p.add_argument("--station-name", default=None)
    p.add_argument("--station-password", default=None)
    p.add_argument("--ocpp201-url", default=None)
    p.add_argument("--ocpp16-url", default=None)
    p.add_argument(
        "--primary",
        default=None,
        help="Primary protocol version: 201 (OCPP 2.0.1) or 16 (OCPP 1.6J).",
    )

    p.add_argument("--vendor-name", default=None)
    p.add_argument("--model", default=None)
    p.add_argument("--id-token", default=None, help="Phase-1 test idToken/idTag.")

    p.add_argument(
        "--poc",
        action="store_true",
        help="Run Phase-1 PoC message sequence and exit (smoke test).",
    )
    p.add_argument(
        "--poc-stop-source",
        default=None,
        choices=["auto", "evdisconnected", "local"],
        help=(
            "Phase-1.3 PoC: stoppedReason mapping evidence. "
            "auto=Remote if inbound RequestStopTransaction seen, else EVDisconnected; "
            "evdisconnected=force EVDisconnected; local=force Local."
        ),
    )
    p.add_argument(
        "--poc-remote-stop-wait-seconds",
        default=None,
        help=(
            "Phase-1.3 PoC: optionally wait this many seconds before TransactionEvent(Ended) "
            "to allow inbound RequestStopTransaction. Default 0."
        ),
    )
    p.add_argument(
        "--poc-transaction-id",
        default=None,
        help=(
            "Phase-1.3 PoC: optional fixed transactionId to use for the run. "
            "This makes it easy for CSMS to send RequestStopTransaction(transactionId=...)."
        ),
    )
    p.add_argument(
        "--poc-remote-start",
        action="store_true",
        help=(
            "Phase-1.4 PoC: wait for inbound RequestStartTransaction and emit "
            "TransactionEvent(Started) with triggerReason=RemoteStart, then exit."
        ),
    )
    p.add_argument(
        "--poc-remote-start-wait-seconds",
        default=None,
        help=(
            "Phase-1.4 PoC: max seconds to wait for inbound RequestStartTransaction "
            "before failing the run. Default 120."
        ),
    )
    p.add_argument(
        "--poc-runbook",
        action="store_true",
        help=(
            "Phase-1.4 runbook: A=RequestStartTransaction → Started(RemoteStart), "
            "B=SetChargingProfile(Accepted), C=RequestStopTransaction → Ended(Remote/RemoteStop)."
        ),
    )
    p.add_argument(
        "--poc-runbook-wait-profile-seconds",
        default=None,
        help="Phase-1.4 runbook: max seconds to wait for SetChargingProfile after Started. Default 120.",
    )
    p.add_argument(
        "--poc-runbook-wait-stop-seconds",
        default=None,
        help="Phase-1.4 runbook: max seconds to wait for RequestStopTransaction after Started. Default 120.",
    )
    p.add_argument(
        "--once",
        action="store_true",
        help="Connect, send Boot+Status(+1 Heartbeat), then exit (non-daemon smoke test).",
    )
    p.add_argument(
        "--heartbeat-seconds",
        default=None,
        help="Override Heartbeat interval seconds (0=use CSMS BootNotification interval).",
    )

    p.add_argument(
        "--local-api-base-url",
        default=None,
        help="Read-only local API base URL (default: http://localhost:8000).",
    )
    p.add_argument(
        "--local-poll-enabled",
        default=None,
        help="Enable read-only local API polling (true/false). Default true.",
    )
    p.add_argument(
        "--local-poll-interval-seconds",
        default=None,
        help="Local API polling interval seconds (default: 10).",
    )
    return p.parse_args(argv)


async def _run_primary_then_fallback(cfg: OcppRuntimeConfig) -> None:
    """
    Start station client.

    Phase-1 behavior:
    - Try primary once.
    - If primary fails to connect, try fallback once.
    - In PoC mode, the adapter runs the PoC sequence then exits.
    """
    # Local adapter import (kept inside function to avoid import-time surprises in some environments).
    from handlers import Ocpp201Adapter

    if cfg.primary == "201":
        try:
            adapter = Ocpp201Adapter(cfg)
            await adapter.run()
            return
        except BaseException as e:
            sys.stderr.write(f"[OCPP] Primary (2.0.1) failed: {e}\n")
            sys.stderr.flush()

        adapter = Ocpp16Adapter(cfg)
        await adapter.run()
        return

    # Primary 1.6J
    try:
        adapter = Ocpp16Adapter(cfg)
        await adapter.run()
        return
    except BaseException as e:
        sys.stderr.write(f"[OCPP] Primary (1.6J) failed: {e}\n")
        sys.stderr.flush()

    adapter = Ocpp201Adapter(cfg)
    await adapter.run()


async def _run_daemon_with_shutdown(cfg: OcppRuntimeConfig) -> None:
    """
    Run the daemon with graceful shutdown handling (systemd-friendly).

    Goal:
    - On SIGTERM/SIGINT: cancel the running adapter and exit cleanly.
    """
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGTERM, signal.SIGINT):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop_event.set)

    main_task = asyncio.create_task(_run_primary_then_fallback(cfg))
    stop_task = asyncio.create_task(stop_event.wait())
    done, _pending = await asyncio.wait(
        {main_task, stop_task}, return_when=asyncio.FIRST_COMPLETED
    )

    if stop_task in done:
        print("[OCPP] shutdown requested; stopping daemon")
        main_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await main_task
        return

    stop_task.cancel()
    await main_task


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    cfg = build_config(args)

    try:
        _verify_python_ocpp_package()
    except Exception as exc:
        sys.stderr.write(f"[OCPP] dependency check failed: {exc}\n")
        sys.stderr.flush()
        return 2

    # Safety: this runner is isolated. It must not be started implicitly.
    if cfg.once_mode:
        # IMPORTANT:
        # `--once` MUST output exactly one JSON object to stdout (CSMS ops tooling).
        # Do not print any other lines here.
        report = asyncio.run(run_once_json(cfg))
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 2 if report.get("result", {}).get("callerror") else 0

    print("[OCPP] Station client starting (isolated process)")
    print(
        f"[OCPP] station_name={cfg.station_name} primary={cfg.primary} poc={cfg.poc_mode} once={cfg.once_mode}"
    )
    print(f"[OCPP] url_201={cfg.ocpp201_url}")
    print(f"[OCPP] url_16={cfg.ocpp16_url}")
    print(
        f"[OCPP] local_poll_enabled={cfg.local_poll_enabled} local_api_base_url={cfg.local_api_base_url} local_poll_interval_seconds={cfg.local_poll_interval_seconds}"
    )

    asyncio.run(_run_daemon_with_shutdown(cfg))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
