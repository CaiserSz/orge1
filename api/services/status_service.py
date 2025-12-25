"""
Status Service
Created: 2025-12-10 15:30:00
Last Modified: 2025-12-25 03:12:00
Version: 1.2.2
Description: Status business logic service layer + Serial test manager (USB/GPIO)
"""

import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

from api.services.base_service import BaseService
from api.config import config


class StatusService(BaseService):
    """
    Status business logic service

    Status işlemlerinin business logic'ini içerir.
    Router'lar sadece HTTP handling yapar, business logic burada.
    """

    def get_status(self) -> Optional[Dict[str, Any]]:
        """
        ESP32 durum bilgisini al

        Returns:
            Status dict veya None
        """
        if not self.bridge or not self.bridge.is_connected:
            return None

        return self.bridge.get_status()


# ----------------------------
# Serial Test Manager (USB vs GPIO)
# ----------------------------
class _SerialTestWorker:
    """
    Ham seri dinleme + opsiyonel TX gönderimi için basit worker.

    Notlar:
    - Test UI amaçlıdır; parse/protokol mantığı içermez.
    - Pytest ortamında fiziksel seri port açmaz (simülasyon).
    """

    def __init__(self, *, mode: str, port: str, baudrate: int):
        self.mode = mode
        self.port = port
        self.baudrate = baudrate

        self.started_at_ts = time.time()
        self.rx_total = 0
        self.tx_total = 0
        self.last_rx_at_ts: Optional[float] = None
        self.last_rx_hex: str = ""
        self.last_rx_ascii: str = ""
        self.last_error: Optional[str] = None

        self._stop = threading.Event()
        self._io_lock = threading.Lock()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._ser = None

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        try:
            self._thread.join(timeout=2.0)
        except Exception:
            pass
        try:
            with self._io_lock:
                if self._ser and getattr(self._ser, "is_open", False):
                    self._ser.close()
        except Exception:
            pass

    def snapshot(self) -> Dict[str, Any]:
        return {
            "running": (not self._stop.is_set()) and self._thread.is_alive(),
            "mode": self.mode,
            "port": self.port,
            "baudrate": self.baudrate,
            "started_at_ts": self.started_at_ts,
            "rx_total": self.rx_total,
            "tx_total": self.tx_total,
            "last_rx_at_ts": self.last_rx_at_ts,
            "last_rx_hex": self.last_rx_hex,
            "last_rx_ascii": self.last_rx_ascii,
            "last_error": self.last_error,
        }

    def send_hex(self, hex_payload: str) -> Dict[str, Any]:
        raw = _parse_hex_bytes(hex_payload)
        if not raw:
            raise ValueError("hex payload empty")
        if len(raw) > 512:
            raise ValueError("hex payload too large (max 512 bytes)")

        if os.getenv("PYTEST_CURRENT_TEST") is not None:
            self.tx_total += len(raw)
            return {"written": len(raw), "note": "pytest simulated write"}

        with self._io_lock:
            if not self._ser or not getattr(self._ser, "is_open", False):
                raise RuntimeError("serial not open")
            n = self._ser.write(raw)
            self._ser.flush()
        self.tx_total += int(n or 0)
        return {"written": int(n or 0)}

    def _run(self) -> None:
        if os.getenv("PYTEST_CURRENT_TEST") is not None:
            while not self._stop.is_set():
                time.sleep(0.05)
            return

        try:
            import serial  # type: ignore

            with self._io_lock:
                self._ser = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    timeout=0.1,
                    write_timeout=0.5,
                    xonxoff=False,
                    rtscts=False,
                    dsrdtr=False,
                )
                try:
                    self._ser.reset_input_buffer()
                    self._ser.reset_output_buffer()
                except Exception:
                    pass

            while not self._stop.is_set():
                chunk = b""
                with self._io_lock:
                    if self._ser and getattr(self._ser, "is_open", False):
                        chunk = self._ser.read(512)
                if chunk:
                    self.rx_total += len(chunk)
                    self.last_rx_at_ts = time.time()
                    self.last_rx_hex = chunk.hex()
                    try:
                        self.last_rx_ascii = chunk.decode("utf-8", errors="replace")
                    except Exception:
                        self.last_rx_ascii = ""
                else:
                    time.sleep(0.02)
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
        finally:
            try:
                with self._io_lock:
                    if self._ser and getattr(self._ser, "is_open", False):
                        self._ser.close()
            except Exception:
                pass


def _parse_hex_bytes(raw: str) -> bytes:
    s = (raw or "").strip()
    if not s:
        return b""
    s = s.replace(" ", "").replace("\n", "").replace("\r", "").replace("\t", "")
    s = s.replace("0x", "").replace("0X", "")
    if len(s) % 2 != 0:
        raise ValueError("hex payload must have even length")
    return bytes.fromhex(s)


