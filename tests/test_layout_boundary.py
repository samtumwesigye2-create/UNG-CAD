import pytest
from cad_core.layout_boundary import LayoutBoundaryEvaluator
def c(i,x,y,d=10):return {"component_id":i,"type":"circular","position":{"x_mm":x,"y_mm":y},"rotation":0,"clearance_mm":0,"geometry_payload":{"diameter_mm":d}}
def test_panel_border(): assert not LayoutBoundaryEvaluator(100,80,3).verify_layout([c("a",5,40,10)])[0]
def test_circle_bridge(): assert not LayoutBoundaryEvaluator(100,80,3).verify_layout([c("a",20,20),c("b",31,20)])[0]
def test_safe_circles(): assert LayoutBoundaryEvaluator(100,80,3).verify_layout([c("a",20,20),c("b",40,20)])[0]
def test_rotated_rectangle_bounds():
 e=LayoutBoundaryEvaluator(100,80,3);d={"component_id":"r","type":"rectangular","position":{"x_mm":50,"y_mm":40},"rotation":45,"clearance_mm":0,"geometry_payload":{"width_mm":20,"height_mm":10}}
 b=e._get_bounding_box(d);assert b[2]-b[0]>20
