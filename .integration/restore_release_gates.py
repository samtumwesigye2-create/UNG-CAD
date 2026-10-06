from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "ung-cad-3d" / "main.py"
BRIDGE = ROOT / "ung-cad-3d" / "ung-cad-ad5m-bridge.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")

    if "from cad_core.draco_release_gate import" not in text:
        text = replace_once(
            text,
            "from typing import Optional\n",
            "from typing import Optional\n"
            "import sys\n"
            "sys.path.insert(0, str(Path(__file__).resolve().parent.parent))\n"
            "from cad_core.draco_release_gate import RELEASE_MANIFEST, parse_release_manifest, evaluate_package, is_draco_name\n"
            "try:\n"
            "    from production_readiness_api import router as production_readiness_router\n"
            "    from cad_core.production_readiness import evaluate_manifest as evaluate_production_manifest, sign_machine_file, verify_machine_file\n"
            "except ImportError:\n"
            "    production_readiness_router = None\n"
            "    evaluate_production_manifest = None\n"
            "    sign_machine_file = None\n"
            "    verify_machine_file = None\n",
            "main imports",
        )

    if "app.include_router(production_readiness_router)" not in text:
        text = replace_once(
            text,
            'app = FastAPI(title="UNG-CAD-3D", version="1.4.0")\n',
            'app = FastAPI(title="UNG-CAD-3D", version="1.4.0")\n'
            'if production_readiness_router is not None:\n'
            '    app.include_router(production_readiness_router)\n',
            "production readiness router",
        )

    new_slice = r'''@app.post("/api/manufacturing/slice")
async def slice_part(file: UploadFile = File(...), selected: str = Form(...), production_manifest:str|None=Form(None),
                     layer_height: float = Form(0.20), material: str = Form("PLA"),
                     xy_hole_comp_mm: float = Form(0.0), elephant_foot_mm: float = Form(0.1)):
    _check_layer_height(layer_height)
    material = _check_material(material)
    _check_compensation(xy_hole_comp_mm, elephant_foot_mm)

    # Evaluate release policy against the exact uploaded package before slicing.
    package_bytes = await read_upload(file)
    await file.seek(0)
    filename = file.filename or "project"
    entries = [filename]
    draco_scope = is_draco_name(filename) or is_draco_name(selected)
    release_ok = True
    blockers = []
    if filename.lower().endswith(".zip"):
        with open_checked_zip(package_bytes) as z:
            members = [n for n in z.namelist() if not n.endswith("/")]
            entries = printable_entries(members)
            draco_scope = draco_scope or any(is_draco_name(n) for n in entries)
            release_manifest_name = next((n for n in members if Path(n).name == RELEASE_MANIFEST), None)
            release_manifest = parse_release_manifest(z.read(release_manifest_name)) if release_manifest_name else None
            release_ok, blockers = evaluate_package(entries, release_manifest)
    elif draco_scope:
        release_ok = False
        blockers = ["single DRACO production part has no package release manifest"]

    if draco_scope and not release_ok:
        raise HTTPException(423, {"message":"DRACO package release gate is not PASS; slicing is locked for this DRACO release.",
                                  "blockers":blockers, "selected":selected})

    supplied_manifest = (production_manifest or "").strip()
    if supplied_manifest:
        if evaluate_production_manifest is None:
            raise HTTPException(503, "Production readiness evaluator unavailable for the supplied release manifest.")
        try:
            manifest = json.loads(supplied_manifest)
            if not isinstance(manifest, dict):
                raise ValueError("manifest must be a JSON object")
        except (json.JSONDecodeError, ValueError) as exc:
            raise HTTPException(400, f"Invalid production_manifest: {exc}")
        production_release=evaluate_production_manifest(manifest)
        if not production_release.get("production_release_allowed"):
            raise HTTPException(423, {"message":"Production readiness gate is not PASS for the supplied manifest.",
                                      "release":production_release})
    elif draco_scope:
        raise HTTPException(422, {"message":"DRACO production slicing requires a production_manifest.",
                                  "selected":selected})
    else:
        # Standalone manufacturing path: normal geometry/process validation is authoritative.
        production_release={
            "production_release_allowed":True,
            "status":"PASS",
            "gate_scope":"standalone",
            "project":Path(filename).stem or "standalone",
            "revision":"standalone",
            "manifest_hash":hashlib.sha256(package_bytes).hexdigest(),
            "note":"Standalone manufacturing path: geometry/process validation is authoritative for this job."
        }

    if sign_machine_file is None:
        raise HTTPException(503, "Machine-file signer unavailable; slicing cannot create a printable verified file.")

    await file.seek(0)
    source_name, data = await read_selected(file, selected)
    low = source_name.lower()

    if low.endswith((".gcode", ".gx", ".3mf")):
        target = unique_output_path(Path(source_name).stem, "AD5M")
        target.write_bytes(data)
        try:
            release_signature=sign_machine_file(target,production_release)
        except RuntimeError as exc:
            target.unlink(missing_ok=True)
            raise HTTPException(503, str(exc))
        job_id = log_job("3d_printer", Path(source_name).name, target.name, "sliced", None,
                         {"pre_sliced": True}, "dashboard")
        return {"ok":True,"status":"machine_file_ready","job_id":job_id,
                "source":Path(source_name).name,"machine_file":target.name,
                "download":f"/api/manufacturing/download/{target.name}",
                "printer":"FlashForge Adventurer 5M","stats":{"pre_sliced":True},
                "transmission":"local AD5M bridge required","production_release":production_release,
                "release_signature":release_signature}

    if not low.endswith(".stl"):
        raise HTTPException(400, "Only STL geometry or pre-sliced G-code/GX/3MF machine files can be used here")

    # Compatibility alias keeps the release-gate ordering contract explicit while
    # routing through the new validated slicer implementation.
    slice_stl = _run_3d_slice
    done, failure = slice_stl(data, Path(source_name).name, "dashboard", layer_height, material,
                              xy_hole_comp_mm, elephant_foot_mm)
    if failure:
        return failure
    target = done["target"]
    try:
        release_signature=sign_machine_file(target,production_release)
    except RuntimeError as exc:
        target.unlink(missing_ok=True)
        raise HTTPException(503, str(exc))
    return {"ok":True,"status":"sliced","job_id":done["job_id"],"source":Path(source_name).name,
            "machine_file":target.name,"download":f"/api/manufacturing/download/{target.name}",
            "printer":"FlashForge Adventurer 5M","stats":done["stats"],
            "warnings":done["report"]["warnings"],"errors":done["report"]["errors"],
            "validation":done["report"],"transmission":"local AD5M bridge required",
            "production_release":production_release,"release_signature":release_signature}


def _save_gcode(source_name, gcode, suffix):
    """Compatibility helper retained for production-gate contract boundaries."""
    target = unique_output_path(Path(source_name).stem, suffix.strip("_").replace(".gcode", "") or "machine")
    target.write_bytes(gcode if isinstance(gcode, bytes) else gcode.encode())
    return target
'''

    pattern = re.compile(
        r'@app\.post\("/api/manufacturing/slice"\)\nasync def slice_part.*?(?=\n\n@app\.post\("/api/manufacturing/preview"\))',
        re.S,
    )
    text, count = pattern.subn(new_slice.rstrip(), text, count=1)
    if count != 1:
        raise RuntimeError(f"slice endpoint: expected exactly one replacement, found {count}")

    MAIN.write_text(text, encoding="utf-8")


