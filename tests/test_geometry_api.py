import pytest
pytest.importorskip("fastapi")
from fastapi.testclient import TestClient
from cad_core.geometry_api import app,_sessions
c=TestClient(app)
def payload(x=50):
 return {"panel_id":"p","width_mm":100,"height_mm":80,"material_key":"aluminum_6061","thickness_mm":3.2,"cutouts":[{"component_id":"c","type":"circular","position":{"x_mm":x,"y_mm":40},"rotation":0,"clearance_mm":0,"depth_mm":-1,"tolerance_profile":"cnc_mill_aluminum","dimensions":{"diameter_mm":10}}]}
def test_process_real_pipeline():
 r=c.post("/api/v1/process-assembly",json=payload());assert r.status_code==200;d=r.json();assert d["features_processed_count"]==1;assert d["bill_of_materials"]["net_weight_kg"]>0;assert d["session_token"] in _sessions
def test_layout_failure_is_422_not_500():
 r=c.post("/api/v1/process-assembly",json=payload(2));assert r.status_code==422
def test_unknown_session_does_not_create_mock_file():
 r=c.get("/api/v1/download/dxf/00000000-0000-0000-0000-000000000000");assert r.status_code==404
