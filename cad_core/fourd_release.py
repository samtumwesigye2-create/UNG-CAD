"""Time-aware engineering state and 4D manufacturing release evidence."""
from dataclasses import dataclass
from enum import Enum
from .release_evidence import GateEvidence, evidence_check, aggregate_evidence

class TimeState(str,Enum):
    VALID="VALID"; STALE="STALE"; INVALID="INVALID"

@dataclass(frozen=True)
class TimelineState:
    time_s: float
    duration_s: float
    state: TimeState=TimeState.VALID
    source: str="4D timeline"
    detail: str=""
    @property
    def in_range(self): return 0.0 <= self.time_s <= self.duration_s

@dataclass(frozen=True)
class FourDReleaseResult:
    state: object
    checks: tuple
    @property
    def releasable(self): return getattr(self.state,"value",self.state)=="RELEASE"

def evaluate_4d_release(*,timeline:TimelineState, material_calibrated:bool,
                        stimulus_validated:bool, toolpath_valid:bool,
                        machine_profile_valid:bool):
    evidence=(
      ("timeline",GateEvidence(timeline.source,True,timeline.state is TimeState.VALID and timeline.in_range,
                               timeline.detail or f"t={timeline.time_s:g}s / {timeline.duration_s:g}s")),
      ("material-response",GateEvidence("4D material calibration",True,material_calibrated,
                                       "material/process response must be calibrated")),
      ("stimulus",GateEvidence("4D stimulus validation",True,stimulus_validated,
                               "heat/moisture/light stimulus validation")),
      ("toolpath",GateEvidence("4D transformed toolpath",True,toolpath_valid,
                               "post-transform toolpath validation")),
      ("machine-envelope",GateEvidence("machine profile",True,machine_profile_valid,
                                       "machine limits after 4D transformation")),
    )
    checks=tuple(evidence_check(name,e) for name,e in evidence)
    return FourDReleaseResult(aggregate_evidence(checks),checks)
