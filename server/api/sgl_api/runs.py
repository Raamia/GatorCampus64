"""Verified runs and leaderboards (docs/web_platform_spec.md §10.1-§10.2).

A `run` event is always stored (table `runs`); it is ranked only when it passes validation and every
player resolves to a Gator Pass link from the current server session. Invalid runs never make the
bridge's POST fail: the reason is stored instead (schema.sql lists the reasons).
"""
from __future__ import annotations

import hashlib
import re
import uuid
from typing import Any

from .missions import MISSIONS

MAX_FRAMES = 30 * 60 * 60     # 1 h at 30 fps: anything longer is a stuck clock
MAX_PLAYERS = 16              # coopdx MAX_PLAYERS
CLOCK_TOLERANCE = 60          # |frames - client_frames| allowed: 2 s at 30 fps
TOP_DEFAULT = 5               # rows per mission in GET /leaderboards
LIMIT_MAX = 50                # GET /leaderboards/{mission}?limit=


def _int(v: Any) -> int | None:
    """An integer field from the Lua JSON encoder (integers, or floats with no fraction)."""
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float) and v.is_integer():
        return int(v)
    if isinstance(v, str) and re.fullmatch(r"-?\d{1,9}", v.strip()):
        return int(v)
    return None


def player_tag(sub: str) -> str:
    """A stable public tag for a Gator Pass account that does not reveal the Auth0 subject."""
    return "GP-" + hashlib.sha256(f"sgl-player:{sub}".encode()).hexdigest()[:8].upper()


def parse(f: dict) -> dict:
    """Validate a run event's fields. Returns the row to store (without subs), reason set when the
    run can never be ranked; player linking happens afterwards (store())."""
    mission = str(f.get("mission") or "")[:64]
    frames, client_frames = _int(f.get("frames")), _int(f.get("client_frames"))
    retries = _int(f.get("retries")) if f.get("retries") is not None else 0
    n = _int(f.get("players"))
    row: dict[str, Any] = {"mission": mission, "frames": frames, "client_frames": client_frames,
                           "retries": max(0, min(retries or 0, 1_000_000)), "players": 0, "gis": [],
                           "names": [], "level": _int(f.get("level")), "act": _int(f.get("act")),
                           "reason": None}
    # the players, as far as they parse (stored even when the run is invalid)
    gis, names = [], []
    i = 1
    while i <= MAX_PLAYERS + 1 and (f"gi{i}" in f or f"name{i}" in f):
        gis.append(_int(f.get(f"gi{i}")))
        names.append(str(f.get(f"name{i}") or "")[:64])
        i += 1
    row["players"] = n if n is not None and 0 <= n <= 32767 else len(gis)
    row["gis"] = [g if g is not None and 0 <= g <= 32767 else None for g in gis]
    row["names"] = names

    def bad(reason: str) -> dict:
        row["reason"] = reason
        return row

    if mission not in MISSIONS:
        return bad("unknown_mission")
    if frames is None or client_frames is None or retries is None or retries < 0 or n is None:
        return bad("bad_fields")
    if not 0 < frames <= MAX_FRAMES or not 0 < client_frames <= MAX_FRAMES:
        return bad("out_of_range")
    if abs(frames - client_frames) > CLOCK_TOLERANCE:
        return bad("clock_mismatch")
    if frames < MISSIONS[mission]["floor_frames"]:
        return bad("below_floor")
    if not 1 <= n <= MAX_PLAYERS or len(gis) != n or any(g is None for g in row["gis"]) or not all(names):
        return bad("player_count")
    if len(set(row["gis"])) != n:
        return bad("player_count")
    return row


def resolve_link(c, gi: int, name: str, fields: dict, bridge_sub: str | None) -> dict | None:
    """Use the login captured by the bridge at event creation, never a newer login.

    Legacy events without an explicit identity remain stored but unranked. Receipt
    order, player names and global indices alone are not an authentication proof.
    """
    identities = fields.get("identities")
    identity = identities.get(str(gi)) if isinstance(identities, dict) else None
    if not isinstance(identity, dict) or identity.get("name") != name:
        return None
    if type(identity.get("link_id")) is not int or not 0 < identity["link_id"] < 2**63:
        return None
    try:
        session = uuid.UUID(str(fields.get("session_id")))
        connection = uuid.UUID(str(identity.get("connection_id")))
        if uuid.UUID(str(identity.get("session_id"))) != session:
            return None
    except ValueError:
        return None
    return c.execute(
        """SELECT l.sub, u.nickname FROM links l JOIN users u ON u.sub = l.sub
            WHERE l.id = %s AND l.gi = %s AND l.coopdx_name = %s
              AND l.session_id = %s AND l.connection_id = %s AND l.bridge_sub = %s""",
        (identity["link_id"], gi, name, session, connection, bridge_sub)).fetchone()


