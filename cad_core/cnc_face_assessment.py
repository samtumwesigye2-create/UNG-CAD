"""UNG-CAD CNC feature assessment: conservative, review-first planning.

Consumes explicitly supplied face metadata, not raw CAD meshes. It never
authorizes machining or emits machine-ready G-code.
"""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class Face:
    face_id: str
    kind: str
    diameter_mm: float | None = None
    width_mm: float | None = None
    height_mm: float | None = None
    depth_mm: float | None = None

def assess_faces(faces, tool_diameter_mm, stock_thickness_mm):
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v > 0
               for v in (tool_diameter_mm, stock_thickness_mm)):
        raise ValueError("Tool diameter and stock thickness must be positive finite values")
    results = []
    seen = set()
    for f in faces:
        if not isinstance(f, Face) or not f.face_id or f.face_id in seen:
            raise ValueError("Faces require unique nonempty identifiers")
        seen.add(f.face_id)
        dims = [v for v in (f.diameter_mm, f.width_mm, f.height_mm, f.depth_mm) if v is not None]
        if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or v <= 0 for v in dims):
            raise ValueError("Invalid face dimension")
        issues = []
        operation = "manual_review"
        if f.kind == "cylindrical" and f.diameter_mm is not None:
            operation = "hole_candidate"
            if f.diameter_mm < tool_diameter_mm:
                issues.append("Selected cutter exceeds hole diameter")
        elif f.kind == "planar_pocket" and f.width_mm is not None and f.height_mm is not None:
            operation = "pocket_candidate"
            if min(f.width_mm, f.height_mm) <= tool_diameter_mm:
                issues.append("Selected cutter does not fit pocket width")
        else:
            issues.append("Unsupported or insufficient face metadata")
        if f.depth_mm is None:
            issues.append("Depth must be confirmed")
        elif f.depth_mm > stock_thickness_mm:
            issues.append("Depth exceeds stock thickness")
        results.append({"face_id": f.face_id, "operation": operation,
                        "status": "blocked" if issues else "review_required",
                        "issues": issues,
                        "requires": ["machine profile", "tool length", "stock origin", "fixturing",
                                     "collision simulation", "operator approval"]})
    return results
