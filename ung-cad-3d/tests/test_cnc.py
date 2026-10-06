import pytest

import slicer_cnc

RECT = {"t": "rect", "a": {"x": 100, "y": 50}, "b": {"x": 300, "y": 150}}
LINE_DOWN = {"t": "line", "a": {"x": 100, "y": 50}, "b": {"x": 100, "y": 150}}
LABEL = {"t": "label", "a": {"x": 0, "y": 0}, "text": "x"}


def cut_lines(gcode, prefix="G1 X"):
    return [l for l in gcode.splitlines() if l.startswith(prefix)]


def test_y_flip_and_origin_bottom_left():
    paths = slicer_cnc.shapes_to_paths([RECT, LINE_DOWN, LABEL], 0.5)
    allpts = [p for path in paths for p in path]
    assert min(x for x, _ in allpts) == pytest.approx(0)
    assert min(y for _, y in allpts) == pytest.approx(0)
    assert max(x for x, _ in allpts) == pytest.approx(100)
    assert max(y for _, y in allpts) == pytest.approx(50)
    line = paths[1]
    assert line[0] == pytest.approx((0, 50))
    assert line[1] == pytest.approx((0, 0))


def test_laser_uses_m4_dynamic_mode_without_m3():
    gcode, n, est = slicer_cnc.slice_shapes_to_gcode([RECT], {"mode": "laser", "laser_power_percent": 80})
    lines = gcode.splitlines()
    assert not any(l.startswith("M3") for l in lines)
    m4 = [l for l in lines if l.startswith("M4")]
    assert m4 == [m4[0]] and m4[0].startswith("M4 S0")
    assert all(l.endswith("S800") for l in cut_lines(gcode))
    assert all(l.endswith("S0") for l in cut_lines(gcode, "G0 X"))
    assert lines[-2].startswith("M5")
    assert not any(l.startswith("G0 Z") or l.startswith("G1 Z") for l in lines)
    assert n == 1 and est > 0


def test_laser_max_s_scale():
    gcode, _, _ = slicer_cnc.slice_shapes_to_gcode([RECT], {"mode": "laser", "laser_power_percent": 50, "max_s": 255})
    assert all(l.endswith("S128") for l in cut_lines(gcode))


def test_cnc_mode_spindle_and_plunges():
    settings = {"mode": "cnc", "spindle_speed": 18000, "total_depth": 3, "cut_depth_per_pass": 1}
    gcode, _, _ = slicer_cnc.slice_shapes_to_gcode([RECT], settings)
    lines = gcode.splitlines()
    assert "M3 S18000 ; spindle on" in lines
    assert not any(l.startswith("M4") for l in lines)
    plunges = [l for l in lines if l.startswith("G1 Z")]
    assert plunges == ["G1 Z-1.000 F200", "G1 Z-2.000 F200", "G1 Z-3.000 F200"]
    assert "S" not in "".join(cut_lines(gcode))


@pytest.mark.parametrize("settings, message", [
    ({"mode": "cnc", "spindle_speed": 500}, "spindle_speed"),
    ({"mode": "cnc", "spindle_speed": 40000}, "spindle_speed"),
    ({"mode": "laser", "laser_power_percent": 120}, "laser_power_percent"),
    ({"mode": "laser", "laser_power_percent": -1}, "laser_power_percent"),
    ({"mode": "plasma"}, "mode"),
    ({"mode": "cnc", "cut_depth_per_pass": 0}, "cut_depth_per_pass"),
])
def test_validation(settings, message):
    with pytest.raises(ValueError) as e:
        slicer_cnc.slice_shapes_to_gcode([RECT], settings)
    assert message in str(e.value)


def test_laser_settings_ignore_spindle_range():
    slicer_cnc.slice_shapes_to_gcode([RECT], {"mode": "laser", "spindle_speed": 0})


def test_time_estimate_consistent_with_gcode_defaults_and_plunges():
    paths = slicer_cnc.shapes_to_paths([RECT], 1.0)
    base = {"mode": "cnc", "cut_depth_per_pass": 1.5}
    gcode = slicer_cnc.generate_gcode(paths, base)
    assert len([l for l in gcode.splitlines() if l.startswith("G1 Z")]) == 1
    one = slicer_cnc.estimate_seconds(paths, base)
    cut = 600 / 800 * 60
    plunge = (5 + 1.5) / 200 * 60
    assert one >= cut + plunge - 1
    three = slicer_cnc.estimate_seconds(paths, {**base, "total_depth": 4.5})
    assert three > 2.9 * one
    laser = slicer_cnc.estimate_seconds(paths, {"mode": "laser"})
    assert laser < one