def store(c, fields: dict, event_id: int | None, bridge_sub: str | None = None) -> dict:
    """Validate, link and insert one run (inside the caller's transaction). Ranked runs also get an
    outbox row for the DeepSpace push. Returns {id, ranked, reason}."""
    row = parse(fields)
    subs: list[str | None] = [None] * len(row["gis"])
    player_key = None
    if row["reason"] is None:
        for i, (gi, name) in enumerate(zip(row["gis"], row["names"])):
            link = resolve_link(c, gi, name, fields, bridge_sub)
            subs[i] = link["sub"] if link else None
        if any(s is None for s in subs):
            row["reason"] = "unlinked"
        elif len(set(subs)) != len(subs):
            row["reason"] = "duplicate_player"
        else:
            player_key = " ".join(sorted(subs))
    ranked = row["reason"] is None
    r = c.execute(
        """INSERT INTO runs (mission, frames, client_frames, retries, players, gis, names, subs, coop, level, act,
                             ranked, reason, player_key, event_id)
           VALUES (%(mission)s, %(frames)s, %(client_frames)s, %(retries)s, %(players)s, %(gis)s, %(names)s,
                   %(subs)s, %(coop)s, %(level)s, %(act)s, %(ranked)s, %(reason)s, %(player_key)s, %(event_id)s)
           RETURNING id, uid""",
        {**row, "subs": subs, "coop": row["players"] > 1, "ranked": ranked, "player_key": player_key,
         "event_id": event_id}).fetchone()
    if ranked:
        c.execute("INSERT INTO run_pushes (run_id) VALUES (%s) ON CONFLICT DO NOTHING", (r["id"],))
    return {"id": r["id"], "uid": str(r["uid"]), "mission": row["mission"], "ranked": ranked, "reason": row["reason"]}


# Display names: the linked nickname, else the coopdx name the player had in the run.
_DISPLAY = """ARRAY(SELECT COALESCE(NULLIF(u.nickname, ''), p.name)
                     FROM unnest(b.subs, b.names) WITH ORDINALITY AS p(sub, name, i)
                     LEFT JOIN users u ON u.sub = p.sub ORDER BY p.i)"""


def boards(c, missions: list[str], limit: int) -> dict[str, list[dict]]:
    """Top `limit` ranked rows per mission, best run per player set; ties go to the earlier run."""
    rows = c.execute(
        f"""WITH best AS (
                SELECT DISTINCT ON (mission, player_key) id, mission, frames, retries, players, subs, names, created
                  FROM runs WHERE ranked AND mission = ANY(%s)
                 ORDER BY mission, player_key, frames, created, id),
            ranked AS (
                SELECT b.*, row_number() OVER (PARTITION BY mission ORDER BY frames, created, id) AS rank FROM best b)
            SELECT b.rank, b.mission, b.frames, b.retries, b.players, b.created, {_DISPLAY} AS names
              FROM ranked b WHERE b.rank <= %s ORDER BY b.mission, b.rank""",
        (missions, limit)).fetchall()
    out: dict[str, list[dict]] = {m: [] for m in missions}
    for r in rows:
        out[r["mission"]].append({"rank": r["rank"], "names": r["names"], "frames": r["frames"],
                                  "retries": r["retries"], "players": r["players"], "at": r["created"]})
    return out


def push_payload(c, run_id: int) -> dict | None:
    """The body sent to the DeepSpace app's ingestVerifiedRun (§10.4) for a ranked run."""
    b = c.execute(f"SELECT b.*, {_DISPLAY} AS display FROM runs b WHERE b.id = %s AND b.ranked", (run_id,)).fetchone()
    if not b:
        return None
    m = MISSIONS.get(b["mission"], {})
    return {
        "v": 1,
        "runId": str(b["uid"]),
        "missionId": b["mission"],
        "missionTitle": m.get("title", b["mission"]),
        "frames": b["frames"],
        "retries": b["retries"],
        "coop": b["coop"],
        "players": [{"name": name, "tag": player_tag(sub)} for name, sub in zip(b["display"], b["subs"])],
        "level": b["level"],
        "act": b["act"],
        "createdAt": b["created"].isoformat(),
    }
