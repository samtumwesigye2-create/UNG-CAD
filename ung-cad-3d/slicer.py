"""
UNG-CAD 3D slicer for the FlashForge Adventurer 5M (AD5M).

Pipeline (slice_model):
  1. validate_and_prepare  - load the STL, report/repair problems on a COPY
                             (never silently), analyse bodies (separate parts,
                             sealed internal cavities, parts nested in cavities),
                             overhangs, units, bed fit. Errors block slicing.
  2. plan_layers           - cut the mesh at the MIDDLE of every layer, print it
                             with the nozzle at the TOP of the layer; walls,
                             infill, solid top/bottom skin, skirt; thin-wall /
                             tiny-feature / first-layer-contact warnings.
  3. G-code emission       - volumetric extrusion for 1.75 mm filament,
                             retraction, fan, PLA/PETG profiles.
  4. self-checks           - dimensions (no scaling: outer wall centres sit
                             line_width/2 inside the true outline) and a G-code
                             audit (bed bounds, Z order, no extrusion on travel,
                             monotonic E, temperatures first, every layer
                             extrudes). G-code that fails is never returned.

Coordinates: the AD5M origin is the CENTRE of the bed (FlashForge, OrcaSlicer
PR #2450), so X/Y run from -110 to +110. Parts are centred on X0 Y0.

Inside/outside is decided by nesting (even-odd, trimesh polygons_full), so a
sealed internal cavity stays hollow and a body inside that cavity prints solid.

It is not PrusaSlicer/OrcaSlicer quality (no gap fill, no bridging detection,
no seam alignment, no supports). Always check the first layer.
"""
import io
import math
import re

import numpy as np
import shapely
import trimesh
from shapely import affinity
from shapely.geometry import GeometryCollection, LineString, MultiLineString, MultiPolygon, Polygon
from shapely.ops import unary_union


# ---------- Printer / material constants ----------

FILAMENT_DIAMETER = 1.75
FILAMENT_AREA = math.pi * (FILAMENT_DIAMETER / 2) ** 2   # mm^2

BED_SIZE = 220.0          # AD5M build plate is 220 x 220 mm
BED_HALF = BED_SIZE / 2   # origin is the bed centre -> -110 .. +110
MAX_Z = 220.0             # AD5M max build height
BED_MARGIN = 5.0          # keep parts at least this far from the bed edge

MATERIALS = {
    "PLA": {"nozzle_temp": 210, "bed_temp": 55, "fan": 255, "density": 1.24},
    "PETG": {"nozzle_temp": 235, "bed_temp": 80, "fan": 102, "density": 1.27},   # fan ~40 %
}

FEED_TRAVEL = 9000        # mm/min
FEED_FIRST_LAYER = 1200   # mm/min, every extrusion on layer 1
FEED_OUTER_WALL = 2400
FEED_INNER_WALL = 3000
FEED_SOLID = 3000
FEED_SPARSE = 4200
FEED_Z = 600
RETRACT_LENGTH = 0.8      # mm, AD5M is direct drive
RETRACT_FEED = 2100       # mm/min = 35 mm/s
RETRACT_MIN_TRAVEL = 2.0  # only retract on travels longer than this (mm)
FAN_START_LAYER = 3
SKIRT_DISTANCE = 3.0      # mm between the part and the skirt loop
PURGE_Y = -105.0          # purge line near the front edge
PURGE_X = (-90.0, 90.0)
PURGE_HEIGHT = 0.3
PURGE_WIDTH = 0.8
PARK_XY = (-100.0, 100.0)

OVERHANG_LIMIT_DEG = 50.0
DIMENSION_TOLERANCE = 0.05
MAX_LOCATIONS = 10

PREVIEW_TYPES = {
    "outer_wall": "perimeter",
    "inner_wall": "perimeter",
    "skirt": "perimeter",
    "solid_infill": "solid",
    "sparse_infill": "infill",
}


class SliceValidationError(ValueError):
    """Raised when pre-slice validation finds blocking errors. `.report` has errors + warnings."""

    def __init__(self, report):
        self.report = report
        super().__init__("; ".join(e["message"] for e in report["errors"]) or "Model failed validation")


class GcodeCheckError(ValueError):
    """Raised when generated G-code fails the self-check (it is never returned)."""

    def __init__(self, problems, report=None):
        self.problems = problems
        self.report = report
        super().__init__("G-code self-check failed: " + "; ".join(problems[:5]))


def material_profile(material):
    key = str(material or "PLA").strip().upper()
    if key not in MATERIALS:
        raise ValueError(f"Unknown material '{material}'. Choose one of: {', '.join(MATERIALS)}")
    return key, MATERIALS[key]


def bead_area(line_width, layer_height):
    """Cross-section of an extruded bead: a rectangle with rounded (semicircular) ends."""
    return (line_width - layer_height) * layer_height + math.pi * (layer_height / 2) ** 2


def extrusion_per_mm(line_width, layer_height):
    """Millimetres of 1.75 mm filament per millimetre of toolpath."""
    return bead_area(line_width, layer_height) / FILAMENT_AREA


def new_report():
    return {"errors": [], "warnings": [], "repairs": [], "bodies": [], "checks": {}}


def _warn(report, code, message, **details):
    report["warnings"].append({"code": code, "message": message, **details})


def _error(report, code, message, **details):
    report["errors"].append({"code": code, "message": message, **details})


# ---------- Geometry helpers ----------

def _polygons(geom):
    """Flatten any shapely geometry into a list of non-empty Polygons."""
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, (MultiPolygon, GeometryCollection)):
        out = []
        for g in geom.geoms:
            out.extend(_polygons(g))
        return out
    return []


def _as_multipolygon(geom):
    polys = _polygons(geom)
    return MultiPolygon(polys) if polys else MultiPolygon()


def _rings(geom):
    """All closed rings (exteriors and holes) of a geometry as lists of (x, y)."""
    rings = []
    for poly in _polygons(geom):
        rings.append(list(poly.exterior.coords))
        for interior in poly.interiors:
            rings.append(list(interior.coords))
    return rings


