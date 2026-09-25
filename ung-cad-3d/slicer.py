import io, math
import numpy as np
import trimesh
from shapely.geometry import Polygon, MultiPolygon, LineString, MultiLineString
from shapely.ops import unary_union

def _loop_points(coords, z):
    pts=[]
    for p in coords:
        pts.append((float(p[0]), float(p[1]), z))
    if len(pts)>1 and pts[0] == pts[-1]:
        pts.pop()
    return pts

def _emit_loop(lines, pts, xoff, yoff, z, e_state, feed=1800):
    if len(pts)<3: return e_state
    px,py,_=pts[0]
    lines.append(f"G0 X{px+xoff:.3f} Y{py+yoff:.3f}")
    for x,y,_ in pts[1:]+[pts[0]]:
        dist=math.hypot(x-px,y-py)
        e_state += dist*0.045
        lines.append(f"G1 X{x+xoff:.3f} Y{y+yoff:.3f} E{e_state:.5f} F{feed}")
        px,py=x,y
    return e_state

def _wall_polygons(poly: Polygon, nozzle: float, wall_count: int):
    shells=[]
    for i in range(max(1,wall_count)):
        inset=nozzle*(i+0.5)
        shrunk=poly.buffer(-inset, join_style=2)
        if shrunk.is_empty:
            break
        shells.append(shrunk)
    return shells

def _emit_wall_shell(lines, shell, xoff, yoff, z, e_state):
    geoms=shell.geoms if isinstance(shell,MultiPolygon) else [shell]
    for g in geoms:
        if g.is_empty or not isinstance(g,Polygon): continue
        e_state=_emit_loop(lines,_loop_points(np.asarray(g.exterior.coords),z),xoff,yoff,z,e_state)
        for ring in g.interiors:
            e_state=_emit_loop(lines,_loop_points(np.asarray(ring.coords),z),xoff,yoff,z,e_state)
    return e_state


def _infill_lines(poly, spacing, angle_deg):
    """Rasterize polygon interior into clipped parallel line segments."""
    if poly.is_empty or spacing<=0: return []
    minx,miny,maxx,maxy=poly.bounds
    diag=math.hypot(maxx-minx,maxy-miny)+2*spacing
    cx,cy=(minx+maxx)/2,(miny+maxy)/2
    theta=math.radians(angle_deg); dx,dy=math.cos(theta),math.sin(theta); nx,ny=-dy,dx
    n_lines=int(diag/spacing)+2; segments=[]
    for i in range(-n_lines,n_lines+1):
        off=i*spacing; ox,oy=cx+nx*off,cy+ny*off
        try: clipped=LineString([(ox-dx*diag,oy-dy*diag),(ox+dx*diag,oy+dy*diag)]).intersection(poly)
        except Exception: continue
        if clipped.is_empty: continue
        if isinstance(clipped,LineString):
            if clipped.length>1e-6: segments.append(clipped)
        elif isinstance(clipped,MultiLineString):
            segments.extend(g for g in clipped.geoms if g.length>1e-6)
    return segments

def _emit_infill(lines, segments, xoff, yoff, e_state, feed=2400):
    for seg in segments:
        (x0,y0),(x1,y1)=seg.coords[0],seg.coords[-1]
        lines.append(f"G0 X{x0+xoff:.3f} Y{y0+yoff:.3f}")
        e_state+=math.hypot(x1-x0,y1-y0)*0.045
        lines.append(f"G1 X{x1+xoff:.3f} Y{y1+yoff:.3f} E{e_state:.5f} F{feed}")
    return e_state

def _compute_support_polygons(valid_layers, nozzle):
    n=len(valid_layers)
    layer_union=[unary_union([p for p in polys if p.is_valid and p.area>0]) if polys else None for _,polys in valid_layers]
    cumulative=None; new_overhang=[None]*n
    for i,u in enumerate(layer_union):
        if u is None: continue
        if cumulative is None: cumulative=u
        else:
            diff=u.difference(cumulative)
            if not diff.is_empty and diff.area>1.0: new_overhang[i]=diff
            cumulative=cumulative.union(u).simplify(0.05,preserve_topology=True).buffer(0)
    support_needed_above=[None]*n; acc=None
    for i in range(n-1,-1,-1):
        support_needed_above[i]=acc
        if new_overhang[i] is not None:
            acc=new_overhang[i] if acc is None else acc.union(new_overhang[i])
            acc=acc.simplify(0.05,preserve_topology=True).buffer(0)
    out=[None]*n
    for i,needed in enumerate(support_needed_above):
        if needed is None or needed.is_empty: continue
        model=layer_union[i]
        avail=needed.difference(model.buffer(nozzle*0.3)) if model is not None else needed
        if not avail.is_empty and avail.area>1.0: out[i]=avail
    return out

MATERIAL_TEMPS={
    "PLA":{"nozzle":200,"bed":55},
    "PETG":{"nozzle":235,"bed":80},
    "ABS":{"nozzle":245,"bed":100},
    "TPU":{"nozzle":225,"bed":50},
}

