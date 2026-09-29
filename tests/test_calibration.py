import pytest
from cad_core.calibration import (
    CalibrationMeasurement, calibration_coupon_set, profile_from_measurements,
    ring_triangles
)


def test_coupon_set_contains_dimension_and_hole_artifacts():
    parts,manifest=calibration_coupon_set()
    assert "XY_20x40x5" in parts
    assert "HOLE_5mm" in parts
    assert len(parts["HOLE_5mm"]) > 100
    assert manifest["schema"]=="ung-cad.calibration-coupon.v1"


def test_ring_geometry_validates_basic_inputs():
    with pytest.raises(ValueError): ring_triangles(5,4,2)


def test_profile_learns_hole_bias_and_outer_scale():
    ms=[
      CalibrationMeasurement("hole",3,2.8),
      CalibrationMeasurement("hole",5,4.8),
      CalibrationMeasurement("hole",8,7.8),
      CalibrationMeasurement("outer",5,5.05),
      CalibrationMeasurement("outer",10,10.10),
      CalibrationMeasurement("z",20,20.2),
    ]
    p=profile_from_measurements(ms)
    assert p["hole_diameter_error_mm"]==pytest.approx(-.2)
    assert p["xy_scale_error_fraction"]==pytest.approx(.01)
    assert p["z_scale_error_fraction"]==pytest.approx(.01)
    assert p["calibrated"]
    assert p["coverage"]["hole"]==3


def test_single_outer_measurement_produces_scale_only():
    p=profile_from_measurements([CalibrationMeasurement("outer",20,20.2)])
    assert p["xy_scale_error_fraction"]==pytest.approx(.01)
    assert p["outer_dimension_error_mm"]==pytest.approx(0)
