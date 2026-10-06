import shutil
import subprocess
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parent.parent

JS_FILES = ["drafting_cnc_section.js", "public/ung-auth.js", "public/preview_viewer.js"]
node = shutil.which("node")


@pytest.mark.skipif(node is None, reason="node not installed")
@pytest.mark.parametrize("name", JS_FILES)
def test_node_check(name):
    subprocess.run([node, "--check", str(APP_DIR / name)], check=True)


@pytest.mark.skipif(node is None, reason="node not installed")
def test_js_smoke():
    out = subprocess.run([node, str(APP_DIR / "tests" / "js_smoke.js")], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "OK" in out.stdout
