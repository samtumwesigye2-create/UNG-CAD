"""Dependency-free numerical solvers for shared UNG engineering workflows."""
from dataclasses import dataclass
from typing import Callable, Sequence

@dataclass(frozen=True)
class SolverResult:
    x: float
    value: float
    iterations: int
    converged: bool

def bisection(f: Callable[[float],float], lo: float, hi: float, tol: float=1e-9, max_iter: int=100) -> SolverResult:
    flo,fhi=f(lo),f(hi)
    if flo==0:return SolverResult(lo,0.0,0,True)
    if fhi==0:return SolverResult(hi,0.0,0,True)
    if flo*fhi>0:raise ValueError("interval must bracket a root")
    mid=lo
    for i in range(1,max_iter+1):
        mid=(lo+hi)/2; fm=f(mid)
        if abs(fm)<=tol or abs(hi-lo)/2<=tol:return SolverResult(mid,fm,i,True)
        if flo*fm<=0:hi=mid
        else:lo=mid;flo=fm
    return SolverResult(mid,f(mid),max_iter,False)

def newton(f, df, x0: float, tol: float=1e-9, max_iter: int=50) -> SolverResult:
    x=float(x0)
    for i in range(1,max_iter+1):
        fx=f(x)
        if abs(fx)<=tol:return SolverResult(x,fx,i-1,True)
        d=df(x)
        if abs(d)<1e-15:raise ZeroDivisionError("derivative too small")
        x-=fx/d
    return SolverResult(x,f(x),max_iter,abs(f(x))<=tol)

def numerical_gradient(f, x: Sequence[float], h: float=1e-6):
    x=list(map(float,x)); g=[]
    for i in range(len(x)):
        a=x.copy();b=x.copy();a[i]+=h;b[i]-=h
        g.append((f(a)-f(b))/(2*h))
    return g

def numerical_jacobian(func, x: Sequence[float], h: float=1e-6):
    x=list(map(float,x)); base=list(func(x)); J=[[0.0]*len(x) for _ in base]
    for j in range(len(x)):
        a=x.copy();b=x.copy();a[j]+=h;b[j]-=h
        fa,fb=list(func(a)),list(func(b))
        for i in range(len(base)):J[i][j]=(fa[i]-fb[i])/(2*h)
    return J

def numerical_hessian(f, x: Sequence[float], h: float=1e-4):
    x=list(map(float,x)); n=len(x); H=[[0.0]*n for _ in range(n)]; f0=f(x)
    for i in range(n):
        xp=x.copy();xm=x.copy();xp[i]+=h;xm[i]-=h
        H[i][i]=(f(xp)-2*f0+f(xm))/(h*h)
        for j in range(i+1,n):
            pp=x.copy();pm=x.copy();mp=x.copy();mm=x.copy()
            pp[i]+=h;pp[j]+=h;pm[i]+=h;pm[j]-=h;mp[i]-=h;mp[j]+=h;mm[i]-=h;mm[j]-=h
            H[i][j]=H[j][i]=(f(pp)-f(pm)-f(mp)+f(mm))/(4*h*h)
    return H
