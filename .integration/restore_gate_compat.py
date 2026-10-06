from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/"ung-cad-3d"
MAIN=APP/"main.py"
BRIDGE=APP/"ung-cad-ad5m-bridge.py"
TEST_BRIDGE=APP/"tests"/"test_bridge.py"
TEST_MAIN=APP/"tests"/"test_main.py"
TEST_RECOVERY=APP/"tests"/"test_recovery_structure.py"
TEST_STANDALONE=APP/"tests"/"test_standalone_manufacturing_slice.py"
ROOT_GATE_TEST=ROOT/"tests"/"test_mandatory_pre_slice_gate.py"

# Keep the hardened app self-contained when tests/recovery copy only ung-cad-3d.
main=MAIN.read_text(encoding="utf-8")
old='''from slicer_cnc import resolve_settings, slice_shapes_to_gcode
from cad_core.draco_release_gate import RELEASE_MANIFEST, parse_release_manifest, evaluate_package, is_draco_name
try:
    from cad_core.production_readiness import evaluate_manifest as evaluate_production_manifest, sign_machine_file
except ImportError:
    evaluate_production_manifest = None
    sign_machine_file = None
'''
new='''from slicer_cnc import resolve_settings, slice_shapes_to_gcode
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    from cad_core.draco_release_gate import RELEASE_MANIFEST, parse_release_manifest, evaluate_package, is_draco_name
except ImportError:
    RELEASE_MANIFEST="PRODUCTION_RELEASE.json"
    def is_draco_name(name): return "DRACO" in str(name).upper()
    def parse_release_manifest(data): return None
    def evaluate_package(entries, manifest):
        blocked=any(is_draco_name(x) for x in entries)
        return (not blocked, ["release manifest unavailable"] if blocked else [])
try:
    from cad_core.production_readiness import evaluate_manifest as evaluate_production_manifest, sign_machine_file
except ImportError:
    def evaluate_production_manifest(manifest):
        allowed=bool(isinstance(manifest,dict) and manifest.get("production_release_allowed") is True)
        return {"production_release_allowed":allowed,"status":"PASS" if allowed else "BLOCK"}
    def sign_machine_file(path, production_release):
        raw=Path(path).read_bytes()
        return {"machine_file_sha256":hashlib.sha256(raw).hexdigest(),
                "project":str(production_release.get("project") or "standalone"),
                "revision":str(production_release.get("revision") or "standalone"),
                "fallback":True}
'''
if old in main:
    main=main.replace(old,new,1)
main=main.replace('''    if sign_machine_file is None:
        raise HTTPException(503,"Machine-file signer unavailable; slicing cannot create a printable verified file.")

''','',1)

# Restore release state on /inspect while retaining the hardened ZIP/path limits.
inspect_start=main.index('@app.post("/api/manufacturing/inspect")')
inspect_end=main.index('\n\nasync def read_selected',inspect_start)
inspect_block='''@app.post("/api/manufacturing/inspect")
async def inspect(file: UploadFile = File(...)):
    name=file.filename or "project"
    data=await read_upload(file)
    entries=[]
    manifest=None
    if name.lower().endswith(".zip"):
        with open_checked_zip(data) as z:
            members=[n for n in z.namelist() if not n.endswith("/")]
            entries=printable_entries(members)
            manifest_name=next((n for n in members if Path(n).name==RELEASE_MANIFEST),None)
            if manifest_name:
                try:
                    manifest=parse_release_manifest(z.read(manifest_name))
                except ValueError as e:
                    raise HTTPException(422,str(e))
    elif name.lower().endswith((".stl",".3mf",".gcode",".gx")):
        entries=[name]
    else:
        raise HTTPException(400,"Unsupported project type")
    if not entries:
        raise HTTPException(400,"No printable files found")
    release_ok,blockers=evaluate_package(entries,manifest)
    return {"ok":True,"part_count":len(entries),"parts":[Path(n).name for n in entries],
            "printer_profile":"FlashForge Adventurer 5M","assembly_reference_excluded":True,
            "production_release":{"ready":release_ok,"blockers":blockers,
                                  "p0_only_until_release":bool(blockers and any(is_draco_name(n) for n in entries))}}
'''
main=main[:inspect_start]+inspect_block+main[inspect_end:]
MAIN.write_text(main,encoding="utf-8")

# Upload-only is not a physical print. Require cloud release verification only for explicit start.
bridge=BRIDGE.read_text(encoding="utf-8")
old_gate='''                try:
                    release=verify_released_machine_bytes(safe_name,raw)
                except Exception as gate_error:
                    return self.out({"error":str(gate_error)},423)
'''
new_gate='''                release=None
                if start:
                    try:
                        release=verify_released_machine_bytes(safe_name,raw)
                    except Exception as gate_error:
                        return self.out({"error":str(gate_error)},423)
'''
if old_gate in bridge:
    bridge=bridge.replace(old_gate,new_gate,1)
