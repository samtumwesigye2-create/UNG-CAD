"""Evidence-aware checks for the production release gate."""
from dataclasses import dataclass
from .release_gate import GateCheck, GateState

@dataclass(frozen=True)
class GateEvidence:
    source: str
    evaluated: bool
    passed: bool | None
    detail: str=""

def evidence_check(name: str, evidence: GateEvidence, *, missing=GateState.STALE) -> GateCheck:
    if not evidence.evaluated or evidence.passed is None:
        return GateCheck(name, missing, evidence.detail or f"{evidence.source}: not evaluated")
    return GateCheck(name, GateState.RELEASE if evidence.passed else GateState.BLOCKED,
                     evidence.detail or evidence.source)

def aggregate_evidence(checks):
    checks=tuple(checks)
    if any(c.state is GateState.BLOCKED for c in checks): return GateState.BLOCKED
    if any(c.state is GateState.STALE for c in checks): return GateState.STALE
    if any(c.state is GateState.WARNING for c in checks): return GateState.WARNING
    return GateState.RELEASE
