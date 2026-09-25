"""CAD-facing adapter for the shared Calculus & Field Engine."""
from typing import Callable, Sequence
from ung_shared.calculus_field import (
    derivative, integrate, accumulation, evaluate_antiderivative,
    gradient, divergence, curl, line_integral, surface_flux,
)

class CADMath:
    """Stable CAD API over reusable numerical calculus primitives."""

    derivative = staticmethod(derivative)
    integrate = staticmethod(integrate)
    accumulation = staticmethod(accumulation)
    evaluate_antiderivative = staticmethod(evaluate_antiderivative)
    gradient = staticmethod(gradient)
    divergence = staticmethod(divergence)
    curl = staticmethod(curl)
    line_integral = staticmethod(line_integral)
    surface_flux = staticmethod(surface_flux)

    @staticmethod
    def rate(samples: Sequence[float], dt: float) -> list[float]:
        """Finite-difference rate for simulation/sensor histories."""
        if dt <= 0:
            raise ValueError("dt must be positive")
        if len(samples) < 2:
            return []
        return [(samples[i] - samples[i-1]) / dt for i in range(1, len(samples))]

    @staticmethod
    def accumulated(samples: Sequence[float], dt: float) -> float:
        """Trapezoidal accumulation for discrete CAD/simulation histories."""
        if dt <= 0:
            raise ValueError("dt must be positive")
        if len(samples) < 2:
            return 0.0
        return sum((samples[i-1] + samples[i]) * 0.5 * dt for i in range(1, len(samples)))
