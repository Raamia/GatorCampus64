"""Shared test helpers: upload a character, and play the worker's part directly in SQL.

The SQL follows schema.sql's worker contract (server/worker/db.py implements it for real; the
end-to-end check against that code is server/worker/tests/test_integration_api.py).
"""
from psycopg.types.json import Jsonb

from .conftest import BUCKET, jpeg

BUILD_ID = "sglguest"
ACTOR_FILES = ("geo_header.h", "geo.inc.c", "model.inc.c")


def upload(client, headers, name="Gator", n=1, consent="true", photo=None):
    files = [("photos", (f"p{i}.jpg", photo or jpeg(), "image/jpeg")) for i in range(n)]
    return client.post("/characters", headers=headers, data={"name": name, "consent": consent}, files=files)


def claim(conn, worker="gpu-1"):
    """The worker's claim transaction, from schema.sql's contract (no slot: builds are neutral)."""
    with conn.transaction():
        j = conn.execute("SELECT j.id, j.character_id, j.photos FROM jobs j JOIN characters c ON c.id = j.character_id "
                         "WHERE j.state = 'queued' ORDER BY j.created LIMIT 1 FOR UPDATE OF c SKIP LOCKED").fetchone()
        if not j:
            return None
        conn.execute("UPDATE jobs SET state='spec', step='spec', started=now(), finished=NULL, worker=%s, log='', "
                     "error=NULL, attempts=attempts+1 WHERE id=%s", (worker, j["id"]))
        conn.execute("UPDATE characters SET state='spec', step='spec' WHERE id=%s", (j["character_id"],))
    return dict(j)


def artifacts(jid, previews=("front.png", "side.png")):
    """jobs.artifacts as the worker writes it (schema.sql header)."""
    p = f"builds/{jid}/"
    files = ([p + "previews/" + f for f in previews] + [p + f"actors/{BUILD_ID}/{f}" for f in ACTOR_FILES]
             + [p + f for f in ("portrait.png", "character.json", "manifest.json", "build_report.json",
                                "face_sheet.png", "log.txt")])
    return {"build_id": BUILD_ID, "prefix": p, "manifest": p + "manifest.json", "character_json": p + "character.json",
            "portrait": p + "portrait.png", "previews": [p + "previews/" + f for f in previews],
            "actor_dir": p + f"actors/{BUILD_ID}/", "files": sorted(files)}


def finish(conn, s3, job, state="ready", write_artifacts=True, assign=True):
    """The worker's ready / failed transaction. Returns the job dict with the assigned slot.
    assign=False skips the sgl_assign_slot call (a worker that found no slot / crashed after commit)."""
    jid, cid = job["id"], job["character_id"]
    arts = artifacts(jid) if state == "ready" else None
    if arts:
        for k in arts["files"]:
            s3.put_object(Bucket=BUCKET, Key=k, Body=b"x")
    slot = None
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(hashtext('sgl_slots'))")
        conn.execute("SELECT id FROM characters WHERE id = %s FOR UPDATE", (cid,))
        if state == "ready":
            conn.execute("UPDATE jobs SET state='ready', step='ready', artifacts=%s, finished=now(), log='tail', "
                         "error=NULL WHERE id=%s", (Jsonb(arts) if write_artifacts else None, jid))
            conn.execute("UPDATE characters SET state='ready', step='ready', spec=%s WHERE id=%s",
                         (Jsonb({"id": BUILD_ID}), cid))
            if assign:
                slot = conn.execute("SELECT sgl_assign_slot(%s) AS s", (cid,)).fetchone()["s"]
        else:
            conn.execute("UPDATE jobs SET state='failed', step='build', finished=now(), log='tail', error='boom' "
                         "WHERE id=%s", (jid,))
            conn.execute("UPDATE characters SET state='failed', step='build' WHERE id=%s", (cid,))
            conn.execute("SELECT sgl_release_slot(%s)", (cid,))
    return {**job, "slot": slot}


def run_job(conn, s3, state="ready"):
    return finish(conn, s3, claim(conn), state)
