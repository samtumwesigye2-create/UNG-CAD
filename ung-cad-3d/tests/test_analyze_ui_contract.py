from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_analyze_ui_contract():
    html=(ROOT/"manufacturing.html").read_text(encoding="utf-8")
    preview=(ROOT/"manufacturing-preview.js").read_text(encoding="utf-8")
    engine=(ROOT/"analyze-engine.js").read_text(encoding="utf-8")
    assert "Build 2026-09-28.1" in html
    assert "analyze-engine.js" in html
    for label in ["Measure","Print estimate","Rotate & scale","Support check","Best position","Frames & assembly","Stress check"]:
        assert label in html
    for control in ["measureToggle","estimateAll","exactTurn","resizePart","checkSupports","bestPos","showAssembly","checkClashes","checkGeometryClashes","checkClearance","fitReport","downloadFitCsv","saveVersion","undoChanges","stRun","explodeRange"]:
        assert f'id="{control}"' in html
    for hook in ["__previewSTL","__analyzeApplyMatrix","__analyzeSupport","__analyzeBestPosition","__showAssembly","__checkAssemblyClashes","__checkAssemblyGeometryClashes","__checkAssemblyClearance","__assemblyFitReport","__analyzeMarkSection","__explodeAssembly"]:
        assert hook in preview
    for api in ["measure","printEstimate","rotationX","rotationY","rotationZ","scaling","mirror","findOverhangs","autoOrient","worldMatrix","trianglesIntersect","pairwiseGeometryClashes","pairwiseClearances","pairwiseDistances","toBinarySTL"]:
        assert api in engine

def test_recovered_manufacturing_routes_stay_present():
    main=(ROOT/"main.py").read_text(encoding="utf-8")
    for route in [
        "/api/manufacturing/cnc-slice",
        "/api/machines",
        "/api/jobs",
        "/api/v1/slice/3d",
        "/api/v1/slice/cnc",
    ]:
        assert route in main


def test_analyze_panel_is_wired():
    html=(ROOT/"manufacturing.html").read_text(encoding="utf-8")
    panel=(ROOT/"analyze-panel.js").read_text(encoding="utf-8")
    assert "strength-engine.js" in html and "analyze-panel.js" in html
    for control in ["measureToggle","estimateAll","exactTurn","resizePart","checkSupports","bestPos","stRun","showAssembly","explodeRange","checkGeometryClashes","checkClearance","fitReport","saveVersion","undoChanges"]:
        assert f"'{control}'" in panel, control

def test_preview_module_has_no_literal_backslash_n():
    preview=(ROOT/"manufacturing-preview.js").read_text(encoding="utf-8")
    assert ";\\nwindow." not in preview