def _line_strings(geom):
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, LineString):
        return [geom]
    if hasattr(geom, "geoms"):
        out = []
        for g in geom.geoms:
            out.extend(_line_strings(g))
        return out
    return []


def _inset(geom, distance):
    """
    Inward offset. Convex corners stay sharp; concave corners get an arc (round join),
    so every point of the offset is exactly `distance` from the outline.
    """
    return geom.buffer(-distance, join_style="round", quad_segs=8)


def _rectilinear_lines(area, spacing, angle_deg, min_length):
    """
    Parallel lines at `angle_deg`, `spacing` apart, clipped to `area`.
    The line grid is anchored at the origin so sparse infill lines up layer to layer.
    Returns a list of ((x0, y0), (x1, y1)) segments.
    """
    if area is None or area.is_empty:
        return []
    rotated = affinity.rotate(area, -angle_deg, origin=(0, 0))
    minx, miny, maxx, maxy = rotated.bounds
    k0 = math.ceil(miny / spacing)
    k1 = math.floor(maxy / spacing)
    if k1 < k0:
        return []
    lines = []
    for k in range(k0, k1 + 1):
        y = k * spacing
        lines.append([(minx - 1.0, y), (maxx + 1.0, y)])
    clipped = rotated.intersection(MultiLineString(lines))
    segments = []
    for ls in _line_strings(clipped):
        if ls.length < min_length:
            continue
        back = affinity.rotate(ls, angle_deg, origin=(0, 0))
        coords = list(back.coords)
        segments.append((coords[0], coords[-1]))
    return segments


def _order_segments(segments, start):
    """Greedy nearest-neighbour ordering (each segment may be reversed) to keep travels short."""
    if not segments:
        return []
    a = np.array([s[0] for s in segments], dtype=float)
    b = np.array([s[1] for s in segments], dtype=float)
    used = np.zeros(len(segments), dtype=bool)
    pos = np.array(start if start is not None else segments[0][0], dtype=float)
    ordered = []
    for _ in range(len(segments)):
        da = np.hypot(*(a - pos).T)
        db = np.hypot(*(b - pos).T)
        da[used] = np.inf
        db[used] = np.inf
        ia = int(np.argmin(da))
        ib = int(np.argmin(db))
        if da[ia] <= db[ib]:
            idx, seg = ia, (tuple(a[ia]), tuple(b[ia]))
        else:
            idx, seg = ib, (tuple(b[ib]), tuple(a[ib]))
        used[idx] = True
        ordered.append(seg)
        pos = np.array(seg[1])
    return ordered


def _ring_from_nearest(ring, pos):
    """Rotate a closed ring so it starts at the vertex nearest to `pos`."""
    pts = list(ring)
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    if pos is not None and len(pts) > 2:
        arr = np.array(pts)
        i = int(np.argmin(np.hypot(arr[:, 0] - pos[0], arr[:, 1] - pos[1])))
        pts = pts[i:] + pts[:i]
    return pts + [pts[0]]


def _compensate_holes(geom, amount):
    """Grow (amount > 0) or shrink (amount < 0) holes only; outer outlines are untouched."""
    if not amount:
        return geom
    out = []
    for poly in _polygons(geom):
        shell = Polygon(poly.exterior)
        holes = [Polygon(r).buffer(amount, join_style="mitre", mitre_limit=10.0) for r in poly.interiors]
        holes = [h for h in holes if not h.is_empty]
        out.append(shell.difference(unary_union(holes)) if holes else shell)
    return _as_multipolygon(unary_union(out))


def _add_location(locations, x, y, z):
    key = (round(x), round(y))
    for loc in locations:
        if (round(loc["x"]), round(loc["y"])) == key:
            loc["z_to"] = round(z, 3)
            return
    if len(locations) < MAX_LOCATIONS:
        locations.append({"x": round(x, 2), "y": round(y, 2), "z_from": round(z, 3), "z_to": round(z, 3)})


# ---------- Validation / preparation ----------

def _body_depths(bodies):
    """Even-odd nesting depth of each body (0 = separate part, odd = cavity, even>0 = solid inside a cavity)."""
    n = len(bodies)
    depths = [0] * n
    if n < 2 or n > 30:
        return depths
    probes = [b.triangles_center[0] for b in bodies]
    for i in range(n):
        for j in range(n):
            if i == j or not bodies[j].is_watertight:
                continue
            bi, bj = bodies[i].bounds, bodies[j].bounds
            if np.any(bi[0] < bj[0] - 1e-6) or np.any(bi[1] > bj[1] + 1e-6):
                continue
            try:
                if bool(bodies[j].contains([probes[i]])[0]):
                    depths[i] += 1
            except Exception:
                pass
    return depths


