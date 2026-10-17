import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sglbridge.httpclient import HttpResponse, TransportError  # noqa: E402


class FakeHttp:
    """Scripted HTTP: routes[(method, url)] = list of HttpResponse | Exception, consumed in order
    (the last one repeats). Every call is recorded in .calls."""

    def __init__(self):
        self.routes = {}
        self.calls = []

    def add(self, method, url, *responses):
        self.routes.setdefault((method, url), []).extend(responses)

    def request(self, method, url, *, json_body=None, form=None, headers=None, timeout=None):
        self.calls.append({"method": method, "url": url, "json": json_body, "form": form, "headers": headers or {}})
        script = self.routes.get((method, url))
        if not script:
            raise TransportError(f"no route for {method} {url}")
        r = script.pop(0) if len(script) > 1 else script[0]
        if isinstance(r, Exception):
            raise r
        return r


def resp(status, body=None, raw=None):
    import json
    if raw is not None:
        return HttpResponse(status, raw)
    return HttpResponse(status, json.dumps(body).encode() if body is not None else b"")


class FakeClock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t

    def wait(self, seconds):
        """A `wait` that advances the clock and records the pauses; returns False (not cancelled)."""
        self.waits.append(seconds)
        self.t += seconds
        return False

    @property
    def waits(self):
        if not hasattr(self, "_waits"):
            self._waits = []
        return self._waits


@pytest.fixture
def http():
    return FakeHttp()


@pytest.fixture
def clock():
    return FakeClock()
