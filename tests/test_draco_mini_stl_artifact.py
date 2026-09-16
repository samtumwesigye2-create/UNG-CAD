from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "test.yml"


def test_ci_publishes_rendered_stls_as_artifact_bundle():
    text = WORKFLOW.read_text()
    assert "actions/upload-artifact@v4" in text
    assert "name: draco-mini-stl" in text
    assert "path: build/draco-mini/*.stl" in text
    assert "if-no-files-found: error" in text
