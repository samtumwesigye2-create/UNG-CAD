import pytest
from cad_core.gcode_generator import *
def circle(d=10):
 return {"component_id":"c","type":"circular","position":{"x_mm":20,"y_mm":30},"clearance_mm":0,"geometry_payload":{"diameter_mm":d}}
def gen():return UngCadGCodeGenerator(2,1200,400,5,3.2,1,12000)
def test_tool_radius_compensation():
 s=gen().generate_circular_contour_gcode([circle()]);assert "X24.000 Y30.000" in s and "I-4.000" in s
def test_depth_steps_and_final_depth():
 s=gen().generate_circular_contour_gcode([circle()]);assert "Z-1.000" in s and "Z-3.200" in s
def test_tool_must_fit():
 with pytest.raises(GCodeValidationError):gen().generate_circular_contour_gcode([circle(2)])
def test_no_assumed_home_motion():
 s=gen().generate_circular_contour_gcode([circle()]);assert "G00 X0 Y0" not in s
def test_requires_explicit_positive_parameters():
 with pytest.raises(GCodeValidationError):UngCadGCodeGenerator(0,1200,400,5,3,1,12000)
