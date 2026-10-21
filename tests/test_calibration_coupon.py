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


def test_measurement_sheet_covers_every_coupon_piece():
    from cad_core.calibration_coupon import measurement_template_rows
    _,manifest=generate_calibration_coupon(CalibrationCouponSpec(radial_segments=32))
    rows=measurement_template_rows(manifest)
    assert {r["piece_id"] for r in rows}=={p["id"] for p in manifest["pieces"]}
    assert all(r["measured_mm"]=="" for r in rows)
    groups={r["group"] for r in rows}
    assert groups=={"xy_scale_samples","z_scale_samples","hole_samples","outer_samples"}


def test_filled_sheet_feeds_profile_and_skips_blank_rows():
    from cad_core.calibration_coupon import measurement_template_rows, feedback_from_measurement_rows
    _,manifest=generate_calibration_coupon(CalibrationCouponSpec(radial_segments=32))
    rows=measurement_template_rows(manifest)
    for r in rows:
        if r["group"]=="hole_samples": r["measured_mm"]=str(r["nominal_mm"]-0.2)
    groups=feedback_from_measurement_rows(rows)
    assert len(groups["hole_samples"])==4
    assert groups["xy_scale_samples"]==[]  # blank, not zero
    profile=derive_compensation_profile(name="kit",**{k:v for k,v in groups.items()})
    assert profile.calibrated
    assert profile.hole_diameter_error_mm==pytest.approx(-0.2)


def test_sheet_rejects_typos_instead_of_guessing():
    from cad_core.calibration_coupon import feedback_from_measurement_rows
    with pytest.raises(ValueError, match="unknown group"):
        feedback_from_measurement_rows([{"group":"holes","nominal_mm":"5","measured_mm":"4.8"}])
    with pytest.raises(ValueError, match="must be numbers"):
        feedback_from_measurement_rows([{"group":"hole_samples","nominal_mm":"5","measured_mm":"4,8"}])
    with pytest.raises(ValueError, match="no measured values"):
        feedback_from_measurement_rows([{"group":"hole_samples","nominal_mm":"5","measured_mm":""}])
