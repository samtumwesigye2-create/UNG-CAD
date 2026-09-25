from pathlib import Path
J=(Path(__file__).resolve().parents[1]/"ung-cad-3d"/"viewer.js").read_text()
def test_geometry_derived_electrical_inputs():
    assert "function deriveElectricalGeometry(o)" in J
    assert "function syncElectricalGeometry(o)" in J
    assert "syncElectricalGeometry(one)" in J
    assert "wire-length" in J and "wire-area" in J
