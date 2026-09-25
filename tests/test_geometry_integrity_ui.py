from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/"ung-cad-3d"/"viewer.html").read_text()
JS=(ROOT/"ung-cad-3d"/"viewer.js").read_text()

def test_geometry_integrity_panel_is_present():
    for token in ("Geometry Integrity","integrity-badge","integrity-topology","integrity-envelope","integrity-manufacturing","integrity-units"):
        assert token in HTML

def test_geometry_integrity_engine_is_wired():
    for token in ("inspectPolygons","boundary","nonmanifold","degenerate","watertight","updateIntegrity"):
        assert token in JS

def test_integrity_gate_is_refreshed_with_scene():
    assert "updateTwin(one)" in JS\n    assert "updateIntegrity()" in JS
    assert "integrity-run" in JS
