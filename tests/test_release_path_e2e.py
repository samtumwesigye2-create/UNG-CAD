from pathlib import Path
from cad_core.release_gate import GateState, evaluate_release_gate
from cad_core.engineering_dependencies import EngineeringDependencyEngine, EngineeringState

ROOT=Path(__file__).resolve().parents[1]
JS=(ROOT/"ung-cad-3d"/"viewer.js").read_text()

def test_cad_change_to_release_gate_contract():
    eng=EngineeringDependencyEngine()
    eng.register("part","electrical",lambda: {"resistance_ohm":0.1})
    assert eng.recalculate("part","electrical").state is EngineeringState.VALID
    eng.invalidate("part")
    # Geometry edits invalidate downstream engineering/manufacturing evidence.
    assert "markEngineeringStale" in JS
    assert "releaseGateState='STALE'" in JS
    stale=evaluate_release_gate(downstream_stale=True)
    assert stale.state is GateState.STALE and not stale.releasable

def test_bad_topology_blocks_manufacturing_path():
    blocked=evaluate_release_gate(topology_valid=False)
    assert blocked.state is GateState.BLOCKED and not blocked.releasable
    assert "Manufacturing BLOCKED — Production Release Gate failed" in JS

def test_machine_envelope_violation_blocks_release():
    assert evaluate_release_gate(machine_envelope_ok=False).state is GateState.BLOCKED

def test_clean_validated_path_releases():
    released=evaluate_release_gate()
    assert released.state is GateState.RELEASE and released.releasable

def test_studio_requires_toolpath_validation_before_handoff():
    assert "['Toolpath',false]" in JS
    assert "Manufacturing STALE — regenerate/validate toolpath before release" in JS
