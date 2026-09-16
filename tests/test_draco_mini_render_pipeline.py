from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "test.yml"


def test_ci_renders_all_draco_mini_scad_sources_to_stl():
    text = WORKFLOW.read_text()
    assert "Install OpenSCAD" in text
    assert "openscad -o" in text
    for source in (
        "projects/draco-mini/parts/rotating_base.scad",
        "projects/draco-mini/parts/pan_tilt_cradle.scad",
        "projects/draco-mini/parts/sensor_shell.scad",
        "projects/draco-mini/parts/camera_insert.scad",
        "projects/draco-mini/parts/electronics_cartridge.scad",
        "projects/draco-mini/assembly.scad",
    ):
        assert source in text


def test_ci_rejects_empty_stl_outputs():
    text = WORKFLOW.read_text()
    assert "test -s" in text
    assert "build/draco-mini" in text
