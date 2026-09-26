import math
import re

MOVE_RE = re.compile(r"^\s*G1\b", re.I)
AXIS_RE = re.compile(r"([XYZEF])(-?\d+(?:\.\d+)?)", re.I)

def _axis(line, key):
    vals = {k.upper(): float(v) for k, v in AXIS_RE.findall(line.split(";", 1)[0])}
    return vals.get(key)

def compile_ad5m_4d(gcode, *, layer_height=0.20, thermal=False,
                    thermal_base=3000, thermal_boost=6000,
                    material_swap=False, swap_layer=15,
                    light=False, light_every=10):
    """Experimental AD5M post-processor. Operator pauses are explicit and never auto-resume."""
    if not (0.08 <= layer_height <= 0.40):
        raise ValueError("layer_height must be 0.08-0.40 mm")
    if thermal_base <= 0 or thermal_boost < 0:
        raise ValueError("invalid thermal feedrate settings")
    if swap_layer < 1 or light_every < 1:
        raise ValueError("layer settings must be positive")

    out = ["; --- UNG-CAD EXPERIMENTAL 4D / AD5M ---\n",
           "; Verify PAUSE/RESUME behavior on the installed AD5M firmware before use.\n"]
    cx = cy = 0.0
    last_layer = -1
    swapped = False
    light_layers = set()

    for raw in gcode.splitlines(True):
        clean = raw.split(";", 1)[0].strip()
        x = _axis(clean, "X"); y = _axis(clean, "Y"); z = _axis(clean, "Z")
        e = _axis(clean, "E")
        if x is not None: cx = x
        if y is not None: cy = y

        if z is not None:
            layer = max(0, int(round(z / layer_height)))
            if layer != last_layer:
                last_layer = layer
                if material_swap and layer == swap_layer and not swapped:
                    swapped = True
                    out += ["; 4D MATERIAL SWAP — load validated moisture-responsive filament\n",
                            "PAUSE\n",
                            "; OPERATOR: change filament using printer controls, then resume manually.\n"]
                if light and layer > 0 and layer % light_every == 0 and layer not in light_layers:
                    light_layers.add(layer)
                    out += ["; 4D LIGHT TREATMENT — only for validated photo-responsive material\n",
                            "PAUSE\n",
                            "; OPERATOR: park/confirm safe position, apply external light treatment, then resume manually.\n"]

        # Preserve slicer control of extrusion, first layers and non-print moves.
        # Thermal stress programming applies only to XY extrusion moves after layer 2.
        if thermal and last_layer > 2 and MOVE_RE.match(clean) and e is not None and (x is not None or y is not None):
            gradient = (math.sin(cx * 0.05) + math.cos(cy * 0.05) + 2.0) / 4.0
            feed = int(thermal_base + gradient * thermal_boost)
            body, *comment = raw.rstrip("\n").split(";", 1)
            if re.search(r"F-?\d+(?:\.\d+)?", body, re.I):
                body = re.sub(r"F-?\d+(?:\.\d+)?", f"F{feed}", body, flags=re.I)
            else:
                body = body.rstrip() + f" F{feed}"
            suffix = (" ;" + comment[0]) if comment else ""
            out.append(body + suffix + " ; UNG-4D thermal-stress\n")
        else:
            out.append(raw if raw.endswith("\n") else raw + "\n")
    return "".join(out)
