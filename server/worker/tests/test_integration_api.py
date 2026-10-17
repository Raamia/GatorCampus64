"""Integration: the real API (server/api: schema.sql, FastAPI app) and the real worker (db.py,
worker.handle, pipeline with tests/fake_blender.py standing in for Blender) on one Postgres and
one (moto) bucket. Checks the whole contract the bridge relies on:

  POST /characters → claim (no slot) → pipeline → ready + sgl_assign_slot → GET /jobs/{id}
  previews → GET /deploys/pending: actor guest_<slot>, build_id sglguest, files[] = the worker's keys.

Needs the API's deps too: pip install -r server/api/requirements-dev.txt -r server/worker/requirements-dev.txt
"""
import io
import json
import os
import sys
import time

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("moto")
pytest.importorskip("jwt")

import boto3  # noqa: E402
import jwt  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from jwt.algorithms import RSAAlgorithm  # noqa: E402
from moto import mock_aws  # noqa: E402

import db  # noqa: E402
import spec_ai  # noqa: E402
import storage  # noqa: E402
import worker  # noqa: E402
import pipeline  # noqa: E402
from test_pipeline import fake_repo  # noqa: E402,F401 - fixture
from test_spec_ai import GOOD, synthetic_photo  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "api"))
from sgl_api import config  # noqa: E402
from sgl_api.app import create_app  # noqa: E402
from sgl_api.auth import JWKSCache, Verifier  # noqa: E402
from sgl_api.db import Database  # noqa: E402
from sgl_api.storage import Storage  # noqa: E402

ISSUER, AUDIENCE, BUCKET = "https://login.test.example/", "https://api.chooseyourgator.select", "sgl-integ"


@pytest.fixture
def api(pg, tmp_path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(RSAAlgorithm.to_jwk(key.public_key()))
    jwk.update(kid="k", use="sig", alg="RS256")

    def headers(sub, scope, **claims):
        now = int(time.time())
        tok = jwt.encode({"sub": sub, "aud": AUDIENCE, "iss": ISSUER, "iat": now, "exp": now + 600, "scope": scope,
                          **claims}, key, algorithm="RS256", headers={"kid": "k"})
        return {"Authorization": f"Bearer {tok}"}

    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1", aws_access_key_id="x", aws_secret_access_key="x")
        s3.create_bucket(Bucket=BUCKET)
        s = config.Settings(database_url=pg, auth0_issuer=ISSUER, auth0_audience=AUDIENCE,
                            auth0_jwks_url=ISSUER + ".well-known/jwks.json", s3_endpoint=None, s3_region="us-east-1",
                            s3_bucket=BUCKET, s3_access_key="x", s3_secret_key="x")
        database = Database(pg, max_size=2)
        app = create_app(s, db=database, storage=Storage(s, client=s3),
                         verifier=Verifier(ISSUER, AUDIENCE, JWKSCache("unused", fetch=lambda _u: {"keys": [jwk]})))
        with TestClient(app) as client:
            yield client, headers, s3
        database.close()


def test_upload_build_deploy_contract(api, pg, fake_repo, tmp_path):  # noqa: F811
    client, headers, s3 = api
    user = headers("auth0|ali", "create:character read:own", nickname="Ali")
    bridge = headers("bridge@clients", "bridge", gty="client-credentials")

    # 1. the API stores the photos and the queued job
    files = [("photos", (f"p{i}.png", synthetic_photo(), "image/png")) for i in range(2)]
    r = client.post("/characters", headers=user, data={"name": "Ally", "consent": "true"}, files=files)
    assert r.status_code == 201, r.text
    job_id, char_id = r.json()["job_id"], r.json()["character_id"]

    # 2. the worker claims it: in progress, no slot yet
    conn = db.connect(pg)
    try:
        job = db.claim_job(conn, "gpu-test")
        assert str(job["id"]) == job_id and job["photos"] == [f"photos/{job_id}/0.jpg", f"photos/{job_id}/1.jpg"]
        jr = client.get(f"/jobs/{job_id}", headers=user).json()
        assert jr["state"] == "spec" and jr["slot"] is None and jr["step_index"] == 1

        # 3. the real pipeline (fake Blender) on the API's bucket, through worker.handle
        store = storage.S3Storage(BUCKET, client=s3)
        cfg = pipeline.Config(repo=fake_repo, blender="/nonexistent/blender", work_root=str(tmp_path / "work"),
                              build_timeout=30, use_cv=False)
        assert worker.handle(conn, job, store, spec_ai.StaticBackend(GOOD), cfg, log=lambda m: None)
        ch = conn.execute("SELECT state, step, slot FROM characters WHERE id = %s", (char_id,)).fetchone()
        assert ch == {"state": "ready", "step": "ready", "slot": 1}
    finally:
        conn.close()
    assert store.list(f"photos/{job_id}/") == []

    # 4. the owner's job page: previews/portrait are the worker's keys
    jr = client.get(f"/jobs/{job_id}", headers=user).json()
    assert jr["state"] == "ready" and jr["step"] == "ready" and jr["step_index"] == 7 and jr["slot"] == 1
    names = [p["name"] for p in jr["previews"]]
    assert "front.png" in names and "head.png" in names
    assert all(f"builds/{job_id}/previews/" in p["url"] for p in jr["previews"])
    assert f"builds/{job_id}/portrait.png" in jr["portrait"]
    gal = client.get("/characters").json()["characters"]
    assert [g["name"] for g in gal] == ["Ally"] and gal[0]["slot"] == 1 and gal[0]["previews"]

    # 5. the bridge's view
    pend = client.get("/deploys/pending", headers=bridge).json()
    assert len(pend["deploys"]) == 1
    d = pend["deploys"][0]
    assert d["kind"] == "character" and d["slot"] == 1 and d["actor"] == "guest_1"
    assert d["build_id"] == "sglguest" and d["job_id"] == job_id and d["prefix"] == f"builds/{job_id}/"
    paths = [f["path"] for f in d["files"]]
    assert paths == ["actors/sglguest/geo.inc.c", "actors/sglguest/geo_header.h", "actors/sglguest/model.inc.c",
                     "character.json", "manifest.json", "portrait.png"]
    for p in paths:  # every listed file really exists where the presigned URL points
        s3.head_object(Bucket=BUCKET, Key=d["prefix"] + p)
    spec = json.load(io.BytesIO(s3.get_object(Bucket=BUCKET, Key=d["prefix"] + "character.json")["Body"].read()))
    assert spec["id"] == "sglguest" and spec["name"] == "Ally"
    assert pend["roster"][0]["name"] == "Ally" and pend["roster"][0]["slot"] == 1

    # 6. deployed: the deploy leaves the queue and the character shows as on the server
    assert client.post(f"/deploys/{d['id']}", json={"state": "deployed"}, headers=bridge).status_code == 200
    assert client.get("/deploys/pending", headers=bridge).json()["deploys"] == []
    assert client.get(f"/jobs/{job_id}", headers=user).json()["deployed"] is True
