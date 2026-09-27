# UNG Shared Heterogeneous Compute & Memory Architecture

Status: approved shared capability. Integrate into existing UNG-CAD / shared analytics and data fabric; do not create a duplicate standalone system.

## Hardware-adaptive execution
- CPU/system-RAM fallback is mandatory.
- Detect available integrated/discrete GPUs and accelerator memory at runtime.
- Support future HBM/HBM3E-class accelerators without making HBM a deployment requirement.
- Select execution target from workload size, precision, device capability, free memory and transfer cost.
- Keep large working sets accelerator-resident where beneficial; minimize host/device copies.
- Asynchronous transfers, prefetching, batching, chunking/tiling, reusable buffers and memory pools.
- VRAM/HBM budgeting, pressure telemetry, deterministic out-of-memory recovery and CPU fallback.
- Profile compute time, transfer time, peak memory, cache/buffer reuse and throughput.

## UNG-CAD / geometry workloads
Accelerate large independent/batched operations where numerically appropriate:
- mesh/voxel processing and adaptive tessellation
- collision/interference and clearance grids
- ray/path and field calculations
- differential geometry: derivatives, normals, first/second fundamental forms, Gaussian/mean curvature
- minimal-surface sampling and curvature maps
- linkage/kinematic sweeps, Jacobians, velocity/acceleration, singular/dead-center detection
- nonlinear/iterated vector maps, orbit histories, convergence/divergence and fixed/periodic-point analysis
- optimization and parameter sweeps
Preserve double-precision/manufacturing tolerances where required; GPU results never bypass manifold, dimensional or manufacturing validation.

## Shared analytics / AI / data fabric
- device-aware arrays/tensors and dataframe-style batches
- automatic placement and migration policy
- streaming/batched scoring and feature extraction
- accelerator-resident sensor-fusion buffers where beneficial
- memory-aware model inference/training utilities
- telemetry-driven scheduling across concurrent UNG workloads

## DRACO integration
Do not put HBM-class hardware in the Pi Zero 2 W DRACO enclosure.
DRACO remains an edge sensor node. Camera/thermal/radar/LiDAR observations may be streamed to a capable UNG backend/node for GPU-resident fusion and analysis. Local operation must remain valid within DRACO hardware limits.

## Electronics / packaging CAD
Add modeling/validation concepts for accelerator + high-bandwidth-memory packages:
- GPU/accelerator and stacked-memory package envelopes
- chiplets/interposers/substrates
- keep-outs, escape/routing regions and package clearances
- thermal maps / heat-flow inputs
- power-delivery regions and estimated power-density metadata
- high-speed interconnect length/geometry constraints
- 3D package visualization
These are design/simulation capabilities; do not claim an FDM printer can manufacture semiconductor packages or HBM stacks.

## Geometry additions from approved math batch
### Analytic cone/cylinder
Exact radius, height, slant length, area/volume, revolution, intersection/tangency and offset utilities.

### Differential/minimal surfaces
General parametric surface frames, normals, metric/fundamental forms, K/H curvature, H≈0 detection, singular/self-intersection diagnostics, parameter/arbitrary paths and curvature overlays.

### Mechanism synthesis
Four-bar/Watt-type and general constrained-linkage solving; crank sweeps; coupler trajectories; velocity/acceleration/Jacobians; singularity/dead-center, collision and clearance detection; optimize link dimensions against target paths.

### Nonlinear dynamical/procedural geometry
User-defined vector maps p[n+1]=f(p[n]); iteration history; fixed/periodic points; convergence/divergence; Jacobian/eigenvalue local stability; constraint/level-set evaluation; orbit-to-curve/surface conversion. Treat social-media example notation as inspiration, not a validated theorem.

## DRACO tilt application
Use mechanism synthesis to evaluate the base-mounted MG90S TILT transmission while simultaneously sweeping PAN -90..+90 degrees and TILT -25..+25 degrees. Reject mechanisms that bind, collide, slip, excessively backlash, contact wiring, pull connectors, stall servos or change commanded tilt as pan moves. Physical P0 validation remains mandatory.
