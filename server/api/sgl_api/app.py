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
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Literal, Annotated, Any, Callable

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from psycopg.types.json import Jsonb
from pydantic import AwareDatetime, BaseModel, Field, model_validator

from . import accounts, config, images, names, runs, pipeline_status
from .auth import AuthError, JWKSCache, Principal, Verifier, bearer
from .deepspace import Pusher
from .cleanup import Cleaner
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
    session_id: uuid.UUID | None = None
    connection_id: uuid.UUID | None = None
    sub: str | None = Field(None, max_length=200)       # device flow: from the validated ID token
    code: str | None = Field(None, max_length=16)       # §7.2: typed with /link <code>
    coopdx_name: str = Field(..., min_length=1, max_length=64)
    gi: int = Field(..., ge=0, le=255)
    nickname: str | None = Field(None, max_length=64)   # device flow: ID token nickname (optional)
    uf: bool | None = None                              # device flow: ID token uf claim (optional)

    @model_validator(mode="after")
    def one_of(self):
        if (self.session_id is None) != (self.connection_id is None):
            raise ValueError("session_id and connection_id must be supplied together")
        if bool(self.sub) == bool(self.code):
            raise ValueError("give exactly one of sub (device flow) or code (link code)")
        return self


def event_fields(e: dict) -> dict:
    """An event's fields. The bridge posts {t, payload, at} with the payload's fields repeated at
    the top level; top-level wins, the nested payload fills in anything missing."""
    nested = e.get("payload")
    return {**nested, **e} if isinstance(nested, dict) else e


class IdentityProof(BaseModel):
    action: Literal['link', 'unlink', 'status']
    user_id: str = Field(min_length=1, max_length=256, pattern=r'^[A-Za-z0-9_:@.|-]+$')
    token_hash: str = Field(pattern=r'^[0-9a-f]{64}$')


class PresencePlayer(BaseModel):
    gi: int = Field(ge=0, le=255)
    name: str = Field(max_length=64)


class PresenceIn(BaseModel):
    session_id: uuid.UUID
    observed_at: AwareDatetime
    online: bool
    since: AwareDatetime | None = None
    version: str | None = Field(None, max_length=64)
    players: list[PresencePlayer] = Field(default_factory=list, max_length=256)

    @model_validator(mode="after")
    def valid_snapshot(self):
        if self.since and self.since > self.observed_at:
            raise ValueError("since must not follow observed_at")
        if len({p.gi for p in self.players}) != len(self.players):
            raise ValueError("duplicate player index")
        return self


class DeployResult(BaseModel):
    state: str = Field(..., pattern="^(deployed|failed)$")
    error: str | None = Field(None, max_length=2000)


class DeployCheck(BaseModel):
    ids: list[int] = Field(max_length=8)


class DeployInventory(BaseModel):
    installed: dict[int, int | None] = Field(default_factory=dict, max_length=8)

    @model_validator(mode="after")
    def valid_slots(self):
        if any(n < 1 or n > 8 for n in self.installed):
            raise ValueError("slot must be between 1 and 8")
        return self


class LinkCheck(BaseModel):
    ids: list[int] = Field(max_length=256)


