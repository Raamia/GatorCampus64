#!/usr/bin/env python3
"""Read-only remote configuration checks; emit comparisons and presence flags, never secret values."""
import inspect
import json
from pathlib import Path
import release

def login_checks(expected, configured, running):
    """Check what systemd actually passed to the bridge, without printing values."""
    import re
    client = running.get('AUTH0_CLIENT_ID', '')
    return {
        'bridge_running_client_matches_file': bool(client) and client == configured.get('AUTH0_CLIENT_ID'),
        'bridge_running_client_is_single_id': bool(re.fullmatch(r'[A-Za-z0-9_-]+', client)),
        'bridge_running_domain_matches_browser': running.get('AUTH0_DOMAIN') == expected['domain'],
        'bridge_running_audience_matches_browser': running.get('AUTH0_AUDIENCE') == expected['audience'],
    }


REMOTE = inspect.getsource(login_checks) + r'''
import json, pathlib, shlex, subprocess, sys
expected = json.loads(sys.argv[1])
def env(path):
    result = {}
    for line in pathlib.Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        k, v = line.split('=', 1)
        values = shlex.split(v, comments=True)
        result[k.strip()] = values[0] if values else ''
    return result
api, bridge = env('/etc/sgl/api.env'), env('/etc/sgl/bridge.env')
checks = {
    'api_issuer_matches_browser': api.get('AUTH0_ISSUER') == 'https://' + expected['domain'] + '/',
    'api_audience_matches_browser': api.get('AUTH0_AUDIENCE') == expected['audience'],
    'bridge_domain_matches_browser': bridge.get('AUTH0_DOMAIN') == expected['domain'],
    'bridge_audience_matches_browser': bridge.get('AUTH0_AUDIENCE') == expected['audience'],
    'bridge_device_client_configured': bool(bridge.get('AUTH0_CLIENT_ID')),
    'bridge_m2m_configured': bool(bridge.get('AUTH0_M2M_CLIENT_ID') and bridge.get('AUTH0_M2M_CLIENT_SECRET')),
    'api_database_configured': bool(api.get('DATABASE_URL')),
    'api_storage_credentials_configured': bool(api.get('S3_ACCESS_KEY') and api.get('S3_SECRET_KEY')),
    'api_deepspace_delivery_configured': bool(api.get('DEEPSPACE_APP_URL') and api.get('DEEPSPACE_INGEST_SECRET')),
    'startup_schema_disabled': api.get('SGL_APPLY_SCHEMA', '0') == '0',
}
# EnvironmentFile syntax differs from shell tokenization. A malformed line can
# look correct after shlex.split(...)[0] yet pass extra assignments as ID text.
pid = subprocess.check_output(['systemctl', 'show', '-p', 'MainPID', '--value', 'sgl-bridge'], text=True).strip()
running = {}
if pid.isdigit() and pid != '0':
    running = dict(part.decode().split('=', 1) for part in pathlib.Path('/proc', pid, 'environ').read_bytes().split(b'\0') if b'=' in part)
checks.update(login_checks(expected, bridge, running))
print(json.dumps(checks, indent=2))
sys.exit(0 if all(checks.values()) else 1)
'''

if __name__ == '__main__':
    config = json.loads((Path(__file__).resolve().parents[2] / 'companion/app/src/lib/gator-config.json').read_text())
    release.ssh('host', REMOTE, json.dumps(config))