def validate_and_prepare(data, layer_height=0.20, nozzle=0.40, line_width=None,
                         bed=BED_SIZE, max_z=MAX_Z, margin=BED_MARGIN):
    """
    Load and check an STL. Repairs are attempted on a copy and always reported.
    Returns (placed_mesh, report). Raises SliceValidationError on blocking errors.
    The placed mesh is centred on X0 Y0 with its lowest point on Z0 - never scaled.
    """
    report = new_report()
    lw = float(line_width) if line_width else nozzle * 1.125
    try:
        loaded = trimesh.load_mesh(io.BytesIO(data), file_type="stl")
    except Exception as e:
        _error(report, "unreadable", f"Could not read STL: {e}")
        raise SliceValidationError(report)
    if not isinstance(loaded, trimesh.Trimesh) or len(loaded.faces) == 0:
        _error(report, "empty", "STL did not produce a mesh with triangles")
        raise SliceValidationError(report)
    mesh = loaded.copy()

    # --- degenerate faces ---
    mask = mesh.nondegenerate_faces()
    degenerate = int((~mask).sum())
    report["checks"]["degenerate_faces"] = degenerate
    if degenerate:
        mesh.update_faces(mask)
        mesh.remove_unreferenced_vertices()
        report["repairs"].append(f"Removed {degenerate} degenerate (zero-area) face(s)")

    # --- manifold / watertight ---
    edges = mesh.edges_sorted
    if len(edges):
        _, counts = np.unique(edges, axis=0, return_counts=True)
        non_manifold = int((counts > 2).sum())
        open_edges = int((counts == 1).sum())
    else:
        non_manifold = open_edges = 0
    report["checks"]["non_manifold_edges"] = non_manifold
    report["checks"]["open_edges"] = open_edges
    if not mesh.is_winding_consistent:
        trimesh.repair.fix_winding(mesh)
        report["repairs"].append("Fixed inconsistent face winding")
    if not mesh.is_watertight:
        before = open_edges
        filled = trimesh.repair.fill_holes(mesh)
        if mesh.is_watertight:
            report["repairs"].append(f"Filled holes ({before} open edge(s)) to make the mesh watertight")
        elif filled:
            report["repairs"].append("Attempted hole filling (partial)")
    report["checks"]["watertight"] = bool(mesh.is_watertight)
    if not mesh.is_watertight:
        _error(report, "not_watertight",
               f"STL is not watertight/manifold even after a safe repair "
               f"({open_edges} open edge(s), {non_manifold} non-manifold edge(s)). Repair it in your CAD tool.")
    elif non_manifold:
        _warn(report, "non_manifold", f"{non_manifold} non-manifold edge(s) found")

    # --- size, units, bed fit (never scaled) ---
    ext = mesh.extents
    report["checks"]["model_size_mm"] = [round(float(v), 3) for v in ext]
    biggest = float(max(ext))
    if biggest < 2.0:
        _warn(report, "units_too_small",
              f"Model is only {biggest:.3f} mm across - it may have been exported in inches or metres. "
              "It is NOT rescaled; fix the export units if this is wrong.")
    elif biggest > 1000.0:
        _warn(report, "units_too_large",
              f"Model is {biggest:.0f} mm across - it may have been exported in micrometres or the wrong unit. "
              "It is NOT rescaled.")
    height = float(ext[2])
    if height <= 0:
        _error(report, "zero_height", "Model has zero height")
    elif height < layer_height / 2:
        _error(report, "too_thin", f"Model height {height:.3f} mm is less than half a layer")
    if height > max_z:
        _error(report, "too_tall", f"Model height {height:.1f} mm exceeds the Adventurer 5M build height of {max_z:.0f} mm")
    max_xy = bed - 2 * margin
    if ext[0] > max_xy or ext[1] > max_xy:
        _error(report, "off_bed",
               f"Model XY footprint {ext[0]:.1f} x {ext[1]:.1f} mm exceeds the usable "
               f"{max_xy:.0f} x {max_xy:.0f} mm area of the Adventurer 5M 220 mm bed")

    if report["errors"]:
        raise SliceValidationError(report)

    # --- place: centre on X0 Y0 (AD5M origin), lowest point on Z0 ---
    (xmin, ymin, zmin), (xmax, ymax, _zmax) = mesh.bounds
    mesh.apply_translation([-(xmin + xmax) / 2, -(ymin + ymax) / 2, -zmin])
    report["checks"]["placement"] = "centred at X0 Y0 (bed centre), lowest point on Z0"

    # --- bodies: separate parts, internal cavities, nested solids; normals ---
    try:
        bodies = list(mesh.split(only_watertight=False))
    except Exception:
        bodies = [mesh]
    depths = _body_depths(bodies)
    fixed_any = False
    for i, (body, depth) in enumerate(zip(bodies, depths)):
        role = "separate" if depth == 0 else ("internal_cavity" if depth % 2 == 1 else "nested_solid")
        vol = float(body.volume) if body.is_watertight else None
        want_positive = depth % 2 == 0
        inverted = vol is not None and ((vol < 0) == want_positive)
        if inverted:
            body.invert()
            fixed_any = True
            report["repairs"].append(
                f"Body {i + 1} ({role}) had inverted normals - flipped on a copy "
                "(slicing uses nesting, so the toolpath is unaffected)")
        b0, b1 = body.bounds
        report["bodies"].append({
            "index": i + 1,
            "role": role,
            "nesting_depth": depth,
            "watertight": bool(body.is_watertight),
            "volume_mm3": round(abs(vol), 2) if vol is not None else None,
            "faces": int(len(body.faces)),
            "bounds_mm": [[round(float(v), 3) for v in b0], [round(float(v), 3) for v in b1]],
            "normals_were_inverted": bool(inverted),
        })
    if fixed_any:
        mesh = trimesh.util.concatenate(bodies)
    # Bodies are sliced one by one and combined by nesting depth (see _section_regions),
    # which stays correct when separate bodies overlap each other.
    mesh.metadata["ung_bodies"] = list(zip(bodies, depths)) if 1 < len(bodies) <= 200 else None
    roles = [b["role"] for b in report["bodies"]]
    if roles.count("separate") > 1:
        _warn(report, "multiple_bodies", f"{roles.count('separate')} separate bodies will be printed together")
    if "internal_cavity" in roles:
        _warn(report, "internal_cavity",
              f"{roles.count('internal_cavity')} sealed internal cavit(y/ies) will print hollow, exactly as modelled")
    if "nested_solid" in roles:
        _warn(report, "nested_solid",
              f"{roles.count('nested_solid')} solid bod(y/ies) sit inside a cavity and will print as loose parts")

    # --- overhangs steeper than 50 degrees from vertical (no supports are generated) ---
    normals = mesh.face_normals
    areas = mesh.area_faces
    tri_z = mesh.triangles[:, :, 2]
    on_bed = tri_z.max(axis=1) < 0.05
    steep = (-normals[:, 2] > math.sin(math.radians(OVERHANG_LIMIT_DEG))) & ~on_bed
    total_area = float(areas.sum()) or 1.0
    over_area = float(areas[steep].sum())
    pct = 100.0 * over_area / total_area
    report["checks"]["overhang_percent"] = round(pct, 2)
    if over_area > 1.0:
        z_lo = float(tri_z[steep].min())
        z_hi = float(tri_z[steep].max())
        _warn(report, "overhang",
              f"{pct:.1f}% of the surface overhangs more than {OVERHANG_LIMIT_DEG:.0f} degrees with no support "
              f"(Z {z_lo:.2f}-{z_hi:.2f} mm). Expect sagging or failed bridges there.",
              percent=round(pct, 2), z_range_mm=[round(z_lo, 3), round(z_hi, 3)])
    return mesh, report


