"""Auth0 pieces of the bridge (spec §7): device flow for in-game /login, ID token checks, M2M token."""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

import jwt

from .httpclient import TransportError

log = logging.getLogger("sglbridge.auth")

DEVICE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"


@dataclass
class Auth0Config:
    domain: str                    # e.g. login.gatorcamp.us (custom domain) or <tenant>.us.auth0.com
    client_id: str                 # "Gator Pass" native app (device code grant on, no secret)
    audience: str                  # https://api.gatorcamp.us
    issuer: str | None = None      # default https://<domain>/ (Auth0 uses the domain the flow ran on)
    scope: str = "openid profile email"

    @property
    def base(self) -> str:
        return f"https://{self.domain}"

    @property
    def issuer_url(self) -> str:
        return self.issuer or f"https://{self.domain}/"


@dataclass
class DeviceCode:
    device_code: str
    user_code: str
    verification_uri: str
    verification_uri_complete: str
    expires_in: int
    interval: int


class LoginFailed(Exception):
    """The login ended without tokens. reason: expired | denied | invalid_token | error | unavailable."""

    def __init__(self, reason: str, detail: str = ""):
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.detail = detail


class Cancelled(Exception):
    """The player left (or asked again) while the flow was running."""


class DeviceFlowClient:
    """RFC 8628 against Auth0: /oauth/device/code then poll /oauth/token."""

    MAX_TRANSPORT_ERRORS = 10

    def __init__(self, cfg: Auth0Config, http: Any, clock: Callable[[], float] = time.monotonic):
        self.cfg = cfg
        self.http = http
        self.clock = clock

    def request_code(self) -> DeviceCode:
        try:
            resp = self.http.request("POST", f"{self.cfg.base}/oauth/device/code", form={
                "client_id": self.cfg.client_id, "scope": self.cfg.scope, "audience": self.cfg.audience})
        except TransportError as e:
            raise LoginFailed("unavailable", str(e)) from e
        body = resp.json() or {}
        if not resp.ok or "device_code" not in body:
            raise LoginFailed("error", f"device/code {resp.status}: {body.get('error_description') or body.get('error')}")
        uri = body.get("verification_uri") or ""
        return DeviceCode(
            device_code=body["device_code"], user_code=body.get("user_code", ""), verification_uri=uri,
            verification_uri_complete=body.get("verification_uri_complete") or uri,
            expires_in=int(body.get("expires_in", 900)), interval=int(body.get("interval", 5)))

    def poll(self, dc: DeviceCode, wait: Callable[[float], bool]) -> dict[str, Any]:
        """Poll until tokens arrive. wait(seconds) sleeps and returns True when the login was cancelled."""
        interval = max(1, dc.interval)
        deadline = self.clock() + dc.expires_in
        transport_errors = 0
        while True:
            if wait(interval):
                raise Cancelled()
            if self.clock() >= deadline:
                raise LoginFailed("expired")
            try:
                resp = self.http.request("POST", f"{self.cfg.base}/oauth/token", form={
                    "grant_type": DEVICE_GRANT, "device_code": dc.device_code, "client_id": self.cfg.client_id})
            except TransportError as e:
                transport_errors += 1
                log.warning("device flow: token poll failed (%d): %s", transport_errors, e)
                if transport_errors >= self.MAX_TRANSPORT_ERRORS:
                    raise LoginFailed("unavailable", str(e)) from e
                continue
            transport_errors = 0
            body = resp.json() or {}
            if resp.ok and body.get("access_token"):
                return body
            err = body.get("error")
            if err == "authorization_pending":
                continue
            if err == "slow_down":
                interval += 5
                continue
            if err == "expired_token":
                raise LoginFailed("expired")
            if err == "access_denied":
                raise LoginFailed("denied", body.get("error_description", ""))
            raise LoginFailed("error", f"token {resp.status}: {err} {body.get('error_description', '')}".strip())


class IdTokenValidator:
    """Checks an Auth0 ID token: RS256 signature from the tenant JWKS, iss, aud (= the app's client id), exp."""

    def __init__(self, issuer: str, client_id: str, key_resolver: Callable[[str], Any] | None = None,
                 leeway: float = 60.0):
        self.issuer = issuer
        self.client_id = client_id
        self.leeway = leeway
        if key_resolver is None:
            jwks = jwt.PyJWKClient(issuer.rstrip("/") + "/.well-known/jwks.json", cache_keys=True, lifespan=3600)
            key_resolver = lambda token: jwks.get_signing_key_from_jwt(token).key  # noqa: E731
        self.key_resolver = key_resolver

    def validate(self, id_token: str) -> dict[str, Any]:
        try:
            key = self.key_resolver(id_token)
            return jwt.decode(id_token, key, algorithms=["RS256"], audience=self.client_id, issuer=self.issuer,
                              leeway=self.leeway, options={"require": ["exp", "iat", "iss", "aud", "sub"]})
        except jwt.PyJWTError as e:
            raise LoginFailed("invalid_token", str(e)) from e
        except Exception as e:  # noqa: BLE001 - JWKS fetch problems
            raise LoginFailed("unavailable", f"jwks: {e}") from e


class M2MTokenProvider:
    """Client-credentials access token for the API (scope `bridge`), cached until shortly before expiry."""

    def __init__(self, domain: str, client_id: str, client_secret: str, audience: str, http: Any,
                 clock: Callable[[], float] = time.time, margin: float = 60.0):
        self.url = f"https://{domain}/oauth/token"
        self.client_id = client_id
        self.client_secret = client_secret
        self.audience = audience
        self.http = http
        self.clock = clock
        self.margin = margin
        self._token: str | None = None
        self._expires = 0.0
        self._lock = threading.Lock()

    def get(self) -> str:
        with self._lock:
            if self._token and self.clock() < self._expires - self.margin:
                return self._token
            resp = self.http.request("POST", self.url, json_body={
                "grant_type": "client_credentials", "client_id": self.client_id,
                "client_secret": self.client_secret, "audience": self.audience})
            body = resp.json() or {}
            if not resp.ok or not body.get("access_token"):
                raise TransportError(f"M2M token {resp.status}: {body.get('error')}")
            self._token = body["access_token"]
            self._expires = self.clock() + float(body.get("expires_in", 3600))
            return self._token

    def invalidate(self) -> None:
        with self._lock:
            self._token = None
            self._expires = 0.0
