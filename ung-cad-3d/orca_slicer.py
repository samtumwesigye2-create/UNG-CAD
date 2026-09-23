"""UNG-CAD -> FlashForge Adventurer 5M slicing (OrcaSlicer).

Fixes vs the old path:
- Uses the real AD5M profiles with every "inherits" level merged in, so the
  bed is -110..110 (centre = 0,0), the real AD5M start code runs, and the
  part gets walls, floors, roofs and infill.
- Textured PEI plate (PLA: 220 C nozzle / 55 C bed).
- Adds the 140x110 preview picture the printer screen shows.
- Adds ";LAYER:n" markers and absolute extrusion so the UNG-CAD toolpath
  preview shows every layer.
"""
import base64, json, os, re, shutil, struct, subprocess, tempfile, textwrap, urllib.request, zlib
from pathlib import Path

import numpy as np

ORCA_VERSION = "2.3.1"
ORCA_URL = (f"https://github.com/OrcaSlicer/OrcaSlicer/releases/download/v{ORCA_VERSION}/"
            f"OrcaSlicer_Linux_AppImage_Ubuntu2404_V{ORCA_VERSION}.AppImage")
CACHE = Path("/tmp/ungcad_orca")
APPIMAGE = CACHE / "OrcaSlicer.AppImage"
APPDIR = CACHE / "squashfs-root"

PRINTER = "Flashforge Adventurer 5M 0.4 Nozzle"
PROCESS = "0.20mm Standard @Flashforge AD5M 0.4 Nozzle"
FILAMENT = "Flashforge PLA Basic"
BED_TYPE = "Textured PEI Plate"

