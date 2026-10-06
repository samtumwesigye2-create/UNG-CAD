"""
UNG-CAD local bridge: FlashForge Adventurer 5M (LAN) + GRBL-style CNC/laser (USB serial).

Security model (this process can move real machines, so it is locked down):
  * Listens on 127.0.0.1 only.
  * Browser requests are accepted only from allowed origins
    (env UNG_CAD_ALLOWED_ORIGINS, comma separated; entries without a port match any
    port, e.g. http://localhost matches http://localhost:8000).
  * Every request except GET /health needs the pairing token printed in this
    terminal at startup, sent as header  X-UNG-Bridge-Token: <token>.
    Set UNG_CAD_BRIDGE_TOKEN to keep the same token across restarts.
  * /print uploads only; it starts the print only with header  X-Confirm-Start: true.
  * /serial/send runs as a background job with /serial/status and /serial/stop.
"""
import asyncio
import hmac
import json
import os
import secrets
import tempfile
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


HOST = "127.0.0.1"
PORT = 8765
BRIDGE_VERSION = "2026-09-20-3"   # kept the same as before: studio.html checks this exact string
BRIDGE_API = 2                    # new: token + confirm-start + background serial jobs
STATE = {"printer": None, "check_code": None}

# Replaced automatically with the real origin when downloaded from a server that has
# UNG_CAD_PUBLIC_ORIGIN set; otherwise set UNG_CAD_ALLOWED_ORIGINS or edit this line.
DEFAULT_RAILWAY_ORIGIN = "https://YOUR-APP.up.railway.app"
DEFAULT_ALLOWED_ORIGINS = [DEFAULT_RAILWAY_ORIGIN, "http://localhost", "http://127.0.0.1"]

ALLOWED_HEADERS = ("Content-Type, X-UNG-Bridge-Token, X-Filename, X-Level, X-Confirm-Start, "
                   "X-Port, X-Baud, X-Line-Timeout, X-Machine-Mode")
MAX_BODY_BYTES = int(float(os.getenv("UNG_CAD_BRIDGE_MAX_MB", "200")) * 1024 * 1024)

OPEN_SETTLE_SECONDS = 2.0     # let the controller finish resetting after the port opens
DEFAULT_LINE_TIMEOUT = 30.0   # seconds to wait for "ok" per line
DRAIN_TIMEOUT = 1800.0        # seconds to wait for the final G4 P0 (all motion finished)
READ_TIMEOUT = 0.5            # serial readline timeout, so stop requests are noticed quickly


def load_allowed_origins():
    raw = os.getenv("UNG_CAD_ALLOWED_ORIGINS", "")
    items = [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]
    return items or list(DEFAULT_ALLOWED_ORIGINS)


ALLOWED_ORIGINS = load_allowed_origins()
BRIDGE_TOKEN = os.getenv("UNG_CAD_BRIDGE_TOKEN") or secrets.token_hex(8)


def origin_allowed(origin, allowed=None):
    """Exact match, or scheme+host match for allowlist entries that have no explicit port."""
    if not origin:
        return False
    allowed = ALLOWED_ORIGINS if allowed is None else allowed
    o = urlparse(origin.strip())
    if not o.scheme or not o.hostname:
        return False
    for entry in allowed:
        a = urlparse(entry)
        if a.scheme != o.scheme or (a.hostname or "").lower() != o.hostname.lower():
            continue
        if a.port is None or a.port == o.port:
            return True
    return False


# ---------- FlashForge Adventurer 5M ----------
# Imported lazily so this bridge still runs for CNC/laser-only setups that
# haven't installed the flashforge-python-api package.

def _flashforge():
    try:
        from flashforge import FlashForgeClient, FiveMClientConnectionOptions, PrinterDiscovery
        return FlashForgeClient, FiveMClientConnectionOptions, PrinterDiscovery
    except ImportError:
        raise RuntimeError("flashforge-python-api not installed — run: pip install flashforge-python-api")


