"""Deterministic production-release gate for CAD/manufacturing artifacts."""
from dataclasses import dataclass, field
from enum import Enum

class GateState(str,Enum):
    RELEASE="RELEASE"; WARNING="WARNING"; BLOCKED="BLOCKED"; STALE="STALE"

@dataclass(frozen=True)
class GateCheck:
    name: str
    state: GateState
    detail: str=""

@dataclass(frozen=True)
class ReleaseGateResult:
    state: GateState
    checks: tuple[GateCheck,...]=field(default_factory=tuple)
    @property
    def releasable(self): return self.state is GateState.RELEASE

def evaluate_release_gate(*, feature_valid=True, topology_valid=True,
    dimensions_valid=True, tolerance_valid=True, assembly_clear=True,
    manufacturable=True, machine_envelope_ok=True, toolpath_valid=True,
    downstream_stale=False):
    checks=(
      GateCheck("feature",GateState.RELEASE if feature_valid else GateState.BLOCKED),
      GateCheck("topology",GateState.RELEASE if topology_valid else GateState.BLOCKED),
      GateCheck("dimensions",GateState.RELEASE if dimensions_valid else GateState.BLOCKED),
      GateCheck("tolerance",GateState.RELEASE if tolerance_valid else GateState.WARNING),
      GateCheck("assembly",GateState.RELEASE if assembly_clear else GateState.BLOCKED),
      GateCheck("manufacturability",GateState.RELEASE if manufacturable else GateState.BLOCKED),
      GateCheck("machine-envelope",GateState.RELEASE if machine_envelope_ok else GateState.BLOCKED),
      GateCheck("toolpath",GateState.RELEASE if toolpath_valid else GateState.BLOCKED),
    )
    if any(c.state is GateState.BLOCKED for c in checks): state=GateState.BLOCKED
    elif downstream_stale: state=GateState.STALE
    elif any(c.state is GateState.WARNING for c in checks): state=GateState.WARNING
    else: state=GateState.RELEASE
    return ReleaseGateResult(state,checks)