def _ensure_orca():
    CACHE.mkdir(parents=True, exist_ok=True)
    if not APPIMAGE.exists():
        tmp = APPIMAGE.with_suffix(".download")
        urllib.request.urlretrieve(ORCA_URL, tmp)
        tmp.chmod(0o755)
        tmp.replace(APPIMAGE)
    if not (APPDIR / "AppRun").exists():
        work = CACHE / "extract"
        shutil.rmtree(work, ignore_errors=True); work.mkdir()
        subprocess.run([str(APPIMAGE), "--appimage-extract"], cwd=work, check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
        extracted = work / "squashfs-root"
        if not extracted.exists():
            raise RuntimeError("OrcaSlicer extraction failed")
        shutil.rmtree(APPDIR, ignore_errors=True)
        extracted.replace(APPDIR)
        shutil.rmtree(work, ignore_errors=True)
    return APPDIR / "AppRun"

def _index_profiles():
    idx = {}
    root = APPDIR / "resources" / "profiles"
    for path in root.rglob("*.json"):
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(d, dict) and "name" in d:
            idx.setdefault((path.parent.name, d["name"]), d)
    return idx

def _resolve(idx, kind, name):
    if (kind, name) not in idx:
        raise RuntimeError(f"Missing Orca profile: {kind}/{name}")
    d = idx[(kind, name)]
    base = _resolve(idx, kind, d["inherits"]) if d.get("inherits") else {}
    out = dict(base); out.update(d)
    return out

def _write_presets(folder: Path):
    idx = _index_profiles()
    m = _resolve(idx, "machine", PRINTER)
    p = _resolve(idx, "process", PROCESS)
    f = _resolve(idx, "filament", FILAMENT)
    m["layer_change_gcode"] = ";AFTER_LAYER_CHANGE\nG92 E0\n;[layer_z]"
    for d in (m, p):
        d["curr_bed_type"] = BED_TYPE
    paths = []
    for d, fn in ((m, "machine.json"), (p, "process.json"), (f, "filament.json")):
        d["from"] = "system"; d["inherits"] = ""
        path = folder / fn
        path.write_text(json.dumps(d))
        paths.append(path)
    return paths

def _png(rgb: np.ndarray) -> bytes:
    h, w, _ = rgb.shape
    raw = b"".join(b"\x00" + rgb[y].astype(np.uint8).tobytes() for y in range(h))
    def chunk(t, data):
        c = struct.pack(">I", len(data)) + t + data
        return c + struct.pack(">I", zlib.crc32(t + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))

def render_thumbnail(stl_bytes: bytes, w=140, h=110) -> bytes:
    import trimesh
    mesh = trimesh.load(trimesh.util.wrap_as_stream(stl_bytes), file_type="stl", force="mesh")
    v = mesh.vertices - mesh.bounds.mean(axis=0)
    az, el = np.radians(-35), np.radians(-30)
    rz = np.array([[np.cos(az), -np.sin(az), 0], [np.sin(az), np.cos(az), 0], [0, 0, 1]])
    rx = np.array([[1, 0, 0], [0, np.cos(el), -np.sin(el)], [0, np.sin(el), np.cos(el)]])
    r = v @ rz.T
    r = np.c_[r[:, 0], r[:, 2], r[:, 1]] @ rx.T
    span = max(np.ptp(r[:, 0]) / (w - 12), np.ptp(r[:, 1]) / (h - 12), 1e-6)
    sx = (r[:, 0] - r[:, 0].min()) / span + (w - np.ptp(r[:, 0]) / span) / 2
    sy = (r[:, 1].max() - r[:, 1]) / span + (h - np.ptp(r[:, 1]) / span) / 2
    depth = r[:, 2]
    img = np.full((h, w, 3), (30, 30, 32), float)
    zbuf = np.full((h, w), np.inf)
    light = np.array([0.4, 0.6, -0.7]); light /= np.linalg.norm(light)
    fn = np.c_[mesh.face_normals @ rz.T]
    fn = np.c_[fn[:, 0], fn[:, 2], fn[:, 1]] @ rx.T
    for fi, (a, b, c) in enumerate(mesh.faces):
        xs, ys, zs = sx[[a, b, c]], sy[[a, b, c]], depth[[a, b, c]]
        x0, x1 = int(max(xs.min(), 0)), int(min(xs.max() + 1, w - 1))
        y0, y1 = int(max(ys.min(), 0)), int(min(ys.max() + 1, h - 1))
        if x1 < x0 or y1 < y0: continue
        den = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
        if abs(den) < 1e-9: continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        l0 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / den
        l1 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / den
        l2 = 1 - l0 - l1
        inside = (l0 >= 0) & (l1 >= 0) & (l2 >= 0)
        if not inside.any(): continue
        z = l0 * zs[0] + l1 * zs[1] + l2 * zs[2]
        sub = zbuf[y0:y1 + 1, x0:x1 + 1]
        upd = inside & (z < sub)
        shade = 0.35 + 0.65 * abs(float(fn[fi] @ light))
        sub[upd] = z[upd]
        img[y0:y1 + 1, x0:x1 + 1][upd] = np.array([235, 235, 235]) * shade
    return _png(np.clip(img, 0, 255))

def _add_thumbnail(text: str, png: bytes) -> str:
    b = base64.b64encode(png).decode()
    block = (f"; THUMBNAIL_BLOCK_START\n;\n; thumbnail begin 140x110 {len(b)}\n"
             + "".join(f"; {line}\n" for line in textwrap.wrap(b, 78))
             + "; thumbnail end\n; THUMBNAIL_BLOCK_END\n\n")
    marker = "; HEADER_BLOCK_END\n"
    i = text.find(marker)
    return text[:i + len(marker)] + "\n" + block + text[i + len(marker):] if i >= 0 else block + text

def _layers_and_absolute_e(text: str):
    out, rel, acc, layer = [], False, 0.0, 0
    for line in text.splitlines(True):
        s = line.strip(); code = s.split(";", 1)[0].strip().upper()
        if s == ";LAYER_CHANGE":
            out.append(f";LAYER:{layer}\n"); layer += 1
        if code == "M83":
            rel = True; out.append("M82 ; absolute extrusion\n"); continue
        if code == "M82": rel = False
        if re.match(r"G92\b", code):
            m = re.search(r"\bE(-?[\d.]+)", code)
            if m: acc = float(m.group(1))
        if rel and re.match(r"G[01]\b", code):
            body = line.split(";", 1)[0]
            m = re.search(r"\bE(-?\d*\.?\d+)", body)
            if m:
                acc += float(m.group(1))
                line = line[:m.start()] + f"E{acc:.5f}" + line[m.end():]
        out.append(line)
    return "".join(out), layer

def _validate(text: str):
    moves = len(re.findall(r"(?m)^G[01]\s", text))
    ext = len(re.findall(r"(?m)^G1\s+[^;\n]*\bE-?\d", text))
    if moves < 100 or ext < 50:
        raise RuntimeError(f"G-code failed validation (moves={moves}, extrusion_moves={ext})")
    xs = [float(x) for x in re.findall(r"(?m)^G1 [^;\n]*X(-?[\d.]+)[^;\n]*E", text)]
    if xs and (min(xs) < -111 or max(xs) > 111):
        raise RuntimeError("G-code goes outside the AD5M bed (-110..110)")
    return moves, ext

def slice_stl_orca(data: bytes, filename: str, layer_height=0.20):
    app = _ensure_orca()
    with tempfile.TemporaryDirectory(prefix="ungcad_orca_job_") as td:
        td = Path(td)
        machine, process, filament = _write_presets(td)
        pj = json.loads(process.read_text())
        pj["layer_height"] = str(layer_height)
        process.write_text(json.dumps(pj))
        src = td / (re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(filename).stem) + ".stl")
        src.write_bytes(data)
        out = td / "out"; out.mkdir()
        cmd = [str(app), str(src), "--load-settings", f"{machine};{process}",
               "--load-filaments", str(filament), "--arrange", "1", "--orient", "0",
               "--slice", "0", "--outputdir", str(out)]
        env = os.environ.copy(); env.setdefault("QT_QPA_PLATFORM", "offscreen")
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env, timeout=600)
        files = sorted(out.glob("*.gcode"))
        if p.returncode != 0 or not files:
            raise RuntimeError("OrcaSlicer failed: " + p.stdout[-1500:])
        text = files[0].read_text(encoding="utf-8", errors="ignore")
    try:
        text = _add_thumbnail(text, render_thumbnail(data))
    except Exception:
        pass
    text, layers = _layers_and_absolute_e(text)
    moves, ext = _validate(text)
    t = re.search(r"estimated printing time \(normal mode\) = (.+)", text)
    g = re.search(r"filament used \[g\] = ([\d.]+)", text)
    payload = text.encode()
    return payload, {
        "engine": "OrcaSlicer", "engine_version": ORCA_VERSION,
        "printer_profile": PRINTER, "process_profile": PROCESS, "filament_profile": FILAMENT,
        "bed": BED_TYPE, "layers": layers, "moves": moves, "extrusion_moves": ext,
        "print_time": t.group(1).strip() if t else None,
        "filament_g": float(g.group(1)) if g else None,
        "thumbnail": "thumbnail begin 140x110" in text, "bytes": len(payload),
    }
