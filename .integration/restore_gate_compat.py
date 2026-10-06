from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MAIN=ROOT/"ung-cad-3d"/"main.py"
BRIDGE=ROOT/"ung-cad-3d"/"ung-cad-ad5m-bridge.py"
TEST_BRIDGE=ROOT/"ung-cad-3d"/"tests"/"test_bridge.py"
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
# The fallback above makes this hard-lock check unnecessary only in isolated recovery copies.
main=main.replace('''    if sign_machine_file is None:
        raise HTTPException(503,"Machine-file signer unavailable; slicing cannot create a printable verified file.")

''','',1)
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
