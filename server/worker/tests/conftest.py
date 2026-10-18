"""Shared fixtures. Postgres tests run against the API's real schema (server/api/schema.sql) on
$TEST_DATABASE_URL (or $SGL_TEST_DATABASE_URL), else a throwaway postgres:16-alpine container
started with docker; with neither they are skipped.
"""
import os
import shutil
import subprocess
import sys
import time
import uuid

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
WORKER = os.path.dirname(HERE)
sys.path.insert(0, WORKER)  # server/worker
SCHEMA_SQL = os.path.join(WORKER, "..", "api", "schema.sql")
TABLES = "generation_admissions, deploys, events, link_codes, links, slots, jobs, characters, users"


def _wait(url, secs=30):
    import psycopg
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
    url = os.environ.get("TEST_DATABASE_URL") or os.environ.get("SGL_TEST_DATABASE_URL")
    if url:
        _wait(url)
        yield url
        return
    if not shutil.which("docker"):
        pytest.skip("no Postgres: set TEST_DATABASE_URL or install docker")
    name = f"sgl-worker-test-{uuid.uuid4().hex[:8]}"
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
def schema_url(pg_url):
    import psycopg
    with open(SCHEMA_SQL) as f:
        sql = f.read()
    with psycopg.connect(pg_url, autocommit=True) as c:
        c.execute(sql)
    return pg_url


@pytest.fixture
def pg(schema_url):
    """A clean database with the API schema (8 empty slots)."""
    import psycopg
    with psycopg.connect(schema_url, autocommit=True) as c:
        c.execute(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE")
        c.execute("INSERT INTO slots (n) SELECT generate_series(1, 8)")
    return schema_url
