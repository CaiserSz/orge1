"""
Test Router
Created: 2025-12-10
Last Modified: 2025-12-22 17:42:00
Version: 1.2.0
Description: Test endpoints + minimal Admin UI (OCPP runner profiles)
"""

import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from api.config import config
from api.database import get_database

router = APIRouter(tags=["Test"])
admin_router = APIRouter(tags=["Admin"])
_basic = HTTPBasic()

_ADMIN_VALIDATION_ERROR_MSG = (
    "Invalid request. Please check required fields and formats."
)


def _http_400(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


@router.get("/api/test/key")
async def get_test_api_key():
    """
    Test sayfası için API key'i döndürür

    NOT:
    - Bu endpoint test sayfası için gereklidir.
    - Production ortamında güvenlik nedeniyle kapalıdır (404 döndürür).
    """
    # Production ortamında test endpoint'ini kapat
    if os.getenv("ENVIRONMENT", "").lower() == "production":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )

    # Test sayfası için API key gerekli - Ngrok üzerinden erişim için aktif
    try:
        api_key = config.get_secret_api_key()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key not configured",
        )

    return {
        "api_key": api_key,
        "user_id": config.get_user_id() or "",
        "note": "This endpoint is for testing purposes only.",
    }


@router.get("/test", response_class=HTMLResponse)
async def api_test_page():
    """
    API test sayfası

    Dışarıdan API'leri test etmek için web arayüzü
    """
    test_page_path = Path(__file__).parent.parent.parent / "api_test.html"
    if test_page_path.exists():
        # Tarayıcı/Ngrok cache kaynaklı "eski JS" problemlerini engelle
        headers = {
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        }
        return FileResponse(test_page_path, headers=headers)
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Test page not found"
        )


@router.get("/favicon.ico")
async def favicon():
    """Avoid noisy 404 in browser console for favicon requests."""
    return Response(status_code=204)


def _run_cmd(cmd: list[str], *, timeout: float = 10.0) -> Dict[str, Any]:
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "ok": p.returncode == 0,
            "returncode": p.returncode,
            "stdout": (p.stdout or "").strip(),
            "stderr": (p.stderr or "").strip(),
            "cmd": cmd,
        }
    except Exception as exc:
        return {
            "ok": False,
            "returncode": None,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
            "cmd": cmd,
        }


def _sudo_cmd(cmd: list[str], *, timeout: float = 10.0) -> Dict[str, Any]:
    if os.geteuid() == 0:
        return _run_cmd(cmd, timeout=timeout)
    return _run_cmd(["sudo", "-n", *cmd], timeout=timeout)


