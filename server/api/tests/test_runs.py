"""Verified runs (§10.1-§10.2): validation, linking, leaderboards, and the DeepSpace outbox (§10.4)."""
import hashlib
import hmac
import json

import httpx
import pytest

from sgl_api import deepspace, runs
from sgl_api.missions import MISSIONS

SECRET = "test-ingest-secret-0123456789abcdef"
APP_URL = "https://board.example.app.space"


def run_ev(mission="swamp_sprint", frames=1200, client_frames=None, players=(("1", "Ali"),), retries=0, **extra):
    """A `run` event in the bridge's shape ({t, payload, at} + the fields at the top level)."""
    f = {"mission": mission, "frames": frames, "client_frames": frames if client_frames is None else client_frames,
         "retries": retries, "level": 9, "act": 2, "players": len(players)}
    for i, (gi, name) in enumerate(players, 1):
        f[f"gi{i}"], f[f"name{i}"] = int(gi), name
    f.update(extra)
    return {"t": "run", "payload": {"t": "run", **f}, "at": "2026-10-17T12:00:00Z", **f}


def link(client, bridge, sub, gi, name, nickname=None):
    r = client.post("/links", json={"sub": sub, "coopdx_name": name, "gi": gi, "nickname": nickname}, headers=bridge)
    assert r.status_code == 200, r.text


def post(client, bridge, *evs):
    r = client.post("/events", json=list(evs), headers=bridge)
    assert r.status_code == 202, r.text
    return r.json()


@pytest.fixture
def session(client, bridge):
    """A server session (hello) with Ali (gi 1) and Bo (gi 2) logged in."""
    post(client, bridge, {"t": "hello", "version": "1.4.0"})
    link(client, bridge, "auth0|ali", 1, "Ali", "AliGator")
    link(client, bridge, "auth0|bo", 2, "Bo", "Bo the Bold")
    return client


# ── parsing ───────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("over,reason", [
    ({"mission": "nope"}, "unknown_mission"),
    ({"frames": "fast"}, "bad_fields"),
    ({"client_frames": None}, "bad_fields"),
    ({"frames": 0, "client_frames": 0}, "out_of_range"),
    ({"frames": 200_000, "client_frames": 200_000}, "out_of_range"),
    ({"frames": 1200, "client_frames": 1261}, "clock_mismatch"),
    ({"frames": 674, "client_frames": 674}, "below_floor"),
    ({"players": 2}, "player_count"),
    ({"players": 0}, "player_count"),
])
def test_parse_rejects(over, reason):
    f = {k: v for k, v in run_ev().items() if k not in ("t", "payload", "at")}
    f.update(over)
    assert runs.parse(f)["reason"] == reason


def test_parse_accepts_edges():
    base = {k: v for k, v in run_ev().items() if k not in ("t", "payload", "at")}
    assert runs.parse({**base, "frames": 1200, "client_frames": 1260})["reason"] is None    # exactly 2 s apart
    assert runs.parse({**base, "frames": 675, "client_frames": 700})["reason"] is None      # exactly the floor
    assert runs.parse({**base, "frames": 1200.0})["frames"] == 1200                         # Lua number
    two = {k: v for k, v in run_ev(players=(("1", "A"), ("2", "B"))).items() if k not in ("t", "payload", "at")}
    assert runs.parse(two)["reason"] is None
    assert runs.parse({**two, "gi2": 1})["reason"] == "player_count"                        # same gi twice
    assert runs.parse({**base, "gi2": 4, "name2": "X"})["reason"] == "player_count"          # extra pair


# ── POST /events ──────────────────────────────────────────────────────────────────────────────

