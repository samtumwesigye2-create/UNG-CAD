"""Printable dimensional-calibration kit and measured-feedback fitting.

The coupon generator uses simple watertight primitives so it stays independent
of external boolean kernels. The generated STL contains multiple disconnected
calibration pieces that are intended to be printed together on the same bed.

All calibration values are derived from user-entered measurements. No printer
correction is guessed or silently enabled.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from statistics import mean
from typing import Iterable, Sequence

from .fit_analysis import PrinterCompensationProfile

Point = tuple[float,float,float]
Triangle = tuple[Point,Point,Point]


@dataclass(frozen=True)
class CalibrationCouponSpec:
    outer_x_mm: float = 40.0
    outer_y_mm: float = 20.0
    base_height_mm: float = 4.0
    z_tower_height_mm: float = 20.0
    z_tower_size_mm: float = 10.0
    hole_diameters_mm: tuple[float,...] = (3.0,4.0,5.0,6.0)
    pin_diameters_mm: tuple[float,...] = (3.0,4.0,5.0,6.0)
    ring_wall_mm: float = 2.0
    spacing_mm: float = 8.0
    radial_segments: int = 64

    def __post_init__(self):
        vals=(self.outer_x_mm,self.outer_y_mm,self.base_height_mm,
              self.z_tower_height_mm,self.z_tower_size_mm,self.ring_wall_mm,
              self.spacing_mm)
        if any(v<=0 for v in vals): raise ValueError("coupon dimensions must be positive")
        if self.radial_segments<24: raise ValueError("radial_segments must be at least 24")
        if any(d<=0 for d in self.hole_diameters_mm+self.pin_diameters_mm):
            raise ValueError("hole/pin diameters must be positive")

    def to_dict(self): return asdict(self)


def _box(x0,y0,z0,sx,sy,sz)->list[Triangle]:
    x1,y1,z1=x0+sx,y0+sy,z0+sz
    p=[
      (x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),
      (x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1),
    ]
    faces=[
      (0,2,1),(0,3,2), (4,5,6),(4,6,7),
      (0,1,5),(0,5,4), (1,2,6),(1,6,5),
      (2,3,7),(2,7,6), (3,0,4),(3,4,7),
    ]
    return [(p[a],p[b],p[c]) for a,b,c in faces]


def _cylinder(cx,cy,z0,r,h,n=64)->list[Triangle]:
    if r<=0 or h<=0: raise ValueError("cylinder radius/height must be positive")
    bot=[(cx+r*math.cos(2*math.pi*i/n),cy+r*math.sin(2*math.pi*i/n),z0) for i in range(n)]
    top=[(x,y,z0+h) for x,y,_ in bot]
    cb=(cx,cy,z0);ct=(cx,cy,z0+h);out=[]
    for i in range(n):
        j=(i+1)%n
        out += [(bot[i],top[i],top[j]),(bot[i],top[j],bot[j])]
        out += [(cb,bot[j],bot[i]),(ct,top[i],top[j])]
    return out


def _annulus(cx,cy,z0,inner_r,outer_r,h,n=64)->list[Triangle]:
    if not (0<inner_r<outer_r) or h<=0:
        raise ValueError("annulus radii/height invalid")
    ib=[(cx+inner_r*math.cos(2*math.pi*i/n),cy+inner_r*math.sin(2*math.pi*i/n),z0) for i in range(n)]
    it=[(x,y,z0+h) for x,y,_ in ib]
    ob=[(cx+outer_r*math.cos(2*math.pi*i/n),cy+outer_r*math.sin(2*math.pi*i/n),z0) for i in range(n)]
    ot=[(x,y,z0+h) for x,y,_ in ob]
    out=[]
    for i in range(n):
        j=(i+1)%n
        out += [(ob[i],ot[i],ot[j]),(ob[i],ot[j],ob[j])]        # outer wall
        out += [(ib[i],it[j],it[i]),(ib[i],ib[j],it[j])]        # inner wall
        out += [(ob[i],ob[j],ib[j]),(ob[i],ib[j],ib[i])]        # bottom
        out += [(ot[i],it[j],ot[j]),(ot[i],it[i],it[j])]        # top
    return out


def generate_calibration_coupon(spec:CalibrationCouponSpec=CalibrationCouponSpec()):
    """Return (triangles, manifest) for a printable calibration kit."""
    tris:list[Triangle]=[]
    manifest={"schema":"ungcad-calibration-coupon/v1","spec":spec.to_dict(),"pieces":[]}

    # XY block: measure X and Y outside dimensions.
    x0=y0=0.0
    tris += _box(x0,y0,0,spec.outer_x_mm,spec.outer_y_mm,spec.base_height_mm)
    manifest["pieces"].append({"id":"outer_xy","type":"outer_block","nominal_x_mm":spec.outer_x_mm,
                                "nominal_y_mm":spec.outer_y_mm,"nominal_z_mm":spec.base_height_mm})

    # Z tower.
    tx=spec.outer_x_mm+spec.spacing_mm
    tris += _box(tx,0,0,spec.z_tower_size_mm,spec.z_tower_size_mm,spec.z_tower_height_mm)
    manifest["pieces"].append({"id":"z_tower","type":"height_block","nominal_z_mm":spec.z_tower_height_mm})

    # Hole rings.
    cursor_x=0.0
    row_y=spec.outer_y_mm+spec.spacing_mm+max(spec.hole_diameters_mm)/2+spec.ring_wall_mm
    for i,d in enumerate(spec.hole_diameters_mm):
        ro=d/2+spec.ring_wall_mm
        cx=cursor_x+ro
        tris += _annulus(cx,row_y,0,d/2,ro,spec.base_height_mm,spec.radial_segments)
        manifest["pieces"].append({"id":f"hole_{i+1}","type":"hole_ring","nominal_hole_diameter_mm":d})
        cursor_x += 2*ro+spec.spacing_mm

    # Pins for external-diameter calibration and fit trials.
    cursor_x=0.0
    row2_y=row_y+max(d+2*spec.ring_wall_mm for d in spec.hole_diameters_mm)+spec.spacing_mm
    for i,d in enumerate(spec.pin_diameters_mm):
        r=d/2
        cx=cursor_x+r
        tris += _cylinder(cx,row2_y,0,r,spec.base_height_mm,spec.radial_segments)
        manifest["pieces"].append({"id":f"pin_{i+1}","type":"pin","nominal_pin_diameter_mm":d})
        cursor_x += d+spec.spacing_mm

    xs=[p[0] for t in tris for p in t];ys=[p[1] for t in tris for p in t];zs=[p[2] for t in tris for p in t]
    manifest["bounds_mm"]={"x":max(xs)-min(xs),"y":max(ys)-min(ys),"z":max(zs)-min(zs)}
    manifest["triangle_count"]=len(tris)
    return tris,manifest


def _samples(items:Iterable[dict], key_nominal="nominal_mm", key_measured="measured_mm"):
    out=[]
    for item in items or ():
        n=float(item[key_nominal]);m=float(item[key_measured])
        if n<=0 or m<=0: raise ValueError("nominal and measured dimensions must be positive")
        out.append((n,m))
    return out


def derive_compensation_profile(
    *,
    name:str,
    outer_samples:Sequence[dict]=(),
    xy_scale_samples:Sequence[dict]=(),
    z_scale_samples:Sequence[dict]=(),
    hole_samples:Sequence[dict]=(),
    slot_samples:Sequence[dict]=(),
    clearance_samples:Sequence[dict]=(),
    nozzle_diameter_mm:float=0.4,
    source:str="measured calibration coupon",
)->PrinterCompensationProfile:
    """Fit the simple UNG printer-error model from physical measurements."""
    if not name.strip(): raise ValueError("profile name is required")
    xy=_samples(xy_scale_samples)
    zs=_samples(z_scale_samples)
    holes=_samples(hole_samples)
    slots=_samples(slot_samples)
    outers=_samples(outer_samples)
    clearances=_samples(clearance_samples)

    xy_scale=mean((m-n)/n for n,m in xy) if xy else 0.0
    z_scale=mean((m-n)/n for n,m in zs) if zs else 0.0
    outer_offset=mean(m-n*(1+xy_scale) for n,m in outers) if outers else 0.0
    hole_error=mean(m-n for n,m in holes) if holes else 0.0
    slot_error=mean(m-n for n,m in slots) if slots else 0.0
    clearance_error=mean(m-n for n,m in clearances) if clearances else 0.0

    count=sum(map(len,(xy,zs,holes,slots,outers,clearances)))
    return PrinterCompensationProfile(
        name=name.strip(),nozzle_diameter_mm=float(nozzle_diameter_mm),
        xy_scale_error_fraction=xy_scale,z_scale_error_fraction=z_scale,
        hole_diameter_error_mm=hole_error,slot_width_error_mm=slot_error,
        outer_dimension_error_mm=outer_offset,clearance_error_mm=clearance_error,
        source=source,calibrated=count>0,
    )
