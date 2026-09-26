from pathlib import Path
def test_studio_release_gate_reports_real_evidence_sources():
    text=(Path(__file__).parents[1]/"ung-cad-3d"/"viewer.js").read_text()
    for token in ("Studio feature/object state","UNG-GEOMETRY mesh integrity","Tolerance policy","Assembly interference solver","Machine profile/envelope validator","Slicer/CAM validation"):
        assert token in text
    assert "evaluated:false,passed:null" in text
