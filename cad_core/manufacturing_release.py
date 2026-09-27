"""Manufacturing release record tying preflight, drawings and inspection together."""
from dataclasses import dataclass
from typing import Any,Dict
from cad_core.engineering_drawings import EngineeringDrawingGenerator
@dataclass(frozen=True)
class ManufacturingRelease:
 panel_id:str;drawing:Dict[str,Any];preflight_passed:bool;inspection_required:bool=True
def build_release(panel:Dict[str,Any],preflight_result)->ManufacturingRelease:
 if not preflight_result.passed:raise RuntimeError("manufacturing release blocked by failed preflight")
 return ManufacturingRelease(str(panel.get("panel_id","panel")),EngineeringDrawingGenerator().generate(panel),True,True)
