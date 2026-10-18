"""Explicit two-provider proof; never match accounts by email or display name."""
import hashlib
import hmac
import re
import time

from .auth import AuthError
from .deepspace import sign


def verify(c, secret, raw, headers, bearer_token, body):
    if not secret:
        raise AuthError(503, 'identity linking is not configured')
    timestamp, nonce = headers.get('x-sgl-timestamp', ''), headers.get('x-sgl-nonce', '')
    if not re.fullmatch(r'\d{1,12}', timestamp) or abs(time.time() - int(timestamp)) > 300:
        raise AuthError(401, 'expired identity proof')
    if not re.fullmatch(r'[0-9a-f]{32}', nonce):
        raise AuthError(401, 'invalid identity proof')
    key = hmac.new(secret.encode(), b'sgl-identity-v1', hashlib.sha256).hexdigest()
    expected = sign(key, raw, timestamp, nonce)['X-SGL-Signature']
    if not hmac.compare_digest(expected, headers.get('x-sgl-signature', '')):
        raise AuthError(401, 'invalid identity proof')
    if not hmac.compare_digest(hashlib.sha256(bearer_token.encode()).hexdigest(), body.token_hash):
        raise AuthError(401, 'identity proof belongs to another login')
    c.execute("DELETE FROM identity_nonces WHERE created < now() - interval '10 minutes'")
    if not c.execute('INSERT INTO identity_nonces (nonce) VALUES (%s) ON CONFLICT DO NOTHING RETURNING nonce',
                     (nonce,)).fetchone():
        raise AuthError(409, 'identity proof already used')
