"""Minimal ASGI test helper that avoids external client dependencies."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from urllib.parse import urlencode


@dataclass
class ASGIResponse:
    """Minimal HTTP response wrapper for ASGI test calls."""

    status_code: int
    body: bytes
    headers: dict[str, str]

    @property
    def text(self) -> str:
        return self.body.decode("utf-8")

    def json(self) -> object:
        return json.loads(self.text)


def request(app: object, path: str, params: dict[str, object] | None = None, method: str = "GET") -> ASGIResponse:
    """Execute one ASGI HTTP request against an app."""
    query_string = urlencode({key: value for key, value in (params or {}).items() if value is not None}, doseq=True)
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method.upper(),
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": query_string.encode("utf-8"),
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }

    response_start: dict[str, object] = {}
    response_body = bytearray()

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, object]) -> None:
        if message["type"] == "http.response.start":
            response_start["status"] = int(message["status"])
            raw_headers = message.get("headers", [])
            response_start["headers"] = {
                key.decode("latin-1"): value.decode("latin-1")
                for key, value in raw_headers
            }
        elif message["type"] == "http.response.body":
            response_body.extend(message.get("body", b""))

    asyncio.run(app(scope, receive, send))
    return ASGIResponse(
        status_code=int(response_start.get("status", 500)),
        body=bytes(response_body),
        headers=dict(response_start.get("headers", {})),
    )
