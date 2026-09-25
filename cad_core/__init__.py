"""Shared UNG-CAD optimization/simulation primitives."""
from .state import CADState, StateKind, StateStore
from .optimization import OptimizationProblem, GradientDescentOptimizer
from .simulation import SimulationRun
from .math_engine import CADMath
from .geometry_adapter import CADGeometry

__all__ = ["CADState","StateKind","StateStore","OptimizationProblem","GradientDescentOptimizer","SimulationRun","CADMath","CADGeometry"]

from .electromechanical import Connection, ThreePhaseResult, solve_three_phase, winding_graph

from .surfaces_of_revolution import GabrielHornAnalysis, gabriel_radius, analyze_gabriel_horn, gabriel_horn_profile

from .electrical import ohms_law, dc_power, energy_joules, conductor_resistance, series_resistance, parallel_resistance, series_capacitance, parallel_capacitance, series_inductance, parallel_inductance, series_rlc, resonance_hz, ideal_transformer, capacitor_energy, inductor_energy, RLCResult, TransformerResult

from .electrical_binding import ElectricalMaterial, ConductorGeometry, ElectricalBinding, ElectricalBindingRegistry, COPPER, ALUMINUM
