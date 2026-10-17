#!/usr/bin/env python3
"""Super Gatorlator 64 bridge (docs/web_platform_spec.md §6.4): one process that owns the headless game.

  * runs sm64coopdx as its child (GAME_CMD, default = the flags of server/deploy/sgl-game.service),
    restarts it when it exits, logs its stdout to the journal;
  * parses `SGLEVT {json}` lines (mods/sgl64/sgl_bridge.lua) and forwards every event to the API
    (POST /events, M2M token) through a bounded retry queue: an API outage never blocks the pipe;
  * login_req -> Auth0 device flow -> POST /links -> inbox `verified` (§7.1); link_req -> §7.2;
  * writes the inbox (<savepath>/sav/sgl64.modfs) the mod polls;
  * applies guest character deploys (§5.3), at most one game restart per 5 minutes.
Configuration: environment variables, see server/deploy/bridge.env.example.
"""
from __future__ import annotations

import datetime as dt
import logging
import signal
import sys
import threading
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sglbridge import config as config_mod  # noqa: E402
from sglbridge.api import ApiClient, RetryQueue  # noqa: E402
from sglbridge.auth import Auth0Config, DeviceFlowClient, IdTokenValidator, M2MTokenProvider  # noqa: E402
from sglbridge.deploy import DeployLoop  # noqa: E402
from sglbridge.events import event_payload, parse_line  # noqa: E402
from sglbridge.game import GameSupervisor, line_buffered  # noqa: E402
from sglbridge.httpclient import Http  # noqa: E402
from sglbridge.inbox import Inbox  # noqa: E402
from sglbridge.login import LoginService  # noqa: E402

log = logging.getLogger("sglbridge")
game_log = logging.getLogger("game")


class Bridge:
    """Event routing; everything with I/O is injected so tests can drive it line by line."""

    def __init__(self, inbox: Inbox, queue: RetryQueue | None, login: LoginService):
        self.inbox = inbox
        self.queue = queue
        self.login = login
        self.players: dict[int, str] = {}
        self._lock = threading.Lock()

    def players_online(self) -> int:
        with self._lock:
            return len(self.players)

    def on_game_start(self) -> None:
        with self._lock:
            self.players.clear()
        self.login.reset()
        self.inbox.reset()

    def on_game_exit(self, rc: int) -> None:
        """The game process ended: tell the API (/status) with an `exit` event."""
        with self._lock:
            self.players.clear()
        self._forward({"t": "exit", "code": rc})

    def _forward(self, ev: dict[str, Any]) -> None:
        if self.queue is not None:
            at = dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            self.queue.put({"t": ev["t"], "payload": event_payload(ev), "at": at})

    def on_line(self, line: str) -> None:
        ev, other = parse_line(line)
        if other is not None:
            game_log.info("%s", other)
        if ev is not None:
            self.on_event(ev)

    def on_event(self, ev: dict[str, Any]) -> None:
        t = ev["t"]
        gi = ev.get("gi")
        name = str(ev.get("name") or "")
        log.info("event %s %s", t, event_payload(ev))
        if t == "hello":
            with self._lock:
                self.players.clear()
        elif t == "join" and isinstance(gi, int):
            with self._lock:
                self.players[gi] = name
            self.login.forget(gi)                 # a new player in that slot is not linked
            self.login.resend_verified()          # late joiners see every star
        elif t == "leave" and isinstance(gi, int):
            with self._lock:
                self.players.pop(gi, None)
            self.login.cancel(gi)
            self.login.forget(gi)
        elif t == "login_cancel" and isinstance(gi, int):
            self.login.cancel(gi)
        elif t == "login_req" and isinstance(gi, int):
            self.login.on_login_req(gi, name)
        elif t == "link_req" and isinstance(gi, int):
            code = "".join(c for c in str(ev.get("code") or "") if c.isalnum()).upper()[:16]
            if code:
                self.login.on_link_req(gi, name, code)
            else:
                self.inbox.push("login_failed", gi=gi, reason="bad_code")
        self._forward(ev)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s", stream=sys.stderr)
    cfg = config_mod.from_env()
    http = Http()
    inbox = Inbox(cfg.modfs_path)
    stop = threading.Event()
    threads: list[threading.Thread] = []

    api = None
    queue = None
    if cfg.api_enabled:
        tokens = M2MTokenProvider(cfg.m2m_domain or cfg.auth0_domain, cfg.m2m_client_id, cfg.m2m_client_secret,
                                  cfg.auth0_audience, http)
        api = ApiClient(cfg.api_url, tokens, http)
        queue = RetryQueue(lambda e: api.post_event(e["t"], e["payload"], e["at"]))
        threads.append(threading.Thread(target=queue.run, args=(stop,), daemon=True, name="events"))
    else:
        log.warning("API not configured (API_URL / AUTH0_M2M_*): events are logged only, no deploys")

    flow = validator = None
    if cfg.login_enabled:
        a0 = Auth0Config(cfg.auth0_domain, cfg.auth0_client_id, cfg.auth0_audience, cfg.auth0_issuer)
        flow = DeviceFlowClient(a0, http)
        validator = IdTokenValidator(a0.issuer_url, a0.client_id)
    else:
        log.warning("Auth0 not configured (AUTH0_DOMAIN / AUTH0_CLIENT_ID / AUTH0_AUDIENCE): /login answers 'unavailable'")
    login = LoginService(flow, validator, api, inbox)
    bridge = Bridge(inbox, queue, login)

    cmd = line_buffered(cfg.game_cmd) if cfg.line_buffer else cfg.game_cmd
    game = GameSupervisor(cmd, cfg.game_cwd, bridge.on_line, bridge.on_game_start, on_exit=bridge.on_game_exit)

    if api is not None and cfg.deploys:
        deploy = DeployLoop(api, inbox, game, cfg.mod_dir, Path(cfg.state_dir) / "roster.json", bridge.players_online,
                            placeholder_mod=cfg.placeholder_mod, rename_tool=cfg.actor_rename,
                            poll_interval=cfg.deploy_poll, min_restart_gap=cfg.deploy_gap,
                            announce_wait=cfg.announce_wait)
        threads.append(threading.Thread(target=deploy.run, args=(stop,), daemon=True, name="deploy"))

    def on_signal(signum: int, _frame: Any) -> None:
        log.info("signal %d: stopping", signum)
        stop.set()
        threading.Thread(target=game.stop, daemon=True).start()

    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)
    for t in threads:
        t.start()
    game.run(stop)
    game.stop()
    if queue is not None:
        queue.next_attempt = 0.0
        queue.drain_once()                       # best effort: deliver `exit` before going down
    log.info("bridge stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
