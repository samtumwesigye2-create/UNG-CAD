import ast
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PYTHON_FILES=["main.py","slicer.py","slicer_cnc.py","ung-cad-ad5m-bridge.py"]

def test_recovered_python_parses():
    for name in PYTHON_FILES:
        ast.parse((ROOT/name).read_text(encoding="utf-8"),filename=name)

def test_expected_recovered_files_present():
    for name in PYTHON_FILES+["drafting.html","drafting.js","requirements.txt"]:
        assert (ROOT/name).is_file(), name

def test_main_routes_are_present():
    src=(ROOT/"main.py").read_text(encoding="utf-8")
    for route in ["/health","/api/manufacturing/inspect","/api/manufacturing/slice",
                  "/api/manufacturing/cnc-slice","/api/machines","/api/jobs",
                  "/api/v1/slice/3d","/api/v1/slice/cnc","/api/scenes"]:
        assert route in src

def test_bridge_safety_contract():
    src=(ROOT/"ung-cad-ad5m-bridge.py").read_text(encoding="utf-8")
    assert 'start_print=False' in src
    assert 'print_local_file' in src
    assert 'HOST="127.0.0.1"' in src
