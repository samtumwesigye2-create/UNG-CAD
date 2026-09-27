import pytest
from cad_core.structural_ribs import *
def test_valid_rib():
 r=parse_structural_ribs([{"rib_id":"r","start_point":{"x":10,"y":10},"end_point":{"x":50,"y":10},"thickness_mm":3,"height_mm":6}],100,80)[0];assert r.length_mm==40
def test_zero_length_rejected():
 with pytest.raises(RibValidationError):parse_structural_ribs([{"rib_id":"r","start_point":{"x":1,"y":1},"end_point":{"x":1,"y":1}}])
def test_outside_panel_rejected():
 with pytest.raises(RibValidationError):parse_structural_ribs([{"rib_id":"r","start_point":{"x":1,"y":1},"end_point":{"x":101,"y":1}}],100,80)
def test_bad_profile_rejected():
 with pytest.raises(RibValidationError):parse_structural_ribs([{"rib_id":"r","start_point":{"x":1,"y":1},"end_point":{"x":2,"y":1},"profile_type":"x"}])
