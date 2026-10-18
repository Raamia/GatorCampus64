"""Test fixtures: a real Postgres (SKIP LOCKED and the plpgsql slot functions need it), a local RSA
key standing in for Auth0's JWKS, and moto for Object Storage.

Postgres comes from $SGL_TEST_DATABASE_URL if set, else a throwaway `postgres:16-alpine` container
started with docker. With neither, every DB test is skipped with a message saying so.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import time
import uuid

import boto3
import jwt
import psycopg
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jwt.algorithms import RSAAlgorithm
from moto import mock_aws
from PIL import Image

from sgl_api import config
from sgl_api.app import create_app
from sgl_api.auth import JWKSCache, Verifier
from sgl_api.db import Database, apply_schema
from sgl_api.storage import Storage

ISSUER = "https://login.test.example/"
AUDIENCE = "https://api.gatorcamp.us"
BUCKET = "sgl-test"
TABLES = "server_presence, generation_admissions, run_pushes, runs, deploys, events, link_codes, links, slots, jobs, characters, users"


# ── Postgres ──────────────────────────────────────────────────────────────────────────────────

def _wait(url: str, secs: float = 30) -> None:
    deadline = time.time() + secs
    while True:
        try:
            with psycopg.connect(url, connect_timeout=2) as c:
                c.execute("SELECT 1")
            return
        except psycopg.OperationalError:
            if time.time() > deadline:
                raise
            time.sleep(0.5)


@pytest.fixture(scope="session")
def pg_url():
    url = os.environ.get("SGL_TEST_DATABASE_URL")
    if url:
        _wait(url)
        yield url
        return
    if not shutil.which("docker"):
        pytest.skip("no Postgres for DB tests: set SGL_TEST_DATABASE_URL or install docker "
                    "(SQLite can't stand in: the schema needs SKIP LOCKED and plpgsql)")
    name = f"sgl-api-test-{uuid.uuid4().hex[:8]}"
    try:
        subprocess.run(["docker", "run", "-d", "--rm", "--name", name, "-e", "POSTGRES_PASSWORD=sgl",
                        "-e", "POSTGRES_USER=sgl", "-e", "POSTGRES_DB=sgl", "-p", "127.0.0.1::5432",
                        "postgres:16-alpine"], check=True, capture_output=True, timeout=120)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        pytest.skip(f"could not start a Postgres container: {getattr(e, 'stderr', e)!r}")
    try:
        port = subprocess.run(["docker", "port", name, "5432/tcp"], check=True, capture_output=True,
                              text=True).stdout.strip().splitlines()[0].rsplit(":", 1)[1]
        url = f"postgresql://sgl:sgl@127.0.0.1:{port}/sgl"
        _wait(url, 60)
        yield url
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)


@pytest.fixture(scope="session")
def schema(pg_url):
    apply_schema(pg_url)
    apply_schema(pg_url)  # idempotent
    return pg_url


@pytest.fixture
def pg(schema):
    with psycopg.connect(schema, autocommit=True) as c:
        c.execute(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE")
        c.execute("INSERT INTO slots (n) SELECT generate_series(1, 8)")
    return schema


@pytest.fixture
def conn(pg):
    from psycopg.rows import dict_row
    with psycopg.connect(pg, autocommit=True, row_factory=dict_row) as c:
        yield c


# ── Auth0 stand-in ────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="session")
def jwks(rsa_key):
    jwk = json.loads(RSAAlgorithm.to_jwk(rsa_key.public_key()))
    jwk.update(kid="test-kid", use="sig", alg="RS256")
    return {"keys": [jwk]}


@pytest.fixture
def token(rsa_key):
    def make(sub="auth0|alice", scope="create:character read:own", aud=AUDIENCE, iss=ISSUER,
             exp_in=3600, kid="test-kid", key=None, alg="RS256", **claims):
        now = int(time.time())
        payload = {"sub": sub, "aud": aud, "iss": iss, "iat": now, "exp": now + exp_in, "scope": scope, **claims}
        k = key if key is not None else rsa_key
        return jwt.encode(payload, k, algorithm=alg, headers={"kid": kid})
    return make


@pytest.fixture
def auth(token):
    def h(**kw):
        return {"Authorization": f"Bearer {token(**kw)}"}
    return h


@pytest.fixture
def bridge(auth):
    return auth(sub="bridgeclient@clients", scope="bridge", gty="client-credentials")


# ── S3 + app ──────────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def s3():
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1", aws_access_key_id="x", aws_secret_access_key="x")
        client.create_bucket(Bucket=BUCKET)
        yield client


def make_settings(url: str, **over) -> config.Settings:
    base = dict(database_url=url, auth0_issuer=ISSUER, auth0_audience=AUDIENCE,
                auth0_jwks_url=ISSUER + ".well-known/jwks.json", s3_endpoint=None, s3_region="us-east-1",
                s3_bucket=BUCKET, s3_access_key="x", s3_secret_key="x", cors_origins=["http://localhost:5173"],
                leaderboard_cache_secs=0, deepspace_push_interval=0)
    base.update(over)
    return config.Settings(**base)


@pytest.fixture
def make_client(pg, s3, jwks):
    made = []

    def make(transport=None, **over):
        s = make_settings(pg, **over)
        db = Database(pg, max_size=4)
        app = create_app(s, db=db, storage=Storage(s, client=s3),
                         verifier=Verifier(ISSUER, AUDIENCE, JWKSCache("unused", fetch=lambda _u: jwks)),
                         deepspace_transport=transport)
        tc = TestClient(app)
        tc.__enter__()
        made.append((tc, db))
        return tc
    yield make
    for tc, db in made:
        tc.__exit__(None, None, None)
        db.close()


@pytest.fixture
def client(make_client):
    return make_client()


def jpeg(w=1600, h=1200, exif=True, color=(200, 120, 40)) -> bytes:
    img = Image.new("RGB", (w, h), color)
    out = io.BytesIO()
    if exif:
        ex = Image.Exif()
        ex[0x010F] = "SecretCam"           # Make
        ex[0x8825] = {2: (29.0, 38.0, 0.0)}  # GPSInfo
        img.save(out, "JPEG", exif=ex)
    else:
        img.save(out, "JPEG")
    return out.getvalue()


def png(w=300, h=500, alpha=True) -> bytes:
    img = Image.new("RGBA" if alpha else "RGB", (w, h), (10, 80, 200, 128) if alpha else (10, 80, 200))
    out = io.BytesIO()
    img.save(out, "PNG")
    return out.getvalue()
