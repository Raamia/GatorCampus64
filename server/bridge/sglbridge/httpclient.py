"""Tiny JSON-over-HTTP client on urllib (keeps the bridge stdlib-only apart from PyJWT).

Every component takes an `Http`-like object, so tests swap in a fake with the same `request()`.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any


class TransportError(Exception):
    """No HTTP response at all (DNS, refused, timeout, TLS)."""


@dataclass
class HttpResponse:
    status: int
    body: bytes = b""
    headers: dict[str, str] = field(default_factory=dict)

    def json(self) -> Any:
        if not self.body:
            return None
        try:
            return json.loads(self.body.decode("utf-8"))
        except ValueError:
            return None

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


class Http:
    def __init__(self, timeout: float = 15.0, user_agent: str = "sgl64-bridge/1", max_body: int = 128 * 1024 * 1024):
        self.timeout = timeout
        self.user_agent = user_agent
        self.max_body = max_body

    def request(self, method: str, url: str, *, json_body: Any = None, form: dict[str, str] | None = None,
                headers: dict[str, str] | None = None, timeout: float | None = None) -> HttpResponse:
        hdrs = {"User-Agent": self.user_agent, "Accept": "application/json"}
        data = None
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            hdrs["Content-Type"] = "application/json"
        elif form is not None:
            data = urllib.parse.urlencode(form).encode("ascii")
            hdrs["Content-Type"] = "application/x-www-form-urlencoded"
        hdrs.update(headers or {})
        req = urllib.request.Request(url, data=data, method=method, headers=hdrs)
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
                body = resp.read(self.max_body + 1)
                if len(body) > self.max_body:
                    raise TransportError(f"{method} {url}: response larger than {self.max_body} bytes")
                return HttpResponse(resp.status, body, dict(resp.headers.items()))
        except urllib.error.HTTPError as e:
            try:
                body = e.read(1024 * 1024)
            except Exception:  # noqa: BLE001 - the body of an error response is best effort
                body = b""
            return HttpResponse(e.code, body, dict(e.headers.items()) if e.headers else {})
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise TransportError(f"{method} {url}: {e}") from e
