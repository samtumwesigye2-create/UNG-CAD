import math
import pytest
from cad_core.circle_geometry import Point3D,CADCircle3D,scale_cad_circle,rotate_cad_circle_z

def test_tolerance_driven_circle_and_arbitrary_plane():
    c=CADCircle3D(Point3D(1,2,3),10,Point3D(1,0,0))
    pts=c.generate_tessellated_vertices(.01)
    assert len(pts)>=12
    assert all(abs(p.x-1)<1e-9 for p in pts)

def test_scale_preserves_parametric_intent():
    c=CADCircle3D(Point3D(1,2,3),5,Point3D(0,0,1))
    s=scale_cad_circle(c,2)
    assert s.center==Point3D(2,4,6) and s.radius==10 and s.normal==c.normal

def test_z_rotation_rotates_normal_too():
    c=CADCircle3D(Point3D(1,0,2),5,Point3D(1,0,0))
    r=rotate_cad_circle_z(c,90)
    assert abs(r.center.x)<1e-12 and r.center.y==pytest.approx(1)
    assert abs(r.normal.x)<1e-12 and r.normal.y==pytest.approx(1)
    assert r.radius==5

def test_invalid_parameters_are_rejected():
    c=CADCircle3D(Point3D(0,0,0),1,Point3D(0,0,1))
    with pytest.raises(ValueError): c.generate_tessellated_vertices(0)
    with pytest.raises(ValueError): scale_cad_circle(c,0)
