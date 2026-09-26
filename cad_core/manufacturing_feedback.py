"""Closed-loop manufacturing quality/calibration feedback."""
from dataclasses import dataclass
from typing import Dict

@dataclass(frozen=True)
class DimensionalFeedback:
    nominal_mm: float
    measured_mm: float
    error_mm: float
    scale_correction: float

def dimensional_feedback(nominal_mm: float, measured_mm: float) -> DimensionalFeedback:
    if nominal_mm <= 0 or measured_mm <= 0:
        raise ValueError("dimensions must be positive")
    error = measured_mm - nominal_mm
    return DimensionalFeedback(nominal_mm, measured_mm, error, nominal_mm / measured_mm)

def calibration_summary(samples: Dict[str, tuple]) -> Dict[str, DimensionalFeedback]:
    return {axis: dimensional_feedback(nominal, measured) for axis, (nominal, measured) in samples.items()}
