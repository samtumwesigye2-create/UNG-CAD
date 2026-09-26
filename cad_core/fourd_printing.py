"""4D-print toolpath transformation contracts.

This module programs spatially varying process parameters and stimulus events while
keeping the result explicitly experimental. It does not claim a universal mapping
from feed rate to residual strain or final shape.
"""
from dataclasses import dataclass
import math, re

_MOVE_RE=re.compile(r"^(G0|G1)\b",re.I)
_AXIS_RE={a:re.compile(rf"\b{a}(-?\d+(?:\.\d+)?)",re.I) for a in "XYZEF"}

@dataclass(frozen=True)
class FourDProfile:
    base_speed_mm_min: float=1800.0
    max_speed_boost_mm_min: float=3600.0
    stripe_mm: float=5.0
    light_interval_mm: float=0.5
    light_dwell_ms: int=5000
    active_tool: int=0
    passive_tool: int=1
    min_speed_mm_min: float=300.0
    max_speed_mm_min: float=12000.0

@dataclass(frozen=True)
class FourDCompilation:
    gcode: str
    tool_changes: int
    light_dwells: int
    modified_moves: int
    experimental: bool=True

class FourDPrintEngine:
    def __init__(self,profile:FourDProfile|None=None):
        self.profile=profile or FourDProfile()

    def _speed(self,x:float,y:float)->int:
        p=self.profile
        gradient=(math.sin(x*.1)*math.cos(y*.1)+1.0)/2.0
        value=p.base_speed_mm_min+gradient*p.max_speed_boost_mm_min
        return int(max(p.min_speed_mm_min,min(p.max_speed_mm_min,value)))

    def compile(self,text:str)->FourDCompilation:
        p=self.profile
        x=y=z=0.0
        current_tool=p.active_tool
        last_light_bucket=None
        out=["; --- UNG 4D PRINT ENGINE ---",
             "; EXPERIMENTAL: process modulation requires material/printer calibration."]
        tool_changes=light_dwells=modified_moves=0
        for raw in text.splitlines():
            code,sep,comment=raw.partition(";")
            clean=code.strip()
            for axis,var in (("X","x"),("Y","y"),("Z","z")):
                m=_AXIS_RE[axis].search(clean)
                if m:
                    if var=="x": x=float(m.group(1))
                    elif var=="y": y=float(m.group(1))
                    else: z=float(m.group(1))
            if clean and z>0 and p.light_interval_mm>0:
                bucket=int((z+1e-9)/p.light_interval_mm)
                if bucket!=last_light_bucket and abs(z-bucket*p.light_interval_mm)<1e-6:
                    out.append(f"G4 P{p.light_dwell_ms} ; 4D LIGHT EXPOSURE EVENT")
                    light_dwells+=1
                    last_light_bucket=bucket
            if _MOVE_RE.match(clean) and ("X" in clean.upper() or "Y" in clean.upper()):
                target=p.active_tool if (int(y/p.stripe_mm)%2==0) else p.passive_tool
                if target!=current_tool:
                    out.append(f"T{target} ; 4D MATERIAL REGION")
                    current_tool=target
                    tool_changes+=1
                speed=self._speed(x,y)
                if _AXIS_RE["F"].search(clean):
                    clean=_AXIS_RE["F"].sub(f"F{speed}",clean)
                else:
                    clean=f"{clean} F{speed}"
                suffix=f" ; {comment.strip()}" if sep and comment.strip() else ""
                out.append(f"{clean}{suffix} ; 4D PROCESS SPEED")
                modified_moves+=1
            else:
                out.append(raw)
        return FourDCompilation("\n".join(out)+"\n",tool_changes,light_dwells,modified_moves)

def compile_4d_gcode(text:str,profile:FourDProfile|None=None)->FourDCompilation:
    return FourDPrintEngine(profile).compile(text)
