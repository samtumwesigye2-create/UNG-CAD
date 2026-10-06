"""
UNG-CAD CNC/Laser toolpath engine.

Takes the shape list produced by drafting.js (line, rect, circle - dim/label
are annotations, not geometry, and are skipped) and turns it into G-code for
a CNC router or laser cutter (GRBL-style controllers).

Coordinates / work origin:
  The drafting canvas has Y growing DOWN. The G-code has Y growing UP, and the
  drawing is shifted so the bottom-left corner of its bounding box is X0 Y0.
  => Set the machine's work zero (G92 X0 Y0 / "set origin" in your sender) at
     the BOTTOM-LEFT corner of where the part should be cut. All coordinates
     are then positive.

Laser mode:
  Uses GRBL dynamic power mode (M4). 'M4 S0' is sent once at the start, the
  power is set with S on every cutting G1 move, travels are G0 with S0, and M5
  turns the laser off at the end. No Z moves are emitted in laser mode (focus
  is set by the operator). The S scale is settings.max_s (default 1000, the
  GRBL $30 default) - set it to match your controller's $30.

Scope note: this cuts exactly along the drawn lines (centerline toolpath).
It does not do tool-radius compensation/offsetting - for a laser that's
usually fine (kerf is tiny); for CNC routing where the bit has real
diameter, either draw the outline already offset by the bit radius, or
treat this as a first pass and true up parts afterward. That's a deliberate
scope line, not an oversight - full polygon offsetting for arbitrary,
possibly self-intersecting shapes is a much deeper geometry problem.
"""
import math


SPINDLE_MIN = 1000
SPINDLE_MAX = 30000
MAX_PASSES = 200

DEFAULTS = {
    "mode": "laser",
    "feed_rate": 800.0,
    "plunge_rate": 200.0,
    "rapid_rate": 3000.0,
    "safe_z": 5.0,
    "cut_depth_per_pass": 1.0,
    "spindle_speed": 12000,
    "laser_power_percent": 80.0,
    "max_s": 1000,
    "scale_mm_per_px": 1.0,
}


def resolve_settings(settings):
    """Single source of truth for defaults + validation."""
    s = dict(DEFAULTS)
    s.update({k: v for k, v in (settings or {}).items() if v is not None})
    mode = s["mode"]
    if mode not in ("cnc", "laser"):
        raise ValueError("settings.mode must be 'cnc' or 'laser'")
    out = {"mode": mode}
    try:
        for key in ("feed_rate", "plunge_rate", "rapid_rate", "safe_z", "cut_depth_per_pass",
                    "laser_power_percent", "scale_mm_per_px"):
            out[key] = float(s[key])
        out["total_depth"] = float(s.get("total_depth", out["cut_depth_per_pass"]))
        out["spindle_speed"] = int(float(s["spindle_speed"]))
        out["max_s"] = int(float(s["max_s"]))
    except (TypeError, ValueError):
        raise ValueError("CNC/laser settings must be numbers")

    for key in ("feed_rate", "plunge_rate", "rapid_rate", "scale_mm_per_px", "max_s"):
        if not out[key] > 0:
            raise ValueError(f"{key} must be greater than 0")
    if mode == "cnc":
        if not (SPINDLE_MIN <= out["spindle_speed"] <= SPINDLE_MAX):
            raise ValueError(f"spindle_speed must be between {SPINDLE_MIN} and {SPINDLE_MAX} rpm")
        if not out["cut_depth_per_pass"] > 0:
            raise ValueError("cut_depth_per_pass must be greater than 0")
        if not out["total_depth"] > 0:
            raise ValueError("total_depth must be greater than 0")
        if not out["safe_z"] > 0:
            raise ValueError("safe_z must be greater than 0")
        out["passes"] = max(1, math.ceil(out["total_depth"] / out["cut_depth_per_pass"] - 1e-9))
        if out["passes"] > MAX_PASSES:
            raise ValueError(f"total_depth / cut_depth_per_pass needs more than {MAX_PASSES} passes")
    else:
        if not (0.0 <= out["laser_power_percent"] <= 100.0):
            raise ValueError("laser_power_percent must be between 0 and 100")
        out["passes"] = 1
    out["laser_s"] = int(round(out["laser_power_percent"] / 100.0 * out["max_s"]))
    return out


def _line_points(shape):
    return [(shape["a"]["x"], shape["a"]["y"]), (shape["b"]["x"], shape["b"]["y"])]


def _rect_points(shape):
    ax, ay = shape["a"]["x"], shape["a"]["y"]
    bx, by = shape["b"]["x"], shape["b"]["y"]
    x0, x1 = min(ax, bx), max(ax, bx)
    y0, y1 = min(ay, by), max(ay, by)
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]


