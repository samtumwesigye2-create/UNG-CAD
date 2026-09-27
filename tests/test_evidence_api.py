import importlib.util
from pathlib import Path
import pytest
pytest.importorskip("fastapi")
from fastapi import FastAPI
from fastapi.testclient import TestClient

P=Path(__file__).resolve().parents[1]/"ung-cad-3d"/"evidence_api.py"
spec=importlib.util.spec_from_file_location("evidence_api_test",P)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
app=FastAPI(); app.include_router(m.router); c=TestClient(app)

def test_health():
    r=c.get("/api/evidence/health"); assert r.status_code==200
    assert r.json()["acquisition_or_bypass"] is False

def test_search_graph_timeline_report():
    a=[{"source_ref":"sms:1","artifact_type":"message","timestamp":"2026-01-01T00:00:00Z","observed":{"contact":"alice@example.com","thread_id":"t"}},
       {"source_ref":"call:2","artifact_type":"call","timestamp":"2026-01-01T00:00:30Z","observed":{"contact":"alice@example.com"}}]
    assert len(c.post("/api/evidence/search",json={"artifacts":a,"query":"alice@example.com"}).json()["matches"])==2
    assert c.post("/api/evidence/graph",json=a).json()["edges"]
    assert c.post("/api/evidence/timeline",json={"artifacts":a}).json()["correlations"]
    rep=c.post("/api/evidence/report",json={"case_id":"C","evidence":[],"findings":[]}).json()
    assert c.post("/api/evidence/report/verify",json=rep).json()["verified"]

def test_redaction_default():
    r=c.post("/api/evidence/protect",json={"text":"verification code is 299040","actor_id":"u","roles":[]})
    assert "299040" not in r.json()["text"]
