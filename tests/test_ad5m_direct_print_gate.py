from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "ung-cad-3d" / "ung-cad-ad5m-bridge.py"


def test_direct_print_requires_production_release():
    text = BRIDGE.read_text(encoding="utf-8")
    assert "def verify_released_machine_bytes" in text
    assert '"/api/manufacturing/readiness/machine-file/"' in text
    direct = text.split('if self.path=="/print":', 1)[1].split('return self.out({"error":"not found"},404)', 1)[0]
    assert "verify_released_machine_bytes(safe_name,raw)" in direct
    assert "return self.out({\"error\":str(gate_error)},423)" in direct
    assert direct.index("verify_released_machine_bytes(safe_name,raw)") < direct.index("print_file(")


def test_cloud_queue_uses_same_machine_byte_verifier():
    text = BRIDGE.read_text(encoding="utf-8")
    worker = text.split("def cloud_worker():", 1)[1].split("class H(BaseHTTPRequestHandler):", 1)[0]
    assert 'verify_released_machine_bytes(j["machine_file"],Path(path).read_bytes())' in worker
    assert worker.index("verify_released_machine_bytes") < worker.index("print_file(")
