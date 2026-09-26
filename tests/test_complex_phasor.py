import math
from cad_core.complex_phasor import Phasor,euler,magnitude,three_phase,euler_identity_error

def test_euler_unit_circle_and_identity():
    assert math.isclose(magnitude(euler(1.234)),1.0,rel_tol=1e-12)
    assert euler_identity_error()<1e-12

def test_phasor_derivative():
    p=Phasor(2.0,0.3,60.0); t=.002
    assert abs(p.derivative(t)-1j*2*math.pi*60*p.value(t))<1e-10

def test_balanced_three_phase_sums_to_zero():
    a,b,c=three_phase(120,60,.001)
    assert abs(a+b+c)<1e-10
