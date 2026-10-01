"""UNG-CAD mandatory production readiness gate.

This module is the live enforcement boundary between CAD/slicing and the AD5M
print queue. Critical HOLD or BLOCK findings can never be bypassed by the
slicer, API, UI, or local printer bridge.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from pathlib import Path
from typing import Any

PASS="PASS"
HOLD="HOLD"
BLOCK="BLOCK"
SCHEMA="UNG-PRODUCTION-READINESS-v7"

REQUIRED_SECTIONS=(
    "project",
    "inventory",
    "constraints",
    "parts",
    "electronics",
    "tests",
    "release_policy",
)

def _finding(rule_id:str,state:str,message:str,next_action:str|None=None)->dict:
    return {"rule_id":rule_id,"state":state,"message":message,"next_action":next_action}

def stable_hash(value:Any)->str:
    raw=json.dumps(value,sort_keys=True,separators=(",",":"),default=str).encode()
    return hashlib.sha256(raw).hexdigest()

def evaluate_manifest(manifest:dict)->dict:
    findings=[]
    for section in REQUIRED_SECTIONS:
        if section not in manifest:
            findings.append(_finding("PRG-MISSING-"+section.upper(),HOLD,
                f"Required manufacturing section '{section}' is missing.",
                f"Provide and verify {section}."))

    policy=manifest.get("release_policy",{})
    if policy.get("allow_critical_bypass") is True:
        findings.append(_finding("PRG-NO-BYPASS",BLOCK,
            "Critical bypass is enabled. Production release is forbidden.",
            "Set allow_critical_bypass=false."))

    forbidden=set(manifest.get("constraints",{}).get("forbidden_processes",[]))
    for op in manifest.get("process",{}).get("required_operations",[]):
        method=op.get("method")
        if method in forbidden:
            findings.append(_finding("PRG-FORBIDDEN-PROCESS",BLOCK,
                f"Operation '{op.get('name','unnamed')}' requires forbidden process '{method}'.",
                "Use a verified allowed process."))
        elif op.get("verified") is not True:
            findings.append(_finding("PRG-PROCESS-UNVERIFIED",HOLD,
                f"Operation '{op.get('name','unnamed')}' is not verified.",
                "Verify the manufacturing/assembly method."))

    acceptable_inventory={"physically_verified","dimensionally_verified",
                          "electrically_verified","installed","tested"}
    for item in manifest.get("inventory",[]):
        if item.get("quarantined") is True or item.get("state")=="quarantined":
            findings.append(_finding("PRG-INVENTORY-QUARANTINED",BLOCK,
                f"Inventory item '{item.get('name','unnamed')}' is quarantined.",
                "Remove the quarantined item from the build."))
        elif item.get("required_for_release",True) and item.get("state") not in acceptable_inventory:
            findings.append(_finding("PRG-INVENTORY-HOLD",HOLD,
                f"Required inventory '{item.get('name','unnamed')}' is not physically verified.",
                "Physically verify the actual item."))

    for part in manifest.get("parts",[]):
        name=part.get("name","unnamed")
        if part.get("can_manufacture") is False:
            findings.append(_finding("PRG-NOT-MANUFACTURABLE",BLOCK,
                f"Part '{name}' is marked non-manufacturable.",
                "Correct geometry/process constraints."))
        checks=part.get("checks",{})
        for key in ("dimensions_verified","fit_verified","clearance_verified",
                    "holes_verified","wire_routing_verified","assembly_access_verified",
                    "printer_envelope_verified","material_verified"):
            val=checks.get(key)
            if val is False:
                findings.append(_finding("PRG-PART-"+key.upper(),BLOCK,
                    f"Part '{name}' failed {key}.",
                    f"Resolve {key.replace('_',' ')}."))
            elif val is not True:
                findings.append(_finding("PRG-PART-"+key.upper(),HOLD,
                    f"Part '{name}' has not verified {key}.",
                    f"Verify {key.replace('_',' ')}."))

    for e in manifest.get("electronics",[]):
        name=e.get("name","unnamed")
        for key in ("voltage","polarity","connector_or_contact","current_capacity"):
            val=e.get("checks",{}).get(key)
            if val=="block" or val is False:
                findings.append(_finding("PRG-ELEC-"+key.upper(),BLOCK,
                    f"Electronics '{name}' failed {key}.",
                    f"Correct {key.replace('_',' ')} compatibility."))
            elif val!="pass" and val is not True:
                findings.append(_finding("PRG-ELEC-"+key.upper(),HOLD,
                    f"Electronics '{name}' has unverified {key}.",
                    f"Verify {key.replace('_',' ')}."))

    required_tests=policy.get("required_tests",[])
    by_name={t.get("name"):t for t in manifest.get("tests",[]) if t.get("name")}
    for name in required_tests:
        test=by_name.get(name)
        if not test:
            findings.append(_finding("PRG-TEST-MISSING",HOLD,
                f"Required test '{name}' is missing.","Run and record the test."))
            continue
        if test.get("result")=="fail":
            findings.append(_finding("PRG-TEST-FAIL",BLOCK,
                f"Required test '{name}' failed.","Fix the failure and rerun the test."))
        elif test.get("result")!="pass":
            findings.append(_finding("PRG-TEST-PENDING",HOLD,
                f"Required test '{name}' is pending.","Complete the test."))
        elif test.get("evidence_required") and not test.get("evidence_present"):
            findings.append(_finding("PRG-TEST-EVIDENCE",HOLD,
                f"Required test '{name}' lacks required evidence.","Attach required evidence."))

    if any(f["state"]==BLOCK for f in findings):
        state=BLOCK
    elif findings:
        state=HOLD
    else:
        state=PASS

    project=manifest.get("project",{})
    return {
        "schema":SCHEMA,
        "project":project.get("name","Unnamed"),
        "revision":project.get("revision","unknown"),
        "state":state,
        "production_release_allowed":state==PASS,
        "findings":findings,
        "manifest_hash":stable_hash(manifest),
    }

def require_release(manifest:dict)->dict:
    result=evaluate_manifest(manifest)
    if not result["production_release_allowed"]:
        msg="; ".join(f["message"] for f in result["findings"][:5]) or result["state"]
        raise PermissionError(f"PRODUCTION {result['state']}: {msg}")
    return result

def signing_key()->bytes:
    value=os.environ.get("UNG_GCODE_SIGNING_KEY","")
    if not value:
        raise RuntimeError("UNG_GCODE_SIGNING_KEY is not configured")
    return value.encode()

def sign_machine_file(path:Path, release:dict)->dict:
    data=path.read_bytes()
    metadata={
        "schema":SCHEMA,
        "project":release["project"],
        "revision":release["revision"],
        "manifest_hash":release["manifest_hash"],
        "machine_file_sha256":hashlib.sha256(data).hexdigest(),
        "signed_at_unix":int(time.time()),
    }
    body=json.dumps(metadata,sort_keys=True,separators=(",",":")).encode()
    metadata["signature"]=hmac.new(signing_key(),body,hashlib.sha256).hexdigest()
    sidecar=path.with_name(path.name+".ungrelease.json")
    sidecar.write_text(json.dumps(metadata,indent=2,sort_keys=True))
    return metadata

def verify_machine_file(path:Path)->tuple[bool,str,dict|None]:
    sidecar=path.with_name(path.name+".ungrelease.json")
    if not sidecar.exists():
        return False,"HARD LOCK: production release sidecar missing.",None
    try:
        metadata=json.loads(sidecar.read_text())
        sig=metadata.pop("signature")
        expected_file=hashlib.sha256(path.read_bytes()).hexdigest()
        if metadata.get("machine_file_sha256")!=expected_file:
            return False,"HARD LOCK: machine file changed after approval.",None
        body=json.dumps(metadata,sort_keys=True,separators=(",",":")).encode()
        expected=hmac.new(signing_key(),body,hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig,expected):
            return False,"HARD LOCK: release signature invalid.",None
        metadata["signature"]=sig
        return True,"Production release verified.",metadata
    except Exception as exc:
        return False,f"HARD LOCK: release verification failed: {exc}",None
