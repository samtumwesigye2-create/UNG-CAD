"""Manufacturing-aware typed cutout geometry and validation."""
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any

class CADValidationError(Exception):
    pass

@dataclass(frozen=True)
class Vector2D:
    x_mm: float
    y_mm: float

@dataclass(frozen=True)
class Countersink:
    outer_diameter_mm: float
    angle_deg: float

@dataclass(frozen=True)
class MountingHole:
    offset_x_mm: float
    offset_y_mm: float
    diameter_mm: float
    countersink: Optional[Countersink]=None

@dataclass(frozen=True)
class CustomSegment:
    start_idx: int
    end_idx: int
    type: str
    arc_bulge: float=0.0
    control_points: List[Tuple[float,float]]=field(default_factory=list)

@dataclass(frozen=True)
class ArbitraryGeometry:
    vertices: List[Tuple[float,float]]
    segments: List[CustomSegment]

@dataclass
class CutoutComponent:
    component_id: str
    type: str
    position: Vector2D
    rotation: float
    clearance_mm: float
    depth_mm: float
    tolerance_profile: str
    mounting_holes: List[MountingHole]=field(default_factory=list)
    dimensions: Dict[str,Any]=field(default_factory=dict)
    custom_geometry: Optional[ArbitraryGeometry]=None

    def __post_init__(self):
        self.validate_manufacturing_constraints()

    def validate_manufacturing_constraints(self) -> bool:
        if self.depth_mm<=0 and self.depth_mm!=-1:
            raise CADValidationError(f"Invalid depth ({self.depth_mm}mm). Must be positive or -1 for through-hole.")
        if self.clearance_mm<0: raise CADValidationError("Clearance cannot be negative.")
        if self.type=="circular" and float(self.dimensions.get("diameter_mm",0))<=0:
            raise CADValidationError("Circular cutout requires positive diameter_mm.")
        if self.type in {"rectangular","usb_c","ethernet"}:
            if float(self.dimensions.get("width_mm",0))<=0 or float(self.dimensions.get("height_mm",0))<=0:
                raise CADValidationError("Rectangular cutout requires positive width/height.")
        if self.tolerance_profile=="cnc_mill_aluminum" and self.type in {"rectangular","usb_c","ethernet"}:
            r=float(self.dimensions.get("corner_radius_mm",0))
            if r<1.0: raise CADValidationError(f"Corner radius ({r}mm) violates configured 2mm-tool minimum radius of 1.0mm.")
        if self.type=="arbitrary_custom":
            if not self.custom_geometry or len(self.custom_geometry.vertices)<3:
                raise CADValidationError("Arbitrary cutout requires at least three vertices.")
            segs=self.custom_geometry.segments
            if len(segs)<3: raise CADValidationError("Arbitrary cutout requires at least three segments.")
            n=len(self.custom_geometry.vertices)
            for s in segs:
                if not (0<=s.start_idx<n and 0<=s.end_idx<n): raise CADValidationError("Segment index out of range.")
                if s.type not in {"linear","arc","bezier"}: raise CADValidationError("Unsupported segment type.")
                if s.type=="bezier" and not 1<=len(s.control_points)<=2: raise CADValidationError("Bezier requires one or two control points.")
            for a,b in zip(segs,segs[1:]):
                if a.end_idx!=b.start_idx: raise CADValidationError("Custom boundary contains a disconnected segment.")
            if segs[-1].end_idx!=segs[0].start_idx: raise CADValidationError("Custom boundary must form a closed loop.")
        for h in self.mounting_holes:
            if h.diameter_mm<=0: raise CADValidationError("Mounting-hole diameter must be positive.")
            if h.countersink:
                if h.countersink.outer_diameter_mm<=h.diameter_mm: raise CADValidationError("Countersink must exceed hole diameter.")
                if h.countersink.angle_deg not in {82,90,120}: raise CADValidationError("Unsupported countersink angle.")
        return True

    def calculate_compensated_bounding_box(self) -> Tuple[float,float]:
        d=2*self.clearance_mm
        if self.type=="circular":
            v=float(self.dimensions.get("diameter_mm",0))+d; return v,v
        if self.type in {"rectangular","usb_c","ethernet"}:
            return float(self.dimensions.get("width_mm",0))+d,float(self.dimensions.get("height_mm",0))+d
        if self.type=="arbitrary_custom" and self.custom_geometry:
            xs=[v[0] for v in self.custom_geometry.vertices];ys=[v[1] for v in self.custom_geometry.vertices]
            return max(xs)-min(xs)+d,max(ys)-min(ys)+d
        return 0.0,0.0
