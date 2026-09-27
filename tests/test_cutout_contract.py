import uuid,pytest
from cad_core.cutout_contract import parse_cutout,compensated_geometry

def base(kind="rectangular",geom=None):
    return {"component_id":str(uuid.uuid4()),"type":kind,"position":{"x_mm":10,"y_mm":20},"rotation":0,"clearance_mm":.2,"depth_mm":-1,"tolerance_profile":"3d_print_pla","geometry_payload":geom or {"width_mm":10,"height_mm":5}}

def test_rectangular_cutout_clearance_compensation():
    c=parse_cutout(base())
    assert compensated_geometry(c)["width_mm"]==pytest.approx(10.4)
    assert compensated_geometry(c)["height_mm"]==pytest.approx(5.4)

def test_circular_cutout():
    c=parse_cutout(base("circular",{"diameter_mm":8}))
    assert compensated_geometry(c)["diameter_mm"]==pytest.approx(8.4)

def test_invalid_depth_blocked():
    d=base();d["depth_mm"]=0
    with pytest.raises(ValueError):parse_cutout(d)
