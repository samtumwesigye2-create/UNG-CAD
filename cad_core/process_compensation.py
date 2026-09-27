"""Manufacturing-process compensation for nominal internal cutout geometry.

Values are configurable process parameters, not universal machine constants.
Positive diameter/dimension deltas enlarge internal openings; kerf values reduce
the commanded path envelope for centered-beam/jet cutting.
"""
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict

@dataclass(frozen=True)
class ProcessCompensation:
    kerf_mm: float=0.0
    internal_delta_mm: float=0.0
    tool_radius_mm: float=0.0
    shrinkage_fraction: float=0.0

DEFAULT_PROFILES={
 "laser_cut":ProcessCompensation(kerf_mm=0.12),
 "waterjet":ProcessCompensation(kerf_mm=1.00),
 "3d_print_pla":ProcessCompensation(internal_delta_mm=0.15),
 "3d_print_petg":ProcessCompensation(internal_delta_mm=0.20),
 "3d_print_abs":ProcessCompensation(internal_delta_mm=0.25),
 "cnc_mill_aluminum":ProcessCompensation(tool_radius_mm=1.00),
}

def apply_manufacturing_compensation(nominal_cutout:Dict[str,Any],parameters:ProcessCompensation|None=None)->Dict[str,Any]:
    out=deepcopy(nominal_cutout);profile=out.get("tolerance_profile")
    p=parameters or DEFAULT_PROFILES.get(profile,ProcessCompensation())
    g=out.get("geometry_payload") or out.get("dimensions")
    if not isinstance(g,dict): raise ValueError("cutout geometry payload required")
    # CNC cutter-radius compensation belongs to toolpath generation, not nominal CAD size.
    out["process_compensation"]={"profile":profile,"kerf_mm":p.kerf_mm,"internal_delta_mm":p.internal_delta_mm,"tool_radius_mm":p.tool_radius_mm,"shrinkage_fraction":p.shrinkage_fraction}
    path_delta=p.internal_delta_mm-p.kerf_mm
    if p.shrinkage_fraction:
        scale=1.0/(1.0-p.shrinkage_fraction)
    else: scale=1.0
    if out.get("type")=="circular":
        g["diameter_mm"]=float(g["diameter_mm"])*scale+path_delta
        if g["diameter_mm"]<=0: raise ValueError("compensation produced invalid diameter")
    elif out.get("type") in {"rectangular","usb_c","ethernet"}:
        for k in ("width_mm","height_mm"):
            g[k]=float(g[k])*scale+path_delta
            if g[k]<=0: raise ValueError("compensation produced invalid dimension")
    return out
