"""FastAPI app: docs/web_platform_spec.md §8 (plus §5.1-§5.3, §7.2-§7.4, §10.2 leaderboards).

Run:  uvicorn --factory sgl_api.app:create_app --host 127.0.0.1 --port 8000   (from server/api/)
"""

import json
import logging
import re
import secrets
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Annotated, Any, Callable

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field, model_validator

from . import config, images, names, runs
from .auth import AuthError, JWKSCache, Principal, Verifier, bearer
from .deepspace import Pusher
from .missions import MISSIONS
from .db import Database, apply_schema
from .storage import Storage

log = logging.getLogger("sgl_api")

PIPELINE = ["queued", "spec", "face", "build", "export", "validate", "preview", "ready"]
IN_PROGRESS = ("queued", "spec", "face", "build", "export", "validate", "preview")
SUBSTEPS = {"store": "preview"}  # jobs.step values finer than jobs.state (schema.sql header)
BUILD_ID = "sglguest"            # neutral actor id every job is built under (server/worker/actor_rename.py)
DEPLOY_TOP_FILES = ("portrait.png", "character.json", "manifest.json")
CODE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"  # no 0/O/1/I: typed from a phone into chat
CODE_LEN = 6
MAX_PHOTOS = 4
LOG_TAIL = 4000
SCOPE_CREATE, SCOPE_READ, SCOPE_ADMIN, SCOPE_BRIDGE = "create:character", "read:own", "admin:slots", "bridge"
IMG_RE = re.compile(r"\.(png|jpe?g|webp)$", re.I)


# ── request bodies ────────────────────────────────────────────────────────────────────────────

class LinkIn(BaseModel):
    sub: str | None = Field(None, max_length=200)       # device flow: from the validated ID token
    code: str | None = Field(None, max_length=16)       # §7.2: typed with /link <code>
    coopdx_name: str = Field(..., min_length=1, max_length=64)
    gi: int = Field(..., ge=0, le=255)
    nickname: str | None = Field(None, max_length=64)   # device flow: ID token nickname (optional)
    uf: bool | None = None                              # device flow: ID token uf claim (optional)

    @model_validator(mode="after")
    def one_of(self):
        if bool(self.sub) == bool(self.code):
            raise ValueError("give exactly one of sub (device flow) or code (link code)")
        return self


def event_fields(e: dict) -> dict:
    """An event's fields. The bridge posts {t, payload, at} with the payload's fields repeated at
    the top level; top-level wins, the nested payload fills in anything missing."""
    nested = e.get("payload")
    return {**nested, **e} if isinstance(nested, dict) else e


class DeployResult(BaseModel):
    state: str = Field(..., pattern="^(deployed|failed)$")
    error: str | None = Field(None, max_length=2000)


class SlotPatch(BaseModel):
    pinned: bool


# ── app factory ───────────────────────────────────────────────────────────────────────────────

