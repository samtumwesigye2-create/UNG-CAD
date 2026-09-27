import sys,types,pytest
from cad_core.solid_exporter import UngCadSolidExporter
def test_rejects_bad_format_before_geometry(monkeypatch):
 monkeypatch.setitem(sys.modules,"cadquery",types.SimpleNamespace())
 with pytest.raises(ValueError,match="STEP or STL"):UngCadSolidExporter.generate_3d_solid({"width_mm":1,"height_mm":1,"thickness_mm":1},"OBJ")
def test_rejects_bad_panel_dimensions(monkeypatch):
 monkeypatch.setitem(sys.modules,"cadquery",types.SimpleNamespace())
 with pytest.raises(ValueError,match="positive"):UngCadSolidExporter.generate_3d_solid({"width_mm":0,"height_mm":1,"thickness_mm":1})
