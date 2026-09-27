# UNG-CAD Industrial Capability Architecture

Status: approved architecture and implementation roadmap. This document defines capability contracts; it does **not** claim unfinished kernels are production-ready.

## Core capabilities to implement

1. **Exact B-Rep geometry kernel**
   - analytic curves/surfaces, NURBS, topology graph, tolerances
   - exact/robust Boolean union, subtract, intersect
   - sewing, healing, defeaturing, manifold validation, persistent topology naming
2. **Complete sketch constraint solver**
   - dimensional + geometric constraints, DOF accounting, under/fully/over-constrained diagnostics
   - stable solve under edits, driven/reference dimensions, construction geometry
3. **Native STEP / IGES interoperability**
   - STEP AP203/AP214/AP242 import/export architecture, IGES import/export
   - units, assemblies, names/colors/layers and validation round-trips
4. **FEA / multiphysics solver**
   - meshing, materials, loads/BCs, linear static, modal, buckling, thermal and thermo-mechanical
   - convergence/error checks and result visualization; nonlinear/contact as later production tier
5. **Topology + generative optimization**
   - design/non-design regions, loads/constraints, manufacturing constraints, objective/constraint optimization
   - reconstruction of optimized results into manufacturable CAD
6. **Industrial assembly + collision solver**
   - mates/joints, kinematics, interference, clearance/contact, swept-volume collision, motion studies
7. **True 5-axis CAM kernel**
   - 3+2 and simultaneous 5-axis paths, tool orientation, stock/rest machining, gouge/collision avoidance
   - machine kinematics, feeds/speeds, post-processing and machine simulation
8. **Collision-aware nonplanar slicer**
   - nozzle/toolhead envelope, printed-part collision checks, continuous/nonplanar layers
   - overhang/accessibility, extrusion/path planning, machine/material constraints

## Additional missing industrial capabilities

9. **Production parametric feature kernel** — extrude/revolve/sweep/loft, fillet/chamfer/shell/draft, patterns, robust parent/child regeneration.
10. **Surface/Class-A modeling** — NURBS editing, trim/extend, blends, curvature combs, zebra/reflection and G0/G1/G2/G3 analysis.
11. **Sheet-metal system** — bends, bend allowance/K-factor, hems, flanges, reliefs, flat-pattern generation and DXF.
12. **Weldments/frames/routing** — structural members, cut lists, pipe/tube/hose/cable routing and bend-radius rules.
13. **PMI, GD&T and drawings** — associative drawing views, sections/details, dimensions, tolerances, datums, symbols, BOM/balloons and model-based definition.
14. **Tolerance stack-up + variation analysis** — worst-case/statistical stacks, fit classes, assembly variation and inspection requirements.
15. **Advanced meshing** — surface/volume tetra/hex strategies, adaptive refinement, mesh quality and convergence control.
16. **CFD + thermal/field simulation architecture** — flow, conjugate heat transfer and links to existing electrical/electromagnetic engineering.
17. **Mechanism/dynamics** — rigid-body motion, motors/actuators, forces, contacts and time-history results.
18. **Manufacturing DFM/DFA** — additive, CNC, molding, sheet-metal and assembly rule engines with explainable violations.
19. **Metrology/inspection** — measurement plans, datum alignment, deviation maps, CMM/scan comparison and tolerance verification.
20. **Reverse engineering** — point clouds/meshes to surfaces/features, segmentation, fitting and deviation analysis.
21. **Lattice/implicit geometry** — TPMS/lattices, field-driven structures and scalable implicit evaluation for additive manufacturing.
22. **Advanced additive manufacturing** — supports, orientation/nesting, infill/process regions, multi-material, thermal/distortion-aware planning.
23. **CAM beyond milling** — turning, mill-turn, drilling, probing, laser/waterjet/plasma and EDM architecture.
24. **Machine/digital twin** — axis limits, fixtures, workholding, stock, tool library, machine collision simulation and verified posts.
25. **Materials engineering database** — versioned physical, mechanical, thermal, electrical and manufacturing properties with provenance.
26. **PDM/PLM + configuration management** — parts/assemblies/BOMs, revisions, variants/configurations, release states and change control.
27. **CAD-aware version control** — semantic feature diffs, branching/merging, conflict visualization, provenance and reproducible history.
28. **Extensible API/plugin/automation system** — stable object model, scripting, events, batch/headless execution and custom workbenches.
29. **Interoperability expansion** — Parasolid/ACIS adapter contracts where licensed, JT, 3MF, glTF, DXF/DWG adapters and mesh formats.
30. **Engineering requirements + traceability** — requirement-to-feature/test/manufacturing evidence links and release traceability.
31. **Uncertainty and numerical robustness framework** — unit-safe computation, tolerances, conditioning, deterministic predicates and error propagation.
32. **Performance architecture** — large assemblies, LOD, spatial acceleration, multithreading/GPU jobs, incremental recompute and out-of-core data.
33. **Collaboration/security** — permissions, review/markup, audit trail, signed release artifacts and reproducible manufacturing packages.
34. **AI-assisted CAD with deterministic authority** — intent-to-feature suggestions, repair/DFM assistance and optimization guidance; AI output never bypasses geometry/manufacturing release gates.


