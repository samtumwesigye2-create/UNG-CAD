# Shared Physics, Digital Twin, Predictive Health, and Evidence Architecture

Status: approved architecture and implementation contract.

This document extends the existing UNG shared geometry, simulation, analytics, runtime-health, manufacturing, and data-fabric capabilities. It does not create duplicate standalone systems.

## 1. CFD and thermal simulation core

The shared physics core shall support:

- incompressible continuity and Navier-Stokes formulations
- pressure, velocity, temperature, viscosity, density, and body-force fields
- no-slip, moving-wall, velocity-inlet, pressure-outlet, fan/source, symmetry, and thermal boundary conditions
- exact benchmark cases including plane Couette flow and pressure-driven Poiseuille flow
- Reynolds-number calculation and regime diagnostics
- structured/unstructured discretization contracts for finite-difference / finite-volume implementations
- iterative nonlinear and pressure-velocity coupling solvers
- residual monitoring, conservation checks, mesh-refinement studies, and convergence gates
- vector fields, scalar fields, streamlines, pressure maps, temperature maps, and hot-zone visualization
- conjugate heat-transfer hooks for solid/fluid coupling
- solver provenance: geometry revision, mesh settings, material properties, boundary conditions, solver version, convergence history, and timestamp

Plane Couette flow is a required analytical regression test:

```
u(y) = U*y/h
```

A CFD result that fails conservation, residual, benchmark, or mesh-convergence requirements shall be marked INVALID and may not release manufacturing geometry.

## 2. CAD-to-physics pipeline

The production simulation path is:

**CAD geometry -> identify fluid/solid regions -> assign materials and boundary conditions -> mesh -> solve -> validate -> visualize -> optimization -> manufacturing preflight**

Geometry edits invalidate stale simulation results automatically.

The physics layer shall expose machine-readable failure states rather than silently substituting approximate results.

## 3. Closed-loop thermal and airflow optimization

The optimization layer may vary only approved parameters, including:

- vent area, spacing, and placement
- internal duct geometry
- fan position and orientation
- component spacing and airflow clearance
- selected thermal-interface parameters

Frozen geometry, interfaces, validated sensor seats, mounting datums, connector interfaces, required fields of view, and manufacturing constraints remain locked unless explicitly released for optimization.

Each candidate follows:

**regenerate parametric geometry -> collision/clearance check -> CFD/thermal solve -> numerical validation -> objective evaluation -> manufacturability check -> retain/reject**

Invalid solver runs and non-manufacturable geometry are rejected rather than scored.

## 4. DRACO reference case

DRACO is the first hardware validation case for the shared physics pipeline.

The reference model includes:

- 40 mm base fan
- Raspberry Pi Zero 2 W
- regulator and other internal electronics volumes
- vents and internal air volume
- servo/transmission envelopes
- wiring clearances
- AMG8833 thermal-sensor region

Optimization objectives include:

- reduce component temperature
- eliminate stagnant or recirculating hot-air zones
- reduce unnecessary pressure loss
- maintain useful airflow through the base
- prevent warm exhaust from contaminating the AMG8833 measurement region
- preserve cable clearance, mechanical travel, serviceability, and printable wall/bridge geometry

## 5. Digital Twin

The Digital Twin binds a physical configuration to:

- CAD revision and assembly configuration
- component/material model
- CFD/thermal simulation revision
- operating mode
- telemetry stream
- maintenance/recovery history

Runtime telemetry may include:

- processor temperature
- fan command/state/speed where available
- regulator and board temperatures where instrumented
- servo activity/current/load indicators where available
- supply voltage/current
- sensor operating state
- ambient/environmental measurements

The UI shall support Predicted / Measured / Error views.

Calibration shall compare measured and predicted behavior and may estimate effective fan flow, vent resistance, component heat generation, and heat-transfer coefficients. Calibrated values are versioned and may not overwrite original engineering assumptions without traceability.

## 6. Predictive health and fault isolation