async def discover():
    _, FiveMClientConnectionOptions, PrinterDiscovery = _flashforge()
    found = await PrinterDiscovery().discover()
    return [
        {"name": p.name, "ip": p.ip_address, "serial": p.serial_number,
         "http_port": p.event_port, "tcp_port": p.command_port}  # RECONSTRUCTED: truncated in PDF
        for p in found if p.serial_number  # RECONSTRUCTED: truncated in PDF
    ]


async def connect(check_code):
    FlashForgeClient, FiveMClientConnectionOptions, PrinterDiscovery = _flashforge()
    found = await PrinterDiscovery().discover()
    if not found:
        raise RuntimeError("No FlashForge printer discovered on this LAN")
    p = next((x for x in found if x.serial_number), None)
    if not p:
        raise RuntimeError("Discovered printer did not report a serial number")
    opts = FiveMClientConnectionOptions(http_port=p.event_port, tcp_port=p.command_port)
    async with FlashForgeClient(p.ip_address, p.serial_number, check_code, options=opts) as c:
        try:
            info = await c.get_printer_status()
        except Exception as e:
            msg = str(e)
            if "Access code is different" in msg or "access code is different" in msg:
                raise RuntimeError("Access Code mismatch — enter the CURRENT Access Code / Check Code shown in the printer Network settings")
            raise
        if not info:
            raise RuntimeError("Printer rejected connection / Access Code")
        STATE["printer"] = {
            "name": c.printer_name or p.name, "ip": p.ip_address, "serial": p.serial_number,
            "firmware": c.firmware_version,
            "http_port": p.event_port, "tcp_port": p.command_port,  # RECONSTRUCTED: truncated in PDF
        }
        STATE["check_code"] = check_code
        return STATE["printer"]


async def print_file(path, level=True, start=False):
    """Upload the file; start it only when start=True (explicit confirmation from the user)."""
    FlashForgeClient, FiveMClientConnectionOptions, PrinterDiscovery = _flashforge()
    if not STATE["check_code"]:
        raise RuntimeError("Pair printer first")
    found = await PrinterDiscovery().discover()
    serial = STATE["printer"]["serial"]
    p = next((x for x in found if x.serial_number == serial), None)
    if not p:
        raise RuntimeError("Paired printer is not discoverable")
    opts = FiveMClientConnectionOptions(http_port=p.event_port, tcp_port=p.command_port)
    async with FlashForgeClient(p.ip_address, p.serial_number, STATE["check_code"], options=opts) as c:
        info = await c.get_printer_status()
        if not info:
            raise RuntimeError("Printer connection failed")
        await c.init_control()
        uploaded = await c.job_control.upload_file(path, start_print=False, level_before_print=level)
        if not uploaded:
            raise RuntimeError("Printer rejected file upload")
        if not start:
            return {"uploaded": True, "started": False, "file": Path(path).name, "mode": "upload_only",
                    "note": "Send again with header X-Confirm-Start: true to start the print"}
        started = await c.job_control.print_local_file(Path(path).name, leveling_before_print=level)
        if not started:
            raise RuntimeError("File uploaded but printer rejected explicit start command")
        return {"uploaded": True, "started": True, "file": Path(path).name, "mode": "upload_then_explicit_start"}


# ---------- CNC / laser over USB serial (GRBL-style controllers) ----------
# Covers hobby CNC routers and laser cutters running GRBL/Marlin-style
# firmware, which is the large majority of USB-connected machines.

def list_serial_ports():
    import serial.tools.list_ports          # pyserial
    return [{"device": p.device, "description": p.description} for p in serial.tools.list_ports.comports()]


def open_serial(port, baud):
    """Transport factory (replaced by a fake in tests)."""
    import serial         # pyserial
    return serial.Serial(port, baud, timeout=READ_TIMEOUT, write_timeout=5)


