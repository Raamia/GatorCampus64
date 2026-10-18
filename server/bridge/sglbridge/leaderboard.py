"""Verified leaderboards, bridge side (spec §10.3): GET /leaderboards -> inbox `leaderboard` commands.

The API's public `GET /leaderboards` returns `{missions: [{mission, title, rows: [{rank, names, frames}]}]}`
(top 5 per mission). The poller fetches it at start, every `interval` seconds and `after_run` seconds
after each `run` event (and after each run the API accepted), and broadcasts one command per mission
whose rows changed since the last broadcast:

    leaderboard {mission, n, name1, frames1, ... name5, frames5, at}

`n` = rows sent (0-5), `nameK` = the run's player names joined with " + " (trimmed to NAME_MAX
characters), `framesK` = the run's frames, `at` = Unix time of the fetch that saw these rows change
(the in-game "updated ... ago"; a join re-send keeps it). Fields are primitives only
(the mod forwards them in a packet). A board that loses all its rows is sent once with n = 0; empty
boards are never sent otherwise. A joining player gets every non-empty board again, addressed to
their gi (like `verified` with resend). When the game (re)starts, the next poll re-broadcasts all of
them. A failed fetch keeps the last boards (join re-sends still work) and is retried on schedule.
"""
from __future__ import annotations

import logging
import re
import threading
import time
from typing import Any, Callable

from .api import ApiUnavailable
from .httpclient import TransportError

log = logging.getLogger("sglbridge.leaderboard")

ROWS = 5
NAME_MAX = 28                    # what fits a row of the in-game board (sgl_deepspace.lua)
MISSION_RE = re.compile(r"^[A-Za-z0-9_.+-]{1,64}$")   # the mod rejects other ids

Rows = tuple[tuple[str, int], ...]


def fetch_leaderboards(http: Any, base_url: str) -> list[dict[str, Any]]:
    """GET <api>/leaderboards (public: no token). Raises ApiUnavailable on any failure."""
    url = base_url.rstrip("/") + "/leaderboards"
    try:
        resp = http.request("GET", url)
    except TransportError as e:
        raise ApiUnavailable(str(e)) from e
    if not resp.ok:
        raise ApiUnavailable(f"GET /leaderboards: {resp.status}")
    body = resp.json()
    missions = body.get("missions") if isinstance(body, dict) else None
    if not isinstance(missions, list):
        raise ApiUnavailable("GET /leaderboards: no missions list")
    return [m for m in missions if isinstance(m, dict)]


def join_names(names: Any, limit: int = NAME_MAX) -> str:
    """A run's player names as one string: "Alice + Bob", trimmed to `limit` characters."""
    if isinstance(names, str):
        parts = [names]
    elif isinstance(names, (list, tuple)):
        parts = [str(n) for n in names if isinstance(n, (str, int)) and not isinstance(n, bool)]
    else:
        parts = []
    parts = [" ".join(p.split()) for p in parts]
    text = " + ".join(p for p in parts if p) or "?"
    if len(text) > limit:
        text = text[: limit - 3].rstrip(" +") + "..."
    return text


def board_rows(entry: dict[str, Any]) -> Rows:
    """The (name, frames) rows of one mission, best first, at most ROWS."""
    rows = entry.get("rows")
    if not isinstance(rows, list):
        return ()
    good = []
    for i, r in enumerate(rows):
        if not isinstance(r, dict):
            continue
        frames = r.get("frames")
        if isinstance(frames, bool) or not isinstance(frames, (int, float)) or frames < 1:
            continue
        rank = r.get("rank")
        rank = rank if isinstance(rank, int) and not isinstance(rank, bool) else 10_000 + i
        good.append((rank, i, join_names(r.get("names")), int(frames)))
    good.sort()
    return tuple((name, frames) for _, _, name, frames in good[:ROWS])


def command_fields(mission: str, rows: Rows, at: int) -> dict[str, Any]:
    fields: dict[str, Any] = {"mission": mission, "n": len(rows)}
    for k, (name, frames) in enumerate(rows, 1):
        fields[f"name{k}"] = name
        fields[f"frames{k}"] = frames
    fields["at"] = at
    return fields


class LeaderboardPoller:
    def __init__(self, fetch: Callable[[], list[dict[str, Any]]], inbox: Any, *, interval: float = 60.0,
                 after_run: float = 2.0, clock: Callable[[], float] = time.monotonic,
                 wall: Callable[[], float] = time.time):
        self.fetch = fetch
        self.inbox = inbox
        self.interval = interval
        self.after_run = after_run
        self.clock = clock
        self.wall = wall
        self.next_at = 0.0                       # poll right away
        self._boards: dict[str, tuple[Rows, int]] = {}     # last fetched: mission -> (rows, at)
        self._sent: dict[str, Rows] = {}                   # last broadcast per mission
        self._lock = threading.Lock()
        self._wake = threading.Condition(self._lock)

    def poll_once(self) -> int:
        """Fetch and broadcast the changed boards. Returns how many commands were pushed."""
        try:
            missions = self.fetch()
        except Exception as e:  # noqa: BLE001 - an outage keeps the last boards
            log.warning("leaderboards unavailable: %s", e)
            return 0
        at = int(self.wall())
        fresh: dict[str, Rows] = {}
        for m in missions:
            mission = m.get("mission")
            if isinstance(mission, str) and MISSION_RE.match(mission):
                fresh[mission] = board_rows(m)
        pushed = 0
        with self._lock:
            for mission in sorted(set(fresh) | set(self._sent)):
                rows = fresh.get(mission, ())
                if rows == self._sent.get(mission, ()):
                    if mission in fresh and mission not in self._boards:
                        self._boards[mission] = (rows, at)
                    continue
                self._boards[mission] = (rows, at)
                self.inbox.push("leaderboard", **command_fields(mission, rows, at))
                pushed += 1
                if rows:
                    self._sent[mission] = rows
                else:
                    self._sent.pop(mission, None)
            for mission in list(self._boards):
                if mission not in fresh:
                    del self._boards[mission]
        if pushed:
            log.info("leaderboards: %d board(s) changed", pushed)
        return pushed

    def on_join(self, gi: int) -> int:
        """Send every non-empty board to the player who just joined."""
        with self._lock:
            boards = sorted((m, rows, at) for m, (rows, at) in self._boards.items() if rows)
        for mission, rows, at in boards:
            self.inbox.push("leaderboard", gi=gi, **command_fields(mission, rows, at))
        return len(boards)

    def kick(self, delay: float | None = None) -> None:
        """Poll `delay` seconds from now (default after_run) unless one is due sooner."""
        delay = self.after_run if delay is None else delay
        with self._wake:
            self.next_at = min(self.next_at, self.clock() + delay)
            self._wake.notify()

    def reset(self) -> None:
        """The game (re)started: nothing has been broadcast to it yet."""
        with self._wake:
            self._sent.clear()
            self.next_at = min(self.next_at, self.clock() + self.after_run)
            self._wake.notify()

    def run(self, stop: threading.Event) -> None:
        while not stop.is_set():
            with self._wake:
                pause = self.next_at - self.clock()
                if pause > 0:
                    self._wake.wait(timeout=min(pause, 1.0))
                    continue
                self.next_at = self.clock() + self.interval
            self.poll_once()
