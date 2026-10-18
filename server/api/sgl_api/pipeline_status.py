"""Allowlisted public operational projection; never serialize job rows wholesale."""
from datetime import datetime
from hashlib import sha256

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


def snapshot(conn):
    observed = conn.execute('SELECT clock_timestamp() AS at').fetchone()['at']
    rows = conn.execute('''SELECT id, state, step, created, finished, step_history
                           FROM jobs ORDER BY created DESC, id DESC LIMIT %s''', (LIMIT,)).fetchall()
    return {'observed_at': observed.isoformat(), 'jobs': [public_job(row, observed) for row in rows]}
