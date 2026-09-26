"""Immutable parametric feature timeline with bounded-error circle tessellation."""
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any

class ToleranceExceededError(ValueError):
    """Requested chord tolerance exceeds configured tessellation capacity."""

@dataclass(frozen=True)
class Point3D:
    x: float
    y: float
    z: float
    def to_array(self) -> List[float]:
        return [self.x,self.y,self.z]

@dataclass(frozen=True)
class Vector3D:
    x: float
    y: float
    z: float
    def normalize(self) -> "Vector3D":
        mag=math.hypot(self.x,self.y,self.z)
        if mag < 1e-12:
            raise ValueError("Circle normal must be non-zero.")
        return Vector3D(self.x/mag,self.y/mag,self.z/mag)
    def cross(self,other:"Vector3D")->"Vector3D":
        return Vector3D(self.y*other.z-self.z*other.y,self.z*other.x-self.x*other.z,self.x*other.y-self.y*other.x)

@dataclass(frozen=True)
class ParametricCircle:
    center: Point3D
    radius: float
    normal: Vector3D=field(default_factory=lambda:Vector3D(0,0,1))
    def __post_init__(self):
        if self.radius<=0: raise ValueError(f"Circle radius must be strictly positive. Got: {self.radius}")
        object.__setattr__(self,"normal",self.normal.normalize())
    def tessellate(self,chord_tolerance:float,max_segments:int=10000)->List[Dict[str,float]]:
        if chord_tolerance<=0: raise ValueError(f"Chord tolerance must be strictly positive. Got: {chord_tolerance}")
        if max_segments<16: raise ValueError("max_segments must be at least 16.")
        c=max(-1.0,min(1.0,1.0-chord_tolerance/self.radius))
        step=2*math.acos(c)
        if step<=1e-12:
            raise ToleranceExceededError(f"Requested tolerance ({chord_tolerance} mm) requires an infinite or near-infinite number of segments for radius {self.radius} mm.")
        segments=max(16,int(math.ceil(2*math.pi/step)))
        if segments>max_segments:
            raise ToleranceExceededError(f"Requested tolerance ({chord_tolerance} mm) requires {segments} segments, which exceeds the configured maximum safety limit of {max_segments} segments.")
        n=self.normal
        ref=Vector3D(1,0,0) if abs(n.x)<.9 else Vector3D(0,1,0)
        u=n.cross(ref).normalize();v=n.cross(u).normalize()
        return [{"x":self.center.x+self.radius*(math.cos(t)*u.x+math.sin(t)*v.x),
                 "y":self.center.y+self.radius*(math.cos(t)*u.y+math.sin(t)*v.y),
                 "z":self.center.z+self.radius*(math.cos(t)*u.z+math.sin(t)*v.z)}
                for t in (2*math.pi*i/segments for i in range(segments))]

class PrecisionGeometryEngine:
    EPSILON=1e-12
    @classmethod
    def _clamp_zero(cls,v): return 0.0 if abs(v)<cls.EPSILON else v
    @classmethod
    def apply_rotation_z(cls,circle,angle_degrees):
        a=math.radians(angle_degrees);c=cls._clamp_zero(math.cos(a));s=cls._clamp_zero(math.sin(a))
        return ParametricCircle(Point3D(circle.center.x*c-circle.center.y*s,circle.center.x*s+circle.center.y*c,circle.center.z),circle.radius,Vector3D(circle.normal.x*c-circle.normal.y*s,circle.normal.x*s+circle.normal.y*c,circle.normal.z))
    @classmethod
    def apply_scaling(cls,circle,scale_factor):
        if scale_factor<=0: raise ValueError(f"Scaling factor must be positive. Got: {scale_factor}")
        p=circle.center
        return ParametricCircle(Point3D(p.x*scale_factor,p.y*scale_factor,p.z*scale_factor),circle.radius*scale_factor,circle.normal)
    @classmethod
    def update_radius(cls,circle,new_radius):
        return ParametricCircle(circle.center,new_radius,circle.normal)

class UNGCadFeatureTimeline:
    QUALITY_TOLERANCES={"ui":0.05,"export":0.001}
    def __init__(self): self.registry:Dict[str,ParametricCircle]={}
    def add_circle(self,entity_id:str,circle:ParametricCircle):
        if not entity_id: raise ValueError("entity_id is required.")
        if entity_id in self.registry: raise KeyError(f"Entity identity token {entity_id} already exists.")
        self.registry[entity_id]=circle
        return circle
    def process_api_action(self,entity_id:str,action:str,value:float,target_quality:str)->Dict[str,Any]:
        if entity_id not in self.registry: raise KeyError(f"Entity identity token {entity_id} missing from core timeline context.")
        if target_quality not in self.QUALITY_TOLERANCES: raise ValueError(f"Invalid quality target profile '{target_quality}'. Must be one of: {list(self.QUALITY_TOLERANCES)}")
        old=self.registry[entity_id]
        if action=="rotate_z": new=PrecisionGeometryEngine.apply_rotation_z(old,value)
        elif action=="scale": new=PrecisionGeometryEngine.apply_scaling(old,value)
        elif action=="update_radius": new=PrecisionGeometryEngine.update_radius(old,value)
        else: raise NotImplementedError(f"Action '{action}' is unmapped.")
        # Commit only after the new immutable entity has validated successfully.
        self.registry[entity_id]=new
        points=new.tessellate(self.QUALITY_TOLERANCES[target_quality])
        return {"entity_id":entity_id,"status":"synchronized","quality":target_quality,"meta":{"radius":new.radius,"center":new.center.to_array(),"normal":[new.normal.x,new.normal.y,new.normal.z]},"vertices":points}


