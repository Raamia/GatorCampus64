"""NPC chat bridge for Super Gatorlator 64: carries chat between the game and the NPCs' answers.

Game questions are answered locally from game_guide.md (guide.py, no AI call); everything else
(general knowledge, small talk) goes to Gemini. Questions about the game the guide doesn't cover well go
to Gemini grounded in the closest guide entries, and are logged to unanswered.log for new entries.

sm64coopdx's Lua cannot open sockets or make web requests, but a mod can read and write "modfs" files
(zip archives in the game's sav folder), and mod_fs_reload() re-reads one from disk. So the host runs
this script beside the game:

  game  -> sav/sgl64.modfs      npc_out.txt  (written by mods/sgl64/sgl_npc.lua on the host)
  here  -> sav/sgl64_npc.modfs  replies.txt  (public, so the mod may read it; written atomically)

Each side only writes its own file. Both files are tab-separated lines (backslash, tab and newline
escaped as \\\\ \\t \\n):
  npc_out.txt   "session\\t<sid>" then one "<seq>\\t<npc id>\\t<player>\\t<message>\\t<stats>" per pending request
                (<stats>: "key=value;key=value" from the game: stars, lives, coins, here, char, players, go, lock,
                s_<stage>; see sgl_npc.lua)
  replies.txt   "session\\t<sid>" then one "<seq>\\t<npc id>\\t<reply>" per recent reply
<sid> changes every time the mod loads; <seq> counts up within a session.

On the hosted server (play.gatorcamp.us) this script doesn't run: sgl64.modfs is server/bridge's inbox there, so
the headless host prints each request as an `npc_ask` SGLEVT line instead, and server/bridge/sglbridge/npc.py
answers it with this module's Bridge.handle(), writing the same replies.txt.

Usage (from anywhere):
  python3 tools/npc_bridge/bridge.py               Gemini replies (GEMINI_API_KEY in the environment or
                                                   tools/npc_bridge/.env; free key: aistudio.google.com/apikey)
  python3 tools/npc_bridge/bridge.py --fake        canned replies, no API key needed
  python3 tools/npc_bridge/bridge.py --once ...    handle what is pending once, then exit
"""
import argparse
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
import zipfile

import guide as guide_mod

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_MODFS = "sgl64.modfs"         # the mod's own modfs (modPath "sgl64")
OUT_FILE = "npc_out.txt"
IN_MODFS = "sgl64_npc.modfs"      # read by the mod with mod_fs_reload("sgl64_npc")
IN_FILE = "replies.txt"
KEEP_REPLIES = 16                 # replies kept in replies.txt (the game skips the ones it has shown)
MAX_REPLY = 600                   # characters; the bubble shows the first ~200 (sgl_npc.lua), chat shows it all
UNANSWERED = os.path.join(HERE, "unanswered.log")
DEFAULT_MODEL = "gemini-3.8-flash"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent"


def default_sav_dir():
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/sm64coopdx/sav")
    if os.name == "nt":
        return os.path.join(os.environ.get("APPDATA", ""), "sm64coopdx", "sav")
    return os.path.expanduser("~/.local/share/sm64coopdx/sav")


def escape(text):
    return text.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "")


def unescape(text):
    out, i = [], 0
    while i < len(text):
        c = text[i]
        if c == "\\" and i + 1 < len(text):
            out.append({"t": "\t", "n": "\n", "\\": "\\"}.get(text[i + 1], text[i + 1]))
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def clean_reply(text):
    """One line of plain ASCII the in-game font can draw; no backslashes (djui colour codes)."""
    for a, b in (("\u2018", "'"), ("\u2019", "'"), ("\u201c", '"'), ("\u201d", '"'), ("\u2014", "-"),
                 ("\u2013", "-"), ("\u2026", "..."), ("\\", "/"), ("*", ""), ("\n", " "), ("\t", " ")):
        text = text.replace(a, b)
    text = "".join(c for c in text if 32 <= ord(c) < 127)
    text = " ".join(text.split())
    if len(text) > MAX_REPLY:
        cut = text[:MAX_REPLY]
        end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
        text = cut[:end + 1] if end > 40 else cut.rstrip() + "..."
    return text


def parse_stats(text):
    """ "stars=3;lives=4;here=THE HUB" -> {"stars": "3", ...} """
    out = {}
    for pair in unescape(text).split(";"):
        k, sep, v = pair.partition("=")
        if sep and k.strip():
            out[k.strip()] = v.strip()
    return out


def parse_requests(text):
    """npc_out.txt -> (session, [(seq, npc, player, message, stats), ...])."""
    session, reqs = None, []
    for line in text.splitlines():
        parts = line.split("\t")
        if parts[0] == "session" and len(parts) >= 2:
            session = parts[1]
        elif len(parts) >= 4 and parts[0].isdigit():
            stats = parse_stats(parts[4]) if len(parts) >= 5 else {}
            reqs.append((int(parts[0]), parts[1], unescape(parts[2]), unescape(parts[3]), stats))
    return session, reqs


