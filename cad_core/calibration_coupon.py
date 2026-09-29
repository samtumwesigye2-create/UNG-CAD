"""Printable calibration coupon geometry and measured-dimension feedback.

The coupon intentionally avoids hidden printer corrections. Nominal geometry is
exported exactly; measured results are then used to derive a compensation
profile for the specific printer/material/process combination.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, asdict
from typing import Iterable, Mapping

Point=tuple[float,float,float]
Triangle=tuple[Point,Point,Point]


def _tri(a,b,c): return (tuple(map(float,a)),tuple(map(float,b)),tuple(map(float,c)))


def box_triangles(x:float,y:float,z:float,origin:Point=(0,0,0))->list[Triangle]:
    if min(x,y,z)<=0: raise ValueError("box dimensions must be positive")
    ox,oy,oz=map(float,origin)
    p=[
      (ox,oy,oz),(ox+x,oy,oz),(ox+x,oy+y,oz),(ox,oy+y,oz),
      (ox,oy,oz+z),(ox+x,oy,oz+z),(ox+x,oy+y,oz+z),(ox,oy+y,oz+z),
    ]
    faces=[(0,2,1),(0,3,2),(4,5,6),(4,6,7),
           (0,1,5),(0,5,4),(1,2,6),(1,6,5),
           (2,3,7),(2,7,6),(3,0,4),(3,4,7)]
    return [_tri(p[a],p[b],p[c]) for a,b,c in faces]


def solid_cylinder_triangles(diameter:float,height:float,center_xy=(0.0,0.0),segments:int=64)->list[Triangle]:
    if diameter<=0 or height<=0 or segments<12: raise ValueError("invalid cylinder dimensions")
    cx,cy=map(float,center_xy);r=diameter/2;z0=0.0;z1=float(height)
    bot=[(cx+r*math.cos(2*math.pi*i/segments),cy+r*math.sin(2*math.pi*i/segments),z0) for i in range(segments)]
    top=[(x,y,z1) for x,y,_ in bot]; cb=(cx,cy,z0); ct=(cx,cy,z1);out=[]
    for i in range(segments):
        j=(i+1)%segments
        out += [_tri(bot[i],top[i],top[j]),_tri(bot[i],top[j],bot[j])]
        out += [_tri(cb,bot[j],bot[i]),_tri(ct,top[i],top[j])]
    return out


def ring_triangles(inner_diameter:float,outer_diameter:float,height:float,center_xy=(0.0,0.0),segments:int=64)->list[Triangle]:
    if inner_diameter<=0 or outer_diameter<=inner_diameter or height<=0 or segments<12:
        raise ValueError("invalid ring dimensions")
    cx,cy=map(float,center_xy);ri=inner_diameter/2;ro=outer_diameter/2;z0=0.0;z1=float(height)
    oi=[];oo=[];ti=[];to=[]
    for i in range(segments):
        a=2*math.pi*i/segments;c,s=math.cos(a),math.sin(a)
        oo.append((cx+ro*c,cy+ro*s,z0)); oi.append((cx+ri*c,cy+ri*s,z0))
        to.append((cx+ro*c,cy+ro*s,z1)); ti.append((cx+ri*c,cy+ri*s,z1))
    out=[]
    for i in range(segments):
        j=(i+1)%segments
        out += [_tri(oo[i],to[i],to[j]),_tri(oo[i],to[j],oo[j])]
        out += [_tri(oi[i],ti[j],ti[i]),_tri(oi[i],oi[j],ti[j])]
        out += [_tri(to[i],ti[i],ti[j]),_tri(to[i],ti[j],to[j])]
        out += [_tri(oo[i],oi[j],oi[i]),_tri(oo[i],oo[j],oi[j])]
    return out


@dataclass(frozen=True)
class CouponManifest:
    schema:str
    coupon_version:str
    printer_family:str
    nozzle_diameter_mm:float
    nominal_features:tuple[dict,...]

    def to_dict(self): return asdict(self)


def ad5m_coupon_manifest()->CouponManifest:
    feats=[
      {"id":"xy_block_x","feature":"outer","nominal_mm":20.0,"axis":"x","part":"xy_block.stl"},
      {"id":"xy_block_y","feature":"outer","nominal_mm":20.0,"axis":"y","part":"xy_block.stl"},
      {"id":"z_block","feature":"z","nominal_mm":10.0,"axis":"z","part":"xy_block.stl"},
    ]
    for d in (3.0,5.0,8.0,10.0):
        feats.append({"id":f"hole_{d:g}","feature":"hole","nominal_mm":d,"part":f"hole_ring_{d:g}.stl"})
    for d in (5.8,6.0,6.2):
        feats.append({"id":f"plug_{d:g}","feature":"outer","nominal_mm":d,"part":f"plug_{d:g}.stl"})
    return CouponManifest(
      schema="ungcad-calibration-coupon/v1",
      coupon_version="AD5M-0.4-v1",
      printer_family="FlashForge Adventurer 5M",
      nozzle_diameter_mm=0.4,
      nominal_features=tuple(feats),
    )


def ad5m_coupon_parts()->dict[str,list[Triangle]]:
    parts={"xy_block.stl":box_triangles(20,20,10)}
    for d in (3.0,5.0,8.0,10.0):
        parts[f"hole_ring_{d:g}.stl"]=ring_triangles(d,d+6.0,4.0)
    for d in (5.8,6.0,6.2):
        parts[f"plug_{d:g}.stl"]=solid_cylinder_triangles(d,8.0)
    return parts


def measurement_template_rows()->list[dict]:
    return [
      {"feature_id":f["id"],"feature":f["feature"],"nominal_mm":f["nominal_mm"],"measured_mm":""}
      for f in ad5m_coupon_manifest().nominal_features
    ]


def _median(values):
    vals=[float(v) for v in values]
    return statistics.median(vals) if vals else 0.0


def derive_compensation_profile(
    measurements:Iterable[Mapping],
    *,
    name:str="AD5M measured profile",
    source:str="calibration coupon",
    nozzle_diameter_mm:float=0.4,
)->dict:
    """Derive profile using measured error = printed - CAD.

    Multiple hole/slot/clearance samples use median absolute dimensional error.
    Outer X/Y and Z use median fractional scale error so different nominal sizes
    can be combined without inventing a constant offset.
    """
    groups={"hole":[],"slot":[],"clearance":[],"outer":[],"z":[]}
    used=[]
    for raw in measurements:
        feature=str(raw.get("feature","")).strip().lower()
        if feature not in groups: continue
        nominal=float(raw["nominal_mm"]); measured=float(raw["measured_mm"])
        if nominal<=0 or measured<=0: raise ValueError("nominal_mm and measured_mm must be positive")
        err=measured-nominal
        used.append({"feature":feature,"nominal_mm":nominal,"measured_mm":measured,"error_mm":err})
        groups[feature].append((nominal,err))
    if not used: raise ValueError("At least one supported measurement is required")

    hole_err=_median(err for _,err in groups["hole"])
    slot_err=_median(err for _,err in groups["slot"])
    clearance_err=_median(err for _,err in groups["clearance"])
    xy_scale=_median(err/nom for nom,err in groups["outer"])
    z_scale=_median(err/nom for nom,err in groups["z"])
    return {
      "name":name,
      "nozzle_diameter_mm":float(nozzle_diameter_mm),
      "xy_scale_error_fraction":xy_scale,
      "z_scale_error_fraction":z_scale,
      "hole_diameter_error_mm":hole_err,
      "slot_width_error_mm":slot_err,
      "outer_dimension_error_mm":0.0,
      "clearance_error_mm":clearance_err,
      "source":source,
      "calibrated":True,
      "measurement_count":len(used),
      "measurements":used,
    }