def test_ranked_and_unranked_runs_are_stored(session, bridge, conn):
    client = session
    r = post(client, bridge, run_ev(frames=1500), run_ev(frames=1400, players=(("3", "Cy"),)),
             run_ev(frames=100), run_ev(mission="moon_base"))
    assert r["stored"] == 4
    assert [(x["ranked"], x["reason"]) for x in r["runs"]] == [
        (True, None), (False, "unlinked"), (False, "below_floor"), (False, "unknown_mission")]
    rows = conn.execute("SELECT mission, frames, ranked, reason, subs, names, gis, player_key, event_id "
                        "FROM runs ORDER BY id").fetchall()
    assert rows[0]["subs"] == ["auth0|ali"] and rows[0]["player_key"] == "auth0|ali" and rows[0]["event_id"]
    assert rows[1]["subs"] == [None] and rows[1]["names"] == ["Cy"] and rows[1]["gis"] == [3]
    assert conn.execute("SELECT count(*) AS n FROM events WHERE t='run'").fetchone()["n"] == 4
    assert conn.execute("SELECT run_id FROM run_pushes").fetchall() == [{"run_id": 1}]   # only the ranked one


def test_links_are_session_scoped(client, bridge, conn):
    post(client, bridge, {"t": "hello", "version": "1"})
    link(client, bridge, "auth0|ali", 1, "Ali")
    assert post(client, bridge, run_ev())["runs"][0]["ranked"] is True
    # wrong name on that gi, or the right name on another gi: not the linked player
    assert post(client, bridge, run_ev(players=(("1", "Mallory"),)))["runs"][0]["reason"] == "unlinked"
    assert post(client, bridge, run_ev(players=(("5", "Ali"),)))["runs"][0]["reason"] == "unlinked"
    # the player leaves: their link no longer counts, even if someone takes gi 1 with the same name
    post(client, bridge, {"t": "leave", "payload": {"t": "leave", "gi": 1, "name": "Ali"}, "gi": 1, "name": "Ali"})
    assert post(client, bridge, run_ev())["runs"][0]["reason"] == "unlinked"
    link(client, bridge, "auth0|ali", 1, "Ali")          # logs in again
    assert post(client, bridge, run_ev())["runs"][0]["ranked"] is True
    # a server restart (new hello) drops every link
    post(client, bridge, {"t": "hello", "version": "2"})
    assert post(client, bridge, run_ev())["runs"][0]["reason"] == "unlinked"


def test_most_recent_link_wins_and_duplicates(session, bridge, conn):
    client = session
    link(client, bridge, "auth0|carol", 1, "Ali")        # someone else logged in as gi 1 "Ali" later
    post(client, bridge, run_ev())
    assert conn.execute("SELECT subs FROM runs").fetchone()["subs"] == ["auth0|carol"]
    link(client, bridge, "auth0|carol", 2, "Bo")
    r = post(client, bridge, run_ev(players=(("1", "Ali"), ("2", "Bo"))))
    assert r["runs"][0]["reason"] == "duplicate_player"


def test_bad_run_never_fails_the_batch(session, bridge, conn):
    weird = {"t": "run", "mission": None, "frames": {"x": 1}, "players": "many", "gi1": "zz"}
    r = post(session, bridge, weird, {"t": "join", "gi": 4, "name": "Di"})
    assert r["stored"] == 2 and r["runs"][0]["reason"] == "unknown_mission"
    assert conn.execute("SELECT mission, frames FROM runs").fetchone() == {"mission": "", "frames": None}


# ── GET /leaderboards ─────────────────────────────────────────────────────────────────────────

