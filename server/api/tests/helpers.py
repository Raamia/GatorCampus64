"""Shared test helpers: upload a character, and play the worker's part directly in SQL."""
from psycopg.types.json import Jsonb

from .conftest import BUCKET, jpeg


def upload(client, headers, name="Gator", n=1, consent="true", photo=None):
    files = [("photos", (f"p{i}.jpg", photo or jpeg(), "image/jpeg")) for i in range(n)]
    return client.post("/characters", headers=headers, data={"name": name, "consent": consent}, files=files)


def claim(conn, worker="gpu-1"):
    """The worker's claim transaction, verbatim from schema.sql's contract."""
    with conn.transaction():
        j = conn.execute("SELECT id, character_id, photos FROM jobs WHERE state = 'queued' "
                         "ORDER BY created LIMIT 1 FOR UPDATE SKIP LOCKED").fetchone()
        if not j:
            return None
        slot = conn.execute("SELECT sgl_assign_slot(%s) AS s", (j["character_id"],)).fetchone()["s"]
        conn.execute("UPDATE jobs SET state='spec', step='spec', started=now(), worker=%s, attempts=attempts+1 "
                     "WHERE id=%s", (worker, j["id"]))
        conn.execute("UPDATE characters SET state='spec', step='spec' WHERE id=%s", (j["character_id"],))
    return {**j, "slot": slot}


def finish(conn, s3, job, state="ready"):
    jid, cid = job["id"], job["character_id"]
    arts = None
    if state == "ready":
        slot = job.get("slot") or 0
        keys = [f"builds/{jid}/previews/front.png", f"builds/{jid}/previews/side.png"]
        portrait = f"builds/{jid}/sgl_portrait_guest_{slot}.png"
        for k in keys + [portrait, f"builds/{jid}/character.json", f"builds/{jid}/actors/guest_{slot}/model.inc.c",
                         f"builds/{jid}/actors/guest_{slot}/geo.inc.c"]:
            s3.put_object(Bucket=BUCKET, Key=k, Body=b"x")
        arts = {"previews": keys, "portrait": portrait, "character_json": f"builds/{jid}/character.json",
                "actors_prefix": f"builds/{jid}/actors/guest_{slot}/"}
    with conn.transaction():
        conn.execute("UPDATE jobs SET state=%s, step=%s, artifacts=%s, finished=now(), log='tail', "
                     "error=%s WHERE id=%s",
                     (state, "build" if state == "failed" else state, Jsonb(arts) if arts else None,
                      "boom" if state == "failed" else None, jid))
        conn.execute("UPDATE characters SET state=%s, step=%s, spec=%s WHERE id=%s",
                     (state, "build" if state == "failed" else state, Jsonb({"id": "guest"}), cid))
        if state == "failed":
            conn.execute("SELECT sgl_release_slot(%s)", (cid,))


def run_job(conn, s3, state="ready"):
    j = claim(conn)
    finish(conn, s3, j, state)
    return j
