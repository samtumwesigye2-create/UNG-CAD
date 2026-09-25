from pathlib import Path
J=(Path(__file__).resolve().parents[1]/"ung-cad-3d"/"viewer.js").read_text()
def test_release_gate_rows_show_evidence_sources():
    for source in ("UNG-GEOMETRY mesh integrity","Tolerance policy","Assembly interference solver","Machine profile/envelope validator","Slicer/CAM validation"):
        assert source in J
    assert "release-evidence-row" in J
def test_unavailable_solvers_are_explicitly_unevaluated():
    assert "{name:'Assembly',source:'Assembly interference solver',evaluated:false,passed:null}" in J
    assert "{name:'Toolpath',source:'Slicer/CAM validation',evaluated:false,passed:null}" in J
    assert "(not evaluated)" in J
def test_stale_prevents_false_release():
    assert "states.includes('STALE')?'STALE'" in J