Digital-Twin residuals and runtime telemetry feed the shared analytics/health engine.

Detectable conditions include:

- fan degradation or obstruction
- blocked vents or abnormal pressure/airflow behavior
- abnormal processor or regulator heating
- servo loading or repeated stall behavior
- sensor drift
- thermal contamination of a sensing region
- persistent divergence between predicted and measured operation

Fault records shall include:

- affected component/subsystem
- severity
- confidence
- supporting telemetry
- relevant model revision
- diagnostic evidence
- first/last occurrence
- recovery attempts and outcome

No generic health flag should replace available fault-isolation evidence.

## 7. Automated recovery and degraded operation

Predictive-health results integrate with the existing Runtime Health & Recovery Engine.

Permitted recovery actions include:

- workload reduction
- thermal throttling
- fan-control changes
- sensor isolation
- subsystem/service restart
- safe degraded-mode operation
- operator escalation

Recovery policy must prevent endless restart loops. Unsafe or repeatedly failing conditions escalate instead of being continuously retried.

All automated actions are logged and fed back into health analytics and model calibration.

## 8. Cross-system rollout

The shared implementation is reusable by:

- UNG-CAD / Manufacturing
- DRACO
- LINK256
- VECTOR where geometry/thermal/flow or machine-state modeling applies
- future UNG physical hardware

Each system supplies its geometry, components, boundary conditions, constraints, telemetry mapping, and release rules while using the same simulation, optimization, validation, analytics, visualization, provenance, and runtime-health infrastructure.

## 9. Manufacturing release gate

The manufacturing gate becomes:

**Geometry -> Dimensions -> Tolerances -> Assembly -> Collision/Clearance -> Physics/CFD/Thermal -> Manufacturability -> Machine Envelope -> Toolpath**

Critical failures block Auto Prepare / production release. Non-critical warnings remain visible with evidence.

A manufacturing release shall retain:

- CAD hash/revision
- simulation revision
- solver/model version
- mesh and boundary-condition metadata
- convergence state
- optimization parameter set
- machine/material profile
- preflight evidence

Stale simulation evidence shall never validate a changed CAD revision.

## 10. Authorized evidence and device-data analysis

The shared Data Fabric gains an authorized evidence-analysis layer for data the operator is permitted to access.

Supported inputs include user-provided or otherwise authorized:

- device backups and exports
- message/call/contact exports
- CSV, JSON, XML, and similar structured exports
- media folders and attachment collections
- application-generated reports and archives

Core capabilities:

- immutable original evidence storage
- SHA-256 or stronger content hashes
- provenance and chain-of-custody metadata
- parser/extractor versioning
- normalized people, account, device, message, call, media, location, and event records
- timestamp normalization
- entity resolution
- deduplication
- timeline construction
- communication/relationship graphs
- search, filtering, correlation, and anomaly analysis
- attachment/media preview
- read-only handling of originals
- role-based access controls
- complete audit trail
- reproducible analytical reports and exports

This capability is explicitly limited to authorized data access. It does not include credential theft, lock-screen bypass, stealth persistence, spyware deployment, or unauthorized extraction.

## 11. Evidence validation

Evidence-processing validation shall include:

- source hash before processing
- post-copy/ingest integrity verification
- parser success/failure state
- timestamp-normalization checks
- duplicate detection
- provenance links for every derived record
- transformation/version history
- reproducible report inputs

Derived analytics shall never silently alter the source evidence.

## 12. Unified engineering feedback loop

The completed hardware loop is:

**CAD -> CFD/thermal simulation -> constrained optimization -> manufacturing preflight -> manufacture -> physical telemetry -> Digital Twin calibration -> predictive health -> fault isolation -> recovery -> engineering feedback -> next CAD revision**

The completed evidence-data loop is:

**authorized source -> immutable ingest/hash -> parser -> normalized records -> entities/timeline/graph -> analytics -> audited report**

Both loops use the shared provenance, versioning, validation, analytics, and audit infrastructure.
