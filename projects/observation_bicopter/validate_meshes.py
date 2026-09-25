"""Compile and validate Simple Bicopter V2 meshes."""
from pathlib import Path
import shutil, subprocess, sys

root=Path(__file__).resolve().parent
source=root/"simple_v2.scad"
out=root/"exports_v2"
out.mkdir(exist_ok=True)
exe=shutil.which("openscad")
if not exe:
    raise SystemExit("OpenSCAD unavailable")

parts={"body":1,"arm":2,"guard":3}
for name,n in parts.items():
    target=out/f"{name}.stl"
    p=subprocess.run([exe,"-o",str(target),"-D",f"part={n}",str(source)],
                     text=True,capture_output=True)
    log=(p.stdout or "")+(p.stderr or "")
    if p.returncode:
        print(log,file=sys.stderr); raise SystemExit(p.returncode)
    bad=[x for x in log.splitlines()
         if "WARNING" in x.upper() or "ERROR" in x.upper() or "CGAL ERROR" in x.upper()]
    if bad:
        print("\n".join(bad),file=sys.stderr); raise SystemExit(2)
    if not target.exists() or target.stat().st_size < 100:
        raise SystemExit(f"invalid export:{name}")
    print(f"PASS {name}: {target.stat().st_size} bytes")
print("SIMPLE_BICOPTER_V2_MESH_EXPORT_PASS")
