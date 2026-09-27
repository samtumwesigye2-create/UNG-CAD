"""Conservative CNC G-code planner for circular internal contours.

Generation is blocked until machine/process parameters are explicit. The
generator compensates cutter radius, validates reachability, and never assumes
a spindle speed or a machine-specific home command.
"""
from typing import List, Dict, Any

class GCodeValidationError(ValueError): pass

class UngCadGCodeGenerator:
 def __init__(self,tool_diameter_mm:float,feed_rate:int,plunge_rate:int,safe_z:float,cutting_depth:float,step_down_mm:float,spindle_rpm:int):
  vals=(tool_diameter_mm,feed_rate,plunge_rate,safe_z,cutting_depth,step_down_mm,spindle_rpm)
  if any(float(v)<=0 for v in vals): raise GCodeValidationError("all machine/process parameters must be positive")
  self.tool_radius=tool_diameter_mm/2;self.feed=feed_rate;self.plunge=plunge_rate;self.safe_z=safe_z
  self.target_z=-abs(cutting_depth);self.step_down=step_down_mm;self.rpm=spindle_rpm

 def generate_circular_contour_gcode(self,cutouts:List[Dict[str,Any]])->str:
  g=["%","O1000 (UNG-CAD VERIFIED CIRCULAR CONTOUR EXPORT)","G21","G90","G17",f"G00 Z{self.safe_z:.3f}",f"M03 S{self.rpm}"]
  for idx,c in enumerate(cutouts):
   if c.get("type")!="circular":continue
   geom=c.get("geometry_payload") or c.get("dimensions") or {}
   nominal=float(geom["diameter_mm"])/2+float(c.get("clearance_mm",0))
   path_r=nominal-self.tool_radius
   if path_r<=0: raise GCodeValidationError(f"Tool cannot fit internal opening {c.get('component_id',idx)}")
   cx=float(c["position"]["x_mm"]);cy=float(c["position"]["y_mm"]);x=cx+path_r
   g += [f"(COMPONENT {idx}: {c.get('component_id','unnamed')})",f"G00 X{x:.3f} Y{cy:.3f}",f"G01 Z0.000 F{self.plunge}"]
   z=0.0
   while z>self.target_z:
    z=max(z-self.step_down,self.target_z)
    g.append(f"G01 Z{z:.3f} F{self.plunge}")
    g.append(f"G02 X{x:.3f} Y{cy:.3f} I{-path_r:.3f} J0.000 F{self.feed}")
   g += [f"G02 X{x:.3f} Y{cy:.3f} I{-path_r:.3f} J0.000 F{self.feed}",f"G00 Z{self.safe_z:.3f}"]
  g += ["M05","M30","%"];return "\n".join(g)

 # Compatibility name; this is contour milling, not pocket clearing.
 def generate_circular_pocket_gcode(self,cutouts): return self.generate_circular_contour_gcode(cutouts)
