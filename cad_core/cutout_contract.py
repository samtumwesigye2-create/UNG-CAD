"""Parametric panel/component cutout contract used by CAD and Manufacturing."""
from dataclasses import dataclass, field
from typing import Any, Dict, List
import math, uuid

SUPPORTED_TYPES={"circular","rectangular","usb_c","ethernet","keyed","arbitrary_custom"}
TOLERANCE_CLEARANCE={"3d_print_pla":0.20,"3d_print_petg":0.25,"3d_print_abs":0.30,"cnc_mill_aluminum":0.10,"laser_cut":0.10}

@dataclass(frozen=True)
class Cutout:
    component_id: str
    type: str
    x_mm: float
    y_mm: float
    rotation: float
    clearance_mm: float
    depth_mm: float
    geometry: Dict[str,Any]
    mounting_holes: List[Dict[str,Any]]=field(default_factory=list)
    tolerance_profile: str|None=None

def parse_cutout(data: Dict[str,Any]) -> Cutout:
    uuid.UUID(str(data["component_id"]))
    kind=data["type"]
    if kind not in SUPPORTED_TYPES: raise ValueError("unsupported cutout type")
    p=data["position"]; g=dict(data.get("geometry_payload") or {})
    clearance=float(data.get("clearance_mm",TOLERANCE_CLEARANCE.get(data.get("tolerance_profile"),.2)))
    depth=float(data["depth_mm"])
    if clearance<0 or (depth<=0 and depth!=-1): raise ValueError("invalid clearance/depth")
    if kind=="circular" and float(g.get("diameter_mm",0))<=0: raise ValueError("diameter_mm required")
    if kind in {"rectangular","usb_c","ethernet"} and (float(g.get("width_mm",0))<=0 or float(g.get("height_mm",0))<=0): raise ValueError("width/height required")
    if kind=="keyed" and float(g.get("inner_diameter_mm",0))<=0: raise ValueError("inner_diameter_mm required")
    if kind=="arbitrary_custom":
        vertices=g.get("vertices",[]); segments=g.get("segments",[])
        if len(vertices)<3 or len(segments)<3: raise ValueError("custom geometry requires >=3 vertices and segments")
        n=len(vertices)
        for seg in segments:
            a,b=seg.get("start_idx"),seg.get("end_idx")
            if not isinstance(a,int) or not isinstance(b,int) or not (0<=a<n and 0<=b<n): raise ValueError("custom segment index out of range")
            st=seg.get("type")
            if st not in {"linear","arc","bezier"}: raise ValueError("unsupported custom segment type")
            if st=="arc" and "arc_bulge" not in seg: raise ValueError("arc_bulge required for arc")
            if st=="bezier" and not 1<=len(seg.get("control_points",[]))<=2: raise ValueError("bezier requires one or two control points")
    return Cutout(str(data["component_id"]),kind,float(p["x_mm"]),float(p["y_mm"]),float(data["rotation"]),clearance,depth,g,list(data.get("mounting_holes") or []),data.get("tolerance_profile"))

def compensated_geometry(c: Cutout) -> Dict[str,Any]:
    g=dict(c.geometry); d=2*c.clearance_mm
    if "diameter_mm" in g:g["diameter_mm"]+=d
    if "inner_diameter_mm" in g:g["inner_diameter_mm"]+=d
    if "width_mm" in g:g["width_mm"]+=d
    if "height_mm" in g:g["height_mm"]+=d
    return g