def format_replies(session, replies):
    lines = ["session\t" + session]
    lines += ["%d\t%s\t%s" % (seq, npc, escape(text)) for seq, npc, text in replies[-KEEP_REPLIES:]]
    return "\n".join(lines) + "\n"


def read_requests(sav_dir):
    """The game's pending requests, or (None, []) when there is no (complete) outbox yet."""
    path = os.path.join(sav_dir, OUT_MODFS)
    try:
        with zipfile.ZipFile(path) as z:
            return parse_requests(z.read(OUT_FILE).decode("utf-8", "replace"))
    except (OSError, KeyError, zipfile.BadZipFile):
        return None, []   # not written yet, or caught half-written: try again next poll


def write_replies(sav_dir, session, replies):
    """Atomically replace sgl64_npc.modfs (a modfs zip that other mods may read: isPublic)."""
    os.makedirs(sav_dir, exist_ok=True)
    path = os.path.join(sav_dir, IN_MODFS)
    tmp = path + ".tmp"
    props = {"isPublic": True, "files": {IN_FILE: {"isPublic": True, "isText": True}}}
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(IN_FILE, format_replies(session, replies))
        z.writestr("properties.json", json.dumps(props))
    os.replace(tmp, path)


class FakeReplier:
    """Canned in-character lines from npcs.json (no network)."""

    def __init__(self, cast):
        self.cast = cast
        self.turn = {}

    def reply(self, npc, player, message, history, context=None):
        lines = self.cast["npcs"].get(npc, {}).get("fake") or ["Hi, %s!"]
        k = self.turn.get(npc, random.randrange(len(lines)))
        self.turn[npc] = (k + 1) % len(lines)
        return lines[k].replace("%s", player)


class GeminiReplier:
    """In-character replies from the Gemini API (generateContent, standard library HTTP)."""

    def __init__(self, cast, api_key, model=DEFAULT_MODEL, thinking="low", timeout=20, urlopen=urllib.request.urlopen):
        self.cast = cast
        self.api_key = api_key
        self.model = model
        self.thinking = thinking      # None: leave thinking at the model's default
        self.timeout = timeout
        self.urlopen = urlopen

    def system_prompt(self, npc, context=None):
        c = self.cast
        parts = [c["rules"], c["npcs"][npc]["persona"], c["world"]]
        if context:
            parts.append("Notes from the official game guide that may help with this question:\n" + context +
                         "\nUse only these notes for facts about the game. If they don't answer it, say you're "
                         "not sure about that part and suggest asking about something else; never invent game details.")
        return "\n\n".join(parts)

    def body(self, npc, player, message, history, context=None):
        contents = []
        for role, text in history:
            contents.append({"role": role, "parts": [{"text": ("%s says: %s" % (player, text)) if role == "user" else text}]})
        contents.append({"role": "user", "parts": [{"text": "%s says: %s" % (player, message)}]})
        config = {"maxOutputTokens": 1024, "temperature": 1.0}
        if self.thinking:
            config["thinkingConfig"] = {"thinkingLevel": self.thinking}
        return {"systemInstruction": {"parts": [{"text": self.system_prompt(npc, context)}]},
                "contents": contents, "generationConfig": config}

    def post(self, body):
        req = urllib.request.Request(GEMINI_URL % self.model, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key})
        with self.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode())

    def reply(self, npc, player, message, history, context=None):
        body = self.body(npc, player, message, history, context)
        try:
            data = self.post(body)
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")
            if e.code == 400 and self.thinking and "thinking" in detail.lower():
                self.thinking = None   # this model takes no thinking level: drop it from now on
                body["generationConfig"].pop("thinkingConfig", None)
                data = self.post(body)
            else:
                raise RuntimeError("Gemini HTTP %d: %s" % (e.code, detail[:300]))
        cands = data.get("candidates") or []
        parts = (cands[0].get("content") or {}).get("parts") or [] if cands else []
        text = " ".join(p.get("text", "") for p in parts if not p.get("thought"))
        if not text.strip():   # blocked or empty: stay in character instead of going silent
            return "Hmm, let's talk about something else, %s!" % player
        return text


def load_api_key(path=os.path.join(HERE, ".env")):
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key or not os.path.exists(path):
        return key
    with open(path) as f:
        for line in f:
            name, _, value = line.strip().partition("=")
            if name.strip() == "GEMINI_API_KEY":
                return value.strip().strip("'\"")
    return ""


