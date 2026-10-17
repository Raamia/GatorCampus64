"""POST /characters, limits, GET /jobs/{id}, gallery, delete."""
import io

from PIL import Image

from .conftest import BUCKET, jpeg
from .helpers import claim, finish, run_job, upload


def test_upload_creates_queued_job_with_clean_photos(client, auth, conn, s3):
    r = upload(client, auth(nickname="Ali"), name=" Ali Gator ", n=3, photo=jpeg(2400, 1800))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["state"] == "queued" and body["name"] == "Ali Gator"
    job = conn.execute("SELECT * FROM jobs WHERE id = %s", (body["job_id"],)).fetchone()
    ch = conn.execute("SELECT * FROM characters WHERE id = %s", (body["character_id"],)).fetchone()
    assert job["state"] == ch["state"] == "queued" and ch["owner_sub"] == "auth0|alice" and ch["slot"] is None
    assert job["photos"] == [f"photos/{body['job_id']}/{i}.jpg" for i in range(3)]
    for k in job["photos"]:
        data = s3.get_object(Bucket=BUCKET, Key=k)["Body"].read()
        img = Image.open(io.BytesIO(data))
        assert max(img.size) == 1024 and b"SecretCam" not in data


def test_upload_validation(make_client, auth, conn):
    client = make_client(max_photo_bytes=50_000)
    h = auth()
    assert upload(client, h, consent="").status_code == 422
    assert upload(client, h, consent="false").status_code == 422
    assert upload(client, h, name="ThirteenChars").status_code == 422
    assert upload(client, h, name="fuck").status_code == 422
    assert upload(client, h, n=5, photo=jpeg(50, 50)).status_code == 422
    assert client.post("/characters", headers=h, data={"name": "A", "consent": "1"}).status_code == 422
    assert upload(client, h, photo=b"GIF89a....").status_code == 422
    big = Image.effect_noise((1500, 1500), 100).convert("RGB")
    buf = io.BytesIO()
    big.save(buf, "PNG")
    assert upload(client, h, photo=buf.getvalue()).status_code == 413
    assert upload(client, auth(scope="read:own")).status_code == 403
    assert conn.execute("SELECT count(*) AS n FROM jobs").fetchone()["n"] == 0


def test_user_limits(client, auth, conn, s3):
    h = auth()
    assert upload(client, h).status_code == 201
    r = upload(client, h)
    assert r.status_code == 429 and "oven" in r.json()["detail"]
    run_job(conn, s3)
    assert upload(client, h).status_code == 201
    run_job(conn, s3, state="failed")           # failures don't count toward the 3
    assert upload(client, h).status_code == 201
    run_job(conn, s3)
    assert upload(client, h).status_code == 201
    run_job(conn, s3)
    r = upload(client, h)
    assert r.status_code == 429 and "3 gators" in r.json()["detail"]
    assert upload(client, auth(sub="auth0|bob")).status_code == 201  # per user


def test_global_hourly_limit(make_client, auth, conn):
    client = make_client(limit_global_hour=2)
    assert upload(client, auth(sub="a|1")).status_code == 201
    assert upload(client, auth(sub="a|2")).status_code == 201
    r = upload(client, auth(sub="a|3"))
    assert r.status_code == 429 and r.headers["retry-after"]
    conn.execute("UPDATE jobs SET created = now() - interval '2 hours'")
    assert upload(client, auth(sub="a|3")).status_code == 201


def test_rejected_upload_leaves_no_photos(make_client, auth, s3):
    client = make_client(limit_global_hour=0)
    assert upload(client, auth()).status_code == 429
    assert s3.list_objects_v2(Bucket=BUCKET).get("KeyCount", 0) == 0


