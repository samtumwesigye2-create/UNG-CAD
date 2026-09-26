"""Spiral-vase and parametric ellipse toolpaths.

Geometry/toolpath only: machine/firmware capabilities, temperatures, acceleration,
extrusion limits and safe teardown remain validated machine-profile responsibilities.
"""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class SpiralCircle:
    center_x: float; center_y: float; radius: float
    start_z: float; height: float; pitch: float
    extrusion_per_turn: float; feed_mm_min: float=2400.0
    clockwise: bool=True

@dataclass(frozen=True)
class Ellipse:
    center_x: float; center_y: float
    radius_x: float; radius_y: float
    z: float; extrusion_total: float
    feed_mm_min: float=2400.0

def spiral_length_per_turn(radius: float,pitch: float)->float:
    if radius<=0 or pitch<=0: raise ValueError("radius and pitch must be positive")
    return math.hypot(2*math.pi*radius,pitch)

def spiral_circle_gcode(s: SpiralCircle, *, helical_arcs_supported: bool=False, segments_per_turn: int=96)->str:
    if min(s.radius,s.height,s.pitch,s.feed_mm_min)<=0 or s.extrusion_per_turn<0:
        raise ValueError("invalid spiral")
    turns=s.height/s.pitch
    n=max(1,math.ceil(turns*segments_per_turn))
    sx=s.center_x+s.radius
    out=[f"G0 X{sx:.3f} Y{s.center_y:.3f} Z{s.start_z:.3f}"]
    # Full-circle helical arcs are emitted only when the selected machine profile explicitly validates them.
    if helical_arcs_supported and math.isclose(turns,round(turns),abs_tol=1e-9):
        op="G2" if s.clockwise else "G3"
        for k in range(1,int(round(turns))+1):
            z=s.start_z+k*s.pitch
            out.append(f"{op} X{sx:.3f} Y{s.center_y:.3f} Z{z:.3f} I{-s.radius:.3f} J0.000 E{s.extrusion_per_turn:.5f} F{s.feed_mm_min:.0f}")
        return "\n".join(out)+"\n"
    # Portable continuous-Z fallback. Each move advances angle and Z together.
    e=s.extrusion_per_turn/segments_per_turn
    sign=-1 if s.clockwise else 1
    for k in range(1,n+1):
        frac=min(k/n,1.0); theta=sign*2*math.pi*turns*frac
        x=s.center_x+s.radius*math.cos(theta); y=s.center_y+s.radius*math.sin(theta)
        z=s.start_z+s.height*frac
        out.append(f"G1 X{x:.3f} Y{y:.3f} Z{z:.3f} E{e:.5f} F{s.feed_mm_min:.0f}")
    return "\n".join(out)+"\n"

def ellipse_perimeter_ramanujan(rx: float,ry: float)->float:
    if rx<=0 or ry<=0: raise ValueError("ellipse radii must be positive")
    h=((rx-ry)/(rx+ry))**2
    return math.pi*(rx+ry)*(1+3*h/(10+math.sqrt(4-3*h)))

def ellipse_gcode(e: Ellipse, segments: int=128)->str:
    if min(e.radius_x,e.radius_y,e.feed_mm_min)<=0 or e.extrusion_total<0 or segments<8:
        raise ValueError("invalid ellipse")
    x0=e.center_x+e.radius_x; y0=e.center_y
    pts=[]; prev=(x0,y0); lengths=[]
    for k in range(1,segments+1):
        t=2*math.pi*k/segments
        p=(e.center_x+e.radius_x*math.cos(t),e.center_y+e.radius_y*math.sin(t))
        lengths.append(math.hypot(p[0]-prev[0],p[1]-prev[1])); pts.append(p); prev=p
    total=sum(lengths)
    out=[f"G0 X{x0:.3f} Y{y0:.3f} Z{e.z:.3f}"]
    for p,d in zip(pts,lengths):
        ex=e.extrusion_total*(d/total) if total else 0
        out.append(f"G1 X{p[0]:.3f} Y{p[1]:.3f} E{ex:.5f} F{e.feed_mm_min:.0f}")
    return "\n".join(out)+"\n"


@dataclass(frozen=True)
class NonplanarOval:
    center_x: float; center_y: float
    radius_x: float; radius_y: float
    start_z: float; height: float; pitch: float
    wave_amplitude: float; wave_frequency: float
    extrusion_per_mm: float
    feed_mm_min: float=2400.0
    base_accel_mm_s2: float=2000.0
    apex_accel_mm_s2: float=800.0

def ellipse_curvature(rx: float, ry: float, theta: float) -> float:
    if rx<=0 or ry<=0: raise ValueError("ellipse radii must be positive")
    den=(rx*rx*math.sin(theta)**2 + ry*ry*math.cos(theta)**2)**1.5
    return (rx*ry)/den

def nonplanar_oval_gcode(n: NonplanarOval, *, segments_per_turn: int=128,
                         dynamic_accel_supported: bool=False,
                         accel_command: str="M204 P{accel}",
                         allow_downward_z: bool=False) -> str:
    """Generate an experimental continuous-Z ellipse with sinusoidal Z modulation.

    Dynamic acceleration commands are emitted only when a validated machine profile
    explicitly opts in. By default, downward Z motion is rejected because ordinary
    FDM non-planar motion can collide with the nozzle/part.
    """
    if min(n.radius_x,n.radius_y,n.height,n.pitch,n.extrusion_per_mm,n.feed_mm_min)<=0:
        raise ValueError("invalid nonplanar oval")
    if segments_per_turn<16: raise ValueError("segments_per_turn must be >= 16")
    turns=n.height/n.pitch
    steps=max(1,math.ceil(turns*segments_per_turn))
    x0=n.center_x+n.radius_x; y0=n.center_y; z0=n.start_z
    out=[f"G0 X{x0:.3f} Y{y0:.3f} Z{z0:.3f}"]
    prev=(x0,y0,z0)
    max_k=max(n.radius_x,n.radius_y)/(min(n.radius_x,n.radius_y)**2)
    for k in range(1,steps+1):
        progress=k/steps
        theta=2*math.pi*turns*progress
        x=n.center_x+n.radius_x*math.cos(theta)
        y=n.center_y+n.radius_y*math.sin(theta)
        base_z=n.start_z+n.height*progress
        z=base_z+n.wave_amplitude*math.sin(n.wave_frequency*theta)
        if z<n.start_z:
            z=n.start_z
        if not allow_downward_z and z < prev[2]-1e-9:
            raise ValueError("non-planar path contains downward Z motion; validate collision clearance or reduce wave amplitude/frequency")
        if dynamic_accel_supported:
            kappa=ellipse_curvature(n.radius_x,n.radius_y,theta)
            factor=max(0.0,min(1.0,kappa/max_k))
            accel=round(n.base_accel_mm_s2-factor*(n.base_accel_mm_s2-n.apex_accel_mm_s2))
            out.append(accel_command.format(accel=accel))
        dist=math.sqrt((x-prev[0])**2+(y-prev[1])**2+(z-prev[2])**2)
        e=dist*n.extrusion_per_mm
        out.append(f"G1 X{x:.3f} Y{y:.3f} Z{z:.3f} E{e:.5f} F{n.feed_mm_min:.0f}")
        prev=(x,y,z)
    return "\n".join(out)+"\n"
