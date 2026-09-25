"""Dependency-aware engineering state propagation for CAD-linked analyses."""
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Any

class EngineeringState(str,Enum):
    VALID="VALID"; STALE="STALE"; INVALID="INVALID"

@dataclass
class EngineeringResult:
    artifact_id: str
    domain: str
    state: EngineeringState = EngineeringState.STALE
    value: Any = None
    revision: int = 0
    error: str|None = None

class EngineeringDependencyEngine:
    def __init__(self):
        self._deps={}
        self._results={}
        self._solvers={}
    def register(self,artifact_id,domain,solver:Callable[[],Any],depends_on=()):
        key=(artifact_id,domain)
        self._results[key]=EngineeringResult(artifact_id,domain)
        self._solvers[key]=solver
        for source in depends_on: self._deps.setdefault(source,set()).add(key)
        return self._results[key]
    def invalidate(self,source_id):
        changed=[]
        for key in self._deps.get(source_id,set()):
            r=self._results[key]; r.state=EngineeringState.STALE; changed.append(r)
        return tuple(changed)
    def recalculate(self,artifact_id,domain):
        key=(artifact_id,domain); r=self._results[key]
        try:
            r.value=self._solvers[key](); r.state=EngineeringState.VALID; r.error=None; r.revision+=1
        except Exception as e:
            r.value=None; r.state=EngineeringState.INVALID; r.error=str(e); r.revision+=1
        return r
    def recalculate_stale(self):
        return tuple(self.recalculate(*key) for key,r in self._results.items() if r.state is EngineeringState.STALE)
    def result(self,artifact_id,domain): return self._results[(artifact_id,domain)]