def _circle_points(shape, resolution=48):
    ax, ay = shape["a"]["x"], shape["a"]["y"]
    bx, by = shape["b"]["x"], shape["b"]["y"]
    r = math.hypot(bx - ax, by - ay)
    return [
        (ax + r * math.cos(2 * math.pi * i / resolution),
         ay + r * math.sin(2 * math.pi * i / resolution))
        for i in range(resolution + 1)
    ]


def shapes_to_paths(shapes, scale_mm_per_px: float):
    px_paths = []
    for s in shapes:
        t = s.get("t")
        if t == "line":
            pts = _line_points(s)
        elif t == "rect":
            pts = _rect_points(s)
        elif t == "circle":
            pts = _circle_points(s)
        else:
            continue
        px_paths.append([(float(x), float(y)) for x, y in pts])
    if not px_paths:
        return []
    min_x = min(x for path in px_paths for x, _ in path)
    max_y = max(y for path in px_paths for _, y in path)
    return [
        [((x - min_x) * scale_mm_per_px, (max_y - y) * scale_mm_per_px) for x, y in path]
        for path in px_paths
    ]


def generate_gcode(paths, settings: dict) -> str:
    s = resolve_settings(settings)
    mode = s["mode"]
    feed = s["feed_rate"]
    lines = [
        f"; Generated by UNG-CAD ({mode})",
        "; Work origin: bottom-left corner of the drawing (X0 Y0), Y up",
        "G21 ; millimeters",
        "G90 ; absolute positioning",
    ]

    if mode == "laser":
        lines.append(f"; Laser power {s['laser_power_percent']:g}% = S{s['laser_s']} of max S{s['max_s']}")
        lines.append("M4 S0 ; laser dynamic power mode, beam off until a G1 sets S")
        for path in paths:
            if len(path) < 2:
                continue
            fx, fy = path[0]
            lines.append(f"G0 X{fx:.3f} Y{fy:.3f} S0")
            for x, y in path[1:]:
                lines.append(f"G1 X{x:.3f} Y{y:.3f} F{feed:.0f} S{s['laser_s']}")
        lines += ["M5 ; laser off", "M2 ; program end"]
        return "\n".join(lines) + "\n"

    safe_z = s["safe_z"]
    lines.append(f"G0 Z{safe_z:.3f}")
    lines.append(f"M3 S{s['spindle_speed']} ; spindle on")
    for path in paths:
        if len(path) < 2:
            continue
        for p in range(s["passes"]):
            depth = -min((p + 1) * s["cut_depth_per_pass"], s["total_depth"])
            fx, fy = path[0]
            lines.append(f"G0 X{fx:.3f} Y{fy:.3f}")
            lines.append(f"G1 Z{depth:.3f} F{s['plunge_rate']:.0f}")
            for x, y in path[1:]:
                lines.append(f"G1 X{x:.3f} Y{y:.3f} F{feed:.0f}")
            lines.append(f"G0 Z{safe_z:.3f}")
    lines += [f"G0 Z{safe_z:.3f}", "M5 ; spindle off", "M2 ; program end"]
    return "\n".join(lines) + "\n"


def estimate_seconds(paths, settings: dict) -> int:
    s = resolve_settings(settings)
    seconds = 0.0
    pos = (0.0, 0.0)
    for path in paths:
        if len(path) < 2:
            continue
        cut_len = sum(math.hypot(x2 - x1, y2 - y1) for (x1, y1), (x2, y2) in zip(path[:-1], path[1:]))
        for p in range(s["passes"]):
            seconds += math.hypot(path[0][0] - pos[0], path[0][1] - pos[1]) / s["rapid_rate"] * 60
            seconds += cut_len / s["feed_rate"] * 60
            if s["mode"] == "cnc":
                depth = min((p + 1) * s["cut_depth_per_pass"], s["total_depth"])
                seconds += (s["safe_z"] + depth) / s["plunge_rate"] * 60
                seconds += (s["safe_z"] + depth) / s["rapid_rate"] * 60
            pos = path[-1]
    return int(round(seconds))


def slice_shapes_to_gcode(shapes: list, settings: dict):
    s = resolve_settings(settings)
    paths = shapes_to_paths(shapes, s["scale_mm_per_px"])
    if not paths:
        raise ValueError("No cuttable geometry found (lines, rectangles or circles required)")
    gcode = generate_gcode(paths, settings)
    return gcode, len(paths), estimate_seconds(paths, settings)
