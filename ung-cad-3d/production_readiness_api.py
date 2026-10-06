import re
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from cad_core.production_readiness import evaluate_manifest, require_release, sign_machine_file, verify_machine_file

BASE_DIR = Path(__file__).resolve().parent
router = APIRouter(tags=["production-readiness"])

BRIDGE_STATES = {
    "READY",
    "BRIDGE_ONLINE_PRINTER_OFFLINE",
    "PAIRING_ERROR",
    "PRINTER_UNREACHABLE",
}
BRIDGE_HEARTBEAT_TTL_SECONDS = 20
BRIDGE_STATUS = {}
_PRINTER_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")


class ManifestIn(BaseModel):
    manifest: dict


class ReleaseIn(BaseModel):
    manifest: dict
    machine_file: str


class BridgeHeartbeatIn(BaseModel):
    printer_id: str
    state: str
    bridge_version: Optional[str] = None
    last_printer_contact: Optional[float] = None
    error: Optional[str] = None


def now_ts():
    return time.time()


def _clean_error(value):
    if not value:
        return None
    return " ".join(str(value).split())[:240]


def _validate_printer_id(printer_id: str):
    if not _PRINTER_ID_RE.fullmatch(printer_id or ""):
        raise HTTPException(422, "Invalid printer_id")
    return printer_id


@router.post("/api/manufacturing/readiness/validate")
def validate_readiness(body: ManifestIn):
    return evaluate_manifest(body.manifest)


@router.post("/api/manufacturing/readiness/release")
def release_machine_file(body: ReleaseIn):
    machine = Path(body.machine_file).name
    target = BASE_DIR / "generated" / machine
    if not target.exists():
        raise HTTPException(404, "Machine file not found")
    try:
        result = require_release(body.manifest)
        metadata = sign_machine_file(target, result)
        return {"ok": True, "status": "APPROVED_FOR_PRODUCTION", "release": result, "signature": metadata}
    except PermissionError as exc:
        result = evaluate_manifest(body.manifest)
        raise HTTPException(409, {"message": str(exc), "release": result})
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))


@router.get("/api/manufacturing/readiness/machine-file/{name}")
def verify_released_machine_file(name: str):
    target = BASE_DIR / "generated" / Path(name).name
    if not target.exists():
        raise HTTPException(404, "Machine file not found")
    ok, message, metadata = verify_machine_file(target)
    return {"ok": ok, "message": message, "metadata": metadata}


@router.get("/ung-cad-ad5m-agent.py")
def ad5m_agent_download():
    path = BASE_DIR / "ung-cad-ad5m-agent.py"
    if not path.exists():
        raise HTTPException(404, "AD5M status agent not installed")
    return FileResponse(path, filename="ung-cad-ad5m-agent.py", media_type="text/x-python")


@router.post("/api/bridge/heartbeat")
def bridge_heartbeat(body: BridgeHeartbeatIn):
    printer_id = _validate_printer_id(body.printer_id)
    if body.state not in BRIDGE_STATES:
        raise HTTPException(422, "Unknown bridge state")
    ts = now_ts()
    record = {
        "printer_id": printer_id,
        "state": body.state,
        "bridge_version": (body.bridge_version or "")[:64] or None,
        "last_printer_contact": body.last_printer_contact,
        "error": _clean_error(body.error),
        "reported_at": ts,
        "source": "bridge-self-report",
        "trusted": False,
    }
    BRIDGE_STATUS[printer_id] = record
    return {"ok": True, "reported_at": ts}


@router.get("/api/bridge/status/{printer_id}")
def bridge_status(printer_id: str):
    printer_id = _validate_printer_id(printer_id)
    record = BRIDGE_STATUS.get(printer_id)
    if record is None:
        return {
            "printer_id": printer_id,
            "state": "BRIDGE_OFFLINE",
            "last_reported_state": None,
            "fresh": False,
            "age_seconds": None,
            "source": "bridge-self-report",
            "trusted": False,
            "error": None,
        }
    age = max(0.0, now_ts() - record["reported_at"])
    fresh = age <= BRIDGE_HEARTBEAT_TTL_SECONDS
    result = dict(record)
    result["last_reported_state"] = record["state"]
    result["fresh"] = fresh
    result["age_seconds"] = round(age, 3)
    if not fresh:
        result["state"] = "BRIDGE_OFFLINE"
    return result
