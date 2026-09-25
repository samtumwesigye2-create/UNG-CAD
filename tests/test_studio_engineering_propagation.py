from pathlib import Path
J=(Path(__file__).resolve().parents[1]/"ung-cad-3d"/"viewer.js").read_text()
def test_studio_engineering_state_pipeline():
    for token in ("engineeringStates","markEngineeringStale","recalculateEngineering","state='STALE'","state='VALID'","state='INVALID'"): assert token in J
def test_dimension_edit_propagates():
    start=J.index("function applyDimensions()"); block=J[start:J.index("function updateTwin",start)]
    assert "markEngineeringStale(o.id)" in block
    assert "renderElectrical(o.id)" in block
