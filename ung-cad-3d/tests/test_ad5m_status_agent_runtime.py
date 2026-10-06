"""Small runtime checks for the AD5M status agent wrapper."""
import importlib.util
from types import SimpleNamespace

from conftest import APP_DIR


def load_agent():
    spec = importlib.util.spec_from_file_location("ung_ad5m_agent_runtime", APP_DIR / "ung-cad-ad5m-agent.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_probe_ready_updates_last_contact(monkeypatch):
    agent = load_agent()

    class Bridge:
        STATE = {"printer": None, "check_code": "1234"}
        CHECK_CODE = "1234"
        BRIDGE_VERSION = "v-test"

        @staticmethod
        async def connect(code):
            assert code == "1234"
            Bridge.STATE["printer"] = {"serial": "SN123"}
            return Bridge.STATE["printer"]

    monkeypatch.setattr(agent.time, "time", lambda: 123.5)
    payload, last_contact = agent.probe_once(Bridge, None)
    assert payload["state"] == "READY"
    assert payload["last_printer_contact"] == 123.5
    assert payload["error"] is None
    assert last_contact == 123.5


def test_probe_does_not_start_print_on_failure():
    agent = load_agent()
    calls = []

    class Bridge:
        STATE = {"printer": None, "check_code": "1234"}
        CHECK_CODE = "1234"
        BRIDGE_VERSION = "v-test"

        @staticmethod
        async def connect(code):
            calls.append(("connect", code))
            raise RuntimeError("No FlashForge printer discovered on this LAN")

        @staticmethod
        async def print_file(*args, **kwargs):
            calls.append(("print", args, kwargs))

    payload, _ = agent.probe_once(Bridge, None)
    assert payload["state"] == "PRINTER_UNREACHABLE"
    assert calls == [("connect", "1234")]
