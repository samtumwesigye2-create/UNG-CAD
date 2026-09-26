import math
import pytest
from cad_core.precision_geometry import Point, Viewport, points_equal, snap_value, rotate_point, scale_point, enforce_line_length

def test_viewport_roundtrip():
    v=Viewport(zoom=3.5,pan_x=12,pan_y=-4)
    p=Point(15.25,-2.75)
    sx,sy=v.world_to_screen(p)
    assert points_equal(v.screen_to_world(sx,sy),p,1e-12)

def test_grid_snap_and_exact_length():
    assert snap_value(2.49,1)==2
    assert snap_value(2.51,1)==3
    p=enforce_line_length(Point(0,0),Point(3,4),10)
    assert math.isclose(math.hypot(p.x,p.y),10,rel_tol=0,abs_tol=1e-12)

def test_rotation_cleans_quadrant_noise():
    p=rotate_point(Point(1,0),Point(0,0),90)
    assert points_equal(p,Point(0,1),1e-12)

def test_scale_about_origin():
    assert scale_point(Point(3,4),Point(1,2),2)==Point(5,6)

def test_invalid_inputs():
    with pytest.raises(ValueError): Viewport(zoom=0)
    with pytest.raises(ValueError): snap_value(1,0)
    with pytest.raises(ValueError): enforce_line_length(Point(0,0),Point(1,0),-1)
