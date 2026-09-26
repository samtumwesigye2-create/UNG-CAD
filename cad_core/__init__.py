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

from .engineering_dependencies import EngineeringState, EngineeringResult, EngineeringDependencyEngine

from .release_gate import GateState, GateCheck, ReleaseGateResult, evaluate_release_gate

from .electromechanical_components import ComponentKind, ElectromechanicalComponent, WindingComponent, MachineAssembly

from .circle_geometry import Point3D, CADCircle3D, scale_cad_circle, rotate_point_2d, rotate_cad_circle_z

from .feature_timeline import ToleranceExceededError, ParametricCircle, PrecisionGeometryEngine, UNGCadFeatureTimeline

from .orbital_dynamics import OrbitalState, schwarzschild_radius, weak_field_frame_dragging_scalar, lense_thirring_vector, two_body_acceleration, rk4_two_body_step, orbital_elements, fit_residuals, parameter_sweep

from .ml_analytics import GaussianNaiveBayes, KNN, kmeans, Adam, gradient_descent, classification_metrics, mse, mae, r2, log_loss, kl_divergence, cosine_similarity, correlation, z_scores, MODEL_CATALOG
