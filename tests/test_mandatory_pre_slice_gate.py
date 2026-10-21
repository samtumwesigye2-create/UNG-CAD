from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "ung-cad-3d" / "main.py"


def _slice_block():
    text=MAIN.read_text(encoding="utf-8")
    return text.split('@app.post("/api/manufacturing/slice")',1)[1].split("def _save_gcode",1)[0]


def test_standalone_slice_does_not_require_release_manifest():
    block=_slice_block()
    assert "production_manifest:str|None=Form(None)" in block
    assert '"gate_scope":"standalone"' in block
    assert "Standalone manufacturing path" in block
    assert "DRACO production slicing requires a production_manifest." in block


def test_supplied_production_manifest_is_still_enforced():
    block=_slice_block()
    assert "evaluate_production_manifest(manifest)" in block
    assert "Production readiness gate is not PASS for the supplied manifest." in block
    slice_entry="_run_3d_slice(" if "_run_3d_slice(" in block else "slice_stl("
    assert block.index("evaluate_production_manifest(manifest)") < block.index(slice_entry)


def test_draco_package_failure_is_still_hard_locked():
    block=_slice_block()
    assert "DRACO package release gate is not PASS" in block
    assert "single DRACO production part has no package release manifest" in block


def test_slice_signs_exact_generated_machine_file():
    block=_slice_block()
    assert block.count("sign_machine_file(target,production_release)") >= 2
    assert '"release_signature":release_signature' in block