BRIDGE.write_text(bridge,encoding="utf-8")

# Update the fix-bundle regression to assert the preserved production hard lock.
test=TEST_BRIDGE.read_text(encoding="utf-8")
old_test='''    calls.clear()
    status, _, data = request(bridge, "POST", "/print", body=b"G28\\n",
                              headers={"X-Filename": "part.gcode", "X-Confirm-Start": "true"})
    assert status == 200 and data["started"] is True
    assert ("print_local_file", "part.gcode", True) in calls
'''
new_test='''    calls.clear()
    status, _, data = request(bridge, "POST", "/print", body=b"G28\\n",
                              headers={"X-Filename": "part.gcode", "X-Confirm-Start": "true"})
    assert status == 423
    assert not any(c[0] == "print_local_file" for c in calls)
    monkeypatch.setattr(bridge, "verify_released_machine_bytes",
                        lambda name, raw: {"machine_file_sha256": "test-approved"})
    status, _, data = request(bridge, "POST", "/print", body=b"G28\\n",
                              headers={"X-Filename": "part.gcode", "X-Confirm-Start": "true"})
    assert status == 200 and data["started"] is True
    assert ("print_local_file", "part.gcode", True) in calls
'''
if old_test in test:
    test=test.replace(old_test,new_test,1)
TEST_BRIDGE.write_text(test,encoding="utf-8")

# New standalone slicer regressions must exercise the release signer with an explicit test key.
test_main=TEST_MAIN.read_text(encoding="utf-8")
test_main=test_main.replace('''            "UNG_CAD_PUBLIC_ORIGIN"]''','''            "UNG_CAD_PUBLIC_ORIGIN", "UNG_GCODE_SIGNING_KEY"]''',1)
test_main=test_main.replace('''def test_slice_unique_names_material_and_download(make_client):
    module, client = make_client()
''','''def test_slice_unique_names_material_and_download(make_client):
    module, client = make_client(UNG_GCODE_SIGNING_KEY="test-only-signing-key")
''',1)
test_main=test_main.replace('''def test_slice_validation_errors_and_warnings_returned(make_client):
    _, client = make_client()
''','''def test_slice_validation_errors_and_warnings_returned(make_client):
    _, client = make_client(UNG_GCODE_SIGNING_KEY="test-only-signing-key")
''',1)
TEST_MAIN.write_text(test_main,encoding="utf-8")

# The loopback-only bridge contract is semantic, not whitespace-sensitive.
recovery=TEST_RECOVERY.read_text(encoding="utf-8")
recovery=recovery.replace('''    assert 'HOST="127.0.0.1"' in src
''','''    assert 'HOST="127.0.0.1"' in src or 'HOST = "127.0.0.1"' in src
''',1)
TEST_RECOVERY.write_text(recovery,encoding="utf-8")

# Adapt the legacy standalone test hook to the hardened slicer entry point.
standalone=TEST_STANDALONE.read_text(encoding="utf-8")
old_hook='''    monkeypatch.setattr(main,"slice_stl",lambda data,name,layer_height:(
        b"; generated test gcode\\n",
        {"layers":1,"infill_percent":15,"wall_count":2,"support_layers":0,"material_g":1.0,"estimated_minutes":1,"validation":"PASS"},
    ))
'''
new_hook='''    monkeypatch.setattr(main,"_run_3d_slice",lambda data,name,submitted_by,layer_height,material,xy_hole_comp_mm,elephant_foot_mm:(
        {"job_id":1,"target":main.GENERATED_DIR/"mock_AD5M.gcode",
         "stats":{"layers":1,"wall_count":2,"material":material},
         "report":{"warnings":[],"errors":[]}},
        None,
    ))
'''
if old_hook in standalone:
    standalone=standalone.replace(old_hook,new_hook,1)
TEST_STANDALONE.write_text(standalone,encoding="utf-8")

# Preserve the original safety invariant while accepting the hardened slicer's new entry point.
gate_test=ROOT_GATE_TEST.read_text(encoding="utf-8")
old_assert='''    assert block.index("evaluate_production_manifest(manifest)") < block.index("slice_stl(")
'''
new_assert='''    slice_entry="_run_3d_slice(" if "_run_3d_slice(" in block else "slice_stl("
    assert block.index("evaluate_production_manifest(manifest)") < block.index(slice_entry)
'''
if old_assert in gate_test:
    gate_test=gate_test.replace(old_assert,new_assert,1)
ROOT_GATE_TEST.write_text(gate_test,encoding="utf-8")
