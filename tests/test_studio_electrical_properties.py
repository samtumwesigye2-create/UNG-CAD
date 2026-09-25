from pathlib import Path
R=Path(__file__).resolve().parents[1]; H=(R/"ung-cad-3d"/"viewer.html").read_text(); J=(R/"ung-cad-3d"/"viewer.js").read_text()
def test_electrical_properties_panel():
    for x in ("wire-material","wire-length","wire-area","wire-current","wire-temp","wire-bind","wire-result"): assert x in H
def test_selected_part_binding_logic():
    for x in ("electricalBindings","bindElectrical","calculateBoundElectrical","Electrical Binding","I²R"): assert x in J
