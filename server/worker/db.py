"""All of the worker's SQL, in one place, so it is easy to reconcile with the API's
canonical schema (server/api/schema.sql on web/api).

Assumed schema (columns the worker reads/writes):
  jobs(id uuid, character_id uuid, state text, step text, log text, started timestamptz,
       finished timestamptz, worker text, created timestamptz)
  characters(id uuid, owner_sub text, name text, slot int null, state text, spec jsonb,
             created timestamptz, deployed_at timestamptz)

jobs.state:  queued -> spec -> face -> build -> export -> validate -> preview -> ready | failed
jobs.step:   the step being worked on (finer than state: also "store"); on failure, the step
             that failed. jobs.log: the last LOG_TAIL characters of the job log.
characters.state (worker side): CHAR_BUILDING while a job runs, CHAR_READY / CHAR_FAILED at the
end; the API owns every other state (slotting, deploys). Artifacts are at builds/<job id>/ in
Object Storage (manifest.json lists them); the worker does not touch slot or deployed_at.

Env: DATABASE_URL (libpq URL; Vultr Managed PostgreSQL needs sslmode=require).
"""
import json

import psycopg
from psycopg.rows import dict_row

LOG_TAIL = 8000
CHAR_BUILDING = "building"
CHAR_READY = "ready"
CHAR_FAILED = "failed"
TERMINAL = ("ready", "failed")


def connect(url):
    return psycopg.connect(url, autocommit=True, row_factory=dict_row)


def claim_job(conn, worker):
    """Claim the oldest queued job (or None). Commits: the job leaves 'queued' immediately, so
    the row lock is not held while the job runs."""
    with conn.transaction():
        row = conn.execute(
            """SELECT j.id, j.character_id, c.name, c.owner_sub
                 FROM jobs j JOIN characters c ON c.id = j.character_id
                WHERE j.state = 'queued'
                ORDER BY j.created
                FOR UPDATE OF j SKIP LOCKED
                LIMIT 1""").fetchone()
        if row is None:
            return None
        conn.execute(
            """UPDATE jobs SET state = 'spec', step = 'spec', worker = %s, started = now(), finished = NULL,
                      log = '' WHERE id = %s""", (worker, row["id"]))
        conn.execute("UPDATE characters SET state = %s WHERE id = %s", (CHAR_BUILDING, row["character_id"]))
    return row


def update_job(conn, job_id, state=None, step=None, log=None):
    """Progress: any of state / step / log (log = the full log text; only its tail is stored)."""
    sets, args = [], []
    if state is not None:
        sets.append("state = %s")
        args.append(state)
    if step is not None:
        sets.append("step = %s")
        args.append(step)
    if log is not None:
        sets.append("log = %s")
        args.append(log[-LOG_TAIL:])
    if not sets:
        return
    with conn.transaction():
        conn.execute(f"UPDATE jobs SET {', '.join(sets)} WHERE id = %s", (*args, job_id))


def finish_job(conn, job_id, character_id, ok, log, step=None, spec=None):
    """Terminal state for the job and its character (spec stored on success)."""
    with conn.transaction():
        conn.execute(
            """UPDATE jobs SET state = %s, step = COALESCE(%s, step), log = %s, finished = now()
                WHERE id = %s""", ("ready" if ok else "failed", step, log[-LOG_TAIL:], job_id))
        if ok:
            conn.execute("UPDATE characters SET state = %s, spec = %s WHERE id = %s",
                         (CHAR_READY, json.dumps(spec), character_id))
        else:
            conn.execute("UPDATE characters SET state = %s WHERE id = %s", (CHAR_FAILED, character_id))


def orphaned_jobs(conn, worker):
    """Jobs this worker claimed but never finished (the process died mid-job)."""
    with conn.transaction():
        return conn.execute(
            "SELECT id, character_id, step FROM jobs WHERE worker = %s AND state NOT IN ('queued', 'ready', 'failed')",
            (worker,)).fetchall()
