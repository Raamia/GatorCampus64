"""Allowlisted public operational projection; never serialize job rows wholesale."""
from datetime import datetime
from hashlib import sha256
import math

STEPS = ('queued', 'spec', 'face', 'build', 'export', 'validate', 'preview', 'store')
STATES = (*STEPS[:-1], 'ready', 'failed')
LIMIT = 12
CACHE_SECONDS = 5


def elapsed(start, end):
    if start is None or end is None:
        return None
    return round(max(0, (end - start).total_seconds()), 1)


def timestamp(value):
    try:
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.utcoffset() is not None else None
    except (TypeError, ValueError):
        return None


def public_job(row, observed):
    state = row['state'] if row['state'] in STATES else 'unknown'
    step = row['step'] if row['step'] in (*STEPS, 'ready') else None
    timings = []
    history = row['step_history'] if isinstance(row['step_history'], list) else []
    for entry in history[-64:]:
        if not isinstance(entry, dict) or entry.get('step') not in STEPS:
            continue
        start = timestamp(entry.get('started'))
        end = timestamp(entry.get('finished'))
        if start is None or (entry.get('finished') is not None and end is None):
            continue
        # Do not keep a terminal job's clock running if legacy data lacks an end.
        running = end is None and state not in ('ready', 'failed', 'unknown')
        seconds = elapsed(start, end or (observed if running else row['finished']))
        timings.append({'step': entry['step'], 'seconds': seconds, 'running': running})
    return {'id': sha256(str(row['id']).encode()).hexdigest()[:12], 'state': state, 'step': step,
            'elapsed_seconds': elapsed(row['created'], row['finished'] or observed),
            'steps': timings}


def metric(value, maximum):
    # Reject booleans, negative/non-finite numbers and impossible driver output.
    if type(value) not in (int, float) or not 0 <= value <= maximum or not math.isfinite(value):
        return None
    return round(value, 1)


def public_gpu(row):
    devices = []
    if row['available'] and isinstance(row['gpus'], list):
        for index, gpu in enumerate(row['gpus'][:16]):
            if not isinstance(gpu, dict):
                continue
            used = metric(gpu.get('memory_used_mib'), 1_048_576)
            total = metric(gpu.get('memory_total_mib'), 1_048_576)
            if total == 0:
                total = None
            if used is not None and total is not None and used > total:
                used = None
            devices.append({'index': index, 'utilization_gpu_pct': metric(gpu.get('utilization_gpu_pct'), 100),
                            'memory_used_mib': used, 'memory_total_mib': total})
    return {'id': sha256(row['worker'].encode()).hexdigest()[:12],
            'observed_at': row['observed_at'].isoformat(),
            'available': bool(row['available'] and devices), 'gpus': devices}


def snapshot(conn):
    observed = conn.execute('SELECT clock_timestamp() AS at').fetchone()['at']
    rows = conn.execute('''SELECT id, state, step, created, finished, step_history
                           FROM jobs ORDER BY created DESC, id DESC LIMIT %s''', (LIMIT,)).fetchall()
    gpu_rows = conn.execute('''SELECT worker, observed_at, available, gpus FROM worker_gpu_status
                               WHERE observed_at > clock_timestamp() - interval '24 hours'
                               ORDER BY observed_at DESC, worker LIMIT 8''').fetchall()
    return {'observed_at': observed.isoformat(), 'jobs': [public_job(row, observed) for row in rows],
            'gpu': [public_gpu(row) for row in gpu_rows]}
