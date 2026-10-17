"""Auth0 access-token verification (RS256, cached JWKS, issuer + audience) and scope checks."""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from typing import Callable

import httpx
import jwt
from jwt.algorithms import RSAAlgorithm

DEFAULT_CLAIM_NS = "https://gatorcamp.us/"  # Settings.claim_namespace (AUTH0_CLAIM_NAMESPACE / SGL_DOMAIN)


class AuthError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


@dataclass
class Principal:
    sub: str
    scopes: set[str]
    claims: dict = field(default_factory=dict)
    claim_ns: str = DEFAULT_CLAIM_NS   # namespace of the post-login Action's custom claims

    @property
    def is_m2m(self) -> bool:
        # Auth0 client-credentials tokens have sub "<client_id>@clients"
        return self.sub.endswith("@clients") or self.claims.get("gty") == "client-credentials"

    @property
    def nickname(self) -> str | None:
        for c in (self.claim_ns + "nickname", "nickname", "name"):
            v = self.claims.get(c)
            if isinstance(v, str) and v.strip():
                return v.strip()[:64]
        return None

    @property
    def email_uf(self) -> bool:
        return self.claims.get(self.claim_ns + "uf") is True


def _http_fetch(url: str) -> dict:
    r = httpx.get(url, timeout=5.0)
    r.raise_for_status()
    return r.json()


class JWKSCache:
    """Keys by kid; refreshed after `ttl` seconds, or on an unknown kid (at most every `min_refetch`)."""

    def __init__(self, url: str, fetch: Callable[[str], dict] = _http_fetch,
                 ttl: float = 3600.0, min_refetch: float = 30.0):
        self.url, self.fetch, self.ttl, self.min_refetch = url, fetch, ttl, min_refetch
        self._keys: dict[str, object] = {}
        self._fetched = 0.0
        self._lock = threading.Lock()

    def _refresh(self) -> None:
        data = self.fetch(self.url)
        keys = {}
        for k in data.get("keys", []):
            if k.get("kty") == "RSA" and k.get("kid") and k.get("use", "sig") == "sig":
                keys[k["kid"]] = RSAAlgorithm.from_jwk(json.dumps(k))
        self._keys = keys
        self._fetched = time.monotonic()

    def get(self, kid: str):
        with self._lock:
            age = time.monotonic() - self._fetched
            if not self._keys or age > self.ttl or (kid not in self._keys and age > self.min_refetch):
                try:
                    self._refresh()
                except Exception as e:  # noqa: BLE001 - keep serving cached keys if Auth0 blips
                    if not self._keys:
                        raise AuthError(503, f"cannot fetch JWKS: {e}") from e
            key = self._keys.get(kid)
        if key is None:
            raise AuthError(401, "unknown signing key")
        return key


class Verifier:
    def __init__(self, issuer: str, audience: str, jwks: JWKSCache, leeway: int = 30,
                 claim_ns: str = DEFAULT_CLAIM_NS):
        self.issuer, self.audience, self.jwks, self.leeway = issuer, audience, jwks, leeway
        self.claim_ns = claim_ns

    def verify(self, token: str) -> Principal:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as e:
            raise AuthError(401, "malformed token") from e
        if header.get("alg") != "RS256":
            raise AuthError(401, "token must be RS256")
        key = self.jwks.get(header.get("kid", ""))
        try:
            claims = jwt.decode(token, key=key, algorithms=["RS256"], audience=self.audience,
                                issuer=self.issuer, leeway=self.leeway,
                                options={"require": ["exp", "iat", "sub", "iss", "aud"]})
        except jwt.ExpiredSignatureError as e:
            raise AuthError(401, "token expired") from e
        except jwt.PyJWTError as e:
            raise AuthError(401, f"invalid token: {e}") from e
        scopes = set(str(claims.get("scope", "")).split())
        perms = claims.get("permissions")
        if isinstance(perms, list):  # Auth0 RBAC puts granted permissions here
            scopes.update(p for p in perms if isinstance(p, str))
        return Principal(sub=claims["sub"], scopes=scopes, claims=claims, claim_ns=self.claim_ns)


def bearer(header_value: str | None) -> str:
    if not header_value:
        raise AuthError(401, "missing bearer token")
    scheme, _, token = header_value.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise AuthError(401, "missing bearer token")
    return token.strip()
