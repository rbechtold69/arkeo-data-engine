#!/usr/bin/env python3
import json
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
import urllib.error
import urllib.request

ADMIN_DIR = Path(os.environ.get("ADMIN_DIR", "/app/admin")).resolve()
CONFIG_DIR = Path(os.environ.get("CONFIG_DIR", "/app/config")).resolve()
TEST_FILE = CONFIG_DIR / "testing.json"
PORT = int(os.environ.get("ENV_ADMIN_PORT") or os.environ.get("ADMIN_PORT") or 8078)


def load_tests() -> Any:
    if not TEST_FILE.exists():
        return []
    try:
        with TEST_FILE.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:  # pragma: no cover - defensive
        sys.stderr.write(f"Failed to read {TEST_FILE}: {exc}\n")
        return []


def save_tests(data: Any) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = TEST_FILE.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    # Ensure target directory exists before replace (defensive)
    TEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp.replace(TEST_FILE)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ADMIN_DIR), **kwargs)

    def log_message(self, fmt, *args):  # pragma: no cover - quiet logs
        sys.stderr.write("%s - - [%s] %s\n" % (self.client_address[0], self.log_date_time_string(), fmt % args))

    def do_OPTIONS(self):
        if self.path.startswith("/api/tests"):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            return
        if self.path.startswith("/api/proxy"):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST,OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            return
        return super().do_OPTIONS()

    def do_GET(self):
        if self.path.startswith("/api/tests"):
            data = load_tests()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/tests"):
            self.handle_save_tests()
            return
        if self.path.startswith("/api/proxy"):
            self.handle_proxy()
            return
        self.send_error(405, "Method Not Allowed")

    def handle_save_tests(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b"[]"
        try:
            data = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return
        if not isinstance(data, list):
            self.send_error(400, "Payload must be a list")
            return
        save_tests(data)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b"{\"status\":\"ok\"}")

    def handle_proxy(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        target = data.get("target")
        payload = data.get("payload", "")
        method = data.get("method", "POST").upper()
        if not target:
            self.send_error(400, "Missing target")
            return

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        data_bytes = None if method == "GET" else payload.encode("utf-8")

        req = urllib.request.Request(
            target,
            data=data_bytes,
            headers=headers,
            method=method,
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_body = resp.read()
                status = resp.getcode()
                headers = dict(resp.headers)
        except urllib.error.HTTPError as e:
            resp_body = e.read()
            status = e.getcode()
            headers = dict(e.headers)
        except Exception as exc:
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"status": 0, "error": str(exc)}).encode("utf-8"))
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(
            json.dumps(
                {
                    "status": status,
                    "body": resp_body.decode("utf-8", "replace"),
                    "headers": headers,
                }
            ).encode("utf-8")
        )


def main():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("", PORT), Handler)
    sys.stderr.write(f"Serving admin static + API on port {PORT}, admin dir={ADMIN_DIR}, config dir={CONFIG_DIR}\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
