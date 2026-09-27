import sys,types
from cad_core.dxf_dimensioner import UngCadAutoDimensioner
class Obj:
 def __init__(self):self.rendered=False
 def render(self):self.rendered=True
class Text:
 def set_placement(self,p):self.p=p;return self
class MSP:
 def __init__(self):self.dims=[];self.texts=[]
 def add_linear_dim(self,**kw):o=Obj();o.kw=kw;self.dims.append(o);return o
 def add_text(self,*a,**kw):o=Text();o.args=a;self.texts.append(o);return o
class Coll:
 def __init__(self):self.names=set()
 def __contains__(self,n):return n in self.names
 def new(self,n,**kw):self.names.add(n)
class Doc:
 def __init__(self):self.layers=Coll();self.styles=Coll();self.m=MSP();self.saved=False
 def modelspace(self):return self.m
 def save(self):self.saved=True
def test_dimensions_and_diameter(monkeypatch):
 d=Doc();monkeypatch.setitem(sys.modules,"ezdxf",types.SimpleNamespace(readfile=lambda p:d))
 UngCadAutoDimensioner.append_datum_dimensions("x.dxf",[{"type":"circular","position":{"x_mm":20,"y_mm":30},"geometry_payload":{"diameter_mm":10},"clearance_mm":.2}])
 assert len(d.m.dims)==2 and all(x.rendered for x in d.m.dims);assert d.m.dims[0].kw["angle"]==0 and d.m.dims[1].kw["angle"]==90;assert d.m.texts[0].args[0]=="%%c10.4";assert d.saved
