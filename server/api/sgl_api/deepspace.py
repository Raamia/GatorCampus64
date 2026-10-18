"""Push ranked runs to the DeepSpace app (docs/web_platform_spec.md §10.4).

Transport: POST <DEEPSPACE_APP_URL>/api/actions/ingestVerifiedRun with the JSON body from
runs.push_payload() and three headers:

    X-SGL-Timestamp: <unix seconds>
    X-SGL-Nonce:     <32 lowercase hex chars, fresh per attempt>
    X-SGL-Signature: v1=<hex HMAC-SHA256(DEEPSPACE_INGEST_SECRET, "v1:" + timestamp + ":" + nonce + ":" + body)>

`body` is the exact byte string sent. The app (companion/app/src/server/ingest-routes.ts) checks the
signature in constant time, accepts timestamps within ±300 s, rejects a nonce it has already seen,
and upserts by runId, so a retried push is harmless.

Delivery goes through the run_pushes outbox (schema.sql): a ranked run gets a row in the same
transaction that stores it; drain() claims due rows one at a time (a short lease in next_at, so two
API processes never send the same row at once), sends, and marks them sent or reschedules them with
exponential backoff. A DeepSpace outage therefore never loses a run and never blocks POST /events.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import threading
import time
from typing import Any

import httpx

from . import runs
from .config import Settings
from .db import Database

log = logging.getLogger("sgl_api.deepspace")

INGEST_PATH = "/api/actions/ingestVerifiedRun"
LEASE_SECS = 60
BACKOFF_BASE = 30
BACKOFF_CAP = 3600
PERMANENT = (400, 404, 413, 422)   # the app refused the body itself: retrying cannot help


def sign(secret: str, body: bytes, timestamp: str | None = None, nonce: str | None = None) -> dict[str, str]:
    ts = timestamp or str(int(time.time()))
    nonce = nonce or secrets.token_hex(16)
    mac = hmac.new(secret.encode(), b"v1:" + ts.encode() + b":" + nonce.encode() + b":" + body, hashlib.sha256)
    return {"X-SGL-Timestamp": ts, "X-SGL-Nonce": nonce, "X-SGL-Signature": "v1=" + mac.hexdigest(),
            "Content-Type": "application/json"}


def encode(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=False).encode()


def backoff(attempts: int) -> int:
    return min(BACKOFF_BASE * 2 ** max(attempts - 1, 0), BACKOFF_CAP)


class Pusher:
    def __init__(self, settings: Settings, db_getter, transport: httpx.BaseTransport | None = None):
        self.s = settings
        self._db = db_getter
        self._client = httpx.Client(timeout=settings.deepspace_timeout, transport=transport) \
            if settings.deepspace_enabled else None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def enabled(self) -> bool:
        return self._client is not None

    @property
    def db(self) -> Database:
        return self._db()

    # ── one attempt ───────────────────────────────────────────────────────────────────────────

    def _claim(self) -> dict | None:
        with self.db.tx() as c:
            return c.execute(
                """UPDATE run_pushes SET next_at = now() + make_interval(secs => %s), attempts = attempts + 1
                    WHERE run_id = (SELECT run_id FROM run_pushes WHERE state = 'pending' AND next_at <= now()
                                     ORDER BY next_at, run_id LIMIT 1 FOR UPDATE SKIP LOCKED)
                    RETURNING run_id, attempts""", (LEASE_SECS,)).fetchone()

    def _finish(self, run_id: int, attempts: int, ok: bool, error: str | None, permanent: bool = False) -> None:
        with self.db.tx() as c:
            if ok:
                c.execute("UPDATE run_pushes SET state = 'sent', sent_at = now(), last_error = NULL WHERE run_id = %s",
                          (run_id,))
            elif permanent or attempts >= self.s.deepspace_push_max_attempts:
                c.execute("UPDATE run_pushes SET state = 'failed', last_error = %s WHERE run_id = %s",
                          ((error or "")[:2000], run_id))
            else:
                c.execute("UPDATE run_pushes SET next_at = now() + make_interval(secs => %s), last_error = %s "
                          "WHERE run_id = %s", (backoff(attempts), (error or "")[:2000], run_id))

    def send_one(self) -> bool | None:
        """Claim and push one due row. None when nothing was due."""
        job = self._claim()
        if not job:
            return None
        run_id, attempts = job["run_id"], job["attempts"]
        with self.db.tx() as c:
            payload = runs.push_payload(c, run_id)
        if payload is None:   # the run was deleted or un-ranked by hand
            self._finish(run_id, attempts, False, "run is not ranked", permanent=True)
            return False
        body = encode(payload)
        url = self.s.deepspace_app_url.rstrip("/") + INGEST_PATH
        try:
            r = self._client.post(url, content=body, headers=sign(self.s.deepspace_ingest_secret, body))
        except httpx.HTTPError as e:
            log.warning("push run %s: %s", run_id, e)
            self._finish(run_id, attempts, False, f"{type(e).__name__}: {e}")
            return False
        ok = 200 <= r.status_code < 300
        if ok:
            try:
                ok = r.json().get("success") is not False
            except ValueError:
                ok = False
        if not ok:
            log.warning("push run %s: HTTP %s %s", run_id, r.status_code, r.text[:200])
        self._finish(run_id, attempts, ok, None if ok else f"HTTP {r.status_code}: {r.text[:500]}",
                     permanent=r.status_code in PERMANENT)
        return ok

    def erase_one(self, account=False):
        """Deletion delivery retries indefinitely and cannot be lost when the original run is gone."""
        with self.db.tx() as c:
            table = "account_erases" if account else "run_erases"
            pk = "id" if account else "uid"
            row = c.execute(f"SELECT * FROM {table} WHERE next_at <= now() "
                            "ORDER BY next_at LIMIT 1 FOR UPDATE SKIP LOCKED").fetchone()
            if row is None:
                return None
            payload = {"v": 1, "deleteUserRuns": {"userId": row["deepspace_user"], "beforeMs": row["before_ms"]}} if account else {"v": 1, "deleteRunId": str(row["uid"])}
            body = encode(payload)
            ok = False
            error = None
            try:
                response = self._client.post(self.s.deepspace_app_url.rstrip("/") + INGEST_PATH,
                                             content=body, headers=sign(self.s.deepspace_ingest_secret, body))
                ok = response.is_success and response.json().get("success") is True
                error = None if ok else f"HTTP {response.status_code}"
            except (httpx.HTTPError, ValueError) as e:
                error = type(e).__name__
            if ok:
                c.execute(f"UPDATE {table} SET sent_at = now(), attempts = attempts + 1, last_error = NULL, next_at = now() + interval '1 day' "
                          f"WHERE {pk} = %s", (row[pk],))
            else:
                c.execute(f"UPDATE {table} SET attempts = attempts + 1, last_error = %s, "
                          f"next_at = now() + make_interval(secs => %s) WHERE {pk} = %s",
                          (error, backoff(min(row["attempts"] + 1, 10)), row[pk]))
            return ok

    def drain(self, max_items: int = 50) -> int:
        """Push due rows until none is left (or max_items). Returns how many were sent."""
        if not self.enabled or not self._lock.acquire(blocking=False):
            return 0
        sent = 0
        try:
            for _ in range(max_items):
                erased = self.erase_one(account=True)
                if erased is None:
                    break
                sent += bool(erased)
            for _ in range(max_items):
                erased = self.erase_one()
                if erased is None:
                    break
                sent += bool(erased)
            for _ in range(max_items):
                r = self.send_one()
                if r is None:
                    break
                sent += bool(r)
        except Exception:  # noqa: BLE001 - never let the outbox take down a request or the loop
            log.exception("draining run_pushes")
        finally:
            self._lock.release()
        return sent

    # ── background sweep ──────────────────────────────────────────────────────────────────────

    def start(self) -> None:
        if not self.enabled or self.s.deepspace_push_interval <= 0 or self._thread:
            return
        self._thread = threading.Thread(target=self._loop, name="deepspace-push", daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop.wait(self.s.deepspace_push_interval):
            self.drain()

    def close(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        if self._client:
            self._client.close()
