from cad_core.data_fabric import normalize_record, validate_records
from cad_core.evaluation_gate import evaluate, require_pass
from cad_core.manufacturing_feedback import dimensional_feedback, calibration_summary
import pytest

def test_data_contract_normalizes_and_validates():
    r=normalize_record("CAD", {"diameter_mm": 10}, metadata={"unit":"mm"}, provenance="test")
    assert r.source=="CAD" and r.payload["diameter_mm"]==10
    assert validate_records([r])==[r]

def test_evaluation_gate_pass_and_block():
    ok=evaluate({"confidence":.95,"error_mm":.05},{"confidence":(">=",.9),"error_mm":("<=",.1)})
    require_pass(ok)
    bad=evaluate({"confidence":.5},{"confidence":(">=",.9)})
    assert not bad.passed
    with pytest.raises(RuntimeError): require_pass(bad)

def test_dimensional_feedback_and_axis_summary():
    f=dimensional_feedback(100,100.5)
    assert f.error_mm==pytest.approx(.5)
    assert f.scale_correction==pytest.approx(100/100.5)
    s=calibration_summary({"x":(100,100.5),"y":(80,79.8)})
    assert set(s)=={"x","y"}
