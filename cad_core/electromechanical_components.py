"""Electromechanical component metadata bound to CAD object identities."""
from dataclasses import dataclass, field
from enum import Enum
from .electromechanical import Connection, winding_graph

class ComponentKind(str, Enum):
    STATOR="stator"
    ROTOR="rotor"
    WINDING="winding"
    MOTOR="motor"
    GENERATOR="generator"

@dataclass
class ElectromechanicalComponent:
    cad_object_id: str
    kind: ComponentKind
    name: str
    material: str|None=None
    metadata: dict=field(default_factory=dict)

@dataclass
class WindingComponent(ElectromechanicalComponent):
    connection: Connection=Connection.DELTA
    turns: int|None=None
    resistance_ohm: float|None=None
    phase_count: int=3
    def topology(self):
        if self.phase_count != 3: raise ValueError("current winding topology supports three phases")
        return winding_graph(self.connection)

@dataclass
class MachineAssembly:
    name: str
    mode: ComponentKind
    components: list[ElectromechanicalComponent]=field(default_factory=list)
    def __post_init__(self):
        if self.mode not in (ComponentKind.MOTOR,ComponentKind.GENERATOR):
            raise ValueError("machine mode must be motor or generator")
    def add(self, component):
        self.components.append(component); return component
    def by_kind(self, kind):
        kind=ComponentKind(kind)
        return [c for c in self.components if c.kind is kind]
    def validate(self):
        issues=[]
        if not self.by_kind(ComponentKind.STATOR): issues.append("missing stator")
        if not self.by_kind(ComponentKind.ROTOR): issues.append("missing rotor")
        if not self.by_kind(ComponentKind.WINDING): issues.append("missing winding")
        return {"valid":not issues,"issues":issues,"component_count":len(self.components)}
