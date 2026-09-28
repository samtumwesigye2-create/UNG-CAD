"""Calculus-3 parametric surface analysis for UNG-CAD.

Shared symbolic/numerical kernel. Engineering surface-load estimates are explicitly
not a CFD/Navier-Stokes solver.
"""
from __future__ import annotations
import math
from typing import Callable, Iterable
import numpy as np
import sympy as sp

class Calculus3Error(ValueError):
    pass

class UNGCadCalculus3Engine:
    def __init__(self, expr_x, expr_y, expr_z, u_sym="u", v_sym="v"):
        self.u, self.v = sp.symbols(f"{u_sym} {v_sym}", real=True)
        locals_ = {u_sym:self.u, v_sym:self.v}
        parse=lambda x: sp.sympify(x, locals=locals_) if isinstance(x,str) else sp.sympify(x).subs({sp.Symbol(u_sym):self.u,sp.Symbol(v_sym):self.v})
        self.r=sp.Matrix([parse(expr_x),parse(expr_y),parse(expr_z)])
        self.r_u=self.r.diff(self.u); self.r_v=self.r.diff(self.v)
        self.r_uu=self.r_u.diff(self.u); self.r_uv=self.r_u.diff(self.v); self.r_vv=self.r_v.diff(self.v)
        self.n=self.r_u.cross(self.r_v)
        self.E=sp.simplify(self.r_u.dot(self.r_u)); self.F=sp.simplify(self.r_u.dot(self.r_v)); self.G=sp.simplify(self.r_v.dot(self.r_v))
        self.metric_det=sp.simplify(self.E*self.G-self.F**2); self.W=sp.sqrt(self.metric_det)
        self._r=sp.lambdify((self.u,self.v),self.r,"numpy"); self._ru=sp.lambdify((self.u,self.v),self.r_u,"numpy")
        self._rv=sp.lambdify((self.u,self.v),self.r_v,"numpy"); self._n=sp.lambdify((self.u,self.v),self.n,"numpy"); self._W=sp.lambdify((self.u,self.v),self.W,"numpy")

    def jacobian(self,u,v):
        return np.column_stack((np.asarray(self._ru(u,v),float).reshape(3),np.asarray(self._rv(u,v),float).reshape(3)))

    def curvature_expressions(self):
        nhat=self.n/self.W
        L=sp.simplify(self.r_uu.dot(nhat)); M=sp.simplify(self.r_uv.dot(nhat)); N=sp.simplify(self.r_vv.dot(nhat))
        K=sp.simplify((L*N-M**2)/self.metric_det)
        H=sp.simplify((self.E*N-2*self.F*M+self.G*L)/(2*self.metric_det))
        return {"gaussian":K,"mean":H}

    def differential_geometry(self):
        """Return symbolic first/second fundamental forms and curvatures."""
        nhat=self.n/self.W
        L=sp.simplify(self.r_uu.dot(nhat)); M=sp.simplify(self.r_uv.dot(nhat)); N=sp.simplify(self.r_vv.dot(nhat))
        K=sp.simplify((L*N-M**2)/self.metric_det)
        H=sp.simplify((self.E*N-2*self.F*M+self.G*L)/(2*self.metric_det))
        return {"E":self.E,"F":self.F,"G":self.G,"L":L,"M":M,"N":N,
                "metric_det":self.metric_det,"gaussian":K,"mean":H}

    def evaluate_frame(self,u,v):
        """Position, tangent vectors and unit normal at one regular surface point."""
        p=np.asarray(self._r(u,v),float).reshape(3)
        ru=np.asarray(self._ru(u,v),float).reshape(3); rv=np.asarray(self._rv(u,v),float).reshape(3)
        n=np.cross(ru,rv); nl=np.linalg.norm(n)
        if nl<=1e-12: raise Calculus3Error("degenerate/singular surface point")
        return {"position":p.tolist(),"r_u":ru.tolist(),"r_v":rv.tolist(),"normal":(n/nl).tolist()}

    def parameter_curve(self, *, fixed_u=None, fixed_v=None, bounds=(-1,1), samples=101):
        """Sample a u=constant or v=constant coordinate curve on the surface."""
        if (fixed_u is None)==(fixed_v is None): raise Calculus3Error("set exactly one of fixed_u or fixed_v")
        ts=np.linspace(*bounds,samples); pts=[]
        for t in ts:
            u=fixed_u if fixed_u is not None else t; v=t if fixed_u is not None else fixed_v
            pts.append(np.asarray(self._r(u,v),float).reshape(3).tolist())
        return {"kind":"u_constant" if fixed_u is not None else "v_constant",
                "constant":float(fixed_u if fixed_u is not None else fixed_v),"points":pts}

    def arbitrary_surface_path(self, curve_u, curve_v, t, t_bounds, samples=101):
        """Sample an arbitrary symbolic path constrained to the parametric surface."""
        rt=self.r.subs({self.u:curve_u,self.v:curve_v}); fn=sp.lambdify(t,rt,"numpy")
        return [np.asarray(fn(x),float).reshape(3).tolist() for x in np.linspace(*t_bounds,samples)]

    def curvature_samples(self,u_bounds,v_bounds,res=25,singularity_tol=1e-12):
        """Sample Gaussian/mean curvature and flag singular parameter points."""
        geo=self.differential_geometry()
        kf=sp.lambdify((self.u,self.v),geo["gaussian"],"numpy"); hf=sp.lambdify((self.u,self.v),geo["mean"],"numpy")
        out=[]; singular=[]
        for u in np.linspace(*u_bounds,res):
            for v in np.linspace(*v_bounds,res):
                w=float(np.asarray(self._W(u,v)))
                if not np.isfinite(w) or abs(w)<=singularity_tol:
                    singular.append([float(u),float(v)]); continue
                out.append({"u":float(u),"v":float(v),"gaussian":float(kf(u,v)),"mean":float(hf(u,v))})
        return {"samples":out,"singular_uv":singular}

    @classmethod
    def enneper(cls):
        """Canonical Enneper minimal surface used as a differential-geometry regression."""
        return cls("u-u**3/3+u*v**2","-v+v**3/3-v*u**2","u**2-v**2")

    def surface_area(self,u_bounds,v_bounds,samples=101):
        if samples<2: raise Calculus3Error("samples must be >= 2")
        us=np.linspace(*u_bounds,samples); vs=np.linspace(*v_bounds,samples)
        U,V=np.meshgrid(us,vs,indexing="ij")
        z=np.asarray(self._W(U,V),dtype=float)
        return float(np.trapezoid(np.trapezoid(z,vs,axis=1),us,axis=0))

    def line_integral(self,curve_u,curve_v,t,t_bounds,field,samples=201):
        rt=self.r.subs({self.u:curve_u,self.v:curve_v}); dr=rt.diff(t)
        nr=sp.lambdify(t,rt,"numpy"); nd=sp.lambdify(t,dr,"numpy")
        ts=np.linspace(*t_bounds,samples); vals=[]
        for x in ts:
            p=np.asarray(nr(x),float).reshape(3); d=np.asarray(nd(x),float).reshape(3)
            vals.append(float(np.dot(np.asarray(field(*p),float),d)))
        return float(np.trapezoid(vals,ts))

    def stokes_boundary_circulation(self,u_bounds,v_bounds,field,samples=101):
        t=sp.symbols("t",real=True); a,b=u_bounds; c,d=v_bounds
        edges=[(t,c,(a,b)),(b,t,(c,d)),(t,d,(b,a)),(a,t,(d,c))]
        return sum(self.line_integral(U,V,t,rng,field,samples) for U,V,rng in edges)

    def lagrange(self,objective,constraint):
        f=sp.sympify(objective,locals={"u":self.u,"v":self.v}); g=sp.sympify(constraint,locals={"u":self.u,"v":self.v}); lam=sp.symbols("lambda",real=True)
        sols=sp.solve([sp.diff(f-lam*g,self.u),sp.diff(f-lam*g,self.v),g],(self.u,self.v,lam),dict=True)
        out=[]
        for s in sols:
            rec={"symbolic":{str(k):str(v) for k,v in s.items()}}
            try:
                uv=(float(sp.N(s[self.u])),float(sp.N(s[self.v]))); rec["u"],rec["v"]=uv; rec["coords"]=np.asarray(self._r(*uv),float).reshape(3).tolist(); rec["objective"]=float(sp.N(f.subs({self.u:uv[0],self.v:uv[1]})))
            except (TypeError,ValueError,KeyError): rec["numeric_valid"]=False
            else: rec["numeric_valid"]=True
            out.append(rec)
        return out

    def sample_surface(self,u_bounds,v_bounds,res=25):
        if res<2: raise Calculus3Error("resolution must be >= 2")
        us=np.linspace(*u_bounds,res); vs=np.linspace(*v_bounds,res); vertices=[]
        for u in us:
            for v in vs: vertices.append(np.asarray(self._r(u,v),float).reshape(3).tolist())
        triangles=[]
        for i in range(res-1):
            for j in range(res-1):
                a=i*res+j; b=(i+1)*res+j; c=b+1; d=a+1
                triangles.extend([(a,b,c),(a,c,d)])
        return {"vertices":vertices,"triangles":triangles,"resolution":res}

    def surface_load_estimate(self,u_bounds,v_bounds,density,viscosity,velocity,characteristic_length,res=20):
        if density<=0 or viscosity<=0 or characteristic_length<=0: raise Calculus3Error("density, viscosity and characteristic_length must be positive")
        U=np.asarray(velocity,float)
        if U.shape!=(3,) or not np.all(np.isfinite(U)): raise Calculus3Error("velocity must contain three finite values")
        nodes=[]
        for u in np.linspace(*u_bounds,res):
            for v in np.linspace(*v_bounds,res):
                p=np.asarray(self._r(u,v),float).reshape(3); n=np.asarray(self._n(u,v),float).reshape(3); nl=np.linalg.norm(n)
                if nl<=1e-12: continue
                nh=n/nl; normal_speed=max(0.0,-float(np.dot(U,nh))); Ut=U-np.dot(U,nh)*nh; speed=np.linalg.norm(Ut)
                qn=.5*density*normal_speed**2; Re=max(density*speed*characteristic_length/viscosity,1.0)
                cf=.664/math.sqrt(Re) if Re<5e5 else .0592/(Re**.2)
                shear=.5*density*speed**2*cf; shear_vec=np.zeros(3) if speed<=1e-12 else shear*Ut/speed
                pressure_vec=qn*nh; total=pressure_vec+shear_vec
                nodes.append({"position_xyz":p.tolist(),"normal_xyz":nh.tolist(),"normal_speed":normal_speed,"tangent_speed":float(speed),"reynolds":float(Re),"pressure_estimate_pa":float(qn),"shear_estimate_pa":float(shear),"resultant_vector":total.tolist()})
        return {"model":"surface_load_estimator","not_cfd":True,"units":{"length":"caller-defined","velocity":"m/s","pressure":"Pa"},"nodes":nodes}
