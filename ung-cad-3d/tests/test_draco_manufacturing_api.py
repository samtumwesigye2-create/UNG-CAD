"""End-to-end API regression for the DRACO Manufacturing release gate."""
import io, json, zipfile
from fastapi.testclient import TestClient
from main import app

client=TestClient(app)

PARTS=["P1","P2","P9A","P9B","P3","P4","P5","P6","P7","P8"]

def pack(parts=PARTS, manifest=None, p0=False):
    b=io.BytesIO()
    with zipfile.ZipFile(b,"w") as z:
        for p in parts:
            z.writestr(f"DRACO_K2_{p}_PART.gcode",b"; test only\n")
        if p0:
            z.writestr("DRACO_K2_P0_FIT_COUPON.gcode",b"; p0 test only\n")
        if manifest is not None:
            z.writestr("DRACO_PRODUCTION_RELEASE.json",json.dumps(manifest))
    return b.getvalue()

def approved():
    return {"release_ready":True,"actual_hardware_dimensions_verified":True,
      "fit_coupon_passed":True,"dry_assembly_passed":True,
      "pan_tilt_motion_validated":True,"manifold_validation_passed":True,
      "source_cad_included":True,"baffle_material":"black PLA",
      "circular_12v_jack_present":False,"base_mounted_servos":2}

def upload(data,name="DRACO_K2.zip"):
    return {"file":(name,data,"application/zip")}

def test_inspect_incomplete_draco_is_p0_only():
    r=client.post("/api/manufacturing/inspect",files=upload(pack(parts=["P1","P2"],p0=True)))
    assert r.status_code==200
    state=r.json()["production_release"]
    assert state["ready"] is False and state["p0_only_until_release"] is True
    assert state["blockers"]

def test_production_slice_allowed_with_release_warning():
    data=pack(p0=True)
    r=client.post("/api/manufacturing/slice",files=upload(data),
                  data={"selected":"DRACO_K2_P2_PART.gcode"})
    assert r.status_code==200
    body=r.json()
    assert body["status"]=="machine_file_ready"
    assert body.get("release_warning") is not None

def test_p0_machine_file_allowed_before_release():
    data=pack(p0=True)
    r=client.post("/api/manufacturing/slice",files=upload(data),
                  data={"selected":"DRACO_K2_P0_FIT_COUPON.gcode"})
    assert r.status_code==200
    assert r.json()["status"]=="machine_file_ready"

def test_approved_package_inspects_ready_and_allows_part():
    data=pack(manifest=approved())
    r=client.post("/api/manufacturing/inspect",files=upload(data))
    assert r.status_code==200 and r.json()["production_release"]["ready"] is True
    r=client.post("/api/manufacturing/slice",files=upload(data),
                  data={"selected":"DRACO_K2_P2_PART.gcode"})
    assert r.status_code==200 and r.json()["status"]=="machine_file_ready"
