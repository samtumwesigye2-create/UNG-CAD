"""Shared UNG-CAD optimization/simulation primitives."""
from .state import CADState, StateKind, StateStore
from .optimization import OptimizationProblem, GradientDescentOptimizer
from .simulation import SimulationRun
from .math_engine import CADMath
from .geometry_adapter import CADGeometry

__all__ = ["CADState","StateKind","StateStore","OptimizationProblem","GradientDescentOptimizer","SimulationRun","CADMath","CADGeometry"]

from .electromechanical import Connection, ThreePhaseResult, solve_three_phase, winding_graph

from .electromechanical_components import ComponentKind, ElectromechanicalComponent, WindingComponent, MachineAssembly
