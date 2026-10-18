#!/usr/bin/env python3
"""Read-only HTTPS/API/Auth0 discovery checks. No credentials or sign-in performed."""
import argparse
import json
from pathlib import Path
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]


def get(url, method='GET', headers=None):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method=method, headers={'User-Agent': 'sgl-operations-check/1.0', **(headers or {})}), timeout=15) as r:
            return r.status, r.headers, r.read(1_000_000)
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read(1_000_000)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--origin', default='https://gator-field-board-mlh.app.space')
    args = parser.parse_args()
    config = json.loads((ROOT / 'companion/app/src/lib/gator-config.json').read_text())
    result = {}
    failures = []
    def check(name, action):
        try:
            value = action()
            result[name] = value
            if value is False:
                failures.append(name)
        except Exception as e:
            result[name] = {'error': type(e).__name__}
            failures.append(name)
    def discovery():
        status, _, raw = get(f"https://{config['domain']}/.well-known/openid-configuration")
        data = json.loads(raw)
        assert status == 200 and data['issuer'] == f"https://{config['domain']}/"
        assert 'S256' in data.get('code_challenge_methods_supported', [])
        status, _, keys = get(data['jwks_uri'])
        assert status == 200 and any(k.get('kty') == 'RSA' for k in json.loads(keys)['keys'])
        return {'issuer_matches': True, 'pkce_s256': True, 'rsa_jwks': True,
                'device_grant_advertised': 'urn:ietf:params:oauth:grant-type:device_code' in data.get('grant_types_supported', [])}
    check('auth0_discovery', discovery)
    check('api_health', lambda: get(config['apiBase'] + '/healthz')[0] == 200)
    check('anonymous_me_denied', lambda: get(config['apiBase'] + '/me')[0] == 401)
    check('invalid_bearer_denied', lambda: get(config['apiBase'] + '/me', headers={'Authorization': 'Bearer invalid-probe'})[0] == 401)
    def presence():
        status, _, raw = get(config['apiBase'] + '/status')
        data = json.loads(raw)
        assert status == 200
        return {'reachable': True, 'online': data.get('online'), 'player_count': len(data.get('players', []))}
    check('server_status', presence)
    for route in ('/gatorize', '/home'):
        check('companion' + route, lambda route=route: get(args.origin.rstrip('/') + route)[0] == 200)
    def cors():
        status, headers, _ = get(config['apiBase'] + '/characters', 'OPTIONS', {
            'Origin': args.origin, 'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'authorization,content-type'})
        return status == 200 and headers.get('Access-Control-Allow-Origin') == args.origin
    check('browser_api_cors', cors)
    result['limitations'] = 'Discovery does not prove client grant enablement, callback allowlists, user login, or an authenticated workflow.'
    print(json.dumps(result, indent=2))
    return bool(failures)


if __name__ == '__main__':
    raise SystemExit(main())
