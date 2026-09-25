# Simple Bicopter V2 — Mesh Gate

The arm topology repair is committed. The authoritative production gate is `validate_meshes.py`.

A revision is releasable only when OpenSCAD successfully exports **body.stl**, **arm.stl**, and **guard.stl** with:
- zero OpenSCAD/CGAL warnings or errors,
- non-empty STL output for every part,
- no skipped component.

Do not label the current revision print-ready until this validator has actually executed successfully on a worker with OpenSCAD.
