from datetime import datetime, timedelta, timezone
import uuid


def snapshot(**changes):
    now = datetime.now(timezone.utc)
    return {"session_id": str(uuid.uuid4()), "observed_at": now.isoformat(), "online": True,
            "since": (now - timedelta(minutes=5)).isoformat(), "version": "test",
            "players": [{"gi": 1, "name": "Ali"}], **changes}


def test_idle_heartbeat_and_expiry(make_client, bridge, conn):
    client = make_client(status_stale_secs=60)
    assert client.get('/status').json()['online'] is False
    body = snapshot()
    assert client.post('/presence', json=body, headers=bridge).json() == {"accepted": True}
    status = client.get('/status').json()
    assert status['online'] and status['players'] == body['players'] and status['version'] == 'test'
    assert status['last_event_at'] is None
    conn.execute("UPDATE server_presence SET observed_at = now() - interval '61 seconds'")
    assert not client.get('/status').json()['online']
    assert client.get('/status').json()['players'] == []
    assert client.post('/presence', json=snapshot(players=[]), headers=bridge).status_code == 200
    assert client.get('/status').json()['online']  # quiet, empty game still alive
    assert conn.execute('SELECT count(*) AS n FROM events').fetchone()['n'] == 0


def test_reordering_duplicates_and_history_do_not_revive(client, bridge, conn):
    old = snapshot()
    assert client.post('/presence', json=old, headers=bridge).json()['accepted']
    down = snapshot(online=False)
    assert client.post('/presence', json=down, headers=bridge).json()['accepted']
    before = conn.execute('SELECT received_at FROM server_presence').fetchone()
    for body in (old, down):
        assert client.post('/presence', json=body, headers=bridge).json() == {'accepted': False}
    assert conn.execute('SELECT received_at FROM server_presence').fetchone() == before
    client.post('/events', json=[{'t': 'hello'}, {'t': 'join', 'gi': 2, 'name': 'Old'}], headers=bridge)
    assert not client.get('/status').json()['online']
    assert client.get('/status').json()['players'] == []
    new = snapshot(players=[{'gi': 2, 'name': 'New'}])
    client.post('/presence', json=new, headers=bridge)
    client.post('/events', json={'t': 'exit'}, headers=bridge)
    assert client.get('/status').json()['players'] == new['players']


def test_presence_validation_and_auth(client, bridge, auth):
    now = datetime.now(timezone.utc)
    for body in [snapshot(observed_at=(now - timedelta(minutes=1)).isoformat()),
                 snapshot(observed_at=(now + timedelta(minutes=1)).isoformat()),
                 snapshot(observed_at='2026-01-01T00:00:00'),
                 snapshot(players=[{'gi': 1, 'name': 'a'}, {'gi': 1, 'name': 'b'}]),
                 snapshot(players=[{'gi': 256, 'name': 'a'}]),
                 snapshot(version='x' * 65)]:
        assert client.post('/presence', json=body, headers=bridge).status_code == 422
    assert client.post('/presence', json=snapshot()).status_code == 401
    assert client.post('/presence', json=snapshot(), headers=auth(scope='bridge')).status_code == 403
    assert client.post('/presence', json=snapshot(), headers=auth()).status_code == 403


def test_zero_ttl_still_expires(make_client, bridge, conn):
    client = make_client(status_stale_secs=0)
    client.post('/presence', json=snapshot(), headers=bridge)
    conn.execute("UPDATE server_presence SET observed_at = now() - interval '91 seconds'")
    assert not client.get('/status').json()['online']
