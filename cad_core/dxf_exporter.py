"""DXF exporter for UNG-CAD panel layouts.

ezdxf is imported lazily so the CAD core remains usable without the optional
DXF dependency. Geometry is emitted in millimetres and separated by CAM layers.
"""
import math
from typing import List, Dict, Any

class UngCadDxfExporter:
 @staticmethod
 def export_to_dxf(file_path:str,cutouts:List[Dict[str,Any]],panel_w:float,panel_h:float):
  if panel_w<=0 or panel_h<=0: raise ValueError("panel dimensions must be positive")
  try: import ezdxf
  except ImportError as exc: raise RuntimeError("DXF export requires optional dependency 'ezdxf'") from exc
  doc=ezdxf.new("R2010");doc.header["$INSUNITS"]=4;msp=doc.modelspace()
  for name,color in (("PANEL_BORDER",1),("THROUGH_CUTS",3),("MOUNTING_HOLES",4),("COUNTERSINKS",6)):
   if name not in doc.layers: doc.layers.new(name=name,dxfattribs={"color":color})
  msp.add_lwpolyline([(0,0),(panel_w,0),(panel_w,panel_h),(0,panel_h)],close=True,dxfattribs={"layer":"PANEL_BORDER"})
  for c in cutouts:
   p=c["position"];cx,cy=float(p["x_mm"]),float(p["y_mm"]);cl=float(c.get("clearance_mm",0));g=c.get("geometry_payload") or c.get("dimensions") or {}
   rot=math.radians(float(c.get("rotation",0)));co,si=math.cos(rot),math.sin(rot)
   def tx(pt):
    x,y=pt;return cx+x*co-y*si,cy+x*si+y*co
   kind=c["type"]
   if kind=="circular":
    msp.add_circle((cx,cy),float(g["diameter_mm"])/2+cl,dxfattribs={"layer":"THROUGH_CUTS"})
   elif kind in {"rectangular","usb_c","ethernet"}:
    w=float(g["width_mm"])+2*cl;h=float(g["height_mm"])+2*cl;r=max(0,min(float(g.get("corner_radius_mm",0)),w/2,h/2))
    # LWPOLYLINE bulge=tan(90deg/4) for rounded corners.
    if r:
     b=math.tan(math.pi/8);pts=[(-w/2+r,-h/2,0),(w/2-r,-h/2,b),(w/2,-h/2+r,0),(w/2,h/2-r,b),(w/2-r,h/2,0),(-w/2+r,h/2,b),(-w/2,h/2-r,0),(-w/2,-h/2+r,b)]
     msp.add_lwpolyline([(*tx((x,y)),bulge) for x,y,bulge in pts],format="xyb",close=True,dxfattribs={"layer":"THROUGH_CUTS"})
    else:msp.add_lwpolyline([tx(q) for q in [(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2)]],close=True,dxfattribs={"layer":"THROUGH_CUTS"})
   elif kind=="arbitrary_custom":
    verts=g.get("vertices",[]);segs=g.get("segments",[])
    # DXF bulges preserve linear/arcs exactly; Beziers are emitted as SPLINE entities.
    if all(s.get("type") in {"linear","arc"} for s in segs):
     pts=[]
     for s in segs:
      x,y=tx(verts[s["start_idx"]]);pts.append((x,y,float(s.get("arc_bulge",0)) if s["type"]=="arc" else 0))
     msp.add_lwpolyline(pts,format="xyb",close=True,dxfattribs={"layer":"THROUGH_CUTS"})
    else:
     for s in segs:
      p1=tx(verts[s["start_idx"]]);p2=tx(verts[s["end_idx"]])
      if s["type"]=="linear":msp.add_line(p1,p2,dxfattribs={"layer":"THROUGH_CUTS"})
      elif s["type"]=="bezier":
       cps=[tx(q) for q in s.get("control_points",[])];msp.add_spline(fit_points=[p1,*cps,p2],dxfattribs={"layer":"THROUGH_CUTS"})
      else:
       msp.add_lwpolyline([(p1[0],p1[1],float(s.get("arc_bulge",0)))],format="xyb",dxfattribs={"layer":"THROUGH_CUTS"})
   for hole in c.get("mounting_holes",[]):
    # Hole offsets rotate with their parent component.
    hx,hy=tx((float(hole["offset_x_mm"]),float(hole["offset_y_mm"])))
    msp.add_circle((hx,hy),float(hole["diameter_mm"])/2,dxfattribs={"layer":"MOUNTING_HOLES"})
    if hole.get("countersink"):msp.add_circle((hx,hy),float(hole["countersink"]["outer_diameter_mm"])/2,dxfattribs={"layer":"COUNTERSINKS"})
  doc.saveas(file_path)
