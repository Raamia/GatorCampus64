"""Answer game questions from game_guide.md, locally (no AI call).

Guide.match(question) scores every entry of the guide against the question: IDF-weighted word overlap
with the entry's `ask:` phrasings (and its heading), after lowercasing, dropping filler words, a small
synonym table and a light suffix stemmer. Bridge.poll (bridge.py) routes on the best score:
  >= ANSWER   answer from the guide (Guide.answer fills the live-stat placeholders)
  >= RELATED  a game-ish question the guide doesn't cover well: Gemini, grounded in the closest entries
  below       general knowledge / small talk: Gemini with the NPC's persona
"""
import math
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
GUIDE = os.path.join(HERE, "game_guide.md")
ANSWER = 0.55
RELATED = 0.25

STOP = set("""a an the and or but if of to in on at by for with from into onto about as is are was were be been being
am do does did doing done have has had having i me mine im ive your youre we us our they them their it its
this that these those there here what whats which whom whose how hows when where wheres why can could would should
will shall may might must just so very really please tell show give get got gonna wanna want need know let lets
some any all out up down off over again then than too also not no yes ok okay hey hi hello yo albert libby professor
bob thanks thank one""".split())
# kept on purpose: numbers, "my", "who", "you", "act", "door", "star", "level", "next", "first" (they carry meaning here)

SYNONYMS = {
    "entrance": "door", "entry": "door", "doors": "door", "gate": "door",
    "unlock": "open", "unlocked": "open", "opens": "open", "opening": "open",
    "stage": "level", "stages": "level", "course": "level", "courses": "level",
    "lvl": "level", "map": "level", "mission": "act", "missions": "act", "task": "act", "tasks": "act",
    "quest": "act", "quests": "act", "challenge": "act", "challenges": "act", "objective": "act",
    "complete": "finish", "beat": "finish", "clear": "finish", "solve": "finish", "pass": "finish",
    "1up": "1-up", "oneup": "1-up", "life": "lives", "health": "lives",
    "char": "character", "skin": "character", "avatar": "character", "model": "character",
    "multiplayer": "coop", "co": "coop", "op": "coop", "friend": "friends", "buddy": "friends",
    "teleport": "warp", "tp": "warp", "keybind": "controls", "keybinds": "controls", "keys": "controls",
    "lib": "library", "west": "west", "libwest": "library west", "alice": "alice", "lake": "lake",
    "reitz": "reitz", "swamp": "swamp", "marston": "marston", "stadium": "stadium",
    "highscore": "leaderboard", "highscores": "leaderboard", "ranking": "leaderboard", "rankings": "leaderboard",
}

PLACEHOLDERS = {"player", "stars", "lives", "coins", "here", "character", "players", "next_hint", "stage_stars"}
STAGE_KEYS = ("swamp", "reitz", "alice", "marston", "libwest")
STAGE_NAMES = {"swamp": "The Swamp", "reitz": "Reitz & Engineering", "alice": "Lake Alice",
               "marston": "Marston", "libwest": "Library West"}


def stem(w):
    if len(w) > 5 and w.endswith("ing"):
        w = w[:-3]
    elif len(w) > 4 and w.endswith("ies"):
        w = w[:-3] + "y"
    elif len(w) > 4 and w.endswith("ed") and not w.endswith("eed"):
        w = w[:-2]
    elif len(w) > 3 and w.endswith("s") and not w.endswith("ss") and not w.endswith("us"):
        w = w[:-1]
    return w


def tokens(text):
    text = text.lower().replace("'", "").replace("1-up", "1up").replace("1 up", "1up").replace("d-pad", "dpad")
    text = text.replace("d pad", "dpad").replace("co-op", "coop").replace("co op", "coop")
    out = []
    for w in re.findall(r"[a-z0-9]+", text):
        if w in STOP:
            continue
        w = SYNONYMS.get(w, w)
        for part in w.split():
            out.append(stem(part))
    return out


class Entry:
    def __init__(self, eid, title, section, asks, answer, npc=None):
        self.id, self.title, self.section, self.asks, self.answer = eid, title, section, asks, answer
        self.npc = npc   # only this NPC answers with it (e.g. "who are you"), None = everyone
        self.phrases = [set(tokens(p)) for p in [title] + asks]
        self.phrases = [p for p in self.phrases if p]
        self.vocab = set().union(*self.phrases) if self.phrases else set()


def parse(text):
    """game_guide.md -> [Entry]. Raises ValueError on a malformed entry (tests and check_game_guide.py)."""
    entries, section, cur = [], "", None

    def close():
        if cur is None:
            return
        missing = [k for k in ("id", "ask", "answer") if not cur.get(k)]
        if missing:
            raise ValueError("guide entry %r is missing %s" % (cur["title"], ", ".join(missing)))
        asks = [a.strip() for a in cur["ask"].split(",") if a.strip()]
        entries.append(Entry(cur["id"], cur["title"], section, asks, cur["answer"], cur.get("npc") or None))

    for line in text.splitlines():
        if line.startswith("## "):
            close()
            cur = None
            section = line[3:].strip()
        elif line.startswith("### "):
            close()
            cur = {"title": line[4:].strip()}
        elif cur is not None:
            m = re.match(r"^(id|ask|answer|npc):\s*(.*)$", line)
            if m:
                cur[m.group(1)] = m.group(2).strip()
    close()
    ids = [e.id for e in entries]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        raise ValueError("duplicate guide ids: %s" % ", ".join(sorted(dup)))
    return entries


