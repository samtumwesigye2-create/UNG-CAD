"""Geometry-grounded material and machining estimate for flat panels."""
import math
from typing import List,Dict,Any,Tuple

class MaterialCostEstimator:
 MATERIAL_PROFILES={
  "aluminum_6061":{"density":2.70,"cost_per_kg":4.50,"machine_cost_per_m":1.20},
  "acrylic":{"density":1.18,"cost_per_kg":3.10,"machine_cost_per_m":0.40},
  "pla_plastic":{"density":1.24,"cost_per_kg":2.20,"machine_cost_per_m":0.15},
 }
 def __init__(self,material_key:str,thickness_mm:float,material_profiles=None):
  profiles=material_profiles or self.MATERIAL_PROFILES
  if material_key not in profiles: raise ValueError(f"unknown material profile: {material_key}")
  if thickness_mm<=0: raise ValueError("thickness_mm must be positive")
  self.material_key=material_key;self.profile=profiles[material_key];self.thickness=float(thickness_mm)

 @staticmethod
 def _geom(c): return c.get("geometry_payload") or c.get("dimensions") or {}

 def _calculate_cutout_perimeter_and_area(self,c:Dict[str,Any])->Tuple[float,float]:
  clr=float(c.get("clearance_mm",0));g=self._geom(c);typ=c["type"]
  if typ=="circular":
   d=float(g["diameter_mm"])+2*clr
   if d<=0: raise ValueError("invalid circular cutout")
   return math.pi*d,math.pi*(d/2)**2
  if typ in {"rectangular","usb_c","ethernet"}:
   w=float(g["width_mm"])+2*clr;h=float(g["height_mm"])+2*clr;r=max(0.0,float(g.get("corner_radius_mm",0)))
   if w<=0 or h<=0: raise ValueError("invalid rectangular cutout")
   r=min(r,w/2,h/2)
   # Rounded rectangle: straight spans + four quarter-circle corners.
   p=2*(w+h-4*r)+2*math.pi*r
   a=w*h-(4-math.pi)*r*r
   return p,a
  return 0.0,0.0

 def generate_bill_of_materials(self,flat_cutouts:List[Dict[str,Any]],panel_w:float,panel_h:float)->Dict[str,Any]:
  if panel_w<=0 or panel_h<=0: raise ValueError("panel dimensions must be positive")
  raw_area=panel_w*panel_h;cut_area=0.0;cut_len=2*(panel_w+panel_h)
  for c in flat_cutouts:
   p,a=self._calculate_cutout_perimeter_and_area(c);cut_len+=p;cut_area+=a
   for hole in c.get("mounting_holes",[]):
    d=float(hole["diameter_mm"])
    if d<=0: raise ValueError("mounting-hole diameter must be positive")
    cut_len+=math.pi*d;cut_area+=math.pi*(d/2)**2
  if cut_area>raw_area: raise ValueError("cutout area exceeds panel area; layout/overlap validation required")
  net_area=raw_area-cut_area;volume_cm3=(net_area/100)*(self.thickness/10)
  weight_kg=volume_cm3*float(self.profile["density"])/1000
  material_cost=weight_kg*float(self.profile["cost_per_kg"])
  machining_cost=(cut_len/1000)*float(self.profile["machine_cost_per_m"])
  return {
   "material_profile":self.material_key,
   "net_weight_kg":round(weight_kg,3),
   "material_utilization_pct":round(net_area/raw_area*100,2),
   "total_cut_length_meters":round(cut_len/1000,3),
   "estimated_material_cost":round(material_cost,2),
   "estimated_machining_cost":round(machining_cost,2),
   "total_projected_cost":round(material_cost+machining_cost,2),
   "estimate_basis":"Configured material/process rates; excludes stock minimums, setup, labor, tooling, tax, shipping, and scrap outside the panel envelope."
  }
