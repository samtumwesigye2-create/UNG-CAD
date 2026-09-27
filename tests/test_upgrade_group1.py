import pytest
from cad_core.fit_engine import apply_fit
from cad_core.machine_library import MACHINES,ToolProfile
from cad_core.solid_features import validate_features
def test_fit_profiles(): assert apply_fit(10,"slip")==pytest.approx(10.2)
def test_unknown_fit_rejected():
 with pytest.raises(ValueError):apply_fit(10,"magic")
def test_ad5m_envelope_and_material():
 assert MACHINES["flashforge_ad5m"].validate_part(215,80,40,"petg")
 with pytest.raises(ValueError):MACHINES["flashforge_ad5m"].validate_part(221,80,40,"petg")
def test_tool_validation():
 with pytest.raises(ValueError):ToolProfile("bad",0,"cnc")
def test_solid_feature_contract():
 assert validate_features([{"type":"slot","length_mm":20,"width_mm":4},{"type":"boss","diameter_mm":6,"height_mm":5}])