def test_leaderboards(session, bridge, conn):
    client = session
    link(client, bridge, "auth0|cy", 3, "Cy", None)       # no nickname: shown by coopdx name
    post(client, bridge,
         run_ev(frames=1500), run_ev(frames=1300), run_ev(frames=1350),            # Ali: best 1300
         run_ev(frames=1300, players=(("2", "Bo"),)),                               # Bo ties Ali, later
         run_ev(frames=1900, players=(("3", "Cy"),)),
         run_ev(frames=1000, players=(("4", "Nobody"),)),                           # unlinked: never shown
         run_ev(frames=1250, players=(("1", "Ali"), ("2", "Bo"))),                 # the pair: its own entry
         run_ev(frames=1260, players=(("2", "Bo"), ("1", "Ali"))),                 # same set, other order
         run_ev(mission="libwest_coffee", frames=1400, players=(("2", "Bo"),)))
    b = client.get("/leaderboards")
    assert b.status_code == 200 and b.headers["cache-control"].startswith("public")
    boards = {m["mission"]: m for m in b.json()["missions"]}
    assert set(boards) == set(MISSIONS)
    sprint = boards["swamp_sprint"]
    assert sprint["title"] == "STADIUM STAIR SPRINT"
    assert [(r["rank"], r["names"], r["frames"]) for r in sprint["rows"]] == [
        (1, ["AliGator", "Bo the Bold"], 1250), (2, ["AliGator"], 1300), (3, ["Bo the Bold"], 1300), (4, ["Cy"], 1900)]
    assert boards["libwest_coffee"]["rows"][0]["names"] == ["Bo the Bold"]
    assert boards["reitz_rooftop"]["rows"] == []

    one = client.get("/leaderboards/swamp_sprint?limit=2").json()
    assert one["mission"] == "swamp_sprint" and one["gold"] == 45 and one["floor_frames"] == 675
    assert [r["frames"] for r in one["rows"]] == [1250, 1300]
    assert len(client.get("/leaderboards/swamp_sprint?limit=999").json()["rows"]) == 4
    assert client.get("/leaderboards/nope").status_code == 404
    # nicknames are read at query time
    conn.execute("UPDATE users SET nickname = 'Ali G' WHERE sub = 'auth0|ali'")
    assert client.get("/leaderboards/swamp_sprint").json()["rows"][1]["names"] == ["Ali G"]


def test_top5_per_mission(session, bridge, conn):
    client = session
    for i in range(7):
        link(client, bridge, f"auth0|p{i}", 10 + i, f"P{i}")
        post(client, bridge, run_ev(frames=1000 + i, players=((str(10 + i), f"P{i}"),)))
    rows = {m["mission"]: m["rows"] for m in client.get("/leaderboards").json()["missions"]}["swamp_sprint"]
    assert [r["rank"] for r in rows] == [1, 2, 3, 4, 5] and rows[0]["frames"] == 1000


def test_leaderboard_cache(make_client, bridge, conn):
    client = make_client(leaderboard_cache_secs=60)
    post(client, bridge, {"t": "hello"})
    link(client, bridge, "auth0|ali", 1, "Ali", "Ali")
    assert client.get("/leaderboards/swamp_sprint").json()["rows"] == []
    conn.execute("UPDATE users SET nickname = 'stale?'")
    post(client, bridge, run_ev())                       # a ranked run clears the cache
    assert client.get("/leaderboards/swamp_sprint").json()["rows"][0]["names"] == ["stale?"]
    conn.execute("UPDATE users SET nickname = 'cached'")
    assert client.get("/leaderboards/swamp_sprint").json()["rows"][0]["names"] == ["stale?"]


# ── DeepSpace push (§10.4) ────────────────────────────────────────────────────────────────────

