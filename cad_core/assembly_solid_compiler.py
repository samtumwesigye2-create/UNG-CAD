"""Recursive CadQuery assembly compiler for UNG-CAD panel trees."""
import math,re
from pathlib import Path
from typing import Any,Dict,Tuple

class UngCadAssemblySolidCompiler:
 @staticmethod
 def _transform(x:float,y:float,tx:float,ty:float,deg:float)->Tuple[float,float]:
  a=math.radians(deg);return tx+x*math.cos(a)-y*math.sin(a),ty+x*math.sin(a)+y*math.cos(a)

 @classmethod
 def compile(cls,assembly:Dict[str,Any],output_format:str="STEP",default_thickness_mm:float|None=None)->str:
  try: import cadquery as cq
  except ImportError as exc: raise RuntimeError("CadQuery is required for assembly solid compilation") from exc
  fmt=output_format.upper()
  if fmt not in {"STEP","STL"}: raise ValueError("output_format must be STEP or STL")
  root=assembly.get("root_panel",assembly);assy=cq.Assembly(name=str(assembly.get("assembly_id","UNG_ASSEMBLY")))
  seen=set()
  def walk(node,parent_xy=(0.0,0.0),parent_z=0.0,parent_rot=0.0):
   pid=str(node["panel_id"])
   if pid in seen: raise ValueError(f"duplicate/cyclic panel_id: {pid}")
   seen.add(pid);w=float(node["width_mm"]);h=float(node["height_mm"]);t=float(node.get("thickness_mm",default_thickness_mm or 0))
   if min(w,h,t)<=0: raise ValueError(f"panel {pid} requires positive width, height, and thickness")
   pos=node.get("position",{"x":0,"y":0,"z":0});x,y=cls._transform(float(pos.get("x",0)),float(pos.get("y",0)),parent_xy[0],parent_xy[1],parent_rot);z=parent_z+float(pos.get("z",0));rot=(parent_rot+float(node.get("rotation",0)))%360
   # Local panel coordinates use 0..w / 0..h datum, while CadQuery boxes are centered.
   solid=cq.Workplane("XY").box(w,h,t)
   for c in node.get("cutouts",[]):
    p=c["position"];cx=float(p["x_mm"])-w/2;cy=float(p["y_mm"])-h/2;g=c.get("geometry_payload") or c.get("dimensions") or {};cl=float(c.get("clearance_mm",0));cr=float(c.get("rotation",0))
    wp=solid.faces(">Z").workplane().center(cx,cy)
    if c["type"]=="circular": solid=wp.circle(float(g["diameter_mm"])/2+cl).cutThruAll()
    elif c["type"] in {"rectangular","usb_c","ethernet"}: solid=wp.transformed(rotate=(0,0,cr)).rect(float(g["width_mm"])+2*cl,float(g["height_mm"])+2*cl).cutThruAll()
    else: raise ValueError(f"unsupported assembly solid cutout type: {c['type']}")
   # Ribs are local backside solids, matching the viewer convention.
   for r in node.get("structural_ribs",[]):
    a,b=r["start_point"],r["end_point"];dx=float(b["x"])-float(a["x"]);dy=float(b["y"])-float(a["y"]);L=math.hypot(dx,dy);rw=float(r.get("thickness_mm",3));rh=float(r.get("height_mm",6))
    if min(L,rw,rh)<=0: raise ValueError(f"invalid rib {r.get('rib_id','')}")
    mx=(float(a["x"])+float(b["x"]))/2-w/2;my=(float(a["y"])+float(b["y"]))/2-h/2;ang=math.degrees(math.atan2(dy,dx))
    rib=cq.Workplane("XY").box(L,rw,rh).rotate((0,0,0),(0,0,1),ang).translate((mx,my,-(t+rh)/2));solid=solid.union(rib)
   loc=cq.Location(cq.Vector(x,y,z),cq.Vector(0,0,1),rot)
   assy.add(solid,name=pid,loc=loc)
   for child in node.get("child_panels",[]): walk(child,(x,y),z,rot)
  walk(root)
  ident=re.sub(r"[^A-Za-z0-9_.-]","_",str(assembly.get("assembly_id","compiled_assembly")));out=Path("/tmp/ung_cad_builds");out.mkdir(parents=True,exist_ok=True);path=out/f"assembly_{ident}.{'step' if fmt=='STEP' else 'stl'}"
  if fmt=="STEP": cq.exporters.export(assy,str(path))
  else:
   # STL has no assembly container semantics; fuse positioned solids for one mesh artifact.
   shapes=[o.obj.moved(o.loc) for o in assy.objects.values()];combined=shapes[0]
   for s in shapes[1:]: combined=combined.union(s)
   cq.exporters.export(combined,str(path))
  return str(path)
