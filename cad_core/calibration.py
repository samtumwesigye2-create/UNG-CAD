"""Calibration coupon geometry and measured-dimension feedback for UNG-CAD."""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Iterable, Sequence


@dataclass(frozen=True)
class CalibrationMeasurement:
    feature: str
    nominal_mm: float
    measured_mm: float

    def __post_init__(self):
        if self.nominal_mm <= 0 or self.measured_mm <= 0:
            raise ValueError("nominal_mm and measured_mm must be positive")

    @property
    def error_mm(self) -> float:
        return self.measured_mm-self.nominal_mm


def _tri(a,b,c): return [a,b,c]


def box_triangles(x:float,y:float,z:float,origin=(0.0,0.0,0.0)):
    ox,oy,oz=origin
    if min(x,y,z)<=0: raise ValueError("box dimensions must be positive")
    p=[
      (ox,oy,oz),(ox+x,oy,oz),(ox+x,oy+y,oz),(ox,oy+y,oz),
      (ox,oy,oz+z),(ox+x,oy,oz+z),(ox+x,oy+y,oz+z),(ox,oy+y,oz+z)
    ]
    faces=[(0,2,1),(0,3,2),(4,5,6),(4,6,7),(0,1,5),(0,5,4),
           (1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)]
    return [_tri(p[a],p[b],p[c]) for a,b,c in faces]


def cylinder_triangles(diameter:float,height:float,origin=(0.0,0.0,0.0),segments:int=96):
    if diameter<=0 or height<=0 or segments<16: raise ValueError("invalid cylinder dimensions/segments")
    ox,oy,oz=origin;r=diameter/2
    pts0=[(ox+r*math.cos(2*math.pi*i/segments),oy+r*math.sin(2*math.pi*i/segments),oz) for i in range(segments)]
    pts1=[(x,y,oz+height) for x,y,_ in pts0]
    cb=(ox,oy,oz);ct=(ox,oy,oz+height);out=[]
    for i in range(segments):
        j=(i+1)%segments
        out += [_tri(pts0[i],pts1[i],pts1[j]),_tri(pts0[i],pts1[j],pts0[j])]
        out += [_tri(cb,pts0[j],pts0[i]),_tri(ct,pts1[i],pts1[j])]
    return out


def ring_triangles(inner_diameter:float,outer_diameter:float,height:float,origin=(0.0,0.0,0.0),segments:int=128):
    if inner_diameter<=0 or outer_diameter<=inner_diameter or height<=0:
        raise ValueError("ring requires 0 < inner_diameter < outer_diameter and positive height")
    ox,oy,oz=origin;ri=inner_diameter/2;ro=outer_diameter/2
    def ring(r,z): return [(ox+r*math.cos(2*math.pi*i/segments),oy+r*math.sin(2*math.pi*i/segments),z) for i in range(segments)]
    ob=ring(ro,oz);ot=ring(ro,oz+height);ib=ring(ri,oz);it=ring(ri,oz+height);out=[]
    for i in range(segments):
        j=(i+1)%segments
        out += [_tri(ob[i],ot[i],ot[j]),_tri(ob[i],ot[j],ob[j])]
        out += [_tri(ib[i],it[j],it[i]),_tri(ib[i],ib[j],it[j])]
        out += [_tri(ot[i],it[i],it[j]),_tri(ot[i],it[j],ot[j])]
        out += [_tri(ob[i],ib[j],ib[i]),_tri(ob[i],ob[j],ib[j])]
    return out


def calibration_coupon_set():
    """Return independent printable STL geometries and a measurement manifest."""
    parts={}
    parts["XY_20x40x5"]=box_triangles(40,20,5)
    parts["Z_20mm"]=box_triangles(12,12,20)
    for d in (3.0,5.0,8.0):
        parts[f"HOLE_{d:g}mm"]=ring_triangles(d,max(14.0,d+8.0),4.0)
    for d in (5.0,10.0):
        parts[f"POST_{d:g}mm"]=cylinder_triangles(d,10.0)
    manifest={
      "schema":"ung-cad.calibration-coupon.v1",
      "units":"mm",
      "parts":{
        "XY_20x40x5":{"measure":[
          {"feature":"outer_x","nominal_mm":40.0},
          {"feature":"outer_y","nominal_mm":20.0},
          {"feature":"z","nominal_mm":5.0}]},
        "Z_20mm":{"measure":[{"feature":"z","nominal_mm":20.0}]},
        "HOLE_3mm":{"measure":[{"feature":"hole","nominal_mm":3.0}]},
        "HOLE_5mm":{"measure":[{"feature":"hole","nominal_mm":5.0}]},
        "HOLE_8mm":{"measure":[{"feature":"hole","nominal_mm":8.0}]},
        "POST_5mm":{"measure":[{"feature":"outer","nominal_mm":5.0}]},
        "POST_10mm":{"measure":[{"feature":"outer","nominal_mm":10.0}]},
      },
      "instructions":"Print with the same nozzle/material/profile used for production. Measure cooled parts with calipers; enter actual dimensions without pre-correcting them."
    }
    return parts,manifest


def _linear_fit(points:Sequence[tuple[float,float]]):
    """Fit measured = slope*nominal + intercept."""
    if not points: return 1.0,0.0
    if len(points)==1:
        n,m=points[0]
        return (m/n if n else 1.0),0.0
    xs=[p[0] for p in points];ys=[p[1] for p in points]
    xm=sum(xs)/len(xs);ym=sum(ys)/len(ys)
    den=sum((x-xm)**2 for x in xs)
    if den<=1e-12:
        return 1.0,sum(y-x for x,y in points)/len(points)
    slope=sum((x-xm)*(y-ym) for x,y in points)/den
    intercept=ym-slope*xm
    return slope,intercept


def profile_from_measurements(measurements:Iterable[CalibrationMeasurement], *, name="AD5M measured", nozzle_diameter_mm=0.4, source="calibration coupon"):
    ms=list(measurements)
    if not ms: raise ValueError("at least one measurement is required")
    holes=[m.error_mm for m in ms if m.feature.lower() in {"hole","bore"}]
    slots=[m.error_mm for m in ms if m.feature.lower() in {"slot","slot_width"}]
    z=[(m.nominal_mm,m.measured_mm) for m in ms if m.feature.lower() in {"z","height"}]
    outer=[(m.nominal_mm,m.measured_mm) for m in ms if m.feature.lower() in {"outer","outer_x","outer_y","boss","shaft"}]
    clear=[m.error_mm for m in ms if m.feature.lower() in {"clearance","gap"}]

    oslope,ointercept=_linear_fit(outer)
    zslope,_=_linear_fit(z)
    avg=lambda xs: sum(xs)/len(xs) if xs else 0.0
    return {
      "name":name,
      "nozzle_diameter_mm":float(nozzle_diameter_mm),
      "xy_scale_error_fraction":oslope-1.0,
      "z_scale_error_fraction":zslope-1.0,
      "hole_diameter_error_mm":avg(holes),
      "slot_width_error_mm":avg(slots),
      "outer_dimension_error_mm":ointercept,
      "clearance_error_mm":avg(clear),
      "source":source,
      "calibrated":True,
      "measurement_count":len(ms),
      "coverage":{
        "outer":len(outer),"z":len(z),"hole":len(holes),"slot":len(slots),"clearance":len(clear)
      }
    }
