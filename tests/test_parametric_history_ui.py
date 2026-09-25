from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
H=(ROOT/"ung-cad-3d"/"viewer.html").read_text()
J=(ROOT/"ung-cad-3d"/"viewer.js").read_text()
def test_parametric_controls():
    for x in ("param-size","param-height","apply-params","feature-timeline","constraint-state"): assert x in H
def test_history_and_regeneration():
    for x in ("featureTimeline","recordFeature","renderTimeline","applyDimensions","Dimension change"): assert x in J
