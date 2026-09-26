import math
import pytest
from cad_core.orbital_dynamics import *

def test_schwarzschild_and_frame_dragging_scale():
    assert schwarzschild_radius(5.972e24)==pytest.approx(0.00887,rel=2e-3)
    assert weak_field_frame_dragging_scalar(1e34,7e6)>0

def test_circular_orbit_elements_and_propagation():
    mu=3.986004418e14;r=7e6;v=math.sqrt(mu/r)
    s=OrbitalState((r,0,0),(0,v,0))
    e=orbital_elements(mu,s)
    assert e["eccentricity"]<1e-10
    assert e["semi_major_axis_m"]==pytest.approx(r,rel=1e-10)
    n=rk4_two_body_step(s,mu,1.0)
    assert math.isfinite(n.position_m[0])

def test_lense_thirring_vector_and_residuals():
    w=lense_thirring_vector((0,0,1e34),(7e6,0,0))
    assert all(math.isfinite(x) for x in w)
    q=fit_residuals([(0,0,0),(1,0,0)],[(0,0,0),(2,0,0)])
    assert q["mae_m"]==pytest.approx(.5)
