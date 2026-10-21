import csv
import io
import json
import zipfile

from test_main import make_client  # noqa: F401  (pytest fixture)


def _kit(client):
    r = client.get("/api/manufacturing/calibration/coupon-kit")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    return zipfile.ZipFile(io.BytesIO(r.content))


def test_kit_zip_contains_stl_manifest_sheet_and_readme(make_client):
    _, client = make_client()
    z = _kit(client)
    assert sorted(z.namelist()) == ["README.txt", "coupon.stl", "manifest.json", "measurements.csv"]
    assert z.read("coupon.stl").startswith(b"solid")
    manifest = json.loads(z.read("manifest.json"))
    assert manifest["validation"]["watertight"]
    assert manifest["build_volume"]["fits"]
    rows = list(csv.DictReader(io.StringIO(z.read("measurements.csv").decode())))
    assert {r["piece_id"] for r in rows} == {p["id"] for p in manifest["pieces"]}


def test_custom_kit_rejects_bad_dimensions(make_client):
    _, client = make_client()
    r = client.post("/api/manufacturing/calibration/coupon-kit", json={"outer_x_mm": -1})
    assert r.status_code == 422


def test_filled_sheet_round_trip_creates_usable_profile(make_client):
    _, client = make_client()
    rows = list(csv.DictReader(io.StringIO(_kit(client).read("measurements.csv").decode())))
    for r in rows:
        if r["group"] == "hole_samples":
            r["measured_mm"] = f"{float(r['nominal_mm']) - 0.2:.2f}"
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)

    r = client.post("/api/manufacturing/calibration/feedback-csv",
                    files={"file": ("measurements.csv", out.getvalue().encode(), "text/csv")},
                    data={"profile_name": "ad5m-kit"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["saved"] and body["measurements_used"] == {"hole_samples": 4}
    assert abs(body["profile"]["hole_diameter_error_mm"] + 0.2) < 1e-9

    # The saved profile drives compensated CAD generation (PR #143 path).
    r = client.post("/api/cad/parametric/primitive", json={
        "entity_id": "h", "primitive_type": "hole", "params": {"radius": 2.5, "depth": 5},
        "compensation_profile_name": "ad5m-kit"})
    assert r.status_code == 200
    assert abs(r.json()["compensation"]["cad_params"]["diameter"] - 5.2) < 1e-9


def test_sheet_upload_rejects_empty_or_malformed_sheets(make_client):
    _, client = make_client()
    blank = _kit(client).read("measurements.csv")
    r = client.post("/api/manufacturing/calibration/feedback-csv",
                    files={"file": ("m.csv", blank, "text/csv")}, data={"profile_name": "x"})
    assert r.status_code == 422 and "no measured values" in r.text
    r = client.post("/api/manufacturing/calibration/feedback-csv",
                    files={"file": ("m.csv", b"a,b\n1,2\n", "text/csv")}, data={"profile_name": "x"})
    assert r.status_code == 422 and "missing columns" in r.text
