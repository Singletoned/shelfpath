from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MESSAGES: list[dict] = []


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/health":
            self._respond(HTTPStatus.OK, {"status": "ok"})
            return
        if self.path == "/messages":
            self._respond(HTTPStatus.OK, {"messages": MESSAGES})
            return
        self._respond(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/emails":
            self._respond(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        size = int(self.headers.get("Content-Length", "0"))
        MESSAGES.append(json.loads(self.rfile.read(size)))
        self._respond(HTTPStatus.OK, {"id": f"test-{len(MESSAGES)}"})

    def log_message(self, format: str, *args) -> None:
        return

    def _respond(self, status: HTTPStatus, body: dict) -> None:
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
