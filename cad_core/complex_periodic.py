"""Complex, periodic and stationary-point mathematics for UNG-CAD."""
from __future__ import annotations
import cmath, math
from dataclasses import dataclass
from typing import Callable, Iterable

@dataclass(frozen=True)
class Phasor:
    amplitude: float
    phase: float
    def complex(self) -> complex:
        return self.amplitude * cmath.exp(1j*self.phase)
    @classmethod
    def from_complex(cls,z:complex)->"Phasor":
        return cls(abs(z),cmath.phase(z))

def euler(theta:float)->complex:
    return cmath.exp(1j*theta)

def trig_wave(theta:float, amplitude:float=1.0, frequency:float=1.0,
              phase:float=0.0, offset:float=0.0, kind:str="sin")->float:
    x=frequency*theta+phase
    fn={"sin":math.sin,"cos":math.cos}.get(kind)
    if fn is None: raise ValueError("kind must be sin or cos")
    return offset+amplitude*fn(x)

def trig_family(theta:float)->dict[str,float]:
    return {"sin(theta)":math.sin(theta),
            "sin(2theta)":math.sin(2*theta),
            "sin(theta/2)":math.sin(theta/2)}

def periodic_path(start:float,end:float,samples:int=361,**wave)->list[tuple[float,float]]:
    if samples<2: raise ValueError("samples must be >= 2")
    return [(t:=start+(end-start)*i/(samples-1),trig_wave(t,**wave)) for i in range(samples)]

def helix(theta:float,radius:float,pitch_per_turn:float)->tuple[float,float,float]:
    return radius*math.cos(theta),radius*math.sin(theta),pitch_per_turn*theta/(2*math.pi)

def central_derivative(f:Callable[[float],float],x:float,h:float=1e-5)->float:
    if h<=0: raise ValueError("h must be positive")
    return (f(x+h)-f(x-h))/(2*h)

def stationary_points(f:Callable[[float],float],a:float,b:float,samples:int=1001,
                      derivative_tol:float=1e-7)->list[float]:
    """Locate derivative roots by sampled bracketing + bisection.

    Includes tangent/flat roots when a sampled derivative is within tolerance.
    """
    if b<=a or samples<3: raise ValueError("require b>a and samples>=3")
    xs=[a+(b-a)*i/(samples-1) for i in range(samples)]
    ds=[central_derivative(f,x) for x in xs]
    roots=[]
    def add(x):
        if not roots or all(abs(x-r)>max(1e-6,(b-a)/samples) for r in roots): roots.append(x)
    for x,d in zip(xs,ds):
        if abs(d)<=derivative_tol: add(x)
    for i in range(len(xs)-1):
        lo,hi=xs[i],xs[i+1]; dlo,dhi=ds[i],ds[i+1]
        if dlo*dhi<0:
            for _ in range(60):
                mid=(lo+hi)/2; dm=central_derivative(f,mid)
                if abs(dm)<=derivative_tol: lo=hi=mid; break
                if dlo*dm<=0: hi=mid; dhi=dm
                else: lo=mid; dlo=dm
            add((lo+hi)/2)
    return sorted(roots)

def rolle_stationary_point(f:Callable[[float],float],a:float,b:float,
                           endpoint_tol:float=1e-8)->float:
    if not math.isclose(f(a),f(b),abs_tol=endpoint_tol,rel_tol=endpoint_tol):
        raise ValueError("Rolle condition f(a)=f(b) is not satisfied")
    interior=[x for x in stationary_points(f,a,b) if a<x<b]
    if not interior: raise ValueError("No interior stationary point found numerically")
    return interior[0]

def rotation_z(theta:float)->tuple[tuple[float,float,float],...]:
    c,s=math.cos(theta),math.sin(theta)
    return ((c,-s,0.0),(s,c,0.0),(0.0,0.0,1.0))

def sample_pan_tilt(pan_limit_deg:float=90,tilt_limit_deg:float=25,
                    pan_samples:int=37,tilt_samples:int=21)->list[tuple[float,float]]:
    """Continuous-domain validation grid input for DRACO mechanism checks."""
    if pan_samples<2 or tilt_samples<2: raise ValueError("sample counts must be >=2")
    return [(math.radians(-pan_limit_deg+2*pan_limit_deg*i/(pan_samples-1)),
             math.radians(-tilt_limit_deg+2*tilt_limit_deg*j/(tilt_samples-1)))
            for i in range(pan_samples) for j in range(tilt_samples)]
