"""The platform API as the bridge sees it (Bearer M2M token, scope `bridge`), and the bounded retry queue
that keeps an API outage away from the game pipe."""
from __future__ import annotations

import collections
import logging
import threading
import time
from typing import Any, Callable

from .httpclient import TransportError

log = logging.getLogger("sglbridge.api")


class ApiUnavailable(Exception):
    """Transport error, 5xx or no token: worth retrying later."""


class ApiError(Exception):
    """4xx: retrying the same request will not help."""

    def __init__(self, status: int, body: Any):
        super().__init__(f"API {status}: {body}")
        self.status = status
        self.body = body


class ApiClient:
    def __init__(self, base_url: str, tokens: Any, http: Any):
        self.base = base_url.rstrip("/")
        self.tokens = tokens
        self.http = http

    def _call(self, method: str, path: str, body: Any = None) -> Any:
        for attempt in (1, 2):
            try:
                token = self.tokens.get()
                resp = self.http.request(method, self.base + path, json_body=body,
                                         headers={"Authorization": f"Bearer {token}"})
            except TransportError as e:
                raise ApiUnavailable(str(e)) from e
            if resp.status == 401 and attempt == 1:
                self.tokens.invalidate()      # expired / rotated: one fresh token, then give up
                continue
            if resp.status >= 500 or resp.status == 429:
                raise ApiUnavailable(f"{method} {path}: {resp.status}")
            if not resp.ok:
                raise ApiError(resp.status, resp.json())
            return resp.json()
        raise ApiUnavailable(f"{method} {path}: unauthorized")

    # POST /events {t, payload, at}. The event's own fields are repeated at the top level because
    # server/api reads fields such as char's `friend` from the top level.
    def post_event(self, t: str, payload: dict[str, Any], at: str) -> None:
        body = {k: v for k, v in payload.items() if k not in ("t", "payload", "at")}
        body.update({"t": t, "payload": payload, "at": at})
        self._call("POST", "/events", body)

    # POST /links {sub, coopdx_name, gi[, nickname, uf]} -> {nickname, guest_slot|null, uf, ...}
    def post_link(self, sub: str, coopdx_name: str, gi: int, nickname: str | None = None,
                  uf: bool | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"sub": sub, "coopdx_name": coopdx_name, "gi": gi}
        if nickname:
            body["nickname"] = nickname[:64]
        if uf is not None:
            body["uf"] = uf
        return self._call("POST", "/links", body) or {}

    # §7.2 fallback (/link <code>): POST /links {code, coopdx_name, gi} -> same reply; 404 / 410 = bad code
    def redeem_link_code(self, code: str, coopdx_name: str, gi: int) -> dict[str, Any]:
        return self._call("POST", "/links", {"code": code, "coopdx_name": coopdx_name, "gi": gi}) or {}

    # GET /deploys/pending -> {"deploys": [{id, slot, kind, name, owner_sub, files: [{path, url}], ...}],
    # "roster": [...]}; a bare list of deploys is accepted too
    def pending_deploys(self) -> list[dict[str, Any]]:
        out = self._call("GET", "/deploys/pending")
        if isinstance(out, dict):
            out = out.get("deploys")
        return [d for d in out if isinstance(d, dict)] if isinstance(out, list) else []

    # POST /deploys/{id}: server/api reads {state, error}; {status, detail} is sent too
    def report_deploy(self, deploy_id: Any, status: str, detail: str = "") -> None:
        detail = detail[:2000]
        self._call("POST", f"/deploys/{deploy_id}", {"state": status, "error": detail if status == "failed" else None,
                                                     "status": status, "detail": detail})

    def download(self, url: str) -> bytes:
        """Presigned artifact URL (no bearer token: it would leak to object storage)."""
        try:
            resp = self.http.request("GET", url, headers={"Accept": "*/*"}, timeout=120)
        except TransportError as e:
            raise ApiUnavailable(str(e)) from e
        if not resp.ok:
            raise ApiUnavailable(f"artifact download {resp.status}")
        return resp.body


class RetryQueue:
    """Bounded FIFO with one sender thread. put() never blocks: when full, the OLDEST item is dropped.

    send(item) raising ApiError (4xx) drops that item; anything else keeps it at the head and backs off
    (base_delay doubling up to max_delay) so ordering is preserved and the API is not hammered.
    """

    def __init__(self, send: Callable[[Any], None], maxlen: int = 2000, base_delay: float = 1.0,
                 max_delay: float = 60.0, clock: Callable[[], float] = time.monotonic):
        self.send = send
        self.maxlen = maxlen
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.clock = clock
        self.dropped = 0
        self.sent = 0
        self.failures = 0
        self.next_attempt = 0.0
        self._q: collections.deque[Any] = collections.deque()
        self._cv = threading.Condition()

    def __len__(self) -> int:
        with self._cv:
            return len(self._q)

    def put(self, item: Any) -> None:
        with self._cv:
            if len(self._q) >= self.maxlen:
                self._q.popleft()
                self.dropped += 1
                if self.dropped in (1, 10, 100) or self.dropped % 1000 == 0:
                    log.warning("retry queue full: %d items dropped so far", self.dropped)
            self._q.append(item)
            self._cv.notify()

    def drain_once(self) -> int:
        """Send items until the queue is empty or a send fails. Returns how many were delivered."""
        delivered = 0
        while True:
            with self._cv:
                if not self._q:
                    return delivered
                if self.clock() < self.next_attempt:
                    return delivered
                item = self._q[0]
            try:
                self.send(item)
            except ApiError as e:
                log.warning("dropping undeliverable item (%s): %r", e, item)
                self._pop(item)
                continue
            except Exception as e:  # noqa: BLE001 - outage: keep the item, back off
                self.failures += 1
                delay = min(self.max_delay, self.base_delay * (2 ** min(self.failures - 1, 16)))
                self.next_attempt = self.clock() + delay
                if self.failures in (1, 5) or self.failures % 50 == 0:
                    log.warning("send failed (%d in a row, retry in %.0f s): %s", self.failures, delay, e)
                return delivered
            self.failures = 0
            self.next_attempt = 0.0
            self.sent += 1
            delivered += 1
            self._pop(item)

    def _pop(self, item: Any) -> None:
        with self._cv:
            if self._q and self._q[0] is item:
                self._q.popleft()

    def run(self, stop: threading.Event) -> None:
        while not stop.is_set():
            with self._cv:
                if not self._q:
                    self._cv.wait(timeout=1.0)
                    continue
                pause = self.next_attempt - self.clock()
            if pause > 0:
                stop.wait(min(pause, 1.0))
                continue
            self.drain_once()
