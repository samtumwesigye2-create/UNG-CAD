# CNC Manufacturing Integration — UNG-CAD

This is an **incremental CNC capability**, not a CloudNC-equivalent automatic machining system.

## Current implementation
- Existing `cad_core/cam_planner.py`: explicit-parameter 2.5D circular contour and rectangular internal contour paths.
- Existing `cad_core/gcode_generator.py`: circular internal contour G-code.
- Existing `cad_core/machine_library.py`: machine and tool capability contracts.
- New `cad_core/cnc_face_assessment.py`: conservative review-first face classification based on explicit geometry metadata.
- New `tests/test_cnc_face_assessment.py`: candidate recognition, cutter-fit, depth and duplicate-ID tests.

## Gatekeeper restrictions
Face assessment never marks an operation approved for execution. Machine profile, stock origin, tool length, fixturing, cutter/workholding clearance, material and speeds/feeds, collision simulation, controller-specific postprocessor, operator approval, and dry run are required before using any output on physical equipment.

## Not yet implemented
- CAD/B-rep face extraction and interactive selection UI
- Automatic feature recognition from arbitrary STEP/IGES/mesh models
- Stock-removal simulation and verified collision avoidance
- CNC machine profiles, tool libraries, and controller-specific postprocessors
- End-to-end validated CAM workflow with operator signoff

Do not treat generated G-code as machine-ready without independent simulation and operator validation.
