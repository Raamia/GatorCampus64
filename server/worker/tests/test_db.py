"""db.py + worker.handle against a real Postgres with the API's schema (server/api/schema.sql).
Uses $TEST_DATABASE_URL, else starts postgres:16-alpine with docker (see conftest.py)."""
import uuid

import psycopg
import pytest

import db
import pipeline
import worker

QUIET = {"log": lambda m: None}


@pytest.fixture
def conn(pg):
    c = db.connect(pg)
    yield c
    c.close()


def add_job(conn, name="Pat", created="now()", owner="auth0|x"):
    cid, jid = uuid.uuid4(), uuid.uuid4()
    conn.execute("INSERT INTO users (sub) VALUES (%s) ON CONFLICT DO NOTHING", (owner,))
    conn.execute("INSERT INTO characters (id, owner_sub, name, state, step) VALUES (%s, %s, %s, 'queued', 'queued')",
                 (cid, owner, name))
    conn.execute(f"INSERT INTO jobs (id, character_id, state, step, photos, created) "
                 f"VALUES (%s, %s, 'queued', 'queued', %s, {created})",
                 (jid, cid, [f"photos/{jid}/0.jpg", f"photos/{jid}/1.jpg"]))
    return jid, cid


def row(conn, table, id_):
    return conn.execute(f"SELECT * FROM {table} WHERE id = %s", (id_,)).fetchone()


class Store:
    def __init__(self):
        self.deleted = []

    def delete_prefix(self, p):
        self.deleted.append(p)
        return 0


def ok_result(job_id, name):
    p = f"builds/{job_id}/"
    files = [p + k for k in ("actors/sglguest/geo.inc.c", "actors/sglguest/geo_header.h",
                             "actors/sglguest/model.inc.c", "character.json", "manifest.json", "portrait.png",
                             "previews/front.png", "log.txt")]
    return {"spec": {"id": "sglguest", "name": name}, "manifest": {}, "log": "all good",
            "artifacts": {"build_id": "sglguest", "prefix": p, "portrait": p + "portrait.png",
                          "previews": [p + "previews/front.png"], "files": files}}


def test_claim_oldest_and_skip_locked(conn, pg):
    j_new, _ = add_job(conn, "New")
    j_old, c_old = add_job(conn, "Old", "now() - interval '1 minute'")
    other = psycopg.connect(pg)
    # another worker holds the oldest row locked: we get the next one
    other.execute("SELECT id FROM characters WHERE id = %s FOR UPDATE", (c_old,))
    got = db.claim_job(conn, "w1")
    assert got["id"] == j_new and got["name"] == "New"
    assert got["photos"] == [f"photos/{j_new}/0.jpg", f"photos/{j_new}/1.jpg"] and got["attempts"] == 1
    other.rollback()
    got2 = db.claim_job(conn, "w1")
    assert got2["id"] == j_old
    assert db.claim_job(conn, "w1") is None
    j = row(conn, "jobs", j_old)
    assert (j["state"], j["step"], j["worker"], j["attempts"], j["error"]) == ("spec", "spec", "w1", 1, None)
    assert j["started"] is not None
    c = row(conn, "characters", c_old)
    assert (c["state"], c["step"], c["slot"]) == ("spec", "spec", None)  # no slot while building
    other.close()


def test_progress_mirrors_state_to_character(conn):
    jid, cid = add_job(conn)
    job = db.claim_job(conn, "w1")
    db.update_job(conn, jid, cid, lease_token=job["lease_token"], state="preview", step="store", log="x" * 9000)
    j, c = row(conn, "jobs", jid), row(conn, "characters", cid)
    assert (j["state"], j["step"], len(j["log"])) == ("preview", "store", db.LOG_TAIL)
    assert (c["state"], c["step"]) == ("preview", "store")
    with pytest.raises(ValueError):
        db.update_job(conn, jid, cid, lease_token=job["lease_token"], state="building")
    with pytest.raises(psycopg.errors.CheckViolation):  # the schema agrees
        conn.execute("UPDATE jobs SET step = 'done' WHERE id = %s", (jid,))


