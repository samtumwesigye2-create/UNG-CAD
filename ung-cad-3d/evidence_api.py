"""Integrated API for authorized evidence analysis. No device bypass/acquisition."""
from fastapi import APIRouter
from pydantic import BaseModel,Field
from typing import Any,Dict,List
from cad_core.evidence_analysis import build_search_index,search,relationship_graph,frequency_anomalies
from cad_core.evidence_reporting import build_report,verify_report
from cad_core.evidence_timeline import TimelineEvent,build_timeline,correlate,reconstruct_threads
from cad_core.evidence_integrity import sha256_bytes,verify_sha256,redact_sensitive_text
from cad_core.evidence_access import Principal,protected_view,integration_event

router=APIRouter(prefix="/api/evidence",tags=["authorized-evidence"])

class Artifact(BaseModel):
    source_ref:str
    artifact_type:str="unknown"
    observed:Dict[str,Any]=Field(default_factory=dict)
    timestamp:str|None=None
    confidence:float=Field(default=1.0,ge=0.0,le=1.0)

def raw(items:List[Artifact]): return [x.model_dump() for x in items]
def tev(a:Artifact)->TimelineEvent:
    if not a.timestamp: raise ValueError("timestamp required")
    return TimelineEvent(a.timestamp,a.artifact_type,a.source_ref,a.observed,a.confidence)

class SearchRequest(BaseModel):
    artifacts:List[Artifact]; query:str
@router.post("/search")
def evidence_search(req:SearchRequest):
    return {"matches":search(build_search_index(raw(req.artifacts)),req.query)}

@router.post("/graph")
def evidence_graph(artifacts:List[Artifact]):
    return relationship_graph(raw(artifacts))

class TimelineRequest(BaseModel):
    artifacts:List[Artifact]
    window_seconds:int=Field(default=300,ge=1,le=86400)
    threshold:float=Field(default=.25,ge=0,le=1)
@router.post("/timeline")
def timeline(req:TimelineRequest):
    events=[tev(x) for x in req.artifacts]
    ordered=build_timeline(events)
    return {"timeline":[e.__dict__ for e in ordered],
            "correlations":correlate(events,req.threshold,req.window_seconds),
            "threads":{k:[e.__dict__ for e in v] for k,v in reconstruct_threads(events).items()}}

class AnomalyRequest(BaseModel):
    values:List[str]; z_threshold:float=Field(default=2.0,gt=0)
@router.post("/anomalies")
def anomalies(req:AnomalyRequest):
    return {"anomalies":frequency_anomalies(req.values,req.z_threshold)}

class IntegrityRequest(BaseModel):
    content:str; expected_sha256:str|None=None
@router.post("/integrity")
def integrity(req:IntegrityRequest):
    b=req.content.encode()
    digest=sha256_bytes(b)
    return {"sha256":digest,"verified":None if req.expected_sha256 is None else verify_sha256(b,req.expected_sha256)}

class ProtectRequest(BaseModel):
    text:str; actor_id:str; roles:List[str]=Field(default_factory=list)
@router.post("/protect")
def protect(req:ProtectRequest):
    return {"text":protected_view(req.text,Principal(req.actor_id,frozenset(req.roles)))}

class EventRequest(BaseModel):
    event_type:str; case_id:str; evidence_id:str; payload:Dict[str,Any]=Field(default_factory=dict)
@router.post("/events")
def event(req:EventRequest):
    return integration_event(req.event_type,req.case_id,req.evidence_id,req.payload)

class ReportRequest(BaseModel):
    case_id:str
    evidence:List[Dict[str,Any]]=Field(default_factory=list)
    findings:List[Dict[str,Any]]=Field(default_factory=list)
    limitations:List[str]=Field(default_factory=list)
    tool_versions:Dict[str,str]=Field(default_factory=dict)
@router.post("/report")
def evidence_report(req:ReportRequest):
    return build_report(req.case_id,req.evidence,req.findings,req.limitations,req.tool_versions)
@router.post("/report/verify")
def evidence_report_verify(report:Dict[str,Any]):
    return {"verified":verify_report(report)}

@router.get("/health")
def evidence_health():
    return {"status":"ok","scope":"authorized-evidence-analysis","acquisition_or_bypass":False}
