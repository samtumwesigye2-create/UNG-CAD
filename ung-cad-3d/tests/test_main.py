import hashlib
import importlib.util
import io
import itertools
import shutil
import sqlite3
import zipfile

import pytest
import trimesh
from fastapi.testclient import TestClient

from conftest import APP_DIR, box, stl_bytes

_counter = itertools.count()
ENV_VARS = ["UNG_CAD_3D_DB", "UNG_CAD_GENERATED_DIR", "UNG_CAD_DASHBOARD_TOKEN", "UNG_CAD_ADMIN_TOKEN",
            "UNG_CAD_MAX_UPLOAD_MB", "UNG_CAD_MAX_ZIP_UNCOMPRESSED_MB", "UNG_CAD_MAX_ZIP_MEMBERS",
            "UNG_CAD_PUBLIC_ORIGIN"]


def build_app(tmp_path, monkeypatch, legacy_keys=None, **env):
    """Copy the app into a temp dir (so BASE_DIR, the default DB path and /static are realistic) and import it."""
    app = tmp_path / "app"
    app.mkdir()
    for name in ("main.py", "slicer.py", "slicer_cnc.py", "ung-cad-ad5m-bridge.py"):
        shutil.copy(APP_DIR / name, app / name)
    shutil.copytree(APP_DIR / "public", app / "public")
    for page in ("studio.html", "viewer.html", "manufacturing.html", "drafting.html"):
        (app / page).write_text(f"<html>{page}</html>")
    (app / "drafting.js").write_text("console.log('drafting');")
    (app / "viewer.js").write_text("console.log('viewer');")
    (app / ".env").write_text("SECRET=1")
    (app / "start-ad5m-bridge.bat").write_text("@echo off")
    (app / "start-ad5m-bridge.command").write_text("#!/bin/bash")
    if legacy_keys is not None:
        c = sqlite3.connect(app / "ung_cad_3d.db")
        c.execute("CREATE TABLE api_keys (id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT NOT NULL UNIQUE, "
                  "owner_system TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL)")
        for k in legacy_keys:
            c.execute("INSERT INTO api_keys (key,owner_system,active,created_at) VALUES (?,?,1,'2026-01-01')", (k, "legacy"))
        c.commit()
        c.close()
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    spec = importlib.util.spec_from_file_location(f"ungcad_main_{next(_counter)}", app / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def make_client(tmp_path, monkeypatch):
    clients = []

    def _make(**kwargs):
        module = build_app(tmp_path, monkeypatch, **kwargs)
        client = TestClient(module.app)
        client.__enter__()
        clients.append(client)
        return module, client

    yield _make
    for c in clients:
        c.__exit__(None, None, None)


def cube_upload(name="cube.stl", size=10):
    return {"file": (name, stl_bytes(box(size, size, size)), "application/octet-stream")}


# ---------- static files ----------

def test_static_never_serves_db_or_source(make_client):
    module, client = make_client(legacy_keys=["old-key"])
    assert module.DB_PATH == module.BASE_DIR / "data" / "ung_cad_3d.db"
    assert module.DB_PATH.exists()
    for path in ("/static/ung_cad_3d.db", "/static/data/ung_cad_3d.db", "/static/main.py", "/static/slicer.py",
                 "/static/.env", "/static/%2e%2e/app/main.py", "/static/../main.py", "/static/generated/x.gcode",
                 "/static/ung-cad-ad5m-bridge.py"):
        r = client.get(path)
        assert r.status_code == 404, path
        assert b"SQLite" not in r.content
    assert client.get("/static/drafting.js").status_code == 200
    assert client.get("/static/viewer.js").status_code == 200
    assert client.get("/static/ung-auth.js").status_code == 200        # served from public/
    assert client.get("/static/preview_viewer.js").status_code == 200
    assert client.get("/static/studio.html").status_code == 200


# ---------- API keys ----------

def test_api_keys_hashed_shown_once_and_revocable(make_client):
    module, client = make_client(UNG_CAD_ADMIN_TOKEN="admintok")
    assert client.post("/api/admin/api-keys", json={"owner_system": "x", "admin_token": "nope"}).status_code == 403
    r = client.post("/api/admin/api-keys", json={"owner_system": "erp", "admin_token": "admintok"})
    assert r.status_code == 200
    raw = r.json()["api_key"]
    c = sqlite3.connect(module.DB_PATH)
    rows = c.execute("SELECT * FROM api_keys").fetchall()
    c.close()
    assert len(rows) == 1
    assert raw not in repr(rows)
    assert hashlib.sha256(raw.encode()).hexdigest() in repr(rows)
    assert raw.encode() not in module.DB_PATH.read_bytes()
    listing = client.get("/api/admin/api-keys", headers={"X-UNG-Admin-Token": "admintok"}).json()
    assert raw not in repr(listing) and listing[0]["owner_system"] == "erp"
    assert client.get("/api/v1/machines", headers={"X-UNG-API-Key": raw}).status_code == 200
    assert client.get("/api/v1/machines", headers={"X-UNG-API-Key": raw + "x"}).status_code == 401
    assert client.post("/api/admin/api-keys/revoke", json={"admin_token": "bad", "key_id": 1}).status_code == 403
    assert client.post("/api/admin/api-keys/revoke", json={"admin_token": "admintok", "key_id": 1}).status_code == 200
    assert client.get("/api/v1/machines", headers={"X-UNG-API-Key": raw}).status_code == 401


def test_legacy_plaintext_keys_migrated(make_client):
    module, client = make_client(legacy_keys=["legacy-raw-key-123"])
    assert client.get("/api/v1/machines", headers={"X-UNG-API-Key": "legacy-raw-key-123"}).status_code == 200
    assert b"legacy-raw-key-123" not in module.DB_PATH.read_bytes()


def test_admin_disabled_without_env(make_client):
    _, client = make_client()
    assert client.post("/api/admin/api-keys", json={"owner_system": "x", "admin_token": ""}).status_code == 403


# ---------- dashboard auth ----------

def test_dashboard_open_without_token(make_client):
    _, client = make_client()
    assert client.get("/api/jobs").status_code == 200
    assert client.get("/api/auth/status").json() == {"auth_required": False, "authorized": True}


def test_dashboard_token_enforced(make_client):
    _, client = make_client(UNG_CAD_DASHBOARD_TOKEN="dash-secret")
    for method, path in (("get", "/api/jobs"), ("get", "/api/machines"), ("get", "/api/scenes"),
                         ("get", "/api/manufacturing/health"), ("post", "/api/manufacturing/cnc-slice"),
                         ("delete", "/api/machines/1"), ("get", "/api/manufacturing/download/x.gcode")):
        r = getattr(client, method)(path)
        assert r.status_code == 401, path
    assert client.get("/api/jobs", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.get("/api/jobs", headers={"Authorization": "Bearer dash-secret"}).status_code == 200
    # public routes stay public
    for path in ("/health", "/studio.html", "/drafting.html", "/ung-cad-ad5m-bridge.py", "/start-ad5m-bridge.bat",
                 "/static/drafting.js"):
        assert client.get(path).status_code == 200, path
    # cookie login
    assert client.post("/api/login", json={"token": "nope"}).status_code == 401
    r = client.post("/api/login", json={"token": "dash-secret"})
    assert r.status_code == 200
    assert "dash-secret" not in r.headers.get("set-cookie", "")
    assert client.get("/api/jobs").status_code == 200
    client.post("/api/logout")
    client.cookies.clear()
    assert client.get("/api/jobs").status_code == 401


def test_download_with_api_key_when_dashboard_locked(make_client):
    _, client = make_client(UNG_CAD_DASHBOARD_TOKEN="dash", UNG_CAD_ADMIN_TOKEN="adm")
    key = client.post("/api/admin/api-keys", json={"owner_system": "erp", "admin_token": "adm"}).json()["api_key"]
    r = client.post("/api/v1/slice/3d", files=cube_upload(), headers={"X-UNG-API-Key": key})
    assert r.status_code == 200, r.text
    url = r.json()["download"]
    assert client.get(url).status_code == 401
    assert client.get(url, headers={"X-UNG-API-Key": key}).status_code == 200


# ---------- uploads ----------

def test_upload_size_limit(make_client):
    _, client = make_client(UNG_CAD_MAX_UPLOAD_MB="1")
    big = {"file": ("big.stl", b"x" * (3 * 1024 * 1024), "application/octet-stream")}
    r = client.post("/api/manufacturing/inspect", files=big)
    assert r.status_code == 413


def test_upload_size_limit_without_content_length(make_client):
    _, client = make_client(UNG_CAD_MAX_UPLOAD_MB="1")
    boundary = "ungboundary"
    head = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"big.stl\"\r\n"
            "Content-Type: application/octet-stream\r\n\r\n").encode()
    tail = f"\r\n--{boundary}--\r\n".encode()

    def chunks():
        yield head
        for _ in range(40):
            yield b"x" * (128 * 1024)
        yield tail

    r = client.post("/api/manufacturing/inspect", content=chunks(),
                    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    assert r.status_code == 413


def _zip(entries):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in entries:
            z.writestr(name, data)
    return buf.getvalue()


def test_zip_guards(make_client):
    _, client = make_client(UNG_CAD_MAX_ZIP_UNCOMPRESSED_MB="1", UNG_CAD_MAX_ZIP_MEMBERS="5")
    ok = _zip([("parts/a.stl", stl_bytes(box(5, 5, 5)))])
    assert client.post("/api/manufacturing/inspect", files={"file": ("p.zip", ok)}).json()["parts"] == ["a.stl"]
    for bad in (_zip([("../evil.stl", b"x")]), _zip([("/abs/evil.stl", b"x")]), _zip([("a/../../b.stl", b"x")]),
                _zip([("C:/win.stl", b"x")])):
        r = client.post("/api/manufacturing/inspect", files={"file": ("p.zip", bad)})
        assert r.status_code == 400 and "unsafe" in r.json()["detail"]
    many = _zip([(f"p{i}.stl", b"x") for i in range(6)])
    assert "too many" in client.post("/api/manufacturing/inspect", files={"file": ("p.zip", many)}).json()["detail"]
    bomb = _zip([("bomb.stl", b"\0" * (3 * 1024 * 1024))])
    assert len(bomb) < 100 * 1024
    r = client.post("/api/manufacturing/inspect", files={"file": ("p.zip", bomb)})
    assert r.status_code == 400 and "uncompressed" in r.json()["detail"]
    r = client.post("/api/manufacturing/slice", files={"file": ("p.zip", bomb)}, data={"selected": "bomb.stl"})
    assert r.status_code == 400


def test_slice_unique_names_material_and_download(make_client):
    module, client = make_client()
    names = set()
    for _ in range(2):
        r = client.post("/api/manufacturing/slice", files=cube_upload(), data={"selected": "cube.stl"})
        assert r.status_code == 200, r.text
        j = r.json()
        names.add(j["machine_file"])
        assert j["machine_file"].startswith("cube_") and j["machine_file"].endswith("_AD5M.gcode")
        assert client.get(j["download"]).status_code == 200
        assert j["stats"]["material"] == "PLA" and "warnings" in j
    assert len(names) == 2
    r = client.post("/api/manufacturing/slice", files=cube_upload(), data={"selected": "cube.stl", "material": "PETG"})
    assert r.json()["stats"]["material"] == "PETG"
    assert client.post("/api/manufacturing/slice", files=cube_upload(),
                       data={"selected": "cube.stl", "material": "ABS"}).status_code == 400
    assert client.post("/api/manufacturing/slice", files=cube_upload(),
                       data={"selected": "cube.stl", "layer_height": "0.5"}).status_code == 400
    assert client.get("/api/manufacturing/download/..%2Fmain.py").status_code == 404
    assert client.get("/api/manufacturing/download/nothing.gcode").status_code == 404
    jobs = client.get("/api/jobs").json()
    assert len(jobs) == 3


def test_slice_validation_errors_and_warnings_returned(make_client):
    _, client = make_client()
    tall = {"file": ("tall.stl", stl_bytes(box(10, 10, 230)))}
    r = client.post("/api/manufacturing/slice", files=tall, data={"selected": "tall.stl"})
    assert r.status_code == 422
    body = r.json()
    assert isinstance(body["detail"], str)
    assert body["errors"][0]["code"] == "too_tall"
    stem = box(6, 6, 10)
    plate = box(20, 20, 2, center=(0, 0, 11))
    t = {"file": ("t.stl", stl_bytes(trimesh.util.concatenate([stem, plate])))}
    r = client.post("/api/manufacturing/slice", files=t, data={"selected": "t.stl"})
    assert r.status_code == 200
    assert any(w["code"] == "overhang" for w in r.json()["warnings"])


def test_preview_endpoint_json_shape(make_client):
    _, client = make_client()
    r = client.post("/api/manufacturing/preview", files=cube_upload(), data={"selected": "cube.stl", "layer_height": "0.2"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["layer_count"] == 50 and len(j["layers"]) == 50
    first = j["layers"][0]
    assert first["z"] == pytest.approx(0.2)
    assert {p["type"] for l in j["layers"] for p in l["paths"]} == {"perimeter", "infill", "solid", "travel"}
    assert all(len(pt) == 2 for p in first["paths"] for pt in p["points"])
    assert j["stats"]["toolpath_size_mm"] == pytest.approx([10, 10, 10], abs=0.05)
    assert "warnings" in j and "errors" in j
    assert client.get("/api/jobs").json() == []          # preview does not create jobs/files


def test_cnc_endpoint_validation_and_unique_names(make_client):
    _, client = make_client()
    shapes = [{"t": "rect", "a": {"x": 0, "y": 0}, "b": {"x": 10, "y": 10}}]
    r1 = client.post("/api/manufacturing/cnc-slice", json={"shapes": shapes, "settings": {"mode": "laser"}})
    r2 = client.post("/api/manufacturing/cnc-slice", json={"shapes": shapes, "settings": {"mode": "laser"}})
    assert r1.status_code == 200 and r1.json()["machine_file"] != r2.json()["machine_file"]
    bad = client.post("/api/manufacturing/cnc-slice", json={"shapes": shapes, "settings": {"mode": "cnc", "spindle_speed": 100}})
    assert bad.status_code == 400 and "spindle" in bad.json()["detail"]


def test_bridge_download_prefills_origin(make_client):
    _, client = make_client(UNG_CAD_PUBLIC_ORIGIN="https://ung-cad.example.app")
    text = client.get("/ung-cad-ad5m-bridge.py").text
    assert 'DEFAULT_RAILWAY_ORIGIN = "https://ung-cad.example.app"' in text
    assert "YOUR-APP.up.railway.app" not in text


def test_scenes_crud(make_client):
    _, client = make_client()
    sid = client.post("/api/scenes", json={"name": "a", "data": {"k": 1}}).json()["id"]
    assert client.get("/api/scenes").json()[0]["name"] == "a"
    assert client.put(f"/api/scenes/{sid}", json={"name": "b", "data": {"k": 2}}).json()["status"] == "updated"
    assert client.get(f"/api/scenes/{sid}").json()["data"] == {"k": 2}
    assert client.delete(f"/api/scenes/{sid}").json()["status"] == "deleted"
    assert client.get(f"/api/scenes/{sid}").status_code == 404
