"""G-code parsing, validation and preview statistics."""
import re, math
MOVE=re.compile(r"\bG([01])\b",re.I)
AXIS=re.compile(r"\b([XYZEFS])(-?\d+(?:\.\d+)?)",re.I)
FORBIDDEN=("M500","M502","M997","M999")

def analyze(text):
    x=y=z=e=0.0; distance=0.0; moves=0; layers=0; warnings=[]
    for no,raw in enumerate(text.splitlines(),1):
        line=raw.split(";",1)[0].strip()
        if not line: 
            if raw.lstrip().upper().startswith(";LAYER:"): layers+=1
            continue
        up=line.upper()
        if any(cmd in up.split() for cmd in FORBIDDEN): warnings.append(f"line {no}: restricted command")
        if MOVE.search(up):
            vals={k.upper():float(v) for k,v in AXIS.findall(up)}
            nx,ny,nz=vals.get("X",x),vals.get("Y",y),vals.get("Z",z)
            distance+=math.dist((x,y,z),(nx,ny,nz)); x,y,z=nx,ny,nz
            e=vals.get("E",e); moves+=1
    return {"moves":moves,"layers":layers,"travel_mm":round(distance,2),"final_position":{"x":x,"y":y,"z":z,"e":e},"warnings":warnings,"valid":not warnings}
