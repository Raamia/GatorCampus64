"""All configuration comes from the environment (see server/api/.env.example)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name)
    return v if v not in (None, "") else default


def _int(name: str, default: int) -> int:
    return int(_env(name, str(default)))


DEFAULT_DOMAIN = "gatorcamp.us"


@dataclass(frozen=True)
class Settings:
    database_url: str
    auth0_issuer: str               # e.g. https://login.gatorcamp.us/ (trailing slash, as in tokens)
    auth0_audience: str
    auth0_jwks_url: str
    s3_endpoint: str | None         # Vultr Object Storage, e.g. https://ewr1.vultrobjects.com
    s3_region: str
    s3_bucket: str
    s3_access_key: str | None
    s3_secret_key: str | None
    presign_ttl: int = 900
    cors_origins: list[str] = field(default_factory=list)
    apply_schema: bool = False
    max_photo_bytes: int = 8 * 1024 * 1024
    photo_max_side: int = 1024
    limit_user_active: int = 1
    limit_user_total: int = 3
    limit_global_hour: int = 20
    link_code_ttl: int = 600
    status_stale_secs: int = 0      # > 0: report the server offline when no event arrived for this long
    claim_namespace: str = f"https://{DEFAULT_DOMAIN}/"   # Auth0 Action custom claims: <ns>uf, <ns>nickname
    play_address: str = f"play.{DEFAULT_DOMAIN}:7777"     # shown by /status


def load() -> Settings:
    """Every URL defaults from SGL_DOMAIN (default gatorcamp.us); each can be overridden on its own."""
    domain = _env("SGL_DOMAIN", DEFAULT_DOMAIN)
    issuer = _env("AUTH0_ISSUER", f"https://login.{domain}/")
    if not issuer.endswith("/"):
        issuer += "/"
    origins = _env("CORS_ORIGINS", f"https://{domain},https://www.{domain}")
    ns = _env("AUTH0_CLAIM_NAMESPACE", f"https://{domain}/")
    if not ns.endswith("/"):
        ns += "/"
    return Settings(
        database_url=_env("DATABASE_URL", "postgresql://sgl:sgl@127.0.0.1:5432/sgl"),
        auth0_issuer=issuer,
        auth0_audience=_env("AUTH0_AUDIENCE", f"https://api.{domain}"),
        claim_namespace=ns,
        play_address=_env("PLAY_ADDRESS", f"play.{domain}:7777"),
        auth0_jwks_url=_env("AUTH0_JWKS_URL", issuer + ".well-known/jwks.json"),
        s3_endpoint=_env("S3_ENDPOINT"),
        s3_region=_env("S3_REGION", "us-east-1"),
        s3_bucket=_env("S3_BUCKET", "sgl64"),
        s3_access_key=_env("S3_ACCESS_KEY"),
        s3_secret_key=_env("S3_SECRET_KEY"),
        presign_ttl=_int("PRESIGN_TTL", 900),
        cors_origins=[o.strip() for o in origins.split(",") if o.strip()],
        apply_schema=_env("SGL_APPLY_SCHEMA", "0").lower() in ("1", "true", "yes"),
        max_photo_bytes=_int("MAX_PHOTO_BYTES", 8 * 1024 * 1024),
        photo_max_side=_int("PHOTO_MAX_SIDE", 1024),
        limit_user_active=_int("LIMIT_USER_ACTIVE", 1),
        limit_user_total=_int("LIMIT_USER_TOTAL", 3),
        limit_global_hour=_int("LIMIT_GLOBAL_HOUR", 20),
        link_code_ttl=_int("LINK_CODE_TTL", 600),
        status_stale_secs=_int("STATUS_STALE_SECS", 0),
    )
