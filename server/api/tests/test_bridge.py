"""Worker claim (SKIP LOCKED), slot assignment, deploys, links, events and status."""
import threading

import psycopg
from psycopg.rows import dict_row

from .helpers import claim, finish, run_job, upload


def _make_chars(conn, n, state="ready", owner="auth0|o"):
    conn.execute("INSERT INTO users (sub) VALUES (%s) ON CONFLICT DO NOTHING", (owner,))
    ids = []
    for i in range(n):
        r = conn.execute("INSERT INTO characters (owner_sub, name, state, created) "
                         "VALUES (%s, %s, %s, now() + make_interval(secs => %s)) RETURNING id",
                         (owner, f"c{i}", state, i)).fetchone()
        conn.execute("INSERT INTO jobs (character_id, state, finished) VALUES (%s, %s, now())", (r["id"], state))
        ids.append(r["id"])
    return ids


def test_skip_locked_claims_are_disjoint(client, auth, pg, conn):
    for i in range(3):
        assert upload(client, auth(sub=f"u|{i}")).status_code == 201
    c1 = psycopg.connect(pg, row_factory=dict_row)
    c2 = psycopg.connect(pg, row_factory=dict_row)
    try:
        q = "SELECT id FROM jobs WHERE state='queued' ORDER BY created LIMIT 1 FOR UPDATE SKIP LOCKED"
        a = c1.execute(q).fetchone()["id"]   # c1's transaction still open: row locked
        b = c2.execute(q).fetchone()["id"]
        assert a != b
        c1.rollback()
        c2.rollback()
    finally:
        c1.close()
        c2.close()
    got = [claim(conn)["id"] for _ in range(3)]
    assert len(set(got)) == 3 and claim(conn) is None


def test_slots_free_first_then_lru_unpinned(conn):
    ids = _make_chars(conn, 10)
    slots = [conn.execute("SELECT sgl_assign_slot(%s) AS s", (i,)).fetchone()["s"] for i in ids[:8]]
    assert slots == list(range(1, 9))
    assert conn.execute("SELECT sgl_assign_slot(%s) AS s", (ids[0],)).fetchone()["s"] == 1  # idempotent
    conn.execute("UPDATE slots SET pinned = true WHERE n IN (1, 2)")
    conn.execute("UPDATE slots SET last_played = now() - make_interval(mins => n)")  # slot 8 least recent
    conn.execute("UPDATE slots SET last_played = now() WHERE n = 8")                  # ...now 7 is
    assert conn.execute("SELECT sgl_assign_slot(%s) AS s", (ids[8],)).fetchone()["s"] == 7
    victim = conn.execute("SELECT slot, evicted_at FROM characters WHERE id = %s", (ids[6],)).fetchone()
    assert victim["slot"] is None and victim["evicted_at"] is not None
    # the slot just assigned counts as played now, so the next eviction takes the next-oldest:
    assert conn.execute("SELECT sgl_assign_slot(%s) AS s", (ids[9],)).fetchone()["s"] == 6
    conn.execute("UPDATE slots SET pinned = true")
    extra = _make_chars(conn, 1, owner="auth0|p")
    assert conn.execute("SELECT sgl_assign_slot(%s) AS s", (extra[0],)).fetchone()["s"] is None


def test_in_progress_slots_are_not_evicted(conn):
    busy = _make_chars(conn, 8, state="build")
    for i in busy:
        conn.execute("SELECT sgl_assign_slot(%s)", (i,))
    new = _make_chars(conn, 1, state="ready", owner="auth0|n")
    assert conn.execute("SELECT sgl_assign_slot(%s) AS s", (new[0],)).fetchone()["s"] is None


