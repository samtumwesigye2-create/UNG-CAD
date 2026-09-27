"""DXF datum/baseline annotation for manufactured panel drawings."""
from typing import List,Dict,Any

class UngCadAutoDimensioner:
 @staticmethod
 def append_datum_dimensions(dxf_file_path:str,flat_cutouts:List[Dict[str,Any]],offset_distance:float=15.0)->None:
  if offset_distance<=0: raise ValueError("offset_distance must be positive")
  try: import ezdxf
  except ImportError as exc: raise RuntimeError("ezdxf is required for DXF dimensioning") from exc
  doc=ezdxf.readfile(dxf_file_path);msp=doc.modelspace()
  if "DIMENSIONS" not in doc.layers: doc.layers.new(name="DIMENSIONS",dxfattribs={"color":5})
  if "DimText" not in doc.styles: doc.styles.new("DimText",dxfattribs={"font":"txt.shx"})
  for c in flat_cutouts:
   pos=c["position"];cx=float(pos["x_mm"]);cy=float(pos["y_mm"])
   # Baseline dimensions from the panel datum (0,0) to feature center.
   dx=msp.add_linear_dim(base=(cx,-offset_distance),p1=(0.0,cy),p2=(cx,cy),angle=0,dxfattribs={"layer":"DIMENSIONS","dimstyle":"Standard"})
   dy=msp.add_linear_dim(base=(-offset_distance,cy),p1=(cx,0.0),p2=(cx,cy),angle=90,dxfattribs={"layer":"DIMENSIONS","dimstyle":"Standard"})
   # ezdxf dimensions must be rendered to create dimension geometry.
   for dim in (dx,dy):
    if hasattr(dim,"render"): dim.render()
   if c["type"]=="circular":
    g=c.get("geometry_payload") or c.get("dimensions") or {};d=float(g["diameter_mm"])+2*float(c.get("clearance_mm",0))
    if d<=0: raise ValueError("circular dimension must be positive")
    text=msp.add_text(f"%%c{d:.1f}",dxfattribs={"layer":"DIMENSIONS","height":2.5,"style":"DimText"})
    text.set_placement((cx+d/2+2,cy+2))
  doc.save()
