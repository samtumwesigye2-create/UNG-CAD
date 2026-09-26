import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "projects" / "draco-mini" / "ung-manufacturing.json"

def test_draco_mini_manufacturing_manifest():
    assert MANIFEST.exists(), "DRACO-Mini manufacturing manifest must exist"
    data = json.loads(MANIFEST.read_text())
    assert data["format"] == "ung-cad-manufacturing/v1"
    assert data["project"] == "DRACO-Mini Gen-1"
    assert data["envelope_mm"] == {"x": 110, "y": 110, "z": 135}
    assert data["fit_clearance_mm"] == 0.35
    assert data["windowless_camera_aperture"] is True
    assert data["screwless_external_enclosure"] is True
    assert set(data["printable_parts"]) == {"rotating_base","pan_tilt_cradle","sensor_shell","camera_insert","electronics_cartridge"}
    compute=data["electronics"]["compute"]
    assert compute["name"].startswith("Raspberry Pi")
    assert compute["dimensional_authority"] == "physical_hardware_measurement"
    assert compute["power_subsystem"] is False
    assert {"board_length","board_width","board_height","ethernet_connector_offset","usb_c_connector_offset"} <= set(compute["required_measurements_mm"])
    assert "envelope_mm" not in compute
    assert data["electronics"]["camera"]["name"] == "Raspberry Pi Camera Module 3 NoIR"
    assert data["electronics"]["camera"]["envelope_mm"] == [25,24,11.5]
    assert data["electronics"]["servos"]["class"] == "MG90S"
    assert data["electronics"]["servos"]["quantity"] == 2
    assert data["validation"]["fit_coupon_required_before_full_print"] is True
