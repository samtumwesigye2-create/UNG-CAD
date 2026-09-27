"""Fast structural screening for panel cutout layouts."""
import math
from typing import List, Tuple, Dict, Any

class LayoutBoundaryEvaluator:
    def __init__(self,panel_width:float,panel_height:float,minimum_bridge_mm:float=3.0):
        if panel_width<=0 or panel_height<=0 or minimum_bridge_mm<0: raise ValueError("invalid panel/bridge dimensions")
        self.panel_width=panel_width;self.panel_height=panel_height;self.min_bridge=minimum_bridge_mm

    @staticmethod
    def _geom(c):
        return c.get("geometry_payload") or c.get("dimensions") or {}

    def _get_bounding_box(self,c:Dict[str,Any])->Tuple[float,float,float,float]:
        p=c["position"];x=float(p["x_mm"]);y=float(p["y_mm"]);clr=float(c.get("clearance_mm",0));g=self._geom(c)
        if c["type"]=="circular":
            r=float(g["diameter_mm"])/2+clr;return x-r,y-r,x+r,y+r
        if c["type"] in {"rectangular","usb_c","ethernet"}:
            hw=float(g["width_mm"])/2+clr;hh=float(g["height_mm"])/2+clr
            a=math.radians(float(c.get("rotation",0)));ca,sa=abs(math.cos(a)),abs(math.sin(a))
            ex=hw*ca+hh*sa;ey=hw*sa+hh*ca
            return x-ex,y-ey,x+ex,y+ey
        if c["type"]=="arbitrary_custom":
            vs=g.get("vertices",[])
            if not vs:return x,y,x,y
            a=math.radians(float(c.get("rotation",0)));ca,sa=math.cos(a),math.sin(a)
            pts=[(x+vx*ca-vy*sa,y+vx*sa+vy*ca) for vx,vy in vs]
            xs=[q[0] for q in pts];ys=[q[1] for q in pts]
            return min(xs)-clr,min(ys)-clr,max(xs)+clr,max(ys)+clr
        return x,y,x,y

    @staticmethod
    def _box_gap(a,b):
        gx=max(b[0]-a[2],a[0]-b[2],0.0);gy=max(b[1]-a[3],a[1]-b[3],0.0)
        return math.hypot(gx,gy)

    def verify_layout(self,cutouts:List[Dict[str,Any]]):
        errors=[];boxes=[self._get_bounding_box(c) for c in cutouts]
        for i,c1 in enumerate(cutouts):
            b1=boxes[i]
            if b1[0]<self.min_bridge or b1[2]>self.panel_width-self.min_bridge or b1[1]<self.min_bridge or b1[3]>self.panel_height-self.min_bridge:
                errors.append(f"Component {c1['component_id']} breaches safe outer panel structural border limits.")
            for j in range(i+1,len(cutouts)):
                c2=cutouts[j];b2=boxes[j]
                if c1["type"]=="circular" and c2["type"]=="circular":
                    g1,g2=self._geom(c1),self._geom(c2)
                    dist=math.hypot(float(c1["position"]["x_mm"])-float(c2["position"]["x_mm"]),float(c1["position"]["y_mm"])-float(c2["position"]["y_mm"]))
                    r1=float(g1["diameter_mm"])/2+float(c1.get("clearance_mm",0));r2=float(g2["diameter_mm"])/2+float(c2.get("clearance_mm",0))
                    if dist<r1+r2+self.min_bridge:
                        errors.append(f"Collision/Thin Wall structural risk identified between circles: {c1['component_id']} and {c2['component_id']}.")
                elif self._box_gap(b1,b2)<self.min_bridge:
                    errors.append(f"General structural bridge warning: {c1['component_id']} is too close to {c2['component_id']}.")
        return not errors,errors
