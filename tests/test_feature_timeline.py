import pytest
from cad_core.feature_timeline import *

def test_arbitrary_plane_and_profiles():
    t=UNGCadFeatureTimeline()
    t.add_circle("c1",ParametricCircle(Point3D(1,0,2),5,Vector3D(1,0,0)))
    out=t.process_api_action("c1","rotate_z",90,"ui")
    assert out["quality"]=="ui"
    assert out["meta"]["center"][0]==pytest.approx(0,abs=1e-12)
    assert out["meta"]["center"][1]==pytest.approx(1)
    assert out["meta"]["normal"][1]==pytest.approx(1)

def test_export_has_more_or_equal_geometry_than_ui():
    a=ParametricCircle(Point3D(0,0,0),20)
    t=UNGCadFeatureTimeline();t.add_circle("c",a)
    ui=t.process_api_action("c","rotate_z",0,"ui")
    ex=t.process_api_action("c","rotate_z",0,"export")
    assert len(ex["vertices"])>=len(ui["vertices"])

def test_strict_invalid_inputs():
    with pytest.raises(ValueError): ParametricCircle(Point3D(0,0,0),1,Vector3D(0,0,0))
    t=UNGCadFeatureTimeline();t.add_circle("c",ParametricCircle(Point3D(0,0,0),1))
    with pytest.raises(ValueError): t.process_api_action("c","scale",1,"preview")
    with pytest.raises(ValueError): t.process_api_action("c","scale",0,"ui")
    with pytest.raises(NotImplementedError): t.process_api_action("c","skew",1,"ui")

def test_tolerance_safety_limit():
    c=ParametricCircle(Point3D(0,0,0),1000)
    with pytest.raises(ToleranceExceededError): c.tessellate(1e-12,max_segments=100)


def test_cylinder_manufacturing_mesh_preserves_round_xy_profile():
    cyl=ParametricCylinder(Point3D(0,0,0),5,4)
    tris=tessellated_surface_triangles(cyl.tessellate(.05))
    assert len(tris) >= 64
    # A rectangle has only four XY boundary directions. A real tessellated
    # circle must retain many distinct perimeter vertices.
    xy={(round(p["x"],5),round(p["y"],5)) for tri in tris for p in tri}
    perimeter={(x,y) for x,y in xy if abs((x*x+y*y)**0.5-5)<1e-3}
    assert len(perimeter) >= 16
    assert max(x for x,_ in perimeter)==pytest.approx(5,abs=.05)
    assert min(x for x,_ in perimeter)==pytest.approx(-5,abs=.05)
    assert max(y for _,y in perimeter)==pytest.approx(5,abs=.05)
    assert min(y for _,y in perimeter)==pytest.approx(-5,abs=.05)
