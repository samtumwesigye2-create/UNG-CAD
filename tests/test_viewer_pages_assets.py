from pathlib import Path
H=(Path(__file__).resolve().parents[1]/"ung-cad-3d"/"viewer.html").read_text()
def test_viewer_assets_are_repo_relative_for_github_pages():
    assert 'src="./static/csg-engine.js"' in H
    assert 'src="./static/viewer.js"' in H
    assert 'src="/static/csg-engine.js"' not in H
    assert 'src="/static/viewer.js"' not in H
