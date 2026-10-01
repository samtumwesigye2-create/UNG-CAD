import json
from pathlib import Path

from cad_core.production_readiness import HOLD, evaluate_manifest


def test_raven_manifest_stays_on_hold_until_physical_verification():
    root=Path(__file__).resolve().parents[1]
    manifest=json.loads((root/"projects"/"raven"/"production_manifest.json").read_text())
    result=evaluate_manifest(manifest)

    assert result["state"] == HOLD
    assert result["production_release_allowed"] is False
    assert not any(f["state"] == "BLOCK" for f in result["findings"])
    assert any("8520 motors" in f["message"] for f in result["findings"])
    assert any("motor clamp continuity" in f["message"] for f in result["findings"])
