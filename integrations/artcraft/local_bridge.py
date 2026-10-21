#!/usr/bin/env python3
"""UNG ArtCraft local bridge: loopback only, authenticated, fixed allowlist."""
import hmac
import json
import os
from pathlib import Path
import secrets
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

APPS = ("PhotoCraft", "VectorCraft", "FilmCraft", "LightCraft", "PdfCraft",
        "EffectCraft", "DesignCraft", "FigCraft", "WordCraft", "SoundCraft",
        "DeckCraft", "CADCraft", "GridCraft")
HOST = "127.0.0.1"
PORT = int(os.environ.get("UNG_ARTCRAFT_PORT", "18765"))
TOKEN = os.environ.get("UNG_ARTCRAFT_TOKEN") or secrets.token_urlsafe(32)
HOME = Path.home().resolve()

def app_path(name):
    if name not in APPS:
        return None
    for root in (Path("/Applications"), HOME / "Applications"):
        candidate = root / (name + ".app")
        if candidate.is_dir():
            return candidate
    return None

class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, payload):
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def authorized(self):
        supplied = self.headers.get("Authorization", "")
        return hmac.compare_digest(supplied, "Bearer " + TOKEN)

    def origin_ok(self):
        origin = self.headers.get("Origin")
        return origin is None or origin in (
            "http://127.0.0.1:" + str(PORT),
            "http://localhost:" + str(PORT),
        )

    def do_GET(self):
        if not self.authorized():
            return self.send_json(401, {"error": "Unauthorized"})
        if self.path == "/v1/apps":
            return self.send_json(200, {"apps": [
                {"name": name, "installed": app_path(name) is not None}
                for name in APPS
            ]})
        if self.path == "/health":
            return self.send_json(200, {"ok": True, "service": "ung-artcraft-local"})
        self.send_json(404, {"error": "Not found"})

    def do_POST(self):
        if not self.origin_ok():
            return self.send_json(403, {"error": "Origin not allowed"})
        if not self.authorized():
            return self.send_json(401, {"error": "Unauthorized"})
        if self.path != "/v1/open":
            return self.send_json(404, {"error": "Not found"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > 8192:
                return self.send_json(413, {"error": "Invalid request size"})
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict) or not isinstance(data.get("app"), str):
                return self.send_json(400, {"error": "Expected app name"})
            target = app_path(data["app"])
            if target is None:
                return self.send_json(404, {"error": "App not installed or not allowed"})
            args = ["open", "-a", str(target)]
            if "file" in data:
                if not isinstance(data["file"], str):
                    return self.send_json(400, {"error": "Invalid file"})
                file = Path(data["file"]).expanduser().resolve(strict=True)
                if not file.is_file() or not file.is_relative_to(HOME):
                    return self.send_json(403, {"error": "File must be inside your home directory"})
                args.extend(["--", str(file)])
            subprocess.run(args, check=True, timeout=15)
            self.send_json(200, {"ok": True, "requested": data["app"]})
        except (ValueError, TypeError, OSError, subprocess.SubprocessError) as exc:
            self.send_json(400, {"error": type(exc).__name__})

    def log_message(self, fmt, *args):
        print("%s %s" % (self.address_string(), fmt % args))

if __name__ == "__main__":
    print("UNG ArtCraft bridge listening on http://%s:%s" % (HOST, PORT), flush=True)
    print("Authentication token (keep private): " + TOKEN, flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