def _best_effort_disconnect_esp32_bridge() -> None:
    """
    Test modu öncesi mevcut ESP32Bridge instance'ını (varsa) disconnect et.
    get_esp32_bridge() çağrılmaz (bağlantı kurmaya çalışmasın).
    """
    try:
        import esp32.bridge as bridge_mod

        bridge = getattr(bridge_mod, "_esp32_bridge_instance", None)
        if bridge and hasattr(bridge, "disconnect"):
            bridge.disconnect()
    except Exception:
        pass


def _guess_usb_port() -> Optional[str]:
    return _guess_usb_port_from_ports(_list_usb_ports())


_GPIO_PORT = "/dev/ttyS0"


def _list_usb_ports() -> list[str]:
    dev = Path("/dev")
    ports: list[str] = []
    for pat in ("ttyUSB*", "ttyACM*"):
        ports.extend(str(p) for p in sorted(dev.glob(pat)))
    return ports


def _guess_usb_port_from_ports(usb_ports: list[str]) -> Optional[str]:
    # Önce config içinden USB görünümlü bir port varsa onu kullan.
    try:
        port = (getattr(config, "ESP32_PORT", None) or "").strip()
        if port.startswith("/dev/ttyUSB") or port.startswith("/dev/ttyACM"):
            return port
    except Exception:
        pass
    return usb_ports[0] if usb_ports else None


