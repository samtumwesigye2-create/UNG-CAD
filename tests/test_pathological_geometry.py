import math
import pytest
from cad_core.pathological_geometry import gabriel_horn

def test_gabriel_horn_convergence_contract():
    r=gabriel_horn(100)
    assert r.volume_converges is True
    assert r.surface_area_converges is False
    assert r.infinite_volume == pytest.approx(math.pi)
    assert r.finite_volume+r.remaining_infinite_tail_volume == pytest.approx(math.pi)

def test_truncation_feature_gate():
    assert gabriel_horn(10,.1).manufacturable is True
    r=gabriel_horn(100,.1)
    assert r.manufacturable is False
    assert "below" in r.reason

def test_surface_area_grows_with_truncation():
    assert gabriel_horn(100).finite_surface_area > gabriel_horn(10).finite_surface_area

def test_invalid_truncation():
    with pytest.raises(ValueError): gabriel_horn(1)
