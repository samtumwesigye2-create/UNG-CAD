import pytest
from cad_core.assembly_contract import *
def node(i,w=100,h=80,x=0,y=0,r=0,children=None):return {"panel_id":i,"width_mm":w,"height_mm":h,"position":{"x":x,"y":y,"z":0},"rotation":r,"child_panels":children or []}
def test_nested_panel_valid():
 d={"assembly_id":"a","root_panel":node("root",children=[node("child",20,10,50,40,45)])};assert validate_assembly(d).child_panels[0].rotation==45
def test_rotated_child_boundary_rejected():
 d={"assembly_id":"a","root_panel":node("root",children=[node("child",20,20,95,40,45)])}
 with pytest.raises(AssemblyValidationError,match="exceeds parent"):validate_assembly(d)
def test_duplicate_panel_id_rejected():
 d={"assembly_id":"a","root_panel":node("same",children=[node("same",10,10,50,40)])}
 with pytest.raises(AssemblyValidationError,match="duplicate"):validate_assembly(d)