class SerialTestManager:
    """
    USB vs GPIO seri test modlarını yöneten singleton manager.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._worker: Optional[_SerialTestWorker] = None

    def status(self) -> Dict[str, Any]:
        usb_ports = _list_usb_ports()
        usb_candidate = _guess_usb_port_from_ports(usb_ports)
        gpio_exists = Path(_GPIO_PORT).exists()

        with self._lock:
            if self._worker is None:
                base: Dict[str, Any] = {
                    "running": False,
                    "mode": "off",
                    "port": None,
                    "baudrate": None,
                }
            else:
                base = self._worker.snapshot()

        base.update(
            {
                "usb_ports": usb_ports,
                "usb_candidate": usb_candidate,
                "gpio_port": _GPIO_PORT,
                "gpio_exists": gpio_exists,
            }
        )
        return base

    def stop(self) -> Dict[str, Any]:
        with self._lock:
            if self._worker is not None:
                self._worker.stop()
                self._worker = None
        return {"ok": True}

    def start(self, mode: str) -> Dict[str, Any]:
        mode = (mode or "").strip().lower()
        if mode not in ("usb", "gpio"):
            raise ValueError("mode must be 'usb' or 'gpio'")

        usb_ports = _list_usb_ports()
        usb_candidate = _guess_usb_port_from_ports(usb_ports)

        if mode == "usb":
            port = usb_candidate
            baudrate = 115200
            if not port:
                raise RuntimeError("USB port not found (/dev/ttyUSB*|ttyACM*)")
        else:
            port = _GPIO_PORT
            baudrate = 9600

        with self._lock:
            if self._worker is not None:
                # Idempotent start: aynı mode/port/baud aktifse yeniden başlatma.
                snap = self._worker.snapshot()
                if (
                    snap.get("running") is True
                    and self._worker.mode == mode
                    and self._worker.port == port
                    and self._worker.baudrate == baudrate
                ):
                    return {"ok": True, "note": "already running", **snap}

                self._worker.stop()
                self._worker = None

            _best_effort_disconnect_esp32_bridge()

            worker = _SerialTestWorker(mode=mode, port=port, baudrate=baudrate)
            worker.start()
            self._worker = worker

            return {"ok": True, **worker.snapshot()}

    def send_hex(self, hex_payload: str) -> Dict[str, Any]:
        with self._lock:
            if self._worker is None:
                raise RuntimeError("serial test is not running")
            res = self._worker.send_hex(hex_payload)
        return {"ok": True, "result": res}

    def page_html(self, mode: str) -> str:
        mode = (mode or "").strip().lower()
        title = "USB" if mode == "usb" else "GPIO"
        subtitle = "115200 baud (USB)" if mode == "usb" else "9600 baud (/dev/ttyS0)"
        # Single-file HTML (no new workspace files). Auth: HTTP Basic (same as /admin).
        return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/><title>Serial Test - {title}</title><style>body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:24px;color:#111}}.muted{{color:#666;font-size:13px}}.card{{border:1px solid #ddd;border-radius:10px;padding:16px;margin-top:16px;max-width:1100px}}.row{{display:flex;gap:12px;flex-wrap:wrap;align-items:center}}.btn{{padding:8px 12px;border:1px solid #999;border-radius:8px;background:#fafafa;cursor:pointer;font-size:13px}}.btn.primary{{background:#1f6feb;border-color:#1f6feb;color:#fff}}.btn.danger{{background:#b42318;border-color:#b42318;color:#fff}}.pill{{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;border:1px solid #ddd}}.pill.ok{{border-color:#2e7d32;color:#2e7d32}}.pill.warn{{border-color:#b42318;color:#b42318}}.pill.info{{border-color:#999;color:#555}}input{{padding:8px 10px;border:1px solid #ccc;border-radius:8px;font-size:14px;min-width:280px}}pre{{background:#0b1020;color:#d6e2ff;padding:12px;border-radius:10px;overflow:auto;white-space:pre-wrap}}</style></head><body><h1 style="margin:0 0 6px 0;">{title} in/out</h1><div class="muted">{subtitle} — default OFF. Bu sayfa test amaçlı ham seri dinleme/gönderim yapar.</div><div class="card"><div class="row"><button id="btn_on" class="btn primary" onclick="start()">ON</button><button id="btn_off" class="btn danger" onclick="stop()">OFF</button><span id="badge" class="pill info">OFF</span><span class="muted" id="state">loading…</span></div><div class="muted" id="hint" style="margin-top:8px;"></div><div class="muted" id="dev" style="margin-top:6px;"></div><div class="row" style="margin-top:12px;"><input id="hex" placeholder="HEX gönder (örn: 41 01 2C 00 10)"/><button class="btn" onclick="sendHex()">Send HEX</button></div><div class="muted" style="margin-top:10px;">RX son chunk: (hex/ascii) — UI 1sn polling.</div><pre id="out">loading…</pre></div><script>const MODE={mode!r};const $=id=>document.getElementById(id);const api=async(p,o)=>{{const r=await fetch(location.origin+p,Object.assign({{headers:{{\"Content-Type\":\"application/json\"}}}},o||{{}}));const t=await r.text();let d=null;try{{d=t?JSON.parse(t):null}}catch(e){{d={{raw:t}}}}if(!r.ok){{throw new Error(r.status+\" \"+(d&&(d.detail||d.raw)||t))}}return d}};function fmtTs(ts){{if(!ts)return \"-\";try{{return new Date(ts*1000).toISOString()}}catch(e){{return String(ts)}}}}function setBadge(kind,text){{const b=$(\"badge\");b.className=\"pill \"+kind;b.textContent=text;}}async function refresh(){{try{{const s=await api(\"/admin/api/serial_test/status\");const running=!!s.running;const activeMode=(s.mode||\"off\");const port=(s.port||\"-\");const baud=(s.baudrate||\"-\");const matches=running && activeMode===MODE;const other=running && activeMode!==\"off\" && activeMode!==MODE;if(!running || activeMode===\"off\"){{setBadge(\"info\",\"OFF\");$(\"hint\").textContent=\"\";}}else if(matches){{setBadge(\"ok\",\"ON\");$(\"hint\").textContent=\"Aktif kanal: \"+activeMode+\" (bu sayfa)\";}}else{{setBadge(\"warn\",\"OTHER\");$(\"hint\").textContent=\"Şu an '\"+activeMode+\"' aktif. ON tıklarsan '\"+MODE+\"' aktif olur ve '\"+activeMode+\"' durur.\";}}const usbCandidate=(s.usb_candidate||\"\");const usbPorts=(Array.isArray(s.usb_ports)?s.usb_ports.join(\", \"):\"\");if(MODE===\"usb\"){{if(usbCandidate){{$(\"dev\").textContent=\"USB cihaz: \"+usbCandidate;}}else{{$(\"dev\").textContent=\"USB cihaz bulunamadı. Mevcut USB portlar: \"+(usbPorts||\"-\");}}}}else{{const gp=(s.gpio_port||\"/dev/ttyS0\");$(\"dev\").textContent=gp+\" (\"+(s.gpio_exists?\"present\":\"missing\")+\")\";}}$(\"btn_on\").disabled=matches || (MODE===\"usb\" && !usbCandidate);$(\"btn_off\").disabled=!running;$(\"state\").textContent=\"active_mode=\"+activeMode+\" running=\"+running+\" port=\"+port+\" baud=\"+baud+\" rx_total=\"+(s.rx_total||0)+\" tx_total=\"+(s.tx_total||0)+\" last_rx=\"+fmtTs(s.last_rx_at_ts)+\" err=\"+(s.last_error||\"-\");const hex=(s.last_rx_hex||\"\");const asc=(s.last_rx_ascii||\"\").replace(/\\u0000/g,\"\");$(\"out\").textContent=\"HEX: \"+hex+\"\\nASCII: \"+asc;}}catch(e){{setBadge(\"warn\",\"ERR\");$(\"state\").textContent=\"error: \"+e.message;}}}}async function start(){{await api(\"/admin/api/serial_test/start\",{{method:\"POST\",body:JSON.stringify({{mode:MODE}})}});await refresh();}}async function stop(){{await api(\"/admin/api/serial_test/stop\",{{method:\"POST\"}});await refresh();}}async function sendHex(){{const h=$(\"hex\").value||\"\";await api(\"/admin/api/serial_test/send_hex\",{{method:\"POST\",body:JSON.stringify({{hex:h}})}});await refresh();}}refresh();setInterval(refresh,1000);</script></body></html>"""


# Global singleton
serial_test_manager = SerialTestManager()