def test_concurrent_assignment_is_transactional(pg, conn):
    ids = _make_chars(conn, 16, state="build")
    results, errors = [], []

    def worker(chunk):
        try:
            with psycopg.connect(pg, autocommit=True) as c:
                for i in chunk:
                    results.append(c.execute("SELECT sgl_assign_slot(%s)", (i,)).fetchone()[0])
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    ts = [threading.Thread(target=worker, args=(ids[k::4],)) for k in range(4)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert not errors
    got = sorted(r for r in results if r is not None)
    assert got == list(range(1, 9))  # 8 distinct slots, the other 8 get NULL (all busy)
    rows = conn.execute("SELECT n, character_id FROM slots ORDER BY n").fetchall()
    for r in rows:
        assert conn.execute("SELECT slot FROM characters WHERE id=%s", (r["character_id"],)).fetchone()["slot"] == r["n"]


def test_deploy_flow(client, auth, conn, s3, bridge):
    h = auth(nickname="Ali")
    upload(client, h, name="Ally")
    j = run_job(conn, s3)
    r = client.get("/deploys/pending", headers=bridge).json()
    assert len(r["deploys"]) == 1
    d = r["deploys"][0]
    assert d["slot"] == j["slot"] == 1 and d["kind"] == "character" and d["actor"] == "guest_1"
    assert d["name"] == "Ally" and d["owner"] == "Ali"
    paths = sorted(f["path"] for f in d["files"])
    assert paths == ["actors/guest_1/geo.inc.c", "actors/guest_1/model.inc.c", "character.json",
                     "sgl_portrait_guest_1.png"]
    assert all("Signature" in f["url"] for f in d["files"])
    assert r["roster"][0]["name"] == "Ally" and r["roster"][1]["name"] is None
    # polling again doesn't duplicate
    assert len(client.get("/deploys/pending", headers=bridge).json()["deploys"]) == 1
    assert client.post(f"/deploys/{d['id']}", json={"state": "deployed"}, headers=bridge).status_code == 200
    assert client.post(f"/deploys/{d['id']}", json={"state": "deployed"}, headers=bridge).status_code == 409
    assert client.post("/deploys/999", json={"state": "deployed"}, headers=bridge).status_code == 404
    assert client.post(f"/deploys/{d['id']}", json={"state": "meh"}, headers=bridge).status_code == 422
    assert client.get("/deploys/pending", headers=bridge).json()["deploys"] == []
    assert client.get(f"/jobs/{j['id']}", headers=h).json()["deployed"] is True
    assert client.get("/characters").json()["characters"][0]["deployed"] is True


def test_lazy_slotting_when_worker_did_not(client, auth, conn, s3, bridge):
    """A character that became ready without a slot (all were busy at claim) is slotted on poll."""
    upload(client, auth())
    j = claim(conn)
    conn.execute("SELECT sgl_release_slot(%s, false)", (j["character_id"],))
    finish(conn, s3, {**j, "slot": None})
    assert conn.execute("SELECT slot FROM characters").fetchone()["slot"] is None
    d = client.get("/deploys/pending", headers=bridge).json()["deploys"]
    assert [x["slot"] for x in d] == [1]


def test_eviction_queues_new_deploy_and_superseding(client, conn, bridge):
    ids = _make_chars(conn, 9)
    client.get("/deploys/pending", headers=bridge)   # slots 1-8, the 9th: no free slot, nothing evictable yet?
    pend = conn.execute("SELECT slot, character_id FROM deploys WHERE state='pending' ORDER BY slot").fetchall()
    # all 8 slot holders are ready, so the 9th evicts the least recently played (all NULL -> oldest assignment)
    assert len(pend) == 8
    ninth = conn.execute("SELECT slot FROM characters WHERE id=%s", (ids[8],)).fetchone()["slot"]
    assert ninth == 1
    assert conn.execute("SELECT count(*) AS n FROM deploys WHERE state='superseded'").fetchone()["n"] == 1
    # the evicted one is never automatically re-slotted
    client.get("/deploys/pending", headers=bridge)
    assert conn.execute("SELECT slot FROM characters WHERE id=%s", (ids[0],)).fetchone()["slot"] is None


def test_admin_pin_and_redeploy(client, auth, conn, bridge):
    ids = _make_chars(conn, 1)
    client.get("/deploys/pending", headers=bridge)
    adm = auth(sub="auth0|admin", scope="admin:slots")
    assert client.put("/slots/1", json={"pinned": True}, headers=adm).json() == {"slot": 1, "pinned": True}
    assert client.put("/slots/9", json={"pinned": True}, headers=adm).status_code == 404
    r = client.post("/slots/1/redeploy", headers=adm)
    assert r.status_code == 201
    pend = client.get("/deploys/pending", headers=bridge).json()["deploys"]
    assert [(p["slot"], p["kind"], p["character_id"]) for p in pend] == [(1, "character", str(ids[0]))]
    assert client.post("/slots/2/redeploy", headers=adm).status_code == 201
    pend = client.get("/deploys/pending", headers=bridge).json()["deploys"]
    assert sorted((p["slot"], p["kind"]) for p in pend) == [(1, "character"), (2, "placeholder")]


def test_link_code_flow(client, auth, conn, s3, bridge):
    h = auth(nickname="Ali")
    upload(client, h, name="Ally")
    run_job(conn, s3)
    d = client.get("/deploys/pending", headers=bridge).json()["deploys"][0]
    client.post(f"/deploys/{d['id']}", json={"state": "deployed"}, headers=bridge)

    r = client.post("/link-codes", headers=h)
    assert r.status_code == 201
    code = r.json()["code"]
    assert len(code) == 6 and set(code) <= set("23456789ABCDEFGHJKLMNPQRSTUVWXYZ") and r.json()["expires_in"] == 600
    link = client.post("/links", json={"code": code.lower(), "coopdx_name": "AliG", "gi": 3}, headers=bridge)
    assert link.status_code == 200, link.text
    assert link.json() == {"sub": "auth0|alice", "via": "code", "nickname": "Ali", "uf": False, "gi": 3,
                           "coopdx_name": "AliG", "guest_slot": 1, "character_name": "Ally"}
    again = client.post("/links", json={"code": code, "coopdx_name": "AliG", "gi": 3}, headers=bridge)
    assert again.status_code == 410 and again.json()["detail"]["reason"] == "used"
    bad = client.post("/links", json={"code": "ZZZZZZ", "coopdx_name": "x", "gi": 1}, headers=bridge)
    assert bad.status_code == 404 and bad.json()["detail"]["reason"] == "invalid"
    code2 = client.post("/link-codes", headers=h).json()["code"]
    conn.execute("UPDATE link_codes SET expires_at = now() - interval '1 second' WHERE code=%s", (code2,))
    exp = client.post("/links", json={"code": code2, "coopdx_name": "x", "gi": 1}, headers=bridge)
    assert exp.status_code == 410 and exp.json()["detail"]["reason"] == "expired"
    # a new code replaces the user's unused one
    c3 = client.post("/link-codes", headers=h).json()["code"]
    c4 = client.post("/link-codes", headers=h).json()["code"]
    assert client.post("/links", json={"code": c3, "coopdx_name": "x", "gi": 1}, headers=bridge).status_code == 404
    assert client.post("/links", json={"code": c4, "coopdx_name": "x", "gi": 1}, headers=bridge).status_code == 200
    assert client.post("/links", json={"code": c4, "coopdx_name": "x", "gi": 1}, headers=auth()).status_code == 403
    assert client.get("/me", headers=h).json()["last_link"]["coopdx_name"] == "x"


def test_device_flow_link(client, bridge, conn):
    r = client.post("/links", json={"sub": "github|42", "coopdx_name": "Neo", "gi": 2, "nickname": "neo",
                                    "uf": True}, headers=bridge)
    assert r.status_code == 200
    assert r.json()["via"] == "device" and r.json()["nickname"] == "neo" and r.json()["uf"] is True
    assert r.json()["guest_slot"] is None
    assert conn.execute("SELECT email_uf FROM users WHERE sub='github|42'").fetchone()["email_uf"] is True
    for body in ({"coopdx_name": "x", "gi": 1}, {"sub": "a", "code": "ABCDEF", "coopdx_name": "x", "gi": 1},
                 {"sub": "a", "coopdx_name": "x", "gi": 999}):
        assert client.post("/links", json=body, headers=bridge).status_code == 422


def test_events_and_status(client, bridge, conn):
    s = client.get("/status").json()
    assert s["online"] is False and s["player_count"] == 0 and len(s["slots"]) == 8
    assert client.post("/events", json={"t": "hello", "version": "1.2.0"}, headers=bridge).status_code == 202
    evs = [{"t": "join", "gi": 1, "name": "Ali"}, {"t": "join", "gi": 2, "name": "Bo"},
           {"t": "leave", "gi": 1, "name": "Ali"}, {"t": "char", "gi": 2, "friend": "guest_3"}]
    assert client.post("/events", json=evs, headers=bridge).json() == {"stored": 4}
    s = client.get("/status").json()
    assert s["online"] is True and s["version"] == "1.2.0" and s["players"] == [{"gi": 2, "name": "Bo"}]
    assert conn.execute("SELECT last_played FROM slots WHERE n=3").fetchone()["last_played"] is not None
    # a restart: new hello resets presence
    client.post("/events", json={"t": "hello", "version": "1.2.1"}, headers=bridge)
    assert client.get("/status").json()["player_count"] == 0
    client.post("/events", json={"t": "exit"}, headers=bridge)
    assert client.get("/status").json()["online"] is False
    assert client.post("/events", json={"no": "t"}, headers=bridge).status_code == 422
    assert client.post("/events", json={"t": "join"}, headers={}).status_code == 401
    assert conn.execute("SELECT count(*) AS n FROM events").fetchone()["n"] == 7
    assert conn.execute("SELECT payload FROM events WHERE t='char'").fetchone()["payload"]["friend"] == "guest_3"


def test_status_stale(make_client, bridge, conn):
    client = make_client(status_stale_secs=60)
    client.post("/events", json={"t": "hello", "version": "1"}, headers=bridge)
    assert client.get("/status").json()["online"] is True
    conn.execute("UPDATE events SET at = now() - interval '5 minutes'")
    assert client.get("/status").json()["online"] is False


