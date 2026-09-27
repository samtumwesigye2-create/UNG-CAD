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


@dataclass
class OptimizedNestingItem(NestingItem):
 @property
 def is_rotated(self): return self.rotated

class AdvancedNestingEngine(SheetNestingEngine):
 """FFDH-style shelf nesting that evaluates normal and 90-degree orientation at each placement."""
 def __init__(self,sheet_width:float,sheet_height:float,tool_spacing_mm:float=6.0):
  super().__init__(sheet_width,sheet_height,tool_spacing_mm,allow_rotation=True)

 def pack_plates_with_rotation(self,plates:List[Dict[str,Any]])->Tuple[List[OptimizedNestingItem],int]:
  raw=[]
  for p in plates:
   w=float(p["width_mm"]);h=float(p["height_mm"])
   if w<=0 or h<=0: raise ValueError(f"Component {p['panel_id']} has invalid dimensions.")
   if min(w+self.padding,h+self.padding)>min(self.sheet_w,self.sheet_h) and max(w+self.padding,h+self.padding)>max(self.sheet_w,self.sheet_h):
    raise ValueError(f"Component {p['panel_id']} exceeds raw stock sheet dimensions.")
   raw.append((str(p["panel_id"]),w+self.padding,h+self.padding))
  raw.sort(key=lambda x:(-max(x[1],x[2]),-min(x[1],x[2]),x[0]))
  sheets=[];placed=[]
  for ident,w,h in raw:
   options=[(w,h,False)]+([] if w==h else [(h,w,True)])
   choice=None
   # Best-fit existing shelf: minimize horizontal waste, then prefer no rotation.
   for si,levels in enumerate(sheets):
    for li,level in enumerate(levels):
     for ow,oh,rot in options:
      if level[1]+ow<=self.sheet_w and oh<=level[2]:
       score=(self.sheet_w-(level[1]+ow),rot)
       if choice is None or score<choice[0]: choice=(score,"level",si,li,ow,oh,rot)
   if choice is None:
    # Best fresh shelf across existing sheets: minimize resulting shelf height.
    for si,levels in enumerate(sheets):
     top=levels[-1][0]+levels[-1][2] if levels else 0.0
     for ow,oh,rot in options:
      if ow<=self.sheet_w and top+oh<=self.sheet_h:
       score=(oh,self.sheet_w-ow,rot)
       if choice is None or score<choice[0]: choice=(score,"new",si,-1,ow,oh,rot)
   if choice is None:
    feasible=[o for o in options if o[0]<=self.sheet_w and o[1]<=self.sheet_h]
    if not feasible: raise ValueError(f"Component {ident} exceeds raw stock sheet dimensions.")
    ow,oh,rot=min(feasible,key=lambda o:(o[1],self.sheet_w-o[0],o[2]));sheets.append([[0.0,ow,oh]])
    item=OptimizedNestingItem(ident,ow,oh,self.padding/2,self.padding/2,len(sheets)-1,rot);placed.append(item);continue
   _,kind,si,li,ow,oh,rot=choice;levels=sheets[si]
   if kind=="level": y,x=levels[li][0],levels[li][1];levels[li][1]+=ow
   else:
    y=levels[-1][0]+levels[-1][2] if levels else 0.0;x=0.0;levels.append([y,ow,oh])
   placed.append(OptimizedNestingItem(ident,ow,oh,x+self.padding/2,y+self.padding/2,si,rot))
  return placed,len(sheets)
