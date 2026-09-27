import pytest
from cad_core.cam_planner import UngCadCAMPlanner,CAMValidationError
from cad_core.nesting_v2 import *
def test_cam_circle_and_rect():
 p=UngCadCAMPlanner(2,300,100,5,2,1,10000)
 s=p.generate([{"component_id":"c","type":"circular","position":{"x_mm":20,"y_mm":20},"dimensions":{"diameter_mm":10}},{"component_id":"r","type":"rectangular","position":{"x_mm":40,"y_mm":40},"dimensions":{"width_mm":20,"height_mm":10}}])
 assert "G02" in s and "FEATURE 1" in s and "M30" in s
def test_cam_rejects_tool_that_cannot_fit():
 p=UngCadCAMPlanner(10,300,100,5,2,1,10000)
 with pytest.raises(CAMValidationError):p.generate([{"type":"circular","position":{"x_mm":1,"y_mm":1},"dimensions":{"diameter_mm":5}}])
def test_nesting_v2_reports_utilization():
 r=NestingOptimizerV2(1).pack([{"component_id":"a","width_mm":20,"height_mm":10}],StockSheet("s",100,100))
 assert r["sheet_count"]==1 and 0<r["utilization"]<1
