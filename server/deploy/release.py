#!/usr/bin/env python3
"""Local operator releases. Reads SSH inventory from .env without executing it."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import shlex
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def inventory(host):
    values = {}
    for line in (ROOT / '.env').read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        parts = shlex.split(value, comments=True)
        values[key.strip()] = parts[0] if parts else ''
    prefix = 'SGL_HOST' if host == 'host' else 'SGL_GPU'
    address = values[prefix + '_ADDRESS']
    user = values.get(prefix + '_SSH_USER', 'root')
    if address.startswith('-') or user.startswith('-'):
        raise ValueError('Invalid SSH destination')
    opts = ['-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10']
    key = values.get(prefix + '_SSH_KEY_PATH')
    if key:
        key_path = Path(key).expanduser()
        if key_path.suffix == '.pub' and key_path.with_suffix('').is_file():
            key_path = key_path.with_suffix('')
        opts += ['-i', str(key_path)]
    jump = values.get('SGL_SSH_JUMP_HOST')
    if jump:
        opts += ['-J', jump]
    return opts, values.get(prefix + '_SSH_PORT', '22'), user + '@' + address


def ssh(host, script, *args):
    opts, port, dest = inventory(host)
    return run(['ssh', *opts, '-p', port, dest,
                shlex.join(['python3', '-', *args])], input=script, text=True)


def mappings(name, host):
    p = PurePosixPath(name)
    if any(x in {'.env', '.venv', '__pycache__', 'node_modules', '.git'} for x in p.parts):
        return []
    if host == 'gpu':
        # Source only. Host toolchains, vendor checkouts and local configuration survive.
        return ['/opt/sgl64/' + name]
    result = []
    if name.startswith(('server/bridge/', 'server/worker/', 'tools/npc_bridge/', 'mods/sgl64/')):
        result.append('/opt/sgl/' + name)
    if name.startswith('server/api/'):
        result.append('/opt/sgl-api/' + name.removeprefix('server/api/'))
    if name.startswith('mods/sgl64/'):
        relative = name.removeprefix('mods/sgl64/')
        if not (relative == 'guests.lua' or relative.startswith(('actors/guest_', 'textures/sgl_portrait_guest_'))):
            result.append('/srv/sgl/mods/sgl64/' + relative)
    return result


def artifact(ref, host):
    commit = subprocess.check_output(['git', 'rev-parse', '--verify', ref + '^{commit}'], cwd=ROOT, text=True).strip()
    raw = subprocess.check_output(['git', 'archive', '--format=tar', commit], cwd=ROOT)
    data, records = io.BytesIO(), []
    with tarfile.open(fileobj=io.BytesIO(raw)) as source, tarfile.open(fileobj=data, mode='w') as out:
        for member in source:
            if not member.isfile():
                continue  # Never materialize repository symlinks on a production host.
            content = source.extractfile(member).read()
            for target in mappings(member.name, host):
                entry = tarfile.TarInfo(target.lstrip('/'))
                entry.size, entry.mode = len(content), member.mode
                out.addfile(entry, io.BytesIO(content))
                records.append({'path': target, 'sha256': hashlib.sha256(content).hexdigest(), 'mode': member.mode})
    return commit, data.getvalue(), records


def validate_npc_data(commit):
    """Check the candidate's derived navigation, never the operator's working copy."""
    paths = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', commit], cwd=ROOT, text=True).splitlines()
    entry = 'tools/npcs/rebuild.py'
    if entry not in paths:
        return  # Legacy releases predate generated placement data; rollback is separate.
    selected = [p for p in paths if p.startswith('tools/npcs/')
                or (p.startswith('data/uf/') and p.endswith('.json'))
                or p in {'tools/luatest/check_npc_spots.py', 'tools/luatest/check_minimap_textures.py',
                         'tools/luatest/check_hub_materials.py', 'tools/blender/fix_material_lighting.py'}
                or p == 'mods/sgl64/levels/castle_grounds/model.inc.c'
                or p.startswith('mods/sgl64/textures/sgl_minimap_')
                or (p.startswith('mods/sgl64/') and (p.endswith('.lua') or
                    p.endswith('/script.c') or p.endswith('/collision.inc.c') or p.endswith('/model.inc.c')))]
    raw = subprocess.check_output(['git', 'archive', commit, '--', *selected], cwd=ROOT)
    with tempfile.TemporaryDirectory(prefix='sgl-navigation-check-') as folder:
        with tarfile.open(fileobj=io.BytesIO(raw)) as source:
            for member in source:
                if not member.isfile():
                    continue
                relative = PurePosixPath(member.name)
                if relative.is_absolute() or '..' in relative.parts:
                    raise ValueError('Invalid candidate path')
                dest = Path(folder) / member.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(source.extractfile(member).read())
        run(['python3', '-I', str(Path(folder) / entry), '--check'])
        texture_check = Path(folder) / 'tools/luatest/check_minimap_textures.py'
        if texture_check.exists():
            run(['python3', '-I', str(texture_check)])
        material_check = Path(folder) / 'tools/luatest/check_hub_materials.py'
        if material_check.exists():
            run(['python3', '-I', str(material_check)])
        lighting = Path(folder) / 'tools/blender/fix_material_lighting.py'
        if lighting.exists():
            levels = sorted((Path(folder) / 'mods/sgl64/levels').glob('*/model.inc.c'))
            run(['python3', '-I', str(lighting), '--check', *[str(p.parent) for p in levels]])


REMOTE = r'''
import hashlib, json, os, pathlib, shutil, subprocess, sys, tarfile, time, urllib.request
state = pathlib.Path('/var/lib/sgl-releases')
action, host = sys.argv[1:3]
current = state / 'current.json'
def command(args):
    subprocess.run(args, check=True)
def digest(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def load():
    return json.loads(current.read_text()) if current.exists() else None
def healthy():
    if host == 'host':
        command(['systemctl', 'is-active', 'sgl-api', 'sgl-bridge'])
        with urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=10) as response:
            assert response.status == 200
        sockets = subprocess.check_output(['ss', '-H', '-lun'], text=True)
        assert any(':7777' in line for line in sockets.splitlines()), 'Game UDP 7777 missing'
    else:
        result = subprocess.check_output(['docker', 'compose', '-p', 'worker', '-f', '/opt/sgl64/server/worker/docker-compose.yml', 'ps', '--status', 'running', '--services'], text=True)
        assert 'worker' in result.splitlines(), 'Worker container not running'
        print('Worker running; inference and job success need separate checks.')
def activate():
    if host == 'host':
        command(['/opt/sgl-api/.venv/bin/python', '-m', 'pip', 'check'])
        command(['/opt/sgl/server/bridge/.venv/bin/python', '-m', 'pip', 'check'])
        command(['systemctl', 'restart', 'sgl-api', 'sgl-bridge'])
    else:
        command(['docker', 'compose', '-p', 'worker', '-f', '/opt/sgl64/server/worker/docker-compose.yml', 'up', '-d', '--build', '--no-deps', 'worker'])
if action in ('status', 'verify'):
    value = load()
    summary = {k: value[k] for k in ('commit', 'release', 'deployed_at', 'host')} if value else None
    if summary is not None: summary['managed_files'] = len(value['files'])
    print(json.dumps(summary, indent=2) if summary else 'No managed release manifest; existing deployment is unmanaged.')
    if value:
        drift = [f['path'] for f in value['files'] if not pathlib.Path(f['path']).is_file() or digest(f['path']) != f['sha256']]
        if drift:
            raise SystemExit('Source drift: ' + ', '.join(drift))
        print('Managed source hashes match.')
    if action == 'verify': healthy()
    sys.exit(0)
if action == 'rollback':
    value = load()
    if not value: raise SystemExit('No managed release to roll back')
    backup = state / value['release']
    metadata = json.loads((backup / 'backup.json').read_text())
    # Refuse to overwrite changes made after the release.
    for f in value['files']:
        if not pathlib.Path(f['path']).is_file() or digest(f['path']) != f['sha256']:
            raise SystemExit('Source drift; inspect before rollback: ' + f['path'])
    for f in metadata['files']:
        target = pathlib.Path(f['path'])
        if f['existed']: shutil.copy2(backup / 'files' / f['path'].lstrip('/'), target)
        else: target.unlink(missing_ok=True)
    if metadata['previous']: current.write_text(json.dumps(metadata['previous'], indent=2) + '\n')
    else: current.unlink(missing_ok=True)
    activate()
    healthy()
    print('Rolled back source. Database, configuration, game saves and generated assets unchanged.')
    sys.exit(0)
archive, manifest_path, adopt = sys.argv[3:6]
manifest = json.loads(pathlib.Path(manifest_path).read_text())
previous = load()
if not previous and adopt != 'yes': raise SystemExit('First release requires --adopt-current after reviewing the unmanaged deployment')
if previous:
    incoming = {f['path'] for f in manifest['files']}
    removed = [f['path'] for f in previous['files'] if f['path'] not in incoming]
    if removed:
        raise SystemExit('Release removes managed files; archive/reconcile them explicitly first: ' + ', '.join(removed))
    for f in previous['files']:
        if not pathlib.Path(f['path']).is_file() or digest(f['path']) != f['sha256']:
            raise SystemExit('Source drift; inspect before deployment: ' + f['path'])
# A source rollback cannot undo a Python environment update. Require explicit operator preparation.
if host == 'host':
    for f in manifest['files']:
        p = pathlib.Path(f['path'])
        if p.name == 'requirements.txt' and p.exists() and digest(p) != f['sha256']:
            raise SystemExit('Requirements changed: prepare and snapshot dependencies separately before deploying ' + str(p))
for f in manifest['files']:
    p = pathlib.Path(f['path'])
    if p.is_symlink() or any(parent.is_symlink() for parent in p.parents):
        raise SystemExit('Refusing symlink destination: ' + str(p))
state.mkdir(parents=True, exist_ok=True)
release = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-' + manifest['commit'][:12]
backup = state / release
backup.mkdir()  # A repeated release in the same second must fail rather than replace its backup.
metadata = {'previous': previous, 'files': []}
for f in manifest['files']:
    p = pathlib.Path(f['path'])
    exists = p.exists()
    metadata['files'].append({'path': str(p), 'existed': exists})
    if exists:
        saved = backup / 'files' / str(p).lstrip('/')
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, saved)
(backup / 'backup.json').write_text(json.dumps(metadata, indent=2))
# Stage extraction is deliberately not tar.extractall(). Only manifest-listed regular files are copied.
with tarfile.open(archive) as bundle:
    for f in manifest['files']:
        p = pathlib.Path(f['path'])
        member = bundle.getmember(f['path'].lstrip('/'))
        assert member.isfile()
        content = bundle.extractfile(member).read()
        assert hashlib.sha256(content).hexdigest() == f['sha256']
        p.parent.mkdir(parents=True, exist_ok=True)
        # Existing ownership is retained by overwriting in place; new source is world-readable.
        p.write_bytes(content)
        p.chmod(f['mode'])
manifest.update(release=release, deployed_at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), host=host)
current.write_text(json.dumps(manifest, indent=2) + '\n')
print('Source installed; recovery manifest: ' + str(backup / 'backup.json'), flush=True)
activate()
# systemd can be active before uvicorn has bound its port.
for attempt in range(15):
    try:
        healthy()
        break
    except Exception:
        if attempt == 14: raise
        time.sleep(2)
print('Verified release ' + release)
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan', 'deploy', 'status', 'verify', 'rollback'])
    parser.add_argument('host', choices=['host', 'gpu'])
    parser.add_argument('--ref', default='HEAD', help='Committed Git ref; default HEAD')
    parser.add_argument('--adopt-current', action='store_true', help='Allow first managed release; snapshot existing source')
    parser.add_argument('--allow-restart', action='store_true', help='Confirm restart/job interruption window')
    args = parser.parse_args()
    if args.action in {'status', 'verify'}:
        ssh(args.host, REMOTE, args.action, args.host)
        return
    if args.action == 'rollback':
        if not args.allow_restart:
            parser.error('rollback requires --allow-restart')
        ssh(args.host, REMOTE, 'rollback', args.host)
        return
    commit, payload, records = artifact(args.ref, args.host)
    print(json.dumps({'commit': commit, 'host': args.host, 'files': len(records), 'archive_bytes': len(payload)}, indent=2), flush=True)
    if args.action == 'plan':
        for record in records:
            print(record['path'])
        return
    if not args.allow_restart:
        parser.error('deploy requires --allow-restart after reviewing plan and connected players/jobs')
    dirty = subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True)
    if dirty:
        parser.error('Working tree is dirty; commit/review changes before deployment')
    if args.host == 'host':
        validate_npc_data(commit)
    with tempfile.TemporaryDirectory(prefix='sgl-release-') as folder:
        package = Path(folder) / 'source.tar'
        manifest = Path(folder) / 'manifest.json'
        package.write_bytes(payload)
        manifest.write_text(json.dumps({'commit': commit, 'files': records}))
        # Create a private remote staging directory, without sourcing local or remote secrets.
        opts, port, dest = inventory(args.host)
        staging = subprocess.check_output(['ssh', *opts, '-p', port, dest, 'mktemp -d /tmp/sgl-release.XXXXXXXX'], text=True).strip()
        if not staging.startswith('/tmp/sgl-release.') or any(c not in '/.-_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789' for c in staging):
            raise ValueError('Unexpected remote staging path')
        try:
            run(['scp', *opts, '-P', port, str(package), str(manifest), dest + ':' + staging + '/'])
            ssh(args.host, REMOTE, 'deploy', args.host, staging + '/source.tar', staging + '/manifest.json', 'yes' if args.adopt_current else 'no')
        finally:
            ssh(args.host, 'import shutil,sys; shutil.rmtree(sys.argv[1])', staging)


if __name__ == '__main__':
    main()