def layer_heights(height, layer_height, nozzle=0.40):
    """
    Returns [{"z": top, "sample": mid, "thickness": t}, ...].
    z (nozzle height) = TOP of the layer: layer_height, 2*layer_height, ...
    sample = middle of the layer, where the mesh is cut.
    The final layer is adjusted so its top lands exactly on the model height;
    if that would make it thicker than 75 % of the nozzle it is split in two.
    """
    n = max(1, int(round(height / layer_height)))
    tops = [i * layer_height for i in range(1, n)]
    remaining = height - (tops[-1] if tops else 0.0)
    if remaining > 0.75 * nozzle:
        tops.append((tops[-1] if tops else 0.0) + remaining / 2)
    tops.append(height)
    out = []
    prev = 0.0
    for z in tops:
        t = z - prev
        out.append({"z": round(z, 4), "sample": min(prev + t / 2, height - 1e-4), "thickness": t})
        prev = z
    return out


def _section_single(mesh, samples):
    """Cross-section one closed shell at each sample height (even-odd nesting via polygons_full)."""
    sections = mesh.section_multiplane(plane_origin=[0, 0, 0], plane_normal=[0, 0, 1], heights=list(samples))
    regions = []
    for path in sections:
        if path is None or len(path.entities) == 0:
            regions.append(MultiPolygon())
            continue
        try:
            polys = list(path.polygons_full)   # holes and cavities stay hollow
        except Exception:
            polys = []
        to_3d = path.metadata.get("to_3D") if hasattr(path, "metadata") else None
        if to_3d is not None:
            m = np.asarray(to_3d)
            if not np.allclose(m[:2, :2], np.eye(2)) or not np.allclose(m[:2, 3], 0):
                params = [m[0, 0], m[0, 1], m[1, 0], m[1, 1], m[0, 3], m[1, 3]]
                polys = [affinity.affine_transform(p, params) for p in polys]
        merged = unary_union([p.buffer(0) for p in polys if p is not None and not p.is_empty]) if polys else None
        regions.append(_as_multipolygon(merged) if merged is not None and not merged.is_empty else MultiPolygon())
    return regions


def _section_regions(mesh, samples):
    """
    Cross-section the mesh at each sample height; returns a cleaned MultiPolygon per layer.
    Multi-body meshes are sliced body by body and combined by nesting depth:
    depth 0 (separate part) adds material, depth 1 (sealed cavity) removes it,
    depth 2 (solid inside a cavity) adds it again, and so on.
    """
    bodies = mesh.metadata.get("ung_bodies") if hasattr(mesh, "metadata") else None
    if not bodies:
        per_layer = _section_single(mesh, samples)
    else:
        by_depth = {}
        for body, depth in bodies:
            by_depth.setdefault(depth, []).append(_section_single(body, samples))
        per_layer = []
        for i in range(len(samples)):
            region = MultiPolygon()
            for depth in sorted(by_depth):
                layer_geom = unary_union([secs[i] for secs in by_depth[depth]])
                if layer_geom.is_empty:
                    continue
                region = region.union(layer_geom) if depth % 2 == 0 else region.difference(layer_geom)
            per_layer.append(_as_multipolygon(region))
    out = []
    for region in per_layer:
        if region.is_empty:
            out.append(MultiPolygon())
        else:
            out.append(_as_multipolygon(region.buffer(0).simplify(0.005)))
    return out


# ---------- Toolpath planning ----------