class SerialJob:
    def __init__(self, port, baud, lines, line_timeout, mode):
        self.id = uuid.uuid4().hex[:12]
        self.port = port
        self.baud = baud
        self.lines = lines
        self.line_timeout = line_timeout
        self.mode = mode
        self.state = "starting"     # starting -> running -> finishing -> completed | error | stopped
        self.sent = 0
        self.error = None
        self.started_at = time.time()
        self.finished_at = None
        self.stop_event = threading.Event()
        self.write_lock = threading.Lock()
        self.port_lock = threading.RLock()   # held while a stop sequence runs, so the port can't close mid-stop
        self.ser = None
        self.thread = None

    def status(self):
        total = len(self.lines)
        return {
            "job_id": self.id, "state": self.state, "port": self.port, "baud": self.baud, "mode": self.mode,
            "sent_lines": self.sent, "total_lines": total,
            "progress": round(self.sent / total, 4) if total else 1.0,
            "error": self.error, "started_at": self.started_at, "finished_at": self.finished_at,
            "active": self.state in ("starting", "running", "finishing"),
        }

    def write(self, data: bytes):
        with self.write_lock:
            if self.ser is not None:
                self.ser.write(data)

    def _wait_ok(self, timeout, what):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.stop_event.is_set():
                return False
            resp = self.ser.readline().decode(errors="ignore").strip()
            low = resp.lower()
            if low.startswith("ok"):
                return True
            if low.startswith("error") or low.startswith("alarm"):
                raise RuntimeError(f"Machine reported {resp} at {what}")
        raise RuntimeError(f"No 'ok' from the controller within {timeout:g}s at {what} - job aborted")

    def run(self):
        try:
            self.ser = open_serial(self.port, self.baud)
            time.sleep(OPEN_SETTLE_SECONDS)
            self.ser.reset_input_buffer()
            self.state = "running"
            for i, line in enumerate(self.lines):
                if self.stop_event.is_set():
                    break
                self.write((line + "\n").encode())
                if not self._wait_ok(self.line_timeout, f"line {i + 1}: {line}"):
                    break
                self.sent = i + 1
            if not self.stop_event.is_set():
                # G4 P0 is acknowledged only once every buffered move has finished.
                self.state = "finishing"
                self.write(b"G4 P0\n")
                self._wait_ok(DRAIN_TIMEOUT, "end of job (waiting for motion to finish)")
            if self.stop_event.is_set():
                with self.port_lock:     # wait until the stop sequence has been sent
                    self.state = "stopped"
            else:
                self.state = "completed"
        except Exception as e:
            self.error = str(e)
            try:
                with self.port_lock:
                    safe_stop_sequence(self.write, self.mode)   # never leave a laser/spindle running
            except Exception:
                pass
            self.state = "error"
        finally:
            with self.port_lock:
                self.finished_at = time.time()
                with self.write_lock:
                    try:
                        if self.ser is not None:
                            self.ser.close()
                    except Exception:
                        pass
                    self.ser = None


def safe_stop_sequence(write, mode=None):
    """GRBL feed hold, soft reset, then M5 (laser/spindle off)."""
    write(b"!")          # feed hold: decelerate to a stop
    time.sleep(0.2)
    write(b"\x18")       # soft reset (Ctrl-X): flush buffers, stop spindle/laser
    time.sleep(0.5)
    write(b"M5\n")       # explicit laser/spindle off (harmless if already off)


JOB_LOCK = threading.Lock()
JOBS = {"current": None}


def start_serial_job(port, baud, gcode_text, line_timeout=DEFAULT_LINE_TIMEOUT, mode=None):
    lines = [l.strip() for l in gcode_text.splitlines() if l.strip() and not l.strip().startswith(";")]
    with JOB_LOCK:
        cur = JOBS["current"]
        if cur is not None and cur.status()["active"]:
            raise RuntimeError("busy")
        job = SerialJob(port, baud, lines, line_timeout, mode)
        JOBS["current"] = job
        job.thread = threading.Thread(target=job.run, name=f"serial-job-{job.id}", daemon=True)
        job.thread.start()
    return job


