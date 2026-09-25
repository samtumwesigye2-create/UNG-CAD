from cad_core.release_gate import GateState
from cad_core.release_evidence import GateEvidence,evidence_check,aggregate_evidence

def test_missing_advanced_solver_is_stale_not_passed():
    c=evidence_check("assembly",GateEvidence("collision-engine",False,None))
    assert c.state is GateState.STALE
def test_failed_evidence_blocks():
    c=evidence_check("machine-envelope",GateEvidence("machine-profile",True,False,"outside X"))
    assert c.state is GateState.BLOCKED
def test_all_real_evidence_releases():
    cs=[evidence_check(n,GateEvidence(n,True,True)) for n in ("topology","dimensions","manufacturability","machine-envelope","toolpath")]
    assert aggregate_evidence(cs) is GateState.RELEASE
def test_stale_dominates_warning():
    from cad_core.release_gate import GateCheck
    assert aggregate_evidence([GateCheck("tol",GateState.WARNING),GateCheck("cam",GateState.STALE)]) is GateState.STALE