class Bridge:
    def __init__(self, sav_dir, replier, cast, log=print, guide=None, unanswered=UNANSWERED):
        self.sav_dir = sav_dir
        self.replier = replier
        self.cast = cast
        self.log = log
        self.guide = guide              # guide_mod.Guide, or None to send everything to the replier
        self.unanswered = unanswered    # log file of game questions the guide couldn't answer (None: off)
        self.session = None
        self.done = 0          # highest seq answered in this session
        self.replies = []      # (seq, npc, text), newest last
        self.history = {}      # (player, npc) -> [(role, text), ...]

    def poll(self):
        """Answer every new request in the game's outbox; returns how many were answered."""
        session, reqs = read_requests(self.sav_dir)
        if session is None:
            return 0
        return self.handle(session, reqs)

    def handle(self, session, reqs):
        """Answer the new ones of reqs [(seq, npc, player, message, stats), ...] from game session `session` and
        rewrite the replies file; returns how many were answered. (On the hosted server, server/bridge calls this
        for each npc_ask event instead of poll(): there sgl64.modfs is its inbox.)"""
        if session != self.session:   # the mod (re)loaded: start over
            self.session, self.done, self.replies = session, 0, []
        answered = 0
        for seq, npc, player, message, stats in sorted(reqs, key=lambda r: r[0]):
            if seq <= self.done:
                continue
            self.done = seq
            if npc not in self.cast["npcs"]:
                self.log("[npc] unknown npc id %r, skipped" % npc)
                continue
            hist = self.history.setdefault((player, npc), [])
            try:
                text, route = self.answer(npc, player, message, stats, hist)
                text = clean_reply(text)
            except Exception as e:   # network/API trouble: the game shows its own "lost in thought" line
                self.log("[npc] %s -> %s failed: %s" % (player, npc, e))
                continue
            if not text:
                continue
            hist += [("user", message), ("model", text)]
            del hist[:-12]   # the last 6 exchanges
            self.replies.append((seq, npc, text))
            answered += 1
            self.log("[npc] %s -> %s: %s\n      [%s] %s: %s" % (player, npc, message, route,
                                                             self.cast["npcs"][npc]["name"], text))
        if answered:
            write_replies(self.sav_dir, self.session, self.replies)
        return answered

    def answer(self, npc, player, message, stats, hist):
        """-> (reply text, route label). Guide first; the replier (Gemini or fake) for everything else."""
        if self.guide is None:
            return self.replier.reply(npc, player, message, hist), "ai"
        ranked = self.guide.match(message, npc=npc)
        score, entry = ranked[0] if ranked else (0.0, None)
        if entry is not None and score >= guide_mod.ANSWER:
            flair = self.cast["npcs"][npc].get("guide_flair") or [""]
            return random.choice(flair) + self.guide.answer(entry, player, stats), "guide: %s %.2f" % (entry.id, score)
        if entry is not None and score >= guide_mod.RELATED:
            self.note_unanswered(player, message, entry.id, score)
            ctx = self.guide.context(ranked)
            return self.replier.reply(npc, player, message, hist, context=ctx), "ai+guide: near %s %.2f" % (entry.id, score)
        return self.replier.reply(npc, player, message, hist), "ai"

    def note_unanswered(self, player, message, near, score):
        if not self.unanswered:
            return
        try:
            with open(self.unanswered, "a") as f:
                f.write("%s\t%s\t%s\tnear %s %.2f\n" % (time.strftime("%Y-%m-%d %H:%M"), player, message, near, score))
        except OSError:
            pass


def load_cast(path=os.path.join(HERE, "npcs.json")):
    with open(path) as f:
        return json.load(f)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fake", action="store_true", help="canned replies, no API key needed")
    ap.add_argument("--model", default=DEFAULT_MODEL, help="Gemini model id (default %(default)s)")
    ap.add_argument("--thinking", default="low", help="Gemini thinking level: low, medium, high, or none")
    ap.add_argument("--sav-dir", default=default_sav_dir(), help="sm64coopdx's sav folder")
    ap.add_argument("--interval", type=float, default=0.25, help="seconds between polls")
    ap.add_argument("--once", action="store_true", help="handle pending requests once, then exit")
    args = ap.parse_args(argv)

    cast = load_cast()
    if args.fake:
        replier, mode = FakeReplier(cast), "fake replies"
    else:
        key = load_api_key()
        if not key:
            print("[npc] no GEMINI_API_KEY: set it in the environment or in tools/npc_bridge/.env\n"
                  "      (free key: https://aistudio.google.com/apikey), or run with --fake")
            return 1
        thinking = None if args.thinking.lower() == "none" else args.thinking
        replier, mode = GeminiReplier(cast, key, args.model, thinking), "Gemini " + args.model
    guide = guide_mod.Guide()
    bridge = Bridge(args.sav_dir, replier, cast, guide=guide)
    print("[npc] bridge up (%s; game guide: %d entries), watching %s" % (mode, len(guide.entries), args.sav_dir))
    while True:
        bridge.poll()
        if args.once:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
