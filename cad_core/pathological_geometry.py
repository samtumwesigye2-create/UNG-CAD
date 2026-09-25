"""Pathological geometry benchmarks and finite manufacturing representations."""
from dataclasses import dataclass
from math import pi, sqrt, log, asinh

@dataclass(frozen=True)
class GabrielHornReport:
    x_max: float
    finite_volume: float
    remaining_infinite_tail_volume: float
    finite_surface_area: float
    infinite_volume: float
    surface_area_converges: bool
    volume_converges: bool
    tip_radius: float
    manufacturable: bool
    reason: str

def gabriel_horn(x_max: float, minimum_feature: float=0.0) -> GabrielHornReport:
    """Analyze y=1/x revolved about x-axis from x=1 to finite x_max.

    Mathematical infinite horn: volume=pi, surface area diverges.
    finite_surface_area is the exact lateral area of the truncated horn.
    """
    if x_max <= 1: raise ValueError("x_max must be > 1")
    if minimum_feature < 0: raise ValueError("minimum_feature must be >= 0")
    # integral sqrt(x^4+1)/x^3 dx. With u=1/x^2:
    # -1/2 integral sqrt(1+u^2)/u du
    def F(x):
        u=1/(x*x)
        return -pi*(sqrt(1+u*u)+log(u/(1+sqrt(1+u*u))))
    area=F(x_max)-F(1.0)
    finite_volume=pi*(1-1/x_max)
    tail=pi/x_max
    tip=1/x_max
    ok=minimum_feature <= 0 or 2*tip >= minimum_feature
    reason="finite truncation clears minimum feature" if ok else "tip diameter is below manufacturing minimum feature"
    return GabrielHornReport(x_max,finite_volume,tail,area,pi,False,True,tip,ok,reason)
