"""db.py + worker.handle against a real Postgres (the ASSUMED schema from db.py's docstring).
Skipped unless TEST_DATABASE_URL is set, e.g.
  docker run -d --rm --name sglw-pg -e POSTGRES_PASSWORD=pw -p 55432:5432 postgres:16-alpine
  TEST_DATABASE_URL=postgresql://postgres:pw@localhost:55432/postgres pytest server/worker/tests
"""
import json
import os
import uuid

import pytest

import db
import pipeline
import worker

URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL not set")

SCHEMA = """
DROP TABLE IF EXISTS jobs; DROP TABLE IF EXISTS characters;
CREATE TABLE characters (id uuid PRIMARY KEY, owner_sub text NOT NULL, name text NOT NULL, slot int,
    state text NOT NULL, spec jsonb, created timestamptz NOT NULL DEFAULT now(), deployed_at timestamptz);
CREATE TABLE jobs (id uuid PRIMARY KEY, character_id uuid NOT NULL REFERENCES characters(id),
    state text NOT NULL, step text, log text, started timestamptz, finished timestamptz, worker text,
    created timestamptz NOT NULL DEFAULT now());
"""


@pytest.fixture
def conn():
    c = db.connect(URL)
    c.execute(SCHEMA)
    yield c
    c.close()


def add_job(conn, name="Pat", created="now()"):
    cid, jid = uuid.uuid4(), uuid.uuid4()
    conn.execute("INSERT INTO characters (id, owner_sub, name, state) VALUES (%s, 'auth0|x', %s, 'queued')",
                 (cid, name))
    conn.execute(f"INSERT INTO jobs (id, character_id, state, created) VALUES (%s, %s, 'queued', {created})",
                 (jid, cid))
    return jid, cid


def test_claim_oldest_and_skip_locked(conn):
    j_new, _ = add_job(conn, "New")
    j_old, _ = add_job(conn, "Old", "now() - interval '1 minute'")
    other = db.connect(URL)
    # another worker holds the oldest row locked: we get the next one
    other.execute("BEGIN")
    other.execute("SELECT id FROM jobs WHERE id = %s FOR UPDATE", (j_old,))
    got = db.claim_job(conn, "w1")
    assert got["id"] == j_new and got["name"] == "New"
    other.execute("ROLLBACK")
    got2 = db.claim_job(conn, "w1")
    assert got2["id"] == j_old
    assert db.claim_job(conn, "w1") is None
    row = conn.execute("SELECT state, step, worker, started FROM jobs WHERE id = %s", (j_old,)).fetchone()
    assert row["state"] == "spec" and row["worker"] == "w1" and row["started"] is not None
    other.close()


def test_handle_success_and_failure(conn, monkeypatch):
    jid, cid = add_job(conn)
    job = db.claim_job(conn, "w1")

    def fake_run(job_id, name, store, backend, cfg, progress):
        progress("build", "build", "line\n" * 5000)
        assert conn.execute("SELECT state FROM jobs WHERE id = %s", (job_id,)).fetchone()["state"] == "build"
        return {"spec": {"id": "sglguest", "name": name}, "manifest": {}, "log": "all good"}

    monkeypatch.setattr(pipeline, "run_job", fake_run)
    assert worker.handle(conn, job, None, None, None, log=lambda m: None)
    j = conn.execute("SELECT * FROM jobs WHERE id = %s", (jid,)).fetchone()
    c = conn.execute("SELECT * FROM characters WHERE id = %s", (cid,)).fetchone()
    assert j["state"] == "ready" and j["finished"] is not None and j["log"] == "all good"
    assert c["state"] == db.CHAR_READY and c["spec"]["name"] == "Pat"

    jid2, cid2 = add_job(conn)
    job2 = db.claim_job(conn, "w1")

    def failing(*a, **k):
        e = pipeline.StepFailed("validate", "boom")
        e.log = "x" * 20000
        raise e

    monkeypatch.setattr(pipeline, "run_job", failing)
    assert not worker.handle(conn, job2, None, None, None, log=lambda m: None)
    j = conn.execute("SELECT * FROM jobs WHERE id = %s", (jid2,)).fetchone()
    assert j["state"] == "failed" and j["step"] == "validate" and len(j["log"]) == db.LOG_TAIL
    assert conn.execute("SELECT state FROM characters WHERE id = %s", (cid2,)).fetchone()["state"] == db.CHAR_FAILED


def test_recover_orphans(conn):
    class Store:
        deleted = []

        def delete_prefix(self, p):
            self.deleted.append(p)
            return 0
    jid, cid = add_job(conn)
    db.claim_job(conn, "w1")
    db.update_job(conn, jid, state="build", step="build")
    s = Store()
    worker.recover(conn, "w1", s, log=lambda m: None)
    j = conn.execute("SELECT state, step, log FROM jobs WHERE id = %s", (jid,)).fetchone()
    assert j["state"] == "failed" and j["step"] == "build" and "restarted" in j["log"]
    assert s.deleted == [f"photos/{jid}/"]
    assert json.dumps(db.orphaned_jobs(conn, "w1")) == "[]"
