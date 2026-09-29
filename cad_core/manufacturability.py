"""Advisory additive-manufacturing analysis for UNG-CAD.

These checks are deterministic mesh-level signals for FDM preflight. They do
not pretend to replace exact B-rep wall/gap analysis; metrics that are mesh
proxies are explicitly named as such.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Iterable, Mapping, Sequence, Tuple

Point = Tuple[float, float, float]
Triangle = Tuple[Point, Point, Point]


def _point(p) -> Point:
    if isinstance(p, Mapping):
        return (float(p["x"]), float(p["y"]), float(p["z"]))
    return (float(p[0]), float(p[1]), float(p[2]))


def _triangle(t) -> Triangle:
    if len(t) != 3:
        raise ValueError("Each triangle must contain exactly three vertices.")
    return (_point(t[0]), _point(t[1]), _point(t[2]))


def _sub(a:Point,b:Point)->Point:
    return (a[0]-b[0],a[1]-b[1],a[2]-b[2])


def _cross(a:Point,b:Point)->Point:
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])


def _norm(v:Point)->float:
    return math.sqrt(v[0]*v[0]+v[1]*v[1]+v[2]*v[2])


def _area_normal(t:Triangle):
    c=_cross(_sub(t[1],t[0]),_sub(t[2],t[0]))
    n=_norm(c)
    if n<=1e-15:
        return 0.0,(0.0,0.0,0.0)
    return n*.5,(c[0]/n,c[1]/n,c[2]/n)


def _edge_lengths(t:Triangle):
    return (_norm(_sub(t[0],t[1])),_norm(_sub(t[1],t[2])),_norm(_sub(t[2],t[0])))


@dataclass(frozen=True)
class PrintabilityReport:
    triangle_count:int
    surface_area_mm2:float
    min_mesh_edge_mm:float|None
    tiny_mesh_edges:int
    tiny_feature_face_count:int
    overhang_face_count:int
    overhang_area_mm2:float
    overhang_area_percent:float
    bridge_candidate_face_count:int
    bridge_candidate_area_mm2:float
    bed_contact_face_count:int
    bed_contact_area_mm2:float
    max_height_mm:float|None
    nozzle_diameter_mm:float
    layer_height_mm:float
    overhang_limit_deg:float
    minimum_feature_mm:float
    warnings:tuple[str,...]
    notes:tuple[str,...]

    def to_dict(self):
        return asdict(self)


def analyze_fdm_printability(
    triangles:Iterable[Sequence],
    *,
    nozzle_diameter_mm:float=0.4,
    layer_height_mm:float=0.2,
    overhang_limit_deg:float=45.0,
    minimum_feature_mm:float|None=None,
    bed_z_mm:float|None=None,
    bed_tolerance_mm:float=0.05,
    bridge_horizontal_deg:float=12.0,
)->PrintabilityReport:
    """Return advisory FDM printability signals.

    overhang_limit_deg is the minimum downward-facing surface angle measured
    up from the build plane. A downward horizontal underside is 0 degrees and
    a vertical wall is 90 degrees.

    min_mesh_edge_mm is a tessellation/feature proxy, not an exact wall
    thickness measurement. Exact wall and hole clearance belong to the B-rep
    or voxel-analysis stage.
    """
    if nozzle_diameter_mm<=0 or layer_height_mm<=0:
        raise ValueError("nozzle_diameter_mm and layer_height_mm must be positive")
    if not (0<overhang_limit_deg<90):
        raise ValueError("overhang_limit_deg must be between 0 and 90 degrees")
    if bed_tolerance_mm<0:
        raise ValueError("bed_tolerance_mm cannot be negative")
    min_feature=float(minimum_feature_mm if minimum_feature_mm is not None else nozzle_diameter_mm)
    if min_feature<=0:
        raise ValueError("minimum_feature_mm must be positive")

    tris=[_triangle(t) for t in triangles]
    if not tris:
        return PrintabilityReport(0,0.0,None,0,0,0,0.0,0.0,0,0.0,0,0.0,None,
            nozzle_diameter_mm,layer_height_mm,overhang_limit_deg,min_feature,
            ("No triangles available for printability analysis.",),
            ("Exact wall/hole checks require solid/B-rep or voxel analysis.",))

    zs=[p[2] for t in tris for p in t]
    bed=min(zs) if bed_z_mm is None else float(bed_z_mm)
    max_height=max(zs)-bed
    total_area=0.0; min_edge=None; tiny_edges=0; tiny_faces=0
    overhang_faces=0; overhang_area=0.0
    bridge_faces=0; bridge_area=0.0
    bed_faces=0; bed_area=0.0

    for t in tris:
        area,n=_area_normal(t)
        if area<=0:
            continue
        total_area+=area
        edges=_edge_lengths(t)
        local_min=min(edges)
        min_edge=local_min if min_edge is None else min(min_edge,local_min)
        tiny_edges+=sum(1 for e in edges if e<min_feature)
        if local_min<min_feature:
            tiny_faces+=1

        on_bed=all(abs(p[2]-bed)<=bed_tolerance_mm for p in t)
        if on_bed:
            bed_faces+=1; bed_area+=area

        if n[2] < 0:
            angle_from_plane=math.degrees(math.acos(max(-1.0,min(1.0,-n[2]))))
            zc=sum(p[2] for p in t)/3.0
            if angle_from_plane < overhang_limit_deg and zc>bed+bed_tolerance_mm:
                overhang_faces+=1; overhang_area+=area
            if angle_from_plane <= bridge_horizontal_deg and zc>bed+max(layer_height_mm,bed_tolerance_mm):
                bridge_faces+=1; bridge_area+=area

    warnings=[]; notes=[]
    pct=(100.0*overhang_area/total_area) if total_area else 0.0
    if overhang_faces:
        warnings.append(f"{overhang_faces} downward face(s) exceed the {overhang_limit_deg:g}° overhang limit.")
    if bridge_faces:
        warnings.append(f"{bridge_faces} near-horizontal underside face(s) are bridge/support candidates.")
    if min_edge is not None and min_edge<min_feature:
        warnings.append(f"Mesh contains edges below the {min_feature:g} mm minimum-feature proxy.")
    if bed_area<=0:
        warnings.append("No planar triangle was detected at the lowest build Z; bed contact may be point/edge-only or tilted.")
    notes.append("Minimum mesh edge is a tessellation/feature proxy, not exact wall thickness.")
    notes.append("Exact wall thickness, enclosed hole diameter and inter-part clearance require solid/B-rep or voxel analysis.")

    return PrintabilityReport(
        triangle_count=len(tris),surface_area_mm2=total_area,min_mesh_edge_mm=min_edge,
        tiny_mesh_edges=tiny_edges,tiny_feature_face_count=tiny_faces,
        overhang_face_count=overhang_faces,overhang_area_mm2=overhang_area,
        overhang_area_percent=pct,bridge_candidate_face_count=bridge_faces,
        bridge_candidate_area_mm2=bridge_area,bed_contact_face_count=bed_faces,
        bed_contact_area_mm2=bed_area,max_height_mm=max_height,
        nozzle_diameter_mm=nozzle_diameter_mm,layer_height_mm=layer_height_mm,
        overhang_limit_deg=overhang_limit_deg,minimum_feature_mm=min_feature,
        warnings=tuple(warnings),notes=tuple(notes),
    )