def plan_layers(mesh, layer_height=0.20, nozzle=0.40, line_width=None, wall_count=2,
                infill_density=0.20, top_layers=4, bottom_layers=4, skirt=True,
                elephant_foot_mm=0.1, xy_hole_comp_mm=0.0, report=None):
    """
    Plan all toolpaths for an already-placed mesh (see validate_and_prepare).
    Returns a list of layers: {"index", "z", "thickness", "paths": [(kind, [(x, y), ...]), ...],
    "wall_bounds": bounds of the islands that received walls}.
    kinds: skirt, outer_wall, inner_wall, solid_infill, sparse_infill
    """
    if report is None:
        report = new_report()
    lw = float(line_width) if line_width else nozzle * 1.125
    if wall_count < 1:
        raise ValueError("wall_count must be at least 1")
    if not (0.0 <= infill_density <= 1.0):
        raise ValueError("infill_density must be between 0 and 1")

    height = float(mesh.bounds[1][2] - mesh.bounds[0][2])
    zs = layer_heights(height, layer_height, nozzle)
    regions = _section_regions(mesh, [l["sample"] for l in zs])
    regions = [_compensate_holes(r, xy_hole_comp_mm) for r in regions]
    n = len(regions)
    empty = MultiPolygon()

    def region(i):
        return regions[i] if 0 <= i < n else empty

    # ----- diagnostics: thin walls, tiny features, first-layer contact -----
    thin_locs, tiny_locs = [], []
    thin_layers = 0
    for i, reg in enumerate(regions):
        if reg.is_empty:
            continue
        z = zs[i]["z"]
        # morphological opening: true erosion (round) then dilation (mitre keeps convex corners sharp)
        opened = _inset(reg, lw / 2).buffer(lw / 2, join_style="mitre", mitre_limit=10.0)
        thin = reg.difference(opened)
        pieces = [p for p in _polygons(thin) if p.area > 0.25 * lw * lw]
        if pieces:
            thin_layers += 1
            for p in pieces:
                c = p.representative_point()
                _add_location(thin_locs, c.x, c.y, z)
        for island in _polygons(reg):
            if _inset(island, nozzle / 2).is_empty:
                c = island.representative_point()
                _add_location(tiny_locs, c.x, c.y, z)
    if thin_locs:
        _warn(report, "thin_walls",
              f"Walls thinner than one line width ({lw:.2f} mm) on {thin_layers} layer(s) - "
              "they may print incompletely or not at all", locations=thin_locs)
    if tiny_locs:
        _warn(report, "tiny_features",
              f"Features narrower than the {nozzle:.2f} mm nozzle will not print", locations=tiny_locs)
    first_area = float(regions[0].area) if n else 0.0
    max_area = max((float(r.area) for r in regions), default=0.0)
    report["checks"]["first_layer_contact_mm2"] = round(first_area, 2)
    if first_area <= 0:
        _warn(report, "no_first_layer", "Nothing touches the bed on the first layer")
    elif first_area < 25.0 or height > 8 * math.sqrt(first_area) or first_area < 0.1 * max_area:
        _warn(report, "small_contact",
              f"First-layer contact area is only {first_area:.1f} mm2 for a {height:.1f} mm tall part "
              "- risk of detaching or tipping over (consider a brim or reorienting)")

    layers = []
    pos = None
    for i, layer_info in enumerate(zs):
        reg = regions[i]
        if reg.is_empty:
            continue
        z = layer_info["z"]
        paths = []
        is_first = not layers

        # ----- solid skin detection (top + bottom, incl. overhangs and step-downs) -----
        above = region(i + 1)
        for k in range(2, top_layers + 1):
            above = above.intersection(region(i + k))
        below = region(i - 1)
        for k in range(2, bottom_layers + 1):
            below = below.intersection(region(i - k))
        need = unary_union([reg.difference(above) if top_layers > 0 else empty,
                            reg.difference(below) if bottom_layers > 0 else empty])
        if not need.is_empty:
            need = need.buffer(-0.4 * lw).buffer(1.4 * lw)

        # ----- elephant-foot compensation: inset the first layer outline -----
        print_reg = reg
        if is_first and elephant_foot_mm > 0:
            print_reg = _as_multipolygon(_inset(reg, elephant_foot_mm))

        # ----- skirt (first printed layer only) -----
        if skirt and is_first:
            loop = reg.convex_hull.buffer(SKIRT_DISTANCE + lw / 2, quad_segs=4)
            minx, miny, maxx, maxy = loop.bounds
            limit = BED_HALF - 1.0
            if minx >= -limit and miny >= -limit and maxx <= limit and maxy <= limit:
                for ring in _rings(loop):
                    pts = _ring_from_nearest(ring, pos)
                    paths.append(("skirt", pts))
                    pos = pts[-1]

        angle = 45.0 if i % 2 == 0 else -45.0
        wall_islands = []
        outline_error = 0.0
        islands = sorted(_polygons(print_reg), key=lambda p: (p.centroid.x, p.centroid.y))
        for island in islands:
            # ----- perimeters: inner first, outer last; outer centre = outline - lw/2 -----
            shells = []
            for k in range(wall_count):
                off = _inset(island, lw / 2 + k * lw)
                if off.is_empty:
                    break
                shells.append(off)
            if not shells:
                continue   # feature thinner than one line width (reported above)
            wall_islands.append(island)
            # outer wall centres must sit exactly lw/2 (+ elephant-foot inset) inside the true outline
            expected = lw / 2 + (elephant_foot_mm if is_first and elephant_foot_mm > 0 else 0.0)
            ring_pts = [pt for ring in _rings(shells[0]) for pt in ring]
            if ring_pts:
                dists = shapely.distance(reg.boundary, shapely.points(ring_pts))
                outline_error = max(outline_error, float(np.max(np.abs(dists - expected))))
            for k in range(len(shells) - 1, -1, -1):
                kind = "outer_wall" if k == 0 else "inner_wall"
                for ring in _rings(shells[k]):
                    if len(ring) < 4:
                        continue
                    pts = _ring_from_nearest(ring, pos)
                    paths.append((kind, pts))
                    pos = pts[-1]

            # ----- infill inside the innermost perimeter (25 % overlap with it) -----
            fill_area = shells[-1].buffer(-0.75 * lw)
            if fill_area.is_empty:
                continue
            solid = fill_area.intersection(need) if not need.is_empty else empty
            sparse = fill_area.difference(solid) if not solid.is_empty else fill_area
            for seg_a, seg_b in _order_segments(_rectilinear_lines(solid, lw, angle, lw * 0.5), pos):
                paths.append(("solid_infill", [seg_a, seg_b]))
                pos = seg_b
            if infill_density > 0:
                spacing = lw / infill_density
                for seg_a, seg_b in _order_segments(_rectilinear_lines(sparse, spacing, angle, lw), pos):
                    paths.append(("sparse_infill", [seg_a, seg_b]))
                    pos = seg_b

        if paths:
            wall_bounds = unary_union(wall_islands).bounds if wall_islands else None
            layers.append({"index": len(layers) + 1, "z": z, "thickness": layer_info["thickness"],
                           "paths": paths, "wall_bounds": wall_bounds, "outline_error": outline_error,
                           "elephant_foot": elephant_foot_mm if is_first else 0.0})
    return layers


# ---------- G-code writer ----------

