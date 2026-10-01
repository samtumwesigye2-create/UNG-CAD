from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "ung-cad-3d" / "main.py"


def _slice_block():
    text=MAIN.read_text(encoding="utf-8")
    return text.split('@app.post("/api/manufacturing/slice")',1)[1].split("def _save_gcode",1)[0]


def test_slice_requires_production_manifest_and_pass():
    block=_slice_block()
    assert "production_manifest:str=Form(...)" in block
    assert "evaluate_production_manifest(manifest)" in block
    assert "Production readiness gate is not PASS; slicing is hard-locked." in block
    assert block.index("evaluate_production_manifest(manifest)") < block.index("slice_stl(")


def test_slice_signs_exact_generated_machine_file():
    block=_slice_block()
    assert block.count("sign_machine_file(target,production_release)") >= 2
    assert '"release_signature":release_signature' in block
    assert "release_warning" not in block


def test_legacy_package_failure_is_hard_lock_not_advisory():
    block=_slice_block()
    assert "Package release gate is not PASS; slicing is hard-locked." in block
    assert "Release-gate findings are advisory here" not in block
