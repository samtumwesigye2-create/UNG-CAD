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
