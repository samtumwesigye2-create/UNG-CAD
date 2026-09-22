import io
import math
import numpy as np
import trimesh

def _loop_points(coords, z):
    pts=[(float(p[0]), float(p[1]), z) for p in coords]
    if len(pts)>1 and pts[0] == pts[-1]:
        pts.pop()
    return pts

def _emit_loop(lines, pts, xoff, yoff, z, e_state, feed=1800):
    if len(pts)<3:
        return e_state
    x0,y0,_=pts[0]
    lines.append(f"G0 X{x0+xoff:.3f} Y{y0+yoff:.3f}")
    px,py,_=pts[0]
    for x,y,_ in pts[1:]+[pts[0]]:
        dist=math.hypot(x-px,y-py)
        e_state += dist*0.045
        lines.append(f"G1 X{x+xoff:.3f} Y{y+yoff:.3f} E{e_state:.5f} F{feed}")
        px,py=x,y
    return e_state

def _emit_prime_sequence(lines):
    """Prime and wipe the nozzle before layer 1.

    The slicer uses absolute extrusion (M82), so reset E before and after the
    purge line. This guarantees the first model extrusion starts from E0.
    """
    lines += [
        "; UNG-CAD nozzle prime",
        "G92 E0",
        "G1 Z0.28 F600",
        "G1 X10 Y10 F6000",
        "G1 X80 Y10 E8.0000 F600",
        "G1 X80 Y10.4 F1800",
        "G1 X10 Y10.4 E9.0000 F600",
        "G92 E0",
        "G1 Z0.20 F600",
    ]

def slice_stl(data: bytes, filename: str, layer_height=0.20, nozzle=0.40, wall_count=2, bed=220):
    mesh=trimesh.load_mesh(io.BytesIO(data), file_type="stl")
    if not isinstance(mesh,trimesh.Trimesh):
        raise ValueError("STL did not produce a mesh")
    if not mesh.is_watertight:
        raise ValueError("STL is not watertight")
    ext=mesh.extents
    if max(ext[:2]) > bed-10:
        raise ValueError(f"Model XY footprint {max(ext[:2]):.1f} mm exceeds Adventurer 5M 220 mm bed")
    zmin,zmax=mesh.bounds[:,2]
    if zmax-zmin <= 0:
        raise ValueError("Model has zero height")
    xmin,ymin=mesh.bounds[0][:2]; xmax,ymax=mesh.bounds[1][:2]
    xoff=(bed-(xmin+xmax))/2
    yoff=(bed-(ymin+ymax))/2
    first=layer_height/2
    heights=np.arange(first, float(zmax-zmin)+1e-6, layer_height)
    paths=mesh.section_multiplane(plane_origin=[0,0,zmin], plane_normal=[0,0,1], heights=heights)
    lines=[
        "; UNG-CAD generated G-code", f"; Model: {filename}",
        "; Printer: FlashForge Adventurer 5M",
        "; Profile: conservative 0.4mm nozzle / 0.20mm layers / PLA",
        "; NOTE: verify material, bed/nozzle temperature and first layer before production use",
        "G90","M82","M107","G28","M140 S55","M104 S200","M190 S55","M109 S200",
    ]
    _emit_prime_sequence(lines)
    e=0.0; layer_count=0
    for z,path in zip(heights,paths):
        if path is None or len(path.entities)==0:
            continue
        polys=path.polygons_full
        if not polys:
            continue
        layer_count+=1
        lines.append(f";LAYER:{layer_count}")
        lines.append(f"G1 Z{z:.3f} F600")
        for poly in polys:
            e=_emit_loop(lines,_loop_points(np.asarray(poly.exterior.coords),z),xoff,yoff,z,e)
            for ring in poly.interiors:
                e=_emit_loop(lines,_loop_points(np.asarray(ring.coords),z),xoff,yoff,z,e)
    lines += ["G1 E-1.0000 F1800","G1 Z5.000 F600","M104 S0","M140 S0","M107","M84"]
    if layer_count==0:
        raise ValueError("No printable cross-sections were produced")
    raw=("\n".join(lines)+"\n").encode()
    stats={"layers":layer_count,"height_mm":round(float(zmax-zmin),3),
           "size_xy_mm":[round(float(ext[0]),3),round(float(ext[1]),3)],"bytes":len(raw)}
    return raw,stats
