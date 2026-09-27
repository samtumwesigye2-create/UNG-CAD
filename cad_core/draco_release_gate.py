"""Hard release gate for DRACO manufacturing packages.

Prevents legacy/reconstructed/incomplete DRACO packages from being presented as
production-ready or sliced as production parts. P0 validation coupons may still
be sliced for fit testing.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Iterable, Dict, Any, Tuple

CURRENT_PARTS = {
    "P1","P2","P9A","P9B","P3","P4","P5","P6","P7","P8"
}
RELEASE_MANIFEST = "DRACO_PRODUCTION_RELEASE.json"

def is_draco_name(name: str) -> bool:
    return "draco" in Path(name).name.lower()

def is_p0(name: str) -> bool:
    low=Path(name).name.lower()
    return "p0" in low and ("coupon" in low or "fit" in low)

def package_part_ids(names: Iterable[str]) -> set[str]:
    ids=set()
    for name in names:
        stem=Path(name).stem.upper().replace("-","_")
        for p in CURRENT_PARTS:
            if stem.startswith(p+"_") or ("_"+p+"_") in ("_"+stem+"_"):
                ids.add(p)
    return ids

def parse_release_manifest(data: bytes) -> Dict[str,Any]:
    try:
        value=json.loads(data.decode("utf-8"))
    except Exception as e:
        raise ValueError(f"Invalid {RELEASE_MANIFEST}: {e}") from e
    if not isinstance(value,dict):
        raise ValueError(f"{RELEASE_MANIFEST} must contain a JSON object")
    return value

def evaluate_package(names: Iterable[str], manifest: Dict[str,Any] | None) -> Tuple[bool,list[str]]:
    names=list(names)
    if not any(is_draco_name(n) for n in names):
        return True,[]
    blockers=[]
    found=package_part_ids(names)
    missing=sorted(CURRENT_PARTS-found)
    if missing:
        blockers.append("missing current Rev-K2.1 parts: "+", ".join(missing))
    if manifest is None:
        blockers.append(f"missing {RELEASE_MANIFEST}")
        return False,blockers
    required_true=[
        "release_ready","actual_hardware_dimensions_verified",
        "fit_coupon_passed","dry_assembly_passed",
        "pan_tilt_motion_validated","manifold_validation_passed",
        "source_cad_included"
    ]
    for key in required_true:
        if manifest.get(key) is not True:
            blockers.append(f"{key}=true required")
    if str(manifest.get("baffle_material","")).strip().lower()!="black pla":
        blockers.append("baffle_material must be 'black PLA'")
    if manifest.get("circular_12v_jack_present") is not False:
        blockers.append("circular_12v_jack_present must be false")
    if manifest.get("base_mounted_servos") != 2:
        blockers.append("base_mounted_servos must equal 2")
    return not blockers,blockers

def allow_selected_slice(selected: str, release_ok: bool) -> bool:
    return release_ok or is_p0(selected)