class _GcodeWriter:
    def __init__(self, retract_length=RETRACT_LENGTH, z_hop=0.0):
        self.lines = []
        self.x = None
        self.y = None
        self.z = 0.0
        self.e = 0.0
        self.retracted = False
        self.retract_length = retract_length
        self.z_hop = z_hop
        self.filament_mm = 0.0
        self.seconds = 0.0

    def emit(self, line):
        self.lines.append(line)

    @staticmethod
    def _check_xy(x, y):
        if abs(x) > BED_HALF + 1e-6 or abs(y) > BED_HALF + 1e-6:
            raise ValueError(f"Toolpath point X{x:.2f} Y{y:.2f} is outside the 220 mm bed (-110..110)")

    def reset_e(self):
        self.emit("G92 E0")
        self.e = 0.0

    def retract(self):
        if self.retracted or self.retract_length <= 0:
            return
        self.e -= self.retract_length
        self.emit(f"G1 E{self.e:.5f} F{RETRACT_FEED}")
        self.seconds += self.retract_length / RETRACT_FEED * 60
        self.retracted = True

    def unretract(self):
        if not self.retracted:
            return
        self.e += self.retract_length
        self.emit(f"G1 E{self.e:.5f} F{RETRACT_FEED}")
        self.seconds += self.retract_length / RETRACT_FEED * 60
        self.retracted = False

    def move_z(self, z):
        if z > MAX_Z + 1e-6:
            raise ValueError(f"Z {z:.2f} exceeds the {MAX_Z:.0f} mm build height")
        self.seconds += abs(z - self.z) / FEED_Z * 60
        self.z = z
        self.emit(f"G1 Z{z:.3f} F{FEED_Z}")

    def travel(self, x, y):
        self._check_xy(x, y)
        if self.x is None:
            self.emit(f"G0 X{x:.3f} Y{y:.3f} F{FEED_TRAVEL}")
            self.x, self.y = x, y
            return
        dist = math.hypot(x - self.x, y - self.y)
        if dist < 1e-4:
            return
        long_travel = dist > RETRACT_MIN_TRAVEL
        if long_travel:
            self.retract()
            if self.z_hop > 0:
                self.emit(f"G1 Z{self.z + self.z_hop:.3f} F{FEED_Z}")
                self.seconds += 2 * self.z_hop / FEED_Z * 60
        self.emit(f"G0 X{x:.3f} Y{y:.3f} F{FEED_TRAVEL}")
        self.seconds += dist / FEED_TRAVEL * 60
        if long_travel and self.z_hop > 0:
            self.emit(f"G1 Z{self.z:.3f} F{FEED_Z}")
        self.x, self.y = x, y

    def extrude_to(self, x, y, feed, e_per_mm):
        self._check_xy(x, y)
        self.unretract()
        dist = math.hypot(x - self.x, y - self.y)
        if dist < 1e-4:
            return
        de = dist * e_per_mm
        self.e += de
        self.filament_mm += de
        self.seconds += dist / feed * 60
        self.emit(f"G1 X{x:.3f} Y{y:.3f} E{self.e:.5f} F{feed:.0f}")
        self.x, self.y = x, y

    def path(self, pts, feed, e_per_mm):
        if len(pts) < 2:
            return
        self.travel(*pts[0])
        for x, y in pts[1:]:
            self.extrude_to(x, y, feed, e_per_mm)


def _feed_for(kind, first_layer):
    if first_layer:
        return FEED_FIRST_LAYER
    return {
        "skirt": FEED_FIRST_LAYER,
        "outer_wall": FEED_OUTER_WALL,
        "inner_wall": FEED_INNER_WALL,
        "solid_infill": FEED_SOLID,
        "sparse_infill": FEED_SPARSE,
    }[kind]


