"""All of the worker's SQL, in one place. Implements the worker contract in the header of
server/api/schema.sql (the single source of truth for the schema; the tests run against it).

States: jobs.state and characters.state both move queued -> spec -> face -> build -> export ->
validate -> preview -> ready | failed, written together in one transaction. jobs.step /
characters.step are the same names plus "store" (upload, under state "preview"); "ready" on
success, the failing step on failure.

Slots: the worker builds every job under the neutral actor id "sglguest" and never picks a
slot. When a character becomes ready, finish_job calls sgl_assign_slot() in the same
transaction (free slot, else evict the least recently played finished, unpinned one), which also
queues the deploy. The bridge renames sglguest -> guest_<slot> at deploy time.

Ownership: each claim gets a UUID lease token and 120 seconds. Renew every 30 seconds.
Every progress/result write requires the live token. Expired jobs fail, never requeue.

Deletion: the owner may delete the character (and, by cascade, its job) at any time. Any job
UPDATE that hits 0 rows or an invalid lease raises JobGone: the caller stops and cleans up its objects.

Env: DATABASE_URL (libpq URL; Vultr Managed PostgreSQL needs sslmode=require).
"""
import uuid

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

LOG_TAIL = 8000
ERROR_MAX = 300
STATES = ("queued", "spec", "face", "build", "export", "validate", "preview", "ready", "failed")
STEPS = ("queued", "spec", "face", "build", "export", "validate", "preview", "store", "ready")
TERMINAL = ("ready", "failed")
LEASE_SECONDS = 120
RENEW_SECONDS = 30


class JobGone(Exception):
    """The job was deleted or this claim no longer owns a live lease. Stop working."""


def connect(url):
    return psycopg.connect(url, autocommit=True, row_factory=dict_row)


def _one_line(text):
    line = next((ln.strip() for ln in (text or "").splitlines() if ln.strip()), "")
    return line[:ERROR_MAX] or None


def claim_job(conn, worker):
    """Claim the oldest queued job (or None). Commits: the job leaves 'queued' immediately, so
    the row locks are not held while the job runs. Returns {id, character_id, photos, name,
    owner_sub, attempts, lease_token}."""
    token = uuid.uuid4()
    with conn.transaction():
        row = conn.execute(
            """SELECT j.id, j.character_id, j.photos, j.attempts, c.name, c.owner_sub
                 FROM jobs j JOIN characters c ON c.id = j.character_id
                WHERE j.state = 'queued'
                ORDER BY j.created
                LIMIT 1
                FOR UPDATE OF c SKIP LOCKED""").fetchone()
        if row is None:
            return None
        claimed = conn.execute(
            """UPDATE jobs SET state = 'spec', step = 'spec', worker = %s, started = now(), finished = NULL,
                      log = '', error = NULL, attempts = attempts + 1, lease_token = %s,
                      lease_expires_at = clock_timestamp() + make_interval(secs => %s)
                WHERE id = %s AND state = 'queued'""", (worker, token, LEASE_SECONDS, row["id"]))
        if claimed.rowcount == 0:
            return None
        conn.execute("UPDATE characters SET state = 'spec', step = 'spec' WHERE id = %s", (row["character_id"],))
    return {**row, "photos": list(row["photos"] or []), "attempts": row["attempts"] + 1, "lease_token": token}


def update_job(conn, job_id, character_id, state=None, step=None, log=None, *, lease_token):
    """Progress: any of state / step / log (log = the full log text; only its tail is stored).
    state/step go to the job and its character. Raises JobGone if the job no longer exists."""
    if state is not None and state not in STATES[1:-2]:
        raise ValueError(f"bad state {state!r}")
    if step is not None and step not in STEPS:
        raise ValueError(f"bad step {step!r}")
    sets, args = [], []
    for col, val in (("state", state), ("step", step)):
        if val is not None:
            sets.append(f"{col} = %s")
            args.append(val)
    char_sets, char_args = list(sets), list(args)
    if log is not None:
        sets.append("log = %s")
        args.append(log[-LOG_TAIL:])
    with conn.transaction():
        # All job writers lock the character first, then its job. Slot writers
        # additionally acquire sgl_slots before either row lock.
        conn.execute("SELECT id FROM characters WHERE id = %s FOR UPDATE", (character_id,))
        _owned(conn, job_id, character_id, lease_token)
        # always touch the row (even with nothing to set) so a deleted character is noticed
        cur = conn.execute(f"UPDATE jobs SET {', '.join(sets) or 'id = id'} WHERE id = %s", (*args, job_id))
        if cur.rowcount == 0:
            raise JobGone(job_id)
        if char_sets:
            conn.execute(f"UPDATE characters SET {', '.join(char_sets)} WHERE id = %s", (*char_args, character_id))


