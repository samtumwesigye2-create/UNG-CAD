from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cad_core.production_readiness import evaluate_manifest, require_release, sign_machine_file, verify_machine_file

BASE_DIR=Path(__file__).resolve().parent
router=APIRouter(prefix="/api/manufacturing/readiness",tags=["production-readiness"])

class ManifestIn(BaseModel):
    manifest:dict

class ReleaseIn(BaseModel):
    manifest:dict
    machine_file:str

@router.post("/validate")
def validate_readiness(body:ManifestIn):
    return evaluate_manifest(body.manifest)

@router.post("/release")
def release_machine_file(body:ReleaseIn):
    machine=Path(body.machine_file).name
    target=BASE_DIR/"generated"/machine
    if not target.exists():
        raise HTTPException(404,"Machine file not found")
    try:
        result=require_release(body.manifest)
        metadata=sign_machine_file(target,result)
        return {"ok":True,"status":"APPROVED_FOR_PRODUCTION","release":result,"signature":metadata}
    except PermissionError as exc:
        result=evaluate_manifest(body.manifest)
        raise HTTPException(409,{"message":str(exc),"release":result})
    except RuntimeError as exc:
        raise HTTPException(503,str(exc))

@router.get("/machine-file/{name}")
def verify_released_machine_file(name:str):
    target=BASE_DIR/"generated"/Path(name).name
    if not target.exists():
        raise HTTPException(404,"Machine file not found")
    ok,message,metadata=verify_machine_file(target)
    return {"ok":ok,"message":message,"metadata":metadata}
