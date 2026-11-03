"""UNG-CAD Group 1: parametric mechanical and architectural foundation.

Pure-Python models with deterministic validation. These are conceptual geometry,
BOM and constraint primitives, not certified engineering calculations or BIM.
"""
from dataclasses import dataclass, field
from math import isfinite, pi
from typing import Sequence

def positive(name, value):
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return value

@dataclass(frozen=True)
class Solid:
    kind: str
    parameters: dict
    def volume_mm3(self):
        p=self.parameters
        if self.kind=="box":
            return positive("width",p["width"])*positive("depth",p["depth"])*positive("height",p["height"])
        if self.kind=="cylinder":
            return pi*positive("radius",p["radius"])**2*positive("height",p["height"])
        if self.kind=="extrusion":
            return positive("area",p["area_mm2"])*positive("length",p["length"])
        raise ValueError("Unsupported solid")
    def estimate_mass_g(self,density_g_cm3):
        return self.volume_mm3()/1000*positive("density",density_g_cm3)

@dataclass(frozen=True)
class Constraint:
    kind: str
    actual: float
    target: float
    tolerance: float = 0.01
    def satisfied(self):
        if self.kind not in {"distance","length","radius","angle","equal"}:
            raise ValueError("Unknown constraint")
        if not all(isfinite(v) for v in (self.actual,self.target,self.tolerance)) or self.tolerance < 0:
            raise ValueError("Invalid constraint")
        return abs(self.actual-self.target)<=self.tolerance

@dataclass(frozen=True)
class Component:
    part_number: str
    solid: Solid
    material: str
    quantity: int=1
    def __post_init__(self):
        if not self.part_number or not self.material or type(self.quantity) is not int or self.quantity<1:
            raise ValueError("Invalid component")

@dataclass
class Assembly:
    name: str
    components: list[Component]=field(default_factory=list)
    def bill_of_materials(self):
        result={}
        for c in self.components:
            key=(c.part_number,c.material)
            if key in result and result[key]["solid"] != c.solid:
                raise ValueError("Conflicting part definitions")
            if key not in result:
                result[key]={"part_number":c.part_number,"material":c.material,"quantity":0,"solid":c.solid}
            result[key]["quantity"]+=c.quantity
        return list(result.values())
    def total_volume_mm3(self):
        return sum(c.solid.volume_mm3()*c.quantity for c in self.components)

@dataclass(frozen=True)
class Room:
    name: str
    width_mm: float
    length_mm: float
    height_mm: float
    def area_m2(self):
        return positive("width",self.width_mm)*positive("length",self.length_mm)/1_000_000
    def volume_m3(self):
        return self.area_m2()*positive("height",self.height_mm)/1000

@dataclass
class FloorPlan:
    name: str
    rooms: list[Room]=field(default_factory=list)
    def gross_room_area_m2(self):
        return sum(room.area_m2() for room in self.rooms)
    def room_schedule(self):
        return [{"name":r.name,"area_m2":r.area_m2(),"volume_m3":r.volume_m3()} for r in self.rooms]

@dataclass(frozen=True)
class Connection:
    a: str
    b: str
    kind: str
    def __post_init__(self):
        if self.kind not in {"fixed","hinge","slider"} or not self.a or not self.b or self.a==self.b:
            raise ValueError("Invalid assembly connection")

def validate_connections(assembly: Assembly, connections: Sequence[Connection]):
    ids={c.part_number for c in assembly.components}
    errors=[]
    for c in connections:
        if c.a not in ids or c.b not in ids:
            errors.append(f"Missing component: {c.a} or {c.b}")
    return errors
