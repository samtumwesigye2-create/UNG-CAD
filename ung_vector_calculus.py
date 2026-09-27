"""UNG-CAD shared vector calculus and field-analysis core.

Dependency-free numerical primitives for CAD/manufacturing and sensor-field
analysis. Functions accept callables so they can be connected to analytical
models, sampled fields, meshes, or sensor interpolation layers.
"""
from __future__ import annotations
import math
from typing import Callable, Iterable, Sequence

Vec3 = tuple[float, float, float]
ScalarField = Callable[[float, float, float], float]
VectorField = Callable[[float, float, float], Vec3]

def dot(a: Vec3, b: Vec3) -> float:
    return sum(x*y for x,y in zip(a,b))

def cross(a: Vec3, b: Vec3) -> Vec3:
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])

def norm(v: Vec3) -> float:
    return math.sqrt(dot(v,v))

def unit(v: Vec3) -> Vec3:
    n=norm(v)
    if n == 0: raise ValueError("zero vector has no direction")
    return tuple(x/n for x in v)  # type: ignore

def gradient(f: ScalarField, p: Vec3, h: float=1e-5) -> Vec3:
    x,y,z=p
    return ((f(x+h,y,z)-f(x-h,y,z))/(2*h),
            (f(x,y+h,z)-f(x,y-h,z))/(2*h),
            (f(x,y,z+h)-f(x,y,z-h))/(2*h))

def directional_derivative(f: ScalarField, p: Vec3, direction: Vec3, h: float=1e-5) -> float:
    return dot(gradient(f,p,h), unit(direction))

def jacobian(F: VectorField, p: Vec3, h: float=1e-5) -> tuple[Vec3,Vec3,Vec3]:
    x,y,z=p
    cols=[]
    for d in ((h,0,0),(0,h,0),(0,0,h)):
        fp=F(x+d[0],y+d[1],z+d[2]); fm=F(x-d[0],y-d[1],z-d[2])
        cols.append(tuple((fp[i]-fm[i])/(2*h) for i in range(3)))
    return tuple(tuple(cols[j][i] for j in range(3)) for i in range(3))  # type: ignore

def divergence(F: VectorField, p: Vec3, h: float=1e-5) -> float:
    J=jacobian(F,p,h)
    return J[0][0]+J[1][1]+J[2][2]

def curl(F: VectorField, p: Vec3, h: float=1e-5) -> Vec3:
    J=jacobian(F,p,h)
    return (J[2][1]-J[1][2], J[0][2]-J[2][0], J[1][0]-J[0][1])

def hessian(f: ScalarField, p: Vec3, h: float=1e-4):
    x,y,z=p; q=(x,y,z); H=[]
    for i in range(3):
        row=[]
        for j in range(3):
            ei=[0.,0.,0.]; ej=[0.,0.,0.]; ei[i]=h; ej[j]=h
            def ev(si,sj): return f(*(q[k]+si*ei[k]+sj*ej[k] for k in range(3)))
            row.append((ev(1,1)-ev(1,-1)-ev(-1,1)+ev(-1,-1))/(4*h*h))
        H.append(tuple(row))
    return tuple(H)

def trapz(values: Sequence[float], step: float) -> float:
    if len(values)<2: return 0.0
    return step*(0.5*values[0]+sum(values[1:-1])+0.5*values[-1])

def line_integral(F: VectorField, curve: Callable[[float],Vec3], t0:float, t1:float, n:int=512) -> float:
    if n<2: raise ValueError("n must be >= 2")
    dt=(t1-t0)/n; total=0.0
    for i in range(n):
        a=t0+i*dt; b=a+dt; pa=curve(a); pb=curve(b)
        dr=tuple(pb[k]-pa[k] for k in range(3))
        mid=tuple((pa[k]+pb[k])/2 for k in range(3))
        total += dot(F(*mid),dr)
    return total

def flux_triangles(F: VectorField, triangles: Iterable[tuple[Vec3,Vec3,Vec3]]) -> float:
    total=0.0
    for a,b,c in triangles:
        ab=tuple(b[i]-a[i] for i in range(3)); ac=tuple(c[i]-a[i] for i in range(3))
        area_vec=tuple(v*0.5 for v in cross(ab,ac))
        centroid=tuple((a[i]+b[i]+c[i])/3 for i in range(3))
        total += dot(F(*centroid),area_vec)
    return total

def surface_normals(triangles: Iterable[tuple[Vec3,Vec3,Vec3]]):
    out=[]
    for a,b,c in triangles:
        out.append(unit(cross(tuple(b[i]-a[i] for i in range(3)),tuple(c[i]-a[i] for i in range(3)))))
    return out

def lorentz_force(q:float, E:Vec3, v:Vec3, B:Vec3) -> Vec3:
    vxB=cross(v,B)
    return tuple(q*(E[i]+vxB[i]) for i in range(3))  # type: ignore

def torque(r:Vec3, force:Vec3) -> Vec3:
    return cross(r,force)

def rk4_step(state:Vec3, velocity:VectorField, dt:float) -> Vec3:
    def add(a,b,s=1.0): return tuple(a[i]+s*b[i] for i in range(3))
    k1=velocity(*state); k2=velocity(*add(state,k1,dt/2))
    k3=velocity(*add(state,k2,dt/2)); k4=velocity(*add(state,k3,dt))
    return tuple(state[i]+dt*(k1[i]+2*k2[i]+2*k3[i]+k4[i])/6 for i in range(3))  # type: ignore

def streamline(F:VectorField, seed:Vec3, step:float=0.02, count:int=200):
    pts=[seed]
    for _ in range(count): pts.append(rk4_step(pts[-1],F,step))
    return pts

def second_derivative_1d(f:Callable[[float],float], x:float, h:float=1e-4)->float:
    return (f(x+h)-2*f(x)+f(x-h))/(h*h)

def inflection_candidates(f:Callable[[float],float], xs:Sequence[float], h:float=1e-4):
    vals=[second_derivative_1d(f,x,h) for x in xs]; out=[]
    for i in range(1,len(xs)):
        if vals[i-1]*vals[i] < 0: out.append((xs[i-1]+xs[i])/2)
    return out

def divergence_theorem_check(F:VectorField, volume_samples:Iterable[tuple[Vec3,float]],
                             boundary_triangles:Iterable[tuple[Vec3,Vec3,Vec3]], h:float=1e-5):
    volume=sum(divergence(F,p,h)*dv for p,dv in volume_samples)
    flux=flux_triangles(F,boundary_triangles)
    return {"volume_integral":volume,"surface_flux":flux,"absolute_error":abs(volume-flux)}
