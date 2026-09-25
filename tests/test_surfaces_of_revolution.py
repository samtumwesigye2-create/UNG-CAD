from math import pi
import pytest
from cad_core.surfaces_of_revolution import *
def test_gabriel_horn_finite_volume_infinite_area_classification():
    r=analyze_gabriel_horn(100,1000)
    assert r.volume==pytest.approx(pi*.99)
    assert r.infinite_volume==pytest.approx(pi)
    assert r.tail_volume_to_infinity==pytest.approx(pi/100)
    assert r.volume_converges is True
    assert r.surface_area_converges is False
def test_manufacturing_cutoff():
    assert analyze_gabriel_horn(10,min_feature=.25).manufacturable is False
    assert analyze_gabriel_horn(4,min_feature=.25).manufacturable is True
def test_profile_endpoints():
    p=gabriel_horn_profile(10,10)
    assert p[0]==(1.0,1.0)
    assert p[-1][0]==pytest.approx(10)
    assert p[-1][1]==pytest.approx(.1)
