from cad_core.engineering_dependencies import *
def test_geometry_invalidation_marks_domains_stale_and_recalculates():
    x={"length":1}
    e=EngineeringDependencyEngine()
    e.register("wire","electrical",lambda:x["length"]*2,depends_on=("wire-geometry",))
    e.register("wire","thermal",lambda:x["length"]*3,depends_on=("wire-geometry",))
    assert len(e.recalculate_stale())==2
    assert e.result("wire","electrical").state is EngineeringState.VALID
    x["length"]=4
    changed=e.invalidate("wire-geometry")
    assert {r.domain for r in changed}=={"electrical","thermal"}
    e.recalculate_stale()
    assert e.result("wire","electrical").value==8
    assert e.result("wire","thermal").value==12
def test_solver_failure_becomes_invalid_not_valid():
    e=EngineeringDependencyEngine()
    e.register("bad","electrical",lambda:1/0,depends_on=("geometry",))
    r=e.recalculate("bad","electrical")
    assert r.state is EngineeringState.INVALID
    assert r.error
def test_revision_increments_on_recalculation():
    e=EngineeringDependencyEngine(); e.register("x","manufacturing",lambda:42)
    assert e.recalculate("x","manufacturing").revision==1
    assert e.recalculate("x","manufacturing").revision==2
