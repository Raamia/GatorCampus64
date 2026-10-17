"""Token verification and scope checks through the real app."""
import time

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from .conftest import AUDIENCE


def test_no_token(client):
    r = client.get("/me")
    assert r.status_code == 401 and "WWW-Authenticate" in r.headers


def test_good_token_upserts_user(client, auth, conn):
    r = client.get("/me", headers=auth(nickname="Ali", **{"https://chooseyourgator.select/uf": True}))
    assert r.status_code == 200, r.text
    assert r.json()["user"] == {"sub": "auth0|alice", "nickname": "Ali", "email_uf": True}
    row = conn.execute("SELECT * FROM users").fetchone()
    assert row["sub"] == "auth0|alice" and row["email_uf"] is True


def test_rejections(client, auth, token):
    cases = {
        "wrong audience": auth(aud="https://other"),
        "wrong issuer": auth(iss="https://evil.example/"),
        "expired": auth(exp_in=-3600),
        "unknown kid": auth(kid="nope"),
        "other key": auth(key=rsa.generate_private_key(public_exponent=65537, key_size=2048)),
    }
    for why, h in cases.items():
        assert client.get("/me", headers=h).status_code == 401, why
    hs = jwt.encode({"sub": "x", "aud": AUDIENCE, "iss": "https://login.test.example/", "iat": int(time.time()),
                     "exp": int(time.time()) + 60}, "secret", algorithm="HS256", headers={"kid": "test-kid"})
    assert client.get("/me", headers={"Authorization": f"Bearer {hs}"}).status_code == 401
    assert client.get("/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
    assert client.get("/me", headers={"Authorization": "Basic abc"}).status_code == 401


def test_scopes(client, auth, bridge):
    assert client.get("/me", headers=auth(scope="create:character")).status_code == 403
    assert client.get("/me", headers=auth(scope="", permissions=["read:own"])).status_code == 200  # RBAC claim
    assert client.get("/deploys/pending", headers=auth(scope="read:own")).status_code == 403
    assert client.get("/deploys/pending", headers=bridge).status_code == 200
    # the M2M bridge token is not a person: no user endpoints even with the scope
    assert client.get("/me", headers=auth(sub="c@clients", scope="read:own bridge")).status_code == 403
    assert client.post("/link-codes", headers=bridge).status_code == 403
    assert client.put("/slots/1", json={"pinned": True}, headers=auth()).status_code == 403
    assert client.put("/slots/1", json={"pinned": True}, headers=auth(scope="admin:slots")).status_code == 200


def test_public_endpoints(client):
    assert client.get("/characters").status_code == 200
    assert client.get("/status").status_code == 200
    assert client.get("/healthz").json() == {"ok": True}


def test_cors(client):
    r = client.options("/characters", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST",
                                               "Access-Control-Request-Headers": "authorization"})
    assert r.status_code == 200 and r.headers["access-control-allow-origin"] == "http://localhost:5173"
