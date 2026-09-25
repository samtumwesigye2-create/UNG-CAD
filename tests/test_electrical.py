from math import pi
import pytest
from cad_core.electrical import *
def test_ohm_and_power():
    assert ohms_law(voltage=12,resistance=6)==(12,2,6)
    assert dc_power(12,2)==24
    assert energy_joules(24,10)==240
def test_conductor_geometry_drives_resistance():
    assert conductor_resistance(1.68e-8,10,1e-6)==pytest.approx(.168)
def test_series_parallel():
    assert series_resistance(2,3,5)==10
    assert parallel_resistance(10,10)==pytest.approx(5)
    assert parallel_capacitance(1e-6,2e-6)==pytest.approx(3e-6)
    assert series_capacitance(1e-6,1e-6)==pytest.approx(.5e-6)
def test_rlc_and_resonance():
    f=resonance_hz(.01,1e-6)
    r=series_rlc(10,.01,1e-6,f)
    assert r.impedance.imag==pytest.approx(0,abs=1e-10)
    assert r.magnitude_ohm==pytest.approx(10)
def test_transformer():
    r=ideal_transformer(100,50,120,2)
    assert r.voltage_secondary==60
    assert r.current_secondary_ideal==4
def test_stored_energy():
    assert capacitor_energy(1,2)==2
    assert inductor_energy(2,3)==9
