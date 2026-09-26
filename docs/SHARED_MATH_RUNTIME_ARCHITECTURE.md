# UNG Shared Math, Geometry, Boot, and Runtime Architecture

Status: approved shared architecture roadmap.

This document extends the existing UNG shared engines. It does not create duplicate standalone systems.

## Numerical and geometry core

The shared numerical/geometry layer shall expose:

- Bisection and Newton root solving.
- Gradients, Jacobians, Hessians, and second-order multivariable optimization.
- Constrained optimization with explicit geometry and manufacturing constraints.
- Curvature and trajectory mathematics.
- Spatial and field visualization.
- Ray/path tracing and optical focal/FOV analysis.
- Kinematics and dynamics.
- Volumetric decomposition and spatial partitioning.
- Mass-property calculations.
- Collision, clearance, and interference optimization.

Applicable consumers include UNG-CAD, Manufacturing, DRACO, LINK256, and other UNG systems that require these capabilities.

## Boot and preflight manager

The shared lifecycle layer shall provide:

- Hardware self-test / POST-style checks appropriate to the target platform.
- Dependency-aware service startup.
- Integrity verification before dependent services are released.
- Startup telemetry and boot-history diagnostics.
- Recovery and rollback paths for known-good configurations.
- UEFI/GPT inspection and tooling where applicable.
- Legacy MBR inspection for compatibility and diagnostic workflows.

Platform-specific implementations must use the platform's real boot architecture. Raspberry Pi systems, for example, must use the Raspberry Pi firmware/boot flow rather than emulating a PC BIOS.

## Runtime Health & Recovery Engine

After preflight, the runtime manager shall continuously track registered hardware and services through explicit lifecycle states:

`INIT -> SELF_TEST -> READY -> DEGRADED -> FAILED -> RECOVERY`

The shared engine shall provide:

- Hardware and service heartbeats.
- Watchdogs with bounded restart/reconnection policies.
- Dependency-aware fault isolation.
- Degraded-mode operation so unaffected services can remain available.
- Automatic recovery where policy permits.
- Structured event logging.
- Runtime health, startup history, and recovery telemetry for dashboards.

## UNG-CAD and Manufacturing integration

The intended engineering pipeline is:

`real component dimensions -> parametric geometry -> constraints -> collision/clearance analysis -> sensor FOV/ray analysis -> mechanism simulation -> numerical optimization -> geometry validation -> manufacturing preflight -> slicing -> printer preflight -> print -> runtime monitoring`

Manufacturing preflight should distinguish failures such as file-load failure, empty/no-renderable geometry, non-manifold geometry, invalid dimensions, slicer/profile mismatch, bridge/printer unavailability, and printer-not-ready state.

## Integration principles

1. Shared engines are authoritative; consumers call them rather than reimplementing equivalent logic.
2. Hardware dimensions and interfaces come from verified component data, not guessed envelopes.
3. Numerical optimization may adjust only explicitly permitted parameters and must preserve hard constraints.
4. Preflight failures are explicit and actionable; they must not silently fall through to manufacturing.
5. Recovery actions are bounded, logged, and dependency-aware.
6. Boot/runtime support is capability-driven so desktop, server, Raspberry Pi, and printer-connected deployments can use appropriate platform adapters.
7. Existing UNG analytics, CAD, manufacturing, DRACO, and LINK256 architecture is extended rather than replaced.

## Planned implementation boundaries

- `ung_geometry` / `cad_core`: numerical solvers, geometry derivatives, optimization, collision/clearance, ray/FOV, mass properties.
- `ung_shared` / `shared`: lifecycle state model, health events, dependency graph, watchdog/recovery interfaces.
- Manufacturing/bridge: file, slicer, profile, bridge, printer, and job preflight adapters.
- Project integrations: DRACO and LINK256 hardware-specific health/preflight adapters.

Implementation work should add tests for solver convergence/failure, constraint enforcement, lifecycle transitions, dependency failures, recovery limits, geometry-empty detection, and manufacturing preflight outcomes.
