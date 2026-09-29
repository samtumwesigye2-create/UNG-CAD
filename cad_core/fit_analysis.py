"""Dimensional fit and printer-compensation primitives for UNG-CAD.

The profile stores measured printer error as (printed - CAD) in millimetres.
A negative hole_diameter_error_mm means holes print undersize. Compensation
therefore subtracts the measured error from the requested target dimension.

Defaults are deliberately neutral: UNG-CAD must not invent printer calibration.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class PrinterCompensationProfile:
    name: str = "uncalibrated"
    nozzle_diameter_mm: float = 0.4
    xy_scale_error_fraction: float = 0.0
    z_scale_error_fraction: float = 0.0
    hole_diameter_error_mm: float = 0.0
    slot_width_error_mm: float = 0.0
    outer_dimension_error_mm: float = 0.0
    clearance_error_mm: float = 0.0
    source: str = "neutral-default"
    calibrated: bool = False

    def __post_init__(self):
        if self.nozzle_diameter_mm <= 0:
            raise ValueError("nozzle_diameter_mm must be positive")
        if self.xy_scale_error_fraction <= -1 or self.z_scale_error_fraction <= -1:
            raise ValueError("scale error fractions must be greater than -1")

    def to_dict(self):
        return asdict(self)


def compensate_target_dimension(
    target_mm: float,
    *,
    feature: str,
    profile: PrinterCompensationProfile,
) -> float:
    """Return the CAD dimension intended to yield target_mm after printing."""
    target=float(target_mm)
    if target <= 0:
        raise ValueError("target_mm must be positive")

    feature=feature.strip().lower()
    if feature in {"hole","bore","circular_hole"}:
        return target - profile.hole_diameter_error_mm
    if feature in {"slot","slot_width"}:
        return target - profile.slot_width_error_mm
    if feature in {"outer","outer_dimension","boss","shaft"}:
        # Constant offset plus multiplicative XY calibration.
        return (target - profile.outer_dimension_error_mm) / (1.0 + profile.xy_scale_error_fraction)
    if feature in {"z","height","depth"}:
        return target / (1.0 + profile.z_scale_error_fraction)
    if feature in {"clearance","gap"}:
        return target - profile.clearance_error_mm
    raise ValueError(f"Unsupported compensated feature type: {feature}")


def predicted_printed_dimension(
    cad_mm: float,
    *,
    feature: str,
    profile: PrinterCompensationProfile,
) -> float:
    """Predict printed dimension from CAD using the same error convention."""
    cad=float(cad_mm)
    if cad <= 0:
        raise ValueError("cad_mm must be positive")

    feature=feature.strip().lower()
    if feature in {"hole","bore","circular_hole"}:
        return cad + profile.hole_diameter_error_mm
    if feature in {"slot","slot_width"}:
        return cad + profile.slot_width_error_mm
    if feature in {"outer","outer_dimension","boss","shaft"}:
        return cad*(1.0+profile.xy_scale_error_fraction)+profile.outer_dimension_error_mm
    if feature in {"z","height","depth"}:
        return cad*(1.0+profile.z_scale_error_fraction)
    if feature in {"clearance","gap"}:
        return cad + profile.clearance_error_mm
    raise ValueError(f"Unsupported predicted feature type: {feature}")


def radial_clearance(hole_diameter_mm: float, insert_diameter_mm: float) -> float:
    """Per-side radial clearance. Negative values mean interference."""
    hole=float(hole_diameter_mm)
    insert=float(insert_diameter_mm)
    if hole <= 0 or insert <= 0:
        raise ValueError("diameters must be positive")
    return (hole-insert)/2.0


def diametral_clearance(hole_diameter_mm: float, insert_diameter_mm: float) -> float:
    hole=float(hole_diameter_mm)
    insert=float(insert_diameter_mm)
    if hole <= 0 or insert <= 0:
        raise ValueError("diameters must be positive")
    return hole-insert


def classify_fit(
    hole_diameter_mm: float,
    insert_diameter_mm: float,
    *,
    transition_band_mm: float = 0.05,
) -> dict:
    """Classify by actual diametral gap, without claiming an ISO/ANSI fit class."""
    if transition_band_mm < 0:
        raise ValueError("transition_band_mm cannot be negative")
    gap=diametral_clearance(hole_diameter_mm,insert_diameter_mm)
    if gap > transition_band_mm:
        kind="clearance"
    elif gap < -transition_band_mm:
        kind="interference"
    else:
        kind="transition"
    return {
        "fit":kind,
        "diametral_clearance_mm":gap,
        "radial_clearance_mm":gap/2.0,
        "transition_band_mm":transition_band_mm,
    }


def analyze_compensated_fit(
    *,
    target_hole_mm: float,
    target_insert_mm: float,
    profile: PrinterCompensationProfile,
    transition_band_mm: float = 0.05,
) -> dict:
    """Compare target fit with predicted print fit for a calibrated profile."""
    target=classify_fit(target_hole_mm,target_insert_mm,transition_band_mm=transition_band_mm)
    cad_hole=compensate_target_dimension(target_hole_mm,feature="hole",profile=profile)
    cad_insert=compensate_target_dimension(target_insert_mm,feature="outer",profile=profile)
    predicted_hole=predicted_printed_dimension(cad_hole,feature="hole",profile=profile)
    predicted_insert=predicted_printed_dimension(cad_insert,feature="outer",profile=profile)
    predicted=classify_fit(predicted_hole,predicted_insert,transition_band_mm=transition_band_mm)
    return {
        "target":target,
        "cad":{"hole_diameter_mm":cad_hole,"insert_diameter_mm":cad_insert},
        "predicted_print":{"hole_diameter_mm":predicted_hole,"insert_diameter_mm":predicted_insert,**predicted},
        "profile":profile.to_dict(),
        "calibration_warning":None if profile.calibrated else "Profile is uncalibrated; compensation values are neutral unless explicitly supplied.",
    }


def wall_from_opposed_planes(plane_a_offset_mm: float, plane_b_offset_mm: float) -> float:
    """Exact wall spacing when two parallel B-rep planes share one unit normal."""
    thickness=abs(float(plane_b_offset_mm)-float(plane_a_offset_mm))
    if thickness <= 0:
        raise ValueError("Opposed planes must have non-zero separation")
    return thickness


def bore_diameter_from_cylinder_radius(radius_mm: float) -> float:
    """Exact nominal bore diameter for an analytic cylindrical B-rep face."""
    r=float(radius_mm)
    if r <= 0:
        raise ValueError("radius_mm must be positive")
    return 2.0*r
