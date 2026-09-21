# UNG-CAD-3D source recovery

This directory is being recovered from the supplied `ung-cad-combined-for-chatgpt.pdf` combined-source snapshot.

## Verified baseline

- FastAPI + SQLite application named `UNG-CAD-3D`, version `1.3.0`.
- 3D STL slicing plus CNC/laser G-code generation.
- Local bridge required for FlashForge Adventurer 5M and USB serial CNC/laser controllers.
- Existing logical files in the snapshot include `main.py`, `slicer.py`, `slicer_cnc.py`, `ung-cad-ad5m-bridge.py`, `start-ad5m-bridge.bat`, `start-ad5m-bridge.command`, `drafting.html`, `drafting.js`, and `requirements.txt`.

## Recovery rule

Do not overwrite the existing DRACO Mini project. Recovered application files live under `ung-cad-3d/` until validated. The PDF text extraction interleaves some page-boundary content, so executable files are only committed after their boundaries and syntax are reconstructed and checked; ambiguous extracted text is not silently treated as authoritative source.
