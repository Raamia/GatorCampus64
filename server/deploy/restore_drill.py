#!/usr/bin/env python3
"""Synthetic pg_dump/pg_restore drill in a disposable, network-isolated PostgreSQL container.

Accepts no production URL, mounts no host data, and never reads credentials or production records.
Requires an already-present postgres:16-alpine image. Output contains counts/hashes, not row data.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
IMAGE = 'postgres:16-alpine'


def command(argv, *, data=None):
    result = subprocess.run(argv, input=data, capture_output=True, timeout=60)
    if result.returncode:
        raise RuntimeError(f'{argv[0]} failed: ' + result.stderr.decode(errors='replace')[-1500:])
    return result.stdout


def main():
    name = 'sgl-restore-drill-' + uuid.uuid4().hex[:12]
    command(['docker', 'image', 'inspect', IMAGE])  # no implicit network pull
    started = False
    try:
        command(['docker', 'run', '-d', '--rm', '--network', 'none', '--name', name,
                 '-e', 'POSTGRES_HOST_AUTH_METHOD=trust', '-e', 'POSTGRES_DB=source', IMAGE])
        started = True
        for _ in range(60):
            ready = subprocess.run(['docker', 'exec', name, 'pg_isready', '-U', 'postgres'], capture_output=True)
            if ready.returncode == 0:
                break
            time.sleep(0.5)
        else:
            raise RuntimeError('Postgres readiness timed out')
        def sql(database, text):
            return command(['docker', 'exec', '-i', name, 'psql', '-X', '-qAt', '-v', 'ON_ERROR_STOP=1',
                            '-U', 'postgres', '-d', database], data=text.encode()).decode().strip()
        schema = (ROOT / 'server/api/schema.sql').read_text()
        sql('source', schema)
        sql('source', '''
INSERT INTO users (sub,nickname) VALUES ('auth0|drill','Synthetic');
INSERT INTO characters (id,owner_sub,name,state) VALUES ('00000000-0000-0000-0000-000000000001','auth0|drill','Drill','ready');
INSERT INTO jobs (id,character_id,state,artifacts) VALUES ('00000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000001','ready','{"build_id":"sglguest"}');
SELECT sgl_assign_slot('00000000-0000-0000-0000-000000000001');
INSERT INTO links (sub,coopdx_name,gi,via,revoked_at) VALUES ('auth0|drill','Synthetic',1,'device',now());
INSERT INTO deleted_accounts (subject_hash,deleted_before) VALUES ('synthetic-hash',1700000000);
INSERT INTO erased_links (link_id) VALUES (99);
INSERT INTO erased_events VALUES ('drill@clients','00000000-0000-0000-0000-000000000003');
INSERT INTO run_erases (uid) VALUES ('00000000-0000-0000-0000-000000000004');
INSERT INTO identity_links (sub,deepspace_user) VALUES ('auth0|drill','synthetic-board-user');
INSERT INTO identity_nonces (nonce) VALUES ('synthetic-nonce');
INSERT INTO account_erases (deepspace_user,before_ms) VALUES ('deleted-synthetic-board-user',1700000000000);
INSERT INTO runs (mission,frames,players,names,subs,ranked,player_key) VALUES ('swamp_sprint',1200,1,ARRAY['Synthetic'],ARRAY['auth0|drill'],true,'auth0|drill');
INSERT INTO run_pushes (run_id) SELECT id FROM runs;
''')
        tables = sql('source', "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").splitlines()
        def snapshot(database):
            return {t: sql(database, f"SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text), '[]'::jsonb) FROM {t} t") for t in tables}
        before = snapshot('source')
        dump = command(['docker', 'exec', name, 'pg_dump', '-U', 'postgres', '-d', 'source', '-Fc', '--no-owner', '--no-acl'])
        sql('postgres', 'CREATE DATABASE restored')
        command(['docker', 'exec', '-i', name, 'pg_restore', '-U', 'postgres', '-d', 'restored', '--no-owner', '--no-acl', '--exit-on-error'], data=dump)
        if before != snapshot('restored'):
            raise RuntimeError('Restored table contents differ from the dump source')
        # Replay additive migration; restored functions, triggers and sequence state must work.
        sql('restored', schema)
        next_link = int(sql('restored', "INSERT INTO links (sub,coopdx_name,gi,via) VALUES ('auth0|drill','Synthetic2',2,'device') RETURNING id"))
        if next_link != 2:
            raise RuntimeError('Sequence state was not restored')
        sql('restored', "SELECT sgl_release_slot('00000000-0000-0000-0000-000000000001'); DELETE FROM users WHERE sub='auth0|drill';")
        assert sql('restored', 'SELECT count(*) FROM jobs') == '0'
        assert sql('restored', 'SELECT count(*) FROM identity_links') == '0'
        assert sql('restored', 'SELECT count(*) FROM storage_cleanup') == '2'
        assert sql('restored', "SELECT count(*) FROM deploys WHERE kind='placeholder'") == '1'
        assert sql('restored', 'SELECT count(*) FROM run_erases') == '1'
        assert sql('restored', 'SELECT count(*) FROM deleted_accounts') == '1'
        print(json.dumps({'restored': True, 'tables_compared': len(tables), 'dump_bytes': len(dump),
                          'dump_sha256': hashlib.sha256(dump).hexdigest(),
                          'schema_reapplication': True, 'sequences': True, 'cascade_cleanup_and_placeholder': True,
                          'deletion_tombstones_preserved': True,
                          'scope': 'synthetic PostgreSQL only; object storage, provider stores and production backup not tested'}, indent=2))
    finally:
        if started:
            command(['docker', 'rm', '-fv', name])


if __name__ == '__main__':
    main()
