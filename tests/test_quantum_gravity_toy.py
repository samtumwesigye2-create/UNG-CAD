import math
from cad_core.quantum_gravity_toy import planck_units,lqg_area,black_hole,entropy_comparison,GAMMA_SIMPLE

def test_planck_units_positive():
    assert all(v>0 for v in planck_units().values())

def test_area_positive():
    assert lqg_area([0.5])>0

def test_black_hole_scaling():
    a=black_hole(1.0); b=black_hole(2.0)
    assert math.isclose(b["radius_m"]/a["radius_m"],2.0)
    assert math.isclose(b["area_m2"]/a["area_m2"],4.0)
    assert math.isclose(b["temperature_K"]/a["temperature_K"],0.5)
    assert math.isclose(b["evaporation_years"]/a["evaporation_years"],8.0)

def test_calibrated_entropy_ratio_and_metadata():
    r=entropy_comparison(1.98847e30,GAMMA_SIMPLE)
    assert math.isclose(r["ratio"],1.0,rel_tol=1e-12)
    assert r["metadata"]["toy_model"] is True
