import sympy as sp
import numpy as np
from cad_core.calculus3_engine import UNGCadCalculus3Engine

def test_saddle_lagrange_and_mesh():
    e=UNGCadCalculus3Engine("u","v","u**2-v**2")
    pts=e.lagrange("u**2-v**2","u**2+v**2-1")
    vals=sorted(round(p["objective"],6) for p in pts if p.get("numeric_valid"))
    assert vals==[-1.0,-1.0,1.0,1.0]
    m=e.sample_surface((-1,1),(-1,1),10)
    assert len(m["vertices"])==100 and len(m["triangles"])==162

def test_stokes_boundary_regression():
    e=UNGCadCalculus3Engine("u","v","u**2-v**2")
    F=lambda x,y,z: np.array([-y,x*x,z])
    val=e.stokes_boundary_circulation((-1,1),(-1,1),F,301)
    assert np.isfinite(val)

def test_surface_load_metadata():
    e=UNGCadCalculus3Engine("u","v","0.2*(u**2-v**2)")
    out=e.surface_load_estimate((-1,1),(-1,1),1.225,1.81e-5,[30,0,-10],0.1,8)
    assert out["not_cfd"] is True and len(out["nodes"])==64
