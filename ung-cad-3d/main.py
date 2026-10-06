import hashlib
import hmac
import io
import json
import logging
import os
import re
import secrets
import shutil
import sqlite3
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from slicer import MATERIALS, GcodeCheckError, SliceValidationError, preview_stl, slice_model
from slicer_cnc import resolve_settings, slice_shapes_to_gcode


logger = logging.getLogger("ung_cad_3d")

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"
LEGACY_DB_PATH = BASE_DIR / "ung_cad_3d.db"
# The database lives OUTSIDE anything that is served over HTTP. On Railway, mount a
# volume (e.g. at /data) and set UNG_CAD_3D_DB=/data/ung_cad_3d.db so it survives redeploys.
DB_PATH = Path(os.getenv("UNG_CAD_3D_DB", str(BASE_DIR / "data" / "ung_cad_3d.db")))
GENERATED_DIR = Path(os.getenv("UNG_CAD_GENERATED_DIR", str(BASE_DIR / "generated")))
DASHBOARD_COOKIE = "ung_cad_dashboard"

app = FastAPI(title="UNG-CAD-3D", version="1.4.0")


# ---------- Settings read at request time (so they can change without code edits) ----------

def _env_int(name, default):
    try:
        return int(float(os.getenv(name, str(default))))
    except ValueError:
        return default


def max_upload_bytes():
    return _env_int("UNG_CAD_MAX_UPLOAD_MB", 100) * 1024 * 1024


def max_zip_uncompressed_bytes():
    return _env_int("UNG_CAD_MAX_ZIP_UNCOMPRESSED_MB", 500) * 1024 * 1024


def max_zip_members():
    return _env_int("UNG_CAD_MAX_ZIP_MEMBERS", 1000)


def dashboard_token():
    return os.getenv("UNG_CAD_DASHBOARD_TOKEN") or None


# ---------- Database ----------

def now_iso():
    return datetime.now(timezone.utc).isoformat()


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def hash_api_key(raw_key: str) -> str:
    # API keys are 256-bit random tokens, so an unsalted SHA-256 is sufficient.
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _maybe_copy_legacy_db():
    """Old builds kept the DB next to the source (and served it via /static). Copy it once."""
    if os.getenv("UNG_CAD_3D_DB"):
        return
    if LEGACY_DB_PATH.exists() and not DB_PATH.exists():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(LEGACY_DB_PATH, DB_PATH)
        logger.warning("Copied legacy database %s -> %s. Delete the old file once you have verified the copy.",
                       LEGACY_DB_PATH, DB_PATH)


def _migrate_api_keys(c):
    """Convert a legacy plaintext api_keys table to hashed keys (existing keys keep working)."""
    cols = [r["name"] for r in c.execute("PRAGMA table_info(api_keys)").fetchall()]
    if "key" not in cols or "key_hash" in cols:
        return
    rows = c.execute("SELECT id, key, owner_system, active, created_at FROM api_keys").fetchall()
    c.execute("""CREATE TABLE api_keys_hashed (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key_hash TEXT NOT NULL UNIQUE,
        key_prefix TEXT NOT NULL,
        owner_system TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        revoked_at TEXT
    )""")
    for r in rows:
        c.execute(
            "INSERT INTO api_keys_hashed (id,key_hash,key_prefix,owner_system,active,created_at) VALUES (?,?,?,?,?,?)",
            (r["id"], hash_api_key(r["key"]), r["key"][:6], r["owner_system"], r["active"], r["created_at"]),
        )
    c.execute("DROP TABLE api_keys")
    c.execute("ALTER TABLE api_keys_hashed RENAME TO api_keys")
    logger.warning("Migrated %d API key(s) from plaintext to SHA-256 hashes.", len(rows))


def init_db():
    _maybe_copy_legacy_db()
    c = get_connection()
    c.execute(  # RECONSTRUCTED: truncated in PDF (columns after created_at inferred from list/update_scene)
        "CREATE TABLE IF NOT EXISTS scenes (id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,"
        "data_json TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL)"  # RECONSTRUCTED: truncated in PDF
    )
    c.execute("""CREATE TABLE IF NOT EXISTS machines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        kind TEXT NOT NULL,
        connection_type TEXT NOT NULL,
        config_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kind TEXT NOT NULL,
        source_name TEXT NOT NULL,
        machine_file TEXT,
        status TEXT NOT NULL,
        error_message TEXT,
        stats_json TEXT,
        submitted_by TEXT,
        created_at TEXT NOT NULL
    )""")
    _migrate_api_keys(c)
    c.execute("""CREATE TABLE IF NOT EXISTS api_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key_hash TEXT NOT NULL UNIQUE,
        key_prefix TEXT NOT NULL,
        owner_system TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        revoked_at TEXT
    )""")
    c.commit()
    c.close()


