from datetime import datetime, timezone
import hashlib

from psycopg.types.json import Jsonb

from sgl_api import pipeline_status


def seed(conn, count=1):
    conn.execute("INSERT INTO users (sub, nickname) VALUES ('private-account', 'private-name')")
    cid = conn.execute("INSERT INTO characters (owner_sub, name) VALUES ('private-account', 'Secret') RETURNING id").fetchone()['id']
    return [conn.execute("""INSERT INTO jobs (character_id, log, error, photos, artifacts, worker)
        VALUES (%s, 'private-log', 'private-error', ARRAY['private-photo'], %s, 'private-host') RETURNING id""",
        (cid, Jsonb({'portrait': 'private-url'}))).fetchone()['id'] for _ in range(count)]


def test_public_allowlist_limit_order_and_read_only(client, conn):
    ids = seed(conn, 15)
    before = conn.execute('SELECT * FROM jobs ORDER BY id').fetchall()
    response = client.get('/pipeline/status?limit=100000', headers={'Authorization': 'Bearer invalid'})
    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'public, max-age=5'
    data = response.json()
    assert set(data) == {'observed_at', 'jobs', 'gpu'}
    assert data['gpu'] == []
    assert len(data['jobs']) == 12
    expected = sorted(before, key=lambda row: (row['created'], row['id']), reverse=True)[:12]
    assert [row['id'] for row in data['jobs']] == [hashlib.sha256(str(row['id']).encode()).hexdigest()[:12] for row in expected]
    for row in data['jobs']:
        assert set(row) == {'id', 'state', 'step', 'elapsed_seconds', 'steps'}
        assert row['state'] == 'queued'
        assert row['steps'][0]['step'] == 'queued' and row['steps'][0]['running']
        assert set(row['steps'][0]) == {'step', 'seconds', 'running'}
    assert 'private' not in response.text and 'Secret' not in response.text
    assert all(str(jid) not in response.text for jid in ids)
    assert before == conn.execute('SELECT * FROM jobs ORDER BY id').fetchall()


def test_empty_and_cache(client, conn, monkeypatch):
    assert client.get('/pipeline/status').json()['jobs'] == []
    seed(conn)
    assert client.get('/pipeline/status').json()['jobs'] == []
    original = pipeline_status.snapshot
    # Expire just this module's cache TTL by advancing the app's monotonic clock.
    import sgl_api.app as app_module
    clock = app_module.time.monotonic
    monkeypatch.setattr(app_module.time, 'monotonic', lambda: clock() + 6)
    assert len(client.get('/pipeline/status').json()['jobs']) == 1
    monkeypatch.setattr(pipeline_status, 'snapshot', lambda c: (_ for _ in ()).throw(AssertionError('cache miss')))
    assert len(client.get('/pipeline/status').json()['jobs']) == 1
    monkeypatch.setattr(pipeline_status, 'snapshot', original)


def test_transition_timing_retry_failure_and_log_updates(conn):
    jid, = seed(conn)
    def job():
        return conn.execute('SELECT * FROM jobs WHERE id=%s', (jid,)).fetchone()
    def step(state, value):
        conn.execute('UPDATE jobs SET state=%s, step=%s WHERE id=%s', (state, value, jid))
    step('spec', 'spec')
    original = job()['step_history']
    conn.execute("UPDATE jobs SET state='spec', step='spec', log='more output' WHERE id=%s", (jid,))
    assert job()['step_history'] == original
    step('build', 'build')
    step('export', 'export')
    step('build', 'build')
    conn.execute("UPDATE jobs SET state='failed', finished=clock_timestamp() WHERE id=%s", (jid,))
    row = job()
    data = pipeline_status.public_job(row, datetime.now(timezone.utc))
    assert [item['step'] for item in data['steps']] == ['queued', 'spec', 'build', 'export', 'build']
    assert all(not item['running'] and item['seconds'] >= 0 for item in data['steps'])
    assert all(item['finished'] for item in row['step_history'])
    assert data['state'] == 'failed' and data['step'] == 'build'


def test_ready_and_bounded_history(conn):
    jid, = seed(conn)
    for i in range(70):
        state = 'build' if i % 2 else 'export'
        conn.execute('UPDATE jobs SET state=%s, step=%s WHERE id=%s', (state, state, jid))
    conn.execute("UPDATE jobs SET state='ready', step='ready', finished=clock_timestamp() WHERE id=%s", (jid,))
    row = conn.execute('SELECT * FROM jobs WHERE id=%s', (jid,)).fetchone()
    assert len(row['step_history']) == 64
    assert all(entry['finished'] for entry in row['step_history'])


