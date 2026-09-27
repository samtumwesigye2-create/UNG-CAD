import uuid,pytest
from cad_core.cutout_contract import parse_cutout

def custom(vertices,segments):
 return {"component_id":str(uuid.uuid4()),"type":"arbitrary_custom","position":{"x_mm":0,"y_mm":0},"rotation":0,"clearance_mm":.2,"depth_mm":-1,"geometry_payload":{"vertices":vertices,"segments":segments}}

def test_mixed_linear_arc_bezier_boundary():
 d=custom([[0,0],[10,0],[10,10],[0,10]],[
  {"start_idx":0,"end_idx":1,"type":"linear"},
  {"start_idx":1,"end_idx":2,"type":"arc","arc_bulge":.41421356},
  {"start_idx":2,"end_idx":3,"type":"bezier","control_points":[[7,12],[3,12]]},
  {"start_idx":3,"end_idx":0,"type":"linear"}])
 assert parse_cutout(d).geometry["segments"][1]["arc_bulge"]==pytest.approx(.41421356)

def test_bad_segment_index_rejected():
 d=custom([[0,0],[1,0],[0,1]],[{"start_idx":0,"end_idx":9,"type":"linear"}]*3)
 with pytest.raises(ValueError): parse_cutout(d)

def test_arc_requires_bulge():
 d=custom([[0,0],[1,0],[0,1]],[{"start_idx":0,"end_idx":1,"type":"arc"},{"start_idx":1,"end_idx":2,"type":"linear"},{"start_idx":2,"end_idx":0,"type":"linear"}])
 with pytest.raises(ValueError): parse_cutout(d)
