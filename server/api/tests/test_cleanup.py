import uuid

from sgl_api.cleanup import Cleaner
from sgl_api.db import Database
from sgl_api.storage import Storage
from types import SimpleNamespace
from .conftest import BUCKET
from .helpers import upload, run_job


def cleaner(pg, s3):
    db = Database(pg, max_size=2)
    return db, Cleaner(db, Storage(SimpleNamespace(s3_bucket=BUCKET, presign_ttl=600), client=s3))


def due(conn):
    conn.execute("UPDATE storage_cleanup SET next_at = now() - interval '1 second'")


def test_delete_failure_survives_restart_and_retries(client, auth, conn, pg, s3, monkeypatch):
    created = upload(client, auth()).json()
    original = s3.delete_objects
    monkeypatch.setattr(s3, 'delete_objects', lambda **kw: {'Errors': [{'Code': 'AccessDenied'}]})
    assert client.delete('/characters/' + created['character_id'], headers=auth()).status_code == 200
    rows = conn.execute('SELECT * FROM storage_cleanup').fetchall()
    assert len(rows) == 2 and any(r['failures'] and r['last_error'] for r in rows)
    assert s3.list_objects_v2(Bucket=BUCKET).get('KeyCount', 0) > 0
    monkeypatch.setattr(s3, 'delete_objects', original)
    due(conn)
    db, restarted = cleaner(pg, s3)
    try:
        assert restarted.drain() == 2
        assert s3.list_objects_v2(Bucket=BUCKET).get('KeyCount', 0) == 0
        assert conn.execute('SELECT count(*) AS n FROM storage_cleanup WHERE cleaned_at IS NOT NULL').fetchone()['n'] == 2
        # A late writer from a previous release is caught by the retained tombstone.
        s3.put_object(Bucket=BUCKET, Key=f"builds/{created['job_id']}/late", Body=b'x')
        due(conn)
        assert restarted.drain() == 2
        assert s3.list_objects_v2(Bucket=BUCKET).get('KeyCount', 0) == 0
    finally:
        db.close()


def test_orphan_upload_and_live_job_exclusion(client, auth, conn, pg, s3):
    live = upload(client, auth()).json()
    orphan = uuid.uuid4()
    conn.execute('SELECT sgl_enqueue_cleanup(%s)', (orphan,))
    s3.put_object(Bucket=BUCKET, Key=f'photos/{orphan}/0.jpg', Body=b'x')
    db, worker = cleaner(pg, s3)
    try:
        assert worker.drain() == 2
        assert s3.head_object(Bucket=BUCKET, Key=f"photos/{live['job_id']}/0.jpg")
        run_job(conn, s3)
        due(conn)
        worker.drain()
        assert s3.list_objects_v2(Bucket=BUCKET, Prefix=f"photos/{live['job_id']}/")['KeyCount'] == 0
        assert s3.list_objects_v2(Bucket=BUCKET, Prefix=f"builds/{live['job_id']}/")['KeyCount'] > 0
    finally:
        db.close()


def test_cleanup_waits_for_upload_lock_and_survives_cascade(client, auth, conn, pg, s3):
    import psycopg
    created = upload(client, auth()).json()
    # Models process death after DB deletion, before the request reaches object storage.
    conn.execute('DELETE FROM characters WHERE id = %s', (created['character_id'],))
    db, worker = cleaner(pg, s3)
    try:
        with psycopg.connect(pg) as writer:
            writer.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))',
                           (f"sgl_storage:{created['job_id']}",))
            assert worker.drain() == 0
            assert s3.list_objects_v2(Bucket=BUCKET)['KeyCount'] > 0
        due(conn)
        assert worker.drain() == 2
        assert s3.list_objects_v2(Bucket=BUCKET)['KeyCount'] == 0
    finally:
        db.close()


def test_upload_that_writes_then_loses_response_has_durable_cleanup(client, auth, conn, s3, monkeypatch):
    original = s3.put_object
    delete = s3.delete_objects
    def uncertain_put(**kwargs):
        original(**kwargs)
        raise OSError('response lost after storing object')
    monkeypatch.setattr(s3, 'put_object', uncertain_put)
    monkeypatch.setattr(s3, 'delete_objects', lambda **kw: {'Errors': [{'Code': 'SlowDown'}]})
    import pytest
    with pytest.raises(OSError):
        upload(client, auth())
    assert conn.execute('SELECT count(*) AS n FROM jobs').fetchone()['n'] == 0
    assert conn.execute('SELECT count(*) AS n FROM storage_cleanup').fetchone()['n'] == 2
    assert s3.list_objects_v2(Bucket=BUCKET)['KeyCount'] == 1
    monkeypatch.setattr(s3, 'delete_objects', delete)
    due(conn)
    client.app.state.cleaner.drain()
    assert s3.list_objects_v2(Bucket=BUCKET)['KeyCount'] == 0
