"""Surfaces of revolution and convergence-aware pathological geometry."""
from dataclasses import dataclass
from math import pi, sqrt, log

@dataclass(frozen=True)
class GabrielHornAnalysis:
    x_start: float
    x_end: float
    segments: int
    volume: float
    surface_area: float
    tail_volume_to_infinity: float
    infinite_volume: float
    surface_area_converges: bool
    volume_converges: bool
    minimum_radius: float
    manufacturable: bool
    warning: str|None

def gabriel_radius(x: float)->float:
    if x<=0: raise ValueError("x must be positive")
    return 1.0/x

def analyze_gabriel_horn(x_end: float, segments: int=2000, min_feature: float=0.0)->GabrielHornAnalysis:
    if x_end<=1: raise ValueError("x_end must be > 1")
    if segments<10: raise ValueError("segments must be >= 10")
    # Exact volume on [1,b] for y=1/x revolved about x-axis.
    volume=pi*(1.0-1.0/x_end)
    infinite_volume=pi
    tail=pi/x_end
    # Simpson integration of 2*pi*(1/x)*sqrt(1+1/x^4).
    n=segments if segments%2==0 else segments+1
    h=(x_end-1.0)/n
    def f(x): return 2*pi*(1/x)*sqrt(1+1/x**4)
    total=f(1.0)+f(x_end)
    for i in range(1,n):
        total+=(4 if i%2 else 2)*f(1+i*h)
    area=total*h/3
    rmin=1/x_end
    manufacturable=min_feature<=0 or 2*rmin>=min_feature
    warning=None if manufacturable else "terminal diameter is below manufacturing minimum feature"
    return GabrielHornAnalysis(1.0,x_end,n,volume,area,tail,infinite_volume,False,True,rmin,manufacturable,warning)

def gabriel_horn_profile(x_end: float, samples: int=128):
    if samples<2: raise ValueError("samples must be >= 2")
    return tuple((1+(x_end-1)*i/(samples-1), gabriel_radius(1+(x_end-1)*i/(samples-1))) for i in range(samples))
