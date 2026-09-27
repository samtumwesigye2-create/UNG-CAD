import pytest
from cad_core.cutout_component import CutoutComponent, Vector2D, CADValidationError
from cad_core.layout_boundary import LayoutBoundaryEvaluator

@pytest.fixture
def standard_panel_evaluator():
    return LayoutBoundaryEvaluator(panel_width=200.0,panel_height=100.0,minimum_bridge_mm=4.0)

@pytest.fixture
def base_rect_json():
    return {"component_id":"test-rect-id-001","type":"rectangular","position":{"x_mm":50.0,"y_mm":50.0},"rotation":0.0,"clearance_mm":0.2,"depth_mm":-1,"tolerance_profile":"cnc_mill_aluminum","dimensions":{"width_mm":30.0,"height_mm":20.0,"corner_radius_mm":2.0}}

def component(d):
    return CutoutComponent(component_id=d["component_id"],type=d["type"],position=Vector2D(**d["position"]),rotation=d["rotation"],clearance_mm=d["clearance_mm"],depth_mm=d["depth_mm"],tolerance_profile=d["tolerance_profile"],dimensions=d["dimensions"])

def test_valid_rectangular_component_instantiation(base_rect_json):
    item=component(base_rect_json);assert item.validate_manufacturing_constraints() is True

def test_cnc_corner_radius_violation(base_rect_json):
    base_rect_json["dimensions"]["corner_radius_mm"]=0.5
    with pytest.raises(CADValidationError,match="violates configured 2mm-tool minimum"):
        component(base_rect_json)

def test_negative_depth_validation_rejection(base_rect_json):
    base_rect_json["depth_mm"]=-4.5
    with pytest.raises(CADValidationError,match="Invalid depth"):
        component(base_rect_json)

def test_layout_perimeter_breach_detection(standard_panel_evaluator):
    c={"component_id":"breaching-component","type":"circular","position":{"x_mm":2.0,"y_mm":50.0},"clearance_mm":0.0,"dimensions":{"diameter_mm":10.0}}
    ok,errors=standard_panel_evaluator.verify_layout([c]);assert not ok;assert any("breaches safe outer panel" in e for e in errors)

def test_inter_component_collision_detection(standard_panel_evaluator):
    a={"component_id":"circle-left","type":"circular","position":{"x_mm":50.0,"y_mm":50.0},"clearance_mm":0.0,"dimensions":{"diameter_mm":20.0}}
    b={"component_id":"circle-right","type":"circular","position":{"x_mm":65.0,"y_mm":50.0},"clearance_mm":0.0,"dimensions":{"diameter_mm":20.0}}
    ok,errors=standard_panel_evaluator.verify_layout([a,b]);assert not ok;assert any("Collision/Thin Wall structural risk" in e for e in errors)

def test_safe_layout_passes_evaluation(standard_panel_evaluator):
    a={"component_id":"safe-c1","type":"circular","position":{"x_mm":30.0,"y_mm":50.0},"dimensions":{"diameter_mm":10.0}}
    b={"component_id":"safe-c2","type":"circular","position":{"x_mm":100.0,"y_mm":50.0},"dimensions":{"diameter_mm":10.0}}
    ok,errors=standard_panel_evaluator.verify_layout([a,b]);assert ok and errors==[]
