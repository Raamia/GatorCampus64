"""NPC chat on the hosted server: Albert and Alberta (mods/sgl64/sgl_npc.lua, tools/npc_bridge/).

On a player's machine tools/npc_bridge/bridge.py reads the mod's requests from sav/sgl64.modfs (npc_out.txt).
Here that file is this bridge's inbox (inbox.py rewrites it whole, and the mod reloads it every second), so a
second writer would lose requests and could put back a stale inbox.json. Instead the headless host prints each
request as an event:

  SGLEVT {"t":"npc_ask","gi":0,"name":"Campus","npc":"albert","player":"Alberta","seq":3,"session":"...",
          "stats":"stars=3;lives=4;...","text":"how do I unlock lake alice"}

and this service answers it with tools/npc_bridge's own code (game_guide.md first, Gemini for the rest), writing
the reply where the mod already looks: <savepath>/sav/sgl64_npc.modfs (replies.txt). Answers can take seconds
(Gemini), so they run on their own thread and the game's stdout is never held up. npc_ask events stay here:
player chat is not forwarded to the API.
"""
from __future__ import annotations

import importlib.util
import logging
import queue
import sys
import threading
from pathlib import Path
from typing import Any

log = logging.getLogger("sglbridge.npc")

# the repo checkout the bridge runs from (/opt/sgl): tools/npc_bridge next to server/bridge
REPO_NPC_DIR = Path(__file__).resolve().parents[3] / "tools" / "npc_bridge"
MAX_TEXT = 300            # sgl_npc.lua host_enqueue cuts questions to 300 characters too
MAX_STATS = 2000


def load_npc_bridge(npc_dir: str | Path) -> Any:
    """tools/npc_bridge/bridge.py as a module (named sgl_npc_bridge: server/bridge has its own bridge.py)."""
    npc_dir = Path(npc_dir)
    if str(npc_dir) not in sys.path:
        sys.path.append(str(npc_dir))       # for its `import guide`; appended so nothing here is shadowed
    spec = importlib.util.spec_from_file_location("sgl_npc_bridge", npc_dir / "bridge.py")
    if spec is None or spec.loader is None:
        raise ImportError(f"no npc bridge in {npc_dir}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def parse_ask(ev: dict[str, Any]) -> tuple[str, tuple[int, str, str, str, str]] | None:
    """An npc_ask event -> (session, (seq, npc, player, text, stats)), or None when it is malformed."""
    session, seq, npc, text = ev.get("session"), ev.get("seq"), ev.get("npc"), ev.get("text")
    player = ev.get("player") or ev.get("name") or "someone"
    stats = ev.get("stats") or ""
    if not (isinstance(session, str) and session and isinstance(seq, int) and not isinstance(seq, bool)
            and isinstance(npc, str) and npc and isinstance(text, str) and text.strip()
            and isinstance(player, str) and isinstance(stats, str)):
        return None
    return session, (seq, npc, player[:64], text[:MAX_TEXT], stats[:MAX_STATS])


class NpcService:
    """Queues npc_ask events and answers them one at a time on its own thread."""

    def __init__(self, answerer: Any, parse_stats: Any, max_queue: int = 32):
        self.answerer = answerer            # tools/npc_bridge Bridge (handle(session, reqs))
        self.parse_stats = parse_stats      # tools/npc_bridge parse_stats ("k=v;k=v" -> dict)
        self.queue: queue.Queue[tuple[str, tuple[int, str, str, str, str]]] = queue.Queue(max_queue)

    def ask(self, ev: dict[str, Any]) -> bool:
        req = parse_ask(ev)
        if req is None:
            log.warning("malformed npc_ask event dropped: %s", ev)
            return False
        try:
            self.queue.put_nowait(req)
        except queue.Full:
            log.warning("npc queue full, dropped %s's question (the mascot will say 'ask me again')", req[1][2])
            return False
        return True

    def reset(self) -> None:
        """The game (re)started: its old session's questions are moot."""
        while True:
            try:
                self.queue.get_nowait()
            except queue.Empty:
                return

    def answer_one(self, session: str, req: tuple[int, str, str, str, str]) -> int:
        seq, npc, player, text, stats = req
        try:
            return self.answerer.handle(session, [(seq, npc, player, text, self.parse_stats(stats))])
        except Exception:                   # never let one bad answer stop the thread
            log.exception("npc answer failed (%s -> %s)", player, npc)
            return 0

    def run(self, stop: threading.Event) -> None:
        while not stop.is_set():
            try:
                session, req = self.queue.get(timeout=0.5)
            except queue.Empty:
                continue
            self.answer_one(session, req)


def build(cfg: Any) -> NpcService | None:
    """The service for this config, or None when NPC chat is off (SGL_NPC=0 or no tools/npc_bridge)."""
    if not cfg.npc:
        log.info("NPC chat off (SGL_NPC=0)")
        return None
    npc_dir = Path(cfg.npc_dir)
    if not (npc_dir / "bridge.py").is_file():
        log.warning("NPC chat off: no %s (copy tools/npc_bridge/ next to server/bridge)", npc_dir / "bridge.py")
        return None
    nb = load_npc_bridge(npc_dir)
    cast = nb.load_cast(str(npc_dir / "npcs.json"))
    if cfg.npc_fake or not cfg.gemini_api_key:
        if not cfg.npc_fake:
            log.warning("NPC chat: no GEMINI_API_KEY, so game questions come from the guide and the rest get canned lines")
        replier, mode = nb.FakeReplier(cast), "canned lines"
    else:
        thinking = None if cfg.npc_thinking.lower() == "none" else cfg.npc_thinking
        replier, mode = nb.GeminiReplier(cast, cfg.gemini_api_key, cfg.npc_model, thinking), "Gemini " + cfg.npc_model
    guide = nb.guide_mod.Guide(str(npc_dir / "game_guide.md"))
    unanswered = Path(cfg.state_dir) / "npc_unanswered.log"
    unanswered.parent.mkdir(parents=True, exist_ok=True)
    answerer = nb.Bridge(str(Path(cfg.savepath) / "sav"), replier, cast, log=log.info, guide=guide,
                         unanswered=str(unanswered))
    log.info("NPC chat on (%s; game guide: %d entries; unanswered questions: %s)", mode, len(guide.entries), unanswered)
    return NpcService(answerer, nb.parse_stats)
