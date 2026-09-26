import argparse
import math
import re
from pathlib import Path

MOVE_RE = re.compile(r"^\s*G1\b", re.I)
AXIS_RE = re.compile(r"([XYZEF])(-?\d+(?:\.\d+)?)", re.I)
META_RE = re.compile(r";\s*UNG_CAD_4D_TRANSITION_HEIGHT\s*=\s*(-?\d+(?:\.\d+)?)", re.I)

class Missing4DMetadataError(ValueError):
    pass

def _axis(line, key):
    vals={k.upper():float(v) for k,v in AXIS_RE.findall(line.split(";",1)[0])}
    return vals.get(key)

def _metadata_height(lines):
    for raw in lines[:500]:
        m=META_RE.search(raw)
        if m:
            value=float(m.group(1))
            if value <= 0: raise Missing4DMetadataError("4D_METADATA_CORRUPT: transition height must be > 0")
            return value
    raise Missing4DMetadataError("4D_METADATA_MISSING: geometry-driven material mode requires UNG_CAD_4D_TRANSITION_HEIGHT or an explicit override")

def compile_ad5m_4d(gcode, *, thermal=False, thermal_base=3000, thermal_boost=6000,
                    material_swap=False, transition_height_mm=None, geometry_driven=False,
                    light=False, light_interval_mm=None):
    """Shared UNG-CAD/FastAPI/CLI 4D post-processor. PAUSE never auto-resumes."""
    lines=gcode.splitlines(True)
    if thermal_base <= 0 or thermal_boost < 0: raise ValueError("invalid thermal feedrate settings")
    target=None
    if material_swap:
        if transition_height_mm is not None:
            target=float(transition_height_mm)
            if target <= 0: raise Missing4DMetadataError("4D_INVALID_MANUAL_OVERRIDE: transition height must be > 0")
        elif geometry_driven:
            target=_metadata_height(lines)
        else:
            raise Missing4DMetadataError("4D_METADATA_MISSING: material swap requires geometry metadata or an explicit transition height")
    if light:
        if light_interval_mm is None or float(light_interval_mm) <= 0: raise ValueError("light_interval_mm must be > 0 when light treatment is enabled")
        light_interval_mm=float(light_interval_mm)

    out=["; --- UNG-CAD EXPERIMENTAL 4D / AD5M ---\n",
         "; PAUSE checkpoints require operator-controlled resume.\n"]
    if target is not None: out.append(f"; UNG_CAD_4D_TRANSITION_HEIGHT={target:g}\n")
    cx=cy=cz=0.0; swapped=False; next_light=light_interval_mm if light else None
    for raw in lines:
        clean=raw.split(";",1)[0].strip()
        x=_axis(clean,"X"); y=_axis(clean,"Y"); z=_axis(clean,"Z"); e=_axis(clean,"E")
        if x is not None: cx=x
        if y is not None: cy=y
        if z is not None:
            cz=z
            if material_swap and not swapped and cz >= target:
                swapped=True
                out += ["; 4D MATERIAL BOUNDARY REACHED\n","PAUSE\n",
                        "; OPERATOR: perform validated material swap, then resume manually.\n"]
            if light and cz >= next_light:
                while cz >= next_light: next_light += light_interval_mm
                out += ["; 4D LIGHT EXPOSURE CHECKPOINT\n","PAUSE\n",
                        "; OPERATOR: perform validated external light treatment, then resume manually.\n"]
        if thermal and MOVE_RE.match(clean) and e is not None and (x is not None or y is not None) and cz > 0.4:
            gradient=(math.sin(cx*0.05)+math.cos(cy*0.05)+2.0)/4.0
            feed=int(thermal_base+gradient*thermal_boost)
            body,*comment=raw.rstrip("\n").split(";",1)
            body=re.sub(r"F-?\d+(?:\.\d+)?",f"F{feed}",body,flags=re.I) if re.search(r"F-?\d+(?:\.\d+)?",body,re.I) else body.rstrip()+f" F{feed}"
            suffix=(" ;"+comment[0]) if comment else ""
            out.append(body+suffix+" ; UNG-4D thermal-stress\n")
        else: out.append(raw if raw.endswith("\n") else raw+"\n")
    if material_swap and not swapped:
        raise Missing4DMetadataError("4D_TRANSITION_NOT_REACHED: requested transition height is above the generated toolpath")
    return "".join(out)

def main(argv=None):
    p=argparse.ArgumentParser(description="UNG-CAD 4D G-code post-processor")
    p.add_argument("input"); p.add_argument("output",nargs="?")
    p.add_argument("--thermal",action="store_true"); p.add_argument("--material-swap",action="store_true")
    p.add_argument("--geometry-driven",action="store_true"); p.add_argument("--transition-height-mm",type=float)
    p.add_argument("--light",action="store_true"); p.add_argument("--light-interval-mm",type=float)
    a=p.parse_args(argv); src=Path(a.input); dst=Path(a.output) if a.output else src
    try:
        result=compile_ad5m_4d(src.read_text(encoding="utf-8"),thermal=a.thermal,material_swap=a.material_swap,
          transition_height_mm=a.transition_height_mm,geometry_driven=a.geometry_driven,light=a.light,light_interval_mm=a.light_interval_mm)
        dst.write_text(result,encoding="utf-8"); print(f"[SUCCESS] wrote {dst}"); return 0
    except Missing4DMetadataError as e:
        print(f"[FAIL-CLOSED] {e}"); return 2

if __name__=="__main__": raise SystemExit(main())
