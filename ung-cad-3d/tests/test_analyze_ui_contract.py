from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_analyze_ui_contract():
    html=(ROOT/"manufacturing.html").read_text(encoding="utf-8")
    preview=(ROOT/"manufacturing-preview.js").read_text(encoding="utf-8")
    engine=(ROOT/"analyze-engine.js").read_text(encoding="utf-8")
    assert "Build 2026-09-23.3" in html
    assert "/static/analyze-engine.js" in html
    for label in ["Measure","Print estimate","Rotate & scale","Support check","Best position","Frames & assembly"]:
        assert label in html
    for control in ["measureToggle","estimateAll","exactTurn","resizePart","checkSupports","bestPos","showAssembly","checkClashes","checkGeometryClashes","checkClearance","saveVersion","undoChanges"]:
        assert f'id="{control}"' in html
    for hook in ["__previewSTL","__analyzeApplyMatrix","__analyzeSupport","__analyzeBestPosition","__showAssembly","__checkAssemblyClashes","__checkAssemblyGeometryClashes","__checkAssemblyClearance"]:
        assert hook in preview
    for api in ["measure","printEstimate","rotationX","rotationY","rotationZ","scaling","mirror","findOverhangs","autoOrient","worldMatrix","trianglesIntersect","pairwiseGeometryClashes","pairwiseClearances","toBinarySTL"]:
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
