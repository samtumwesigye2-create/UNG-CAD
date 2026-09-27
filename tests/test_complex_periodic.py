import cmath, math
from cad_core.complex_periodic import *

def test_euler_identity():
    for x in [0,.3,math.pi,2*math.pi]:
        assert abs(euler(x)-(math.cos(x)+1j*math.sin(x)))<1e-12

def test_phasor_roundtrip():
    p=Phasor(2.5,.7); q=Phasor.from_complex(p.complex())
    assert math.isclose(q.amplitude,p.amplitude,rel_tol=1e-12)
    assert math.isclose(q.phase,p.phase,rel_tol=1e-12)

def test_trig_family():
    x=.8; f=trig_family(x)
    assert math.isclose(f["sin(theta)"],math.sin(x))
    assert math.isclose(f["sin(2theta)"],math.sin(2*x))
    assert math.isclose(f["sin(theta/2)"],math.sin(x/2))

def test_helix():
    assert helix(0,2,4)==(2.0,0.0,0.0)
    x,y,z=helix(2*math.pi,2,4)
    assert math.isclose(x,2,abs_tol=1e-12) and math.isclose(y,0,abs_tol=1e-12)
    assert math.isclose(z,4)

def test_rolle():
    f=lambda x: (x-1)**2
    c=rolle_stationary_point(f,0,2)
    assert abs(c-1)<1e-4

def test_draco_grid_limits():
    pts=sample_pan_tilt()
    assert len(pts)==37*21
    pans=[p for p,t in pts]; tilts=[t for p,t in pts]
    assert math.isclose(min(pans),-math.pi/2) and math.isclose(max(pans),math.pi/2)
    assert math.isclose(min(tilts),math.radians(-25)) and math.isclose(max(tilts),math.radians(25))
