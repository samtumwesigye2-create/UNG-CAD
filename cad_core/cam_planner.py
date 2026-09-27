"""Process-explicit 2.5D CAM planner for internal contours and rectangular pockets."""
import math
from typing import Any,Dict,List
class CAMValidationError(ValueError):pass
class UngCadCAMPlanner:
 def __init__(self,tool_diameter_mm,feed_rate,plunge_rate,safe_z,cutting_depth,step_down_mm,spindle_rpm,finish_allowance_mm=0.0):
  vals=(tool_diameter_mm,feed_rate,plunge_rate,safe_z,cutting_depth,step_down_mm,spindle_rpm)
  if any(float(v)<=0 for v in vals) or finish_allowance_mm<0:raise CAMValidationError("invalid CAM parameters")
  self.r=tool_diameter_mm/2;self.feed=int(feed_rate);self.plunge=int(plunge_rate);self.safe=float(safe_z);self.depth=-abs(float(cutting_depth));self.step=float(step_down_mm);self.rpm=int(spindle_rpm);self.finish=float(finish_allowance_mm)
 def _depths(self):
  z=0.;out=[]
  while z>self.depth:z=max(z-self.step,self.depth);out.append(z)
  return out
 def generate(self,features:List[Dict[str,Any]])->str:
  g=["%","O2000 (UNG-CAD CAM)","G21","G90","G17",f"G00 Z{self.safe:.3f}",f"M03 S{self.rpm}"]
  for i,c in enumerate(features):
   p=c["position"];x=float(p["x_mm"]);y=float(p["y_mm"]);geom=c.get("geometry_payload") or c.get("dimensions") or {};typ=c["type"];g.append(f"(FEATURE {i} {c.get('component_id','unnamed')})")
   if typ=="circular":
    pr=float(geom["diameter_mm"])/2+float(c.get("clearance_mm",0))-self.r-self.finish
    if pr<=0:raise CAMValidationError("tool cannot fit circular contour")
    sx=x+pr;g += [f"G00 X{sx:.3f} Y{y:.3f}"]
    for z in self._depths():g += [f"G01 Z{z:.3f} F{self.plunge}",f"G02 X{sx:.3f} Y{y:.3f} I{-pr:.3f} J0.000 F{self.feed}"]
   elif typ in {"rectangular","usb_c","ethernet"}:
    hw=float(geom["width_mm"])/2+float(c.get("clearance_mm",0))-self.r-self.finish;hh=float(geom["height_mm"])/2+float(c.get("clearance_mm",0))-self.r-self.finish
    if min(hw,hh)<=0:raise CAMValidationError("tool cannot fit rectangular contour")
    pts=[(x-hw,y-hh),(x+hw,y-hh),(x+hw,y+hh),(x-hw,y+hh),(x-hw,y-hh)];g.append(f"G00 X{pts[0][0]:.3f} Y{pts[0][1]:.3f}")
    for z in self._depths():
     g.append(f"G01 Z{z:.3f} F{self.plunge}")
     g += [f"G01 X{px:.3f} Y{py:.3f} F{self.feed}" for px,py in pts[1:]]
   else:raise CAMValidationError(f"unsupported CAM feature: {typ}")
   g.append(f"G00 Z{self.safe:.3f}")
  g += ["M05","M30","%"];return "\n".join(g)
