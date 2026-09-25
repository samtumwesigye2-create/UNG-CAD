"""Deterministic electrical engineering calculations for CAD-linked components."""
from dataclasses import dataclass
from math import pi, sqrt, atan2, degrees

def ohms_law(*, voltage=None,current=None,resistance=None):
    vals=[voltage,current,resistance]
    if sum(v is None for v in vals)!=1: raise ValueError("provide exactly two of voltage/current/resistance")
    if resistance is not None and resistance<=0: raise ValueError("resistance must be > 0")
    if current is not None and current==0 and resistance is None: raise ValueError("current must be nonzero")
    if voltage is None: voltage=current*resistance
    elif current is None: current=voltage/resistance
    else: resistance=voltage/current
    return voltage,current,resistance

def dc_power(voltage,current): return voltage*current
def energy_joules(power_w,time_s): return power_w*time_s

def conductor_resistance(resistivity_ohm_m,length_m,area_m2):
    if resistivity_ohm_m<0 or length_m<0 or area_m2<=0: raise ValueError("invalid conductor geometry/material")
    return resistivity_ohm_m*length_m/area_m2

def series_resistance(*r): return sum(r)
def parallel_resistance(*r):
    if not r or any(x<=0 for x in r): raise ValueError("positive resistances required")
    return 1/sum(1/x for x in r)

def series_capacitance(*c):
    if not c or any(x<=0 for x in c): raise ValueError("positive capacitances required")
    return 1/sum(1/x for x in c)
def parallel_capacitance(*c): return sum(c)

def series_inductance(*l): return sum(l)
def parallel_inductance(*l):
    if not l or any(x<=0 for x in l): raise ValueError("positive inductances required")
    return 1/sum(1/x for x in l)

@dataclass(frozen=True)
class RLCResult:
    frequency_hz: float
    xl_ohm: float
    xc_ohm: float
    impedance: complex
    magnitude_ohm: float
    phase_deg: float

def series_rlc(resistance_ohm,inductance_h,capacitance_f,frequency_hz):
    if resistance_ohm<0 or inductance_h<0 or capacitance_f<=0 or frequency_hz<=0: raise ValueError("invalid RLC values")
    w=2*pi*frequency_hz; xl=w*inductance_h; xc=1/(w*capacitance_f); z=complex(resistance_ohm,xl-xc)
    return RLCResult(frequency_hz,xl,xc,z,abs(z),degrees(atan2(z.imag,z.real)))

def resonance_hz(inductance_h,capacitance_f):
    if inductance_h<=0 or capacitance_f<=0: raise ValueError("L and C must be positive")
    return 1/(2*pi*sqrt(inductance_h*capacitance_f))

@dataclass(frozen=True)
class TransformerResult:
    voltage_secondary: float
    current_secondary_ideal: float
    turns_ratio: float

def ideal_transformer(primary_turns,secondary_turns,primary_voltage,primary_current=0.0):
    if primary_turns<=0 or secondary_turns<=0: raise ValueError("turns must be positive")
    ratio=secondary_turns/primary_turns
    return TransformerResult(primary_voltage*ratio,primary_current/ratio,ratio)

def capacitor_energy(capacitance_f,voltage): return .5*capacitance_f*voltage*voltage
def inductor_energy(inductance_h,current): return .5*inductance_h*current*current
