# UNG-CAD Optimization & Simulation Core

This module introduces reusable CAD-side primitives for optimization and simulation.

## Invariants
- OBSERVED, PREDICTED, and SIMULATED states are distinct.
- Simulation output never becomes an observation implicitly.
- Optimization parameters are bounded by explicit constraints.
- Every simulated state records provenance to its base state.

## Initial capabilities
- Unified CAD object state model and history store.
- Simulation runs with provenance.
- Bounded gradient-descent optimization.
- Unit tests for state isolation and optimizer convergence.

Future CAD integrations can connect these primitives to the 3D viewer, slicer/print settings, digital-twin views, uncertainty models, experiment management, and model registry without changing the state-isolation contract.
