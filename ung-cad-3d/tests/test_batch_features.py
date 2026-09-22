from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from gcode_preview import analyze
from material import filament_grams,affordable
from routing import rank
def test_gcode_analysis():
    r=analyze("G0 X0 Y0\nG1 X3 Y4 E1\n"); assert r["moves"]==2 and r["travel_mm"]==5
def test_material():
    assert filament_grams(100)>0 and affordable(100,20)
def test_routing():
    m=[{"name":"b","kind":"3d_printer","state":"idle","queue_depth":2},{"name":"a","kind":"3d_printer","state":"ready","queue_depth":0}]
    assert rank(m,"3d_printer")[0]["name"]=="a"
