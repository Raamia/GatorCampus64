"""Gatorize Me GPU worker: claims queued jobs from Postgres and runs the character pipeline.

One job at a time per process (one Blender per GPU VM); run more VMs to scale. SIGTERM/SIGINT
stop the loop after the current job.

  python3 worker.py            # loop forever
  python3 worker.py --once     # handle at most one job, then exit (smoke tests)

Env: DATABASE_URL, WORKER_NAME (default: hostname), POLL_SECONDS (default 3), plus the
pipeline (SGL_REPO, BLENDER, WORK_ROOT, BUILD_TIMEOUT, KEEP_WORKDIR, VLM_REQUIRED,
USE_OPENCV), storage (S3_* or STORAGE_DIR) and model (VLM_BASE_URL, VLM_API_KEY, VLM_MODEL)
settings, see README.md.
"""
import argparse
import os
import signal
import socket
import sys
import threading
import time

import db
import pipeline
import spec_ai
import storage as storage_mod

_stop = False


def _on_signal(signum, _frame):
    global _stop
    _stop = True
    print(f"worker: signal {signum}, stopping after the current job", flush=True)


class LeaseWatch:
    """Renew on a dedicated connection, including during quiet model/Blender calls.

    Any renewal error cancels this attempt. Database fencing is still authoritative if the
    process stalls or cannot reach Postgres. Connections have bounded connect/statement waits.
    """
    def __init__(self, conn, job):
        self.dsn, self.password, self.job = conn.info.dsn, conn.info.password, job
        self.stop = threading.Event()
        self.lost = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True, name="worker-lease")

    def check(self):
        if self.lost.is_set():
            raise pipeline.JobCancelled("worker lease lost")

    def run(self):
        try:
            with db.psycopg.connect(self.dsn, password=self.password, autocommit=True, row_factory=db.dict_row,
                                   connect_timeout=5, options="-c statement_timeout=10000 -c lock_timeout=5000") as conn:
                while not self.stop.wait(db.RENEW_SECONDS):
                    db.renew_lease(conn, self.job["id"], self.job["character_id"], self.job["lease_token"])
        except Exception:
            self.lost.set()


def handle(conn, job, store, backend, cfg, log=print):
    watch = LeaseWatch(conn, job)
    watch.thread.start()
    try:
        return _handle(conn, job, store, backend, cfg, log, watch.check)
    finally:
        watch.stop.set()
        watch.thread.join(timeout=16)


def _handle(conn, job, store, backend, cfg, log, check):
    """Run one claimed job and write its result. Returns True if it ended ready, False if it
    failed or was cancelled (character deleted mid-job: photos and builds/<job>/ are deleted)."""
    job_id, char_id = job["id"], job["character_id"]
    log(f"worker: job {job_id} ({job['name']!r})")

    def progress(state, step, text):
        check()
        try:
            db.update_job(conn, job_id, char_id, state=state, step=step, log=text, lease_token=job["lease_token"])
        except db.JobGone as e:
            raise pipeline.JobCancelled(str(job_id)) from e
        except Exception as e:  # noqa: BLE001
            raise pipeline.JobCancelled("cannot verify worker lease") from e

    def cancelled():
        log(f"worker: job {job_id} cancelled: character deleted or worker lease lost")
        return False

    try:
        result = pipeline.run_job(job_id, job["name"], store, backend, cfg, progress, photos=job.get("photos"), check=check)
    except pipeline.JobCancelled:
        return cancelled()
    except pipeline.StepFailed as e:
        try:
            db.finish_job(conn, job_id, char_id, False, getattr(e, "log", str(e)), step=e.step,
                          error=str(e).splitlines()[0] if str(e) else None, lease_token=job["lease_token"])
        except db.JobGone:
            return cancelled()
        log(f"worker: job {job_id} FAILED at {e.step}: {e}")
        return False
    try:
        slot = db.finish_job(conn, job_id, char_id, True, result["log"], spec=result["spec"],
                             artifacts=result["artifacts"], lease_token=job["lease_token"])
    except db.JobGone:
        pipeline.discard_build(store, job_id, log)
        return cancelled()
    log(f"worker: job {job_id} ready -> builds/{job_id}/, "
        + (f"slot guest_{slot}" if slot else "no slot free yet (the API slots it later)"))
    return True


def recover(conn, store, log=print):
    """Sweep all hosts on every poll, then clean objects only for committed expirations."""
    for job in db.expire_jobs(conn):
        for prefix in (f"photos/{job['id']}/", f"builds/{job['id']}/"):
            try:
                store.delete_prefix(prefix)
            except Exception as e:  # noqa: BLE001
                log(f"worker: cleanup for {prefix} failed: {e}")
        log(f"worker: marked expired job {job['id']} failed")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args(argv)
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)

    worker = os.environ.get("WORKER_NAME") or socket.gethostname()
    poll = float(os.environ.get("POLL_SECONDS", "3"))
    cfg = pipeline.Config.from_env()
    store = storage_mod.from_env()
    backend = spec_ai.OpenAICompatBackend.from_env()
    print(f"worker {worker}: repo {cfg.repo}, blender {cfg.blender}, "
          f"model {os.environ.get('VLM_MODEL') or '-'} @ {os.environ.get('VLM_BASE_URL') or 'none'}", flush=True)
    conn = None
    while not _stop:
        try:
            if conn is None or conn.closed:
                conn = db.connect(os.environ["DATABASE_URL"])
            recover(conn, store)
            job = db.claim_job(conn, worker)
            if job is None:
                if args.once:
                    return 0
                time.sleep(poll)
                continue
            handle(conn, job, store, backend, cfg)
            if args.once:
                return 0
        except Exception as e:  # noqa: BLE001 - DB hiccups: reconnect and keep going
            print(f"worker: error: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
            try:
                if conn is not None:
                    conn.close()
            except Exception:  # noqa: BLE001
                pass
            conn = None
            if args.once:
                return 1
            time.sleep(max(poll, 5))
    return 0


if __name__ == "__main__":
    sys.exit(main())
