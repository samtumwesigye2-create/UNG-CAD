# UNG-CAD-3D recovery status

Recovered from the supplied combined-source PDF on branch `recovery/ung-cad-3d`.

## Implemented
- FastAPI + SQLite baseline, STL slicer and CNC/laser toolpath generator.
- AD5M LAN bridge and GRBL-style USB serial bridge.
- 2D drafting interface.
- Project persistence and revision history.
- Materials, queue and audit database schema.
- Expanded job/machine operational state.
- G-code analysis/preview statistics and restricted-command warnings.
- Material consumption helpers and conservative fleet routing.
- Studio, manufacturing dashboard and viewer recovery shell.
- Structural/feature tests and GitHub Actions validation.

## Deliberate limits
The recovery PDF did not include the original Studio, Viewer, or Manufacturing HTML source, so those three files are new recovery shells rather than claimed original source. The recovered STL slicer remains a simple perimeter/cross-section slicer; it is not a production replacement for a mature slicing engine. Physical AD5M acceptance requires the printer and local bridge on the same LAN and therefore cannot be certified by repository-only tests.
