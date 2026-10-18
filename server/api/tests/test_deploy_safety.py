from .helpers import upload, run_job


def ready(client, auth, conn, s3, bridge):
    created = upload(client, auth()).json()
    run_job(conn, s3)
    deploy = client.get('/deploys/pending', headers=bridge).json()['deploys'][0]
    return created, deploy


def test_deleted_staged_character_cannot_be_checked_or_acknowledged(client, auth, conn, s3, bridge):
    created, deploy = ready(client, auth, conn, s3, bridge)
    assert client.post('/deploys/check', headers=bridge, json={'ids': [deploy['id']]}).json()['current'] == [deploy['id']]
    client.delete('/characters/' + created['character_id'], headers=auth())
    assert client.post('/deploys/check', headers=bridge, json={'ids': [deploy['id']]}).json()['current'] == []
    assert client.post(f"/deploys/{deploy['id']}", headers=bridge, json={'state': 'deployed'}).status_code == 409
    assert client.get('/deploys/pending', headers=bridge).json()['deploys'][0]['kind'] == 'placeholder'


def test_superseded_ack_rejected_and_lost_ack_reconciled(client, auth, conn, s3, bridge):
    created, deploy = ready(client, auth, conn, s3, bridge)
    admin = auth(scope='admin:slots')
    newer = client.post('/slots/1/redeploy', headers=admin).json()
    assert client.post('/deploys/check', headers=bridge, json={'ids': [deploy['id']]}).json()['current'] == []
    assert client.post(f"/deploys/{deploy['id']}", headers=bridge, json={'state': 'deployed'}).status_code == 409
    current = client.get('/deploys/pending', headers=bridge).json()['deploys'][0]
    assert client.post(f"/deploys/{current['id']}", headers=bridge, json={'state': 'deployed'}).status_code == 200
    # API committed, bridge lost response and restored a placeholder. Queue a fresh generation.
    assert client.post('/deploys/reconcile', headers=bridge, json={'installed': {'1': None}}).status_code == 200
    again = client.get('/deploys/pending', headers=bridge).json()['deploys'][0]
    assert again['id'] > current['id']
    assert client.post(f"/deploys/{current['id']}", headers=bridge, json={'state': 'deployed'}).status_code == 409
    assert client.post('/deploys/reconcile', headers=auth(), json={'installed': {}}).status_code == 403
