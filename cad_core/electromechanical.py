"""Deterministic three-phase electromechanical calculations for UNG-CAD."""
from dataclasses import dataclass
from enum import Enum
from math import sqrt

class Connection(str, Enum):
    DELTA="delta"
    WYE="wye"

@dataclass(frozen=True)
class ThreePhaseResult:
    connection: Connection
    line_voltage: float
    line_current: float
    phase_voltage: float
    phase_current: float
    apparent_power_va: float
    real_power_w: float
    copper_loss_w: float | None

def solve_three_phase(line_voltage: float, line_current: float, connection: Connection|str,
                      power_factor: float=1.0, phase_resistance_ohm: float|None=None) -> ThreePhaseResult:
    if line_voltage < 0 or line_current < 0: raise ValueError("voltage/current must be non-negative")
    if not 0 <= power_factor <= 1: raise ValueError("power_factor must be between 0 and 1")
    c=Connection(connection)
    if c is Connection.DELTA:
        vp=line_voltage; ip=line_current/sqrt(3)
    else:
        vp=line_voltage/sqrt(3); ip=line_current
    s=sqrt(3)*line_voltage*line_current
    loss=None if phase_resistance_ohm is None else 3*ip*ip*phase_resistance_ohm
    return ThreePhaseResult(c,line_voltage,line_current,vp,ip,s,s*power_factor,loss)

def winding_graph(connection: Connection|str):
    c=Connection(connection)
    if c is Connection.DELTA:
        return (("L1","W1","L2"),("L2","W2","L3"),("L3","W3","L1"))
    return (("L1","W1","N"),("L2","W2","N"),("L3","W3","N"))
