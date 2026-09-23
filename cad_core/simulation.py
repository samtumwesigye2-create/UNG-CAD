from dataclasses import dataclass, field
from typing import Callable, List
from uuid import uuid4
from .state import CADState, StateKind

@dataclass
class SimulationRun:
    name: str
    run_id: str = field(default_factory=lambda: str(uuid4()))
    states: List[CADState] = field(default_factory=list)

    def step(self, base: CADState, transition: Callable[[dict],dict]) -> CADState:
        simulated=CADState(object_id=base.object_id, kind=StateKind.SIMULATED, values=transition(dict(base.values)), source=f"simulation:{self.run_id}", confidence=base.confidence, provenance={"base_state_id":base.state_id})
        self.states.append(simulated)
        return simulated
