import hashlib
import hmac
import time

from sgl_api.deepspace import encode, sign
from .test_accounts import remove

SECRET = 'identity-test-secret-long-enough-12345'


def proof(auth, *, sub='auth0|ali', uid='ds-ali', action='link', token_hash=None, timestamp=None, nonce=None):
    headers = auth(sub=sub)
    token = headers['Authorization'].split()[1]
    body = encode({'user_id': uid, 'action': action, 'token_hash': token_hash or hashlib.sha256(token.encode()).hexdigest()})
    key = hmac.new(SECRET.encode(), b'sgl-identity-v1', hashlib.sha256).hexdigest()
    headers.update(sign(key, body, timestamp, nonce))
    return {'headers': headers, 'content': body}


def test_two_provider_proof_ownership_conflicts_and_unlink(make_client, auth, conn):
    client = make_client(deepspace_ingest_secret=SECRET)
    request = proof(auth)
    assert client.post('/account/identity', **request).json() == {'linked': True, 'conflict': False}
    assert client.post('/account/identity', **request).status_code == 409
    assert client.post('/account/identity', **proof(auth, sub='auth0|bo')).status_code == 409
    assert client.post('/account/identity', **proof(auth, uid='ds-bo')).status_code == 409
    assert client.post('/account/identity', **proof(auth, sub='auth0|bo', action='unlink')).status_code == 200
    assert conn.execute('SELECT sub FROM identity_links').fetchone()['sub'] == 'auth0|ali'
    assert client.post('/account/identity', **proof(auth, action='unlink')).json()['linked'] is False
    assert client.post('/account/identity', **proof(auth, sub='auth0|bo')).status_code == 200


def test_invalid_or_swapped_proof_fails_closed(make_client, auth, conn):
    client = make_client(deepspace_ingest_secret=SECRET)
    forged = proof(auth)
    forged['headers']['X-SGL-Signature'] = 'v1=' + '0' * 64
    assert client.post('/account/identity', **forged).status_code == 401
    assert client.post('/account/identity', **proof(auth, token_hash='0' * 64)).status_code == 401
    assert client.post('/account/identity', **proof(auth, timestamp=str(int(time.time()) - 400))).status_code == 401
    changed = proof(auth)
    changed['content'] = changed['content'].replace(b'ds-ali', b'ds-bob')
    assert client.post('/account/identity', **changed).status_code == 401
    assert client.post('/account/identity', **proof(auth, sub='bridge@clients')).status_code == 403
    assert not conn.execute('SELECT 1 FROM identity_links').fetchone()


def test_deletion_enqueues_linked_offline_cleanup_and_unlink_preserves_it(make_client, auth, conn):
    client = make_client(deepspace_ingest_secret=SECRET)
    assert client.post('/account/identity', **proof(auth)).status_code == 200
    assert remove(client, auth(sub='auth0|ali')).status_code == 202
    row = conn.execute('SELECT deepspace_user, before_ms FROM account_erases').fetchone()
    assert row['deepspace_user'] == 'ds-ali'
    assert abs(row['before_ms'] - time.time() * 1000) < 3000
    assert not conn.execute('SELECT 1 FROM identity_links').fetchone()
    assert client.post('/account/identity', **proof(auth, sub='auth0|bo', uid='ds-bo')).status_code == 200
    assert client.post('/account/identity', **proof(auth, sub='auth0|bo', uid='ds-bo', action='unlink')).status_code == 200
    assert remove(client, auth(sub='auth0|bo')).status_code == 202
    assert conn.execute('SELECT count(*) AS n FROM account_erases').fetchone()['n'] == 1


def test_linked_erasure_retries_and_is_signed(make_client, auth, conn):
    import httpx
    received = []
    status = [503]
    def remote(request):
        expected = sign(SECRET, request.content, request.headers['x-sgl-timestamp'], request.headers['x-sgl-nonce'])
        assert request.headers['x-sgl-signature'] == expected['X-SGL-Signature']
        received.append(__import__('json').loads(request.content))
        return httpx.Response(status[0], json={'success': status[0] == 200})
    client = make_client(deepspace_ingest_secret=SECRET, deepspace_app_url='https://board.test',
                         transport=httpx.MockTransport(remote))
    client.post('/account/identity', **proof(auth))
    remove(client, auth(sub='auth0|ali'))
    assert client.app.state.pusher.drain() == 0
    assert conn.execute('SELECT last_error FROM account_erases').fetchone()['last_error'] == 'HTTP 503'
    conn.execute('UPDATE account_erases SET next_at = now()')
    status[0] = 200
    assert client.app.state.pusher.drain() == 1
    assert received[-1]['deleteUserRuns']['userId'] == 'ds-ali'
    assert conn.execute('SELECT sent_at FROM account_erases').fetchone()['sent_at'] is not None