def _require_admin(credentials: HTTPBasicCredentials = Depends(_basic)) -> str:
    """
    Admin HTTP Basic auth.

    Default credentials (first run):
      - username: admin
      - password: admin123
    """
    db = get_database()
    db.ensure_default_admin_user()

    username = (credentials.username or "").strip()
    password = credentials.password or ""

    if username != "admin" or not db.verify_admin_basic_auth(username, password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
    return username


def _admin_page_html() -> str:
    # Single-file HTML (no new files in workspace): fetches /admin/api/* endpoints.
    return """<!doctype html><html lang="tr"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/><title>Charger Admin - OCPP Profiles</title><style>body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:24px;color:#111}h1{margin:0 0 8px}.muted{color:#666;font-size:13px}.row{display:flex;gap:16px;flex-wrap:wrap}.card{border:1px solid #ddd;border-radius:10px;padding:16px;margin-top:16px;max-width:1100px}label{display:block;font-size:12px;color:#444;margin-top:10px}input,select,textarea{width:100%;padding:8px 10px;border:1px solid #ccc;border-radius:8px;font-size:14px}textarea{min-height:140px;font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,\"Liberation Mono\",monospace}table{width:100%;border-collapse:collapse;margin-top:10px}th,td{border-bottom:1px solid #eee;padding:8px;text-align:left;font-size:13px}th{font-size:12px;color:#555}.btn{display:inline-block;padding:8px 12px;border:1px solid #999;border-radius:8px;background:#fafafa;cursor:pointer;font-size:13px}.btn.primary{background:#1f6feb;border-color:#1f6feb;color:#fff}.btn.danger{background:#b42318;border-color:#b42318;color:#fff}.pill{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;border:1px solid #ddd}.pill.ok{border-color:#2e7d32;color:#2e7d32}.pill.bad{border-color:#b42318;color:#b42318}.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}@media (max-width:900px){.grid2{grid-template-columns:1fr}}code{background:#f6f8fa;padding:2px 6px;border-radius:6px}</style></head><body><h1>Charger Admin</h1><div class="muted">OCPP 2.0.1 / 1.6j profil yönetimi + systemd servis kontrolü. Auth: HTTP Basic.</div><div class="card"><h2 style="margin:0 0 8px 0;">Admin Password</h2><div class="muted">Parola DB'de hash'li tutulur. Yeni parolayı kaydettikten sonra browser yeniden Basic Auth isteyebilir.</div><div class="row"><div style="flex:1;min-width:260px;"><label>New password (min 8 chars)</label><input id="new_admin_pw" type="password" placeholder="Yeni admin parolası"/></div><div style="display:flex;align-items:flex-end;"><button class="btn primary" onclick="changeAdminPassword()">Change password</button></div></div><div id="admin_pw_msg" class="muted" style="margin-top:8px;"></div></div><div class="card"><h2 style="margin:0 0 8px 0;">OCPP Station Profiles</h2><div class="muted">Password UI'da saklanmaz. Sadece <code>password_env_var</code> girilir (örn: <code>OCPP16_STATION_PASSWORD</code>).</div><div class="grid2"><div><label>profile_key (systemd instance name)</label><input id="profile_key" placeholder="ORGE_AC_001_V16_TEST"/><label>station_name</label><input id="station_name" placeholder="ORGE_AC_001_V16_TEST"/><label>ocpp_version</label><select id="ocpp_version"><option value="2.0.1">2.0.1</option><option value="1.6j">1.6j</option></select><label>password_env_var (from .env)</label><input id="password_env_var" placeholder="OCPP16_STATION_PASSWORD"/><label>heartbeat_seconds</label><input id="heartbeat_seconds" type="number" min="1" max="3600" value="60"/><label>enabled</label><select id="enabled"><option value="true" selected>true</option><option value="false">false</option></select></div><div><label>ocpp201_url</label><input id="ocpp201_url" placeholder="wss://lixhium.xyz/ocpp/ORGE_AC_001"/><label>ocpp16_url</label><input id="ocpp16_url" placeholder="wss://lixhium.xyz/ocpp16/ORGE_AC_001"/><label>vendor_name</label><input id="vendor_name" placeholder="ORGE"/><label>model</label><input id="model" placeholder="ORGE"/><label>serial_number</label><input id="serial_number" placeholder="ORG-20251222-16"/><label>firmware_version</label><input id="firmware_version" placeholder="Comm_v2_13112025"/><div class="row" style="margin-top:12px;"><button class="btn primary" onclick="saveProfile()">Save/Update</button><button class="btn" onclick="refreshProfiles()">Refresh</button><button class="btn" onclick="clearForm()">Clear</button></div><div id="profile_msg" class="muted" style="margin-top:8px;"></div></div></div><table id="profiles_table"></table></div><div class="card"><h2 style="margin:0 0 8px 0;">Service Output</h2><div class="muted">Seçili profile için status/log.</div><div class="row"><div style="flex:1;min-width:260px;"><label>Selected profile_key</label><input id="selected_profile" placeholder="(tablodan seç)"/></div><div style="display:flex;gap:10px;align-items:flex-end;"><button class="btn" onclick="syncService()">Sync systemd</button><button class="btn primary" onclick="startService()">Start</button><button class="btn" onclick="restartService()">Restart</button><button class="btn danger" onclick="stopService()">Stop</button><button class="btn" onclick="getStatus()">Status</button><button class="btn" onclick="getLogs()">Logs</button></div></div><label>Output</label><textarea id="output" readonly></textarea></div><script>const $=id=>document.getElementById(id);const api=async(p,o)=>{const u=location.origin+p;const r=await fetch(u,Object.assign({headers:{\"Content-Type\":\"application/json\"}},o||{}));const t=await r.text();let d=null;try{d=t?JSON.parse(t):null}catch(e){d={raw:t}}if(!r.ok){const m=d&&(d.detail||d.message||d.error||d.raw)?(d.detail||d.message||d.error||d.raw):t;throw new Error(r.status+\" \"+m)}return d};const setMsg=(id,m)=>{$(id).textContent=m};function clearForm(){[\"profile_key\",\"station_name\",\"ocpp201_url\",\"ocpp16_url\",\"vendor_name\",\"model\",\"serial_number\",\"firmware_version\",\"password_env_var\"].forEach(id=>$(id).value=\"\");$(\"ocpp_version\").value=\"2.0.1\";$(\"heartbeat_seconds\").value=\"60\";$(\"enabled\").value=\"true\";setMsg(\"profile_msg\",\"\")}function fillForm(p){$(\"profile_key\").value=p.profile_key||\"\";$(\"station_name\").value=p.station_name||\"\";$(\"ocpp_version\").value=p.ocpp_version||\"2.0.1\";$(\"ocpp201_url\").value=p.ocpp201_url||\"\";$(\"ocpp16_url\").value=p.ocpp16_url||\"\";$(\"vendor_name\").value=p.vendor_name||\"\";$(\"model\").value=p.model||\"\";$(\"serial_number\").value=p.serial_number||\"\";$(\"firmware_version\").value=p.firmware_version||\"\";$(\"password_env_var\").value=p.password_env_var||\"\";$(\"heartbeat_seconds\").value=String(p.heartbeat_seconds||60);$(\"enabled\").value=p.enabled?\"true\":\"false\";$(\"selected_profile\").value=p.profile_key||\"\"}async function refreshProfiles(){try{const rows=await api(\"/admin/api/profiles\");let html=\"<tr><th>profile_key</th><th>station_name</th><th>ocpp</th><th>enabled</th><th>updated</th><th>actions</th></tr>\";for(const p of rows){const ok=p.enabled?\"ok\":\"bad\";html+=`<tr><td><code>${p.profile_key}</code></td><td>${p.station_name}</td><td>${p.ocpp_version}</td><td><span class=\"pill ${ok}\">${p.enabled?\"enabled\":\"disabled\"}</span></td><td>${p.updated_at?new Date(p.updated_at*1000).toISOString():\"\"}</td><td><button class=\"btn\" onclick='fillForm(${JSON.stringify(p)})'>Edit</button> <button class=\"btn danger\" onclick='deleteProfile(\"${p.profile_key}\")'>Delete</button></td></tr>`}$(\"profiles_table\").innerHTML=html}catch(e){setMsg(\"profile_msg\",\"Refresh failed: \"+e.message)}}async function saveProfile(){const payload={profile_key:$(\"profile_key\").value,station_name:$(\"station_name\").value,ocpp_version:$(\"ocpp_version\").value,ocpp201_url:$(\"ocpp201_url\").value,ocpp16_url:$(\"ocpp16_url\").value,vendor_name:$(\"vendor_name\").value,model:$(\"model\").value,serial_number:$(\"serial_number\").value,firmware_version:$(\"firmware_version\").value,password_env_var:$(\"password_env_var\").value,heartbeat_seconds:parseInt($(\"heartbeat_seconds\").value||\"60\",10),enabled:$(\"enabled\").value===\"true\"};try{const saved=await api(\"/admin/api/profiles\",{method:\"POST\",body:JSON.stringify(payload)});setMsg(\"profile_msg\",\"Saved: \"+saved.profile_key);await refreshProfiles()}catch(e){setMsg(\"profile_msg\",\"Save failed: \"+e.message)}}async function deleteProfile(k){if(!confirm(\"Delete profile \"+k+\"?\"))return;try{await api(\"/admin/api/profiles/\"+encodeURIComponent(k),{method:\"DELETE\"});setMsg(\"profile_msg\",\"Deleted: \"+k);await refreshProfiles()}catch(e){setMsg(\"profile_msg\",\"Delete failed: \"+e.message)}}async function changeAdminPassword(){const n=$(\"new_admin_pw\").value;try{await api(\"/admin/api/admin/password\",{method:\"POST\",body:JSON.stringify({new_password:n})});setMsg(\"admin_pw_msg\",\"Password updated. Browser may re-prompt Basic Auth.\");$(\"new_admin_pw\").value=\"\"}catch(e){setMsg(\"admin_pw_msg\",\"Password change failed: \"+e.message)}}const out=m=>{$(\"output\").value=m};const selected=()=>$(\"selected_profile\").value;async function syncService(){try{out(JSON.stringify(await api(`/admin/api/profiles/${encodeURIComponent(selected())}/sync_systemd`,{method:\"POST\"}),null,2))}catch(e){out(\"sync failed: \"+e.message)}}async function startService(){try{out(JSON.stringify(await api(`/admin/api/profiles/${encodeURIComponent(selected())}/start`,{method:\"POST\"}),null,2))}catch(e){out(\"start failed: \"+e.message)}}async function stopService(){try{out(JSON.stringify(await api(`/admin/api/profiles/${encodeURIComponent(selected())}/stop`,{method:\"POST\"}),null,2))}catch(e){out(\"stop failed: \"+e.message)}}async function restartService(){try{out(JSON.stringify(await api(`/admin/api/profiles/${encodeURIComponent(selected())}/restart`,{method:\"POST\"}),null,2))}catch(e){out(\"restart failed: \"+e.message)}}async function getStatus(){try{out(JSON.stringify(await api(`/admin/api/profiles/${encodeURIComponent(selected())}/status`),null,2))}catch(e){out(\"status failed: \"+e.message)}}async function getLogs(){try{out((await api(`/admin/api/profiles/${encodeURIComponent(selected())}/logs?lines=200`)).logs||\"\")}catch(e){out(\"logs failed: \"+e.message)}}refreshProfiles();</script></body></html>"""


@admin_router.get("/admin", response_class=HTMLResponse)
async def admin_page(_admin: str = Depends(_require_admin)):
    return HTMLResponse(
        _admin_page_html(),
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@admin_router.get("/admin/api/profiles")
async def admin_list_profiles(_admin: str = Depends(_require_admin)):
    db = get_database()
    return JSONResponse(db.list_ocpp_profiles())


@admin_router.post("/admin/api/profiles")
async def admin_upsert_profile(
    request: Request,
    _admin: str = Depends(_require_admin),
):
    db = get_database()
    try:
        payload = await request.json()
    except Exception:
        raise _http_400(_ADMIN_VALIDATION_ERROR_MSG)

    try:
        saved = db.upsert_ocpp_profile(payload)
    except ValueError as exc:
        raise _http_400(str(exc))
    return JSONResponse(saved)


@admin_router.delete("/admin/api/profiles/{profile_key}")
async def admin_delete_profile(profile_key: str, _admin: str = Depends(_require_admin)):
    db = get_database()
    try:
        profile_key = db.validate_profile_key(profile_key)
    except ValueError as exc:
        raise _http_400(str(exc))
    ok = db.delete_ocpp_profile(profile_key)
    return JSONResponse({"deleted": ok, "profile_key": profile_key})


@admin_router.post("/admin/api/admin/password")
async def admin_change_password(
    request: Request, _admin: str = Depends(_require_admin)
):
    try:
        payload = await request.json()
    except Exception:
        raise _http_400(_ADMIN_VALIDATION_ERROR_MSG)
    new_password = (payload.get("new_password") or "").strip()
    db = get_database()
    try:
        db.set_admin_password("admin", new_password)
    except ValueError as exc:
        raise _http_400(str(exc))
    return JSONResponse({"ok": True})


def _systemd_unit_content() -> str:
    # Uses bash to resolve password from .env without writing secrets to drop-ins.
    return """[Unit]
Description=OCPP Station Client (%i)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/home/basar/charger
Environment=PYTHONUNBUFFERED=1
ExecStart=/bin/bash -lc 'cd /home/basar/charger; set -a; source .env; set +a; export OCPP_STATION_PASSWORD=\"$${!OCPP_PASSWORD_ENV_VAR}\"; exec ./env/bin/python -u ocpp/main.py --primary ${OCPP_PRIMARY} --heartbeat-seconds ${OCPP_HEARTBEAT_SECONDS} --station-name ${OCPP_STATION_NAME} --ocpp201-url ${OCPP201_URL} --ocpp16-url ${OCPP16_URL} --vendor-name ${OCPP_VENDOR_NAME} --model ${OCPP_MODEL}'
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
"""


def _write_root_file(path: str, content: str) -> Dict[str, Any]:
    # Use sudo tee to avoid creating extra workspace files.
    if os.geteuid() == 0:
        cmd = ["tee", path]
    else:
        cmd = ["sudo", "-n", "tee", path]
    res = subprocess.run(
        cmd,
        input=content,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "ok": res.returncode == 0,
        "returncode": res.returncode,
        "stdout": (res.stdout or "").strip(),
        "stderr": (res.stderr or "").strip(),
        "path": path,
    }


def _profile_override_content(profile: Dict[str, Any]) -> str:
    primary = "201" if profile["ocpp_version"] == "2.0.1" else "16"
    heartbeat = int(profile.get("heartbeat_seconds") or 60)

    # Keep drop-in secret-free (password stays in .env).
    lines = [
        "[Service]",
        f"Environment=OCPP_PRIMARY={primary}",
        f"Environment=OCPP_HEARTBEAT_SECONDS={heartbeat}",
        f"Environment=OCPP_STATION_NAME={profile['station_name']}",
        f"Environment=OCPP201_URL={profile.get('ocpp201_url') or ''}",
        f"Environment=OCPP16_URL={profile.get('ocpp16_url') or ''}",
        f"Environment=OCPP_VENDOR_NAME={profile['vendor_name']}",
        f"Environment=OCPP_MODEL={profile['model']}",
        f"Environment=OCPP_PASSWORD_ENV_VAR={profile['password_env_var']}",
        # v16 metadata is read from env in adapter; safe to set for both versions.
        f"Environment=OCPP_V16_SERIAL_NUMBER={profile.get('serial_number') or ''}",
        f"Environment=OCPP_V16_FIRMWARE_VERSION={profile.get('firmware_version') or ''}",
        "",
    ]
    return "\n".join(lines)


@admin_router.post("/admin/api/profiles/{profile_key}/sync_systemd")
async def admin_sync_systemd(profile_key: str, _admin: str = Depends(_require_admin)):
    db = get_database()
    try:
        profile_key = db.validate_profile_key(profile_key)
    except ValueError as exc:
        raise _http_400(str(exc))
    profile = db.get_ocpp_profile(profile_key)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    unit_path = "/etc/systemd/system/ocpp-station@.service"
    dropin_dir = f"/etc/systemd/system/ocpp-station@{profile_key}.service.d"
    dropin_path = f"{dropin_dir}/override.conf"

    results = []
    results.append(_sudo_cmd(["mkdir", "-p", dropin_dir]))
    results.append(_write_root_file(unit_path, _systemd_unit_content()))
    results.append(_write_root_file(dropin_path, _profile_override_content(profile)))
    results.append(_sudo_cmd(["systemctl", "daemon-reload"]))
    return JSONResponse(
        {
            "ok": all(r.get("ok") for r in results),
            "results": results,
            "unit": unit_path,
            "dropin": dropin_path,
        }
    )


def _svc_name(profile_key: str) -> str:
    # profile_key is validated on write; still sanitize for service calls.
    get_database().validate_profile_key(profile_key)
    return f"ocpp-station@{profile_key}.service"


@admin_router.post("/admin/api/profiles/{profile_key}/start")
async def admin_start_service(profile_key: str, _admin: str = Depends(_require_admin)):
    svc = _svc_name(profile_key)
    res = _sudo_cmd(["systemctl", "start", svc])
    return JSONResponse({"service": svc, "result": res})


@admin_router.post("/admin/api/profiles/{profile_key}/stop")
async def admin_stop_service(profile_key: str, _admin: str = Depends(_require_admin)):
    svc = _svc_name(profile_key)
    res = _sudo_cmd(["systemctl", "stop", svc])
    return JSONResponse({"service": svc, "result": res})


@admin_router.post("/admin/api/profiles/{profile_key}/restart")
async def admin_restart_service(
    profile_key: str, _admin: str = Depends(_require_admin)
):
    svc = _svc_name(profile_key)
    res = _sudo_cmd(["systemctl", "restart", svc])
    return JSONResponse({"service": svc, "result": res})


@admin_router.get("/admin/api/profiles/{profile_key}/status")
async def admin_service_status(profile_key: str, _admin: str = Depends(_require_admin)):
    svc = _svc_name(profile_key)
    is_active = _sudo_cmd(["systemctl", "is-active", svc])
    is_enabled = _sudo_cmd(["systemctl", "is-enabled", svc])
    status_out = _sudo_cmd(["systemctl", "status", "--no-pager", svc], timeout=5.0)
    return JSONResponse(
        {
            "service": svc,
            "is_active": is_active,
            "is_enabled": is_enabled,
            "status": status_out,
            "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        }
    )


@admin_router.get("/admin/api/profiles/{profile_key}/logs")
async def admin_service_logs(
    profile_key: str,
    lines: int = Query(200, ge=10, le=2000),
    _admin: str = Depends(_require_admin),
):
    svc = _svc_name(profile_key)
    res = _sudo_cmd(["journalctl", "-u", svc, "--no-pager", "-n", str(lines)])
    return JSONResponse({"service": svc, "lines": lines, "logs": res.get("stdout", "")})
