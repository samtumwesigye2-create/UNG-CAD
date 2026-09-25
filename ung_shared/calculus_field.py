"""UNG shared numerical calculus and vector-field engine.

Dependency-free reference implementation for CAD/sensor analysis.  Symbolic
rewrites (u-substitution, integration by parts, trig identities) belong in a
future symbolic front-end; this module provides the executable numerical core.
"""
from __future__ import annotations
import math
from typing import Callable, Iterable, Sequence

ScalarFn = Callable[[float], float]
Field3 = Callable[[float, float, float], Sequence[float]]

def derivative(f: ScalarFn, x: float, h: float = 1e-5) -> float:
    if h <= 0: raise ValueError("h must be positive")
    return (f(x+h)-f(x-h))/(2*h)

def integrate(f: ScalarFn, a: float, b: float, n: int = 1000) -> float:
    """Composite Simpson integration."""
    if n < 2: raise ValueError("n must be >= 2")
    if n % 2: n += 1
    h=(b-a)/n
    s=f(a)+f(b)
    s += 4*sum(f(a+i*h) for i in range(1,n,2))
    s += 2*sum(f(a+i*h) for i in range(2,n,2))
    return s*h/3

def accumulation(f: ScalarFn, a: float, x: float, n: int = 1000) -> float:
    """FTC Part 1 accumulation function A(x)=integral_a^x f(t)dt."""
    return integrate(f,a,x,n)

def evaluate_antiderivative(F: ScalarFn, a: float, b: float) -> float:
    """FTC Part 2: integral_a^b f = F(b)-F(a), where F'=f."""
    return F(b)-F(a)

def partial_sum(values: Iterable[float], n: int | None = None) -> float:
    vals=list(values)
    return sum(vals if n is None else vals[:n])

def geometric_sum(a: float, r: float, n: int | None = None) -> float:
    if n is None:
        if abs(r) >= 1: raise ValueError("infinite geometric series diverges for |r| >= 1")
        return a/(1-r)
    if n < 0: raise ValueError("n must be nonnegative")
    if r == 1: return a*n
    return a*(1-r**n)/(1-r)

def taylor(f_derivatives: Sequence[ScalarFn], x: float, center: float = 0.0) -> float:
    """Evaluate a Taylor polynomial from [f, f', f'', ...] at center."""
    dx=x-center
    return sum(df(center)*dx**k/math.factorial(k) for k,df in enumerate(f_derivatives))

def gradient(f: Callable[[float,float,float],float], p: Sequence[float], h: float=1e-5) -> tuple[float,float,float]:
    x,y,z=p
    return (
        (f(x+h,y,z)-f(x-h,y,z))/(2*h),
        (f(x,y+h,z)-f(x,y-h,z))/(2*h),
        (f(x,y,z+h)-f(x,y,z-h))/(2*h),
    )

def divergence(F: Field3, p: Sequence[float], h: float=1e-5) -> float:
    x,y,z=p
    return ((F(x+h,y,z)[0]-F(x-h,y,z)[0])+
            (F(x,y+h,z)[1]-F(x,y-h,z)[1])+
            (F(x,y,z+h)[2]-F(x,y,z-h)[2]))/(2*h)

def curl(F: Field3, p: Sequence[float], h: float=1e-5) -> tuple[float,float,float]:
    x,y,z=p
    dFz_dy=(F(x,y+h,z)[2]-F(x,y-h,z)[2])/(2*h)
    dFy_dz=(F(x,y,z+h)[1]-F(x,y,z-h)[1])/(2*h)
    dFx_dz=(F(x,y,z+h)[0]-F(x,y,z-h)[0])/(2*h)
    dFz_dx=(F(x+h,y,z)[2]-F(x-h,y,z)[2])/(2*h)
    dFy_dx=(F(x+h,y,z)[1]-F(x-h,y,z)[1])/(2*h)
    dFx_dy=(F(x,y+h,z)[0]-F(x,y-h,z)[0])/(2*h)
    return (dFz_dy-dFy_dz, dFx_dz-dFz_dx, dFy_dx-dFx_dy)

def line_integral(F: Field3, path: Callable[[float],Sequence[float]], a: float, b: float, n: int=1000) -> float:
    def g(t: float) -> float:
        p=path(t); eps=1e-5
        pm=path(t-eps); pp=path(t+eps)
        dr=[(pp[i]-pm[i])/(2*eps) for i in range(3)]
        v=F(*p)
        return sum(v[i]*dr[i] for i in range(3))
    return integrate(g,a,b,n)

def surface_flux(F: Field3, surface: Callable[[float,float],Sequence[float]],
                 u0: float,u1: float,v0: float,v1: float,nu: int=80,nv: int=80) -> float:
    """Midpoint quadrature of F dot (r_u cross r_v) over a parametric surface."""
    if nu<=0 or nv<=0: raise ValueError("nu/nv must be positive")
    du=(u1-u0)/nu; dv=(v1-v0)/nv; eps=1e-5; total=0.0
    for i in range(nu):
        u=u0+(i+.5)*du
        for j in range(nv):
            v=v0+(j+.5)*dv; p=surface(u,v)
            pu0=surface(u-eps,v); pu1=surface(u+eps,v)
            pv0=surface(u,v-eps); pv1=surface(u,v+eps)
            ru=[(pu1[k]-pu0[k])/(2*eps) for k in range(3)]
            rv=[(pv1[k]-pv0[k])/(2*eps) for k in range(3)]
            cross=(ru[1]*rv[2]-ru[2]*rv[1],ru[2]*rv[0]-ru[0]*rv[2],ru[0]*rv[1]-ru[1]*rv[0])
            fv=F(*p); total += sum(fv[k]*cross[k] for k in range(3))*du*dv
    return total
