# UNG-CAD Field Analysis Core

The shared field-analysis module is implemented in `ung_vector_calculus.py`.

Capabilities:
- scalar/vector fields and dot/cross products
- gradient and directional derivative
- Jacobian, Hessian, divergence and curl
- numerical integration and line integrals
- triangle-mesh flux and surface normals
- divergence-theorem numerical validation
- Lorentz force and torque
- RK4 trajectory integration and streamlines
- second derivatives, concavity support and inflection candidates

Integration targets:
- UNG-CAD/Manufacturing: surface normals, curvature/concavity analysis,
  field overlays, mesh diagnostics, thermal/airflow/force visualization.
- DRACO/shared analytics: spatial sensor-field interpolation and visualization.

Visualization clients should consume these primitives to render vector arrows,
streamlines, scalar heatmaps, slices, surface normals and trajectories.
