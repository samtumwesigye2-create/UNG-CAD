from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTS = ROOT / "projects" / "draco-mini" / "parts"

EXPECTED = {
    "rotating_base.scad",
    "pan_tilt_cradle.scad",
    "sensor_shell.scad",
    "camera_insert.scad",
    "electronics_cartridge.scad",
}


def test_all_five_printable_part_sources_exist():
    existing = {p.name for p in PARTS.glob("*.scad")} if PARTS.exists() else set()
    assert EXPECTED <= existing


def test_geometry_sources_lock_core_dimensions_and_clearance():
    combined = "\n".join((PARTS / name).read_text() for name in EXPECTED)
    assert "fit_clearance = 0.35" in combined
    assert "overall_x = 110" in combined
    assert "overall_y = 110" in combined
    assert "overall_z = 135" in combined
    assert "pi_zero_x = 65" in combined
    assert "pi_zero_y = 30" in combined
    assert "camera_x = 25" in combined
    assert "camera_y = 24" in combined
    assert "camera_z = 11.5" in combined
    assert "servo_x = 22.8" in combined
    assert "servo_y = 12.2" in combined
    assert "servo_z = 28.5" in combined