def create_app(settings: config.Settings | None = None, *, db: Database | None = None,
               storage: Storage | None = None, verifier: Verifier | None = None,
               deepspace_transport: httpx.BaseTransport | None = None) -> FastAPI:
    s = settings or config.load()
    state: dict[str, Any] = {}
    board_cache: dict[str, tuple[float, Any]] = {}
    board_lock = threading.Lock()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if s.apply_schema:
            apply_schema(s.database_url)
        state["db"] = db or Database(s.database_url)
        state["storage"] = storage or Storage(s)
        state["verifier"] = verifier or Verifier(s.auth0_issuer, s.auth0_audience, JWKSCache(s.auth0_jwks_url),
                                                 claim_ns=s.claim_namespace)
        state["pusher"] = Pusher(s, lambda: state["db"], transport=deepspace_transport)
        state["pusher"].start()
        app.state.pusher = state["pusher"]
        yield
        state["pusher"].close()
        if db is None:
            state["db"].close()

    app = FastAPI(title="Super Gatorlator 64 API", version="1.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=s.cors_origins, allow_credentials=False,
                       allow_methods=["GET", "POST", "DELETE", "PUT", "OPTIONS"],
                       allow_headers=["Authorization", "Content-Type"], max_age=600)

    @app.exception_handler(AuthError)
    async def _auth_error(_req: Request, e: AuthError):
        headers = {"WWW-Authenticate": f'Bearer error="{"insufficient_scope" if e.status == 403 else "invalid_token"}"'}
        return JSONResponse({"detail": e.detail}, status_code=e.status, headers=headers)

    def DB() -> Database:
        return state["db"]

    def ST() -> Storage:
        return state["storage"]

    # ── auth dependencies ─────────────────────────────────────────────────────────────────────

    def principal(request: Request) -> Principal:
        return state["verifier"].verify(bearer(request.headers.get("authorization")))

    def upsert_user(p: Principal, nickname: str | None = None, uf: bool | None = None) -> None:
        with DB().tx() as c:
            c.execute(
                """INSERT INTO users (sub, nickname, email_uf) VALUES (%s, %s, %s)
                   ON CONFLICT (sub) DO UPDATE SET
                     nickname = COALESCE(EXCLUDED.nickname, users.nickname),
                     email_uf = EXCLUDED.email_uf OR users.email_uf,
                     last_seen = now()""",
                (p.sub, nickname or p.nickname, bool(uf if uf is not None else p.email_uf)))

    def user(*scopes: str, admin_ok: bool = False) -> Callable[..., Principal]:
        """A logged-in person (not an M2M client) holding all `scopes`; upserted into users."""
        def dep(p: Annotated[Principal, Depends(principal)]) -> Principal:
            if p.is_m2m:
                raise AuthError(403, "user token required")
            missing = [sc for sc in scopes if sc not in p.scopes]
            if missing and not (admin_ok and SCOPE_ADMIN in p.scopes):
                raise AuthError(403, f"missing scope: {' '.join(missing)}")
            upsert_user(p)
            return p
        return dep

    def scoped(scope: str) -> Callable[..., Principal]:
        def dep(p: Annotated[Principal, Depends(principal)]) -> Principal:
            if scope not in p.scopes:
                raise AuthError(403, f"missing scope: {scope}")
            return p
        return dep

    # ── helpers ───────────────────────────────────────────────────────────────────────────────

    def preview_keys(job: dict, allow_list: bool) -> tuple[list[str], str | None]:
        arts = job.get("artifacts") or {}
        keys = [k for k in arts.get("previews") or [] if isinstance(k, str)]
        if not keys and allow_list and job["state"] in ("preview", "ready"):
            try:
                keys = sorted(k for k in ST().list(f"builds/{job['id']}/previews/") if IMG_RE.search(k))
            except Exception:  # noqa: BLE001
                log.exception("listing previews for %s", job["id"])
        portrait = arts.get("portrait") if isinstance(arts.get("portrait"), str) else None
        return keys, portrait

    def presigned(keys: list[str]) -> list[dict]:
        return [{"name": k.rsplit("/", 1)[-1], "url": ST().presign(k)} for k in keys]

    # ── public ────────────────────────────────────────────────────────────────────────────────

    @app.get("/healthz")
    def healthz():
        with DB().tx() as c:
            c.execute("SELECT 1")
        return {"ok": True}

    @app.get("/characters")
    def gallery(limit: int = 60):
        limit = max(1, min(limit, 200))
        with DB().tx() as c:
            rows = c.execute(
                """SELECT ch.id, ch.name, ch.slot, ch.created, ch.deployed_at, u.nickname, u.email_uf,
                          COALESCE(sl.pinned, false) AS pinned, j.id AS job_id, j.state, j.artifacts
                     FROM characters ch JOIN users u ON u.sub = ch.owner_sub
                     LEFT JOIN slots sl ON sl.character_id = ch.id
                     LEFT JOIN LATERAL (SELECT * FROM jobs WHERE character_id = ch.id AND state = 'ready'
                                        ORDER BY finished DESC NULLS LAST LIMIT 1) j ON true
                    WHERE ch.state = 'ready'
                    ORDER BY ch.deployed_at DESC NULLS LAST, ch.created DESC LIMIT %s""", (limit,)).fetchall()
        out = []
        for r in rows:
            keys, portrait = (preview_keys({"id": r["job_id"], "state": "ready", "artifacts": r["artifacts"]},
                                           allow_list=False) if r["job_id"] else ([], None))
            out.append({"id": r["id"], "name": r["name"], "owner": r["nickname"], "uf": r["email_uf"],
                        "slot": r["slot"], "pinned": r["pinned"], "deployed": r["deployed_at"] is not None,
                        "deployed_at": r["deployed_at"], "created": r["created"],
                        "previews": presigned(keys), "portrait": ST().presign(portrait) if portrait else None})
        return {"characters": out}

    @app.get("/status")
    def status():
        with DB().tx() as c:
            hello = c.execute("SELECT id, at, payload FROM events WHERE t = 'hello' ORDER BY id DESC LIMIT 1").fetchone()
            last = c.execute("SELECT max(at) AS at FROM events").fetchone()["at"]
            slots = c.execute(
                """SELECT sl.n, sl.pinned, ch.name, ch.deployed_at IS NOT NULL AS deployed
                     FROM slots sl LEFT JOIN characters ch ON ch.id = sl.character_id ORDER BY sl.n""").fetchall()
            queue = c.execute(f"SELECT count(*) AS n FROM jobs WHERE state IN {IN_PROGRESS}").fetchone()["n"]
            if not hello:
                return {"online": False, "players": [], "player_count": 0, "version": None,
                        "since": None, "last_event_at": last, "slots": slots, "jobs_in_progress": queue}
            down = c.execute("SELECT 1 FROM events WHERE t IN ('exit','bye') AND id > %s LIMIT 1",
                             (hello["id"],)).fetchone()
            pres = c.execute(
                """SELECT DISTINCT ON (COALESCE(payload->>'gi', payload->'payload'->>'gi')) t, payload FROM events
                    WHERE t IN ('join','leave') AND id > %s
                    ORDER BY COALESCE(payload->>'gi', payload->'payload'->>'gi'), id DESC""",
                (hello["id"],)).fetchall()
            if s.status_stale_secs > 0:
                stale = c.execute("SELECT max(at) < now() - make_interval(secs => %s) AS stale FROM events",
                                  (s.status_stale_secs,)).fetchone()["stale"]
            else:
                stale = False
        online = not down and not stale
        players = [{"gi": f.get("gi"), "name": f.get("name")}
                   for p in pres if p["t"] == "join" for f in [event_fields(p["payload"])]] if online else []
        hp = event_fields(hello["payload"])
        return {"online": online, "players": players, "player_count": len(players),
                "version": hp.get("version") or hp.get("v") or hp.get("mod_version"),
                "since": hello["at"], "last_event_at": last, "slots": slots, "jobs_in_progress": queue,
                "address": s.play_address}

    # ── leaderboards (§10.2, public) ──────────────────────────────────────────────────────────

    def cached(key: str, build: Callable[[], Any]) -> Any:
        if s.leaderboard_cache_secs <= 0:
            return build()
        now = time.monotonic()
        with board_lock:
            hit = board_cache.get(key)
            if hit and hit[0] > now:
                return hit[1]
        value = build()
        with board_lock:
            board_cache[key] = (now + s.leaderboard_cache_secs, value)
        return value

    def board_headers(response: Response) -> None:
        response.headers["Cache-Control"] = f"public, max-age={max(s.leaderboard_cache_secs, 0)}"

    @app.get("/leaderboards")
    def leaderboards(response: Response):
        def build():
            with DB().tx() as c:
                b = runs.boards(c, list(MISSIONS), runs.TOP_DEFAULT)
            return {"missions": [{"mission": m, "title": MISSIONS[m]["title"], "rows": b[m]} for m in MISSIONS]}
        board_headers(response)
        return cached("all", build)

    @app.get("/leaderboards/{mission}")
    def leaderboard(mission: str, response: Response, limit: int = 10):
        if mission not in MISSIONS:
            raise HTTPException(404, "no such mission")
        limit = max(1, min(limit, runs.LIMIT_MAX))

        def build():
            with DB().tx() as c:
                rows = runs.boards(c, [mission], limit)[mission]
            m = MISSIONS[mission]
            return {"mission": mission, "title": m["title"], "par": m["par"], "gold": m["gold"],
                    "floor_frames": m["floor_frames"], "rows": rows}
        board_headers(response)
        return cached(f"{mission}:{limit}", build)

    # ── users ─────────────────────────────────────────────────────────────────────────────────

    @app.get("/me")
    def me(p: Annotated[Principal, Depends(user(SCOPE_READ))]):
        with DB().tx() as c:
            u = c.execute("SELECT sub, nickname, email_uf FROM users WHERE sub = %s", (p.sub,)).fetchone()
            chars = c.execute(
                """SELECT ch.id, ch.name, ch.state, ch.step, ch.slot, ch.created, ch.deployed_at,
                          (SELECT id FROM jobs WHERE character_id = ch.id ORDER BY created DESC LIMIT 1) AS job_id
                     FROM characters ch WHERE owner_sub = %s ORDER BY created DESC""", (p.sub,)).fetchall()
            link = c.execute("SELECT coopdx_name, linked_at FROM links WHERE sub = %s ORDER BY linked_at DESC LIMIT 1",
                             (p.sub,)).fetchone()
        return {"user": u, "characters": chars, "last_link": link, "admin": SCOPE_ADMIN in p.scopes,
                "limits": {"in_progress": s.limit_user_active, "total": s.limit_user_total}}

    @app.post("/characters", status_code=201)
    def create_character(
        p: Annotated[Principal, Depends(user(SCOPE_CREATE))],
        name: Annotated[str, Form(max_length=64)],
        consent: Annotated[str, Form()] = "",
        photos: Annotated[list[UploadFile], File()] = [],  # noqa: B006 - FastAPI default
    ):
        try:
            clean_name = names.validate(name)
        except names.NameInvalid as e:
            raise HTTPException(422, str(e)) from e
        if consent.strip().lower() not in ("1", "true", "on", "yes"):
            raise HTTPException(422, "consent is required: tick the box to confirm these are photos of you "
                                     "(or you have permission) and that they may be processed")
        photos = [f for f in photos if f and f.filename]
        if not 1 <= len(photos) <= MAX_PHOTOS:
            raise HTTPException(422, f"upload 1 to {MAX_PHOTOS} photos")
        raws = []
        for f in photos:
            data = f.file.read(s.max_photo_bytes + 1)
            if len(data) > s.max_photo_bytes:
                raise HTTPException(413, f"{f.filename}: photos must be at most {s.max_photo_bytes // (1024 * 1024)} MB")
            raws.append((f.filename, data))
        try:
            with ThreadPoolExecutor(max_workers=len(raws)) as ex:
                cleaned = list(ex.map(lambda r: images.process(r[1], s.photo_max_side), raws))
        except images.PhotoError as e:
            raise HTTPException(422, str(e)) from e

        cid, jid = uuid.uuid4(), uuid.uuid4()
        keys = [f"photos/{jid}/{i}.jpg" for i in range(len(cleaned))]
        uploaded: list[str] = []
        try:
            with DB().tx() as c:
                c.execute("SELECT pg_advisory_xact_lock(hashtext('sgl_create'))")
                active = c.execute(f"SELECT count(*) AS n FROM characters WHERE owner_sub = %s AND state IN {IN_PROGRESS}",
                                   (p.sub,)).fetchone()["n"]
                if active >= s.limit_user_active:
                    raise HTTPException(429, "you already have a gator in the oven: wait for it to finish")
                total = c.execute("SELECT count(*) AS n FROM characters WHERE owner_sub = %s AND state <> 'failed'",
                                  (p.sub,)).fetchone()["n"]
                if total >= s.limit_user_total:
                    raise HTTPException(429, f"you already have {total} gators: delete one to make another")
                hour = c.execute("SELECT count(*) AS n, min(created) AS oldest FROM jobs "
                                 "WHERE created > now() - interval '1 hour'").fetchone()
                if hour["n"] >= s.limit_global_hour:
                    raise HTTPException(429, "the gator kitchen is at capacity this hour: try again soon",
                                        headers={"Retry-After": "600"})
                for k, data in zip(keys, cleaned):
                    ST().put(k, data, "image/jpeg")
                    uploaded.append(k)
                c.execute("INSERT INTO characters (id, owner_sub, name, state, step) VALUES (%s, %s, %s, 'queued', 'queued')",
                          (cid, p.sub, clean_name))
                c.execute("INSERT INTO jobs (id, character_id, state, step, photos) VALUES (%s, %s, 'queued', 'queued', %s)",
                          (jid, cid, keys))
        except BaseException:
            if uploaded:
                try:
                    ST().delete_keys(uploaded)
                except Exception:  # noqa: BLE001
                    log.exception("cleaning up photos for %s", jid)
            raise
        return {"character_id": cid, "job_id": jid, "state": "queued", "name": clean_name}

    @app.get("/jobs/{job_id}")
    def get_job(job_id: uuid.UUID, p: Annotated[Principal, Depends(user(SCOPE_READ, admin_ok=True))]):
        with DB().tx() as c:
            j = c.execute(
                """SELECT j.*, ch.name, ch.owner_sub, ch.slot, ch.deployed_at,
                          (SELECT state FROM deploys d WHERE d.character_id = ch.id ORDER BY d.id DESC LIMIT 1) AS deploy_state
                     FROM jobs j JOIN characters ch ON ch.id = j.character_id WHERE j.id = %s""", (job_id,)).fetchone()
        if not j or (j["owner_sub"] != p.sub and SCOPE_ADMIN not in p.scopes):
            raise HTTPException(404, "no such job")
        keys, portrait = preview_keys(j, allow_list=True)
        # Only this job's known browser artifact may be presigned; legacy jobs have none.
        browser_model = (j.get("artifacts") or {}).get("browser_model")
        if browser_model != f"builds/{j['id']}/preview.glb":
            browser_model = None
        step = j["step"] or j["state"]
        # position in PIPELINE: the failing step for failed jobs, else the state (store → preview)
        phase = SUBSTEPS.get(step, step) if j["state"] == "failed" else j["state"]
        return {
            "id": j["id"], "character_id": j["character_id"], "name": j["name"], "state": j["state"],
            "step": step, "pipeline": PIPELINE,
            "step_index": PIPELINE.index(phase) if phase in PIPELINE else None,
            "log": (j["log"] or "")[-LOG_TAIL:], "error": j["error"],
            "created": j["created"], "started": j["started"], "finished": j["finished"],
            "slot": j["slot"], "deployed": j["deployed_at"] is not None, "deploy_state": j["deploy_state"],
            "previews": presigned(keys), "portrait": ST().presign(portrait) if portrait else None,
            "browser_model": ST().presign(browser_model) if browser_model else None,
        }

    @app.delete("/characters/{character_id}")
    def delete_character(character_id: uuid.UUID, p: Annotated[Principal, Depends(principal)]):
        if p.is_m2m:
            raise AuthError(403, "user token required")
        is_admin = SCOPE_ADMIN in p.scopes
        with DB().tx() as c:
            ch = c.execute("SELECT id, owner_sub FROM characters WHERE id = %s FOR UPDATE", (character_id,)).fetchone()
            if not ch or (ch["owner_sub"] != p.sub and not is_admin):
                raise HTTPException(404, "no such character")
            freed = c.execute("SELECT sgl_release_slot(%s) AS n", (character_id,)).fetchone()["n"]
            jobs = [r["id"] for r in c.execute("SELECT id FROM jobs WHERE character_id = %s", (character_id,))]
            c.execute("DELETE FROM characters WHERE id = %s", (character_id,))
        for jid in jobs:
            for prefix in (f"photos/{jid}/", f"builds/{jid}/"):
                try:
                    ST().delete_prefix(prefix)
                except Exception:  # noqa: BLE001 - row is gone; storage lifecycle rules catch strays
                    log.exception("deleting %s", prefix)
        return {"deleted": character_id, "freed_slot": freed}

    @app.post("/link-codes", status_code=201)
    def link_code(p: Annotated[Principal, Depends(user())]):
        with DB().tx() as c:
            c.execute("DELETE FROM link_codes WHERE (sub = %s AND used_at IS NULL) OR expires_at < now() - interval '1 day'",
                      (p.sub,))
            for _ in range(10):
                code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LEN))
                row = c.execute(
                    """INSERT INTO link_codes (code, sub, expires_at) VALUES (%s, %s, now() + make_interval(secs => %s))
                       ON CONFLICT (code) DO NOTHING RETURNING code, expires_at""",
                    (code, p.sub, s.link_code_ttl)).fetchone()
                if row:
                    return {"code": row["code"], "expires_at": row["expires_at"], "expires_in": s.link_code_ttl,
                            "command": f"/link {row['code']}"}
        raise HTTPException(503, "could not allocate a code, try again")

    # ── bridge (M2M, scope `bridge`) ──────────────────────────────────────────────────────────

    @app.post("/links")
    def create_link(body: LinkIn, _p: Annotated[Principal, Depends(scoped(SCOPE_BRIDGE))]):
        with DB().tx() as c:
            if body.code:
                code = re.sub(r"[\s-]", "", body.code).upper()
                row = c.execute("SELECT code, sub, used_at, expires_at < now() AS expired FROM link_codes "
                                "WHERE code = %s FOR UPDATE", (code,)).fetchone()
                if not row:
                    raise HTTPException(404, {"reason": "invalid", "message": "unknown link code"})
                if row["used_at"] is not None:
                    raise HTTPException(410, {"reason": "used", "message": "link code already used"})
                if row["expired"]:
                    raise HTTPException(410, {"reason": "expired", "message": "link code expired"})
                c.execute("UPDATE link_codes SET used_at = now() WHERE code = %s", (code,))
                sub, via = row["sub"], "code"
            else:
                sub, via = body.sub, "device"
                c.execute("""INSERT INTO users (sub, nickname, email_uf) VALUES (%s, %s, %s)
                             ON CONFLICT (sub) DO UPDATE SET nickname = COALESCE(EXCLUDED.nickname, users.nickname),
                               email_uf = EXCLUDED.email_uf OR users.email_uf, last_seen = now()""",
                          (sub, body.nickname, bool(body.uf)))
            c.execute("INSERT INTO links (sub, coopdx_name, gi, via) VALUES (%s, %s, %s, %s)",
                      (sub, body.coopdx_name, body.gi, via))
            u = c.execute("SELECT nickname, email_uf FROM users WHERE sub = %s", (sub,)).fetchone()
            g = c.execute(
                """SELECT slot, name FROM characters WHERE owner_sub = %s AND slot IS NOT NULL AND state = 'ready'
                   AND deployed_at IS NOT NULL ORDER BY deployed_at DESC LIMIT 1""", (sub,)).fetchone()
        return {"sub": sub, "via": via, "nickname": (u and u["nickname"]) or body.coopdx_name,
                "uf": bool(u and u["email_uf"]), "gi": body.gi, "coopdx_name": body.coopdx_name,
                "guest_slot": g["slot"] if g else None, "character_name": g["name"] if g else None}

    @app.post("/events", status_code=202)
    async def post_events(request: Request, background: BackgroundTasks,
                          _p: Annotated[Principal, Depends(scoped(SCOPE_BRIDGE))]):
        try:
            body = await request.json()
        except Exception as e:  # noqa: BLE001
            raise HTTPException(422, "body must be JSON") from e
        evs = body if isinstance(body, list) else [body]
        if not evs or len(evs) > 500 or not all(isinstance(e, dict) and isinstance(e.get("t"), str) for e in evs):
            raise HTTPException(422, 'expected an event {"t": ...} or a list of up to 500 of them')
        stored_runs = []
        with DB().tx() as c:
            for e in evs:
                ev = c.execute("INSERT INTO events (t, payload) VALUES (%s, %s) RETURNING id",
                               (e["t"][:32], Jsonb(e))).fetchone()
                if e["t"] == "run":   # §10.1: always stored, ranked only when valid and fully linked
                    stored_runs.append(runs.store(c, event_fields(e), ev["id"]))
                elif e["t"] == "char":
                    f = event_fields(e)
                    fid = str(f.get("friend") or f.get("friend_id") or f.get("id") or "")
                    m = re.fullmatch(r"guest_([1-8])", fid)
                    if m:
                        c.execute("UPDATE slots SET last_played = now() WHERE n = %s", (int(m.group(1)),))
        if not stored_runs:
            return {"stored": len(evs)}
        for r in stored_runs:
            if r["ranked"]:
                log.info("run %s %s ranked", r["id"], r["mission"])
            else:
                log.info("run %s %s not ranked: %s", r["id"], r["mission"], r["reason"])
        if any(r["ranked"] for r in stored_runs):
            with board_lock:
                board_cache.clear()
            if state["pusher"].enabled:
                background.add_task(state["pusher"].drain)
        return {"stored": len(evs),
                "runs": [{k: r[k] for k in ("id", "mission", "ranked", "reason")} for r in stored_runs]}

    def roster(c) -> list[dict]:
        return c.execute(
            """SELECT sl.n AS slot, sl.pinned, ch.id AS character_id, ch.name, ch.owner_sub, u.nickname AS owner
                 FROM slots sl LEFT JOIN characters ch ON ch.id = sl.character_id AND ch.state = 'ready'
                 LEFT JOIN users u ON u.sub = ch.owner_sub ORDER BY sl.n""").fetchall()

    @app.get("/deploys/pending")
    def deploys_pending(_p: Annotated[Principal, Depends(scoped(SCOPE_BRIDGE))]):
        with DB().tx() as c:
            c.execute("SELECT sgl_sync_deploys()")
            rows = c.execute(
                """SELECT d.id, d.slot, d.kind, d.character_id, d.job_id, d.created, ch.name, ch.owner_sub,
                          u.nickname AS owner, j.artifacts
                     FROM deploys d LEFT JOIN characters ch ON ch.id = d.character_id
                     LEFT JOIN users u ON u.sub = ch.owner_sub LEFT JOIN jobs j ON j.id = d.job_id
                    WHERE d.state = 'pending' ORDER BY d.id""").fetchall()
            ros = roster(c)
        out = []
        for r in rows:
            d = {k: r[k] for k in ("id", "slot", "kind", "character_id", "job_id", "created", "name", "owner_sub", "owner")}
            d["actor"] = f"guest_{r['slot']}"
            d["files"] = []
            if r["kind"] == "character" and r["job_id"]:
                prefix = f"builds/{r['job_id']}/"
                arts = r["artifacts"] or {}
                build_id = arts.get("build_id") or BUILD_ID
                d["prefix"] = prefix
                d["build_id"] = build_id
                d["files"] = [{"path": rel, "url": ST().presign(prefix + rel)}
                              for rel in deploy_files(prefix, build_id, arts)]
                d["artifacts"] = r["artifacts"]
            out.append(d)
        return {"deploys": out, "roster": ros}

    def deploy_files(prefix: str, build_id: str, arts: dict) -> list[str]:
        """Paths (relative to builds/<job>/) the bridge needs: the actor export and the top-level
        portrait/spec/manifest. Keys come from jobs.artifacts (written by the worker on success),
        else from the stored manifest.json; never from listing the bucket."""
        keys = arts.get("files") if isinstance(arts.get("files"), list) else None
        if keys is None:
            try:
                keys = json.loads(ST().get(prefix + "manifest.json")).get("files") or []
            except Exception:  # noqa: BLE001 - no manifest: nothing deployable
                log.exception("reading %smanifest.json", prefix)
                keys = []
        actor = f"actors/{build_id}/"
        rels = {k[len(prefix):] for k in keys if isinstance(k, str) and k.startswith(prefix)}
        return sorted(r for r in rels if r in DEPLOY_TOP_FILES or (r.startswith(actor) and "/" not in r[len(actor):]))

    @app.post("/deploys/{deploy_id}")
    def deploy_result(deploy_id: int, body: DeployResult, _p: Annotated[Principal, Depends(scoped(SCOPE_BRIDGE))]):
        with DB().tx() as c:
            d = c.execute("SELECT * FROM deploys WHERE id = %s FOR UPDATE", (deploy_id,)).fetchone()
            if not d:
                raise HTTPException(404, "no such deploy")
            if d["state"] != "pending":
                raise HTTPException(409, {"reason": d["state"], "message": f"deploy is {d['state']}, not pending"})
            c.execute("UPDATE deploys SET state = %s, error = %s, finished = now() WHERE id = %s",
                      (body.state, body.error, deploy_id))
            if body.state == "deployed" and d["kind"] == "character" and d["character_id"]:
                c.execute("UPDATE characters SET deployed_at = now() WHERE id = %s AND slot = %s",
                          (d["character_id"], d["slot"]))
        return {"id": deploy_id, "state": body.state}

    # ── admin (scope admin:slots, §7.3) ───────────────────────────────────────────────────────

    @app.put("/slots/{n}")
    def pin_slot(n: int, body: SlotPatch, _p: Annotated[Principal, Depends(scoped(SCOPE_ADMIN))]):
        if not 1 <= n <= 8:
            raise HTTPException(404, "no such slot")
        with DB().tx() as c:
            c.execute("UPDATE slots SET pinned = %s WHERE n = %s", (body.pinned, n))
        return {"slot": n, "pinned": body.pinned}

    @app.post("/slots/{n}/redeploy", status_code=201)
    def force_deploy(n: int, _p: Annotated[Principal, Depends(scoped(SCOPE_ADMIN))]):
        with DB().tx() as c:
            sl = c.execute("SELECT sl.character_id, ch.state FROM slots sl LEFT JOIN characters ch ON ch.id = sl.character_id "
                           "WHERE sl.n = %s", (n,)).fetchone()
            if not sl:
                raise HTTPException(404, "no such slot")
            ready = sl["character_id"] and sl["state"] == "ready"
            d = c.execute("SELECT sgl_queue_deploy(%s::smallint, %s, %s) AS id",
                          (n, "character" if ready else "placeholder", sl["character_id"] if ready else None)).fetchone()
        return {"deploy_id": d["id"], "slot": n}

    return app