# Extended analytic primitives. Parameters remain authoritative; meshes are derived.
@dataclass(frozen=True)
class ParametricArc:
    center: Point3D; radius: float; start_deg: float; end_deg: float
    normal: Vector3D=field(default_factory=lambda:Vector3D(0,0,1))
    def __post_init__(self):
        if self.radius<=0: raise ValueError("Arc radius must be positive.")
        object.__setattr__(self,"normal",self.normal.normalize())
    def tessellate(self,tol=.05,max_segments=10000):
        if tol<=0: raise ValueError("Tolerance must be positive.")
        sweep=math.radians(self.end_deg-self.start_deg)
        if abs(sweep)<1e-12:return []
        step=2*math.acos(max(-1,min(1,1-tol/self.radius)))
        if step<=1e-12: raise ToleranceExceededError("Arc tolerance exceeds tessellation capacity.")
        n=max(2,int(math.ceil(abs(sweep)/step))+1)
        if n>max_segments: raise ToleranceExceededError("Arc segment safety limit exceeded.")
        N=self.normal;ref=Vector3D(1,0,0) if abs(N.x)<.9 else Vector3D(0,1,0);u=N.cross(ref).normalize();v=N.cross(u).normalize()
        out=[]
        for i in range(n):
            t=math.radians(self.start_deg)+(sweep*i/(n-1));ct,st=math.cos(t),math.sin(t)
            out.append({"x":self.center.x+self.radius*(ct*u.x+st*v.x),"y":self.center.y+self.radius*(ct*u.y+st*v.y),"z":self.center.z+self.radius*(ct*u.z+st*v.z)})
        return out

def _ring(center,r,z,tol):
    return ParametricCircle(Point3D(center.x,center.y,center.z+z),r).tessellate(tol)

@dataclass(frozen=True)
class ParametricCylinder:
    center: Point3D; radius: float; height: float
    def __post_init__(self):
        if self.radius<=0 or self.height<=0: raise ValueError("Cylinder radius and height must be positive.")
    def tessellate(self,tol=.05):
        a=_ring(self.center,self.radius,-self.height/2,tol);b=_ring(self.center,self.radius,self.height/2,tol);return {"rings":[a,b],"closed":True}

