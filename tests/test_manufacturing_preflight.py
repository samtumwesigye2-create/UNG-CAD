import pytest
from cad_core.manufacturing_preflight import *
def cut(x=50):
 return {"component_id":"c","type":"circular","position":{"x_mm":x,"y_mm":40},"rotation":0,"clearance_mm":0.1,"depth_mm":-1,"tolerance_profile":"3d_print_petg","geometry_payload":{"diameter_mm":10}}
def test_preflight_normalizes_validates_compensates_and_passes():
 r=ManufacturingPreflight(100,80).run([cut()]);assert r.passed;assert r.nominal_cutouts[0]["dimensions"]["diameter_mm"]==10;assert r.compensated_cutouts[0]["dimensions"]["diameter_mm"]>10
def test_boundary_failure_blocks_gate():
 with pytest.raises(ManufacturingPreflightError,match="blocked action"):ManufacturingPreflight(100,80).run([cut(2)])
def test_nonthrowing_mode_reports_failure():
 r=ManufacturingPreflight(100,80).run([cut(2)],require_gate=False);assert not r.passed and r.errors
def test_rib_validation_is_part_of_gate():
 with pytest.raises(ManufacturingPreflightError):ManufacturingPreflight(100,80).run([cut()],[{"rib_id":"r","start_point":{"x":1,"y":1},"end_point":{"x":1,"y":1}}])
