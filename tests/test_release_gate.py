from cad_core.release_gate import *
def test_clean_model_releases():
    r=evaluate_release_gate()
    assert r.state is GateState.RELEASE and r.releasable
def test_topology_blocks_release():
    r=evaluate_release_gate(topology_valid=False)
    assert r.state is GateState.BLOCKED and not r.releasable
def test_machine_envelope_blocks_release():
    assert evaluate_release_gate(machine_envelope_ok=False).state is GateState.BLOCKED
def test_stale_downstream_prevents_release():
    assert evaluate_release_gate(downstream_stale=True).state is GateState.STALE
def test_tolerance_warning_is_visible():
    r=evaluate_release_gate(tolerance_valid=False)
    assert r.state is GateState.WARNING and not r.releasable