def finish_job(conn, job_id, character_id, ok, log, step=None, spec=None, artifacts=None, error=None, *, lease_token):
    """Terminal state for the job and its character. Success stores the spec and artifacts and
    gives the character a slot (returns it, or None when no slot can be had right now; the API
    retries on the next bridge poll). Failure records step/error and releases any slot.
    Raises JobGone if the job no longer exists."""
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(hashtext('sgl_slots'))")
        conn.execute("SELECT id FROM characters WHERE id = %s FOR UPDATE", (character_id,))
        _owned(conn, job_id, character_id, lease_token)
        if ok:
            cur = conn.execute(
                """UPDATE jobs SET state = 'ready', step = 'ready', log = %s, error = NULL, artifacts = %s,
                          finished = now(), lease_expires_at = NULL WHERE id = %s""",
                (log[-LOG_TAIL:], Jsonb(artifacts) if artifacts is not None else None, job_id))
            if cur.rowcount == 0:
                raise JobGone(job_id)
            conn.execute("UPDATE characters SET state = 'ready', step = 'ready', spec = %s WHERE id = %s",
                         (Jsonb(spec), character_id))
            return conn.execute("SELECT sgl_assign_slot(%s) AS slot", (character_id,)).fetchone()["slot"]
        if step is not None and step not in STEPS:
            step = None
        cur = conn.execute(
            """UPDATE jobs SET state = 'failed', step = COALESCE(%s, step), log = %s, error = %s,
                      finished = now(), lease_expires_at = NULL WHERE id = %s RETURNING step""",
            (step, log[-LOG_TAIL:], (error or _one_line(log) or "failed")[:ERROR_MAX], job_id))
        row = cur.fetchone()
        if row is None:
            raise JobGone(job_id)
        conn.execute("UPDATE characters SET state = 'failed', step = %s WHERE id = %s", (row["step"], character_id))
        conn.execute("SELECT sgl_release_slot(%s)", (character_id,))
        return None


def _owned(conn, job_id, character_id, token):
    # Lock before checking wall time: a wait must not extend an expired lease.
    row = conn.execute("SELECT * FROM jobs WHERE id = %s AND character_id = %s FOR UPDATE",
                       (job_id, character_id)).fetchone()
    if (row is None or token is None or row["lease_token"] != token
            or row["state"] in ("queued", *TERMINAL)):
        raise JobGone(job_id)
    alive = conn.execute("SELECT %s::timestamptz > clock_timestamp() AS alive",
                         (row["lease_expires_at"],)).fetchone()["alive"]
    if not alive:
        raise JobGone(job_id)


def renew_lease(conn, job_id, character_id, lease_token):
    with conn.transaction():
        conn.execute("SELECT id FROM characters WHERE id = %s FOR UPDATE", (character_id,))
        _owned(conn, job_id, character_id, lease_token)
        conn.execute("UPDATE jobs SET lease_expires_at = clock_timestamp() + make_interval(secs => %s) "
                     "WHERE id = %s", (LEASE_SECONDS, job_id))


def expire_jobs(conn, limit=100):
    """Fail expired claims from any host, atomically; return only rows this sweeper expired.

    NULL leases are pre-upgrade abandoned jobs. Drain old workers before applying this release.
    Never requeue the same job: photos may already have been removed by its pipeline.
    """
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(hashtext('sgl_slots'))")
        rows = conn.execute(
            """SELECT j.id, j.character_id FROM jobs j JOIN characters c ON c.id = j.character_id
               WHERE j.state NOT IN ('queued', 'ready', 'failed')
                 AND (j.lease_expires_at IS NULL OR j.lease_expires_at <= clock_timestamp())
               ORDER BY j.lease_expires_at NULLS FIRST LIMIT %s FOR UPDATE OF c SKIP LOCKED""",
            (limit,)).fetchall()
        expired = []
        for row in rows:
            # A renewal may have committed while the candidate statement was taking locks.
            conn.execute("SELECT id FROM jobs WHERE id = %s FOR UPDATE", (row["id"],))
            job = conn.execute(
                """UPDATE jobs SET state = 'failed', finished = now(), lease_expires_at = NULL,
                          error = 'Worker lease expired; please retry',
                          log = right(COALESCE(log, '') || E'\nWorker lease expired; please retry', %s)
                   WHERE id = %s AND state NOT IN ('queued', 'ready', 'failed')
                     AND (lease_expires_at IS NULL OR lease_expires_at <= clock_timestamp())
                   RETURNING id, character_id, step""", (LOG_TAIL, row["id"])).fetchone()
            if job is None:
                continue
            conn.execute("UPDATE characters SET state = 'failed', step = %s WHERE id = %s",
                         (job["step"], job["character_id"]))
            conn.execute("SELECT sgl_release_slot(%s)", (job["character_id"],))
            expired.append(job)
        return expired
