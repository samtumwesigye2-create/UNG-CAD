import pytest
from cad_core.sheet_nesting import *
def test_packs_multiple_plates():
 e=SheetNestingEngine(100,60,6,False);items,n=e.pack_plates([{"panel_id":"a","width_mm":40,"height_mm":20},{"panel_id":"b","width_mm":40,"height_mm":20}]);assert n==1 and len(items)==2 and items[0].placed_x>=3
def test_new_sheet_when_full():
 e=SheetNestingEngine(50,30,2,False);_,n=e.pack_plates([{"panel_id":"a","width_mm":40,"height_mm":20},{"panel_id":"b","width_mm":40,"height_mm":20}]);assert n==2
def test_rotation_can_make_part_fit():
 e=SheetNestingEngine(60,100,0,True);items,n=e.pack_plates([{"panel_id":"a","width_mm":90,"height_mm":50}]);assert n==1 and items[0].rotated
def test_oversize_rejected():
 with pytest.raises(ValueError,match="exceeds"):SheetNestingEngine(50,50,6).pack_plates([{"panel_id":"a","width_mm":60,"height_mm":60}])
def test_invalid_dimensions_rejected():
 with pytest.raises(ValueError,match="invalid dimensions"):SheetNestingEngine(50,50).pack_plates([{"panel_id":"a","width_mm":0,"height_mm":10}])
