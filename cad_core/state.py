from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Dict, List
from uuid import uuid4
import time

class StateKind(str, Enum):
    OBSERVED="observed"
    PREDICTED="predicted"
    SIMULATED="simulated"

@dataclass(frozen=True)
class CADState:
    object_id: str
    kind: StateKind
    values: Dict[str, Any]
    source: str
    confidence: float = 1.0
    timestamp: float = field(default_factory=time.time)
    state_id: str = field(default_factory=lambda: str(uuid4()))
    provenance: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

class StateStore:
    """Keeps authoritative observations isolated from predictions/simulations."""
    def __init__(self):
        self._history: List[CADState] = []

    def append(self, state: CADState) -> CADState:
        self._history.append(state)
        return state

    def history(self, object_id: str | None = None, kind: StateKind | None = None) -> List[CADState]:
        return [s for s in self._history if (object_id is None or s.object_id == object_id) and (kind is None or s.kind == kind)]

    def latest_observed(self, object_id: str) -> CADState | None:
        rows=self.history(object_id, StateKind.OBSERVED)
        return max(rows, key=lambda s:s.timestamp) if rows else None

    def promote_to_observed(self, state: CADState, *, approved_by: str, source: str) -> CADState:
        if state.kind == StateKind.OBSERVED:
            return self.append(state)
        raise ValueError("Predicted/simulated state cannot be promoted to observed; ingest a real measurement instead.")
