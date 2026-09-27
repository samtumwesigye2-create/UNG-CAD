from cad_core.interference_engine import GeometryInterferenceEngine
def circle(x=50,y=40):
 return {"component_id":"c","type":"circular","position":{"x_mm":x,"y_mm":y},"dimensions":{"diameter_mm":10},"mounting_holes":[]}
def test_rib_circle_collision():
 r={"rib_id":"r","start_point":{"x":0,"y":40},"end_point":{"x":100,"y":40},"thickness_mm":3}
 assert GeometryInterferenceEngine(1).check([circle()], [r])[0].kind=="rib_cutout"
def test_rib_clear():
 r={"rib_id":"r","start_point":{"x":0,"y":5},"end_point":{"x":100,"y":5},"thickness_mm":3}
 assert not GeometryInterferenceEngine(1).check([circle()], [r])
def test_rotated_mounting_hole_collision():
 c=circle(50,40);c["rotation"]=90;c["mounting_holes"]=[{"offset_x_mm":10,"offset_y_mm":0,"diameter_mm":4}]
 r={"rib_id":"r","start_point":{"x":0,"y":50},"end_point":{"x":100,"y":50},"thickness_mm":2}
 assert any(x.kind=="rib_mounting_hole" for x in GeometryInterferenceEngine().check([c],[r]))
def test_component_envelope_overlap():
 e=[{"component_id":"a","position":{"x_mm":10,"y_mm":10},"width_mm":10,"height_mm":10},{"component_id":"b","position":{"x_mm":14,"y_mm":10},"width_mm":10,"height_mm":10}]
 assert GeometryInterferenceEngine().check([],component_envelopes=e)[0].kind=="component_envelope"
