import math
from cad_core.coordinate_flattener import CoordinateFlattener
def close(a,b):assert math.isclose(a,b,abs_tol=1e-8)
def test_nested_transform_and_rotation():
 root={"position":{"x":10,"y":20,"z":0},"rotation":90,"cutouts":[],"child_panels":[{"position":{"x":10,"y":0,"z":0},"rotation":90,"cutouts":[{"component_id":"c","position":{"x_mm":5,"y_mm":0},"rotation":10}]}]}
 c=CoordinateFlattener.flatten_assembly(root)[0];close(c["position"]["x_mm"],5);close(c["position"]["y_mm"],30);close(c["rotation"],190)
def test_mounting_offsets_remain_local_to_avoid_double_rotation():
 root={"position":{"x":0,"y":0,"z":0},"rotation":90,"cutouts":[{"component_id":"c","position":{"x_mm":10,"y_mm":0},"rotation":30,"mounting_holes":[{"offset_x_mm":2,"offset_y_mm":0,"diameter_mm":3}]}]}
 c=CoordinateFlattener.flatten_assembly(root)[0];h=c["mounting_holes"][0];assert h["offset_x_mm"]==2 and h["offset_y_mm"]==0;close(c["rotation"],120)
def test_input_not_mutated():
 cut={"component_id":"c","position":{"x_mm":1,"y_mm":2},"rotation":0};root={"position":{"x":3,"y":4,"z":0},"rotation":0,"cutouts":[cut]}
 CoordinateFlattener.flatten_assembly(root);assert cut["position"]=={"x_mm":1,"y_mm":2}
