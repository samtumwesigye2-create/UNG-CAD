import math
import re

import numpy as np
import pytest
import trimesh
from shapely.geometry import LineString, Point, box as sbox

import slicer
from conftest import box, stl_bytes

LW = 0.45


def parse(gcode_bytes):
    """Split G-code into layers: {index: {"z": float, "lines": [...]}}."""
    layers = {}
    cur = None
    for line in gcode_bytes.decode().splitlines():
        if line.startswith(";LAYER:"):
            cur = int(line.split(":")[1])
            layers[cur] = {"z": None, "lines": []}
            continue
        if line.startswith(";END"):
            cur = None
            continue
        if cur is not None:
            if line.startswith(";Z:"):
                layers[cur]["z"] = float(line[3:])
            layers[cur]["lines"].append(line)
    return layers


def words(line):
    return {k: float(v) for k, v in re.findall(r"([XYZEFS])(-?\d+\.?\d*)", line)}


def extrusion_segments(layer_lines, kinds=None):
    """[(kind, (x0, y0), (x1, y1))] for extruding moves in one layer."""
    segs = []
    kind = None
    x = y = None
    e = 0.0
    for line in layer_lines:
        if line.startswith(";TYPE:"):
            kind = line.split(":")[1]
            continue
        if line.startswith("G92"):
            e = 0.0
            continue
        if not line.startswith(("G0 ", "G1 ")):
            continue
        w = words(line)
        nx, ny = w.get("X", x), w.get("Y", y)
        if "E" in w and ("X" in w or "Y" in w) and w["E"] > e and x is not None:
            if kinds is None or kind in kinds:
                segs.append((kind, (x, y), (nx, ny)))
        if "E" in w:
            e = w["E"]
        x, y = nx, ny
    return segs


@pytest.fixture(scope="module")
def cube_result():
    return slicer.slice_model(stl_bytes(box(20, 20, 20, center=(37.0, -12.0, None))), "cube.stl")


@pytest.mark.parametrize("lh", [0.2, 0.1])
def test_first_layer_z_equals_layer_height(lh):
    gcode, stats = slicer.slice_stl(stl_bytes(box(20, 20, 20)), "cube.stl", layer_height=lh)
    layers = parse(gcode)
    assert layers[1]["z"] == pytest.approx(lh)
    first_z_move = next(l for l in layers[1]["lines"] if l.startswith("G1 Z"))
    assert words(first_z_move)["Z"] == pytest.approx(lh)
    assert layers[2]["z"] == pytest.approx(2 * lh)
    assert stats["first_layer_z_mm"] == pytest.approx(lh)
    assert stats["layers"] == round(20 / lh)


def test_cube_centered_on_bed_origin(cube_result):
    layers = parse(cube_result["gcode"])
    pts = []
    for layer in layers.values():
        for kind, a, b in extrusion_segments(layer["lines"], kinds={"outer_wall", "inner_wall", "solid_infill", "sparse_infill"}):
            pts += [a, b]
    arr = np.array(pts)
    assert arr[:, 0].min() == pytest.approx(-10 + LW / 2, abs=0.11)
    assert arr[:, 0].max() == pytest.approx(10 - LW / 2, abs=0.05)
    assert abs(arr[:, 0].mean()) < 0.5 and abs(arr[:, 1].mean()) < 0.5
    # every coordinate in the whole file stays on the 220 mm bed (origin at centre)
    for line in cube_result["gcode"].decode().splitlines():
        if line.startswith(("G0", "G1")):
            w = words(line)
            assert abs(w.get("X", 0)) <= 110 and abs(w.get("Y", 0)) <= 110
    assert "X0 Y220" not in cube_result["gcode"].decode()