35. **Validated CFD + thermal simulation core** — incompressible flow, Couette/Poiseuille analytical benchmarks, pressure/velocity/temperature fields, fan/vent boundary conditions, convergence/conservation gates, mesh refinement, and solver provenance.
36. **Closed-loop thermal/airflow optimization** — vary approved vents, ducts, fan placement and spacing while locking frozen interfaces, sensor seats, FOVs, mounting datums and manufacturing constraints; reject invalid or non-manufacturable candidates.
37. **Digital Twin + predictive health** — bind CAD/simulation revisions to telemetry, compare predicted/measured behavior, calibrate versioned model parameters, detect fan/vent/thermal/servo/sensor faults, and retain fault evidence.
38. **Automated recovery + degraded operation** — integrate health detections with throttling, fan-control changes, sensor isolation, service restart, safe degraded modes, escalation, retry limits and recovery audit history.
39. **Authorized evidence/device-data analysis** — immutable ingest, cryptographic hashes, provenance/chain-of-custody, normalized communications/media/device/event records, entity/timeline/graph analysis, deduplication, auditing and reproducible reporting; no credential theft, lock bypass, spyware or unauthorized extraction.

Detailed implementation contract: [Shared Physics, Digital Twin, Predictive Health, and Evidence Architecture](./SHARED_PHYSICS_DIGITAL_TWIN_AND_EVIDENCE_ARCHITECTURE.md).


40. **Manufacturing capability classification** — every design/preflight shall classify the requested artifact against the selected machine/process before claiming it can be manufactured:
   - **AD5M PRINTABLE (Level 1):** geometry that the configured FlashForge Adventurer 5M can directly manufacture as thermoplastic FDM parts, subject to build envelope, nozzle/feature size, material, overhang/bridge, tolerance and layer-strength constraints.
   - **HYBRID BUILD (Level 2):** a functional assembly whose printable mechanical parts can be made on the AD5M but which requires purchased or separately fabricated electronics, motors, bearings, fasteners, wiring, connectors, sensors, batteries, metal parts or other non-FDM components.
   - **EXTERNAL FABRICATION REQUIRED (Level 3):** required functional features cannot be produced by the configured FDM process, including conventional PCB copper traces, semiconductor devices, batteries, motors, precision metal conductors and other processes/materials outside the machine profile.

The classification is a manufacturing truth gate, not a design suggestion. UNG-CAD must not report a complete device as directly printable merely because its enclosure or carrier is printable. The preflight result shall identify which parts are printable, which are purchased/assembled, and which require an external process.

## Implementation order

The dependency order is:

**numerical robustness → exact geometry/topology → sketch constraints → parametric features → exchange → assemblies → drawings/GD&T → validated CFD/thermal simulation → constrained optimization → CAM/slicing → manufacturing release gate → machine/digital twin → predictive health/recovery → inspection → PDM/collaboration/AI**

Each production capability must ship with deterministic tests, benchmark geometry, failure-state reporting, provenance and release-gate evidence. Placeholder contracts and approximate mesh operations must never be presented as exact production results.
