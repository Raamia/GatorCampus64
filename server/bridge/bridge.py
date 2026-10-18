#!/usr/bin/env python3
"""Super Gatorlator 64 bridge (docs/web_platform_spec.md §6.4): one process that owns the headless game.

  * runs sm64coopdx as its child (GAME_CMD, default = the flags of server/deploy/sgl-game.service),
    restarts it when it exits, logs its stdout to the journal;
  * parses `SGLEVT {json}` lines (mods/sgl64/sgl_bridge.lua) and forwards every event to the API
    (POST /events, M2M token) through a bounded retry queue: an API outage never blocks the pipe;
  * login_req -> Auth0 device flow -> POST /links -> inbox `verified` (§7.1); link_req -> §7.2;
  * writes the inbox (<savepath>/sav/sgl64.modfs) the mod polls;
  * polls the public GET /leaderboards and sends the changed boards to the game (`leaderboard`, §10.3),
    every board again to a joining player;
  * applies guest character deploys (§5.3), at most one game restart per 5 minutes.
Configuration: environment variables, see server/deploy/bridge.env.example.
"""
from __future__ import annotations

import datetime as dt
import logging
import signal
import sys
import threading
import uuid
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sglbridge import config as config_mod  # noqa: E402
from sglbridge.api import ApiClient, RetryQueue  # noqa: E402
from sglbridge.outbox import DurableRetryQueue  # noqa: E402
from sglbridge.auth import Auth0Config, DeviceFlowClient, IdTokenValidator, M2MTokenProvider  # noqa: E402
from sglbridge.deploy import DeployLoop  # noqa: E402
from sglbridge.events import event_payload, parse_line  # noqa: E402
from sglbridge.game import GameSupervisor, line_buffered  # noqa: E402
from sglbridge.httpclient import Http  # noqa: E402
from sglbridge.inbox import Inbox  # noqa: E402
from sglbridge.leaderboard import LeaderboardPoller, fetch_leaderboards  # noqa: E402
from sglbridge.login import LoginService  # noqa: E402
from sglbridge import npc as npc_mod  # noqa: E402

log = logging.getLogger("sglbridge")
game_log = logging.getLogger("game")


class Bridge:
    """Event routing; everything with I/O is injected so tests can drive it line by line."""

    def __init__(self, inbox: Inbox, queue: RetryQueue | None, login: LoginService,
                 leaderboards: LeaderboardPoller | None = None, *, npc: npc_mod.NpcService | None = None):
        self.inbox = inbox
        self.queue = queue
        self.login = login
        self.leaderboards = leaderboards
        self.npc = npc
        self.players: dict[int, str] = {}
        self.session_id = str(uuid.uuid4())
        self.connections: dict[int, str] = {}
        self.sequence = 0
        self._lock = threading.Lock()

    def players_online(self) -> int:
        with self._lock:
            return len(self.players)

    def on_game_start(self) -> None:
        with self._lock:
            self.players.clear()
            self.connections.clear()
            self.session_id = str(uuid.uuid4())
            self.sequence = 0
        self.login.reset()
        self.inbox.reset()
        if self.leaderboards is not None:
            self.leaderboards.reset()
        if self.npc is not None:
            self.npc.reset()

    def on_game_exit(self, rc: int) -> None:
        """The game process ended: tell the API (/status) with an `exit` event."""
        with self._lock:
            self.players.clear()
            self.connections.clear()
        self.login.reset()
        self.inbox.reset()
        self._forward({"t": "exit", "code": rc})

    def _forward(self, ev: dict[str, Any]) -> None:
        if self.queue is not None:
            at = dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            self.sequence += 1
            # These fields are generated here, never trusted from game output.
            payload = event_payload(ev)
            if ev["t"] == "link_req":
                payload.pop("code", None)  # one-time credential belongs only in /links
            payload.update(session_id=self.session_id, event_id=str(uuid.uuid4()), sequence=self.sequence,
                           identities=self.login.identities() if ev["t"] == "run" else {})
            self.queue.put({"t": ev["t"], "payload": payload, "at": at})

    def _login_context(self, gi: int, name: str) -> dict | None:
        if self.players.get(gi) != name or gi not in self.connections:
            return None
        return {"session_id": self.session_id, "connection_id": self.connections[gi]}

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
        logged = event_payload(ev)
        if t == "link_req":
            logged.pop("code", None)
        log.info("event %s %s", t, logged)
        if t == "hello":
            self.on_game_start()
        elif t == "join" and isinstance(gi, int):
            with self._lock:
                self.players[gi] = name
                self.connections[gi] = str(uuid.uuid4())
            self.login.forget(gi)                 # a new player in that slot is not linked
            self.login.resend_verified()          # late joiners see every star
            if self.leaderboards is not None:
                self.leaderboards.on_join(gi)     # ... and every board
        elif t == "leave" and isinstance(gi, int):
            with self._lock:
                self.players.pop(gi, None)
                self.connections.pop(gi, None)
            self.login.cancel(gi)
            self.login.forget(gi)
        elif t == "login_cancel" and isinstance(gi, int):
            self.login.cancel(gi)
        elif t == "login_req" and isinstance(gi, int):
            context = self._login_context(gi, name)
            if context:
                self.login.on_login_req(gi, name, context)
        elif t == "run" and self.leaderboards is not None:
            self.leaderboards.kick()              # a new verified run may change a board
        elif t == "npc_ask" and self.npc is not None:
            self.npc.ask(ev)
            return
        elif t == "npc_ask":
            return
        elif t == "link_req" and isinstance(gi, int):
            code = "".join(c for c in str(ev.get("code") or "") if c.isalnum()).upper()[:16]
            if code:
                context = self._login_context(gi, name)
                if context:
                    self.login.on_link_req(gi, name, code, context)
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

    leaderboards = None
    if cfg.api_url and cfg.leaderboard_poll > 0:
        api_url = cfg.api_url
        leaderboards = LeaderboardPoller(lambda: fetch_leaderboards(http, api_url), inbox,
                                         interval=cfg.leaderboard_poll)
        threads.append(threading.Thread(target=leaderboards.run, args=(stop,), daemon=True, name="leaderboards"))

    api = None
    queue = None
    if cfg.api_enabled:
        tokens = M2MTokenProvider(cfg.m2m_domain or cfg.auth0_domain, cfg.m2m_client_id, cfg.m2m_client_secret,
                                  cfg.auth0_audience, http)
        api = ApiClient(cfg.api_url, tokens, http)

        def send_event(e: dict[str, Any]) -> None:
            api.post_event(e["t"], e["payload"], e["at"])
            if e["t"] == "run" and leaderboards is not None:
                leaderboards.kick()               # accepted: the board may have changed

        def stop_for_outbox_failure():
            log.critical("Event could not be persisted; stopping game. Inspect the bridge outbox and disk space.")
            if not stop.is_set():
                stop.set()
                threading.Thread(target=game.stop, daemon=True).start()

        queue = DurableRetryQueue(send_event, Path(cfg.state_dir) / "events.sqlite3",
                                  fatal=stop_for_outbox_failure)
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
    npc = npc_mod.build(cfg)
    bridge = Bridge(inbox, queue, login, leaderboards, npc=npc)
    if npc is not None:
        threads.append(threading.Thread(target=npc.run, args=(stop,), daemon=True, name="npc"))

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
