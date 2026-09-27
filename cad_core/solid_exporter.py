"""Optional CadQuery STEP/STL solid compiler for flat manufactured panels."""
import math,os,re
from pathlib import Path
from typing import Dict,Any\nfrom cad_core.solid_features import validate_features

class UngCadSolidExporter:
 @staticmethod
 def generate_3d_solid(panel_json:Dict[str,Any],output_format:str="STEP")->str:
  try: import cadquery as cq
  except ImportError as exc: raise RuntimeError("CadQuery is required for STEP/STL solid export") from exc
  fmt=output_format.upper()
  if fmt not in {"STEP","STL"}: raise ValueError("output_format must be STEP or STL")
  w=float(panel_json["width_mm"]);h=float(panel_json["height_mm"]);t=float(panel_json["thickness_mm"])
  if min(w,h,t)<=0: raise ValueError("panel dimensions and thickness must be positive")
  solid=cq.Workplane("XY").box(w,h,t)\n  validate_features(panel_json.get("features",[]))
  def geom(c): return c.get("geometry_payload") or c.get("dimensions") or {}
  def xy(pos): return float(pos["x_mm"])-w/2,float(pos["y_mm"])-h/2
  for c in panel_json.get("cutouts",[]):
   cx,cy=xy(c["position"]);rot=float(c.get("rotation",0));cl=float(c.get("clearance_mm",0));g=geom(c)
   wp=solid.faces(">Z").workplane().center(cx,cy)
   typ=c["type"]
   if typ=="circular":
    r=float(g["diameter_mm"])/2+cl
    if r<=0: raise ValueError("invalid circular cutout")
    solid=wp.circle(r).cutThruAll()
   elif typ in {"rectangular","usb_c","ethernet"}:
    rw=float(g["width_mm"])+2*cl;rh=float(g["height_mm"])+2*cl
    if min(rw,rh)<=0: raise ValueError("invalid rectangular cutout")
    wp=wp.transformed(rotate=(0,0,rot))
    cr=max(0.0,float(g.get("corner_radius_mm",0)))
    if cr:
     cr=min(cr,rw/2,rh/2);solid=wp.rect(rw-2*cr,rh).union(wp.rect(rw,rh-2*cr)).union(wp.pushPoints([(sx*(rw/2-cr),sy*(rh/2-cr)) for sx in (-1,1) for sy in (-1,1)]).circle(cr)).cutThruAll()
    else: solid=wp.rect(rw,rh).cutThruAll()
   else: raise ValueError(f"unsupported solid cutout type: {typ}")
   # Hole offsets are cutout-local and rotate with the cutout.
   a=math.radians(rot);co,si=math.cos(a),math.sin(a)
   for hole in c.get("mounting_holes",[]):
    ox=float(hole["offset_x_mm"]);oy=float(hole["offset_y_mm"]);hx=cx+ox*co-oy*si;hy=cy+ox*si+oy*co;d=float(hole["diameter_mm"])
    if d<=0: raise ValueError("mounting-hole diameter must be positive")
    cs=hole.get("countersink")
    if cs:
     outer=float(cs["outer_diameter_mm"]);angle=float(cs.get("angle_deg",90))
     if outer<=d or not 0<angle<180: raise ValueError("invalid countersink geometry")
     depth=(outer/2-d/2)/math.tan(math.radians(angle/2))
     solid=solid.faces(">Z").workplane().center(hx,hy).cskHole(d,outer,angle,depth=t)
    else: solid=solid.faces(">Z").workplane().center(hx,hy).hole(d,depth=t)
  for f in panel_json.get("features",[]):
   typ=f["type"];p=f.get("position",{"x_mm":w/2,"y_mm":h/2});fx,fy=xy(p)
   if typ=="slot":
    L=float(f["length_mm"]);W=float(f["width_mm"]);r=W/2
    solid=solid.faces(">Z").workplane().center(fx,fy).slot2D(L,W,float(f.get("rotation",0))).cutThruAll()
   elif typ in {"boss","standoff"}:
    solid=solid.faces(">Z").workplane().center(fx,fy).circle(float(f["diameter_mm"])/2).extrude(float(f["height_mm"]))
   elif typ=="counterbore":
    solid=solid.faces(">Z").workplane().center(fx,fy).circle(float(f["diameter_mm"])/2).cutBlind(-float(f["depth_mm"]))
   elif typ=="fillet": solid=solid.edges(f.get("selector","|Z")).fillet(float(f["size_mm"]))
   elif typ=="chamfer": solid=solid.edges(f.get("selector","|Z")).chamfer(float(f["size_mm"]))
  ident=re.sub(r"[^A-Za-z0-9_.-]","_",str(panel_json.get("panel_id","compiled_output")))
  out=Path("/tmp/ung_cad_builds");out.mkdir(parents=True,exist_ok=True);path=out/f"solid_model_{ident}.{'step' if fmt=='STEP' else 'stl'}"
  cq.exporters.export(solid,str(path));return str(path)
