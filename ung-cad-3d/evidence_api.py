"""FastAPI router for the authorized evidence workspace."""
from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,Field
from typing import Any,Dict,List
from cad_core.evidence_analysis import build_search_index,search,relationship_graph
from cad_core.evidence_reporting import build_report

router=APIRouter(prefix="/api/evidence",tags=["authorized-evidence"])

class Artifact(BaseModel):
    source_ref:str
    artifact_type:str="unknown"
    observed:Dict[str,Any]=Field(default_factory=dict)

class SearchRequest(BaseModel):
    artifacts:List[Artifact]
    query:str

@router.post("/search")
def evidence_search(req:SearchRequest):
    raw=[x.model_dump() for x in req.artifacts]
    return {"matches":search(build_search_index(raw),req.query)}

@router.post("/graph")
def evidence_graph(artifacts:List[Artifact]):
    return relationship_graph([x.model_dump() for x in artifacts])

class ReportRequest(BaseModel):
    case_id:str
    evidence:List[Dict[str,Any]]=Field(default_factory=list)
    findings:List[Dict[str,Any]]=Field(default_factory=list)
    limitations:List[str]=Field(default_factory=list)
    tool_versions:Dict[str,str]=Field(default_factory=dict)

@router.post("/report")
def evidence_report(req:ReportRequest):
    return build_report(req.case_id,req.evidence,req.findings,req.limitations,req.tool_versions)
