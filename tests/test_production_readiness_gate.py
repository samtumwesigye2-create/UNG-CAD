import json
from pathlib import Path

import pytest

from cad_core.production_readiness import (
    BLOCK,
    HOLD,
    PASS,
    evaluate_manifest,
    require_release,
    sign_machine_file,
    verify_machine_file,
)


def passing_manifest():
    return {
        "project": {"name": "TEST", "revision": "r1"},
        "inventory": [
            {"name": "part", "state": "physically_verified", "required_for_release": True}
        ],
        "constraints": {"forbidden_processes": []},
        "process": {"required_operations": [
            {"name": "assembly", "method": "snap_fit", "verified": True}
        ]},
        "parts": [{
            "name": "part",
            "can_manufacture": True,
            "checks": {
                "dimensions_verified": True,
                "fit_verified": True,
                "clearance_verified": True,
                "holes_verified": True,
                "wire_routing_verified": True,
                "assembly_access_verified": True,
                "printer_envelope_verified": True,
                "material_verified": True,
            },
        }],
        "electronics": [{
            "name": "power",
            "checks": {
                "voltage": "pass",
                "polarity": "pass",
                "connector_or_contact": "pass",
                "current_capacity": "pass",
            },
        }],
        "tests": [{"name": "fit", "result": "pass", "evidence_required": True, "evidence_present": True}],
        "release_policy": {"allow_critical_bypass": False, "required_tests": ["fit"]},
    }


def test_pass_manifest_releases():
    result = evaluate_manifest(passing_manifest())
    assert result["state"] == PASS
    assert result["production_release_allowed"] is True


def test_unverified_inventory_holds():
    m = passing_manifest()
    m["inventory"][0]["state"] = "ordered"
    result = evaluate_manifest(m)
    assert result["state"] == HOLD
    assert result["production_release_allowed"] is False


def test_forbidden_process_blocks():
    m = passing_manifest()
    m["constraints"]["forbidden_processes"] = ["soldering"]
    m["process"]["required_operations"][0] = {
        "name": "motor wiring", "method": "soldering", "verified": True
    }
    result = evaluate_manifest(m)
    assert result["state"] == BLOCK


def test_machine_file_signature_and_tamper(monkeypatch, tmp_path):
    monkeypatch.setenv("UNG_GCODE_SIGNING_KEY", "test-secret")
    release = require_release(passing_manifest())
    p = tmp_path / "job.gcode"
    p.write_text("G28\nG1 X10\n")
    sign_machine_file(p, release)

    ok, msg, metadata = verify_machine_file(p)
    assert ok is True
    assert metadata["project"] == "TEST"

    p.write_text("G28\nG1 X99\n")
    ok, msg, metadata = verify_machine_file(p)
    assert ok is False
    assert "changed after approval" in msg
