"""UNG-GEOMETRY v0.2 integrated kernel for UNG-CAD.

This module intentionally separates deterministic geometry/data contracts from
the UNG-CAD workflow/UI layer.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from math import sqrt
from typing import Any, Dict, List, Optional, Set, Tuple

__version__ = "0.2.0"
EPS = 1e-9

@dataclass(frozen=True, slots=True)
class Vec3:
    x: float
    y: float
    z: float
    def __add__(self,o): return Vec3(self.x+o.x,self.y+o.y,self.z+o.z)
    def __sub__(self,o): return Vec3(self.x-o.x,self.y-o.y,self.z-o.z)
    def __mul__(self,s:float): return Vec3(self.x*s,self.y*s,self.z*s)
    __rmul__ = __mul__
    def __truediv__(self,s:float): return Vec3(self.x/s,self.y/s,self.z/s)
    def dot(self,o)->float: return self.x*o.x+self.y*o.y+self.z*o.z
    def cross(self,o): return Vec3(self.y*o.z-self.z*o.y,self.z*o.x-self.x*o.z,self.x*o.y-self.y*o.x)
    def length(self)->float: return sqrt(self.dot(self))
    def normalized(self):
        n=self.length()
        if n<=EPS: raise ValueError("zero vector")
        return self/n

@dataclass(frozen=True, slots=True)
class Ray3:
    origin: Vec3
    direction: Vec3
    def point(self,t:float): return self.origin+self.direction*t

@dataclass(frozen=True, slots=True)
class Triangle:
    a: Vec3
    b: Vec3
    c: Vec3
    @property
    def area(self): return .5*(self.b-self.a).cross(self.c-self.a).length()

@dataclass(frozen=True, slots=True)
class AABB:
    minimum: Vec3
    maximum: Vec3
    @classmethod
    def from_points(cls, points):
        p=list(points)
        if not p: raise ValueError("points required")
        return cls(
            Vec3(min(v.x for v in p),min(v.y for v in p),min(v.z for v in p)),
            Vec3(max(v.x for v in p),max(v.y for v in p),max(v.z for v in p)),
        )

class Mesh:
    def __init__(self, vertices, faces):
        self.vertices=list(vertices)
        self.faces=list(faces)
    @property
    def bounds(self): return AABB.from_points(self.vertices)
    @property
    def surface_area(self):
        return sum(Triangle(self.vertices[a],self.vertices[b],self.vertices[c]).area for a,b,c in self.faces)
    def validate(self):
        edges=Counter(); degenerate=0
        for a,b,c in self.faces:
            if len({a,b,c})<3 or Triangle(self.vertices[a],self.vertices[b],self.vertices[c]).area<=EPS:
                degenerate+=1
            for x,y in ((a,b),(b,c),(c,a)):
                edges[tuple(sorted((x,y)))]+=1
        boundary=sum(n==1 for n in edges.values())
        nonmanifold=sum(n>2 for n in edges.values())
        return {
            "vertices":len(self.vertices),
            "faces":len(self.faces),
            "degenerate_faces":degenerate,
            "boundary_edges":boundary,
            "nonmanifold_edges":nonmanifold,
            "watertight":degenerate==0 and boundary==0 and nonmanifold==0,
        }
    def signed_volume(self):
        return sum(self.vertices[a].dot(self.vertices[b].cross(self.vertices[c]))/6 for a,b,c in self.faces)

def ray_triangle_intersection(ray:Ray3, tri:Triangle):
    e1=tri.b-tri.a; e2=tri.c-tri.a
    h=ray.direction.cross(e2); det=e1.dot(h)
    if abs(det)<=EPS: return None
    inv=1/det; s=ray.origin-tri.a; u=inv*s.dot(h)
    if u<0 or u>1: return None
    q=s.cross(e1); v=inv*ray.direction.dot(q)
    if v<0 or u+v>1: return None
    t=inv*e2.dot(q)
    if t<0: return None
    return {"distance":t,"point":ray.point(t),"barycentric":(1-u-v,u,v)}

@dataclass
class BRepVertex: id: str
@dataclass
class BRepEdge: id: str; start: str; end: str
@dataclass
class BRepLoop: id: str; edges: List[str]=field(default_factory=list)
@dataclass
class BRepFace: id: str; loops: List[str]=field(default_factory=list); surface_type: str="unknown"
@dataclass
class BRepShell: id: str; faces: List[str]=field(default_factory=list); closed: bool=False
@dataclass
class BRepSolid: id: str; shells: List[str]=field(default_factory=list)

class FeatureType(str, Enum):
    SKETCH="sketch"; EXTRUDE="extrude"; REVOLVE="revolve"; SWEEP="sweep"; LOFT="loft"
    SHELL="shell"; DRAFT="draft"; RIB="rib"; HOLE="hole"; PATTERN="pattern"
    MIRROR="mirror"; CHAMFER="chamfer"; FILLET="fillet"

@dataclass
class Feature:
    id: str
    kind: FeatureType
    params: Dict[str,Any]=field(default_factory=dict)
    dependencies: List[str]=field(default_factory=list)
    suppressed: bool=False

@dataclass
class FeatureHistory:
    features: List[Feature]=field(default_factory=list)
    def append(self, feature:Feature): self.features.append(feature)
    def downstream(self, feature_id:str):
        i=next(i for i,f in enumerate(self.features) if f.id==feature_id)
        return self.features[i+1:]

class ConstraintType(str, Enum):
    COINCIDENT="coincident"; PARALLEL="parallel"; PERPENDICULAR="perpendicular"
    TANGENT="tangent"; CONCENTRIC="concentric"; HORIZONTAL="horizontal"; VERTICAL="vertical"
    EQUAL="equal"; DISTANCE="distance"; ANGLE="angle"; RADIUS="radius"

@dataclass
class Constraint:
    kind: ConstraintType
    entity_a: str
    entity_b: Optional[str]=None
    value: Optional[float]=None
    driving: bool=True

class JointType(str, Enum):
    FIXED="fixed"; REVOLUTE="revolute"; PRISMATIC="prismatic"; BALL="ball"

@dataclass
class Joint:
    name: str
    kind: JointType
    parent: str
    child: str
    axis: Vec3=Vec3(0,0,1)
    limits: Optional[Tuple[float,float]]=None

@dataclass
class Assembly:
    components: List[str]=field(default_factory=list)
    joints: List[Joint]=field(default_factory=list)
    def add_component(self,name:str):
        if name not in self.components: self.components.append(name)
    def add_joint(self,joint:Joint):
        if joint.parent not in self.components or joint.child not in self.components:
            raise ValueError("joint components must exist in assembly")
        self.joints.append(joint)

@dataclass(frozen=True)
class TolerancePolicy:
    linear: float=1e-6
    angular: float=1e-8
    merge: float=1e-6
    sliver_area: float=1e-10

DEFAULT_TOLERANCE=TolerancePolicy()

class Continuity(IntEnum):
    G0=0; G1=1; G2=2

def classify_continuity(position_error:float,tangent_error:float,curvature_error:float,
                        pos_tol=1e-6,tangent_tol=1e-5,curvature_tol=1e-4):
    if position_error>pos_tol: return None
    if tangent_error>tangent_tol: return Continuity.G0
    if curvature_error>curvature_tol: return Continuity.G1
    return Continuity.G2

class LengthUnit(str, Enum):
    MM="mm"; CM="cm"; M="m"; IN="in"; FT="ft"

_LENGTH_FACTORS={LengthUnit.MM:1.0,LengthUnit.CM:10.0,LengthUnit.M:1000.0,LengthUnit.IN:25.4,LengthUnit.FT:304.8}
def convert_length(value:float,src:LengthUnit,dst:LengthUnit)->float:
    return value*_LENGTH_FACTORS[src]/_LENGTH_FACTORS[dst]

@dataclass
class Material:
    name: str
    density_kg_m3: Optional[float]=None
    youngs_modulus_pa: Optional[float]=None
    yield_strength_pa: Optional[float]=None
    thermal_conductivity_w_mk: Optional[float]=None
    thermal_expansion_per_k: Optional[float]=None

class CheckStatus(str, Enum):
    VALID="valid"; WARNING="warning"; INVALID="invalid"; STALE="stale"

@dataclass
class CheckResult:
    name: str
    status: CheckStatus
    message: str=""

@dataclass
class GeometryIntegrityReport:
    checks: List[CheckResult]=field(default_factory=list)
    @property
    def status(self):
        if any(c.status==CheckStatus.INVALID for c in self.checks): return CheckStatus.INVALID
        if any(c.status==CheckStatus.STALE for c in self.checks): return CheckStatus.STALE
        if any(c.status==CheckStatus.WARNING for c in self.checks): return CheckStatus.WARNING
        return CheckStatus.VALID

class ArtifactState(str, Enum):
    CURRENT="current"; STALE="stale"

@dataclass
class Artifact:
    id: str
    kind: str
    revision: str
    dependencies: List[str]=field(default_factory=list)
    state: ArtifactState=ArtifactState.CURRENT

class DependencyGraph:
    def __init__(self): self.items: Dict[str,Artifact]={}
    def add(self,a:Artifact): self.items[a.id]=a
    def invalidate_downstream(self,changed_id:str):
        dirty={changed_id}
        changed=True
        while changed:
            changed=False
            for a in self.items.values():
                if a.id not in dirty and any(d in dirty for d in a.dependencies):
                    a.state=ArtifactState.STALE; dirty.add(a.id); changed=True
        return dirty

class ManufacturingMode(str, Enum):
    ADDITIVE="additive"; SUBTRACTIVE="subtractive"

@dataclass
class AdditiveSetup:
    layer_height_mm: float=.2
    infill_percent: float=20
    supports: bool=True
    slicer: str="orcaslicer"

@dataclass
class SubtractiveSetup:
    stock_mm: Tuple[float,float,float]=(0,0,0)
    wcs: str="G54"
    spindle_rpm: float=0
    coolant: str="off"
    operations: List[str]=field(default_factory=list)

@dataclass
class ManufacturingJob:
    id: str
    mode: ManufacturingMode
    source_revision: str
    machine_id: str
    additive: Optional[AdditiveSetup]=None
    subtractive: Optional[SubtractiveSetup]=None
    stale: bool=False

@dataclass
class MachineProfile:
    id: str
    kind: str
    controller: str
    work_envelope_mm: Tuple[float,float,float]
    axes: int=3
    capabilities: Set[str]=field(default_factory=set)

@dataclass
class PostprocessReport:
    controller: str
    valid: bool
    warnings: List[str]
    unsupported: List[str]

SUPPORTED_GCODE={
    "grbl":{"G0","G1","G2","G3","G4","M0","M3","M4","M5","M30"},
    "linuxcnc":{"G0","G1","G2","G3","G4","M3","M5","M6","M7","M8","M9","M30"},
    "haas":{"G0","G1","G2","G3","G4","M3","M5","M6","M8","M9","M30"},
}

def validate_gcode(lines:List[str],controller:str)->PostprocessReport:
    allowed=SUPPORTED_GCODE.get(controller,set())
    unsupported=[]
    for line in lines:
        token=line.strip().split(maxsplit=1)[0] if line.strip() else ""
        if token and token[0] in "GM" and token not in allowed:
            unsupported.append(token)
    return PostprocessReport(controller,not unsupported,[],sorted(set(unsupported)))

class ExchangeFormat(str, Enum):
    STEP="step"; IGES="iges"; STL="stl"; OBJ="obj"; THREE_MF="3mf"
    DXF="dxf"; SVG="svg"; PLY="ply"; GLTF="gltf"

@dataclass
class SyncPolicy:
    local_first: bool=True
    autosave_seconds: int=30
    cloud_enabled: bool=False
    private_server_url: Optional[str]=None
    encrypt_at_rest: bool=True

@dataclass
class ProvenanceEvent:
    operation: str
    source_ids: List[str]
    output_id: str
    params: Dict[str,Any]=field(default_factory=dict)

@dataclass
class HybridBody:
    representation: str
    body: Any

def hybrid_boolean(a:HybridBody,b:HybridBody,operation:str):
    raise NotImplementedError("exact B-Rep/mesh Boolean backend is not yet bound")
