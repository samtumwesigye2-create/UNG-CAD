from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
H=(ROOT/"ung-cad-3d"/"viewer.html").read_text()
J=(ROOT/"ung-cad-3d"/"viewer.js").read_text()
def test_electromechanical_ui():
    for x in ("em-connection","em-voltage","em-current","em-pf","em-resistance","em-calc","em-result"): assert x in H
    assert "calculateThreePhase" in J
