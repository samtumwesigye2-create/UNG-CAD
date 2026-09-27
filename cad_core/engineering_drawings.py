"""Dependency-free engineering drawing specification generator.

Produces a deterministic drawing manifest for UI/PDF/DXF renderers rather than
pretending to implement a full GD&T drafting standard.
"""
from dataclasses import dataclass,asdict
from typing import Any,Dict,List
@dataclass(frozen=True)
class Dimension:
 kind:str;label:str;value_mm:float;origin:str="panel_datum"
class EngineeringDrawingGenerator:
 def generate(self,panel:Dict[str,Any])->Dict[str,Any]:
  w=float(panel["width_mm"]);h=float(panel["height_mm"]);t=float(panel["thickness_mm"])
  if min(w,h,t)<=0:raise ValueError("panel dimensions must be positive")
  dims=[Dimension("overall_width","W",w),Dimension("overall_height","H",h),Dimension("thickness","T",t)]
  holes=[]
  for c in panel.get("cutouts",[]):
   p=c["position"];g=c.get("geometry_payload") or c.get("dimensions") or {};cid=str(c.get("component_id","unnamed"))
   dims += [Dimension("ordinate_x",f"{cid} X",float(p["x_mm"])),Dimension("ordinate_y",f"{cid} Y",float(p["y_mm"]))]
   if c["type"]=="circular":dims.append(Dimension("diameter",f"{cid} DIA",float(g["diameter_mm"])+2*float(c.get("clearance_mm",0))))
   elif c["type"] in {"rectangular","usb_c","ethernet"}:
    dims += [Dimension("feature_width",f"{cid} W",float(g["width_mm"])+2*float(c.get("clearance_mm",0))),Dimension("feature_height",f"{cid} H",float(g["height_mm"])+2*float(c.get("clearance_mm",0)))]
   for i,m in enumerate(c.get("mounting_holes",[])):holes.append({"parent":cid,"index":i,"diameter_mm":float(m["diameter_mm"]),"offset_x_mm":float(m["offset_x_mm"]),"offset_y_mm":float(m["offset_y_mm"]),"countersink":m.get("countersink")})
  return {"panel_id":str(panel.get("panel_id","panel")),"units":"mm","datum":{"x":0.0,"y":0.0},"views":["top","front","right"],"dimensions":[asdict(d) for d in dims],"mounting_holes":holes,"notes":["DIMENSIONS IN MILLIMETERS","VERIFY PROCESS-SPECIFIC TOLERANCES BEFORE RELEASE"]}
