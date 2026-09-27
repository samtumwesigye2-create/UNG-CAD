"""Recursive UNG-CAD panel assembly contract validation."""
from dataclasses import dataclass,field
from math import cos,sin,radians
from typing import Any

class AssemblyValidationError(ValueError): pass

@dataclass(frozen=True)
class Vec3:
 x:float;y:float;z:float

@dataclass
class PanelNode:
 panel_id:str;width_mm:float;height_mm:float;position:Vec3;rotation:float
 cutouts:list[dict]=field(default_factory=list);child_panels:list["PanelNode"]=field(default_factory=list)

 def validate(self,seen=None):
  seen=set() if seen is None else seen
  if self.panel_id in seen: raise AssemblyValidationError(f"duplicate/cyclic panel_id: {self.panel_id}")
  seen.add(self.panel_id)
  if self.width_mm<=0 or self.height_mm<=0: raise AssemblyValidationError("panel dimensions must be positive")
  for c in self.child_panels:
   c.validate(seen)
   # Child position is parent-local. Rotation-aware corner containment prevents
   # a rotated child from extending outside its parent's plate.
   a=radians(c.rotation);ca,sa=cos(a),sin(a);hw,hh=c.width_mm/2,c.height_mm/2
   corners=[(sx*hw,sy*hh) for sx in (-1,1) for sy in (-1,1)]
   for x,y in corners:
    px=c.position.x+x*ca-y*sa;py=c.position.y+x*sa+y*ca
    if not (0<=px<=self.width_mm and 0<=py<=self.height_mm):
     raise AssemblyValidationError(f"child panel {c.panel_id} exceeds parent {self.panel_id} XY boundary")
  return True

def panel_from_dict(d:dict[str,Any])->PanelNode:
 return PanelNode(str(d["panel_id"]),float(d["width_mm"]),float(d["height_mm"]),Vec3(**{k:float(d["position"][k]) for k in ("x","y","z")}),float(d["rotation"]),list(d.get("cutouts",[])),[panel_from_dict(x) for x in d.get("child_panels",[])])

def validate_assembly(data:dict[str,Any])->PanelNode:
 if not data.get("assembly_id"): raise AssemblyValidationError("assembly_id required")
 root=panel_from_dict(data["root_panel"]);root.validate();return root