def patch_bridge() -> None:
    text = BRIDGE.read_text(encoding="utf-8")

    if "import urllib.request" not in text:
        text = replace_once(
            text,
            "import asyncio\n",
            "import asyncio\nimport hashlib\nimport urllib.request\nimport urllib.parse\n",
            "bridge imports",
        )

    if "CLOUD = os.getenv" not in text:
        text = replace_once(
            text,
            'PORT = 8765\n',
            'PORT = 8765\n'
            'CLOUD = os.getenv("UNG_CAD_CLOUD", "https://ung-cad-3d-production.up.railway.app").rstrip("/")\n'
            'PRINTER_ID = os.getenv("UNG_CAD_PRINTER_ID", "a51a5435")\n'
            'CHECK_CODE = os.getenv("UNG_CAD_CHECK_CODE", "").strip()\n',
            "bridge cloud constants",
        )

    if "def verify_released_machine_bytes" not in text:
        cloud_block = r'''

def cloud_json(path, method="GET", body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(CLOUD + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read() or b"{}")


def verify_released_machine_bytes(name, raw):
    """Hard lock: cloud release metadata and exact local bytes must both match."""
    safe_name = Path(name).name
    verify = cloud_json("/api/manufacturing/readiness/machine-file/" + urllib.parse.quote(safe_name))
    if not verify.get("ok"):
        raise RuntimeError("PRODUCTION HARD LOCK: " + str(verify.get("message") or "release verification failed"))
    metadata = verify.get("metadata") or {}
    expected = str(metadata.get("machine_file_sha256") or "").lower()
    actual = hashlib.sha256(raw).hexdigest().lower()
    if not expected or actual != expected:
        raise RuntimeError("PRODUCTION HARD LOCK: machine file hash does not match approved release")
    return metadata


def ensure_paired():
    if STATE["check_code"]:
        return True
    if not CHECK_CODE:
        return False
    try:
        asyncio.run(connect(CHECK_CODE))
        return True
    except Exception as exc:
        print("Cloud queue auto-pair failed:", exc)
        return False


def cloud_worker():
    """Optional cloud queue worker; every downloaded machine file is release-verified before printing."""
    while True:
        try:
            if not ensure_paired():
                time.sleep(5)
                continue
            q = urllib.parse.urlencode({"printer_id": PRINTER_ID})
            j = cloud_json("/api/bridge/jobs/next?" + q).get("job")
            if j:
                tmpdir = tempfile.mkdtemp(prefix="ungcad_cloud_")
                path = str(Path(tmpdir) / Path(j["machine_file"]).name)
                try:
                    urllib.request.urlretrieve(CLOUD + j["download"], path)
                    if not Path(path).exists() or Path(path).stat().st_size < 32:
                        raise RuntimeError("Downloaded machine file is empty or incomplete")
                    verify_released_machine_bytes(j["machine_file"],Path(path).read_bytes())
                    result = asyncio.run(print_file(path, True, start=True))
                    cloud_json("/api/bridge/jobs/" + j["id"] + "/complete", "POST", {"ok": True, "result": result})
                except Exception as exc:
                    cloud_json("/api/bridge/jobs/" + j["id"] + "/complete", "POST", {"ok": False, "error": str(exc)})
                finally:
                    try:
                        os.unlink(path)
                        os.rmdir(tmpdir)
                    except OSError:
                        pass
        except Exception as exc:
            print("Cloud queue:", exc)
        time.sleep(3)
'''
        text = replace_once(
            text,
            "\n\n# ---------- CNC / laser over USB serial (GRBL-style controllers) ----------",
            cloud_block + "\n\n# ---------- CNC / laser over USB serial (GRBL-style controllers) ----------",
            "bridge release verifier",
        )

    text = text.replace('if path == "/print":', 'if self.path=="/print":', 1)

    direct_old = '''                safe_name = Path(name).name
                tmpdir = tempfile.mkdtemp(prefix="ungcad_")
'''
    if "verify_released_machine_bytes(safe_name,raw)" not in text:
        direct_new = '''                safe_name = Path(name).name
                # Direct/local printing is not a bypass: verify the cloud-approved
                # release and exact bytes before the file reaches the printer.
                try:
                    release=verify_released_machine_bytes(safe_name,raw)
                except Exception as gate_error:
                    return self.out({"error":str(gate_error)},423)
                tmpdir = tempfile.mkdtemp(prefix="ungcad_")
'''
        text = replace_once(text, direct_old, direct_new, "direct print hard lock")

    old_print = '                    return self.out(asyncio.run(print_file(file_path, level, start=start)))\n'
    if old_print in text:
        new_print = '''                    result = asyncio.run(print_file(file_path, level, start=start))
                    if isinstance(result, dict):
                        result["production_release"] = release
                    return self.out(result)
'''
        text = replace_once(text, old_print, new_print, "direct print release metadata")

    text = text.replace('            return self.out({"error": "not found"}, 404)\n        except Exception as e:\n            self.out({"error": str(e)}, 500)\n\n    def log_message',
                        '            return self.out({"error":"not found"},404)\n        except Exception as e:\n            self.out({"error": str(e)}, 500)\n\n    def log_message', 1)

    if "UNG_CAD_ENABLE_CLOUD_QUEUE" not in text:
        text = replace_once(
            text,
            "    make_server().serve_forever()\n",
            "    if os.getenv(\"UNG_CAD_ENABLE_CLOUD_QUEUE\", \"\").strip().lower() in (\"1\", \"true\", \"yes\"):\n"
            "        threading.Thread(target=cloud_worker, name=\"ungcad-cloud-worker\", daemon=True).start()\n"
            "        print(\"Cloud queue worker enabled; every machine file is release-verified before print.\")\n"
            "    make_server().serve_forever()\n",
            "optional cloud worker startup",
        )

    BRIDGE.write_text(text, encoding="utf-8")


patch_main()
patch_bridge()
print("Restored production release gates into integrated UNG-CAD implementation.")
