import pytest
from cad_core.cutout_component import *

def test_cnc_corner_radius_gate():
 with pytest.raises(CADValidationError):
  CutoutComponent("id","rectangular",Vector2D(0,0),0,.25,-1,"cnc_mill_aluminum",dimensions={"width_mm":24,"height_mm":14,"corner_radius_mm":.5})

def test_valid_cnc_and_bbox():
 c=CutoutComponent("id","rectangular",Vector2D(0,0),0,.25,-1,"cnc_mill_aluminum",dimensions={"width_mm":24,"height_mm":14,"corner_radius_mm":1})
 assert c.calculate_compensated_bounding_box()==pytest.approx((24.5,14.5))

def test_custom_boundary_must_close():
 g=ArbitraryGeometry([(0,0),(1,0),(0,1)],[CustomSegment(0,1,"linear"),CustomSegment(1,2,"linear"),CustomSegment(2,1,"linear")])
 with pytest.raises(CADValidationError):CutoutComponent("id","arbitrary_custom",Vector2D(0,0),0,.2,-1,"3d_print_petg",custom_geometry=g)

def test_countersink_validation():
 h=MountingHole(0,0,3,Countersink(2,90))
 with pytest.raises(CADValidationError):CutoutComponent("id","circular",Vector2D(0,0),0,.2,-1,"3d_print_petg",[h],{"diameter_mm":8})
