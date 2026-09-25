# UNG-GEOMETRY integration

UNG-GEOMETRY is now embedded as the deterministic geometry foundation of UNG-CAD.

Boundary:
- **UNG-GEOMETRY**: primitives, mesh/B-Rep contracts, tolerances, constraints, assemblies,
  continuity, units, manufacturing job contracts, machine profiles, dependency invalidation,
  provenance, controller validation, exchange-format taxonomy, and integrity states.
- **UNG-CAD**: UI, project workflow, visualization, slicer/CAM orchestration, device bridges,
  simulation orchestration, and manufacturing execution.

The integration facade is `cad_core.geometry_adapter.CADGeometry`.

The geometry dependency graph marks downstream manufacturing artifacts STALE when a source
model changes, so slicer/CAM outputs can be regenerated rather than silently reused.

Current exact-backend limits remain explicit: the package does not pretend to provide a
production exact B-Rep Boolean solver, full sketch constraint solver, STEP/IGES parser,
FEA solver, topology optimizer, or 5-axis CAM kernel until those backends are implemented.
