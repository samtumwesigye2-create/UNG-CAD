import math,pytest
from cad_core.material_cost import MaterialCostEstimator
def test_circle_bom_geometry():
 e=MaterialCostEstimator("aluminum_6061",3);r=e.generate_bill_of_materials([{"type":"circular","dimensions":{"diameter_mm":10},"position":{"x_mm":50,"y_mm":50}}],100,100);assert r["net_weight_kg"]>0;assert r["total_cut_length_meters"]>0.4
def test_rounded_rectangle_uses_arc_geometry():
 e=MaterialCostEstimator("acrylic",2);p,a=e._calculate_cutout_perimeter_and_area({"type":"rectangular","dimensions":{"width_mm":20,"height_mm":10,"corner_radius_mm":2}});assert p<60 and a<200
def test_unknown_material_not_silently_substituted():
 with pytest.raises(ValueError,match="unknown material"):MaterialCostEstimator("unobtainium",3)
def test_invalid_cut_area_rejected():
 e=MaterialCostEstimator("pla_plastic",2)
 with pytest.raises(ValueError,match="exceeds panel"):e.generate_bill_of_materials([{"type":"rectangular","dimensions":{"width_mm":20,"height_mm":20}}],10,10)
