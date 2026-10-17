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


def handle(conn, job, store, backend, cfg, log=print):
    """Run one claimed job and write its result. Returns True if it ended ready, False if it
    failed or was cancelled (character deleted mid-job: photos and builds/<job>/ are deleted)."""
    job_id, char_id = job["id"], job["character_id"]
    log(f"worker: job {job_id} ({job['name']!r})")

    def progress(state, step, text):
        try:
            db.update_job(conn, job_id, char_id, state=state, step=step, log=text)
        except db.JobGone as e:
            raise pipeline.JobCancelled(str(job_id)) from e
        except Exception as e:  # noqa: BLE001 - progress is best effort; the result write is not
            log(f"worker: progress update failed: {e}")

    def cancelled():
        log(f"worker: job {job_id} cancelled: its character was deleted")
        return False

    try:
        result = pipeline.run_job(job_id, job["name"], store, backend, cfg, progress, photos=job.get("photos"))
    except pipeline.JobCancelled:
        return cancelled()
    except pipeline.StepFailed as e:
        try:
            db.finish_job(conn, job_id, char_id, False, getattr(e, "log", str(e)), step=e.step,
                          error=str(e).splitlines()[0] if str(e) else None)
        except db.JobGone:
            return cancelled()
        log(f"worker: job {job_id} FAILED at {e.step}: {e}")
        return False
    try:
        slot = db.finish_job(conn, job_id, char_id, True, result["log"], spec=result["spec"],
                             artifacts=result["artifacts"])
    except db.JobGone:
        pipeline.discard_build(store, job_id, log)
        return cancelled()
    log(f"worker: job {job_id} ready -> builds/{job_id}/, "
        + (f"slot guest_{slot}" if slot else "no slot free yet (the API slots it later)"))
    return True


def recover(conn, worker, store, log=print):
    """Fail the jobs a previous run of this worker left half-done (and delete their photos)."""
    for j in db.orphaned_jobs(conn, worker):
        try:
            store.delete_prefix(f"photos/{j['id']}/")
        except Exception as e:  # noqa: BLE001
            log(f"worker: photo cleanup for {j['id']} failed: {e}")
        msg = f"worker {worker} restarted during step {j['step']}; please retry"
        try:
            db.finish_job(conn, j["id"], j["character_id"], False, msg, step=j["step"], error=msg)
        except db.JobGone:
            continue
        log(f"worker: marked orphaned job {j['id']} failed")


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
                recover(conn, worker, store)
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
