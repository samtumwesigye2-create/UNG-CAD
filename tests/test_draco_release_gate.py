import pytest
from cad_core.draco_release_gate import evaluate_package,allow_selected_slice,CURRENT_PARTS

def names():
    return [f"DRACO_K2_{p}_PART.stl" for p in CURRENT_PARTS]

def manifest():
    return {
      "release_ready":True,
      "actual_hardware_dimensions_verified":True,
      "fit_coupon_passed":True,
      "dry_assembly_passed":True,
      "pan_tilt_motion_validated":True,
      "manifold_validation_passed":True,
      "source_cad_included":True,
      "baffle_material":"black PLA",
      "circular_12v_jack_present":False,
      "base_mounted_servos":2
    }

def test_complete_release_passes():
    ok,b=evaluate_package(names(),manifest())
    assert ok and not b

def test_legacy_eight_part_pack_is_blocked():
    old=[f"DRACO_K2_P{i}_PART.stl" for i in range(1,9)]
    ok,b=evaluate_package(old,manifest())
    assert not ok
    assert any("P9A" in x and "P9B" in x for x in b)

def test_manifest_is_required():
    ok,b=evaluate_package(names(),None)
    assert not ok and any("DRACO_PRODUCTION_RELEASE.json" in x for x in b)

def test_old_power_and_material_rules_are_blocked():
    m=manifest(); m["baffle_material"]="black PETG"; m["circular_12v_jack_present"]=True
    ok,b=evaluate_package(names(),m)
    assert not ok
    assert any("black PLA" in x for x in b)
    assert any("12v" in x.lower() for x in b)

def test_p0_coupon_can_slice_before_release():
    assert allow_selected_slice("DRACO_K2_P0_FIT_COUPON.stl",False)
    assert not allow_selected_slice("DRACO_K2_P2_BASE.stl",False)
