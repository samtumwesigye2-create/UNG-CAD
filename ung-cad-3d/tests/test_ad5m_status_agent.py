import importlib.util
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import APP_DIR


def load_agent():
    spec = importlib.util.spec_from_file_location("ung_ad5m_agent", APP_DIR / "ung-cad-ad5m-agent.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_agent_classifies_ready_pairing_and_unreachable_states():
    agent = load_agent()
    bridge = SimpleNamespace(STATE={"printer": {"serial": "SN123"}, "check_code": "ok"}, CHECK_CODE="ok")
    assert agent.classify_bridge_state(bridge, None) == ("READY", None)

    bridge.STATE = {"printer": None, "check_code": None}
    bridge.CHECK_CODE = ""
    assert agent.classify_bridge_state(bridge, None)[0] == "PAIRING_ERROR"

    bridge.CHECK_CODE = "1234"
    assert agent.classify_bridge_state(bridge, "Access Code mismatch")[0] == "PAIRING_ERROR"
    assert agent.classify_bridge_state(bridge, "No FlashForge printer discovered on this LAN")[0] == "PRINTER_UNREACHABLE"
    assert agent.classify_bridge_state(bridge, "connection reset")[0] == "BRIDGE_ONLINE_PRINTER_OFFLINE"


def test_status_heartbeat_is_fresh_then_stale(monkeypatch):
    import production_readiness_api as status_api

    status_api.BRIDGE_STATUS.clear()
    clock = {"t": 1000.0}
    monkeypatch.setattr(status_api, "now_ts", lambda: clock["t"])

    app = FastAPI()
    app.include_router(status_api.router)
    client = TestClient(app)

    payload = {
        "printer_id": "a51a5435",
        "state": "READY",
        "bridge_version": "2026-09-20-3",
        "last_printer_contact": 998.0,
        "error": None,
    }
    r = client.post("/api/bridge/heartbeat", json=payload)
    assert r.status_code == 200, r.text
    status = client.get("/api/bridge/status/a51a5435").json()
    assert status["state"] == "READY"
    assert status["fresh"] is True
    assert status["age_seconds"] == 0.0
    assert status["source"] == "bridge-self-report"

    clock["t"] += status_api.BRIDGE_HEARTBEAT_TTL_SECONDS + 1
    stale = client.get("/api/bridge/status/a51a5435").json()
    assert stale["fresh"] is False
    assert stale["state"] == "BRIDGE_OFFLINE"
    assert stale["last_reported_state"] == "READY"


def test_status_api_rejects_unknown_state_and_sanitizes_error(monkeypatch):
    import production_readiness_api as status_api

    status_api.BRIDGE_STATUS.clear()
    monkeypatch.setattr(status_api, "now_ts", lambda: 2000.0)
    app = FastAPI()
    app.include_router(status_api.router)
    client = TestClient(app)

    bad = client.post("/api/bridge/heartbeat", json={"printer_id": "p1", "state": "WHATEVER"})
    assert bad.status_code == 422

    long_error = "x" * 2000
    ok = client.post("/api/bridge/heartbeat", json={
        "printer_id": "p1",
        "state": "PAIRING_ERROR",
        "error": long_error,
    })
    assert ok.status_code == 200
    body = client.get("/api/bridge/status/p1").json()
    assert len(body["error"]) <= 240
