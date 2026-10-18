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

Deletion: the owner may delete the character (and, by cascade, its job) at any time. Any job
UPDATE that hits 0 rows raises JobGone: the caller stops and cleans up its objects.

Env: DATABASE_URL (libpq URL; Vultr Managed PostgreSQL needs sslmode=require).
"""
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

LOG_TAIL = 8000
ERROR_MAX = 300
STATES = ("queued", "spec", "face", "build", "export", "validate", "preview", "ready", "failed")
STEPS = ("queued", "spec", "face", "build", "export", "validate", "preview", "store", "ready")
TERMINAL = ("ready", "failed")


class JobGone(Exception):
    """The job's row is gone: its character was deleted. Stop working on it."""


def connect(url):
    return psycopg.connect(url, autocommit=True, row_factory=dict_row)


def _one_line(text):
    line = next((ln.strip() for ln in (text or "").splitlines() if ln.strip()), "")
    return line[:ERROR_MAX] or None


def claim_job(conn, worker):
    """Claim the oldest queued job (or None). Commits: the job leaves 'queued' immediately, so
    the row locks are not held while the job runs. Returns {id, character_id, photos, name,
    owner_sub, attempts}."""
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
        conn.execute(
            """UPDATE jobs SET state = 'spec', step = 'spec', worker = %s, started = now(), finished = NULL,
                      log = '', error = NULL, attempts = attempts + 1 WHERE id = %s""", (worker, row["id"]))
        conn.execute("UPDATE characters SET state = 'spec', step = 'spec' WHERE id = %s", (row["character_id"],))
    return {**row, "photos": list(row["photos"] or []), "attempts": row["attempts"] + 1}


def update_job(conn, job_id, character_id, state=None, step=None, log=None):
    """Progress: any of state / step / log (log = the full log text; only its tail is stored).
    state/step go to the job and its character. Raises JobGone if the job no longer exists."""
    if state is not None and state not in STATES:
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
        # always touch the row (even with nothing to set) so a deleted character is noticed
        cur = conn.execute(f"UPDATE jobs SET {', '.join(sets) or 'id = id'} WHERE id = %s", (*args, job_id))
        if cur.rowcount == 0:
            raise JobGone(job_id)
        if char_sets:
            conn.execute(f"UPDATE characters SET {', '.join(char_sets)} WHERE id = %s", (*char_args, character_id))


def finish_job(conn, job_id, character_id, ok, log, step=None, spec=None, artifacts=None, error=None):
    """Terminal state for the job and its character. Success stores the spec and artifacts and
    gives the character a slot (returns it, or None when no slot can be had right now; the API
    retries on the next bridge poll). Failure records step/error and releases any slot.
    Raises JobGone if the job no longer exists."""
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(hashtext('sgl_slots'))")
        conn.execute("SELECT id FROM characters WHERE id = %s FOR UPDATE", (character_id,))
        if ok:
            cur = conn.execute(
                """UPDATE jobs SET state = 'ready', step = 'ready', log = %s, error = NULL, artifacts = %s,
                          finished = now() WHERE id = %s""",
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
                      finished = now() WHERE id = %s RETURNING step""",
            (step, log[-LOG_TAIL:], (error or _one_line(log) or "failed")[:ERROR_MAX], job_id))
        row = cur.fetchone()
        if row is None:
            raise JobGone(job_id)
        conn.execute("UPDATE characters SET state = 'failed', step = %s WHERE id = %s", (row["step"], character_id))
        conn.execute("SELECT sgl_release_slot(%s)", (character_id,))
        return None


def orphaned_jobs(conn, worker):
    """Jobs this worker claimed but never finished (the process died mid-job)."""
    with conn.transaction():
        return conn.execute(
            "SELECT id, character_id, step FROM jobs WHERE worker = %s AND state NOT IN ('queued', 'ready', 'failed')",
            (worker,)).fetchall()