def test_handle_success_assigns_slot_and_writes_artifacts(conn, monkeypatch):
    jid, cid = add_job(conn)
    job = db.claim_job(conn, "w1")
    seen = {}

    def fake_run(job_id, name, store, backend, cfg, progress, photos=None, check=None):
        seen["photos"] = photos
        progress("build", "build", "line\n" * 5000)
        assert row(conn, "characters", cid)["state"] == "build"
        return ok_result(job_id, name)

    monkeypatch.setattr(pipeline, "run_job", fake_run)
    assert worker.handle(conn, job, Store(), None, None, **QUIET)
    assert seen["photos"] == job["photos"]
    j, c = row(conn, "jobs", jid), row(conn, "characters", cid)
    assert (j["state"], j["step"], j["log"], j["error"]) == ("ready", "ready", "all good", None)
    assert j["finished"] is not None and j["artifacts"]["build_id"] == "sglguest"
    assert (c["state"], c["step"], c["slot"]) == ("ready", "ready", 1) and c["spec"]["name"] == "Pat"
    d = conn.execute("SELECT slot, kind, character_id, job_id, state FROM deploys").fetchall()
    assert d == [{"slot": 1, "kind": "character", "character_id": cid, "job_id": jid, "state": "pending"}]


def test_handle_failure(conn, monkeypatch):
    jid, cid = add_job(conn)
    job = db.claim_job(conn, "w1")

    def failing(*a, **k):
        e = pipeline.StepFailed("validate", "boom\nmore detail")
        e.log = "x" * 20000
        raise e

    monkeypatch.setattr(pipeline, "run_job", failing)
    assert not worker.handle(conn, job, Store(), None, None, **QUIET)
    j, c = row(conn, "jobs", jid), row(conn, "characters", cid)
    assert (j["state"], j["step"], j["error"]) == ("failed", "validate", "validate: boom")
    assert len(j["log"]) == db.LOG_TAIL and j["finished"] is not None
    assert (c["state"], c["step"], c["slot"]) == ("failed", "validate", None)
    assert conn.execute("SELECT count(*) AS n FROM deploys").fetchone()["n"] == 0


def test_no_free_slot_still_ready(conn, monkeypatch):
    """All 8 slots pinned: the character is ready without a slot (the API slots it later)."""
    holders = []
    for i in range(8):
        _, c = add_job(conn, f"h{i}", owner=f"auth0|h{i}")
        conn.execute("UPDATE characters SET state = 'ready' WHERE id = %s", (c,))
        conn.execute("UPDATE jobs SET state = 'ready', step = 'ready' WHERE character_id = %s", (c,))
        assert conn.execute("SELECT sgl_assign_slot(%s) AS s", (c,)).fetchone()["s"] == i + 1
        holders.append(c)
    conn.execute("UPDATE slots SET pinned = true")
    jid, cid = add_job(conn)
    job = db.claim_job(conn, "w1")
    monkeypatch.setattr(pipeline, "run_job", lambda job_id, name, *a, **k: ok_result(job_id, name))
    assert worker.handle(conn, job, Store(), None, None, **QUIET)
    c = row(conn, "characters", cid)
    assert c["state"] == "ready" and c["slot"] is None and c["evicted_at"] is None
    conn.execute("UPDATE slots SET pinned = false WHERE n = 5")
    conn.execute("SELECT sgl_sync_deploys()")
    assert row(conn, "characters", cid)["slot"] == 5
    assert row(conn, "characters", holders[4])["evicted_at"] is not None


def test_deleted_character_cancels_job(conn, monkeypatch):
    jid, cid = add_job(conn)
    job = db.claim_job(conn, "w1")
    calls = []

    def run(job_id, name, store, backend, cfg, progress, photos=None, check=None):
        progress("face", "face", "ok")
        conn.execute("DELETE FROM characters WHERE id = %s", (cid,))  # the owner deletes it
        with pytest.raises(pipeline.JobCancelled):
            progress("build", "build", "...")
        calls.append("cancelled")
        raise pipeline.JobCancelled(str(job_id))

    monkeypatch.setattr(pipeline, "run_job", run)
    assert worker.handle(conn, job, Store(), None, None, **QUIET) is False
    assert calls == ["cancelled"]
    with pytest.raises(db.JobGone):
        db.update_job(conn, jid, cid, lease_token=job["lease_token"], log="x")

    # deleted after the pipeline finished: finish_job notices, the build is discarded
    jid2, cid2 = add_job(conn)
    job2 = db.claim_job(conn, "w1")

    def run_then_delete(job_id, name, *a, **k):
        conn.execute("DELETE FROM characters WHERE id = %s", (cid2,))
        return ok_result(job_id, name)

    monkeypatch.setattr(pipeline, "run_job", run_then_delete)
    s = Store()
    assert worker.handle(conn, job2, s, None, None, **QUIET) is False
    assert s.deleted == [f"builds/{jid2}/"]
    assert conn.execute("SELECT count(*) AS n FROM slots WHERE character_id IS NOT NULL").fetchone()["n"] == 0


