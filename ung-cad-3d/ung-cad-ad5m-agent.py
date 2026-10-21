"""UNG-CAD AD5M agent.

Runs the existing local bridge unchanged and adds:
  * a printer probe + cloud heartbeat, so the Manufacturing page shows the real printer state;
  * a print-job loop: when you press Print on the Manufacturing page, Railway queues the job,
    this agent downloads the sliced file, checks its SHA-256 against the signed release,
    uploads it to the AD5M and starts it. It only ever prints jobs you queued yourself.
"""
from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import json
import os
import shutil
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

HEARTBEAT_SECONDS = max(5.0, float(os.getenv("UNG_CAD_BRIDGE_HEARTBEAT_SECONDS", "10")))
CLOUD = os.getenv("UNG_CAD_CLOUD", "https://ung-cad-3d-production.up.railway.app").rstrip("/")
PRINTER_ID = os.getenv("UNG_CAD_PRINTER_ID", "a51a5435")
BRIDGE_PATH = Path(__file__).with_name("ung-cad-ad5m-bridge.py")
JOB_POLL_SECONDS = max(2.0, float(os.getenv("UNG_CAD_JOB_POLL_SECONDS", "3")))
AGENT_VERSION = "2026-10-06-print-queue"
# one printer conversation at a time (status probe vs. print upload)
PRINTER_LOCK = threading.Lock()
LAST_PAYLOAD = {}


def load_bridge(path: Path = BRIDGE_PATH):
    spec = importlib.util.spec_from_file_location("ung_cad_ad5m_bridge_runtime", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load bridge at {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sanitize_error(exc):
    if not exc:
        return None
    return " ".join(str(exc).split())[:240]


def classify_bridge_state(bridge, last_error):
    state = getattr(bridge, "STATE", {}) or {}
    printer = state.get("printer")
    check_code = state.get("check_code") or getattr(bridge, "CHECK_CODE", "")
    if printer and check_code and not last_error:
        return "READY", None
    if not check_code:
        return "PAIRING_ERROR", "Printer Access / Check Code is not configured"
    error = sanitize_error(last_error)
    low = (error or "").lower()
    if "access code" in low or "check code" in low or "rejected connection" in low:
        return "PAIRING_ERROR", error
    if any(term in low for term in ("no flashforge printer", "not discoverable", "discovered printer", "unreachable", "timed out", "timeout")):
        return "PRINTER_UNREACHABLE", error
    return "BRIDGE_ONLINE_PRINTER_OFFLINE", error


def post_heartbeat(payload):
    req = urllib.request.Request(
        CLOUD + "/api/bridge/heartbeat",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        response.read()


def probe_once(bridge, last_contact=None):
    code = (getattr(bridge, "STATE", {}) or {}).get("check_code") or getattr(bridge, "CHECK_CODE", "")
    error = None
    if code:
        try:
            asyncio.run(bridge.connect(code))
            last_contact = time.time()
        except Exception as exc:  # status reporting must never stop the local bridge
            error = exc
    state, message = classify_bridge_state(bridge, error)
    return {
        "printer_id": PRINTER_ID,
        "state": state,
        "bridge_version": getattr(bridge, "BRIDGE_VERSION", None),
        "last_printer_contact": last_contact,
        "error": message,
    }, last_contact


def heartbeat_loop(bridge, stop_event=None):
    stop_event = stop_event or threading.Event()
    last_contact = None
    while not stop_event.is_set():
        if PRINTER_LOCK.acquire(blocking=False):
            try:
                payload, last_contact = probe_once(bridge, last_contact)
                LAST_PAYLOAD.clear()
                LAST_PAYLOAD.update(payload)
            finally:
                PRINTER_LOCK.release()
        else:
            # a print upload is using the printer right now; keep the page showing "online"
            payload = dict(LAST_PAYLOAD) or {"printer_id": PRINTER_ID, "state": "READY",
                                             "bridge_version": getattr(bridge, "BRIDGE_VERSION", None),
                                             "last_printer_contact": last_contact, "error": None}
        try:
            post_heartbeat(payload)
        except Exception as exc:
            print("AD5M status heartbeat:", sanitize_error(exc))
        stop_event.wait(HEARTBEAT_SECONDS)


def cloud_json(path, method="GET", body=None, timeout=30):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(CLOUD + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read() or b"{}")


def run_job(bridge, job):
    """Download, verify and print one queued job. Returns the bridge's result dict."""
    with urllib.request.urlopen(CLOUD + job["download"], timeout=120) as response:
        raw = response.read()
    actual = hashlib.sha256(raw).hexdigest()
    if not job.get("sha256") or actual != job["sha256"]:
        raise RuntimeError("Downloaded file does not match the approved machine file (SHA-256 mismatch)")
    name = Path(job["machine_file"]).name
    tmpdir = tempfile.mkdtemp(prefix="ungcad_job_")
    path = Path(tmpdir) / name
    path.write_bytes(raw)
    try:
        with PRINTER_LOCK:
            state = getattr(bridge, "STATE", {}) or {}
            if not state.get("check_code"):
                code = getattr(bridge, "CHECK_CODE", "")
                if not code:
                    raise RuntimeError("Printer Access Code is not set on this computer — rerun the installer")
                asyncio.run(bridge.connect(code))
            return asyncio.run(bridge.print_file(str(path), True, start=True))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def job_loop(bridge, stop_event=None):
    stop_event = stop_event or threading.Event()
    query = "/api/bridge/jobs/next?printer_id=" + urllib.parse.quote(PRINTER_ID)
    while not stop_event.is_set():
        job = None
        try:
            job = cloud_json(query).get("job")
        except Exception as exc:
            print("AD5M job poll:", sanitize_error(exc))
        if job:
            print("AD5M print job", job.get("id"), job.get("machine_file"))
            try:
                result = run_job(bridge, job)
                body = {"ok": True, "result": result if isinstance(result, dict) else {"result": str(result)}}
            except Exception as exc:
                body = {"ok": False, "error": sanitize_error(exc)}
            print("AD5M print job result:", body)
            try:
                cloud_json("/api/bridge/jobs/" + urllib.parse.quote(job["id"]) + "/complete", "POST", body)
            except Exception as exc:
                print("AD5M job report:", sanitize_error(exc))
            continue
        stop_event.wait(JOB_POLL_SECONDS)


def run():
    bridge = load_bridge()
    thread = threading.Thread(target=heartbeat_loop, args=(bridge,), name="ad5m-status-heartbeat", daemon=True)
    thread.start()
    jobs = threading.Thread(target=job_loop, args=(bridge,), name="ad5m-print-jobs", daemon=True)
    jobs.start()
    server = bridge.make_server()
    print(f"UNG-CAD AD5M bridge + status agent ({AGENT_VERSION}) on http://{bridge.HOST}:{bridge.PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