def _format_duration(seconds):
    seconds = int(round(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h {m:02d}m" if h else f"{m}m {s:02d}s"


# ---------- G-code self-check ----------

_WORD = re.compile(r"([A-Z])(-?\d+(?:\.\d*)?)")


def check_gcode(text, bed_half=BED_HALF, max_z=MAX_Z):
    """
    Audit generated G-code. Returns a list of problems (empty = OK):
      * every X/Y inside the bed (-bed_half..bed_half), Z inside 0..max_z
      * layer Z (;Z: markers and the Z of extruding moves) never decreases
      * no extrusion on G0 travel moves
      * E on extruding moves never decreases between G92 resets
      * nozzle and bed temperatures set before the first extrusion
      * every ;LAYER has at least one extruding move
    """
    problems = []
    x = y = None
    z = 0.0
    e = 0.0
    last_extrude_e = 0.0
    nozzle_set = bed_set = False
    in_print = False
    layer = None
    layer_extrusions = {}
    last_layer_z = -1.0
    last_extrude_z = -1.0
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.split(";", 1)[0].strip()
        comment = raw.strip()
        if comment.startswith(";LAYER:"):
            in_print = True
            layer = comment.split(":", 1)[1]
            layer_extrusions[layer] = 0
        elif comment.startswith(";Z:"):
            lz = float(comment[3:])
            if lz < last_layer_z - 1e-6:
                problems.append(f"line {lineno}: layer Z {lz} is below the previous layer {last_layer_z}")
            last_layer_z = lz
        elif comment.startswith(";END"):
            in_print = False
        if not line:
            continue
        cmd = line.split()[0]
        words = {k: float(v) for k, v in _WORD.findall(line[len(cmd):])}
        if cmd in ("M104", "M109") and words.get("S", 0) > 0:
            nozzle_set = True
        elif cmd in ("M140", "M190") and words.get("S", 0) > 0:
            bed_set = True
        elif cmd == "G92":
            if "E" in words:
                e = words["E"]
                last_extrude_e = e
        elif cmd in ("G0", "G1"):
            nx, ny, nz = words.get("X", x), words.get("Y", y), words.get("Z", z)
            for axis, val in (("X", words.get("X")), ("Y", words.get("Y"))):
                if val is not None and abs(val) > bed_half + 1e-6:
                    problems.append(f"line {lineno}: {axis}{val} is outside the bed (+/-{bed_half:g})")
            if "Z" in words and not (-1e-6 <= words["Z"] <= max_z + 1e-6):
                problems.append(f"line {lineno}: Z{words['Z']} is outside 0..{max_z:g}")
            moves_xy = ("X" in words and nx != x) or ("Y" in words and ny != y)
            if "E" in words:
                ne = words["E"]
                if cmd == "G0" and ne > e + 1e-9:
                    problems.append(f"line {lineno}: extrusion on a G0 travel move")
                if moves_xy and ne > e + 1e-9:
                    if not (nozzle_set and bed_set):
                        problems.append(f"line {lineno}: extrusion before nozzle and bed temperatures were set")
                    if ne < last_extrude_e - 1e-9:
                        problems.append(f"line {lineno}: E went backwards on an extruding move")
                    if in_print:
                        if nz < last_extrude_z - 1e-6:
                            problems.append(f"line {lineno}: extruding at Z{nz} below a previous layer Z{last_extrude_z}")
                        last_extrude_z = max(last_extrude_z, nz)
                        if layer is not None:
                            layer_extrusions[layer] += 1
                    last_extrude_e = ne
                elif moves_xy and ne < e - 1e-9:
                    problems.append(f"line {lineno}: E went backwards (negative extrusion) during an XY move")
                e = ne
            x, y, z = nx, ny, nz
        if len(problems) > 50:
            break
    for name, count in layer_extrusions.items():
        if count == 0:
            problems.append(f"layer {name} has no extrusion")
    if not layer_extrusions:
        problems.append("no layers found")
    return problems


# ---------- Public entry points ----------

def slice_model(data: bytes, filename: str, layer_height=0.20, nozzle=0.40, wall_count=2, bed=220,
                material="PLA", line_width=None, infill_density=0.20, top_layers=4, bottom_layers=4,
                skirt=True, z_hop=0.0, retract_length=RETRACT_LENGTH,
                elephant_foot_mm=0.1, xy_hole_comp_mm=0.0):
    """
    Validate + slice + self-check. Returns {"gcode": bytes, "stats": dict, "layers": [...], "report": dict}.
    Raises SliceValidationError (blocking model problems), GcodeCheckError (self-check failed)
    or ValueError (bad parameters).
    """
    if not (0.08 <= float(layer_height) <= 0.40):
        raise ValueError("Layer height must be 0.08-0.40 mm")
    if float(bed) != BED_SIZE:
        raise ValueError("Only the Adventurer 5M 220 mm bed is supported")
    if not (0.0 <= float(elephant_foot_mm) <= 0.5):
        raise ValueError("elephant_foot_mm must be between 0 and 0.5")
    if not (-1.0 <= float(xy_hole_comp_mm) <= 1.0):
        raise ValueError("xy_hole_comp_mm must be between -1 and 1")
    mat_name, mat = material_profile(material)
    lw = float(line_width) if line_width else nozzle * 1.125

    mesh, report = validate_and_prepare(data, layer_height=layer_height, nozzle=nozzle, line_width=lw)
    ext = mesh.extents
    height = float(ext[2])

    layers = plan_layers(mesh, layer_height=layer_height, nozzle=nozzle, line_width=lw,
                         wall_count=wall_count, infill_density=infill_density,
                         top_layers=top_layers, bottom_layers=bottom_layers, skirt=skirt,
                         elephant_foot_mm=elephant_foot_mm, xy_hole_comp_mm=xy_hole_comp_mm, report=report)
    if not layers:
        _error(report, "nothing_to_print", "No printable cross-sections were generated")
        raise SliceValidationError(report)

    # ----- dimension self-check (no scaling) -----
    dims = _measure_dimensions(layers, lw, ext, height)
    report["checks"]["dimensions"] = dims
    if dims["toolpath_vs_outline_error_mm"] > DIMENSION_TOLERANCE:
        _error(report, "dimension_mismatch",
               f"Outer wall centres deviate {dims['toolpath_vs_outline_error_mm']:.3f} mm from "
               "line_width/2 inside the sliced outline - refusing to output G-code")
        raise SliceValidationError(report)
    if dims["max_deviation_mm"] > DIMENSION_TOLERANCE:
        _warn(report, "dimension_deviation",
              f"Printed XY size {dims['toolpath_size_mm'][:2]} differs from the model "
              f"{dims['model_size_mm'][:2]} by up to {dims['max_deviation_mm']:.3f} mm (sloped or curved "
              "surfaces are sampled at mid-layer, and features thinner than one line width are skipped)")

    # ----- purge line: near the front edge, clear of the first layer (incl. skirt) -----
    first_paths = layers[0]["paths"]
    first_min_y = min(y for _, pts in first_paths for _, y in pts) - lw / 2
    purge_y = PURGE_Y
    if first_min_y < purge_y + PURGE_WIDTH / 2 + 1.0:
        purge_y = -(BED_HALF - 1.5)
    if first_min_y < purge_y + PURGE_WIDTH / 2 + 0.5:
        layers[0]["paths"] = [p for p in first_paths if p[0] != "skirt"]

    w = _GcodeWriter(retract_length=retract_length, z_hop=z_hop)
    w.emit("; UNG-CAD generated G-code")
    w.emit(f"; Model: {filename}")
    w.emit("; Printer: FlashForge Adventurer 5M (origin = bed centre, X/Y -110..110)")
    w.emit(f"; Material: {mat_name}  nozzle {mat['nozzle_temp']}C  bed {mat['bed_temp']}C")
    w.emit(f"; Layer height {layer_height:.2f} mm, line width {lw:.3f} mm, {wall_count} walls, "
           f"{infill_density * 100:.0f}% infill, {top_layers} top / {bottom_layers} bottom layers")
    w.emit(f"; Elephant-foot inset {elephant_foot_mm:.2f} mm, XY hole compensation {xy_hole_comp_mm:.2f} mm, no scaling")
    w.emit("; NOTE: verify material, temperatures and the first layer before production use")
    for line in ("G90", "M82", "M107",
                 f"M140 S{mat['bed_temp']}", f"M104 S{mat['nozzle_temp']}",
                 "G28",
                 f"M190 S{mat['bed_temp']}", f"M109 S{mat['nozzle_temp']}",
                 "G92 E0"):
        w.emit(line)
    w.move_z(5.0)
    w.emit("; purge line")
    w.travel(PURGE_X[0], purge_y)
    w.move_z(PURGE_HEIGHT)
    w.extrude_to(PURGE_X[1], purge_y, FEED_FIRST_LAYER, extrusion_per_mm(PURGE_WIDTH, PURGE_HEIGHT))

    for layer in layers:
        first = layer["index"] == 1
        epm = extrusion_per_mm(lw, layer["thickness"])
        w.emit(f";LAYER:{layer['index']}")
        w.emit(f";Z:{layer['z']:.3f}")
        w.reset_e()
        if layer["index"] == FAN_START_LAYER:
            w.emit(f"M106 S{mat['fan']}")
        w.retract()
        w.move_z(layer["z"])
        for kind, pts in layer["paths"]:
            w.emit(f";TYPE:{kind}")
            w.path(pts, _feed_for(kind, first), epm)

    top_z = layers[-1]["z"]
    w.emit(";END")
    w.retract()
    w.move_z(min(top_z + 10.0, MAX_Z))
    w.travel(*PARK_XY)
    for line in ("M107", "M104 S0", "M140 S0", "M84"):
        w.emit(line)

    text = "\n".join(w.lines) + "\n"
    problems = check_gcode(text)
    report["checks"]["gcode_self_check"] = "passed" if not problems else problems
    if problems:
        raise GcodeCheckError(problems, report)

    payload = text.encode()
    grams = FILAMENT_AREA * w.filament_mm / 1000.0 * mat["density"]   # mm^3 -> cm^3 -> g
    stats = {
        "layers": len(layers),
        "height_mm": round(height, 3),
        "size_xy_mm": [round(float(ext[0]), 3), round(float(ext[1]), 3)],
        "model_size_mm": dims["model_size_mm"],
        "toolpath_size_mm": dims["toolpath_size_mm"],
        "dimension_deviation_mm": dims["deviation_mm"],
        "top_z_mm": top_z,
        "height_error_mm": round(top_z - height, 4),
        "last_layer_height_mm": round(layers[-1]["thickness"], 4),
        "bytes": len(payload),
        "material": mat_name,
        "nozzle_temp_c": mat["nozzle_temp"],
        "bed_temp_c": mat["bed_temp"],
        "layer_height_mm": float(layer_height),
        "first_layer_z_mm": layers[0]["z"],
        "line_width_mm": round(lw, 3),
        "wall_count": int(wall_count),
        "infill_percent": round(infill_density * 100, 1),
        "top_layers": int(top_layers),
        "bottom_layers": int(bottom_layers),
        "elephant_foot_mm": float(elephant_foot_mm),
        "xy_hole_comp_mm": float(xy_hole_comp_mm),
        "bodies": report["bodies"],
        "filament_mm": round(w.filament_mm, 1),
        "filament_m": round(w.filament_mm / 1000.0, 3),
        "filament_g": round(grams, 2),
        "estimated_seconds": int(round(w.seconds)),
        "estimated_time": _format_duration(w.seconds),
        "estimate_note": "Estimate from path lengths and feed rates only (ignores acceleration); real prints usually take longer.",
        "origin": "bed centre (X0 Y0)",
        "warnings": [wm["message"] for wm in report["warnings"]],
    }
    return {"gcode": payload, "stats": stats, "layers": layers, "report": report}


def _measure_dimensions(layers, lw, ext, height):
    """
    Measure the outer-wall toolpath: centres + line width = printed size.
    (a) every outer-wall vertex must be lw/2 (+ elephant-foot inset on layer 1) from the
        sliced outline (within 0.05 mm) - proves nothing was scaled or shifted;
    (b) the printed size is compared with the model size (reported; warning if off).
    Layer 1 is left out of the size because of the deliberate elephant-foot inset.
    """
    use = [l for l in layers if l["index"] > 1] or layers
    xs, ys = [], []
    for layer in use:
        pts = [p for kind, path in layer["paths"] if kind == "outer_wall" for p in path]
        if not pts:
            continue
        arr = np.array(pts)
        xs += [float(arr[:, 0].min()), float(arr[:, 0].max())]
        ys += [float(arr[:, 1].min()), float(arr[:, 1].max())]
    worst = max((l.get("outline_error", 0.0) for l in layers), default=0.0)
    if xs:
        size = [max(xs) - min(xs) + lw, max(ys) - min(ys) + lw]
    else:
        size = [0.0, 0.0]
    top = layers[-1]["z"]
    model = [float(ext[0]), float(ext[1]), float(height)]
    dev = [size[0] - model[0], size[1] - model[1], top - model[2]]
    return {
        "model_size_mm": [round(v, 3) for v in model],
        "toolpath_size_mm": [round(size[0], 3), round(size[1], 3), round(top, 3)],
        "deviation_mm": [round(v, 3) for v in dev],
        "max_deviation_mm": round(max(abs(v) for v in dev), 4),
        "toolpath_vs_outline_error_mm": round(float(worst), 4),
    }


def slice_stl(data: bytes, filename: str, **kwargs):
    """Backwards-compatible wrapper: returns (gcode_bytes, stats_dict)."""
    result = slice_model(data, filename, **kwargs)
    return result["gcode"], result["stats"]


def preview_stl(data: bytes, filename: str, max_layers=400, **kwargs):
    """
    Slice (with all checks) and return JSON-friendly per-layer toolpaths for the preview viewer:
    {"layers": [{"index", "z", "thickness", "paths": [{"type": perimeter|infill|solid|travel,
     "kind", "points": [[x, y], ...]}]}], "stats", "warnings", "validation", ...}
    """
    result = slice_model(data, filename, **kwargs)
    layers = result["layers"]
    stride = max(1, math.ceil(len(layers) / max(1, int(max_layers))))
    chosen = [l for l in layers if (l["index"] - 1) % stride == 0]
    if chosen[-1] is not layers[-1]:
        chosen.append(layers[-1])
    out_layers = []
    for layer in chosen:
        paths = []
        prev_end = None
        for kind, pts in layer["paths"]:
            if prev_end is not None and (abs(prev_end[0] - pts[0][0]) > 1e-6 or abs(prev_end[1] - pts[0][1]) > 1e-6):
                paths.append({"type": "travel", "kind": "travel",
                              "points": [[round(prev_end[0], 3), round(prev_end[1], 3)],
                                         [round(pts[0][0], 3), round(pts[0][1], 3)]]})
            paths.append({"type": PREVIEW_TYPES[kind], "kind": kind,
                          "points": [[round(px, 3), round(py, 3)] for px, py in pts]})
            prev_end = pts[-1]
        out_layers.append({"index": layer["index"], "z": layer["z"],
                           "thickness": round(layer["thickness"], 4), "paths": paths})
    stats = result["stats"]
    return {
        "ok": True,
        "source": filename,
        "bed": {"x": [-BED_HALF, BED_HALF], "y": [-BED_HALF, BED_HALF], "max_z": MAX_Z, "origin": "centre"},
        "line_width": stats["line_width_mm"],
        "layer_height": stats["layer_height_mm"],
        "layer_count": len(layers),
        "layer_stride": stride,
        "layers": out_layers,
        "stats": stats,
        "warnings": result["report"]["warnings"],
        "errors": result["report"]["errors"],
        "validation": result["report"],
    }