def test_recover_orphans(conn):
    jid, cid = add_job(conn)
    job = db.claim_job(conn, "w1")
    db.update_job(conn, jid, cid, lease_token=job["lease_token"], state="build", step="build")
    s = Store()
    worker.recover(conn, s, **QUIET)
    assert row(conn, "jobs", jid)["state"] == "build"  # same hostname does not revoke a live lease
    assert not s.deleted
    conn.execute("UPDATE jobs SET lease_expires_at = now() - interval '1 second' WHERE id = %s", (jid,))
    worker.recover(conn, s, **QUIET)
    j = conn.execute("SELECT state, step, log, error FROM jobs WHERE id = %s", (jid,)).fetchone()
    assert j["state"] == "failed" and j["step"] == "build" and "expired" in j["log"] and "expired" in j["error"]
    assert row(conn, "characters", cid)["state"] == "failed"
    assert s.deleted == [f"photos/{jid}/", f"builds/{jid}/"]
    assert db.expire_jobs(conn) == []


def test_progress_does_not_lock_job_before_character(conn, pg):
    import time
    from concurrent.futures import ThreadPoolExecutor
    jid, cid = add_job(conn)
    job = db.claim_job(conn, "w1")
    with psycopg.connect(pg) as deleting, ThreadPoolExecutor(max_workers=1) as executor:
        deleting.execute('SELECT id FROM characters WHERE id = %s FOR UPDATE', (cid,))
        def progress():
            with db.connect(pg) as writer:
                db.update_job(writer, jid, cid, state='build', step='build', lease_token=job['lease_token'])
        update = executor.submit(progress)
        try:
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                waiting = conn.execute("SELECT 1 FROM pg_stat_activity WHERE datname = current_database() "
                                       "AND wait_event_type = 'Lock'").fetchone()
                if waiting:
                    break
                time.sleep(.01)
            assert waiting
            deleting.execute('SELECT id FROM jobs WHERE id = %s FOR UPDATE NOWAIT', (jid,))
        finally:
            deleting.rollback()
        update.result(timeout=3)


def test_lease_fences_all_writes_and_wrong_character(conn):
    jid, cid = add_job(conn)
    job = db.claim_job(conn, "same-host")
    _, other = add_job(conn, "Other")
    for token, character in [(uuid.uuid4(), cid), (job["lease_token"], other), (None, cid)]:
        with pytest.raises(db.JobGone):
            db.update_job(conn, jid, character, state="build", lease_token=token)
        with pytest.raises(db.JobGone):
            db.finish_job(conn, jid, character, True, "late", lease_token=token)
        with pytest.raises(db.JobGone):
            db.renew_lease(conn, jid, character, token)
    conn.execute("UPDATE jobs SET lease_expires_at = now() - interval '1 second' WHERE id = %s", (jid,))
    for operation in [lambda: db.renew_lease(conn, jid, cid, job["lease_token"]),
                      lambda: db.update_job(conn, jid, cid, log="late", lease_token=job["lease_token"]),
                      lambda: db.finish_job(conn, jid, cid, True, "late", lease_token=job["lease_token"]),
                      lambda: db.finish_job(conn, jid, cid, False, "late", lease_token=job["lease_token"])]:
        with pytest.raises(db.JobGone):
            operation()
    assert row(conn, "jobs", jid)["state"] == "spec"
    assert db.expire_jobs(conn)[0]["id"] == jid
    assert db.claim_job(conn, "replacement-host")["character_id"] == other
    assert row(conn, "jobs", jid)["state"] == "failed"
    with pytest.raises(db.JobGone):
        db.finish_job(conn, jid, cid, True, "late", lease_token=job["lease_token"])
    assert conn.execute("SELECT count(*) AS n FROM deploys").fetchone()["n"] == 0


def test_renew_and_recover_all_hosts_and_legacy(conn):
    jid, cid = add_job(conn)
    job = db.claim_job(conn, "gone-host")
    conn.execute("UPDATE jobs SET lease_expires_at = now() + interval '10 seconds' WHERE id = %s", (jid,))
    db.renew_lease(conn, jid, cid, job["lease_token"])
    assert conn.execute("SELECT lease_expires_at > now() + interval '100 seconds' AS ok "
                        "FROM jobs WHERE id = %s", (jid,)).fetchone()["ok"]
    legacy, _ = add_job(conn, "Legacy")
    db.claim_job(conn, "another-host")
    conn.execute("UPDATE jobs SET lease_token = NULL, lease_expires_at = NULL WHERE id = %s", (legacy,))
    assert [j["id"] for j in db.expire_jobs(conn)] == [legacy]
    assert row(conn, "jobs", jid)["state"] == "spec"


