"""Shared analytic geometry helpers for UNG-CAD."""
import math


def circle_metrics(radius: float) -> dict[str, float]:
    """Return common circle metrics for a non-negative radius."""
    if radius < 0:
        raise ValueError("radius must be non-negative")
    return {
        "radius": radius,
        "diameter": 2.0 * radius,
        "area": math.pi * radius**2,
        "circumference": 2.0 * math.pi * radius,
    }


def sphere_metrics(radius: float) -> dict[str, float]:
    """Return common sphere metrics for a non-negative radius."""
    if radius < 0:
        raise ValueError("radius must be non-negative")
    return {
        "radius": radius,
        "diameter": 2.0 * radius,
        "surface_area": 4.0 * math.pi * radius**2,
        "volume": (4.0 / 3.0) * math.pi * radius**3,
    }


def radial_metrics(radius: float) -> dict[str, dict[str, float]]:
    """Single radius-driven entry point for CAD/UI consumers."""
    return {
        "circle": circle_metrics(radius),
        "sphere": sphere_metrics(radius),
    }


if __name__ == "__main__":
    r = 5.0
    values = radial_metrics(r)
    print(f"Radius: {r}")
    print(f"Circle Area: {values['circle']['area']:.2f}")
    print(f"Circle Circumference: {values['circle']['circumference']:.2f}")
    print(f"Sphere Surface Area: {values['sphere']['surface_area']:.2f}")
    print(f"Sphere Volume: {values['sphere']['volume']:.2f}")
