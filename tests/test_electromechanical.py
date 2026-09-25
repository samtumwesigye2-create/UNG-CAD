from math import sqrt
import pytest
from cad_core.electromechanical import Connection, solve_three_phase, winding_graph

def test_delta_relationships():
    r=solve_three_phase(480,30,Connection.DELTA,.9,1.2)
    assert r.phase_voltage==480
    assert r.phase_current==pytest.approx(30/sqrt(3))
    assert r.real_power_w==pytest.approx(sqrt(3)*480*30*.9)
    assert r.copper_loss_w==pytest.approx(3*(30/sqrt(3))**2*1.2)

def test_wye_relationships():
    r=solve_three_phase(480,30,Connection.WYE)
    assert r.phase_voltage==pytest.approx(480/sqrt(3))
    assert r.phase_current==30

def test_winding_graphs():
    assert winding_graph("delta")[-1]==("L3","W3","L1")
    assert winding_graph("wye")[0]==("L1","W1","N")

def test_rejects_invalid_pf():
    with pytest.raises(ValueError): solve_three_phase(480,30,"delta",1.1)
