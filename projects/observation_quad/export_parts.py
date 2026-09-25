"""Export Modular V2 parts with OpenSCAD.

Usage:
  python export_parts.py
Requires OpenSCAD on the manufacturing worker.
"""
from pathlib import Path
import shutil, subprocess, sys

root=Path(__file__).resolve().parent
src=root/"modular_v2.scad"
out=root/"exports"
out.mkdir(exist_ok=True)
openscad=shutil.which("openscad")
if not openscad:
    raise SystemExit("OpenSCAD is required on the manufacturing worker")

parts={"center_plate":1,"arm":2,"guard":3}
for name,n in parts.items():
    target=out/f"{name}.stl"
    cmd=[openscad,"-o",str(target),"-D",f"part={n}",str(src)]
    p=subprocess.run(cmd,text=True,capture_output=True)
    log=(p.stdout or "")+(p.stderr or "")
    if p.returncode:
        print(log,file=sys.stderr); raise SystemExit(p.returncode)
    bad=[line for line in log.splitlines() if "WARNING" in line.upper() or "ERROR" in line.upper()]
    if bad:
        print("\n".join(bad),file=sys.stderr); raise SystemExit(2)
    print(target)