@app.on_event("startup")
def startup():
    init_db()
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    if not dashboard_token():
        banner = "!" * 78
        logger.warning(
            "\n%s\n!! UNG_CAD_DASHBOARD_TOKEN is NOT set: /api/manufacturing/*, /api/machines*,\n"
            "!! /api/jobs and /api/scenes* are OPEN to anyone who can reach this server.\n"
            "!! Set UNG_CAD_DASHBOARD_TOKEN in Railway -> Variables to require a token.\n%s",
            banner, banner,
        )
    if not os.getenv("UNG_CAD_ADMIN_TOKEN"):
        logger.warning("UNG_CAD_ADMIN_TOKEN is not set: API key management endpoints are disabled.")


class SceneIn(BaseModel):
    name: str
    data: dict


class MachineIn(BaseModel):
    name: str
    kind: str               # 3d_printer | cnc | laser
    connection_type: str    # bridge_lan | bridge_serial | manual
    config: dict = {}


def log_job(kind, source_name, machine_file, status, error_message, stats, submitted_by):
    c = get_connection()
    cur = c.execute(
        "INSERT INTO jobs (kind,source_name,machine_file,status,error_message,stats_json,submitted_by,created_at) VALUES (?,?,?,?,?,?,?,?)",
        (kind, source_name, machine_file, status, error_message, json.dumps(stats) if stats else None, submitted_by, now_iso())
    )
    c.commit()
    job_id = cur.lastrowid
    c.close()
    return job_id


# ---------- Auth helpers ----------

def _const_eq(a: Optional[str], b: Optional[str]) -> bool:
    if not a or not b:
        return False
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def _cookie_value_for(token: str) -> str:
    # The cookie holds a value derived from the token, not the token itself.
    return hmac.new(token.encode("utf-8"), b"ung-cad-dashboard-session-v1", hashlib.sha256).hexdigest()


def _api_key_owner(raw_key: Optional[str]):
    if not raw_key:
        return None
    c = get_connection()
    row = c.execute("SELECT owner_system FROM api_keys WHERE key_hash=? AND active=1", (hash_api_key(raw_key),)).fetchone()
    c.close()
    return row["owner_system"] if row else None


def dashboard_request_authorized(request: Request) -> bool:
    token = dashboard_token()
    if not token:
        return True   # open mode (loud warning logged at startup)
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer ") and _const_eq(auth[7:].strip(), token):
        return True
    if _const_eq(request.cookies.get(DASHBOARD_COOKIE), _cookie_value_for(token)):
        return True
    return False


DASHBOARD_PREFIXES = ("/api/manufacturing", "/api/machines", "/api/jobs", "/api/scenes")


def _is_dashboard_path(path: str) -> bool:
    return any(path == p or path.startswith(p + "/") for p in DASHBOARD_PREFIXES)


class UploadTooLarge(HTTPException):
    def __init__(self):
        super().__init__(413, f"Upload exceeds the {max_upload_bytes() // (1024 * 1024)} MB limit (UNG_CAD_MAX_UPLOAD_MB)")


