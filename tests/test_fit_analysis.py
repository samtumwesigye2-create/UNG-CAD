import pytest
from cad_core.fit_analysis import (
    PrinterCompensationProfile,
    analyze_compensated_fit,
    bore_diameter_from_cylinder_radius,
    classify_fit,
    compensate_target_dimension,
    predicted_printed_dimension,
    wall_from_opposed_planes,
)


def test_neutral_profile_does_not_invent_compensation():
    p=PrinterCompensationProfile()
    assert compensate_target_dimension(10,feature="hole",profile=p)==10
    assert predicted_printed_dimension(10,feature="outer",profile=p)==10
    assert not p.calibrated


def test_undersize_hole_error_expands_cad_hole():
    p=PrinterCompensationProfile(name="coupon",hole_diameter_error_mm=-0.2,calibrated=True,source="measured coupon")
    cad=compensate_target_dimension(10,feature="hole",profile=p)
    assert cad==pytest.approx(10.2)
    assert predicted_printed_dimension(cad,feature="hole",profile=p)==pytest.approx(10.0)


def test_outer_scale_error_is_inverted_for_compensation():
    p=PrinterCompensationProfile(name="coupon",xy_scale_error_fraction=.01,calibrated=True)
    cad=compensate_target_dimension(100,feature="outer",profile=p)
    assert cad==pytest.approx(100/1.01)
    assert predicted_printed_dimension(cad,feature="outer",profile=p)==pytest.approx(100)


def test_fit_classification_uses_configurable_transition_band():
    assert classify_fit(10.2,10,transition_band_mm=.05)["fit"]=="clearance"
    assert classify_fit(9.8,10,transition_band_mm=.05)["fit"]=="interference"
    assert classify_fit(10.02,10,transition_band_mm=.05)["fit"]=="transition"


def test_compensated_fit_preserves_requested_target_when_profile_model_matches():
    p=PrinterCompensationProfile(
        name="measured",
        hole_diameter_error_mm=-.15,
        xy_scale_error_fraction=.002,
        outer_dimension_error_mm=.03,
        calibrated=True,
        source="dimension coupon",
    )
    r=analyze_compensated_fit(target_hole_mm=6.4,target_insert_mm=6.0,profile=p)
    assert r["predicted_print"]["hole_diameter_mm"]==pytest.approx(6.4)
    assert r["predicted_print"]["insert_diameter_mm"]==pytest.approx(6.0)
    assert r["predicted_print"]["fit"]=="clearance"


def test_exact_brep_helpers():
    assert wall_from_opposed_planes(1.2,3.7)==pytest.approx(2.5)
    assert bore_diameter_from_cylinder_radius(4.25)==pytest.approx(8.5)
