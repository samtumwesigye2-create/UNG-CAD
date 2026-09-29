import math

from cad_core.geometry_validation import bed_fit, validate_triangle_mesh


def tetrahedron():
    a=(0,0,0); b=(1,0,0); c=(0,1,0); d=(0,0,1)
    # Consistent outward winding.
    return [
        (a,c,b),
        (a,b,d),
        (a,d,c),
        (b,c,d),
    ]


def test_closed_tetrahedron_is_watertight():
    r=validate_triangle_mesh(tetrahedron(), require_watertight=True)
    assert r.valid
    assert r.watertight
    assert r.boundary_edges == 0
    assert r.nonmanifold_edges == 0
    assert r.connected_components == 1


def test_open_surface_is_advisory_by_default():
    r=validate_triangle_mesh([((0,0,0),(1,0,0),(0,1,0))])
    assert r.valid
    assert not r.watertight
    assert r.boundary_edges == 3
    assert r.errors == ()
    assert r.warnings


def test_open_surface_can_be_promoted_to_hard_gate():
    r=validate_triangle_mesh([((0,0,0),(1,0,0),(0,1,0))], require_watertight=True)
    assert not r.valid
    assert r.errors


def test_degenerate_face_fails():
    r=validate_triangle_mesh([((0,0,0),(1,0,0),(2,0,0))])
    assert not r.valid
    assert r.degenerate_faces == 1


def test_nonfinite_coordinate_fails():
    r=validate_triangle_mesh([((0,0,0),(1,0,0),(0,math.inf,0))])
    assert not r.valid
    assert not r.finite


def test_disconnected_components_are_reported():
    tris=[
        ((0,0,0),(1,0,0),(0,1,0)),
        ((10,0,0),(11,0,0),(10,1,0)),
    ]
    r=validate_triangle_mesh(tris)
    assert r.valid
    assert r.connected_components == 2


def test_bed_fit_reports_overflow():
    ok=bed_fit((100,80,20),(220,220,220),clearance=5)
    assert ok["fits"]
    bad=bed_fit((215,80,20),(220,220,220),clearance=5)
    assert not bad["fits"]
    assert bad["overflow"][0] == 5


def test_parametric_cylinder_mesh_passes_manufacturing_validation():
    from cad_core.feature_timeline import Point3D, ParametricCylinder, tessellated_surface_triangles
    tris=tessellated_surface_triangles(ParametricCylinder(Point3D(0,0,0),5,4).tessellate(.05))
    r=validate_triangle_mesh(tris)
    assert r.valid
    assert r.triangle_count > 0
    assert r.dimensions[0] > 9.9
    assert r.dimensions[1] > 9.9
    assert r.dimensions[2] == 4


def test_build_volume_clearance_is_enforced():
    fit=bed_fit((210,210,210),(220,220,220),clearance=5)
    assert fit["fits"]
    fit=bed_fit((210.01,210,210),(220,220,220),clearance=5)
    assert not fit["fits"]
