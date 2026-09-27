"""Structural reinforcement rib validation and geometry descriptors."""
from dataclasses import dataclass
from math import hypot
from typing import Iterable

class RibValidationError(ValueError): pass

@dataclass(frozen=True)
class RibPoint:
 x: float
 y: float

@dataclass(frozen=True)
class StructuralRib:
 rib_id: str
 start_point: RibPoint
 end_point: RibPoint
 thickness_mm: float=3.0
 height_mm: float=6.0
 profile_type: str="rectangular"

 @property
 def length_mm(self): return hypot(self.end_point.x-self.start_point.x,self.end_point.y-self.start_point.y)

 def validate(self,panel_width:float|None=None,panel_height:float|None=None):
  if self.length_mm<=0: raise RibValidationError("rib start and end points must differ")
  if self.thickness_mm<=0 or self.height_mm<=0: raise RibValidationError("rib thickness and height must be positive")
  if self.profile_type not in {"rectangular","tapered_draft"}: raise RibValidationError("unsupported rib profile")
  if panel_width is not None and panel_height is not None:
   for p in (self.start_point,self.end_point):
    if not (0<=p.x<=panel_width and 0<=p.y<=panel_height): raise RibValidationError("rib endpoint lies outside panel")
  return True

def parse_structural_ribs(items:Iterable[dict],panel_width=None,panel_height=None):
 out=[]
 for x in items:
  r=StructuralRib(str(x["rib_id"]),RibPoint(float(x["start_point"]["x"]),float(x["start_point"]["y"])),RibPoint(float(x["end_point"]["x"]),float(x["end_point"]["y"])),float(x.get("thickness_mm",3)),float(x.get("height_mm",6)),x.get("profile_type","rectangular"))
  r.validate(panel_width,panel_height);out.append(r)
 return out
