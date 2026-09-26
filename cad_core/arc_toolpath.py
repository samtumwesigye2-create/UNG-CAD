"""Validated circular-arc G-code generation for supported machine profiles.

This module emits geometry/toolpath commands only. Temperature/start/end sequences
remain profile/filament responsibilities; they must not be guessed by CAD geometry.
"""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class ArcCircle:
    center_x: float
    center_y: float
    radius: float
    z: float
    extrusion: float
    feed_mm_min: float=2400.0
    clockwise: bool=True

def circle_length(radius: float) -> float:
    if radius <= 0: raise ValueError("radius must be positive")
    return 2.0*math.pi*radius

def filament_for_bead(radius: float, layer_height: float, line_width: float,
                      filament_diameter: float=1.75, flow: float=1.0) -> float:
    """Volumetric estimate: deposited bead volume / filament cross-sectional area."""
    if min(radius,layer_height,line_width,filament_diameter,flow) <= 0:
        raise ValueError("all extrusion inputs must be positive")
    deposited=circle_length(radius)*layer_height*line_width*flow
    filament_area=math.pi*(filament_diameter/2.0)**2
    return deposited/filament_area

def full_circle_arc_gcode(circle: ArcCircle) -> str:
    """Emit one I/J full-circle arc. Caller must validate firmware dialect/support."""
    if circle.radius <= 0 or circle.extrusion < 0 or circle.feed_mm_min <= 0:
        raise ValueError("invalid circle toolpath")
    sx=circle.center_x+circle.radius
    sy=circle.center_y
    op="G2" if circle.clockwise else "G3"
    return (f"G0 X{sx:.3f} Y{sy:.3f} Z{circle.z:.3f}\n"
            f"{op} X{sx:.3f} Y{sy:.3f} I{-circle.radius:.3f} J0.000 "
            f"E{circle.extrusion:.5f} F{circle.feed_mm_min:.0f}\n")

def segmented_circle_gcode(circle: ArcCircle, segments: int=96) -> str:
    """Portable G1 fallback when the selected firmware/profile has no validated arcs."""
    if segments < 8: raise ValueError("segments must be >= 8")
    lines=[]
    e=circle.extrusion/segments
    for n in range(1,segments+1):
        a=2*math.pi*n/segments
        x=circle.center_x+circle.radius*math.cos(a)
        y=circle.center_y-circle.radius*math.sin(a) if circle.clockwise else circle.center_y+circle.radius*math.sin(a)
        lines.append(f"G1 X{x:.3f} Y{y:.3f} E{e:.5f} F{circle.feed_mm_min:.0f}")
    return "\n".join(lines)+"\n"