def door_phrase(building):
    """ "UNIVERSITY AUDITORIUM" -> "the University Auditorium door", "THE HUB" -> "The Hub door" (as levels.lua)"""
    name = building.title()
    return (name if name.startswith("The ") else "the " + name) + " door"


def next_hint(stats):
    go, lock = stats.get("go", ""), stats.get("lock", "")
    parts = []
    if go:
        name, _, building = go.partition("|")
        parts.append("Head to %s for %s!" % (door_phrase(building), name.title()))
    if lock:
        name, _, rest = lock.partition("|")
        building, _, need = rest.partition("|")
        try:
            more = int(need) - int(stats.get("stars", "0"))
        except ValueError:
            more = 0
        if more > 0:
            parts.append("%s (%s) opens at %s stars: %d more to go." % (name.title(), door_phrase(building), need, more))
    if not parts:
        if "stars" in stats:
            parts.append("Every stage door is open and you've got every star you can get right now. Amazing!")
        else:
            parts.append("Walk into the University Auditorium door, south of the spawn, to start with The Swamp.")
    return " ".join(parts)


def fill(answer, player, stats):
    """Replace {placeholders} with live values from the game (stats: the request's key=value pairs)."""
    def stage_stars(key=None):
        keys = [key] if key else STAGE_KEYS
        out = []
        for k in keys:
            v = stats.get("s_" + k)
            if v is not None:
                out.append("%s %s" % (STAGE_NAMES.get(k, k), v) if not key else v)
        return ", ".join(out) if out else "(not known yet)"

    values = {
        "player": player or "friend",
        "stars": stats.get("stars", "?"),
        "lives": stats.get("lives", "?"),
        "coins": stats.get("coins", "?"),
        "here": stats.get("here", "somewhere on campus").title(),
        "character": stats.get("char") or "yourself",
        "players": stats.get("players", "?"),
        "next_hint": next_hint(stats),
    }

    def sub(m):
        name, _, arg = m.group(1).partition(":")
        if name == "stage_stars":
            return stage_stars(arg or None)
        return str(values.get(name, m.group(0)))
    return re.sub(r"\{([a-z_]+(?::[a-z]+)?)\}", sub, answer)


class Guide:
    def __init__(self, path=GUIDE, text=None):
        if text is None:
            with open(path) as f:
                text = f.read()
        self.entries = parse(text)
        df = {}
        for e in self.entries:
            for t in e.vocab:
                df[t] = df.get(t, 0) + 1
        n = len(self.entries)
        self.idf = {t: math.log(1 + n / d) for t, d in df.items()}
        self.unknown_idf = math.log(1 + n)   # a word the guide never uses weighs like the rarest word

    def w(self, toks):
        return sum(self.idf.get(t, self.unknown_idf) for t in toks)

    def score(self, q, e):
        if not q:
            return 0.0
        wq = self.w(q)
        best = 0.0
        for p in e.phrases:
            hit = q & p
            if not hit:
                continue
            wh = self.w(hit)
            # all of the phrase, and as much of the question as possible: a one-word phrase that matches one
            # word of a long unrelated question ("tallest building in the world") stays low
            best = max(best, (wh / self.w(p)) * math.sqrt(wh / wq))
        # words of the question found anywhere in the entry (helps long questions)
        cover = self.w(q & e.vocab) / wq
        return max(best, 0.75 * cover)

    def match(self, question, k=3, npc=None):
        """-> [(score, Entry)] best first (top k); entries tied to another NPC are skipped."""
        q = set(tokens(question))
        ranked = sorted(((self.score(q, e), e) for e in self.entries if e.npc in (None, npc)),
                        key=lambda se: -se[0])
        return ranked[:k]

    def answer(self, entry, player, stats):
        return fill(entry.answer, player, stats)

    def context(self, ranked):
        """Grounding notes for Gemini (the closest entries, placeholders left out)."""
        lines = []
        for _, e in ranked:
            text = re.sub(r"\{[a-z_:]+\}", "", e.answer).strip()
            lines.append("- %s %s" % (e.title, text))
        return "\n".join(lines)


def check_placeholders(entries):
    """Unknown {names} in answers -> list of (id, name)."""
    bad = []
    for e in entries:
        for m in re.finditer(r"\{([a-z_]+)(?::([a-z]+))?\}", e.answer):
            name, arg = m.group(1), m.group(2)
            if name not in PLACEHOLDERS or (arg and (name != "stage_stars" or arg not in STAGE_KEYS)):
                bad.append((e.id, m.group(0)))
    return bad