class AccountDelete(BaseModel):
    confirm: str = Field(pattern="^DELETE$")


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
    pipeline_cache: tuple[float, Any] | None = None
    pipeline_lock = threading.Lock()

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
        state["cleaner"] = Cleaner(state["db"], state["storage"])
        app.state.cleaner = state["cleaner"]
        state["cleaner"].start()
        yield
        state["cleaner"].close()
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
        p = state["verifier"].verify(bearer(request.headers.get("authorization")))
        if not p.is_m2m:
            with DB().tx() as c:
                accounts.require_active(c, p.sub, p.claims)
        return p

    def upsert_user(p: Principal, nickname: str | None = None, uf: bool | None = None) -> None:
        with DB().tx() as c:
            accounts.lock(c)
            accounts.require_active(c, p.sub, p.claims)
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

    @app.get("/pipeline/status")
    def public_pipeline_status(response: Response):
        nonlocal pipeline_cache
        response.headers["Cache-Control"] = f"public, max-age={pipeline_status.CACHE_SECONDS}"
        # Fixed-size query and a shared cache, like the public boards. Keep the
        # lock during refresh so simultaneous anonymous polls cannot stampede DB.
        with pipeline_lock:
            if pipeline_cache is None or pipeline_cache[0] <= time.monotonic():
                with DB().tx() as c:
                    c.execute("SET TRANSACTION READ ONLY")
                    value = pipeline_status.snapshot(c)
                pipeline_cache = (time.monotonic() + pipeline_status.CACHE_SECONDS, value)
            return pipeline_cache[1]

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

    @app.post("/presence")
    def post_presence(body: PresenceIn, p: Annotated[Principal, Depends(scoped(SCOPE_BRIDGE))]):
        if not p.is_m2m:
            raise AuthError(403, "machine token required")
        with DB().tx() as c:
            # A heartbeat is a fresh snapshot, never durable/replayable. Limit network delay
            # and clock skew; duplicates and reordered requests cannot extend its lifetime.
            fresh = c.execute("SELECT %s BETWEEN clock_timestamp() - interval '30 seconds' "
                              "AND clock_timestamp() + interval '5 seconds' AS fresh",
                              (body.observed_at,)).fetchone()["fresh"]
            if not fresh:
                raise HTTPException(422, "heartbeat timestamp is not fresh; check bridge clock")
            row = c.execute(
                """INSERT INTO server_presence (bridge_sub, session_id, observed_at, online, since, version, players)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (bridge_sub) DO UPDATE SET session_id = EXCLUDED.session_id,
                     observed_at = EXCLUDED.observed_at, received_at = clock_timestamp(),
                     online = EXCLUDED.online, since = EXCLUDED.since,
                     version = EXCLUDED.version, players = EXCLUDED.players
                   WHERE server_presence.observed_at < EXCLUDED.observed_at
                   RETURNING bridge_sub""",
                (p.sub, body.session_id, body.observed_at, body.online, body.since, body.version,
                 Jsonb([player.model_dump() for player in body.players] if body.online else []))).fetchone()
        return {"accepted": row is not None}

    @app.get("/status")
    def status():
        with DB().tx() as c:
            presence = c.execute(
                """SELECT *, online AND observed_at > clock_timestamp() - make_interval(secs => %s)
                          AS fresh FROM server_presence ORDER BY observed_at DESC LIMIT 1""",
                (s.status_stale_secs if s.status_stale_secs > 0 else 90,)).fetchone()
            last = c.execute("SELECT max(at) AS at FROM events").fetchone()["at"]
            slots = c.execute(
                """SELECT sl.n, sl.pinned, ch.name, ch.deployed_at IS NOT NULL AS deployed
                     FROM slots sl LEFT JOIN characters ch ON ch.id = sl.character_id ORDER BY sl.n""").fetchall()
            queue = c.execute(f"SELECT count(*) AS n FROM jobs WHERE state IN {IN_PROGRESS}").fetchone()["n"]
        online = bool(presence and presence["fresh"])
        players = presence["players"] if online else []
        return {"online": online, "players": players, "player_count": len(players),
                "version": presence["version"] if presence else None,
                "since": presence["since"] if presence else None,
                "last_heartbeat_at": presence["observed_at"] if presence else None,
                "last_event_at": last, "slots": slots, "jobs_in_progress": queue,
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
        cid, jid = uuid.uuid4(), uuid.uuid4()
        keys = [f"photos/{jid}/{i}.jpg" for i in range(len(raws))]
        # Commit the intent BEFORE any object write, including writes whose DB transaction fails.
        with DB().tx() as c:
            c.execute("SELECT sgl_enqueue_cleanup(%s)", (jid,))
        writing_started = False
        try:
            with DB().tx() as c:
                c.execute("SELECT pg_advisory_xact_lock(hashtext('sgl_create'))")
                c.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (f"sgl_storage:{jid}",))
                active = c.execute(f"SELECT count(*) AS n FROM characters WHERE owner_sub = %s AND state IN {IN_PROGRESS}",
                                   (p.sub,)).fetchone()["n"]
                if active >= s.limit_user_active:
                    raise HTTPException(429, "you already have a gator in the oven: wait for it to finish")
                total = c.execute("SELECT count(*) AS n FROM characters WHERE owner_sub = %s AND state <> 'failed'",
                                  (p.sub,)).fetchone()["n"]
                if total >= s.limit_user_total:
                    raise HTTPException(429, f"you already have {total} gators: delete one to make another")
                hour = c.execute("SELECT count(*) AS n FROM generation_admissions "
                                 "WHERE created > now() - interval '1 hour'").fetchone()
                if hour["n"] >= s.limit_global_hour:
                    raise HTTPException(429, "the gator kitchen is at capacity this hour: try again soon",
                                        headers={"Retry-After": "600"})
                c.execute("DELETE FROM generation_admissions WHERE created < now() - interval '1 day'")
                c.execute("INSERT INTO generation_admissions (job_id) VALUES (%s)", (jid,))
                # Admission and quotas precede CPU-heavy decompression. The lock
                # also prevents concurrent requests from oversubscribing limits.
                try:
                    with ThreadPoolExecutor(max_workers=len(raws)) as ex:
                        cleaned = list(ex.map(lambda r: images.process(r[1], s.photo_max_side), raws))
                except images.PhotoError as e:
                    raise HTTPException(422, str(e)) from e
                for k, data in zip(keys, cleaned):
                    writing_started = True  # even a failed response may have stored the object
                    ST().put(k, data, "image/jpeg")
                c.execute("INSERT INTO characters (id, owner_sub, name, state, step) VALUES (%s, %s, %s, 'queued', 'queued')",
                          (cid, p.sub, clean_name))
                c.execute("INSERT INTO jobs (id, character_id, state, step, photos) VALUES (%s, %s, 'queued', 'queued', %s)",
                          (jid, cid, keys))
        except BaseException:
            try:
                if writing_started:
                    state["cleaner"].drain(max_items=2, job_id=jid)
                else:
                    with DB().tx() as c:
                        c.execute("DELETE FROM storage_cleanup WHERE job_id = %s", (jid,))
            except Exception:
                log.exception("photo cleanup deferred for %s", jid)
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
            c.execute("SELECT pg_advisory_xact_lock(hashtext('sgl_slots'))")
            ch = c.execute("SELECT id, owner_sub FROM characters WHERE id = %s FOR UPDATE", (character_id,)).fetchone()
            if not ch or (ch["owner_sub"] != p.sub and not is_admin):
                raise HTTPException(404, "no such character")
            freed = c.execute("SELECT sgl_release_slot(%s) AS n", (character_id,)).fetchone()["n"]
            jobs = [r["id"] for r in c.execute("SELECT id FROM jobs WHERE character_id = %s", (character_id,))]
            c.execute("DELETE FROM characters WHERE id = %s", (character_id,))
        for jid in jobs:
            try:
                state["cleaner"].drain(max_items=2, job_id=jid)
            except Exception:
                log.exception("object cleanup deferred for %s", jid)
        return {"deleted": character_id, "freed_slot": freed}

    @app.post("/account/identity")
    async def identity_account(body: IdentityProof, request: Request, p: Annotated[Principal, Depends(user())]):
        from . import identities
        if body.user_id.startswith('anon-'):
            raise AuthError(401, 'Field Board sign-in required')
        with DB().tx() as c:
            accounts.lock(c)
            accounts.require_active(c, p.sub, p.claims)
            identities.verify(c, s.deepspace_ingest_secret, await request.body(), request.headers,
                              bearer(request.headers.get('authorization')), body)
            existing = c.execute('SELECT sub, deepspace_user FROM identity_links WHERE sub = %s OR deepspace_user = %s',
                                 (p.sub, body.user_id)).fetchall()
            matched = any(r['sub'] == p.sub and r['deepspace_user'] == body.user_id for r in existing)
            if body.action == 'link':
                if existing and not matched:
                    raise HTTPException(409, 'One of these accounts is already linked. Unlink the existing pair first.')
                c.execute('INSERT INTO identity_links (sub, deepspace_user) VALUES (%s, %s) ON CONFLICT DO NOTHING',
                          (p.sub, body.user_id))
                matched = True
            elif body.action == 'unlink':
                c.execute('DELETE FROM identity_links WHERE sub = %s AND deepspace_user = %s', (p.sub, body.user_id))
                matched = False
            return {'linked': matched, 'conflict': bool(existing) and not matched and body.action == 'status'}

    @app.delete("/links")
    def unlink_account(p: Annotated[Principal, Depends(user())]):
        with DB().tx() as c:
            accounts.lock(c)
            accounts.require_active(c, p.sub, p.claims)
            c.execute("UPDATE links SET revoked_at = now() WHERE sub = %s AND revoked_at IS NULL", (p.sub,))
            c.execute("DELETE FROM link_codes WHERE sub = %s", (p.sub,))
        return {"unlinked": True}

    @app.delete("/account", status_code=202)
    def delete_account(body: AccountDelete, p: Annotated[Principal, Depends(principal)]):
        if p.is_m2m:
            raise AuthError(403, "user token required")
        if time.time() - accounts.issued_at(p.claims) > 300:
            raise AuthError(401, "sign in again before deleting your Gator account")
        with DB().tx() as c:
            removed = accounts.delete_account(c, p.sub, event_fields, p.claims)
        with board_lock:
            board_cache.clear()
        return {"deleted": True, "removed_runs": removed, "cleanup": "queued", "provider_accounts": "unchanged"}

    @app.post("/account/register")
    def register_again(request: Request):
        p = state["verifier"].verify(bearer(request.headers.get("authorization")))
        if p.is_m2m:
            raise AuthError(403, "user token required")
        with DB().tx() as c:
            accounts.lock(c)
            deleted = c.execute("SELECT deleted_before FROM deleted_accounts WHERE subject_hash = %s",
                                (accounts.subject_hash(p.sub),)).fetchone()
            if deleted and accounts.issued_at(p.claims) <= deleted["deleted_before"]:
                raise AuthError(401, "sign in again before registering a new Gator account")
            c.execute("UPDATE deleted_accounts SET reactivated = true WHERE subject_hash = %s", (accounts.subject_hash(p.sub),))
        upsert_user(p)
        return {"registered": True}

    @app.post("/link-codes", status_code=201)
    def link_code(p: Annotated[Principal, Depends(user())]):
        with DB().tx() as c:
            accounts.lock(c)
            accounts.require_active(c, p.sub, p.claims)
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

    @app.post("/links/check")
    def check_links(body: LinkCheck, p: Annotated[Principal, Depends(scoped(SCOPE_BRIDGE))]):
        with DB().tx() as c:
            rows = c.execute("SELECT id FROM links WHERE id = ANY(%s) AND bridge_sub = %s AND revoked_at IS NULL",
                             (body.ids, p.sub)).fetchall()
        return {"active": [row["id"] for row in rows]}

    @app.post("/links")
    def create_link(body: LinkIn, _p: Annotated[Principal, Depends(scoped(SCOPE_BRIDGE))]):
        with DB().tx() as c:
            accounts.lock(c)
            if body.sub:
                accounts.require_active(c, body.sub)
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
            link_id = c.execute(
                """INSERT INTO links (sub, coopdx_name, gi, via, session_id, connection_id, bridge_sub)
                   VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                (sub, body.coopdx_name, body.gi, via, body.session_id, body.connection_id, _p.sub)).fetchone()["id"]
            u = c.execute("SELECT nickname, email_uf FROM users WHERE sub = %s", (sub,)).fetchone()
            g = c.execute(
                """SELECT slot, name FROM characters WHERE owner_sub = %s AND slot IS NOT NULL AND state = 'ready'
                   AND deployed_at IS NOT NULL ORDER BY deployed_at DESC LIMIT 1""", (sub,)).fetchone()
        return {"link_id": link_id, "sub": sub, "via": via, "nickname": (u and u["nickname"]) or body.coopdx_name,
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
            accounts.lock(c)
            for e in evs:
                e = accounts.normalize_event(e)
                fields = event_fields(e)
                event_key = session_id = occurred_at = None
                if fields.get("event_id") is not None:
                    try:
                        event_key = uuid.UUID(str(fields["event_id"]))
                        session_id = uuid.UUID(str(fields["session_id"]))
                        if fields.get("at"):
                            occurred_at = datetime.fromisoformat(fields["at"].replace('Z', '+00:00'))
                            if occurred_at.tzinfo is None:
                                raise ValueError('timestamp needs timezone')
                    except (ValueError, KeyError, TypeError, AttributeError) as error:
                        raise HTTPException(422, 'invalid event identity or timestamp') from error
                if accounts.erased_event(c, fields, _p.sub):
                    continue  # acknowledge deletion tombstones without recreating private history
                ev = c.execute(
                    """INSERT INTO events (t, payload, event_key, bridge_sub, session_id, occurred_at)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       ON CONFLICT (bridge_sub, event_key) DO NOTHING RETURNING id""",
                    (e["t"][:32], Jsonb(e), event_key, _p.sub, session_id, occurred_at)).fetchone()
                if ev is None:
                    prior = c.execute('SELECT id, payload FROM events WHERE bridge_sub = %s AND event_key = %s',
                                      (_p.sub, event_key)).fetchone()
                    if accounts.normalize_event(prior['payload']) != e:
                        raise HTTPException(409, 'event_id was already used for another payload')
                    if e['t'] == 'run':
                        stored_runs.extend(c.execute(
                            'SELECT id, mission, ranked, reason FROM runs WHERE event_id = %s', (prior['id'],)).fetchall())
                    continue
                if e["t"] == "run":   # §10.1: always stored, ranked only when valid and fully linked
                    stored_runs.append(runs.store(c, event_fields(e), ev["id"], bridge_sub=_p.sub))
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
                    WHERE d.state = 'pending' AND sgl_deploy_current(d.id) ORDER BY d.id""").fetchall()
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

    @app.post("/deploys/check")
    def deploy_check(body: DeployCheck, _p: Annotated[Principal, Depends(scoped(SCOPE_BRIDGE))]):
        with DB().tx() as c:
            c.execute("SELECT pg_advisory_xact_lock(hashtext('sgl_slots'))")
            ids = [r["id"] for r in c.execute(
                "SELECT id FROM deploys WHERE id = ANY(%s) AND state = 'pending' AND sgl_deploy_current(id)",
                (body.ids,))]
        return {"current": ids}

    @app.post("/deploys/reconcile")
    def deploy_reconcile(body: DeployInventory, _p: Annotated[Principal, Depends(scoped(SCOPE_BRIDGE))]):
        with DB().tx() as c:
            c.execute("SELECT pg_advisory_xact_lock(hashtext('sgl_slots'))")
            c.execute("UPDATE deploys SET state = 'superseded', finished = now() "
                      "WHERE state = 'pending' AND NOT sgl_deploy_current(id)")
            c.execute("SELECT sgl_sync_deploys()")
            for row in c.execute("SELECT n, character_id FROM slots ORDER BY n").fetchall():
                n = row["n"]
                latest = c.execute("SELECT id, state FROM deploys WHERE slot = %s ORDER BY id DESC LIMIT 1", (n,)).fetchone()
                if latest and latest["state"] == "pending":
                    continue
                installed = body.installed.get(n)
                if latest and latest["state"] == "deployed" and installed == latest["id"]:
                    continue
                if row["character_id"] is not None or installed is not None:
                    c.execute("UPDATE characters SET deployed_at = NULL WHERE id = %s", (row["character_id"],))
                    c.execute("SELECT sgl_queue_deploy(%s::smallint, %s, %s)",
                              (n, "character" if row["character_id"] else "placeholder", row["character_id"]))
        return {"ok": True}

    @app.post("/deploys/{deploy_id}")
    def deploy_result(deploy_id: int, body: DeployResult, _p: Annotated[Principal, Depends(scoped(SCOPE_BRIDGE))]):
        with DB().tx() as c:
            c.execute("SELECT pg_advisory_xact_lock(hashtext('sgl_slots'))")
            d = c.execute("SELECT * FROM deploys WHERE id = %s FOR UPDATE", (deploy_id,)).fetchone()
            if not d:
                raise HTTPException(404, "no such deploy")
            if not c.execute("SELECT sgl_deploy_current(%s) AS ok", (deploy_id,)).fetchone()["ok"]:
                raise HTTPException(409, "deploy no longer matches the current slot")
            if d["state"] == "deployed" and body.state == "deployed":
                return {"id": deploy_id, "state": "deployed"}
            if d["state"] != "pending":
                raise HTTPException(409, {"reason": d["state"], "message": f"deploy is {d['state']}, not pending"})
            c.execute("UPDATE deploys SET state = %s, error = %s, finished = now() WHERE id = %s",
                      (body.state, body.error, deploy_id))
            if body.state == "failed" and d["character_id"]:
                c.execute("UPDATE characters SET deployed_at = NULL WHERE id = %s", (d["character_id"],))
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
            c.execute("SELECT pg_advisory_xact_lock(hashtext('sgl_slots'))")
            c.execute("UPDATE slots SET pinned = %s WHERE n = %s", (body.pinned, n))
        return {"slot": n, "pinned": body.pinned}

    @app.post("/slots/{n}/redeploy", status_code=201)
    def force_deploy(n: int, _p: Annotated[Principal, Depends(scoped(SCOPE_ADMIN))]):
        with DB().tx() as c:
            c.execute("SELECT pg_advisory_xact_lock(hashtext('sgl_slots'))")
            sl = c.execute("SELECT sl.character_id, ch.state FROM slots sl LEFT JOIN characters ch ON ch.id = sl.character_id "
                           "WHERE sl.n = %s", (n,)).fetchone()
            if not sl:
                raise HTTPException(404, "no such slot")
            ready = sl["character_id"] and sl["state"] == "ready"
            d = c.execute("SELECT sgl_queue_deploy(%s::smallint, %s, %s) AS id",
                          (n, "character" if ready else "placeholder", sl["character_id"] if ready else None)).fetchone()
        return {"deploy_id": d["id"], "slot": n}

    return app

