from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
H=(ROOT/"ung-cad-3d"/"viewer.html").read_text()
J=(ROOT/"ung-cad-3d"/"viewer.js").read_text()
def test_horn_controls_and_generator():
    for x in ("horn-x","horn-radial","horn-length","horn-min-feature","horn-create","horn-analysis"): assert x in H
    for x in ("generateGabrielHorn","Surface of Revolution","volume converges","area diverges"): assert x in J
