import time
import uuid

from .helpers import upload, run_job
from .test_runs import link, post, run_ev, ds  # noqa: F401


def remove(client, headers):
    return client.request('DELETE', '/account', headers=headers, json={'confirm': 'DELETE'})


def test_delete_removes_gator_data_runs_and_blocks_old_sessions(client, auth, bridge, conn, s3):
    h = auth(sub='auth0|ali')
    made = upload(client, h).json()
    run_job(conn, s3)
    post(client, bridge, {'t': 'hello'})
    link(client, bridge, 'auth0|ali', 1, 'Ali')
    link(client, bridge, 'auth0|bo', 2, 'Bo')
    post(client, bridge, run_ev(players=(('1', 'Ali'), ('2', 'Bo'))))
    # The bridge includes Ali's identity even though only Bo participated.
    post(client, bridge, run_ev(players=(('2', 'Bo'),)))
    result = remove(client, h)
    assert result.status_code == 202, result.text
    assert result.json()['removed_runs'] == 1
    assert result.json()['provider_accounts'] == 'unchanged'
    assert not conn.execute("SELECT 1 FROM users WHERE sub = 'auth0|ali'").fetchone()
    assert not conn.execute('SELECT 1 FROM characters WHERE id = %s', (made['character_id'],)).fetchone()
    assert conn.execute('SELECT count(*) AS n FROM run_erases').fetchone()['n'] == 1
    assert conn.execute('SELECT subs FROM runs').fetchone()['subs'] == ['auth0|bo']
    assert conn.execute('SELECT kind FROM deploys ORDER BY id DESC LIMIT 1').fetchone()['kind'] == 'placeholder'
    assert client.get('/me', headers=h).status_code == 403
    assert client.post('/links', headers=bridge, json={'sub': 'auth0|ali', 'gi': 1, 'coopdx_name': 'Ali'}).status_code == 403
    before = conn.execute('SELECT count(*) AS n FROM events').fetchone()['n']
    # A delayed run referring to an erased login is acknowledged without retaining its names.
    post(client, bridge, run_ev())
    assert conn.execute('SELECT count(*) AS n FROM events').fetchone()['n'] == before
    assert conn.execute('SELECT count(*) AS n FROM runs').fetchone()['n'] == 1
    client.app.state.cleaner.drain()
    assert client.post('/account/register', headers=h).status_code == 401
    assert client.post('/account/register', headers=auth(sub='auth0|ali', iat=int(time.time()) + 2)).status_code == 200
    assert conn.execute('SELECT count(*) AS n FROM characters').fetchone()['n'] == 0
    assert client.get('/me', headers=h).status_code == 401
    assert client.post('/link-codes', headers=h).status_code == 401
    assert client.get('/me', headers=auth(sub='auth0|ali', iat=int(time.time()) + 2)).status_code == 200
    for event in conn.execute("SELECT payload FROM events WHERE t = 'run'"):
        assert 'Ali' not in str(event['payload'])


def test_unlink_revokes_future_ranking_but_preserves_past_runs(client, auth, bridge, conn):
    post(client, bridge, {'t': 'hello'})
    link(client, bridge, 'auth0|ali', 1, 'Ali')
    post(client, bridge, run_ev())
    lid = client.game_links['1']['link_id']
    h = auth(sub='auth0|ali')
    client.post('/link-codes', headers=h)
    assert client.delete('/links', headers=h).json() == {'unlinked': True}
    assert client.post('/links/check', headers=bridge, json={'ids': [lid]}).json() == {'active': []}
    assert not conn.execute('SELECT 1 FROM link_codes').fetchone()
    post(client, bridge, run_ev())
    assert [r['ranked'] for r in conn.execute('SELECT ranked FROM runs ORDER BY id')] == [True, False]


def test_deletion_requires_owner_confirmation_and_recent_user_token(client, auth, bridge, conn):
    assert remove(client, {}).status_code == 401
    assert remove(client, bridge).status_code == 403
    assert remove(client, auth(iat=int(time.time()) - 600)).status_code == 401
    assert client.request('DELETE', '/account', headers=auth(), json={'confirm': 'no'}).status_code == 422
    assert not conn.execute('SELECT 1 FROM deleted_accounts').fetchone()


def test_remote_deletion_retries_and_outlives_run(ds, auth, bridge, conn):
    client, remote = ds
    post(client, bridge, {'t': 'hello'})
    link(client, bridge, 'auth0|ali', 1, 'Ali')
    post(client, bridge, run_ev())
    uid = str(conn.execute('SELECT uid FROM runs').fetchone()['uid'])
    assert remove(client, auth(sub='auth0|ali')).status_code == 202
    assert not conn.execute('SELECT 1 FROM runs').fetchone()
    remote.status = 503
    assert client.app.state.pusher.drain() == 0
    assert conn.execute('SELECT last_error, sent_at FROM run_erases').fetchone() == {'last_error': 'HTTP 503', 'sent_at': None}
    remote.status = 200
    conn.execute('UPDATE run_erases SET next_at = now()')
    assert client.app.state.pusher.drain() == 1
    assert remote.bodies()[-1] == {'v': 1, 'deleteRunId': uid}
    assert conn.execute('SELECT sent_at FROM run_erases').fetchone()['sent_at'] is not None


def test_legacy_spectator_metadata_is_scrubbed_without_erasing_run(client, auth, bridge, conn):
    from psycopg.types.json import Jsonb
    post(client, bridge, {'t': 'hello'})
    link(client, bridge, 'auth0|ali', 1, 'Ali')
    link(client, bridge, 'auth0|bo', 2, 'Bo')
    post(client, bridge, run_ev(players=(('2', 'Bo'),)))
    row = conn.execute("SELECT id, payload FROM events WHERE t = 'run'").fetchone()
    payload = row['payload']
    payload['identities'] = dict(client.game_links)
    payload['event_id'] = 'legacy-invalid-uuid'
    conn.execute('UPDATE events SET payload = %s WHERE id = %s', (Jsonb(payload), row['id']))
    assert remove(client, auth(sub='auth0|ali')).json()['removed_runs'] == 0
    assert 'Ali' not in str(conn.execute('SELECT payload FROM events WHERE id = %s', (row['id'],)).fetchone())
    assert conn.execute('SELECT subs FROM runs').fetchone()['subs'] == ['auth0|bo']
