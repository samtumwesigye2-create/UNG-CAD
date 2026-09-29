import pytest

from cad_core.calibration_coupon import (
    CalibrationCouponSpec,
    derive_compensation_profile,
    generate_calibration_coupon,
)
from cad_core.geometry_validation import validate_triangle_mesh


def test_coupon_generates_printable_watertight_components():
    tris,manifest=generate_calibration_coupon(CalibrationCouponSpec(radial_segments=32))
    r=validate_triangle_mesh(tris)
    assert r.valid
    assert r.watertight
    assert r.connected_components >= 2
    assert manifest["triangle_count"]==len(tris)
    assert manifest["bounds_mm"]["x"] < 220
    assert manifest["bounds_mm"]["y"] < 220
    assert manifest["bounds_mm"]["z"] <= 20


def test_measurements_derive_actual_errors_without_guessing():
    p=derive_compensation_profile(
        name="AD5M coupon 1",
        xy_scale_samples=[{"nominal_mm":40,"measured_mm":40.4}],
        z_scale_samples=[{"nominal_mm":20,"measured_mm":19.8}],
        hole_samples=[{"nominal_mm":5,"measured_mm":4.8},{"nominal_mm":6,"measured_mm":5.8}],
        outer_samples=[{"nominal_mm":20,"measured_mm":20.2}],
        nozzle_diameter_mm=.4,
    )
    assert p.calibrated
    assert p.xy_scale_error_fraction==pytest.approx(.01)
    assert p.z_scale_error_fraction==pytest.approx(-.01)
    assert p.hole_diameter_error_mm==pytest.approx(-.2)
    # 20.2 is fully explained by the +1% scale, so constant offset is ~0.
    assert p.outer_dimension_error_mm==pytest.approx(0,abs=1e-9)


def test_no_measurements_stays_uncalibrated_and_neutral():
    p=derive_compensation_profile(name="blank")
    assert not p.calibrated
    assert p.xy_scale_error_fraction==0
    assert p.hole_diameter_error_mm==0
