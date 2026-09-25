# Print-Ready Export Gate

The Modular V2 source is finalized, but STL files are only considered print-ready after geometry compilation.

Run `python export_parts.py` on the UNG-CAD manufacturing worker with OpenSCAD installed. It exports:
- `exports/center_plate.stl`
- `exports/arm.stl`
- `exports/guard.stl`

The exporter fails on OpenSCAD warnings/errors rather than silently shipping questionable geometry.

After export, inspect the three meshes in UNG-CAD/OrcaSlicer before printing. Print one center plate and one arm for the first physical fit check; duplicate the arm only after that interface is confirmed.
