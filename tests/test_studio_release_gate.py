from pathlib import Path
R=Path(__file__).resolve().parents[1]; H=(R/"ung-cad-3d"/"viewer.html").read_text(); J=(R/"ung-cad-3d"/"viewer.js").read_text()
def test_release_gate_visible():
    assert "release-gate-state" in H and "release-gate-checks" in H
def test_manufacturing_enforces_gate():
    assert "function evaluateStudioReleaseGate()" in J
    assert "Manufacturing BLOCKED — Production Release Gate failed" in J
    assert "Manufacturing STALE — regenerate/validate toolpath before release" in J
def test_geometry_change_stales_gate():
    assert "releaseGateState='STALE'" in J
