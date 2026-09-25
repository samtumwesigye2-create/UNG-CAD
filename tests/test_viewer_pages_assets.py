from pathlib import Path
H=(Path(__file__).resolve().parents[1]/"ung-cad-3d"/"viewer.html").read_text()

def test_viewer_assets_exist_at_referenced_repo_relative_paths():
    assert 'src="./csg-engine.js"' in H
    assert 'src="./viewer.js"' in H
    assert 'src="./ung-geometry-integration.js"' in H
    root=Path(__file__).resolve().parents[1]/"ung-cad-3d"
    assert (root/"csg-engine.js").is_file()
    assert (root/"viewer.js").is_file()
    assert (root/"ung-geometry-integration.js").is_file()
