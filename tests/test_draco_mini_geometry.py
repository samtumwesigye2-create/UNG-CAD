from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTS = ROOT / "projects" / "draco-mini" / "parts"
EXPECTED = {"rotating_base.scad","pan_tilt_cradle.scad","sensor_shell.scad","camera_insert.scad","electronics_cartridge.scad"}

def test_all_five_printable_part_sources_exist():
    existing={p.name for p in PARTS.glob("*.scad")} if PARTS.exists() else set()
    assert EXPECTED <= existing

def test_geometry_sources_lock_core_dimensions_and_clearance():
    combined="\n".join((PARTS/name).read_text() for name in EXPECTED)
    assert "fit_clearance = 0.35" in combined
    assert "overall_x = 110" in combined
    assert "overall_y = 110" in combined
    assert "overall_z = 135" in combined
    assert "sensor_x = 25" in combined
    assert "sensor_y = 24" in combined
    assert "sensor_z = 11.5" in combined
    assert "servo_x = 22.8" in combined
    assert "servo_y = 12.2" in combined
    assert "servo_z = 28.5" in combined

def test_compute_geometry_remains_measurement_gated():
    source=(PARTS/"electronics_cartridge.scad").read_text()
    assert "compute_board_x = 65; // PLACEHOLDER until actual installed Pi is measured" in source
    assert "compute_board_y = 30; // PLACEHOLDER until actual installed Pi is measured" in source
    assert "final dimensions come from BUILD_HANDOFF.md physical-hardware measurements" in source
    assert "Release gate: this source is architectural until the actual Pi" in source
