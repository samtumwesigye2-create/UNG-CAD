from pathlib import Path
R=Path(__file__).resolve().parents[1]
H=(R/"ung-cad-3d"/"viewer.html").read_text(); J=(R/"ung-cad-3d"/"viewer.js").read_text()
def test_component_binding_ui():
    for x in ("em-role","em-bind","em-bindings"): assert x in H
    for x in ("emBindings","bindElectromechanicalPart","renderElectromechanicalBindings"): assert x in J
