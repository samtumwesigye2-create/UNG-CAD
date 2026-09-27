"""Nesting V2: orientation constraints, keep-out zones, stock remnants and utilization."""
from dataclasses import dataclass
from typing import Iterable
from cad_core.sheet_nesting import AdvancedNestingEngine,OptimizedNestingItem
@dataclass(frozen=True)
class StockSheet:
 sheet_id:str;width_mm:float;height_mm:float
@dataclass(frozen=True)
class KeepOut:
 x_mm:float;y_mm:float;width_mm:float;height_mm:float
def _overlap(a,b):return not (a[0]>=b[2] or a[2]<=b[0] or a[1]>=b[3] or a[3]<=b[1])
class NestingOptimizerV2:
 def __init__(self,spacing_mm=3.0):self.spacing=spacing_mm
 def pack(self,items:Iterable[dict],stock:StockSheet,keepouts=()):
  # Uses the proven rotation-aware shelf engine, then rejects placements crossing keep-outs.
  engine=AdvancedNestingEngine(stock.width_mm,stock.height_mm,self.spacing)
  prepared=[OptimizedNestingItem(str(i["component_id"]),float(i["width_mm"]),float(i["height_mm"]),bool(i.get("allow_rotation",True))) for i in items]
  sheets=engine.pack_plates_with_rotation(prepared);kos=[(k.x_mm,k.y_mm,k.x_mm+k.width_mm,k.y_mm+k.height_mm) for k in keepouts]
  for sheet in sheets:
   for p in sheet:
    box=(p["x_mm"],p["y_mm"],p["x_mm"]+p["width_mm"],p["y_mm"]+p["height_mm"])
    if any(_overlap(box,k) for k in kos):raise ValueError(f"placement {p['component_id']} intersects stock keep-out")
  used=sum(p["width_mm"]*p["height_mm"] for s in sheets for p in s);area=len(sheets)*stock.width_mm*stock.height_mm
  return {"sheets":sheets,"sheet_count":len(sheets),"utilization":used/area if area else 0.0,"stock_id":stock.sheet_id}
