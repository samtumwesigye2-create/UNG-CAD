"""Mandatory manufacturing preflight: normalize -> validate -> layout -> compensate -> evaluate."""
from dataclasses import dataclass
from typing import Any,Dict,List
from cad_core.cutout_component import CutoutComponent,Vector2D,MountingHole,Countersink,CADValidationError
from cad_core.layout_boundary import LayoutBoundaryEvaluator
from cad_core.process_compensation import apply_manufacturing_compensation
from cad_core.structural_ribs import parse_structural_ribs,RibValidationError
from cad_core.evaluation_gate import EvaluationResult,evaluate,require_pass\nfrom cad_core.interference_engine import GeometryInterferenceEngine

@dataclass(frozen=True)
class PreflightResult:
 passed:bool
 nominal_cutouts:List[Dict[str,Any]]
 compensated_cutouts:List[Dict[str,Any]]
 evaluation:EvaluationResult
 errors:List[str]

class ManufacturingPreflightError(RuntimeError): pass

def _normalized(c):
 out=dict(c);g=c.get("geometry_payload") or c.get("dimensions")
 if not isinstance(g,dict): raise CADValidationError("cutout geometry payload required")
 out["dimensions"]=dict(g);out.pop("geometry_payload",None)
 out.setdefault("rotation",0.0);out.setdefault("clearance_mm",0.0);out.setdefault("depth_mm",-1);out.setdefault("mounting_holes",[])
 return out

def _typed(c):
 holes=[]
 for h in c.get("mounting_holes",[]):
  cs=h.get("countersink");sink=Countersink(float(cs["outer_diameter_mm"]),float(cs.get("angle_deg",90))) if cs else None
  holes.append(MountingHole(float(h["offset_x_mm"]),float(h["offset_y_mm"]),float(h["diameter_mm"]),sink))
 p=c["position"]
 return CutoutComponent(str(c["component_id"]),c["type"],Vector2D(float(p["x_mm"]),float(p["y_mm"])),float(c["rotation"]),float(c["clearance_mm"]),float(c["depth_mm"]),str(c.get("tolerance_profile","")),holes,dict(c["dimensions"]))

class ManufacturingPreflight:
 def __init__(self,panel_width:float,panel_height:float,minimum_bridge_mm:float=3.0):
  if panel_width<=0 or panel_height<=0: raise ValueError("panel dimensions must be positive")
  self.w=panel_width;self.h=panel_height;self.bridge=minimum_bridge_mm

 def run(self,cutouts:List[Dict[str,Any]],structural_ribs=None,component_envelopes=None,require_gate:bool=True)->PreflightResult:
  errors=[];nominal=[];comp=[]
  try:
   nominal=[_normalized(c) for c in cutouts]
   for c in nominal:_typed(c)
   parse_structural_ribs(structural_ribs or [],self.w,self.h)
   ok,layout_errors=LayoutBoundaryEvaluator(self.w,self.h,self.bridge).verify_layout(nominal)
   errors.extend(layout_errors)\n   hits=GeometryInterferenceEngine(self.bridge).check(nominal,structural_ribs or [],component_envelopes or [])\n   errors.extend(h.message for h in hits)
   if ok: comp=[apply_manufacturing_compensation(c) for c in nominal]
  except (CADValidationError,RibValidationError,ValueError,KeyError,TypeError) as exc: errors.append(str(exc))
  metrics={"validation_errors":float(len(errors))}
  gate=evaluate(metrics,{"validation_errors":("<=",0.0)})
  result=PreflightResult(gate.passed,nominal,comp,gate,errors)
  if require_gate:
   try: require_pass(gate)
   except RuntimeError as exc: raise ManufacturingPreflightError(str(exc)+(" | "+"; ".join(errors) if errors else "")) from exc
  return result
