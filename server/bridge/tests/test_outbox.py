import json
import threading

import pytest

from sglbridge.api import ApiError, ApiUnavailable
from sglbridge.outbox import DurableRetryQueue, OutboxFull


def test_restart_replays_identical_unacknowledged_event(tmp_path):
    path = tmp_path / 'events.sqlite3'
    envelope = {'t': 'run', 'payload': {'event_id': 'stable-id'}, 'at': 'original-time'}
    sent = []

    def lost_response(item):
        sent.append(item)
        raise ApiUnavailable('response lost after commit')

    first = DurableRetryQueue(lost_response, path)
    first.put(envelope)
    envelope['payload']['event_id'] = 'caller-mutated-after-put'
    first.drain_once()
    first.close()
    second = DurableRetryQueue(sent.append, path)
    assert second.drain_once() == 1
    assert sent[0] == sent[1]
    assert sent[0]['payload']['event_id'] == 'stable-id'
    second.close()
    third = DurableRetryQueue(sent.append, path)
    assert len(third) == 0
    third.close()


def test_full_outbox_keeps_accepted_rows_and_stops_producer(tmp_path):
    fatal = []
    q = DurableRetryQueue(lambda _: None, tmp_path / 'events.sqlite3', maxlen=2, fatal=lambda: fatal.append(True))
    q.put({'n': 1})
    q.put({'n': 2})
    with pytest.raises(OutboxFull):
        q.put({'n': 3})
    assert fatal == [True] and len(q) == 2
    assert [json.loads(r[0])['n'] for r in q.db.execute('SELECT envelope FROM outbox ORDER BY id')] == [1, 2]
    q.close()


def test_permanent_rejection_is_retained_for_operator(tmp_path):
    def reject(_):
        raise ApiError(422, 'invalid event')
    q = DurableRetryQueue(reject, tmp_path / 'events.sqlite3')
    q.put({'t': 'run'})
    assert q.drain_once() == 0 and len(q) == 0
    assert '422' in q.db.execute('SELECT error FROM outbox').fetchone()[0]
    q.close()


def test_only_one_sender_and_one_owner(tmp_path):
    entered, release = threading.Event(), threading.Event()
    sent = []
    def send(item):
        entered.set()
        assert release.wait(2)
        sent.append(item)
    path = tmp_path / 'events.sqlite3'
    q = DurableRetryQueue(send, path)
    with pytest.raises(BlockingIOError):
        DurableRetryQueue(send, path)
    q.put({'t': 'run'})
    thread = threading.Thread(target=q.drain_once)
    thread.start()
    assert entered.wait(2)
    assert q.drain_once() == 0
    release.set()
    thread.join(2)
    assert sent == [{'t': 'run'}]
    q.close()
