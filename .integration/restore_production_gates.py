from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "ung-cad-3d" / "main.py"
BRIDGE = ROOT / "ung-cad-3d" / "ung-cad-ad5m-bridge.py"


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f"missing patch anchor: {label}")
    return text.replace(old, new, 1)


# Restore the existing mandatory production-readiness gate around the new hardened slicer.
main = MAIN.read_text(encoding="utf-8")
import_anchor = "from slicer_cnc import resolve_settings, slice_shapes_to_gcode\n"
imports = '''from slicer_cnc import resolve_settings, slice_shapes_to_gcode\nfrom cad_core.draco_release_gate import RELEASE_MANIFEST, parse_release_manifest, evaluate_package, is_draco_name\ntry:\n    from cad_core.production_readiness import evaluate_manifest as evaluate_production_manifest, sign_machine_file\nexcept ImportError:\n    evaluate_production_manifest = None\n    sign_machine_file = None\n'''
if "from cad_core.draco_release_gate import" not in main:
    main = replace_once(main, import_anchor, imports, "main imports")

start = main.index('@app.post("/api/manufacturing/slice")')
end = main.index('@app.post("/api/manufacturing/preview")', start)
new_slice = '''@app.post("/api/manufacturing/slice")\nasync def slice_part(file:UploadFile=File(...), selected:str=Form(...), production_manifest:str|None=Form(None), layer_height:float=Form(0.20), material:str=Form("PLA"), xy_hole_comp_mm:float=Form(0.0), elephant_foot_mm:float=Form(0.1)):\n    _check_layer_height(layer_height)\n    material = _check_material(material)\n    _check_compensation(xy_hole_comp_mm, elephant_foot_mm)\n\n    # Preserve the package-level production gate before any slicing work begins.\n    package_bytes=await read_upload(file)\n    await file.seek(0)\n    filename=file.filename or "project"\n    entries=[filename]\n    draco_scope=is_draco_name(filename) or is_draco_name(selected)\n    release_ok=True; blockers=[]\n    if filename.lower().endswith(".zip"):\n        try:\n            with open_checked_zip(package_bytes) as z:\n                members=[n for n in z.namelist() if not n.endswith("/")]\n                entries=printable_entries(members)\n                draco_scope=draco_scope or any(is_draco_name(n) for n in entries)\n                release_manifest_name=next((n for n in members if Path(n).name==RELEASE_MANIFEST),None)\n                release_manifest=parse_release_manifest(z.read(release_manifest_name)) if release_manifest_name else None\n                release_ok,blockers=evaluate_package(entries,release_manifest)\n        except ValueError as e:\n            raise HTTPException(422,str(e))\n    elif draco_scope:\n        release_ok=False\n        blockers=["single DRACO production part has no package release manifest"]\n\n    if draco_scope and not release_ok:\n        raise HTTPException(423,{"message":"DRACO package release gate is not PASS; slicing is locked for this DRACO release.","blockers":blockers,"selected":selected})\n\n    supplied_manifest=(production_manifest or "").strip()\n    if supplied_manifest:\n        if evaluate_production_manifest is None:\n            raise HTTPException(503,"Production readiness evaluator unavailable for the supplied release manifest.")\n        try:\n            manifest=json.loads(supplied_manifest)\n            if not isinstance(manifest,dict): raise ValueError("manifest must be a JSON object")\n        except (json.JSONDecodeError,ValueError) as e:\n            raise HTTPException(400,f"Invalid production_manifest: {e}")\n        production_release=evaluate_production_manifest(manifest)\n        if not production_release.get("production_release_allowed"):\n            raise HTTPException(423,{"message":"Production readiness gate is not PASS for the supplied manifest.","release":production_release})\n    elif draco_scope:\n        raise HTTPException(422,{"message":"DRACO production slicing requires a production_manifest.","selected":selected})\n    else:\n        production_release={\n            "production_release_allowed":True,\n            "status":"PASS",\n            "gate_scope":"standalone",\n            "project":Path(filename).stem or "standalone",\n            "revision":"standalone",\n            "manifest_hash":hashlib.sha256(package_bytes).hexdigest(),\n            "note":"Standalone manufacturing path: geometry/process validation is authoritative for this job."\n        }\n\n    if sign_machine_file is None:\n        raise HTTPException(503,"Machine-file signer unavailable; slicing cannot create a printable verified file.")\n\n    source_name, data = await read_selected(file, selected)\n    low=source_name.lower()\n    if low.endswith((".gcode",".gx")) or low.endswith(".gcode.3mf"):\n        GENERATED_DIR.mkdir(parents=True, exist_ok=True)\n        suffix="".join(Path(source_name).suffixes) or ".gcode"\n        stamp=datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")\n        target=GENERATED_DIR / f"{_safe_stem(Path(source_name).stem)}_{stamp}_{secrets.token_hex(4)}{suffix}"\n        target.write_bytes(data)\n        try: release_signature=sign_machine_file(target,production_release)\n        except RuntimeError as e:\n            target.unlink(missing_ok=True)\n            raise HTTPException(503,str(e))\n        job_id=log_job("3d_printer",Path(source_name).name,target.name,"machine_file_ready",None,{"pre_sliced":True},"dashboard")\n        return {"ok":True,"status":"machine_file_ready","job_id":job_id,"source":Path(source_name).name,\n                "machine_file":target.name,"download":f"/api/manufacturing/download/{target.name}",\n                "printer":"FlashForge Adventurer 5M","stats":{"pre_sliced":True},\n                "transmission":"local AD5M bridge required","production_release":production_release,\n                "release_signature":release_signature}\n\n    if not low.endswith(".stl"):\n        raise HTTPException(400,"Only STL geometry or pre-sliced G-code/GX/GCODE.3MF can be sent here")\n    done, failure = _run_3d_slice(data, Path(source_name).name, "dashboard", layer_height, material,\n                                  xy_hole_comp_mm, elephant_foot_mm)\n    if failure:\n        return failure\n    target = done["target"]\n    try: release_signature=sign_machine_file(target,production_release)\n    except RuntimeError as e:\n        target.unlink(missing_ok=True)\n        raise HTTPException(503,str(e))\n    return {"ok": True, "status": "sliced", "job_id": done["job_id"], "source": Path(source_name).name,\n            "machine_file": target.name, "download": f"/api/manufacturing/download/{target.name}",\n            "printer": "FlashForge Adventurer 5M", "stats": done["stats"],\n            "warnings": done["report"]["warnings"], "errors": done["report"]["errors"],\n            "validation": done["report"], "production_release":production_release,\n            "release_signature":release_signature,\n            "transmission": "local AD5M bridge required"}\n\n\n'''
main = main[:start] + new_slice + main[end:]
MAIN.write_text(main, encoding="utf-8")