def stop_serial_job(port=None, baud=115200):
    job = JOBS["current"]
    if job is not None and job.status()["active"]:
        with job.port_lock:              # keep the port open until the whole stop sequence is sent
            job.stop_event.set()
            safe_stop_sequence(job.write, job.mode)
        job.thread.join(timeout=5)
        return {"stopped": True, "job": job.status()}
    # No active job (e.g. all lines sent but the machine is still moving): open the port and stop.
    port = port or (job.port if job is not None else None)
    if not port:
        return {"stopped": False, "reason": "no active job and no X-Port given"}
    ser = open_serial(port, baud if job is None else job.baud)
    try:
        safe_stop_sequence(lambda b: ser.write(b))
    finally:
        ser.close()
    return {"stopped": True, "job": job.status() if job is not None else None, "port": port}


# ---------- HTTP server ----------

class H(BaseHTTPRequestHandler):
    server_version = "UNG-CAD-Bridge"

    # --- helpers ---
    def _origin(self):
        return self.headers.get("Origin")

    def _cors_headers(self):
        # RECONSTRUCTED: the original one-line cors() was truncated in the PDF; rewritten with the origin allowlist
        origin = self._origin()
        if origin and origin_allowed(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Headers", ALLOWED_HEADERS)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Max-Age", "600")

    def cors(self, code=200, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self._cors_headers()
        self.end_headers()

    def out(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _host_ok(self):
        host = (self.headers.get("Host") or "").split(":")[0].lower()
        return host in ("127.0.0.1", "localhost", "")

    def _guard(self, need_token=True):
        """Origin/Host/token checks. Returns True if the request may proceed (else a response was sent)."""
        origin = self._origin()
        if origin and not origin_allowed(origin):
            self.out({"error": "Origin not allowed. Add it to UNG_CAD_ALLOWED_ORIGINS on the bridge."}, 403)
            return False
        if not self._host_ok():
            self.out({"error": "Bad Host header"}, 403)
            return False
        if need_token:
            token = self.headers.get("X-UNG-Bridge-Token", "")
            if not token or not hmac.compare_digest(token.encode(), BRIDGE_TOKEN.encode()):
                self.out({"error": "Bridge token required: enter the token shown in the bridge terminal",
                          "token_required": True}, 401)
                return False
        return True

    def _read_body(self):
        n = int(self.headers.get("Content-Length", "0") or 0)
        if n > MAX_BODY_BYTES:
            raise ValueError(f"Body larger than {MAX_BODY_BYTES // (1024 * 1024)} MB")
        return self.rfile.read(n) if n > 0 else b""

    # --- verbs ---
    def do_OPTIONS(self):
        origin = self._origin()
        if not origin or not origin_allowed(origin):
            self.send_response(403)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_response(204)
        self._cors_headers()
        if (self.headers.get("Access-Control-Request-Private-Network") or "").lower() == "true":
            self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        try:
            url = urlparse(self.path)
            path = url.path
            if path == "/health":
                if not self._guard(need_token=False):
                    return
                printer = STATE["printer"]
                return self.out({"ok": True, "bridge": "UNG-CAD", "version": BRIDGE_VERSION, "api": BRIDGE_API,
                                 "token_required": True, "paired": printer is not None,
                                 "printer": {"name": printer["name"]} if printer else None})
            if not self._guard():
                return
            if path == "/discover":
                return self.out({"printers": asyncio.run(discover())})
            if path == "/printer":
                return self.out({"printer": STATE["printer"]})
            if path == "/serial/ports":
                try:
                    return self.out({"ports": list_serial_ports()})
                except ImportError:
                    return self.out({"error": "pyserial not installed — run: pip install pyserial"}, 500)
            if path == "/serial/status":
                job = JOBS["current"]
                qs = parse_qs(url.query)
                if job is not None and qs.get("job_id") and qs["job_id"][0] != job.id:
                    return self.out({"error": "unknown job_id"}, 404)
                return self.out({"job": job.status() if job else None})
            return self.out({"error": "not found"}, 404)
        except Exception as e:
            self.out({"error": str(e)}, 500)

    def do_POST(self):
        try:
            path = urlparse(self.path).path
            if not self._guard():
                return
            if path == "/pair":
                data = json.loads(self._read_body() or b"{}")
                code = str(data.get("printer_id", "")).strip()
                if not code:
                    return self.out({"error": "Printer ID required"}, 400)
                return self.out({"paired": True, "printer": asyncio.run(connect(code))})
            if path == "/print":
                name = self.headers.get("X-Filename", "print.gcode")
                if not name.lower().endswith((".gcode", ".gx", ".3mf")):
                    return self.out({"error": "File must already be sliced (.gcode/.gx/.3mf)"}, 400)
                raw = self._read_body()
                if not raw:
                    return self.out({"error": "Empty file body"}, 400)
                start = (self.headers.get("X-Confirm-Start") or "").strip().lower() == "true"
                level = (self.headers.get("X-Level") or "true").lower() == "true"
                safe_name = Path(name).name
                tmpdir = tempfile.mkdtemp(prefix="ungcad_")
                file_path = str(Path(tmpdir) / safe_name)
                Path(file_path).write_bytes(raw)
                try:
                    return self.out(asyncio.run(print_file(file_path, level, start=start)))
                finally:
                    try:
                        os.unlink(file_path)
                        os.rmdir(tmpdir)
                    except OSError:
                        pass
            if path == "/serial/send":
                port = self.headers.get("X-Port")
                if not port:
                    return self.out({"error": "X-Port header required (e.g. /dev/ttyUSB0 or COM3)"}, 400)
                try:
                    baud = int(self.headers.get("X-Baud", "115200"))
                    line_timeout = float(self.headers.get("X-Line-Timeout", str(DEFAULT_LINE_TIMEOUT)))
                except ValueError:
                    return self.out({"error": "X-Baud / X-Line-Timeout must be numbers"}, 400)
                line_timeout = max(1.0, min(line_timeout, 600.0))
                mode = self.headers.get("X-Machine-Mode")
                gcode_text = self._read_body().decode(errors="ignore")
                if not gcode_text.strip():
                    return self.out({"error": "Empty G-code body"}, 400)
                try:
                    job = start_serial_job(port, baud, gcode_text, line_timeout, mode)
                except RuntimeError as e:
                    if str(e) == "busy":
                        return self.out({"error": "A serial job is already running - stop it first",
                                         "job": JOBS["current"].status()}, 409)
                    raise
                return self.out({"ok": True, "job_id": job.id, "state": job.state,
                                 "total_lines": len(job.lines)}, 202)
            if path == "/serial/stop":
                try:
                    baud = int(self.headers.get("X-Baud", "115200"))
                except ValueError:
                    baud = 115200
                try:
                    return self.out(stop_serial_job(self.headers.get("X-Port"), baud))
                except ImportError:
                    return self.out({"error": "pyserial not installed — run: pip install pyserial"}, 500)
            return self.out({"error": "not found"}, 404)
        except Exception as e:
            self.out({"error": str(e)}, 500)

    def log_message(self, *args):
        pass


def make_server(host=HOST, port=PORT):
    return ThreadingHTTPServer((host, port), H)


if __name__ == "__main__":
    print(f"UNG-CAD bridge ready on http://{HOST}:{PORT}  (version {BRIDGE_VERSION}, api {BRIDGE_API})")
    print("Handles: FlashForge Adventurer 5M (LAN) and CNC/laser controllers (USB serial)")
    print("")
    print("  PAIRING TOKEN:  " + BRIDGE_TOKEN)
    print("  Enter this token in the UNG-CAD page when asked (it is stored in that browser).")
    print("")
    print("Allowed browser origins: " + ", ".join(ALLOWED_ORIGINS))
    if DEFAULT_RAILWAY_ORIGIN in ALLOWED_ORIGINS and "YOUR-APP" in DEFAULT_RAILWAY_ORIGIN:
        print("WARNING: the Railway origin is still a placeholder. Set UNG_CAD_ALLOWED_ORIGINS,")
        print("         e.g. UNG_CAD_ALLOWED_ORIGINS=https://your-app.up.railway.app")
    make_server().serve_forever()
