import pytest
from cad_core.process_compensation import *
def c(profile,kind="circular"):
 g={"diameter_mm":10} if kind=="circular" else {"width_mm":10,"height_mm":5}
 return {"type":kind,"tolerance_profile":profile,"geometry_payload":g}
def test_laser_internal_path_contracts_for_kerf(): assert apply_manufacturing_compensation(c("laser_cut"))["geometry_payload"]["diameter_mm"]==pytest.approx(9.88)
def test_waterjet_configurable_kerf(): assert apply_manufacturing_compensation(c("waterjet"),ProcessCompensation(kerf_mm=.8))["geometry_payload"]["diameter_mm"]==pytest.approx(9.2)
def test_pla_internal_opening_allowance(): assert apply_manufacturing_compensation(c("3d_print_pla"))["geometry_payload"]["diameter_mm"]==pytest.approx(10.15)
def test_petg_rectangular_allowance():
 g=apply_manufacturing_compensation(c("3d_print_petg","rectangular"))["geometry_payload"];assert g["width_mm"]==pytest.approx(10.2);assert g["height_mm"]==pytest.approx(5.2)
def test_cnc_keeps_nominal_geometry_and_records_tool_radius():
 o=apply_manufacturing_compensation(c("cnc_mill_aluminum"));assert o["geometry_payload"]["diameter_mm"]==10;assert o["process_compensation"]["tool_radius_mm"]==1
def test_input_not_mutated():
 x=c("laser_cut");apply_manufacturing_compensation(x);assert x["geometry_payload"]["diameter_mm"]==10
