import sys,types,pytest
from cad_core.assembly_solid_compiler import UngCadAssemblySolidCompiler as C
def test_transform_composes_rotation():
 x,y=C._transform(10,0,5,5,90);assert abs(x-5)<1e-8 and abs(y-15)<1e-8
def test_bad_format_fails_before_cadquery_use(monkeypatch):
 monkeypatch.setitem(sys.modules,"cadquery",types.SimpleNamespace())
 with pytest.raises(ValueError,match="STEP or STL"):C.compile({"panel_id":"p"},"OBJ")
