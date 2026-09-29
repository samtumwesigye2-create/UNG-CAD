import io, zipfile
from fastapi.testclient import TestClient
from main import app

client=TestClient(app)


def test_calibration_coupon_download_contains_printable_parts_and_template():
    r=client.get("/api/manufacturing/calibration/coupon")
    assert r.status_code==200
    assert r.headers["content-type"].startswith("application/zip")
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        names=set(z.namelist())
        assert "xy_block.stl" in names
        assert "hole_ring_5.stl" in names
        assert "plug_6.stl" in names
        assert "manifest.json" in names
        assert "measurements.csv" in names


def test_measured_feedback_persists_calibrated_profile():
    payload={
      "printer_id":"TEST_AD5M_CAL_001",
      "material":"PLA",
      "process_key":"0.4mm-nozzle_0.20mm-layer",
      "profile_name":"pytest coupon",
      "measurements":[
        {"feature":"hole","nominal_mm":5.0,"measured_mm":4.8},
        {"feature":"hole","nominal_mm":8.0,"measured_mm":7.8},
        {"feature":"outer","nominal_mm":20.0,"measured_mm":20.2},
        {"feature":"z","nominal_mm":10.0,"measured_mm":9.9},
      ],
    }
    r=client.post("/api/manufacturing/calibration/feedback",json=payload)
    assert r.status_code==200
    body=r.json()
    assert body["profile"]["calibrated"] is True
    assert body["profile"]["hole_diameter_error_mm"] < 0

    r=client.get("/api/manufacturing/calibration/profile/TEST_AD5M_CAL_001",
                 params={"material":"PLA","process_key":"0.4mm-nozzle_0.20mm-layer"})
    assert r.status_code==200
    got=r.json()
    assert got["found"] is True
    assert got["profile"]["calibrated"] is True


def test_unknown_printer_returns_neutral_profile():
    r=client.get("/api/manufacturing/calibration/profile/NO_SUCH_PRINTER")
    assert r.status_code==200
    body=r.json()
    assert body["found"] is False
    assert body["profile"]["calibrated"] is False
    assert body["profile"]["hole_diameter_error_mm"] == 0.0