def test_multiple_perimeters_infill_and_solid_skins(cube_result):
    layers = parse(cube_result["gcode"])
    n = len(layers)

    def kinds(i):
        return {k for k, _, _ in extrusion_segments(layers[i]["lines"])}

    mid = kinds(n // 2)
    assert {"outer_wall", "inner_wall", "sparse_infill"} <= mid
    assert "solid_infill" not in mid
    for i in (1, 2, 3, 4, n - 3, n - 2, n - 1, n):
        k = kinds(i)
        assert "solid_infill" in k, i
        assert "sparse_infill" not in k, i
    # two wall loops per layer on the middle layer
    walls = [l for l in layers[n // 2]["lines"] if l.startswith(";TYPE:") and "wall" in l]
    assert len(walls) >= 2


def test_e_monotonic_after_each_g92(cube_result):
    layers = parse(cube_result["gcode"])
    for idx, layer in layers.items():
        assert layer["lines"][1] == "G92 E0" or "G92 E0" in layer["lines"][:3]
        e_vals = []
        for line in layer["lines"]:
            if line.startswith("G1 X") and " E" in line:
                e_vals.append(words(line)["E"])
        assert e_vals, idx
        assert all(b >= a for a, b in zip(e_vals, e_vals[1:])), idx
        assert e_vals[0] > 0


def test_extrusion_math_and_print_settings(cube_result):
    lh = 0.2
    expected = ((LW - lh) * lh + math.pi * (lh / 2) ** 2) / (math.pi * (1.75 / 2) ** 2)
    assert slicer.extrusion_per_mm(LW, lh) == pytest.approx(expected)
    text = cube_result["gcode"].decode()
    assert "M82" in text
    assert "M106 S255" in text
    layers = parse(cube_result["gcode"])
    assert any("M106" in l for l in layers[3]["lines"])
    assert not any("M106" in l for l in layers[1]["lines"] + layers[2]["lines"])
    assert any(l.startswith("G0 ") and "F9000" in l for l in text.splitlines())
    assert all("F1200" in l for l in layers[1]["lines"] if l.startswith("G1 X"))
    assert "G1 E-0.80000 F2100" in text            # retraction 0.8 mm at 35 mm/s
    assert ";TYPE:skirt" in "\n".join(layers[1]["lines"])
    assert "G1 X90.000 Y-105.000" in text           # purge line near front edge
    assert "G0 X-100.000 Y100.000" in text          # park inside the bed
    stats = cube_result["stats"]
    assert stats["filament_g"] > 0 and stats["filament_mm"] > 0
    assert stats["estimated_seconds"] > 0 and "estimate" in stats["estimate_note"].lower()


def test_petg_profile():
    gcode, stats = slicer.slice_stl(stl_bytes(box(10, 10, 5)), "p.stl", material="petg")
    text = gcode.decode()
    assert stats["material"] == "PETG"
    assert "M104 S235" in text and "M140 S80" in text and "M106 S102" in text
    pla = slicer.slice_stl(stl_bytes(box(10, 10, 5)), "p.stl")[1]
    assert stats["filament_g"] > pla["filament_g"]  # same volume, higher density
    with pytest.raises(ValueError):
        slicer.slice_stl(stl_bytes(box(10, 10, 5)), "p.stl", material="ABS")


def test_hollow_tube_stays_hollow():
    tube = trimesh.creation.annulus(r_min=6, r_max=10, height=12, sections=96)
    result = slicer.slice_model(stl_bytes(tube), "tube.stl")
    layers = parse(result["gcode"])
    hole = Point(0, 0).buffer(5.8)
    for idx in (1, 5, len(layers) // 2, len(layers)):
        segs = extrusion_segments(layers[idx]["lines"], kinds={"outer_wall", "inner_wall", "solid_infill", "sparse_infill"})
        assert segs
        for _, a, b in segs:
            assert not LineString([a, b]).intersects(hole), (idx, a, b)
        # outer ring + hole ring for each wall
        walls = [l for l in layers[idx]["lines"] if l == ";TYPE:outer_wall"]
        assert len(walls) == 2
    mid = {k for k, _, _ in extrusion_segments(layers[len(layers) // 2]["lines"])}
    assert "sparse_infill" in mid
    bottom = {k for k, _, _ in extrusion_segments(layers[1]["lines"])}
    assert "solid_infill" in bottom


def test_footprint_and_height_limits():
    with pytest.raises(slicer.SliceValidationError) as e:
        slicer.slice_stl(stl_bytes(box(215, 10, 10)), "wide.stl")
    assert e.value.report["errors"][0]["code"] == "off_bed"
    with pytest.raises(slicer.SliceValidationError) as e:
        slicer.slice_stl(stl_bytes(box(10, 10, 225)), "tall.stl")
    assert any(x["code"] == "too_tall" for x in e.value.report["errors"])
    # 210 mm still fits (5 mm margin each side)
    _, stats = slicer.slice_stl(stl_bytes(box(210, 10, 0.6)), "edge.stl")
    assert stats["layers"] == 3


def test_exact_dimensions_box_20x15x10():
    result = slicer.slice_model(stl_bytes(box(20, 15, 10, center=(5, 5, None))), "box.stl")
    layers = parse(result["gcode"])
    stats = result["stats"]
    for idx in range(2, len(layers) + 1):
        pts = []
        for _, a, b in extrusion_segments(layers[idx]["lines"], kinds={"outer_wall"}):
            pts += [a, b]
        arr = np.array(pts)
        width = arr[:, 0].max() - arr[:, 0].min() + LW
        depth = arr[:, 1].max() - arr[:, 1].min() + LW
        assert width == pytest.approx(20.0, abs=0.05), idx
        assert depth == pytest.approx(15.0, abs=0.05), idx
    # first layer is inset by the elephant-foot compensation (0.1 mm per side)
    pts = np.array([p for _, a, b in extrusion_segments(layers[1]["lines"], kinds={"outer_wall"}) for p in (a, b)])
    assert pts[:, 0].max() - pts[:, 0].min() + LW == pytest.approx(20.0 - 0.2, abs=0.01)
    assert layers[len(layers)]["z"] == pytest.approx(10.0, abs=1e-6)
    assert stats["top_z_mm"] == pytest.approx(10.0)
    assert stats["model_size_mm"] == [20.0, 15.0, 10.0]
    assert stats["toolpath_size_mm"] == pytest.approx([20.0, 15.0, 10.0], abs=0.05)
    assert result["report"]["checks"]["dimensions"]["toolpath_vs_outline_error_mm"] <= 0.05


def test_last_layer_snaps_to_model_height():
    result = slicer.slice_model(stl_bytes(box(10, 10, 10.1)), "b.stl", layer_height=0.2)
    stats = result["stats"]
    assert stats["top_z_mm"] == pytest.approx(10.1, abs=1e-6)
    assert stats["height_error_mm"] == pytest.approx(0.0, abs=1e-6)
    assert 0.1 <= stats["last_layer_height_mm"] <= 0.3
    assert slicer.check_gcode(result["gcode"].decode()) == []


def test_hole_compensation_grows_holes_only():
    tube = trimesh.creation.annulus(r_min=5, r_max=10, height=4, sections=128)
    base = slicer.slice_model(stl_bytes(tube), "t.stl", elephant_foot_mm=0)
    comp = slicer.slice_model(stl_bytes(tube), "t.stl", elephant_foot_mm=0, xy_hole_comp_mm=0.2)
    assert comp["stats"]["toolpath_size_mm"][:2] == pytest.approx(base["stats"]["toolpath_size_mm"][:2], abs=0.01)

    def hole_radius(result):
        layer = parse(result["gcode"])[5]
        pts = [p for _, a, b in extrusion_segments(layer["lines"], kinds={"outer_wall"}) for p in (a, b)]
        return min(math.hypot(*p) for p in pts)

    assert hole_radius(comp) == pytest.approx(hole_radius(base) + 0.2, abs=0.03)


def _cavity_box(invert_inner=True):
    outer = box(20, 20, 20)                      # Z 0..20
    inner = box(10, 10, 10, center=(0, 0, 10))   # sealed cavity, Z 5..15
    if invert_inner:
        inner.invert()
    return trimesh.util.concatenate([outer, inner])


@pytest.mark.parametrize("invert_inner", [True, False])
def test_internal_sealed_cavity_stays_hollow(invert_inner):
    result = slicer.slice_model(stl_bytes(_cavity_box(invert_inner)), "cavity.stl")
    roles = [b["role"] for b in result["stats"]["bodies"]]
    assert roles.count("separate") == 1 and roles.count("internal_cavity") == 1
    assert any(w["code"] == "internal_cavity" for w in result["report"]["warnings"])
    if not invert_inner:
        assert any("inverted normals" in r for r in result["report"]["repairs"])
    layers = parse(result["gcode"])
    void = sbox(-4.7, -4.7, 4.7, 4.7)
    # cavity spans Z 5..15 -> layers whose band lies fully inside it must not extrude into the void
    for idx, layer in layers.items():
        if layer["z"] - 0.2 >= 5.0 and layer["z"] <= 15.0:
            for _, a, b in extrusion_segments(layer["lines"]):
                assert not LineString([a, b]).intersects(void), (idx, a, b)
    # and the solid regions above/below the cavity do get material in the middle
    mid_floor = [s for s in extrusion_segments(layers[10]["lines"]) if LineString([s[1], s[2]]).intersects(void)]
    assert mid_floor


def test_nested_solid_inside_cavity_prints():
    outer = box(30, 30, 30)
    cavity = box(20, 20, 20, center=(0, 0, 15))
    cavity.invert()
    core = box(6, 6, 6, center=(0, 0, 15))
    result = slicer.slice_model(stl_bytes(trimesh.util.concatenate([outer, cavity, core])), "nest.stl")
    roles = sorted(b["role"] for b in result["stats"]["bodies"])
    assert roles == ["internal_cavity", "nested_solid", "separate"]
    layers = parse(result["gcode"])
    z15 = min(layers, key=lambda i: abs(layers[i]["z"] - 15))
    segs = extrusion_segments(layers[z15]["lines"])
    assert any(LineString([a, b]).intersects(sbox(-2.5, -2.5, 2.5, 2.5)) for _, a, b in segs)
    assert not any(LineString([a, b]).intersects(sbox(-9.5, -9.5, -3.5, 9.5)) for _, a, b in segs)


def test_multiple_separate_bodies_reported():
    two = trimesh.util.concatenate([box(10, 10, 5, center=(-20, 0, None)), box(10, 10, 5, center=(20, 0, None))])
    result = slicer.slice_model(stl_bytes(two), "two.stl")
    assert [b["role"] for b in result["stats"]["bodies"]] == ["separate", "separate"]
    assert any(w["code"] == "multiple_bodies" for w in result["report"]["warnings"])


def test_thin_wall_warning():
    block = box(10, 10, 6)
    fin = box(4.2, 0.3, 6, center=(6.9, 0, None))    # 0.3 mm thick fin (< one 0.45 mm line) sticking out 4 mm
    result = slicer.slice_model(stl_bytes(trimesh.util.concatenate([block, fin])), "fin.stl")
    thin = [w for w in result["report"]["warnings"] if w["code"] == "thin_walls"]
    assert thin
    assert thin[0]["locations"] and 2.5 < thin[0]["locations"][0]["x"] < 7.1   # fin after centring: x 2.8..7.0


def test_tiny_feature_and_units_warnings():
    pin = trimesh.util.concatenate([box(10, 10, 3), box(0.3, 0.3, 3, center=(15, 0, None))])
    result = slicer.slice_model(stl_bytes(pin), "pin.stl")
    assert any(w["code"] == "tiny_features" for w in result["report"]["warnings"])
    small = slicer.slice_model(stl_bytes(box(1.5, 1.5, 1.5)), "inch.stl")
    assert any(w["code"] == "units_too_small" for w in small["report"]["warnings"])
    assert small["stats"]["model_size_mm"] == [1.5, 1.5, 1.5]   # never auto-scaled


def test_overhang_warning():
    stem = box(6, 6, 10)
    plate = box(20, 20, 2, center=(0, 0, 11))
    result = slicer.slice_model(stl_bytes(trimesh.util.concatenate([stem, plate])), "t.stl")
    over = [w for w in result["report"]["warnings"] if w["code"] == "overhang"]
    assert over and over[0]["percent"] > 5
    # the overhang top gets solid skin even though it is not the last 4 layers of the part
    plain = slicer.slice_model(stl_bytes(box(20, 20, 10)), "b.stl")
    assert not any(w["code"] == "overhang" for w in plain["report"]["warnings"])


def test_small_contact_area_warning():
    tower = box(3, 3, 40)
    result = slicer.slice_model(stl_bytes(tower), "tower.stl")
    assert any(w["code"] == "small_contact" for w in result["report"]["warnings"])


def test_repair_is_reported_not_silent():
    m = box(10, 10, 10)
    m.update_faces(np.arange(len(m.faces)) != 0)       # punch a one-triangle hole
    result = slicer.slice_model(stl_bytes(m), "holey.stl")
    assert any("Filled holes" in r for r in result["report"]["repairs"])
    assert result["report"]["checks"]["open_edges"] > 0


def test_unrepairable_mesh_blocked():
    m = box(10, 10, 10)
    n = m.face_normals
    keep = ~((n[:, 0] > 0.9) | (n[:, 1] > 0.9))          # remove two whole adjacent sides
    m.update_faces(keep)
    with pytest.raises(slicer.SliceValidationError) as e:
        slicer.slice_model(stl_bytes(m), "open.stl")
    assert e.value.report["errors"][0]["code"] == "not_watertight"


def test_gcode_self_check_catches_problems():
    good = "\n".join(["M140 S55", "M104 S210", "M190 S55", "M109 S210", "G92 E0",
                      ";LAYER:1", ";Z:0.200", "G92 E0", "G1 Z0.200 F600", "G0 X0 Y0 F9000",
                      "G1 X10 Y0 E0.5 F1200", ";END"])
    assert slicer.check_gcode(good) == []
    assert any("outside the bed" in p for p in slicer.check_gcode(good.replace("X10 Y0", "X120 Y0")))
    assert any("G0 travel" in p for p in slicer.check_gcode(good.replace("G0 X0 Y0 F9000", "G0 X0 Y0 E1 F9000")))
    no_temp = good.replace("M109 S210", "").replace("M104 S210", "")
    assert any("temperatures" in p for p in slicer.check_gcode(no_temp))
    backwards = good.replace(";END", "G1 X20 Y0 E0.4 F1200\n;END")
    assert any("E went backwards" in p for p in slicer.check_gcode(backwards))
    z_down = good.replace(";END", ";LAYER:2\n;Z:0.100\nG92 E0\nG1 Z0.100\nG1 X0 Y5 E1\n;END")
    assert any("below" in p for p in slicer.check_gcode(z_down))
    empty_layer = good.replace(";END", ";LAYER:2\n;Z:0.400\nG92 E0\n;END")
    assert any("no extrusion" in p for p in slicer.check_gcode(empty_layer))


def test_slicer_refuses_gcode_that_fails_self_check(monkeypatch):
    monkeypatch.setattr(slicer._GcodeWriter, "_check_xy", staticmethod(lambda x, y: None))
    monkeypatch.setattr(slicer, "PARK_XY", (-150.0, 0.0))
    with pytest.raises(slicer.GcodeCheckError) as e:
        slicer.slice_stl(stl_bytes(box(10, 10, 5)), "b.stl")
    assert any("outside the bed" in p for p in e.value.problems)


def test_preview_json_shape():
    tube = trimesh.creation.annulus(r_min=4, r_max=8, height=6)
    data = slicer.preview_stl(stl_bytes(tube), "tube.stl")
    assert data["ok"] is True and data["layer_count"] == 30
    layer = data["layers"][0]
    assert set(layer) >= {"z", "paths", "index", "thickness"}
    types = {p["type"] for l in data["layers"] for p in l["paths"]}
    assert types <= {"perimeter", "infill", "solid", "travel"}
    assert {"perimeter", "infill", "solid", "travel"} <= types
    assert all(isinstance(pt, list) and len(pt) == 2 for p in layer["paths"] for pt in p["points"])
    assert "warnings" in data and "stats" in data
    sub = slicer.preview_stl(stl_bytes(tube), "tube.stl", max_layers=7)
    assert len(sub["layers"]) <= 8 and sub["layers"][-1]["z"] == pytest.approx(6.0)
