"""Deterministic shelf-based stock-sheet nesting for panel manufacturing."""
from dataclasses import dataclass
from typing import List,Dict,Tuple,Any

@dataclass
class NestingItem:
 id:str;width:float;height:float
 placed_x:float=0.0;placed_y:float=0.0;sheet_index:int=-1
 rotated:bool=False
 @property
 def nominal_x(self): return self.placed_x
 @property
 def nominal_y(self): return self.placed_y

class SheetNestingEngine:
 def __init__(self,sheet_width:float,sheet_height:float,tool_spacing_mm:float=6.0,allow_rotation:bool=True):
  if sheet_width<=0 or sheet_height<=0 or tool_spacing_mm<0: raise ValueError("invalid sheet/spacing dimensions")
  self.sheet_w=sheet_width;self.sheet_h=sheet_height;self.padding=tool_spacing_mm;self.allow_rotation=allow_rotation

 def pack_plates(self,plates:List[Dict[str,Any]])->Tuple[List[NestingItem],int]:
  # Padding is split equally around each part; stored width/height are occupied envelopes.
  items=[]
  for p in plates:
   w=float(p["width_mm"]);h=float(p["height_mm"])
   if w<=0 or h<=0: raise ValueError(f"Component {p['panel_id']} has invalid dimensions.")
   candidates=[(w,h,False)]
   if self.allow_rotation and w!=h:candidates.append((h,w,True))
   feasible=[c for c in candidates if c[0]+self.padding<=self.sheet_w and c[1]+self.padding<=self.sheet_h]
   if not feasible: raise ValueError(f"Component {p['panel_id']} exceeds raw stock sheet dimensions.")
   # Prefer orientation with smaller shelf height; tie-break on width.
   w,h,rot=min(feasible,key=lambda c:(c[1],c[0]))
   items.append(NestingItem(str(p["panel_id"]),w+self.padding,h+self.padding,rotated=rot))
  items.sort(key=lambda i:(-i.height,-i.width,i.id))
  sheets=[];placed=[]
  for item in items:
   done=False
   for si,levels in enumerate(sheets):
    for level in levels:
     if level[1]+item.width<=self.sheet_w and item.height<=level[2]:
      item.placed_x=level[1];item.placed_y=level[0];item.sheet_index=si;level[1]+=item.width;done=True;break
    if done:break
    top=levels[-1][0]+levels[-1][2] if levels else 0
    if top+item.height<=self.sheet_h:
     levels.append([top,item.width,item.height]);item.placed_x=0;item.placed_y=top;item.sheet_index=si;done=True;break
   if not done:
    sheets.append([[0.0,item.width,item.height]]);item.sheet_index=len(sheets)-1;placed.append(item);continue
   placed.append(item)
  # Report coordinates at the actual part edge, not the padded-envelope edge.
  margin=self.padding/2
  for item in placed:item.placed_x+=margin;item.placed_y+=margin
  return placed,len(sheets)
