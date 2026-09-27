"""Sensitive-data policy and integration-event primitives."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any,Dict,Iterable,List
from cad_core.evidence_integrity import redact_sensitive_text

@dataclass(frozen=True)
class Principal:
    actor_id:str
    roles:frozenset[str]

def can_reveal_sensitive(p:Principal)->bool:
    return bool(p.roles & {"evidence-sensitive-reviewer","evidence-admin"})

def protected_view(value:str,p:Principal)->str:
    return value if can_reveal_sensitive(p) else redact_sensitive_text(value)

def integration_event(kind:str,case_id:str,evidence_id:str,payload:Dict[str,Any]|None=None)->Dict[str,Any]:
    allowed={"evidence.imported","hash.verified","hash.failed","parser.completed","parser.failed",
             "sensitive.detected","timeline.updated","correlation.created","report.generated",
             "export.generated","access.reveal"}
    if kind not in allowed: raise ValueError("unsupported evidence event")
    return {"event_type":kind,"case_id":case_id,"evidence_id":evidence_id,"payload":dict(payload or {})}
