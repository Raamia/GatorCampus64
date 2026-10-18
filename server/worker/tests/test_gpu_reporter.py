from datetime import datetime, timezone
import threading

import db
import gpu_reporter


def test_reporter_persists_idle_readings_and_replaces_old_sample(pg, monkeypatch):
    sample = {'available': True, 'gpus': [{'name': 'private-name', 'utilization_gpu_pct': 0,
              'memory_used_mib': 9000, 'memory_total_mib': 16384}]}
    monkeypatch.setattr(gpu_reporter.gpu_telemetry, 'capture', lambda point: sample)
    reporter = gpu_reporter.GpuReporter(pg, 'private-worker')
    with db.connect(pg) as conn:
        conn.execute("INSERT INTO worker_gpu_status(worker, observed_at, available) VALUES ('old', now() - interval '2 days', false)")
    reporter.sample()
    with db.connect(pg) as conn:
        rows = conn.execute('SELECT * FROM worker_gpu_status').fetchall()
        assert len(rows) == 1
        row = rows[0]
        assert row['available'] and row['gpus'][0]['utilization_gpu_pct'] == 0
        assert 'name' not in row['gpus'][0]
        assert (datetime.now(timezone.utc) - row['observed_at']).total_seconds() < 5
    sample.update(available=False, gpus=[])
    reporter.sample()
    with db.connect(pg) as conn:
        rows = conn.execute('SELECT * FROM worker_gpu_status').fetchall()
        assert len(rows) == 1 and not rows[0]['available'] and rows[0]['gpus'] == []


def test_failure_is_isolated_retried_and_logs_no_secrets(monkeypatch):
    messages, attempts = [], []
    reporter = gpu_reporter.GpuReporter('unused', 'worker', messages.append)
    def sample():
        attempts.append(1)
        if len(attempts) < 3:
            raise RuntimeError('private-password')
        reporter.stop.set()
    monkeypatch.setattr(reporter, 'sample', sample)
    monkeypatch.setattr(gpu_reporter, 'INTERVAL_SECONDS', 0)
    reporter.run()
    assert len(attempts) == 3
    assert messages == ['worker: GPU reporting unavailable; retrying in 10 seconds', 'worker: GPU reporting recovered']


def test_reporting_runs_independently_and_stops_promptly(monkeypatch):
    sampled = threading.Event()
    reporter = gpu_reporter.GpuReporter('unused', 'worker')
    monkeypatch.setattr(reporter, 'sample', sampled.set)
    with reporter:
        assert sampled.wait(2)
        assert reporter.thread.is_alive()
    assert not reporter.thread.is_alive()
