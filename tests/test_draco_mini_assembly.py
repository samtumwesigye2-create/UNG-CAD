from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects" / "draco-mini"
ASSEMBLY = PROJECT / "assembly.scad"


def test_assembly_source_exists_and_uses_all_five_parts():
    assert ASSEMBLY.exists(), "DRACO-Mini assembly source must exist"
    text = ASSEMBLY.read_text()
    for part in (
        "rotating_base.scad",
        "pan_tilt_cradle.scad",
        "sensor_shell.scad",
        "camera_insert.scad",
        "electronics_cartridge.scad",
    ):
        assert part in text


def test_assembly_locks_envelope_and_interface_clearance():
    text = ASSEMBLY.read_text()
    assert "overall_x = 110" in text
    assert "overall_y = 110" in text
    assert "overall_z = 135" in text
    assert "fit_clearance = 0.35" in text
    assert "base_z = 0" in text
    assert "cradle_z = 18" in text
    assert "shell_z = 52" in text
    assert "camera_insert_y = -41" in text
    assert "electronics_cartridge_y = 29" in text
