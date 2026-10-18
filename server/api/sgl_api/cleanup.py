"""Durable object cleanup. Queue transactions are held during deletion for exclusive ownership.

Writers and cleaners share a per-job advisory lock. No arbitrary prefix comes from a request.
A successful tombstone is revisited daily; errors retry indefinitely with capped backoff.
"""
import logging
import threading

log = logging.getLogger('sgl_api.cleanup')


class Cleaner:
    def __init__(self, db, storage, interval=30):
        self.db, self.storage, self.interval = db, storage, interval
        self.stop = threading.Event()
        self.thread = None

    def drain(self, max_items=20, job_id=None):
        if job_id is None:
            with self.db.tx() as c:
                # Let active workers finish; deletion triggers enqueue all draft artifacts.
                # Slot lock comes first to match claim/delete/worker lock ordering.
                c.execute("SELECT pg_advisory_xact_lock(hashtext('sgl_slots'))")
                c.execute("""DELETE FROM characters WHERE owner_sub IS NULL
                             AND draft_expires_at <= now() AND state IN ('ready', 'failed')""")
        cleaned = 0
        for _ in range(max_items):
            with self.db.tx() as c:
                row = c.execute(
                    """SELECT q.* FROM storage_cleanup q
                       WHERE q.next_at <= clock_timestamp() AND (%s::uuid IS NULL OR q.job_id = %s)
                         AND NOT EXISTS (SELECT 1 FROM jobs j WHERE j.id = q.job_id
                           AND (j.state NOT IN ('ready', 'failed') OR (q.kind = 'builds' AND j.state = 'ready')))
                       ORDER BY q.next_at, q.job_id, q.kind LIMIT 1 FOR UPDATE OF q SKIP LOCKED""",
                    (job_id, job_id)).fetchone()
                if row is None:
                    break
                locked = c.execute("SELECT pg_try_advisory_xact_lock(hashtextextended(%s, 0)) AS ok",
                                   (f"sgl_storage:{row['job_id']}",)).fetchone()['ok']
                if not locked:
                    # Upload still in progress; leave its intent durable, without starving other jobs.
                    c.execute("UPDATE storage_cleanup SET next_at = now() + interval '30 seconds' "
                              "WHERE job_id = %s AND kind = %s", (row['job_id'], row['kind']))
                    continue
                # Recheck after acquiring the writer lock: a queued upload may just have committed.
                live = c.execute("SELECT 1 FROM jobs WHERE id = %s AND "
                                 "(state NOT IN ('ready', 'failed') OR (%s = 'builds' AND state = 'ready'))",
                                 (row['job_id'], row['kind'])).fetchone()
                if live:
                    continue
                try:
                    self.storage.delete_prefix(f"{row['kind']}/{row['job_id']}/")
                except Exception as e:  # storage failures must never discard the durable intent
                    delay = min(30 * 2 ** min(row['failures'], 7), 3600)
                    c.execute("UPDATE storage_cleanup SET attempts = attempts + 1, failures = failures + 1, "
                              "last_error = %s, next_at = clock_timestamp() + make_interval(secs => %s) "
                              "WHERE job_id = %s AND kind = %s",
                              (type(e).__name__, delay, row['job_id'], row['kind']))
                    log.warning('cleanup failed for %s/%s: %s', row['kind'], row['job_id'], type(e).__name__)
                else:
                    c.execute("UPDATE storage_cleanup SET attempts = attempts + 1, failures = 0, "
                              "last_error = NULL, cleaned_at = clock_timestamp(), "
                              "next_at = clock_timestamp() + interval '1 day' WHERE job_id = %s AND kind = %s",
                              (row['job_id'], row['kind']))
                    cleaned += 1
        return cleaned

    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True, name='storage-cleanup')
        self.thread.start()

    def _run(self):
        while not self.stop.wait(self.interval):
            try:
                self.drain()
            except Exception:
                log.exception('storage cleanup database failure; retrying next sweep')

    def close(self):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=5)
