"""Deterministic mesh validation for UNG-CAD.

This module keeps manufacturability checks separate from geometry generation.
Watertightness is advisory by default and can be promoted to a hard gate per
workflow/profile.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Iterable, Mapping, Sequence, Tuple

Point = Tuple[float, float, float]
Triangle = Tuple[Point, Point, Point]


@dataclass(frozen=True)
class MeshValidationReport:
    triangle_count: int
    vertex_count: int
    degenerate_faces: int
    boundary_edges: int
    nonmanifold_edges: int
    inconsistent_winding_edges: int
    connected_components: int
    finite: bool
    watertight: bool
    valid: bool
    bbox_min: Point | None
    bbox_max: Point | None
    dimensions: Point | None
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self):
        return asdict(self)


def _point(p) -> Point:
    if isinstance(p, Mapping):
        v = (float(p["x"]), float(p["y"]), float(p["z"]))
    else:
        if len(p) != 3:
            raise ValueError("Each point must contain exactly three coordinates.")
        v = (float(p[0]), float(p[1]), float(p[2]))
    return v


def _triangle(t) -> Triangle:
    if len(t) != 3:
        raise ValueError("Each triangle must contain exactly three vertices.")
    return (_point(t[0]), _point(t[1]), _point(t[2]))


def _finite(p: Point) -> bool:
    return all(math.isfinite(v) for v in p)


def _cross(a: Point, b: Point, c: Point) -> Point:
    ab = (b[0]-a[0], b[1]-a[1], b[2]-a[2])
    ac = (c[0]-a[0], c[1]-a[1], c[2]-a[2])
    return (
        ab[1]*ac[2]-ab[2]*ac[1],
        ab[2]*ac[0]-ab[0]*ac[2],
        ab[0]*ac[1]-ab[1]*ac[0],
    )


def _norm(v: Point) -> float:
    return math.sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2])


def _q(p: Point, tolerance: float) -> tuple[int, int, int]:
    return tuple(int(round(v/tolerance)) for v in p)


def validate_triangle_mesh(
    triangles: Iterable[Sequence],
    *,
    tolerance: float = 1e-9,
    require_watertight: bool = False,
) -> MeshValidationReport:
    """Validate triangle topology without changing the source mesh.

    Hard errors:
      * malformed/non-finite input
      * zero-area faces
      * non-manifold edges
      * disconnected empty result

    Boundary edges are warnings unless require_watertight=True.
    Winding disagreements are warnings because some imported meshes remain
    printable after slicer-side repair.
    """
    if tolerance <= 0:
        raise ValueError("tolerance must be positive")

    tris = [_triangle(t) for t in triangles]
    errors: list[str] = []
    warnings: list[str] = []

    if not tris:
        return MeshValidationReport(
            0, 0, 0, 0, 0, 0, 0, True, False, False,
            None, None, None, ("Mesh contains no triangles.",), ()
        )

    all_points = [p for t in tris for p in t]
    finite = all(_finite(p) for p in all_points)
    if not finite:
        errors.append("Mesh contains NaN or infinite coordinates.")

    q_to_point = {}
    faces = []
    degenerate = 0
    for t in tris:
        ids = tuple(_q(p, tolerance) for p in t)
        for k, p in zip(ids, t):
            q_to_point.setdefault(k, p)
        if len(set(ids)) < 3 or _norm(_cross(*t)) <= tolerance:
            degenerate += 1
        faces.append(ids)

    if degenerate:
        errors.append(f"Mesh contains {degenerate} degenerate triangle(s).")

    edge_uses: dict[tuple, list[tuple]] = {}
    face_neighbors = [set() for _ in faces]
    edge_to_faces: dict[tuple, list[int]] = {}
    for fi, face in enumerate(faces):
        directed = ((face[0], face[1]), (face[1], face[2]), (face[2], face[0]))
        for a, b in directed:
            key = tuple(sorted((a, b)))
            edge_uses.setdefault(key, []).append((a, b))
            edge_to_faces.setdefault(key, []).append(fi)

    boundary = sum(1 for uses in edge_uses.values() if len(uses) == 1)
    nonmanifold = sum(1 for uses in edge_uses.values() if len(uses) > 2)
    inconsistent = 0
    for uses in edge_uses.values():
        if len(uses) == 2 and uses[0] == uses[1]:
            inconsistent += 1

    if nonmanifold:
        errors.append(f"Mesh contains {nonmanifold} non-manifold edge(s).")
    if boundary:
        msg = f"Mesh contains {boundary} boundary edge(s)."
        (errors if require_watertight else warnings).append(msg)
    if inconsistent:
        warnings.append(f"Mesh contains {inconsistent} shared edge(s) with inconsistent winding.")

    for linked in edge_to_faces.values():
        for i in linked:
            face_neighbors[i].update(j for j in linked if j != i)

    seen = set()
    components = 0
    for start in range(len(faces)):
        if start in seen:
            continue
        components += 1
        stack = [start]
        seen.add(start)
        while stack:
            cur = stack.pop()
            for nxt in face_neighbors[cur]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
    if components > 1:
        warnings.append(f"Mesh contains {components} disconnected components.")

    xs = [p[0] for p in q_to_point.values()]
    ys = [p[1] for p in q_to_point.values()]
    zs = [p[2] for p in q_to_point.values()]
    bmin = (min(xs), min(ys), min(zs))
    bmax = (max(xs), max(ys), max(zs))
    dims = tuple(bmax[i]-bmin[i] for i in range(3))

    watertight = boundary == 0 and nonmanifold == 0
    valid = finite and degenerate == 0 and nonmanifold == 0 and (watertight or not require_watertight)

    return MeshValidationReport(
        triangle_count=len(tris),
        vertex_count=len(q_to_point),
        degenerate_faces=degenerate,
        boundary_edges=boundary,
        nonmanifold_edges=nonmanifold,
        inconsistent_winding_edges=inconsistent,
        connected_components=components,
        finite=finite,
        watertight=watertight,
        valid=valid,
        bbox_min=bmin,
        bbox_max=bmax,
        dimensions=dims,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def bed_fit(
    dimensions: Sequence[float],
    bed_size: Sequence[float],
    *,
    clearance: float = 0.0,
) -> dict:
    """Check axis-aligned fit against a machine bed/build volume."""
    if len(dimensions) != 3 or len(bed_size) != 3:
        raise ValueError("dimensions and bed_size must each contain 3 values")
    if clearance < 0:
        raise ValueError("clearance cannot be negative")
    part = tuple(float(v) for v in dimensions)
    bed = tuple(float(v) for v in bed_size)
    if any(v < 0 for v in part) or any(v <= 0 for v in bed):
        raise ValueError("part dimensions must be nonnegative and bed dimensions positive")
    available = tuple(v - 2*clearance for v in bed)
    fits = all(part[i] <= available[i] for i in range(3))
    return {
        "fits": fits,
        "part_dimensions": part,
        "bed_size": bed,
        "clearance": clearance,
        "available": available,
        "overflow": tuple(max(0.0, part[i]-available[i]) for i in range(3)),
    }
