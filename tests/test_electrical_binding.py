import pytest
from cad_core.electrical_binding import *
def test_geometry_drives_resistance_and_loss():
    b=ElectricalBinding("wire-1",ConductorGeometry(1000,1),COPPER,current_a=10)
    assert b.resistance_ohm==pytest.approx(.0168)
    assert b.copper_loss_w==pytest.approx(1.68)
def test_geometry_change_recalculates():
    r=ElectricalBindingRegistry(); r.bind(ElectricalBinding("w",ConductorGeometry(1000,1)))
    a=r.get("w").resistance_ohm
    b=r.update_geometry("w",path_length_mm=2000).resistance_ohm
    assert b==pytest.approx(2*a)
def test_cross_section_change_recalculates():
    b=ElectricalBinding("w",ConductorGeometry(1000,2))
    assert b.resistance_ohm==pytest.approx(.0084)
def test_temperature_coefficient():
    b=ElectricalBinding("w",ConductorGeometry(1000,1),COPPER,temperature_c=120)
    assert b.resistance_ohm>ElectricalBinding("w",ConductorGeometry(1000,1),COPPER).resistance_ohm
def test_invalid_geometry_rejected():
    with pytest.raises(ValueError): ElectricalBindingRegistry().bind(ElectricalBinding("w",ConductorGeometry(1,0)))