def test_renew_waiting_on_character_cannot_revive_expired_job(conn, pg):
    import time
    from concurrent.futures import ThreadPoolExecutor
    jid, cid = add_job(conn)
    job = db.claim_job(conn, "w")
    with psycopg.connect(pg) as locker, ThreadPoolExecutor(max_workers=1) as pool:
        locker.execute("SELECT id FROM characters WHERE id = %s FOR UPDATE", (cid,))
        def renew():
            with db.connect(pg) as c:
                db.renew_lease(c, jid, cid, job["lease_token"])
        task = pool.submit(renew)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if conn.execute("SELECT 1 FROM pg_stat_activity WHERE datname = current_database() "
                            "AND wait_event_type = 'Lock'").fetchone():
                break
            time.sleep(.01)
        else:
            pytest.fail("renewal did not wait on character")
        locker.execute("UPDATE jobs SET lease_expires_at = clock_timestamp() - interval '1 second' WHERE id = %s",
                       (jid,))
        locker.commit()
        with pytest.raises(db.JobGone):
            task.result(timeout=3)


def test_watch_renews_during_quiet_pipeline_and_cancels_on_loss(conn, monkeypatch):
    import time
    jid, cid = add_job(conn)
    job = db.claim_job(conn, "w")
    monkeypatch.setattr(db, "RENEW_SECONDS", .02)
    conn.execute("UPDATE jobs SET lease_expires_at = now() + interval '10 seconds' WHERE id = %s", (jid,))
    watch = worker.LeaseWatch(conn, job)
    watch.thread.start()
    try:
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if conn.execute("SELECT lease_expires_at > now() + interval '100 seconds' AS ok "
                            "FROM jobs WHERE id = %s", (jid,)).fetchone()["ok"]:
                break
            time.sleep(.01)
        else:
            pytest.fail("quiet job lease was not renewed")
        conn.execute("DELETE FROM characters WHERE id = %s", (cid,))
        assert watch.lost.wait(3)
        with pytest.raises(pipeline.JobCancelled):
            watch.check()
    finally:
        watch.stop.set()
        watch.thread.join(3)
    assert not watch.thread.is_alive()


def test_concurrent_sweepers_only_one_owns_cleanup(conn, pg):
    from concurrent.futures import ThreadPoolExecutor
    jid, cid = add_job(conn)
    db.claim_job(conn, 'retired-host')
    conn.execute("UPDATE jobs SET lease_expires_at = now() - interval '1 second'")
    def sweep():
        with db.connect(pg) as c:
            return db.expire_jobs(c)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = pool.submit(sweep), pool.submit(sweep)
        expired = first.result(timeout=5) + second.result(timeout=5)
    assert [j['id'] for j in expired] == [jid]
    assert row(conn, 'characters', cid)['state'] == 'failed'


def test_completed_job_is_immutable_and_not_swept(conn):
    jid, cid = add_job(conn)
    job = db.claim_job(conn, 'w')
    db.finish_job(conn, jid, cid, True, 'done', spec={}, artifacts={}, lease_token=job['lease_token'])
    assert not db.expire_jobs(conn)
    with pytest.raises(db.JobGone):
        db.update_job(conn, jid, cid, state='build', lease_token=job['lease_token'])
    with pytest.raises(db.JobGone):
        db.finish_job(conn, jid, cid, False, 'late failure', lease_token=job['lease_token'])
    assert row(conn, 'jobs', jid)['state'] == 'ready'
    assert row(conn, 'characters', cid)['slot'] == 1


def test_storage_fences_upload_after_delete_or_lease_loss(conn):
    jid, cid = add_job(conn)
    job = db.claim_job(conn, 'w')
    class Uploads(Store):
        def __init__(self):
            super().__init__()
            self.puts = []
        def put_file(self, key, path):
            self.puts.append(key)
    raw = Uploads()
    guarded = worker.JobStorage(conn, job, raw)
    guarded.put_file(f'builds/{jid}/one', 'unused')
    conn.execute("UPDATE jobs SET lease_expires_at = now() - interval '1 second' WHERE id = %s", (jid,))
    with pytest.raises(pipeline.JobCancelled):
        guarded.put_file(f'builds/{jid}/two', 'unused')
    conn.execute('DELETE FROM characters WHERE id = %s', (cid,))
    with pytest.raises(pipeline.JobCancelled):
        guarded.put_file(f'builds/{jid}/three', 'unused')
    assert raw.puts == [f'builds/{jid}/one']
    assert conn.execute('SELECT count(*) AS n FROM storage_cleanup WHERE job_id = %s', (jid,)).fetchone()['n'] == 2
