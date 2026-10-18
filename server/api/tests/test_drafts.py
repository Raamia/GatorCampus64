"""Anonymous capability privacy and the authenticated boundary to the game."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256

import pytest
from psycopg.types.json import Jsonb

from sgl_api.cleanup import Cleaner
from sgl_api.db import Database
from sgl_api.storage import Storage
from .conftest import BUCKET, make_settings
from .helpers import claim, finish, upload

KEY = 'ab' * 32
GUEST = {'Authorization': f'Guest {KEY}'}
OTHER = {'Authorization': 'Guest ' + 'cd' * 32}


def draft(client):
    response = upload(client, GUEST)
    assert response.status_code == 201, response.text
    return response.json()


def test_private_creation_preview_and_restore(client, conn, s3, auth):
    created = draft(client)
    assert created['requires_login'] is True
    row = conn.execute('SELECT * FROM characters').fetchone()
    assert row['owner_sub'] is None and row['slot'] is None
    assert row['draft_token_hash'] == sha256(KEY.encode()).hexdigest()
    assert conn.execute('SELECT count(*) AS n FROM users').fetchone()['n'] == 0
    listed = client.get('/drafts', headers=GUEST).json()['characters']
    assert len(listed) == 1 and listed[0]['job_id'] == created['job_id']
    assert 'draft_token_hash' not in listed[0]
    assert client.get('/drafts', headers=OTHER).json()['characters'] == []
    job = finish(conn, s3, claim(conn))
    assert job['slot'] is None
    conn.execute('UPDATE jobs SET artifacts = artifacts || %s WHERE id = %s',
                 (Jsonb({'browser_model': f"builds/{job['id']}/preview.glb"}), job['id']))
    response = client.get('/jobs/' + created['job_id'], headers=GUEST)
    assert response.status_code == 200
    info = response.json()
    assert info['requires_login'] and info['draft_expires_at']
    assert info['previews'] and '/preview.glb' in info['browser_model']
    assert 'draft_token_hash' not in info and KEY not in response.text
    assert client.get('/characters').json()['characters'] == []
    for headers in (OTHER, auth(), auth(sub='auth0|bob')):
        assert client.get('/jobs/' + created['job_id'], headers=headers).status_code == 404
        assert client.delete('/characters/' + created['character_id'], headers=headers).status_code == 404
    assert client.delete('/characters/' + created['character_id'], headers=GUEST).status_code == 200
    assert conn.execute('SELECT count(*) AS n FROM jobs').fetchone()['n'] == 0


def test_ready_drafts_never_deploy_or_starve_users(client, conn, s3, auth, bridge):
    created = draft(client)
    finish(conn, s3, claim(conn))
    assert conn.execute('SELECT sgl_assign_slot(%s) AS slot', (created['character_id'],)).fetchone()['slot'] is None
    owned = upload(client, auth()).json()
    finish(conn, s3, claim(conn), assign=False)
    conn.execute('SELECT sgl_sync_deploys()')
    rows = conn.execute('SELECT character_id FROM deploys').fetchall()
    assert [str(r['character_id']) for r in rows] == [owned['character_id']]
    assert created['character_id'] not in client.get('/deploys/pending', headers=bridge).text


def test_claim_requires_human_login_matching_key_and_finished_build(client, conn, s3, auth, bridge):
    created = draft(client)
    path = '/characters/' + created['character_id'] + '/claim'
    body = {'draft_token': KEY}
    for headers in ({}, GUEST):
        assert client.post(path, headers=headers, json=body).status_code == 401
    assert client.post(path, headers=bridge, json=body).status_code == 403
    assert client.post(path, headers=auth(scope='read:own'), json=body).status_code == 403
    assert client.post(path, headers=auth(), json={'draft_token': 'cd' * 32}).status_code == 404
    assert client.post(path, headers=auth(), json=body).status_code == 409
    finish(conn, s3, claim(conn))
    response = client.post(path, headers=auth(), json=body)
    assert response.status_code == 200 and response.json()['slot'] == 1
    assert client.post(path, headers=auth(), json=body).json() == response.json()
    assert client.post(path, headers=auth(sub='auth0|bob'), json=body).status_code == 404
    assert client.get('/jobs/' + created['job_id'], headers=GUEST).status_code == 404
    info = client.get('/jobs/' + created['job_id'], headers=auth()).json()
    assert info['requires_login'] is False and info['draft_expires_at'] is None
    row = conn.execute('SELECT * FROM characters').fetchone()
    assert row['owner_sub'] == 'auth0|alice' and row['draft_token_hash'] is None
    assert conn.execute('SELECT count(*) AS n FROM deploys').fetchone()['n'] == 1
    assert len(client.get('/me', headers=auth()).json()['characters']) == 1


def test_concurrent_claim_has_one_owner_and_one_deploy(client, conn, s3, auth):
    created = draft(client)
    finish(conn, s3, claim(conn))
    path = '/characters/' + created['character_id'] + '/claim'
    with ThreadPoolExecutor(max_workers=2) as executor:
        replies = list(executor.map(lambda sub: client.post(path, headers=auth(sub=sub), json={'draft_token': KEY}),
                                    ['auth0|alice', 'auth0|bob']))
    assert sorted(r.status_code for r in replies) == [200, 404]
    assert conn.execute('SELECT count(*) AS n FROM deploys').fetchone()['n'] == 1


def test_draft_and_account_quotas_and_global_admission(make_client, conn, s3, auth):
    client = make_client(limit_user_total=1, limit_global_hour=3)
    created = draft(client)
    assert upload(client, GUEST).status_code == 429  # one active per browser
    finish(conn, s3, claim(conn))
    assert upload(client, GUEST).status_code == 429  # one retained per browser
    owned = upload(client, auth()).json()
    finish(conn, s3, claim(conn))
    path = '/characters/' + created['character_id'] + '/claim'
    assert client.post(path, headers=auth(), json={'draft_token': KEY}).status_code == 429
    assert client.delete('/characters/' + owned['character_id'], headers=auth()).status_code == 200
    assert client.post(path, headers=auth(), json={'draft_token': KEY}).status_code == 200
    assert upload(client, GUEST).status_code == 201
    # Rotating a capability cannot evade the shared hourly limit.
    assert upload(client, OTHER).status_code == 429


def test_expired_drafts_are_inaccessible_and_cleaned(client, conn, s3, auth, pg):
    created = draft(client)
    finish(conn, s3, claim(conn))
    conn.execute("UPDATE characters SET draft_expires_at = now() - interval '1 second'")
    assert client.get('/drafts', headers=GUEST).json()['characters'] == []
    assert client.get('/jobs/' + created['job_id'], headers=GUEST).status_code == 404
    assert client.post('/characters/' + created['character_id'] + '/claim', headers=auth(),
                       json={'draft_token': KEY}).status_code == 404
    db = Database(pg)
    try:
        Cleaner(db, Storage(make_settings(pg), client=s3)).drain()
    finally:
        db.close()
    assert conn.execute('SELECT count(*) AS n FROM characters').fetchone()['n'] == 0
    assert not s3.list_objects_v2(Bucket=BUCKET).get('Contents')


@pytest.mark.parametrize('authorization', ['', 'Guest invalid', 'Bearer invalid'])
def test_bad_authorization_does_not_fall_back_to_guest(client, authorization):
    assert upload(client, {'Authorization': authorization}).status_code == 401
