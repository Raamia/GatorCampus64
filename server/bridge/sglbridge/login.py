"""In-game Gator Pass login (spec §7.1, §7.2): login_req / link_req events -> device flow -> /links -> inbox.

Inbox commands produced (fields exactly as the mod receives them):
  login_code   {gi, user_code, uri, page, expires}  uri = verification_uri_complete (for the QR),
                                                    page = verification_uri (to print next to the code),
                                                    expires = seconds until the code expires
  verified     {gi, name, nickname, guest_slot?, uf?, resend?}
                                                    guest_slot only when the user owns one; uf = true when
                                                    the account has the UF badge; resend = true on the
                                                    copies re-broadcast when someone joins (late joiners
                                                    see every star), so clients can skip the welcome
  login_failed {gi, reason}  reason: expired | denied | invalid_token | bad_code | unavailable | error
Links live for the game session, keyed by global index (spec §7.1): forgotten on leave and on game restart.
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Callable

from .api import ApiError, ApiUnavailable
from .auth import Cancelled, LoginFailed

log = logging.getLogger("sglbridge.login")

UF_CLAIM = "https://gatorcamp.us/uf"


class LoginService:
    def __init__(self, flow: Any, validator: Any, api: Any, inbox: Any, max_sessions: int = 16,
                 spawn: Callable[[Callable[[], None]], None] | None = None,
                 waiter: Callable[[threading.Event, float], bool] | None = None):
        self.flow = flow
        self.validator = validator
        self.api = api
        self.inbox = inbox
        self.max_sessions = max_sessions
        self.spawn = spawn or (lambda fn: threading.Thread(target=fn, daemon=True, name="login").start())
        self.waiter = waiter or (lambda ev, seconds: ev.wait(seconds))
        self._sessions: dict[int, threading.Event] = {}
        self._links: dict[int, dict[str, Any]] = {}     # gi -> the verified command's fields
        self._identities: dict[int, dict[str, Any]] = {}  # server-only, never sent to game clients
        self._lock = threading.Lock()

    # events ------------------------------------------------------------------------------------
    def on_login_req(self, gi: int, name: str, context: dict | None = None) -> None:
        if self.flow is None or self.validator is None or self.api is None:
            self.inbox.push("login_failed", gi=gi, reason="unavailable")
            return
        cancel = self._begin(gi)
        if cancel is None:
            self.inbox.push("login_failed", gi=gi, reason="unavailable")
            return
        self.spawn(lambda: self._guarded(gi, cancel, lambda: self.run_device_flow(gi, name, cancel, context)))

    def on_link_req(self, gi: int, name: str, code: str, context: dict | None = None) -> None:
        if self.api is None:
            self.inbox.push("login_failed", gi=gi, reason="unavailable")
            return
        cancel = self._begin(gi)
        if cancel is None:
            self.inbox.push("login_failed", gi=gi, reason="unavailable")
            return
        self.spawn(lambda: self._guarded(gi, cancel, lambda: self.run_link_code(gi, name, code, cancel, context)))

    def cancel(self, gi: int) -> None:
        """Stop a running login of gi (login_cancel, leave): no further polling, no inbox message."""
        with self._lock:
            ev = self._sessions.pop(gi, None)
            if ev is not None:
                ev.set()

    def forget(self, gi: int, expected_link_id: int | None = None) -> None:
        with self._lock:
            if expected_link_id is not None and self._identities.get(gi, {}).get("link_id") != expected_link_id:
                return
            ev = self._sessions.pop(gi, None)
            if ev is not None:
                ev.set()
            self._links.pop(gi, None)
            self._identities.pop(gi, None)
            self.inbox.discard_player(gi)

    def reset(self) -> None:
        """The game (re)started: every login and link is gone."""
        with self._lock:
            sessions, self._sessions = self._sessions, {}
            self._links.clear()
            self._identities.clear()
            for ev in sessions.values():
                ev.set()

    cancel_all = reset

    def linked(self) -> dict[int, dict[str, Any]]:
        with self._lock:
            return {gi: dict(f) for gi, f in self._links.items()}

    def identities(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {str(gi): dict(identity) for gi, identity in self._identities.items()}

    def resend_verified(self) -> int:
        """Broadcast `verified` again for every linked player (someone joined)."""
        with self._lock:
            for gi in sorted(self._links):
                self.inbox.push("verified", **self._links[gi], resend=True)
            return len(self._links)

    # flows (synchronous; tests call these directly) ---------------------------------------------
    def run_device_flow(self, gi: int, name: str, cancel: threading.Event, context: dict | None = None) -> None:
        dc = self.flow.request_code()
        with self._lock:
            self._check_current(gi, cancel)
            self.inbox.push("login_code", gi=gi, user_code=dc.user_code, uri=dc.verification_uri_complete,
                            page=dc.verification_uri, expires=dc.expires_in)
        tokens = self.flow.poll(dc, lambda seconds: self.waiter(cancel, seconds))
        id_token = tokens.get("id_token")
        if not id_token:
            raise LoginFailed("invalid_token", "no id_token (scope openid missing?)")
        claims = self.validator.validate(id_token)
        if cancel.is_set():
            raise Cancelled()
        nickname = claims.get("nickname") or claims.get("name")
        uf = claims.get(UF_CLAIM) if isinstance(claims.get(UF_CLAIM), bool) else None
        link = self._api(lambda: self.api.post_link(claims["sub"], name, gi, nickname=nickname, uf=uf,
                                                   **(context or {})))
        if cancel.is_set():
            raise Cancelled()
        self._verified(gi, name, link, claims, cancel, context)

    def run_link_code(self, gi: int, name: str, code: str, cancel: threading.Event,
                      context: dict | None = None) -> None:
        with self._lock:
            self._check_current(gi, cancel)
        try:
            link = self._api(lambda: self.api.redeem_link_code(code, name, gi, **(context or {})))
        except ApiError as e:
            reason = (e.body.get("detail") or {}) if isinstance(e.body, dict) else {}
            reason = reason.get("reason") if isinstance(reason, dict) else None
            raise LoginFailed("expired" if e.status == 410 and reason == "expired" else "bad_code", str(e)) from e
        self._verified(gi, name, link, {}, cancel, context)

    # helpers -----------------------------------------------------------------------------------
    def _begin(self, gi: int) -> threading.Event | None:
        with self._lock:
            old = self._sessions.pop(gi, None)
            if old is not None:
                old.set()                       # asking again replaces the running attempt
            if len(self._sessions) >= self.max_sessions:
                return None
            ev = threading.Event()
            self._sessions[gi] = ev
            return ev

    def _end(self, gi: int, cancel: threading.Event) -> None:
        with self._lock:
            if self._sessions.get(gi) is cancel:
                del self._sessions[gi]

    def _guarded(self, gi: int, cancel: threading.Event, fn: Callable[[], None]) -> None:
        try:
            fn()
        except Cancelled:
            log.info("login gi=%d cancelled", gi)
        except LoginFailed as e:
            log.info("login gi=%d failed: %s", gi, e)
            self._failure(gi, cancel, e.reason)
        except Exception:  # noqa: BLE001 - never kill the bridge over one login
            log.exception("login gi=%d crashed", gi)
            self._failure(gi, cancel, "error")
        finally:
            self._end(gi, cancel)

    @staticmethod
    def _api(fn: Callable[[], Any]) -> Any:
        try:
            return fn()
        except ApiUnavailable as e:
            raise LoginFailed("unavailable", str(e)) from e

    def _check_current(self, gi: int, cancel: threading.Event) -> None:
        # Caller holds _lock: checking and publishing must be one operation.
        if cancel.is_set() or self._sessions.get(gi) is not cancel:
            raise Cancelled()

    def _failure(self, gi: int, cancel: threading.Event, reason: str) -> None:
        with self._lock:
            if not cancel.is_set() and self._sessions.get(gi) is cancel:
                self.inbox.push("login_failed", gi=gi, reason=reason)

    def _verified(self, gi: int, name: str, link: dict[str, Any], claims: dict[str, Any],
                  cancel: threading.Event, context: dict | None = None) -> None:
        slot = link.get("guest_slot")
        nickname = link.get("nickname") or claims.get("nickname") or claims.get("name") or name
        fields: dict[str, Any] = {"gi": gi, "name": name, "nickname": str(nickname)[:24]}
        if isinstance(slot, int) and not isinstance(slot, bool):
            fields["guest_slot"] = slot
        if claims.get(UF_CLAIM) is True or link.get("uf") is True:
            fields["uf"] = True
        with self._lock:
            self._check_current(gi, cancel)
            if context:
                link_id = link.get("link_id")
                if type(link_id) is not int or link_id < 1:
                    raise LoginFailed("unavailable", "API does not support session-bound links")
                self._identities[gi] = {**context, "link_id": link_id, "name": name}
            self._links[gi] = fields
            self.inbox.push("verified", **fields)
        log.info("login gi=%d (%s) verified as %s, slot %s", gi, name, nickname, slot)