def test_get_job_progress_and_previews(client, auth, conn, s3):
    h = auth()
    jid = upload(client, h).json()["job_id"]
    r = client.get(f"/jobs/{jid}", headers=h).json()
    assert r["state"] == "queued" and r["step_index"] == 0 and r["previews"] == [] and r["pipeline"][-1] == "ready"
    j = claim(conn)
    r = client.get(f"/jobs/{jid}", headers=h).json()
    assert r["step"] == "spec" and r["step_index"] == 1 and r["slot"] is None
    conn.execute("UPDATE jobs SET state='preview', step='store' WHERE id=%s", (j["id"],))
    r = client.get(f"/jobs/{jid}", headers=h).json()
    assert r["state"] == "preview" and r["step"] == "store" and r["step_index"] == 6
    finish(conn, s3, j)
    r = client.get(f"/jobs/{jid}", headers=h).json()
    assert r["state"] == "ready" and r["step_index"] == 7 and r["slot"] == 1 and not r["deployed"]
    assert [p["name"] for p in r["previews"]] == ["front.png", "side.png"]
    assert "Signature=" in r["previews"][0]["url"] or "X-Amz-Signature=" in r["previews"][0]["url"]
    assert r["portrait"]
    assert client.get(f"/jobs/{jid}", headers=auth(sub="auth0|mallory")).status_code == 404
    assert client.get(f"/jobs/{jid}", headers=auth(sub="auth0|admin", scope="admin:slots")).status_code == 200
    assert client.get("/jobs/not-a-uuid", headers=h).status_code == 422


def test_get_job_lists_previews_when_worker_left_no_manifest(client, auth, conn, s3):
    h = auth()
    jid = upload(client, h).json()["job_id"]
    j = claim(conn)
    s3.put_object(Bucket=BUCKET, Key=f"builds/{jid}/previews/a.png", Body=b"x")
    s3.put_object(Bucket=BUCKET, Key=f"builds/{jid}/previews/notes.txt", Body=b"x")
    conn.execute("UPDATE jobs SET state='preview', step='preview' WHERE id=%s", (j["id"],))
    assert [p["name"] for p in client.get(f"/jobs/{jid}", headers=h).json()["previews"]] == ["a.png"]


def test_failed_job(client, auth, conn, s3):
    h = auth()
    jid = upload(client, h).json()["job_id"]
    run_job(conn, s3, state="failed")
    r = client.get(f"/jobs/{jid}", headers=h).json()
    assert r["state"] == "failed" and r["step"] == "build" and r["error"] == "boom" and r["log"] == "tail"
    assert r["slot"] is None
    assert conn.execute("SELECT count(*) AS n FROM slots WHERE character_id IS NOT NULL").fetchone()["n"] == 0


def test_gallery_and_me(client, auth, conn, s3):
    h = auth(nickname="Ali", **{"https://chooseyourgator.select/uf": True})
    cid = upload(client, h, name="Ally").json()["character_id"]
    assert client.get("/characters").json()["characters"] == []  # only ready ones
    run_job(conn, s3)
    g = client.get("/characters").json()["characters"]
    assert len(g) == 1 and g[0]["name"] == "Ally" and g[0]["owner"] == "Ali" and g[0]["uf"] is True
    assert g[0]["slot"] == 1 and g[0]["deployed"] is False and len(g[0]["previews"]) == 2
    assert "owner_sub" not in g[0]
    me = client.get("/me", headers=h).json()
    assert [c["id"] for c in me["characters"]] == [cid] and me["characters"][0]["job_id"]


def test_delete(client, auth, conn, s3, bridge):
    h = auth()
    body = upload(client, h).json()
    run_job(conn, s3)
    client.get("/deploys/pending", headers=bridge)
    d = conn.execute("SELECT id FROM deploys WHERE state='pending'").fetchone()
    assert client.post(f"/deploys/{d['id']}", json={"state": "deployed"}, headers=bridge).status_code == 200
    assert client.delete(f"/characters/{body['character_id']}", headers=auth(sub="auth0|mallory")).status_code == 404
    r = client.delete(f"/characters/{body['character_id']}", headers=h)
    assert r.status_code == 200 and r.json()["freed_slot"] == 1
    assert conn.execute("SELECT count(*) AS n FROM characters").fetchone()["n"] == 0
    assert conn.execute("SELECT character_id FROM slots WHERE n=1").fetchone()["character_id"] is None
    assert s3.list_objects_v2(Bucket=BUCKET, Prefix=f"builds/{body['job_id']}/").get("KeyCount", 0) == 0
    p = client.get("/deploys/pending", headers=bridge).json()["deploys"]
    assert [(x["slot"], x["kind"]) for x in p] == [(1, "placeholder")]


def test_admin_delete_in_progress(client, auth, conn):
    body = upload(client, auth()).json()
    r = client.delete(f"/characters/{body['character_id']}", headers=auth(sub="auth0|admin", scope="admin:slots"))
    assert r.status_code == 200 and r.json()["freed_slot"] is None
    assert conn.execute("SELECT count(*) AS n FROM jobs").fetchone()["n"] == 0
    assert conn.execute("SELECT count(*) AS n FROM deploys").fetchone()["n"] == 0