def slice_stl(data: bytes, filename: str, layer_height=0.20, nozzle=0.40, wall_count=2, bed=220,
              quality="balanced", material="PLA", filament_color="", supports="auto", copies=1, infill_density=0.15, top_bottom_layers=3, **kwargs):
    temps=MATERIAL_TEMPS.get(material.upper(), MATERIAL_TEMPS["PLA"])
    mesh=trimesh.load_mesh(io.BytesIO(data), file_type='stl')
    if not isinstance(mesh,trimesh.Trimesh):
        raise ValueError("STL did not produce a mesh")
    repaired=False
    if not mesh.is_watertight:
        repaired=True
        mesh.remove_unreferenced_vertices()
        mesh.merge_vertices()
        trimesh.repair.fix_normals(mesh, multibody=True)
        trimesh.repair.fix_winding(mesh)
        trimesh.repair.fill_holes(mesh)
        mesh.remove_unreferenced_vertices()
        mesh.merge_vertices()
    open_shell = not mesh.is_watertight
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
    total_h=float(zmax-zmin)
    bottom_thresh=top_bottom_layers*layer_height
    top_thresh=total_h-top_bottom_layers*layer_height
    valid_layers=[(z,path.polygons_full) for z,path in zip(heights,paths) if path is not None and len(path.entities)>0 and path.polygons_full]
    supports_enabled=str(supports).lower() not in ("off","none","false","0")
    support_by_layer=_compute_support_polygons(valid_layers,nozzle) if supports_enabled else [None]*len(valid_layers)
    lines=[
        "; UNG-CAD generated G-code",
        f"; Model: {filename}",
        "; Printer: FlashForge Adventurer 5M",
        f"; Profile: {nozzle}mm nozzle / {layer_height}mm layers / {wall_count} walls / {infill_density*100:.0f}% infill / {material}",
        f"; Filament color: {filament_color or 'not specified'}",
        f"; Supports: {'enabled' if supports_enabled else 'disabled'}",
        "; NOTE: verify material, bed/nozzle temperature and first layer before production use",
        "G90","M82","M107","G28",
        f"M140 S{temps['bed']}",f"M104 S{temps['nozzle']}",f"M190 S{temps['bed']}",f"M109 S{temps['nozzle']}",
        "G92 E0","G1 Z0.20 F600",
        "G1 X10 Y10 F6000",
        "G1 X10 Y100 E15 F600","G1 X10.4 Y100 F600","G1 X10.4 Y10 E30 F600",
        "G92 E0",
        "G1 Z0.20 F600"
    ]
    e=0.0
    layer_count=0
    support_layer_count=0
    for idx,(z,polys) in enumerate(valid_layers):
        layer_count+=1
        if layer_count==3: lines.append("M106 S180")
        lines.append(f";LAYER:{layer_count}")
        lines.append(f"G1 Z{z:.3f} F600")
        is_solid_layer=z<=bottom_thresh or z>=top_thresh
        infill_angle=45 if layer_count%2==0 else 135
        for poly in polys:
            if not poly.is_valid or poly.area<=0: continue
            shells=_wall_polygons(poly,nozzle,wall_count)
            for shell in shells: e=_emit_wall_shell(lines,shell,xoff,yoff,z,e)
            inner=shells[-1] if shells else poly.buffer(-nozzle*0.5,join_style=2)
            inner_geoms=inner.geoms if isinstance(inner,MultiPolygon) else [inner]
            for g in inner_geoms:
                if g.is_empty or not isinstance(g,Polygon): continue
                if is_solid_layer:
                    for ang in (infill_angle-45,infill_angle+45):
                        e=_emit_infill(lines,_infill_lines(g,nozzle*0.95,ang),xoff,yoff,e)
                elif infill_density>0:
                    e=_emit_infill(lines,_infill_lines(g,nozzle/max(infill_density,0.02),infill_angle),xoff,yoff,e)
        support_poly=support_by_layer[idx]
        if support_poly is not None and not support_poly.is_empty:
            geoms=support_poly.geoms if isinstance(support_poly,MultiPolygon) else [support_poly]
            emitted=False
            for g in geoms:
                if g.is_empty or not isinstance(g,Polygon): continue
                segs=_infill_lines(g,nozzle/0.15,0)
                if segs:
                    if not emitted: lines.append(";SUPPORT"); emitted=True
                    e=_emit_infill(lines,segs,xoff,yoff,e,feed=1800)
            if emitted: support_layer_count+=1
    lines += [
        "G92 E0","G1 E-1.0000 F1800","G1 Z5.000 F600","G1 X0 Y110 F6000",
        "M104 S0","M140 S0","M107","M84",";END"
    ]
    if layer_count==0:
        raise ValueError("No printable cross-sections were generated")
    payload=("\n".join(lines)+"\n").encode()
    return payload, {"layers":layer_count,"height_mm":round(float(zmax-zmin),2),
                     "size_xy_mm":[round(float(ext[0]),2),round(float(ext[1]),2)],
                     "wall_count":wall_count,"infill_density":infill_density,"top_bottom_layers":top_bottom_layers,"bytes":len(payload),
                     "material":material,"filament_color":filament_color,"supports_enabled":supports_enabled,"support_layer_count":support_layer_count,
                     "mesh_repaired":repaired,"open_shell_sliced":open_shell}
