"""UNG-CAD AD5M status wrapper.

Runs the existing local bridge unchanged, but adds a read-only printer probe and
cloud heartbeat so the production service can distinguish bridge/printer states.
It never starts a print and never sends a machine-control command.
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import threading
import time
import urllib.request
from pathlib import Path

HEARTBEAT_SECONDS = max(5.0, float(os.getenv("UNG_CAD_BRIDGE_HEARTBEAT_SECONDS", "10")))
CLOUD = os.getenv("UNG_CAD_CLOUD", "https://ung-cad-3d-production.up.railway.app").rstrip("/")
PRINTER_ID = os.getenv("UNG_CAD_PRINTER_ID", "a51a5435")
BRIDGE_PATH = Path(__file__).with_name("ung-cad-ad5m-bridge.py")


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
        payload, last_contact = probe_once(bridge, last_contact)
        try:
            post_heartbeat(payload)
        except Exception as exc:
            print("AD5M status heartbeat:", sanitize_error(exc))
        stop_event.wait(HEARTBEAT_SECONDS)


def run():
    bridge = load_bridge()
    thread = threading.Thread(target=heartbeat_loop, args=(bridge,), name="ad5m-status-heartbeat", daemon=True)
    thread.start()
    server = bridge.make_server()
    print(f"UNG-CAD AD5M bridge + status agent on http://{bridge.HOST}:{bridge.PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
