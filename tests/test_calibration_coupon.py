import pytest
from cad_core.calibration_coupon import ad5m_coupon_manifest,ad5m_coupon_parts,derive_compensation_profile,measurement_template_rows


def test_coupon_contains_block_holes_and_plugs():
    parts=ad5m_coupon_parts()
    assert "xy_block.stl" in parts
    assert "hole_ring_5.stl" in parts
    assert "plug_6.stl" in parts
    assert all(len(tris)>0 for tris in parts.values())


def test_manifest_and_template_match():
    m=ad5m_coupon_manifest()
    rows=measurement_template_rows()
    assert len(rows)==len(m.nominal_features)
    assert m.nozzle_diameter_mm==0.4


def test_profile_uses_printed_minus_cad_error():
    p=derive_compensation_profile([
      {"feature":"hole","nominal_mm":5.0,"measured_mm":4.8},
      {"feature":"hole","nominal_mm":8.0,"measured_mm":7.8},
      {"feature":"outer","nominal_mm":20.0,"measured_mm":20.2},
      {"feature":"z","nominal_mm":10.0,"measured_mm":9.9},
    ])
    assert p["hole_diameter_error_mm"]==pytest.approx(-.2)
    assert p["xy_scale_error_fraction"]==pytest.approx(.01)
    assert p["z_scale_error_fraction"]==pytest.approx(-.01)
    assert p["calibrated"]


def test_profile_requires_real_measurements():
    with pytest.raises(ValueError):
        derive_compensation_profile([])