def test_legacy_and_untrusted_history(conn):
    jid, = seed(conn)
    history = [{'step': 'private-name', 'started': '2026-10-17T00:00:00+00:00'},
               {'step': 'build', 'started': 'bad-date', 'private': 'value'},
               {'step': 'spec', 'started': '2026-10-17T00:00:00'}, 'private']
    conn.execute('UPDATE jobs SET step_history=%s WHERE id=%s', (Jsonb(history), jid))
    row = conn.execute('SELECT * FROM jobs WHERE id=%s', (jid,)).fetchone()
    assert pipeline_status.public_job(row, datetime.now(timezone.utc))['steps'] == []
    conn.execute("UPDATE jobs SET step_history='[]' WHERE id=%s", (jid,))
    conn.execute("UPDATE jobs SET state='build', step='build' WHERE id=%s", (jid,))
    row = conn.execute('SELECT * FROM jobs WHERE id=%s', (jid,)).fetchone()
    assert [entry['step'] for entry in row['step_history']] == ['build']


def test_gpu_projection_is_public_bounded_private_and_read_only(client, conn):
    metrics = [{'name': 'private-device', 'utilization_gpu_pct': 0, 'memory_used_mib': 12000,
                'memory_total_mib': 16384, 'serial': 'private-serial', 'processes': ['private-account']},
               {'utilization_gpu_pct': None, 'memory_used_mib': None, 'memory_total_mib': None}]
    for i in range(10):
        conn.execute('INSERT INTO worker_gpu_status(worker, available, gpus) VALUES (%s, true, %s)',
                     (f'private-host-{i}', Jsonb(metrics)))
    conn.execute("INSERT INTO worker_gpu_status(worker, observed_at, available) VALUES ('private-expired', now() - interval '2 days', false)")
    before = conn.execute('SELECT * FROM worker_gpu_status ORDER BY worker').fetchall()
    response = client.get('/pipeline/status')
    assert response.status_code == 200
    gpu = response.json()['gpu']
    assert len(gpu) == 8
    assert 'private' not in response.text
    for reading in gpu:
        assert set(reading) == {'id', 'observed_at', 'available', 'gpus'}
        assert len(reading['id']) == 12 and reading['available']
        assert reading['gpus'] == [
            {'index': 0, 'utilization_gpu_pct': 0, 'memory_used_mib': 12000, 'memory_total_mib': 16384},
            {'index': 1, 'utilization_gpu_pct': None, 'memory_used_mib': None, 'memory_total_mib': None}]
    assert before == conn.execute('SELECT * FROM worker_gpu_status ORDER BY worker').fetchall()


def test_gpu_missing_unavailable_stale_and_invalid_values(client, conn):
    conn.execute("""INSERT INTO worker_gpu_status(worker, observed_at, available, gpus)
        VALUES ('private-offline', now() - interval '1 hour', false, %s)""", (Jsonb([{'name': 'secret'}]),))
    row = client.get('/pipeline/status').json()['gpu'][0]
    assert not row['available'] and row['gpus'] == []
    assert (datetime.now(timezone.utc) - datetime.fromisoformat(row['observed_at'])).total_seconds() > 3500
    base = dict(worker='private', observed_at=datetime.now(timezone.utc), available=True)
    for bad in (True, 'secret', -1, float('nan'), float('inf'), 1_048_577, 10 ** 1000):
        projected = pipeline_status.public_gpu({**base, 'gpus': [dict(utilization_gpu_pct=bad, memory_used_mib=bad, memory_total_mib=bad)]})
        assert projected['gpus'][0] == dict(index=0, utilization_gpu_pct=None, memory_used_mib=None, memory_total_mib=None)
    projected = pipeline_status.public_gpu({**base, 'gpus': [dict(utilization_gpu_pct=101, memory_used_mib=5, memory_total_mib=2)]})
    assert projected['gpus'][0] == dict(index=0, utilization_gpu_pct=None, memory_used_mib=None, memory_total_mib=2)
    assert not pipeline_status.public_gpu({**base, 'gpus': ['secret']})['available']
