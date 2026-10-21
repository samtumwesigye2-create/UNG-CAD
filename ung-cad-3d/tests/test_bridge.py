import http.client
import importlib.util
import json
import threading
import time
from types import SimpleNamespace

import pytest

from conftest import APP_DIR

ALLOWED = "https://ung-cad.example.app"
TOKEN = "test-bridge-token"


@pytest.fixture(scope="module")
def bridge():
    mp = pytest.MonkeyPatch()
    mp.setenv("UNG_CAD_ALLOWED_ORIGINS", f"{ALLOWED},http://localhost,http://127.0.0.1")
    mp.setenv("UNG_CAD_BRIDGE_TOKEN", TOKEN)
    spec = importlib.util.spec_from_file_location("ung_bridge", APP_DIR / "ung-cad-ad5m-bridge.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OPEN_SETTLE_SECONDS = 0.0
    server = module.make_server("127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    module.TEST_PORT = server.server_address[1]
    yield module
    server.shutdown()
    mp.undo()


def request(bridge, method, path, body=None, headers=None, token=True, origin=ALLOWED):
    conn = http.client.HTTPConnection("127.0.0.1", bridge.TEST_PORT, timeout=10)
    hdrs = dict(headers or {})
    if token:
        hdrs["X-UNG-Bridge-Token"] = TOKEN
    if origin:
        hdrs["Origin"] = origin
    conn.request(method, path, body=body, headers=hdrs)
    resp = conn.getresponse()
    raw = resp.read()
    conn.close()
    try:
        data = json.loads(raw) if raw else None
    except ValueError:
        data = raw
    return resp.status, dict(resp.getheaders()), data


class FakeSerial:
    """Fake GRBL: answers 'ok' (or nothing / an error) to every line."""

    def __init__(self, mode="ok", delay=0.0, error_at=None):
        self.mode = mode
        self.delay = delay
        self.error_at = error_at
        self.written = []
        self.pending = []
        self.lines_seen = 0
        self.closed = False
        self.lock = threading.Lock()

    def write(self, data):
        with self.lock:
            self.written.append(data)
            if data.endswith(b"\n"):
                self.lines_seen += 1
                if self.mode == "ok":
                    if self.error_at is not None and self.lines_seen == self.error_at:
                        self.pending.append(b"error:20\r\n")
                    else:
                        self.pending.append(b"ok\r\n")

    def readline(self):
        time.sleep(self.delay or 0.005)
        with self.lock:
            if self.pending:
                return self.pending.pop(0)
        return b""

    def reset_input_buffer(self):
        pass

    def close(self):
        self.closed = True


def wait_job(bridge, until=lambda j: not j["active"], timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        _, _, data = request(bridge, "GET", "/serial/status")
        if data["job"] and until(data["job"]):
            return data["job"]
        time.sleep(0.05)
    raise AssertionError("job did not reach the expected state")


def gcode(n):
    return "\n".join(["G21", "G90"] + [f"G1 X{i} Y0 F800" for i in range(n)] + ["M5"])


# ---------- auth / CORS ----------

def test_health_is_open_and_has_no_secrets(bridge):
    bridge.STATE["printer"] = {"name": "AD5M", "ip": "192.168.1.50", "serial": "SN123", "firmware": "1.0",
                               "http_port": 8898, "tcp_port": 8899}
    bridge.STATE["check_code"] = "abcd"
    status, headers, data = request(bridge, "GET", "/health", token=False)
    assert status == 200
    assert data["version"] == "2026-09-20-3" and data["token_required"] is True
    text = json.dumps(data)
    assert "SN123" not in text and "192.168.1.50" not in text and "abcd" not in text and TOKEN not in text
    assert headers["Access-Control-Allow-Origin"] == ALLOWED


def test_missing_or_wrong_token_rejected(bridge):
    for method, path in (("GET", "/discover"), ("GET", "/serial/ports"), ("GET", "/serial/status"),
                         ("POST", "/serial/send"), ("POST", "/serial/stop"), ("POST", "/print"), ("POST", "/pair")):
        status, _, data = request(bridge, method, path, body=b"", token=False)
        assert status == 401, path
        assert data["token_required"] is True
    status, _, _ = request(bridge, "GET", "/discover", headers={"X-UNG-Bridge-Token": "wrong"}, token=False)
    assert status == 401


def test_disallowed_origin_rejected(bridge):
    status, headers, _ = request(bridge, "GET", "/health", token=False, origin="https://evil.example")
    assert status == 403
    assert "Access-Control-Allow-Origin" not in headers
    status, headers, _ = request(bridge, "POST", "/serial/send", body=b"G0 X1", origin="https://evil.example",
                                 headers={"X-Port": "COM3"})
    assert status == 403
    # lookalike hosts are not allowed either
    assert request(bridge, "GET", "/health", token=False, origin="https://ung-cad.example.app.evil.com")[0] == 403
    # localhost on any port is allowed
    status, headers, _ = request(bridge, "GET", "/health", token=False, origin="http://localhost:8000")
    assert status == 200 and headers["Access-Control-Allow-Origin"] == "http://localhost:8000"


def test_preflight_private_network_access(bridge):
    pna = {"Access-Control-Request-Method": "POST", "Access-Control-Request-Private-Network": "true",
           "Access-Control-Request-Headers": "x-ung-bridge-token"}
    status, headers, _ = request(bridge, "OPTIONS", "/serial/send", headers=pna, token=False)
    assert status == 204
    assert headers["Access-Control-Allow-Private-Network"] == "true"
    assert headers["Access-Control-Allow-Origin"] == ALLOWED
    assert "X-UNG-Bridge-Token" in headers["Access-Control-Allow-Headers"]
    status, headers, _ = request(bridge, "OPTIONS", "/serial/send", headers=pna, token=False, origin="https://evil.example")
    assert status == 403
    assert "Access-Control-Allow-Private-Network" not in headers


def test_bad_host_header_rejected(bridge):
    status, _, _ = request(bridge, "GET", "/health", token=False, headers={"Host": "attacker.example:8765"})
    assert status == 403


# ---------- serial streaming ----------

def test_serial_job_completes_in_background(bridge, monkeypatch):
    fake = FakeSerial()
    monkeypatch.setattr(bridge, "open_serial", lambda port, baud: fake)
    status, _, data = request(bridge, "POST", "/serial/send", body=gcode(20).encode(),
                              headers={"X-Port": "COM3", "X-Baud": "115200"})
    assert status == 202 and data["job_id"] and data["total_lines"] == 23
    job = wait_job(bridge)
    assert job["state"] == "completed" and job["sent_lines"] == 23 and job["progress"] == 1.0
    assert fake.written[-1] == b"G4 P0\n"    # waited for motion to finish
    assert fake.closed


def test_timeout_aborts_instead_of_continuing(bridge, monkeypatch):
    fake = FakeSerial(mode="silent")
    monkeypatch.setattr(bridge, "open_serial", lambda port, baud: fake)
    status, _, _ = request(bridge, "POST", "/serial/send", body=gcode(5).encode(),
                           headers={"X-Port": "COM3", "X-Line-Timeout": "1"})
    assert status == 202
    job = wait_job(bridge)
    assert job["state"] == "error"
    assert "No 'ok'" in job["error"] and "line 1" in job["error"]
    assert job["sent_lines"] == 0
    line_writes = [w for w in fake.written if w.endswith(b"\n") and w not in (b"M5\n",)]
    assert line_writes == [b"G21\n"]           # never sent line 2
    assert b"!" in fake.written and b"\x18" in fake.written and b"M5\n" in fake.written


def test_controller_error_aborts(bridge, monkeypatch):
    fake = FakeSerial(error_at=3)
    monkeypatch.setattr(bridge, "open_serial", lambda port, baud: fake)
    request(bridge, "POST", "/serial/send", body=gcode(10).encode(), headers={"X-Port": "COM3"})
    job = wait_job(bridge)
    assert job["state"] == "error" and "error:20" in job["error"] and job["sent_lines"] == 2


def test_stop_feed_hold_reset_and_m5(bridge, monkeypatch):
    fake = FakeSerial(delay=0.02)
    monkeypatch.setattr(bridge, "open_serial", lambda port, baud: fake)
    status, _, _ = request(bridge, "POST", "/serial/send", body=gcode(500).encode(),
                           headers={"X-Port": "COM3", "X-Machine-Mode": "laser"})
    assert status == 202
    wait_job(bridge, until=lambda j: j["sent_lines"] >= 5)
    # only one job at a time
    busy, _, data = request(bridge, "POST", "/serial/send", body=b"G0 X1", headers={"X-Port": "COM3"})
    assert busy == 409
    status, _, data = request(bridge, "POST", "/serial/stop")
    assert status == 200 and data["stopped"] is True
    job = wait_job(bridge)
    assert job["state"] == "stopped" and job["sent_lines"] < job["total_lines"]
    i_hold = fake.written.index(b"!")
    assert fake.written[i_hold + 1] == b"\x18" and fake.written[i_hold + 2] == b"M5\n"
    sent_after = [w for w in fake.written[i_hold + 3:] if w.startswith(b"G1")]
    assert sent_after == []


def test_stop_without_active_job_opens_port(bridge, monkeypatch):
    fake = FakeSerial()
    monkeypatch.setattr(bridge, "open_serial", lambda port, baud: fake)
    bridge.JOBS["current"] = None
    status, _, data = request(bridge, "POST", "/serial/stop", headers={"X-Port": "COM7"})
    assert status == 200 and data["stopped"] is True and data["port"] == "COM7"
    assert fake.written == [b"!", b"\x18", b"M5\n"] and fake.closed
    status, _, data = request(bridge, "POST", "/serial/stop")
    assert data["stopped"] is False


# ---------- AD5M printing ----------

class FakeJobControl:
    def __init__(self, calls):
        self.calls = calls

    async def upload_file(self, path, start_print=False, level_before_print=True):
        self.calls.append(("upload_file", path.split("/")[-1].split("\\")[-1], start_print, level_before_print))
        return True

    async def print_local_file(self, name, leveling_before_print=True):
        self.calls.append(("print_local_file", name, leveling_before_print))
        return True


def fake_flashforge(calls):
    printer = SimpleNamespace(name="AD5M", ip_address="192.168.1.50", serial_number="SN123",
                              event_port=8898, command_port=8899)

    class Client:
        def __init__(self, ip, serial, code, options=None):
            calls.append(("client", ip, serial, code))
            self.printer_name = "AD5M"
            self.firmware_version = "3.1.3"
            self.job_control = FakeJobControl(calls)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def get_printer_status(self):
            return {"status": "ready"}

        async def init_control(self):
            calls.append(("init_control",))
            return True

    class Options:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class Discovery:
        async def discover(self):
            return [printer]

    return lambda: (Client, Options, Discovery)


def test_print_requires_explicit_confirm(bridge, monkeypatch):
    calls = []
    monkeypatch.setattr(bridge, "_flashforge", fake_flashforge(calls))
    status, _, data = request(bridge, "POST", "/pair", body=json.dumps({"printer_id": "abcd"}).encode())
    assert status == 200 and data["printer"]["serial"] == "SN123"
    calls.clear()
    status, _, data = request(bridge, "POST", "/print", body=b"G28\n", headers={"X-Filename": "part.gcode"})
    assert status == 200
    assert data["started"] is False and data["uploaded"] is True
    assert ("upload_file", "part.gcode", False, True) in calls
    assert not any(c[0] == "print_local_file" for c in calls)
    calls.clear()
    status, _, data = request(bridge, "POST", "/print", body=b"G28\n",
                              headers={"X-Filename": "part.gcode", "X-Confirm-Start": "true"})
    assert status == 423
    assert not any(c[0] == "print_local_file" for c in calls)
    monkeypatch.setattr(bridge, "verify_released_machine_bytes",
                        lambda name, raw: {"machine_file_sha256": "test-approved"})
    status, _, data = request(bridge, "POST", "/print", body=b"G28\n",
                              headers={"X-Filename": "part.gcode", "X-Confirm-Start": "true"})
    assert status == 200 and data["started"] is True
    assert ("print_local_file", "part.gcode", True) in calls
    # wrong file type still refused
    status, _, _ = request(bridge, "POST", "/print", body=b"solid", headers={"X-Filename": "part.stl"})
    assert status == 400


def test_origin_matcher_unit(bridge):
    allowed = ["https://a.example", "http://localhost", "http://127.0.0.1:5500"]
    assert bridge.origin_allowed("https://a.example", allowed)
    assert not bridge.origin_allowed("http://a.example", allowed)
    assert bridge.origin_allowed("http://localhost:3000", allowed)
    assert bridge.origin_allowed("http://127.0.0.1:5500", allowed)
    assert not bridge.origin_allowed("http://127.0.0.1:8000", allowed)
    assert not bridge.origin_allowed("null", allowed)
    assert not bridge.origin_allowed("", allowed)