# Restore cloud/direct-print byte verification around the new safer bridge transport.
bridge = BRIDGE.read_text(encoding="utf-8")
bridge = bridge.replace("import asyncio\n", "import asyncio\nimport hashlib\nimport urllib.request\nimport urllib.parse\n", 1)
constants_anchor = 'STATE = {"printer": None, "check_code": None}\n'
constants = '''STATE = {"printer": None, "check_code": None}\nCLOUD = os.getenv("UNG_CAD_CLOUD", "https://ung-cad-3d-production.up.railway.app").rstrip("/")\nPRINTER_ID = os.getenv("UNG_CAD_PRINTER_ID", "a51a5435")\nCHECK_CODE = os.getenv("UNG_CAD_CHECK_CODE", "").strip()\n'''
if "UNG_CAD_CLOUD" not in bridge:
    bridge = replace_once(bridge, constants_anchor, constants, "bridge cloud constants")

server_anchor = "# ---------- HTTP server ----------\n"
gate_helpers = r'''# ---------- Production release verification + cloud queue ----------

def cloud_json(path, method="GET", body=None):
    data=None if body is None else json.dumps(body).encode()
    req=urllib.request.Request(CLOUD+path,data=data,method=method,headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=30) as r: return json.loads(r.read() or b"{}")


def verify_released_machine_bytes(name, raw):
    safe_name=Path(name).name
    verify=cloud_json("/api/manufacturing/readiness/machine-file/"+urllib.parse.quote(safe_name))
    if not verify.get("ok"):
        raise RuntimeError("PRODUCTION HARD LOCK: "+str(verify.get("message") or "release verification failed"))
    metadata=verify.get("metadata") or {}
    expected=str(metadata.get("machine_file_sha256") or "").lower()
    actual=hashlib.sha256(raw).hexdigest().lower()
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
    except Exception as e:
        print("Cloud queue: auto-pair failed:", e)
        return False


def cloud_worker():
    last_error=None
    while True:
        try:
            try:
                cloud_json("/api/bridge/heartbeat","POST",{"printer_id":PRINTER_ID,"version":BRIDGE_VERSION,"printer":STATE["printer"],"error":last_error})
                last_error=None
            except Exception as hb:
                print("Heartbeat:",hb)
            if not ensure_paired():
                time.sleep(5); continue
            q=urllib.parse.urlencode({"printer_id":PRINTER_ID})
            j=cloud_json("/api/bridge/jobs/next?"+q).get("job")
            if j:
                tmpdir=tempfile.mkdtemp(prefix="ungcad_cloud_")
                path=str(Path(tmpdir)/Path(j["machine_file"]).name)
                try:
                    urllib.request.urlretrieve(CLOUD+j["download"],path)
                    if not Path(path).exists() or Path(path).stat().st_size < 32:
                        raise RuntimeError("Downloaded machine file is empty or incomplete")
                    verify_released_machine_bytes(j["machine_file"],Path(path).read_bytes())
                    result=asyncio.run(print_file(path,True,start=True))
                    cloud_json("/api/bridge/jobs/"+j["id"]+"/complete","POST",{"ok":True,"result":result})
                except Exception as e:
                    cloud_json("/api/bridge/jobs/"+j["id"]+"/complete","POST",{"ok":False,"error":str(e)})
                finally:
                    try:
                        os.unlink(path); os.rmdir(tmpdir)
                    except OSError:
                        pass
        except Exception as e:
            last_error=str(e)
            print("Cloud queue:",e)
        time.sleep(3)


'''
if "def verify_released_machine_bytes" not in bridge:
    bridge = replace_once(bridge, server_anchor, gate_helpers + server_anchor, "bridge gate helpers")