@dataclass(frozen=True)
class ParametricSphere:
    center: Point3D; radius: float
    def __post_init__(self):
        if self.radius<=0: raise ValueError("Sphere radius must be positive.")
    def tessellate(self,tol=.05,max_segments=10000):
        equator=ParametricCircle(self.center,self.radius).tessellate(tol,max_segments);lon=len(equator);lat=max(8,lon//2)
        if lon*lat>max_segments*8: raise ToleranceExceededError("Sphere tessellation safety limit exceeded.")
        rings=[]
        for j in range(1,lat):
            phi=-math.pi/2+math.pi*j/lat;r=self.radius*math.cos(phi);z=self.radius*math.sin(phi)
            rings.append([{"x":self.center.x+r*math.cos(2*math.pi*i/lon),"y":self.center.y+r*math.sin(2*math.pi*i/lon),"z":self.center.z+z} for i in range(lon)])
        return {"rings":rings,"poles":[{"x":self.center.x,"y":self.center.y,"z":self.center.z-self.radius},{"x":self.center.x,"y":self.center.y,"z":self.center.z+self.radius}]}

@dataclass(frozen=True)
class ParametricHole:
    center: Point3D; radius: float; depth: float
    def __post_init__(self):
        if self.radius<=0 or self.depth<=0: raise ValueError("Hole radius and depth must be positive.")
    def tessellate(self,tol=.05): return ParametricCylinder(self.center,self.radius,self.depth).tessellate(tol)

@dataclass(frozen=True)
class ParametricExtrusion:
    profile: tuple; height: float
    def __post_init__(self):
        if len(self.profile)<3 or self.height==0: raise ValueError("Extrusion requires >=3 profile points and nonzero height.")
    def tessellate(self):
        base=[{"x":float(p[0]),"y":float(p[1]),"z":0.0} for p in self.profile];top=[{**p,"z":self.height} for p in base]
        return {"rings":[base,top],"closed":True}

@dataclass(frozen=True)
class ParametricRevolve:
    profile: tuple; angle_deg: float=360.0
    def __post_init__(self):
        if len(self.profile)<2 or self.angle_deg==0: raise ValueError("Revolve requires >=2 profile points and nonzero angle.")
    def tessellate(self,segments=64):
        rings=[]
        for i in range(segments+1):
            a=math.radians(self.angle_deg*i/segments);ca,sa=math.cos(a),math.sin(a)
            rings.append([{"x":float(r)*ca,"y":float(r)*sa,"z":float(z)} for r,z in self.profile])
        return {"rings":rings,"closed":abs(self.angle_deg)>=360}

def tessellated_surface_triangles(data):
    """Convert ring-based derived geometry to manufacturing triangles.

    Supports unequal ring sizes (including sphere poles) and optional planar
    end caps. Open shells remain valid when closed=False.
    """
    rings=[list(r) for r in data.get("rings",[]) if r]
    tris=[]
    def tri(a,b,c):
        # Reject zero-area triangles before they reach STL/slicer.
        ab=(b["x"]-a["x"],b["y"]-a["y"],b["z"]-a["z"])
        ac=(c["x"]-a["x"],c["y"]-a["y"],c["z"]-a["z"])
        cr=(ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0])
        if math.hypot(*cr)>1e-12: tris.append([a,b,c])
    for a,b in zip(rings,rings[1:]):
        na,nb=len(a),len(b)
        if na==nb:
            for i in range(na):
                j=(i+1)%na;tri(a[i],b[i],b[j]);tri(a[i],b[j],a[j])
        elif na==1:
            for i in range(nb):tri(a[0],b[i],b[(i+1)%nb])
        elif nb==1:
            for i in range(na):tri(a[i],b[0],a[(i+1)%na])
        else:
            # General loft: normalized index mapping.
            n=max(na,nb)
            for i in range(n):
                a0=a[(i*na)//n%na];a1=a[((i+1)*na)//n%na]
                b0=b[(i*nb)//n%nb];b1=b[((i+1)*nb)//n%nb]
                tri(a0,b0,b1);tri(a0,b1,a1)
    if data.get("closed") and rings:
        for ring,reverse in ((rings[0],True),(rings[-1],False)):
            if len(ring)>=3:
                center={"x":sum(p["x"] for p in ring)/len(ring),"y":sum(p["y"] for p in ring)/len(ring),"z":sum(p["z"] for p in ring)/len(ring)}
                for i in range(len(ring)):
                    j=(i+1)%len(ring)
                    tri(center,ring[j],ring[i]) if reverse else tri(center,ring[i],ring[j])
    return tris

def sphere_manufacturing_triangles(sphere, tol=.05, max_segments=10000):
    """Pole-safe closed sphere tessellation for STL/manufacturing."""
    equator=ParametricCircle(sphere.center,sphere.radius).tessellate(tol,max_segments)
    lon=len(equator);lat=max(8,lon//2)
    south={"x":sphere.center.x,"y":sphere.center.y,"z":sphere.center.z-sphere.radius}
    north={"x":sphere.center.x,"y":sphere.center.y,"z":sphere.center.z+sphere.radius}
    rings=[[south]]
    for j in range(1,lat):
        phi=-math.pi/2+math.pi*j/lat;r=sphere.radius*math.cos(phi);z=sphere.center.z+sphere.radius*math.sin(phi)
        rings.append([{"x":sphere.center.x+r*math.cos(2*math.pi*i/lon),"y":sphere.center.y+r*math.sin(2*math.pi*i/lon),"z":z} for i in range(lon)])
    rings.append([north])
    return tessellated_surface_triangles({"rings":rings,"closed":False})

@dataclass(frozen=True)
class FeatureNode:
    id: str
    kind: str
    entity_id: str
    params: dict
    parents: tuple=()
    revision: int=1

class ParametricDependencyGraph:
    """Dependency-aware regeneration graph for non-destructive CAD history."""
    def __init__(self):
        self.nodes: Dict[str,FeatureNode]={}
        self.children: Dict[str,set]={}
    def add(self,node:FeatureNode):
        if node.id in self.nodes: raise KeyError(f"Feature {node.id} already exists.")
        missing=[p for p in node.parents if p not in self.nodes]
        if missing: raise KeyError(f"Missing parent features: {missing}")
        self.nodes[node.id]=node
        for p in node.parents:self.children.setdefault(p,set()).add(node.id)
        self._assert_acyclic()
        return node
    def replace(self,node_id:str,params:dict):
        old=self.nodes[node_id]
        self.nodes[node_id]=FeatureNode(old.id,old.kind,old.entity_id,dict(params),old.parents,old.revision+1)
        return self.regeneration_order(node_id)
    def regeneration_order(self,node_id:str):
        if node_id not in self.nodes: raise KeyError(node_id)
        seen=set();out=[]
        def walk(n):
            if n in seen:return
            seen.add(n);out.append(n)
            for ch in sorted(self.children.get(n,())):walk(ch)
        walk(node_id);return out
    def _assert_acyclic(self):
        visiting=set();done=set()
        def dfs(n):
            if n in visiting: raise ValueError("Feature dependency cycle detected.")
            if n in done:return
            visiting.add(n)
            for ch in self.children.get(n,()):dfs(ch)
            visiting.remove(n);done.add(n)
        for n in self.nodes:dfs(n)
    def serialize(self):
        return [{"id":n.id,"kind":n.kind,"entity_id":n.entity_id,"params":n.params,"parents":list(n.parents),"revision":n.revision} for n in self.nodes.values()]
