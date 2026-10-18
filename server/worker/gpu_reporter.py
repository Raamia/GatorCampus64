"""Bounded, best-effort GPU reporting, independent of job progress and leases."""
import threading

import db
import gpu_telemetry

INTERVAL_SECONDS = 10


class GpuReporter:
    def __init__(self, url, worker, log=print):
        self.url, self.worker, self.log = url, worker, log
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True, name="worker-gpu")

    def sample(self):
        # Never share the job connection: slow or failed diagnostics must not
        # hold up a build, lease renewal, or queue claim.
        sample = gpu_telemetry.capture('periodic')
        with db.psycopg.connect(self.url, autocommit=True, connect_timeout=3,
                               options="-c statement_timeout=3000 -c lock_timeout=1000") as conn:
            db.record_gpu(conn, self.worker, sample)

    def run(self):
        failing = False
        while not self.stop.is_set():
            try:
                self.sample()
                if failing:
                    self.log('worker: GPU reporting recovered')
                failing = False
            except Exception:
                # Do not print database credentials, driver output or host paths.
                if not failing:
                    self.log('worker: GPU reporting unavailable; retrying in 10 seconds')
                failing = True
            self.stop.wait(INTERVAL_SECONDS)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.stop.set()
        self.thread.join(timeout=12)
