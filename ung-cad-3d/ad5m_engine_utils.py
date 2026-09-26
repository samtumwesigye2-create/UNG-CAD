"""
FlashForge Adventurer 5M (AD5M) Slicer & CAD Geometry Engine
Optimized for 0.4mm Stock Nozzle Calibration & Volumetric Extrusion Control
"""

import math

AD5M_NOZZLE_DIAMETER = 0.40
AD5M_MAX_VOLUMETRIC_SPEED = 20.0

def calculate_bead_width_from_area(cross_sectional_area: float, layer_height: float) -> float:
    """Calculate extrusion bead width using a flattened stadium cross-section model."""
    if cross_sectional_area <= 0 or layer_height <= 0:
        raise ValueError("Area and layer height must be positive values.")
    stadium_radius = layer_height / 2.0
    stadium_cap_area = math.pi * stadium_radius ** 2
    return ((cross_sectional_area - stadium_cap_area) / layer_height) + layer_height

def calculate_safe_feedrate_from_volume(sphere_volume: float, extrusion_time_seconds: float) -> float:
    """Return volumetric throughput and warn when it exceeds the configured AD5M limit."""
    if sphere_volume <= 0 or extrusion_time_seconds <= 0:
        raise ValueError("Volume and extrusion time must be positive.")
    volumetric_rate = sphere_volume / extrusion_time_seconds
    if volumetric_rate > AD5M_MAX_VOLUMETRIC_SPEED:
        print(
            f"[WARNING] Requested throughput {volumetric_rate:.2f} mm³/s exceeds "
            f"configured AD5M 0.4mm melt limit ({AD5M_MAX_VOLUMETRIC_SPEED} mm³/s)."
        )
    return volumetric_rate

def radius_from_nozzle_area(target_area: float) -> float:
    """Find circular flow-path radius from target area."""
    if target_area <= 0:
        raise ValueError("Target area must be greater than zero.")
    return math.sqrt(target_area / math.pi)

def radius_from_mass_and_density(target_mass_grams: float, density_g_cm3: float = 1.24) -> float:
    """Calculate solid-sphere radius for a target mass and material density."""
    if target_mass_grams <= 0 or density_g_cm3 <= 0:
        raise ValueError("Mass and density must be positive.")
    volume_mm3 = (target_mass_grams / density_g_cm3) * 1000.0
    return (3.0 * volume_mm3 / (4.0 * math.pi)) ** (1.0 / 3.0)

if __name__ == "__main__":
    print("=== AD5M Engine Initialization ===")
    target_layer_h = 0.20
    target_area = 0.088
    computed_width = calculate_bead_width_from_area(target_area, target_layer_h)
    print(f"Calculated Extrusion Width for Slicer: {computed_width:.3f} mm (Nozzle: {AD5M_NOZZLE_DIAMETER}mm)")
    pla_ball_radius = radius_from_mass_and_density(target_mass_grams=5.5, density_g_cm3=1.24)
    print(f"CAD Sphere Model Radius required for 5.5g PLA component: {pla_ball_radius:.2f} mm")
