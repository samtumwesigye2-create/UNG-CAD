from pathlib import Path

def test_calculus3_ui_has_deployable_api_configuration():
    s=Path("ung-cad-3d/calculus3_dashboard.py").read_text()
    assert "UNG_CALC3_API_URL" in s
    assert "127.0.0.1:8000/api/v3/calculate/manifold" in s
    assert "characteristic_length" in s
    assert "not CFD" in s
