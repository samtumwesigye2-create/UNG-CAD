"""Validated weak-field orbital dynamics and frame-dragging utilities for UNG.

Strong-field Kerr models are intentionally excluded until separately validated.
SI units throughout.
"""
import math
from dataclasses import dataclass

G=6.67430e-11
C=299792458.0

def _v3(v):
    if len(v)!=3: raise ValueError("vector must have three components")
    return tuple(float(x) for x in v)
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def norm(a): return math.sqrt(dot(a,a))
def scale(a,s): return tuple(x*s for x in a)
def sub(a,b): return tuple(x-y for x,y in zip(a,b))

def schwarzschild_radius(mass_kg):
    if mass_kg<=0: raise ValueError("mass_kg must be positive")
    return 2*G*mass_kg/C**2

def weak_field_frame_dragging_scalar(angular_momentum, radius_m):
    """Characteristic weak-field Lense-Thirring angular rate 2 G J/(c² r³), rad/s."""
    if radius_m<=0: raise ValueError("radius_m must be positive")
    return 2*G*float(angular_momentum)/(C**2*radius_m**3)

def lense_thirring_vector(spin_angular_momentum, position_m):
    """Weak-field gravitomagnetic precession vector:
    G/(c² r³) [3(J·rhat)rhat - J].
    """
    J=_v3(spin_angular_momentum);r=_v3(position_m);R=norm(r)
    if R<=0: raise ValueError("position magnitude must be positive")
    rh=scale(r,1/R)
    return scale(sub(scale(rh,3*dot(J,rh)),J),G/(C**2*R**3))

@dataclass(frozen=True)
class OrbitalState:
    position_m: tuple
    velocity_m_s: tuple

def two_body_acceleration(mu,position_m):
    r=_v3(position_m);R=norm(r)
    if mu<=0 or R<=0: raise ValueError("mu and radius must be positive")
    return scale(r,-mu/R**3)

def rk4_two_body_step(state,mu,dt_s):
    """One deterministic RK4 propagation step for Newtonian two-body motion."""
    if dt_s<=0: raise ValueError("dt_s must be positive")
    r=_v3(state.position_m);v=_v3(state.velocity_m_s)
    def acc(x): return two_body_acceleration(mu,x)
    def add(a,b,s=1): return tuple(x+s*y for x,y in zip(a,b))
    k1r=v;k1v=acc(r)
    k2r=add(v,k1v,dt_s/2);k2v=acc(add(r,k1r,dt_s/2))
    k3r=add(v,k2v,dt_s/2);k3v=acc(add(r,k2r,dt_s/2))
    k4r=add(v,k3v,dt_s);k4v=acc(add(r,k3r,dt_s))
    rn=tuple(r[i]+dt_s*(k1r[i]+2*k2r[i]+2*k3r[i]+k4r[i])/6 for i in range(3))
    vn=tuple(v[i]+dt_s*(k1v[i]+2*k2v[i]+2*k3v[i]+k4v[i])/6 for i in range(3))
    return OrbitalState(rn,vn)

def orbital_elements(mu,state):
    """Return classical elements where defined: a,e,i,raan,arg_periapsis,true_anomaly."""
    r=_v3(state.position_m);v=_v3(state.velocity_m_s);R=norm(r);V=norm(v)
    if mu<=0 or R<=0: raise ValueError("mu and radius must be positive")
    h=cross(r,v);H=norm(h);evec=sub(scale(cross(v,h),1/mu),scale(r,1/R));e=norm(evec)
    energy=V*V/2-mu/R;a=math.inf if abs(energy)<1e-30 else -mu/(2*energy)
    inc=math.acos(max(-1,min(1,h[2]/H))) if H else 0.0
    n=(-h[1],h[0],0.0);N=norm(n)
    raan=math.atan2(n[1],n[0])%(2*math.pi) if N else 0.0
    def angle(a1,b1):
        na,nb=norm(a1),norm(b1)
        return math.acos(max(-1,min(1,dot(a1,b1)/(na*nb)))) if na and nb else 0.0
    arg=angle(n,evec) if N and e>1e-14 else 0.0
    if evec[2]<0: arg=2*math.pi-arg
    nu=angle(evec,r) if e>1e-14 else angle(n,r)
    if dot(r,v)<0: nu=2*math.pi-nu
    return {"semi_major_axis_m":a,"eccentricity":e,"inclination_rad":inc,"raan_rad":raan,"arg_periapsis_rad":arg,"true_anomaly_rad":nu,"specific_angular_momentum":H}

def fit_residuals(observed,predicted):
    if len(observed)!=len(predicted) or not observed: raise ValueError("observed/predicted must have equal nonzero length")
    residuals=[norm(sub(_v3(o),_v3(p))) for o,p in zip(observed,predicted)]
    return {"residuals_m":residuals,"rmse_m":math.sqrt(sum(x*x for x in residuals)/len(residuals)),"mae_m":sum(residuals)/len(residuals),"max_m":max(residuals)}

def parameter_sweep(values,fn):
    return [{"value":float(v),"result":fn(float(v))} for v in values]