class BodySizeLimitMiddleware:
    """
    Pure ASGI guard for bodies sent WITHOUT a Content-Length (chunked): counts bytes as
    they arrive and aborts with 413 once the limit is passed, before the whole body is
    spooled to disk by the multipart parser.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        limit = max_upload_bytes() + 1024 * 1024
        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    raise UploadTooLarge()
            return message

        response_started = False

        async def tracking_send(message):
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracking_send)
        except UploadTooLarge as exc:
            if response_started:
                raise
            response = JSONResponse({"detail": exc.detail}, status_code=413)
            await response(scope, receive, send)


# Registered BEFORE the http middleware below so it sits closer to the routes (inner layer):
# the 413 raised from receive() then reaches FastAPI as an HTTPException.
app.add_middleware(BodySizeLimitMiddleware)


@app.middleware("http")
async def dashboard_auth_and_size_limit(request: Request, call_next):
    # 1) request body size limit (fast path using Content-Length)
    limit = max_upload_bytes()
    overhead = 1024 * 1024   # multipart boundaries / form fields
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > limit + overhead:
        return JSONResponse({"detail": UploadTooLarge().detail}, status_code=413)

    # 2) dashboard token for the dashboard API routes
    if _is_dashboard_path(request.url.path) and not dashboard_request_authorized(request):
        # generated files may also be fetched by external systems with their API key
        is_download = request.url.path.startswith("/api/manufacturing/download/")
        if not (is_download and _api_key_owner(request.headers.get("x-ung-api-key"))):
            return JSONResponse(
                {"detail": "Dashboard token required (Authorization: Bearer <token> or POST /api/login)"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
    return await call_next(request)


async def read_upload(file: UploadFile) -> bytes:
    """Read an upload but never more than the configured limit (works without Content-Length too)."""
    limit = max_upload_bytes()
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise UploadTooLarge()
    return data


class LoginIn(BaseModel):
    token: str


@app.post("/api/login")
def login(payload: LoginIn, request: Request):
    token = dashboard_token()
    if not token:
        return {"ok": True, "auth_required": False}
    if not _const_eq(payload.token.strip(), token):
        raise HTTPException(401, "Invalid dashboard token")
    secure = request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
    resp = JSONResponse({"ok": True, "auth_required": True})
    resp.set_cookie(DASHBOARD_COOKIE, _cookie_value_for(token), httponly=True, samesite="strict",
                    secure=secure, max_age=60 * 60 * 24 * 30, path="/")
    return resp


@app.post("/api/logout")
def logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(DASHBOARD_COOKIE, path="/")
    return resp


@app.get("/api/auth/status")
def auth_status(request: Request):
    return {"auth_required": bool(dashboard_token()), "authorized": dashboard_request_authorized(request)}


# ---------- Pages (public) ----------

@app.get("/")
def root():
    return RedirectResponse(url="/studio.html")


@app.get("/studio.html")
def studio():
    return FileResponse(BASE_DIR / "studio.html")


@app.get("/studio")
def studio_short():
    return FileResponse(BASE_DIR / "studio.html")


@app.get("/viewer.html")
def viewer():
    return FileResponse(BASE_DIR / "viewer.html")


@app.get("/manufacturing.html")
def manufacturing():
    return FileResponse(BASE_DIR / "manufacturing.html")


@app.get("/drafting.html")
def drafting():
    return FileResponse(BASE_DIR / "drafting.html")


BRIDGE_ORIGIN_PLACEHOLDER = "https://YOUR-APP.up.railway.app"


@app.get("/ung-cad-ad5m-bridge.py")
def bridge():
    path = BASE_DIR / "ung-cad-ad5m-bridge.py"
    origin = os.getenv("UNG_CAD_PUBLIC_ORIGIN", "").strip().rstrip("/")
    if origin and re.fullmatch(r"https?://[A-Za-z0-9.-]+(:\d+)?", origin):
        # Pre-fill the bridge's CORS allowlist with this deployment's public origin.
        text = path.read_text(encoding="utf-8").replace(BRIDGE_ORIGIN_PLACEHOLDER, origin)
        return Response(text, media_type="text/x-python",
                        headers={"Content-Disposition": 'attachment; filename="ung-cad-ad5m-bridge.py"'})
    return FileResponse(path, filename="ung-cad-ad5m-bridge.py")


@app.get("/start-ad5m-bridge.bat")
def bridge_bat():
    return FileResponse(BASE_DIR / "start-ad5m-bridge.bat", filename="start-ad5m-bridge.bat")


@app.get("/start-ad5m-bridge.command")
def bridge_mac():
    return FileResponse(BASE_DIR / "start-ad5m-bridge.command", filename="start-ad5m-bridge.command",
                        media_type="application/octet-stream")


# ---------- Upload / ZIP handling ----------

def printable_entries(names):
    out = []
    for n in names:
        low = n.lower()
        if low.endswith((".stl", ".3mf", ".gcode", ".gx")) and not low.endswith("draco_gen1_full_assembly_reference.stl"):
            out.append(n)
    return out


def _unsafe_member_name(name: str) -> bool:
    norm = name.replace("\\", "/")
    if norm.startswith("/") or re.match(r"^[A-Za-z]:", norm):
        return True
    return ".." in norm.split("/")


def open_checked_zip(data: bytes) -> zipfile.ZipFile:
    """Open a ZIP and enforce member-count, total-uncompressed-size and path-safety limits."""
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise HTTPException(400, "Invalid ZIP")
    infos = z.infolist()
    if len(infos) > max_zip_members():
        z.close()
        raise HTTPException(400, f"ZIP has too many entries ({len(infos)} > {max_zip_members()})")
    total = sum(i.file_size for i in infos)
    if total > max_zip_uncompressed_bytes():
        z.close()
        raise HTTPException(400, "ZIP uncompressed size exceeds the limit (UNG_CAD_MAX_ZIP_UNCOMPRESSED_MB)")
    bad = [i.filename for i in infos if _unsafe_member_name(i.filename)]
    if bad:
        z.close()
        raise HTTPException(400, f"ZIP contains unsafe paths (absolute or '..'): {bad[0]}")
    return z


@app.post("/api/manufacturing/inspect")
async def inspect(file: UploadFile = File(...)):
    name = file.filename or "project"
    data = await read_upload(file)
    entries = []
    if name.lower().endswith(".zip"):
        with open_checked_zip(data) as z:
            entries = printable_entries([n for n in z.namelist() if not n.endswith("/")])
    elif name.lower().endswith((".stl", ".3mf", ".gcode", ".gx")):
        entries = [name]
    else:
        raise HTTPException(400, "Unsupported project type")
    if not entries:
        raise HTTPException(400, "No printable files found")
    return {"ok": True, "part_count": len(entries), "parts": [Path(n).name for n in entries],
            "printer_profile": "FlashForge Adventurer 5M",
            "assembly_reference_excluded": True}


async def read_selected(file: UploadFile, selected: str):
    data = await read_upload(file)
    if not data:
        raise HTTPException(400, "Empty package")
    if not selected:
        raise HTTPException(400, "Select a printable part")
    filename = file.filename or "upload"
    if filename.lower().endswith(".zip"):
        with open_checked_zip(data) as z:
            names = printable_entries([n for n in z.namelist() if not n.endswith("/")])
            target = next((n for n in names if Path(n).name == selected or n == selected), None)
            if not target:
                raise HTTPException(404, "Selected part not found in package")
            with z.open(target) as member:
                content = member.read(max_zip_uncompressed_bytes() + 1)
            return target, content
    if Path(filename).name == selected:
        return filename, data
    raise HTTPException(404, "Selected part not found")


def _safe_stem(name: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("._") or "part"
    return stem[:80]


def unique_output_path(stem: str, suffix: str) -> Path:
    """generated/<stem>_<UTC timestamp>_<random>_<suffix>.gcode - never collides between users/jobs."""
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return GENERATED_DIR / f"{_safe_stem(stem)}_{stamp}_{secrets.token_hex(4)}_{suffix}.gcode"


def _check_layer_height(layer_height: float):
    if not (0.08 <= layer_height <= 0.4):
        raise HTTPException(400, "Layer height must be 0.08–0.40 mm")


def _check_material(material: str) -> str:
    key = (material or "PLA").strip().upper()
    if key not in MATERIALS:
        raise HTTPException(400, f"material must be one of: {', '.join(MATERIALS)}")
    return key


def _check_compensation(xy_hole_comp_mm: float, elephant_foot_mm: float):
    if not (-1.0 <= xy_hole_comp_mm <= 1.0):
        raise HTTPException(400, "xy_hole_comp_mm must be between -1 and 1")
    if not (0.0 <= elephant_foot_mm <= 0.5):
        raise HTTPException(400, "elephant_foot_mm must be between 0 and 0.5")


def _slice_failure(e: Exception, source: str, submitted_by: str, log: bool = True):
    """Turn slicer exceptions into a 422 that still carries the validation warnings/errors."""
    content = {"detail": f"Slicing failed: {e}"}
    if isinstance(e, SliceValidationError):
        content = {"detail": f"Slicing blocked by pre-slice validation: {e}",
                   "errors": e.report["errors"], "warnings": e.report["warnings"], "validation": e.report}
    elif isinstance(e, GcodeCheckError):
        content = {"detail": f"Generated G-code failed the self-check and was not returned: {e}",
                   "problems": e.problems,
                   "warnings": (e.report or {}).get("warnings", []), "validation": e.report}
    if log:
        log_job("3d_printer", source, None, "failed", content["detail"], None, submitted_by)
    return JSONResponse(content, status_code=422)


def _run_3d_slice(data: bytes, source: str, submitted_by: str, layer_height: float, material: str,
                  xy_hole_comp_mm: float, elephant_foot_mm: float):
    try:
        result = slice_model(data, source, layer_height=layer_height, material=material,
                             xy_hole_comp_mm=xy_hole_comp_mm, elephant_foot_mm=elephant_foot_mm)
    except Exception as e:
        return None, _slice_failure(e, source, submitted_by)
    target = unique_output_path(Path(source).stem, "AD5M")
    target.write_bytes(result["gcode"])
    job_id = log_job("3d_printer", source, target.name, "sliced", None, result["stats"], submitted_by)
    return {"job_id": job_id, "target": target, "stats": result["stats"], "report": result["report"]}, None


@app.post("/api/manufacturing/slice")
async def slice_part(file: UploadFile = File(...), selected: str = Form(...), layer_height: float = Form(0.20),
                     material: str = Form("PLA"), xy_hole_comp_mm: float = Form(0.0),
                     elephant_foot_mm: float = Form(0.1)):
    _check_layer_height(layer_height)
    material = _check_material(material)
    _check_compensation(xy_hole_comp_mm, elephant_foot_mm)
    source_name, data = await read_selected(file, selected)
    if not source_name.lower().endswith(".stl"):
        raise HTTPException(400, "Only STL geometry can be sliced here")
    done, failure = _run_3d_slice(data, Path(source_name).name, "dashboard", layer_height, material,
                                  xy_hole_comp_mm, elephant_foot_mm)
    if failure:
        return failure
    target = done["target"]
    return {"ok": True, "status": "sliced", "job_id": done["job_id"], "source": Path(source_name).name,
            "machine_file": target.name, "download": f"/api/manufacturing/download/{target.name}",
            "printer": "FlashForge Adventurer 5M", "stats": done["stats"],
            "warnings": done["report"]["warnings"], "errors": done["report"]["errors"],
            "validation": done["report"],
            "transmission": "local AD5M bridge required"}


@app.post("/api/manufacturing/preview")
async def preview_part(file: UploadFile = File(...), selected: str = Form(...), layer_height: float = Form(0.20),
                       material: str = Form("PLA"), xy_hole_comp_mm: float = Form(0.0),
                       elephant_foot_mm: float = Form(0.1), max_layers: int = Form(400)):
    """Same inputs as /slice; returns per-layer toolpaths as JSON (no G-code file is written)."""
    _check_layer_height(layer_height)
    material = _check_material(material)
    _check_compensation(xy_hole_comp_mm, elephant_foot_mm)
    source_name, data = await read_selected(file, selected)
    if not source_name.lower().endswith(".stl"):
        raise HTTPException(400, "Only STL geometry can be previewed here")
    try:
        return preview_stl(data, Path(source_name).name, max_layers=max(1, min(max_layers, 2000)),
                           layer_height=layer_height, material=material,
                           xy_hole_comp_mm=xy_hole_comp_mm, elephant_foot_mm=elephant_foot_mm)
    except Exception as e:
        return _slice_failure(e, Path(source_name).name, "dashboard", log=False)


@app.get("/api/manufacturing/download/{name}")
def download_machine_file(name: str):
    safe = Path(name).name
    target = (GENERATED_DIR / safe).resolve()
    if target.parent != GENERATED_DIR.resolve() or not target.is_file():
        raise HTTPException(404, "Machine file not found")
    return FileResponse(target, media_type="application/octet-stream", filename=safe)


@app.get("/api/manufacturing/health")
def manufacturing_health():
    return {"ok": True, "slicer": "available", "printer_profile": "FlashForge Adventurer 5M",
            "materials": list(MATERIALS),
            "direct_railway_printer_connection": False, "local_bridge_required": True}


# ---------- CNC / laser toolpath generation (from the 2D drafting tool) ----------

class CncSliceIn(BaseModel):
    shapes: list
    drawing_name: str = "drawing"
    settings: dict = {}


def _run_cnc_slice(payload: CncSliceIn, submitted_by: str):
    try:
        resolved = resolve_settings(payload.settings)
    except ValueError as e:
        raise HTTPException(400, str(e))
    mode = resolved["mode"]
    try:
        gcode, path_count, est_seconds = slice_shapes_to_gcode(payload.shapes, payload.settings)
    except Exception as e:
        log_job(mode, payload.drawing_name, None, "failed", str(e), None, submitted_by)
        raise HTTPException(422, f"CNC/laser toolpath generation failed: {e}")
    target = unique_output_path(payload.drawing_name, mode)
    target.write_text(gcode)
    stats = {"paths": path_count, "estimated_seconds": est_seconds, "mode": mode,
             "work_origin": "bottom-left of drawing (X0 Y0), Y up"}
    job_id = log_job(mode, payload.drawing_name, target.name, "sliced", None, stats, submitted_by)
    return {"ok": True, "status": "sliced", "job_id": job_id, "mode": mode, "machine_file": target.name,
            "download": f"/api/manufacturing/download/{target.name}", "stats": stats}


@app.post("/api/manufacturing/cnc-slice")
def cnc_slice(payload: CncSliceIn):
    return _run_cnc_slice(payload, "dashboard")


# ---------- Machine registry ----------

@app.post("/api/machines")
def create_machine(m: MachineIn):
    if m.kind not in ("3d_printer", "cnc", "laser"):
        raise HTTPException(400, "kind must be one of: 3d_printer, cnc, laser")
    if m.connection_type not in ("bridge_lan", "bridge_serial", "manual"):
        raise HTTPException(400, "connection_type must be one of: bridge_lan, bridge_serial, manual")
    c = get_connection()
    cur = c.execute("INSERT INTO machines (name,kind,connection_type,config_json,created_at) VALUES (?,?,?,?,?)",
                    (m.name, m.kind, m.connection_type, json.dumps(m.config), now_iso()))
    c.commit()
    mid = cur.lastrowid
    c.close()
    return {"id": mid, "status": "created"}


@app.get("/api/machines")
def list_machines():
    c = get_connection()
    rows = c.execute("SELECT * FROM machines ORDER BY created_at DESC").fetchall()
    c.close()
    out = []
    for r in rows:
        d = dict(r)
        d["config"] = json.loads(d.pop("config_json"))
        out.append(d)
    return out


@app.delete("/api/machines/{machine_id}")
def delete_machine(machine_id: int):
    c = get_connection()
    c.execute("DELETE FROM machines WHERE id=?", (machine_id,))
    c.commit()
    c.close()
    return {"status": "deleted"}


# ---------- Job history (both 3D print and CNC/laser jobs) ----------

@app.get("/api/jobs")
def list_jobs(limit: int = 100):
    limit = max(1, min(limit, 1000))
    c = get_connection()
    rows = c.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    c.close()
    out = []
    for r in rows:
        d = dict(r)
        d["stats"] = json.loads(d.pop("stats_json")) if d.get("stats_json") else None
        out.append(d)
    return out


# ---------- External API - lets other UNG systems submit jobs here ----------

def require_api_key(x_ung_api_key: str = Header(default=None)):
    if not x_ung_api_key:
        raise HTTPException(401, "Missing X-UNG-API-Key header")
    owner = _api_key_owner(x_ung_api_key)
    if not owner:
        raise HTTPException(401, "Invalid or inactive API key")
    return owner


def _require_admin(token: Optional[str]):
    expected = os.getenv("UNG_CAD_ADMIN_TOKEN")
    if not expected or not _const_eq(token, expected):
        raise HTTPException(403, "Invalid admin token")


class ApiKeyIn(BaseModel):
    owner_system: str
    admin_token: str


class ApiKeyRevokeIn(BaseModel):
    admin_token: str
    key_id: Optional[int] = None
    api_key: Optional[str] = None


@app.post("/api/admin/api-keys")
def create_api_key(payload: ApiKeyIn):
    """
    Requires UNG_CAD_ADMIN_TOKEN env var to be set on the server and matched here,
    so random callers can't mint themselves API keys.
    Only a SHA-256 hash is stored; the raw key is returned exactly once.
    """
    _require_admin(payload.admin_token)
    new_key = secrets.token_urlsafe(32)
    c = get_connection()
    cur = c.execute("INSERT INTO api_keys (key_hash,key_prefix,owner_system,active,created_at) VALUES (?,?,?,1,?)",
                    (hash_api_key(new_key), new_key[:6], payload.owner_system, now_iso()))
    c.commit()
    key_id = cur.lastrowid
    c.close()
    return {"id": key_id, "api_key": new_key, "key_prefix": new_key[:6], "owner_system": payload.owner_system,
            "note": "Store this key now - it is not stored on the server and cannot be shown again."}


@app.get("/api/admin/api-keys")
def list_api_keys(x_ung_admin_token: str = Header(default=None)):
    _require_admin(x_ung_admin_token)
    c = get_connection()
    rows = c.execute("SELECT id,key_prefix,owner_system,active,created_at,revoked_at FROM api_keys ORDER BY id").fetchall()
    c.close()
    return [dict(r) for r in rows]


@app.post("/api/admin/api-keys/revoke")
def revoke_api_key(payload: ApiKeyRevokeIn):
    _require_admin(payload.admin_token)
    if payload.key_id is None and not payload.api_key:
        raise HTTPException(400, "Provide key_id or api_key")
    c = get_connection()
    if payload.key_id is not None:
        cur = c.execute("UPDATE api_keys SET active=0, revoked_at=? WHERE id=? AND active=1", (now_iso(), payload.key_id))
    else:
        cur = c.execute("UPDATE api_keys SET active=0, revoked_at=? WHERE key_hash=? AND active=1",
                        (now_iso(), hash_api_key(payload.api_key)))
    c.commit()
    changed = cur.rowcount
    c.close()
    if not changed:
        raise HTTPException(404, "Active API key not found")
    return {"status": "revoked"}


@app.post("/api/v1/slice/3d")
async def api_slice_3d(file: UploadFile = File(...), layer_height: float = Form(0.20), material: str = Form("PLA"),
                       xy_hole_comp_mm: float = Form(0.0), elephant_foot_mm: float = Form(0.1),
                       owner_system: str = Depends(require_api_key)):
    _check_layer_height(layer_height)
    material = _check_material(material)
    _check_compensation(xy_hole_comp_mm, elephant_foot_mm)
    data = await read_upload(file)
    filename = file.filename or "upload.stl"
    done, failure = _run_3d_slice(data, filename, owner_system, layer_height, material,
                                  xy_hole_comp_mm, elephant_foot_mm)
    if failure:
        return failure
    target = done["target"]
    return {"ok": True, "job_id": done["job_id"], "machine_file": target.name,
            "download": f"/api/manufacturing/download/{target.name}", "stats": done["stats"],
            "warnings": done["report"]["warnings"], "errors": done["report"]["errors"]}


@app.post("/api/v1/slice/cnc")
def api_slice_cnc(payload: CncSliceIn, owner_system: str = Depends(require_api_key)):
    result = _run_cnc_slice(payload, owner_system)
    return {"ok": True, "job_id": result["job_id"], "machine_file": result["machine_file"],
            "download": result["download"], "stats": result["stats"]}


@app.get("/api/v1/jobs/{job_id}")
def api_get_job(job_id: int, owner_system: str = Depends(require_api_key)):
    c = get_connection()
    row = c.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    c.close()
    if not row:
        raise HTTPException(404, "Job not found")
    d = dict(row)
    d["stats"] = json.loads(d.pop("stats_json")) if d.get("stats_json") else None
    return d


@app.get("/api/v1/machines")
def api_list_machines(owner_system: str = Depends(require_api_key)):
    return list_machines()


# ---------- Scenes (3D modeling save/load) ----------

@app.get("/api/scenes")
def list_scenes():
    c = get_connection()
    rows = c.execute("SELECT id,name,created_at,updated_at FROM scenes ORDER BY updated_at DESC").fetchall()
    c.close()
    return [dict(r) for r in rows]  # RECONSTRUCTED: truncated in PDF


@app.get("/api/scenes/{scene_id}")
def get_scene(scene_id: int):
    c = get_connection()
    row = c.execute("SELECT * FROM scenes WHERE id=?", (scene_id,)).fetchone()
    c.close()
    if not row:
        raise HTTPException(404, "Scene not found")
    r = dict(row)
    r["data"] = json.loads(r.pop("data_json"))
    return r


@app.post("/api/scenes")
def create_scene(scene: SceneIn):
    c = get_connection()
    n = now_iso()
    q = c.execute("INSERT INTO scenes (name,data_json,created_at,updated_at) VALUES (?,?,?,?)",
                  (scene.name, json.dumps(scene.data), n, n))  # RECONSTRUCTED: truncated in PDF
    c.commit()  # RECONSTRUCTED: truncated in PDF
    scene_id = q.lastrowid  # RECONSTRUCTED: truncated in PDF
    c.close()  # RECONSTRUCTED: truncated in PDF
    return {"id": scene_id, "status": "created"}  # RECONSTRUCTED: truncated in PDF (return shape guessed - check studio.html)


@app.put("/api/scenes/{scene_id}")
def update_scene(scene_id: int, scene: SceneIn):
    c = get_connection()
    if not c.execute("SELECT id FROM scenes WHERE id=?", (scene_id,)).fetchone():
        c.close()
        raise HTTPException(404, "Scene not found")
    c.execute("UPDATE scenes SET name=?,data_json=?,updated_at=? WHERE id=?",
              (scene.name, json.dumps(scene.data), now_iso(), scene_id))
    c.commit()
    c.close()  # RECONSTRUCTED: truncated in PDF
    return {"id": scene_id, "status": "updated"}  # RECONSTRUCTED: truncated in PDF (return shape guessed - check studio.html)


@app.delete("/api/scenes/{scene_id}")
def delete_scene(scene_id: int):
    c = get_connection()
    c.execute("DELETE FROM scenes WHERE id=?", (scene_id,))
    c.commit()
    c.close()
    return {"status": "deleted"}


@app.get("/health")
def health():
    return {"system": "UNG-CAD-3D", "status": "ok", "ui": "/studio.html", "manufacturing": "/manufacturing.html",
            "drafting": "/drafting.html (now with CNC/laser G-code export)",
            "ad5m_bridge": "/ung-cad-ad5m-bridge.py", "external_api": "/api/v1/* (requires X-UNG-API-Key header)"}


# ---------- Static front-end assets ----------
# Only front-end files are served. Lookup order for /static/<path>:
#   1. public/<path>   (anything except blocked extensions)
#   2. <app dir>/<path> only if the extension is a front-end type below.
# The database, Python source, .env files, generated G-code, tests etc. are never served.

STATIC_EXTENSIONS = {
    ".html", ".htm", ".js", ".mjs", ".css", ".map",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
    ".woff", ".woff2", ".ttf", ".otf",
    ".glb", ".gltf", ".wasm",
}
STATIC_BLOCKED_EXTENSIONS = {".db", ".sqlite", ".sqlite3", ".db-journal", ".db-wal", ".db-shm",
                             ".py", ".pyc", ".env", ".ini", ".toml", ".cfg", ".log", ".bak"}
STATIC_DENIED_DIRS = {"data", "generated", "tests", "__pycache__", "venv", ".venv", "node_modules", ".git"}


def static_path_allowed(full_path: str) -> bool:
    try:
        p = Path(full_path).resolve()
    except OSError:
        return False
    try:
        if p == DB_PATH.resolve():
            return False
    except OSError:
        pass
    suffix = p.suffix.lower()
    if suffix in STATIC_BLOCKED_EXTENSIONS or p.name.lower().endswith(tuple(STATIC_BLOCKED_EXTENSIONS)):
        return False
    for root, whitelist_only in ((PUBLIC_DIR.resolve(), False), (BASE_DIR, True)):
        try:
            rel = p.relative_to(root)
        except ValueError:
            continue
        if any(part.startswith(".") for part in rel.parts):
            return False
        if whitelist_only:
            if rel.parts and rel.parts[0] in STATIC_DENIED_DIRS:
                return False
            if rel.parts and rel.parts[0] == "public":
                return True
            return suffix in STATIC_EXTENSIONS
        return True
    return False


class FrontendStaticFiles(StaticFiles):
    def __init__(self, directories):
        super().__init__(directory=str(directories[-1]))
        self.all_directories = [str(d) for d in directories]

    def lookup_path(self, path):
        full_path, stat_result = super().lookup_path(path)
        if stat_result is None or not static_path_allowed(full_path):
            return "", None
        return full_path, stat_result


_static_dirs = [PUBLIC_DIR, BASE_DIR] if PUBLIC_DIR.is_dir() else [BASE_DIR]
app.mount("/static", FrontendStaticFiles(_static_dirs), name="static")
