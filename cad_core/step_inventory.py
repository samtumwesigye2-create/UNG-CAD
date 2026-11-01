"""Conservative STEP entity inventory for UNG-CAD CNC preflight.

This module scans ISO-10303-21 text STEP files for entity types and metadata.
It does NOT resolve topology, extract B-rep faces, or certify manufacturability.
"""
from collections import Counter
from pathlib import Path
import re

ENTITY_RE = re.compile(r"(?m)^\s*#(\d+)\s*=\s*([A-Z][A-Z0-9_]*)\s*\(", re.I)
MAX_BYTES = 25 * 1024 * 1024

def inventory_step(path):
    p = Path(path)
    if p.suffix.lower() not in (".step", ".stp"):
        raise ValueError("Expected a .step or .stp file")
    if p.stat().st_size > MAX_BYTES:
        raise ValueError("STEP file exceeds 25 MB inventory limit")
    content = p.read_text(encoding="latin-1")
    if "ISO-10303-21;" not in content[:4096].upper() or "END-ISO-10303-21;" not in content.upper():
        raise ValueError("Not a complete STEP Part 21 text file")
    entities = ENTITY_RE.findall(content)
    if not entities:
        raise ValueError("No STEP entities found")
    ids = [i for i, _ in entities]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate STEP entity IDs")
    counts = Counter(name.upper() for _, name in entities)
    faces = counts["ADVANCED_FACE"]
    return {"file": p.name, "entity_count": len(entities), "entity_types": dict(sorted(counts.items())),
            "advanced_face_count": faces, "has_closed_shell": counts["CLOSED_SHELL"] > 0,
            "status": "inventory_only",
            "warnings": ["Entity counts do not prove geometry is valid or machinable.",
                         "STEP topology, units, surface dimensions, adjacency and tool access are not extracted.",
                         "Do not generate machine-ready toolpaths from this inventory."]}
