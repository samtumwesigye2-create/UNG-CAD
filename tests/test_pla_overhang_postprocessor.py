from pathlib import Path
import importlib.util

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "ung_overhang_fix.py"
spec = importlib.util.spec_from_file_location("ung_overhang_fix", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def run(tmp_path, text):
    p = tmp_path / "sample.gcode"
    p.write_text(text, encoding="utf-8")
    mod.process_orcaslicer_pla_overhang_cross_platform(str(p))
    return p.read_text(encoding="utf-8")

def test_overhang_injects_and_restores(tmp_path):
    out = run(tmp_path, "M104 S210\nM106 S180\n;TYPE:Overhang perimeter\nG1 X1 Y1 E0.3 F3600\n;TYPE:External perimeter\nG1 X2 Y2 E0.4 F3000\n")
    assert "M106 S255 ; UNG-CAD PLA Overhang Max Fan" in out
    assert "M104 S200 ; UNG-CAD bounded PLA overhang temperature" in out
    assert "G1 X1 Y1 E0.3 F1200 ; UNG-CAD PLA Speed Clamp (20mm/s)" in out
    assert "M106 S180 ; UNG-CAD Restore Baseline PLA Cooling" in out
    assert "M104 S210 ; UNG-CAD Restore Original Temp" in out

def test_repeated_bridge_markers_do_not_double_inject(tmp_path):
    out = run(tmp_path, "M104 S205\n;TYPE:Bridge\n;TYPE:Bridge\nG1 X1 E1 F2400\n;TYPE:Internal infill\n")
    assert out.count("UNG-CAD PLA Overhang Max Fan") == 1
    assert out.count("UNG-CAD bounded PLA overhang temperature") == 1

def test_temperature_floor(tmp_path):
    out = run(tmp_path, "M104 S195\n;TYPE:Bridge\nG1 X1 E1 F2400\n;TYPE:Internal infill\n")
    assert "M104 S190 ; UNG-CAD bounded PLA overhang temperature" in out

def test_non_extrusion_move_is_not_speed_modified(tmp_path):
    out = run(tmp_path, ";TYPE:Bridge\nG1 X10 Y10 F6000\n;TYPE:Internal infill\n")
    assert "G1 X10 Y10 F6000" in out
    assert "Speed Clamp" not in out