bridge = bridge.replace('if path == "/print":', 'if self.path=="/print":', 1)
print_anchor = '''                safe_name = Path(name).name\n                tmpdir = tempfile.mkdtemp(prefix="ungcad_")\n'''
print_gate = '''                safe_name = Path(name).name\n                try:\n                    release=verify_released_machine_bytes(safe_name,raw)\n                except Exception as gate_error:\n                    return self.out({"error":str(gate_error)},423)\n                tmpdir = tempfile.mkdtemp(prefix="ungcad_")\n'''
if "verify_released_machine_bytes(safe_name,raw)" not in bridge.split('if self.path=="/print":', 1)[1]:
    bridge = replace_once(bridge, print_anchor, print_gate, "direct print gate")
bridge = bridge.replace('return self.out(asyncio.run(print_file(file_path, level, start=start)))',
                        'result=asyncio.run(print_file(file_path, level, start=start))\n                    if isinstance(result,dict): result["production_release"]=release\n                    return self.out(result)', 1)
bridge = bridge.replace('return self.out({"error": "not found"}, 404)', 'return self.out({"error":"not found"},404)')
main_anchor = '    print("Allowed browser origins: " + ", ".join(ALLOWED_ORIGINS))\n'
if "target=cloud_worker" not in bridge:
    bridge = replace_once(bridge, main_anchor,
        '    threading.Thread(target=cloud_worker,daemon=True).start()\n' + main_anchor, "bridge cloud worker startup")
BRIDGE.write_text(bridge, encoding="utf-8")