class FakeDeepSpace:
    """Stands in for the app's ingest route: checks the signature like ingest-routes.ts does."""

    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.status = 200
        self.fail = False

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if self.fail:
            raise httpx.ConnectError("deepspace down", request=request)
        self.requests.append(request)
        h = request.headers
        msg = b"v1:" + h["x-sgl-timestamp"].encode() + b":" + h["x-sgl-nonce"].encode() + b":" + request.content
        good = "v1=" + hmac.new(SECRET.encode(), msg, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(good, h["x-sgl-signature"]):
            return httpx.Response(401, json={"success": False, "error": "bad signature"})
        if self.status != 200:
            return httpx.Response(self.status, json={"success": False, "error": "nope"})
        return httpx.Response(200, json={"success": True, "data": {"duplicate": False}})

    def bodies(self):
        return [json.loads(r.content) for r in self.requests]


@pytest.fixture
def ds(make_client):
    fake = FakeDeepSpace()
    client = make_client(transport=httpx.MockTransport(fake), deepspace_app_url=APP_URL + "/",
                         deepspace_ingest_secret=SECRET, deepspace_push_max_attempts=3)
    return client, fake


def test_push_signed_after_ranked_run(ds, bridge, conn):
    client, fake = ds
    post(client, bridge, {"t": "hello"})
    link(client, bridge, "auth0|ali", 1, "Ali", "AliGator")
    link(client, bridge, "auth0|bo", 2, "Bo", None)
    post(client, bridge, run_ev(frames=1300, retries=2, players=(("1", "Ali"), ("2", "Bo"))),
         run_ev(players=(("7", "Nobody"),)))
    assert len(fake.requests) == 1                        # the unranked run is never pushed
    req = fake.requests[0]
    assert str(req.url) == APP_URL + "/api/actions/ingestVerifiedRun"
    body = fake.bodies()[0]
    uid = conn.execute("SELECT uid FROM runs WHERE ranked").fetchone()["uid"]
    assert body["runId"] == str(uid) and body["missionId"] == "swamp_sprint" and body["frames"] == 1300
    assert body["retries"] == 2 and body["coop"] is True and body["v"] == 1
    assert [p["name"] for p in body["players"]] == ["AliGator", "Bo"]
    assert body["players"][0]["tag"] == runs.player_tag("auth0|ali") and "auth0" not in json.dumps(body)
    assert conn.execute("SELECT state, attempts FROM run_pushes").fetchone() == {"state": "sent", "attempts": 1}


def test_push_outage_retries_then_fails(ds, bridge, conn):
    client, fake = ds
    fake.fail = True
    post(client, bridge, {"t": "hello"})
    link(client, bridge, "auth0|ali", 1, "Ali")
    r = client.post("/events", json=run_ev(), headers=bridge)
    assert r.status_code == 202 and r.json()["runs"][0]["ranked"] is True     # the bridge never sees the outage
    p = conn.execute("SELECT state, attempts, last_error, next_at > now() AS later FROM run_pushes").fetchone()
    assert p["state"] == "pending" and p["attempts"] == 1 and "deepspace down" in p["last_error"] and p["later"]
    pusher = client.app.state.pusher
    assert pusher.drain() == 0                            # not due yet (backoff)
    conn.execute("UPDATE run_pushes SET next_at = now()")
    fake.fail = False
    assert pusher.drain() == 1 and len(fake.requests) == 1
    # a second ranked run during another outage: bounded attempts, then failed
    fake.fail = True
    post(client, bridge, run_ev(frames=1250))
    for _ in range(3):
        conn.execute("UPDATE run_pushes SET next_at = now() WHERE state = 'pending'")
        pusher.drain()
    assert conn.execute("SELECT state, attempts FROM run_pushes WHERE run_id = 2").fetchone() == \
        {"state": "failed", "attempts": 3}


def test_push_nonce_fresh_per_attempt_and_permanent_errors(ds, bridge, conn):
    client, fake = ds
    fake.status = 503
    post(client, bridge, {"t": "hello"})
    link(client, bridge, "auth0|ali", 1, "Ali")
    post(client, bridge, run_ev())
    conn.execute("UPDATE run_pushes SET next_at = now()")
    client.app.state.pusher.drain()
    assert len(fake.requests) == 2
    assert fake.requests[0].headers["x-sgl-nonce"] != fake.requests[1].headers["x-sgl-nonce"]
    assert fake.requests[0].content == fake.requests[1].content          # same run, same body
    fake.status = 422
    conn.execute("UPDATE run_pushes SET next_at = now()")
    client.app.state.pusher.drain()
    assert conn.execute("SELECT state FROM run_pushes").fetchone()["state"] == "failed"


def test_push_disabled_keeps_outbox(client, bridge, conn):
    """Without DEEPSPACE_APP_URL/SECRET nothing is sent, but ranked runs wait in the outbox."""
    post(client, bridge, {"t": "hello"})
    link(client, bridge, "auth0|ali", 1, "Ali")
    post(client, bridge, run_ev())
    assert client.app.state.pusher.enabled is False and client.app.state.pusher.drain() == 0
    assert conn.execute("SELECT state, attempts FROM run_pushes").fetchone() == {"state": "pending", "attempts": 0}


def test_sign_vector():
    """A fixed vector, shared with companion/app/src/server/ingest-routes.test.ts."""
    h = deepspace.sign("s3cret", b'{"runId":"r1"}', timestamp="1760000000", nonce="0" * 32)
    assert h["X-SGL-Signature"] == "v1=3d19ad467ef59d58cb86868105871536d42b5edbbe0e2c62ef9a8ccacaa1b9d0"
    assert deepspace.backoff(1) == 30 and deepspace.backoff(2) == 60 and deepspace.backoff(30) == 3600
