"""2D manufacturing interference checks for ribs, cutouts, mounting holes, and reserved component envelopes."""
import math
from dataclasses import dataclass
from typing import Any,Dict,List,Tuple

@dataclass(frozen=True)
class Interference:
 kind:str
 first_id:str
 second_id:str
 clearance_mm:float
 message:str

def _seg_dist(px,py,ax,ay,bx,by):
 dx,dy=bx-ax,by-ay
 if dx==dy==0:return math.hypot(px-ax,py-ay)
 t=max(0,min(1,((px-ax)*dx+(py-ay)*dy)/(dx*dx+dy*dy)))
 return math.hypot(px-(ax+t*dx),py-(ay+t*dy))

def _cut_radius(c):
 g=c.get("geometry_payload") or c.get("dimensions") or {};cl=float(c.get("clearance_mm",0))
 if c["type"]=="circular":return float(g["diameter_mm"])/2+cl
 if c["type"] in {"rectangular","usb_c","ethernet"}:
  return math.hypot(float(g["width_mm"])/2+cl,float(g["height_mm"])/2+cl)
 return 0.0

class GeometryInterferenceEngine:
 def __init__(self,minimum_clearance_mm:float=0.0):
  if minimum_clearance_mm<0:raise ValueError("minimum_clearance_mm cannot be negative")
  self.minimum=minimum_clearance_mm

 def check(self,cutouts:List[Dict[str,Any]],ribs=None,component_envelopes=None)->List[Interference]:
  hits=[];ribs=ribs or [];envs=component_envelopes or []
  # Rib vs cutout: exact for circles; conservative circumscribed radius for other supported profiles.
  for r in ribs:
   a,b=r["start_point"],r["end_point"];half=float(r.get("thickness_mm",3))/2;rid=str(r["rib_id"])
   for c in cutouts:
    p=c["position"];rad=_cut_radius(c);gap=_seg_dist(float(p["x_mm"]),float(p["y_mm"]),float(a["x"]),float(a["y"]),float(b["x"]),float(b["y"]))-half-rad
    if gap<self.minimum:hits.append(Interference("rib_cutout",rid,str(c["component_id"]),gap,f"Rib {rid} conflicts with cutout {c['component_id']}."))
    # Mounting holes are cutout-local and rotate with cutout.
    ang=math.radians(float(c.get("rotation",0)));co,si=math.cos(ang),math.sin(ang)
    for i,h in enumerate(c.get("mounting_holes",[])):
     ox,oy=float(h["offset_x_mm"]),float(h["offset_y_mm"]);hx=float(p["x_mm"])+ox*co-oy*si;hy=float(p["y_mm"])+ox*si+oy*co;hr=float(h["diameter_mm"])/2
     gap=_seg_dist(hx,hy,float(a["x"]),float(a["y"]),float(b["x"]),float(b["y"]))-half-hr
     if gap<self.minimum:hits.append(Interference("rib_mounting_hole",rid,f"{c['component_id']}:hole:{i}",gap,f"Rib {rid} conflicts with mounting hole {i} of {c['component_id']}."))
  # Reserved component envelopes: rotation-aware AABB overlap screening.
  boxes=[]
  for e in envs:
   p=e["position"];w=float(e["width_mm"]);h=float(e["height_mm"]);a=math.radians(float(e.get("rotation",0)));ca,sa=abs(math.cos(a)),abs(math.sin(a));ex=(w*ca+h*sa)/2;ey=(w*sa+h*ca)/2;x,y=float(p["x_mm"]),float(p["y_mm"]);boxes.append((str(e["component_id"]),(x-ex,y-ey,x+ex,y+ey)))
  for i,(aid,a) in enumerate(boxes):
   for bid,b in boxes[i+1:]:
    gx=max(b[0]-a[2],a[0]-b[2],0);gy=max(b[1]-a[3],a[1]-b[3],0);gap=math.hypot(gx,gy)
    if gap<self.minimum or (gx==0 and gy==0):hits.append(Interference("component_envelope",aid,bid,gap,f"Reserved component envelopes {aid} and {bid} overlap or violate clearance."))
  return hits
