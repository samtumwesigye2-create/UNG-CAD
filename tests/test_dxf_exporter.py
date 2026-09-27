import sys,types
from cad_core.dxf_exporter import UngCadDxfExporter
class MSP:
 def __init__(self):self.items=[]
 def __getattr__(self,n):return lambda *a,**k:self.items.append((n,a,k))
class Layers:
 def __init__(self):self.s=set()
 def __contains__(self,n):return n in self.s
 def new(self,name,dxfattribs):self.s.add(name)
class Doc:
 def __init__(self):self.header={};self.layers=Layers();self.m=MSP();self.saved=None
 def modelspace(self):return self.m
 def saveas(self,p):self.saved=p
def test_dxf_layers_rotation_and_units(monkeypatch):
 d=Doc();monkeypatch.setitem(sys.modules,"ezdxf",types.SimpleNamespace(new=lambda v:d))
 c={"type":"rectangular","position":{"x_mm":20,"y_mm":20},"rotation":90,"clearance_mm":.2,"geometry_payload":{"width_mm":10,"height_mm":5,"corner_radius_mm":1},"mounting_holes":[{"offset_x_mm":2,"offset_y_mm":0,"diameter_mm":3}]}
 UngCadDxfExporter.export_to_dxf("x.dxf",[c],100,80)
 assert d.header["$INSUNITS"]==4 and d.saved=="x.dxf"
 assert {"PANEL_BORDER","THROUGH_CUTS","MOUNTING_HOLES","COUNTERSINKS"}<=d.layers.s
 circles=[x for x in d.m.items if x[0]=="add_circle"];assert abs(circles[0][1][0][0]-20)<1e-9 and abs(circles[0][1][0][1]-22)<1e-9
