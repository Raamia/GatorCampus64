-- Super Gatorlator 64 web platform: Postgres schema (docs/web_platform_spec.md §8).
--
-- SINGLE SOURCE OF TRUTH for the api (server/api), the gpu worker (server/worker) and, through
-- the api, the bridge (server/bridge). Idempotent: safe to run on every API start
-- (`python -m sgl_api.schema` or SGL_APPLY_SCHEMA=1). Postgres >= 13 (gen_random_uuid built in).
-- Adding a column later: append an `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` at the bottom.
--
-- ── Job / character states ─────────────────────────────────────────────────────────────────────
-- jobs.state and characters.state use the same set. The worker writes both in one transaction
-- at every step, so characters.state always mirrors its job's state:
--   queued    created by POST /characters, photos are in Object Storage (jobs.photos)
--   spec      worker: vision model → character.json         ┐
--   face      worker: sgl_face_gen.py sglguest               │ "in progress"
--   build     worker: build_character.py                     │ (the worker moves through these
--   export    worker: Fast64 export                          │  in order)
--   validate  worker: validate_export.py (also renamed)      │
--   preview   worker: previews + 64x64 portrait + upload     ┘
--   ready     worker: artifacts are in builds/<job_id>/ (terminal, success)
--   failed    worker: `step` = the step that failed, jobs.log = log tail (terminal)
-- jobs.step / characters.step take the same names plus `store` (the upload, a sub-step of state
-- `preview`). While running: the current step. On success: 'ready'. On failure: the step that
-- failed (never 'failed').
--
-- ── Worker contract (server/worker/db.py implements it) ────────────────────────────────────────
-- Every job builds under the neutral actor id `sglguest`, and the worker never reads or writes a
-- slot. Slots are handed out only when a character is ready, so a live gator is never evicted for
-- a build that might fail. The bridge renames sglguest → guest_<slot> when it deploys.
--   Claim (one transaction):
--     SELECT j.id, j.character_id, j.photos, c.name FROM jobs j JOIN characters c ON c.id = j.character_id
--      WHERE j.state = 'queued' ORDER BY j.created LIMIT 1 FOR UPDATE OF c SKIP LOCKED;
--     UPDATE jobs SET state='spec', step='spec', started=now(), finished=NULL, worker=<host>,
--            log='', error=NULL, attempts=attempts+1 WHERE id=<job_id>;
--     UPDATE characters SET state='spec', step='spec' WHERE id=<character_id>;
--   Each claim also sets a new lease_token UUID and a lease_expires_at (120 seconds).
--   Renew every 30 seconds on a separate connection. All progress/terminal writes must
--   check matching character/token, active state and unexpired lease AFTER taking row locks.
--   Pollers fail expired claims from all hosts; they never requeue a job or reuse its keys.
--   Photos: download exactly the keys in jobs.photos (photos/<job_id>/<i>.jpg).
--   Each step: lock character FOR UPDATE, then UPDATE jobs and characters together.
--   Ready/failed: take pg_advisory_xact_lock(hashtext('sgl_slots')), then lock character,
--     then update job/character. Deletion uses the same advisory -> character -> job order.
--   Ready (one transaction):
--     UPDATE jobs SET state='ready', step='ready', log=<tail>, error=NULL, finished=now(), artifacts=<below>;
--     UPDATE characters SET state='ready', step='ready', spec=<character.json>;
--     SELECT sgl_assign_slot(<character_id>);    -- slot + pending deploy, or NULL when every slot is
--                                                -- pinned/busy: sgl_sync_deploys() retries on each bridge poll
--   jobs.artifacts (object keys, all under builds/<job_id>/):
--     {"build_id": "sglguest", "prefix": "builds/<job>/", "manifest": ".../manifest.json",
--      "character_json": ".../character.json", "portrait": ".../portrait.png",
--      "previews": [".../previews/front.png", ...], "actor_dir": ".../actors/sglguest/",
--      "files": [every stored key, manifest.json and log.txt included]}
--   Failed: jobs state='failed', step=<failing step>, log=<tail>, error=<one line>, finished=now();
--     characters state='failed', step=<failing step>; SELECT sgl_release_slot(<character_id>).
--   Always delete photos/<job_id>/ when the job ends.
--   The character (and its job, via ON DELETE CASCADE) may be deleted by its owner at any time.
--   An UPDATE of the job that affects 0 rows means "abort this job": stop, then delete
--   photos/<job_id>/ and builds/<job_id>/.
--
-- ── Object Storage layout (private bucket) ─────────────────────────────────────────────────────
--   photos/<job_id>/<i>.jpg                         EXIF-stripped, longest side ≤ 1024 (api)
--   builds/<job_id>/manifest.json                   build index (worker)
--   builds/<job_id>/character.json                  spec, "id": "sglguest" (worker)
--   builds/<job_id>/build_report.json, log.txt      (worker)
--   builds/<job_id>/previews/*.png                  builder previews: front, back, head, ... (worker)
--   builds/<job_id>/portrait.png                    64x64 character-select portrait (worker)
--   builds/<job_id>/face_sheet.png                  face texture sheet (worker)
--   builds/<job_id>/actors/sglguest/{geo_header.h,geo.inc.c,model.inc.c}   DynOS actor export (worker)
--   Deploy (bridge): server/worker/actor_rename.py actors/sglguest → <mod>/actors/guest_<slot>,
--   portrait.png → <mod>/textures/sgl_portrait_guest_<slot>.png.
--
-- ── Deploy states (deploys.state) ──────────────────────────────────────────────────────────────
--   pending     waiting for the bridge (GET /deploys/pending)
--   deployed    bridge applied it and restarted the game (POST /deploys/{id} {"state":"deployed"})
--   failed      bridge could not apply it (POST /deploys/{id} {"state":"failed","error":...})
--   superseded  a newer deploy for the same slot replaced it before the bridge applied it
--   deploys.kind: 'character' (write that character's artifacts into guest_<slot>) or
--                 'placeholder' (restore the shipped placeholder actor/portrait for guest_<slot>)

CREATE TABLE IF NOT EXISTS users (
    sub         text PRIMARY KEY,                       -- Auth0 subject, e.g. "google-oauth2|123"
    nickname    text,
    email_uf    boolean NOT NULL DEFAULT false,         -- claim https://gatorcamp.us/uf (AUTH0_CLAIM_NAMESPACE)
    created     timestamptz NOT NULL DEFAULT now(),
    last_seen   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS characters (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_sub   text NOT NULL REFERENCES users(sub) ON DELETE CASCADE,
    name        text NOT NULL CHECK (char_length(name) BETWEEN 1 AND 12),
    slot        smallint CHECK (slot BETWEEN 1 AND 8),  -- mirror of slots.n (kept in sync by the functions below)
    state       text NOT NULL DEFAULT 'queued' CHECK (state IN
                  ('queued','spec','face','build','export','validate','preview','ready','failed')),
    step        text CONSTRAINT characters_step_check CHECK (step IN          -- current / failing step
                  ('queued','spec','face','build','export','validate','preview','store','ready')),
    spec        jsonb,                                  -- character.json once known
    created     timestamptz NOT NULL DEFAULT now(),
    deployed_at timestamptz,                            -- last successful deploy into its slot; NULL = not on the server
    evicted_at  timestamptz                             -- lost its slot to a newer character (never auto re-slotted)
);
CREATE INDEX IF NOT EXISTS characters_owner_idx ON characters (owner_sub);
CREATE INDEX IF NOT EXISTS characters_state_idx ON characters (state);

CREATE TABLE IF NOT EXISTS jobs (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id uuid NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    state        text NOT NULL DEFAULT 'queued' CHECK (state IN
                   ('queued','spec','face','build','export','validate','preview','ready','failed')),
    step         text CONSTRAINT jobs_step_check CHECK (step IN               -- current / failing step
                   ('queued','spec','face','build','export','validate','preview','store','ready')),
    log          text,                                 -- log tail (worker keeps it ≤ ~8 KB)
    error        text,                                  -- one-line failure reason
    photos       text[] NOT NULL DEFAULT '{}',          -- object keys under photos/<id>/
    artifacts    jsonb,                                 -- see worker contract above
    attempts     integer NOT NULL DEFAULT 0,
    created      timestamptz NOT NULL DEFAULT now(),
    started      timestamptz,
    finished     timestamptz,
    worker       text                                   -- hostname of the claiming worker
);
CREATE INDEX IF NOT EXISTS jobs_queued_idx ON jobs (created) WHERE state = 'queued';
CREATE INDEX IF NOT EXISTS jobs_character_idx ON jobs (character_id);
CREATE INDEX IF NOT EXISTS jobs_created_idx ON jobs (created);

-- Admission history is independent of deletable jobs. No user/photo data or FK.
CREATE TABLE IF NOT EXISTS generation_admissions (
    job_id uuid PRIMARY KEY,
    created timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS generation_admissions_created_idx ON generation_admissions (created);
INSERT INTO generation_admissions (job_id, created)
    SELECT id, created FROM jobs WHERE created > now() - interval '1 day'
    ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS slots (
    n            smallint PRIMARY KEY CHECK (n BETWEEN 1 AND 8),   -- guest_<n>
    character_id uuid UNIQUE REFERENCES characters(id) ON DELETE SET NULL,
    pinned       boolean NOT NULL DEFAULT false,        -- team demo characters, never evicted
    last_played  timestamptz,                           -- bumped by `char` events picking guest_<n>
    assigned_at  timestamptz
);
INSERT INTO slots (n) SELECT generate_series(1, 8) ON CONFLICT (n) DO NOTHING;

CREATE TABLE IF NOT EXISTS links (
    id          bigserial PRIMARY KEY,
    sub         text NOT NULL REFERENCES users(sub) ON DELETE CASCADE,
    coopdx_name text NOT NULL,
    gi          smallint NOT NULL,                      -- coopdx global player index (session-scoped)
    via         text NOT NULL CHECK (via IN ('device','code')),
    linked_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS links_sub_idx ON links (sub, linked_at DESC);
CREATE INDEX IF NOT EXISTS links_player_idx ON links (gi, coopdx_name, linked_at DESC);   -- run → sub (§10.2)

CREATE TABLE IF NOT EXISTS link_codes (
    code        text PRIMARY KEY CHECK (code ~ '^[A-Z0-9]{6}$'),   -- §7.2, alphabet without 0/O/1/I
    sub         text NOT NULL REFERENCES users(sub) ON DELETE CASCADE,
    created     timestamptz NOT NULL DEFAULT now(),
    expires_at  timestamptz NOT NULL,                   -- created + 10 min
    used_at     timestamptz                             -- single use
);

CREATE TABLE IF NOT EXISTS events (
    id          bigserial PRIMARY KEY,
    t           text NOT NULL,                          -- hello, join, leave, login_req, link_req, char, fin, run, exit
    payload     jsonb NOT NULL,                         -- the full SGLEVT object
    at          timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS events_t_at_idx ON events (t, at DESC);
CREATE INDEX IF NOT EXISTS events_at_idx ON events (at DESC);

CREATE TABLE IF NOT EXISTS deploys (
    id           bigserial PRIMARY KEY,
    slot         smallint NOT NULL CHECK (slot BETWEEN 1 AND 8),
    kind         text NOT NULL CHECK (kind IN ('character','placeholder')),
    character_id uuid REFERENCES characters(id) ON DELETE SET NULL,
    job_id       uuid REFERENCES jobs(id) ON DELETE SET NULL,      -- artifacts are under builds/<job_id>/
    state        text NOT NULL DEFAULT 'pending' CHECK (state IN ('pending','deployed','failed','superseded')),
    error        text,
    created      timestamptz NOT NULL DEFAULT now(),
    finished     timestamptz
);
CREATE INDEX IF NOT EXISTS deploys_pending_idx ON deploys (created) WHERE state = 'pending';

-- ── Verified leaderboards (§10) ────────────────────────────────────────────────────────────────
-- One row per `run` event (POST /events). Every run is stored; only ranked runs reach a board.
--   ranked = validation passes AND every player has an exact bridge-captured link bound to
--            its session/connection and authenticated bridge subject. Legacy events without
--            these references are unranked. Receipt order is not an identity boundary.
--            reason is NULL exactly when ranked.
--   reason (not ranked): unknown_mission, bad_fields, out_of_range, below_floor (faster than the
--            mission's floor, sgl_api/missions.py), clock_mismatch (|frames - client_frames| > 60),
--            player_count (players != number of gi/name pairs), duplicate_player (one account twice),
--            unlinked (valid, but someone was not logged in: shown nowhere, kept for the record).
--   player_key = the sorted subs joined by ' ' (ranked runs): boards keep the best run per key.
-- run_pushes is the outbox to the DeepSpace app (§10.4): one row per ranked run, drained by the API
-- (sgl_api/deepspace.py) with exponential backoff; 'failed' after DEEPSPACE_PUSH_MAX_ATTEMPTS. To
-- retry those: UPDATE run_pushes SET state='pending', attempts=0, next_at=now() WHERE state='failed'.
CREATE TABLE IF NOT EXISTS runs (
    id            bigserial PRIMARY KEY,
    uid           uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),  -- runId sent to DeepSpace (idempotency key)
    mission       text NOT NULL,                        -- sgl_mission_register id, e.g. swamp_sprint
    frames        integer,                              -- host-measured, 30 fps (NULL only when unparsable)
    client_frames integer,                              -- the leader's own count (sanity check)
    retries       integer NOT NULL DEFAULT 0,
    players       smallint NOT NULL DEFAULT 0,
    gis           smallint[] NOT NULL DEFAULT '{}',      -- per player, in event order
    names         text[] NOT NULL DEFAULT '{}',          -- per player: coopdx name from the event
    subs          text[] NOT NULL DEFAULT '{}',          -- per player: linked Auth0 sub, or NULL
    coop          boolean NOT NULL DEFAULT false,       -- players > 1
    level         integer,
    act           integer,
    ranked        boolean NOT NULL DEFAULT false,
    reason        text CHECK ((reason IS NULL) = ranked),
    player_key    text CHECK (NOT ranked OR player_key IS NOT NULL),
    event_id      bigint REFERENCES events(id) ON DELETE SET NULL,
    created       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS runs_board_idx ON runs (mission, player_key, frames, created) WHERE ranked;
CREATE INDEX IF NOT EXISTS runs_created_idx ON runs (created DESC);

CREATE TABLE IF NOT EXISTS run_pushes (
    run_id      bigint PRIMARY KEY REFERENCES runs(id) ON DELETE CASCADE,
    state       text NOT NULL DEFAULT 'pending' CHECK (state IN ('pending','sent','failed')),
    attempts    integer NOT NULL DEFAULT 0,
    next_at     timestamptz NOT NULL DEFAULT now(),     -- also the claim lease while a push is in flight
    last_error  text,
    created     timestamptz NOT NULL DEFAULT now(),
    sent_at     timestamptz
);
CREATE INDEX IF NOT EXISTS run_pushes_due_idx ON run_pushes (next_at) WHERE state = 'pending';

-- ── Slot assignment (§5.2) ─────────────────────────────────────────────────────────────────────
-- All slot changes serialize on one transaction-scoped advisory lock, so the api and any number
-- of workers can call these concurrently. Callable from plain SQL: SELECT sgl_assign_slot(id).

-- Give a READY character a guest slot and queue its deploy: free slot first (lowest n), else the
-- least recently played unpinned slot whose character is finished (ready/failed). The evicted
-- character keeps its row (state ready, slot NULL, evicted_at set). Returns the slot, or NULL if
-- nothing can be evicted or the character is not ready (in-progress builds never hold a slot:
-- the worker calls this right after marking the character ready, and sgl_sync_deploys() catches
-- up on every bridge poll). If the character is already slotted, returns that slot.
CREATE OR REPLACE FUNCTION sgl_assign_slot(cid uuid) RETURNS smallint
LANGUAGE plpgsql AS $$
DECLARE
    s smallint;
    victim uuid;
    cstate text;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtext('sgl_slots'));
    SELECT slot, state INTO s, cstate FROM characters WHERE id = cid FOR UPDATE;
    IF NOT FOUND THEN
        RETURN NULL;
    END IF;
    IF s IS NOT NULL THEN
        RETURN s;
    END IF;
    IF cstate <> 'ready' THEN
        RETURN NULL;
    END IF;

    SELECT n INTO s FROM slots WHERE character_id IS NULL ORDER BY n LIMIT 1;
    IF s IS NULL THEN
        SELECT sl.n, sl.character_id INTO s, victim
          FROM slots sl JOIN characters c ON c.id = sl.character_id
         WHERE NOT sl.pinned AND c.state IN ('ready','failed') AND c.id <> cid
         ORDER BY sl.last_played ASC NULLS FIRST, sl.assigned_at ASC NULLS FIRST, sl.n
         LIMIT 1;
        IF s IS NULL THEN
            RETURN NULL;
        END IF;
        UPDATE characters SET slot = NULL, deployed_at = NULL, evicted_at = now() WHERE id = victim;
    END IF;

    UPDATE slots SET character_id = cid, assigned_at = now(), last_played = now() WHERE n = s;  -- grace: not evicted first
    UPDATE characters SET slot = s, evicted_at = NULL WHERE id = cid;
    PERFORM sgl_queue_deploy(s, 'character', cid);
    RETURN s;
END $$;

-- Free a character's slot (job failed, character deleted). With restore => true a placeholder
-- deploy is queued when the slot held something that is (or is about to be) on the server.
CREATE OR REPLACE FUNCTION sgl_release_slot(cid uuid, restore boolean DEFAULT true) RETURNS smallint
LANGUAGE plpgsql AS $$
DECLARE
    s smallint;
    was_deployed boolean;
    had_deploy boolean;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtext('sgl_slots'));
    SELECT n INTO s FROM slots WHERE character_id = cid;
    IF s IS NULL THEN
        RETURN NULL;
    END IF;
    SELECT deployed_at IS NOT NULL INTO was_deployed FROM characters WHERE id = cid;
    SELECT EXISTS (SELECT 1 FROM deploys WHERE slot = s AND character_id = cid
                    AND state IN ('pending','deployed')) INTO had_deploy;
    UPDATE slots SET character_id = NULL, assigned_at = NULL, last_played = NULL, pinned = false WHERE n = s;
    UPDATE characters SET slot = NULL, deployed_at = NULL WHERE id = cid;
    IF restore AND (coalesce(was_deployed, false) OR had_deploy) THEN
        PERFORM sgl_queue_deploy(s, 'placeholder', NULL);
    ELSE
        UPDATE deploys SET state = 'superseded', finished = now()
         WHERE slot = s AND state = 'pending' AND character_id = cid;
    END IF;
    RETURN s;
END $$;

-- Queue a deploy for a slot, superseding any older pending deploy of that slot.
CREATE OR REPLACE FUNCTION sgl_queue_deploy(s smallint, k text, cid uuid) RETURNS bigint
LANGUAGE plpgsql AS $$
DECLARE
    d bigint;
    jid uuid;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtext('sgl_slots'));
    UPDATE deploys SET state = 'superseded', finished = now() WHERE slot = s AND state = 'pending';
    IF cid IS NOT NULL THEN
        SELECT id INTO jid FROM jobs WHERE character_id = cid AND state = 'ready'
         ORDER BY finished DESC NULLS LAST, created DESC LIMIT 1;
    END IF;
    INSERT INTO deploys (slot, kind, character_id, job_id) VALUES (s, k, cid, jid) RETURNING id INTO d;
    RETURN d;
END $$;

-- Lazy reconciliation, called by GET /deploys/pending (the worker already calls
-- sgl_assign_slot when a character becomes ready; this catches the ones that found no slot
-- then): slot every ready, never-evicted, unslotted character (oldest first), and queue a
-- deploy for every ready slotted character that has no pending/deployed deploy for its slot.
CREATE OR REPLACE FUNCTION sgl_sync_deploys() RETURNS integer
LANGUAGE plpgsql AS $$
DECLARE
    r record;
    queued integer := 0;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtext('sgl_slots'));
    FOR r IN SELECT id FROM characters
              WHERE state = 'ready' AND slot IS NULL AND evicted_at IS NULL ORDER BY created LOOP
        IF sgl_assign_slot(r.id) IS NULL THEN
            EXIT;                                           -- every slot is pinned or busy
        END IF;
        queued := queued + 1;
    END LOOP;
    FOR r IN SELECT c.id, c.slot FROM characters c
              WHERE c.state = 'ready' AND c.slot IS NOT NULL
                AND NOT EXISTS (SELECT 1 FROM deploys d WHERE d.slot = c.slot AND d.character_id = c.id
                                   AND d.state IN ('pending','deployed')) LOOP
        PERFORM sgl_queue_deploy(r.slot, 'character', r.id);
        queued := queued + 1;
    END LOOP;
    RETURN queued;
END $$;

-- ── Migrations for databases created before a change above (idempotent) ───────────────────────
-- Session-bound login references, assigned by the bridge rather than game clients.
ALTER TABLE links ADD COLUMN IF NOT EXISTS session_id uuid;
ALTER TABLE links ADD COLUMN IF NOT EXISTS connection_id uuid;
ALTER TABLE links ADD COLUMN IF NOT EXISTS bridge_sub text;
ALTER TABLE events ADD COLUMN IF NOT EXISTS event_key uuid;
ALTER TABLE events ADD COLUMN IF NOT EXISTS bridge_sub text;
ALTER TABLE events ADD COLUMN IF NOT EXISTS session_id uuid;
ALTER TABLE events ADD COLUMN IF NOT EXISTS occurred_at timestamptz;
CREATE UNIQUE INDEX IF NOT EXISTS events_delivery_idx ON events (bridge_sub, event_key);

-- step check constraints: NOT VALID, so rows written by older builds don't block the upgrade.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'characters_step_check') THEN
        ALTER TABLE characters ADD CONSTRAINT characters_step_check CHECK (step IN
            ('queued','spec','face','build','export','validate','preview','store','ready')) NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'jobs_step_check') THEN
        ALTER TABLE jobs ADD CONSTRAINT jobs_step_check CHECK (step IN
            ('queued','spec','face','build','export','validate','preview','store','ready')) NOT VALID;
    END IF;
END $$;

-- Lease tokens fence every worker write; expired jobs fail rather than reuse photo/build keys.
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS lease_token uuid;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS lease_expires_at timestamptz;
CREATE INDEX IF NOT EXISTS jobs_lease_idx ON jobs (lease_expires_at)
    WHERE state NOT IN ('queued', 'ready', 'failed');

-- Ephemeral presence is separate from the durable event history.
CREATE TABLE IF NOT EXISTS server_presence (
    bridge_sub text PRIMARY KEY,
    session_id uuid NOT NULL,
    observed_at timestamptz NOT NULL,
    received_at timestamptz NOT NULL DEFAULT now(),
    online boolean NOT NULL,
    since timestamptz,
    version text,
    players jsonb NOT NULL DEFAULT '[]'
);

-- Durable cleanup intents outlive jobs and contain no account identifiers or photo data.
-- Successful rows remain as low-frequency tombstones to catch late writes by old processes.
CREATE TABLE IF NOT EXISTS storage_cleanup (
    job_id uuid NOT NULL,
    kind text NOT NULL CHECK (kind IN ('photos', 'builds')),
    next_at timestamptz NOT NULL DEFAULT now(),
    attempts integer NOT NULL DEFAULT 0,
    failures integer NOT NULL DEFAULT 0,
    last_error text,
    cleaned_at timestamptz,
    PRIMARY KEY (job_id, kind)
);
CREATE INDEX IF NOT EXISTS storage_cleanup_due_idx ON storage_cleanup (next_at);

CREATE OR REPLACE FUNCTION sgl_enqueue_cleanup(jid uuid) RETURNS void
LANGUAGE sql AS $$
    INSERT INTO storage_cleanup (job_id, kind) VALUES (jid, 'photos'), (jid, 'builds')
    ON CONFLICT (job_id, kind) DO UPDATE SET next_at = LEAST(storage_cleanup.next_at, now());
$$;

CREATE OR REPLACE FUNCTION sgl_cleanup_job_trigger() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        PERFORM sgl_enqueue_cleanup(OLD.id);
        RETURN OLD;
    END IF;
    PERFORM sgl_enqueue_cleanup(NEW.id);
    RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS jobs_cleanup_changed ON jobs;
CREATE TRIGGER jobs_cleanup_changed AFTER INSERT OR UPDATE OF state ON jobs
    FOR EACH ROW EXECUTE FUNCTION sgl_cleanup_job_trigger();
DROP TRIGGER IF EXISTS jobs_cleanup_deleted ON jobs;
CREATE TRIGGER jobs_cleanup_deleted BEFORE DELETE ON jobs
    FOR EACH ROW EXECUTE FUNCTION sgl_cleanup_job_trigger();
-- Backfill extant jobs; historical objects whose jobs were already deleted need a separate inventory.
INSERT INTO storage_cleanup (job_id, kind)
    SELECT j.id, k.kind FROM jobs j CROSS JOIN (VALUES ('photos'), ('builds')) k(kind)
    ON CONFLICT DO NOTHING;

-- The newest generation must still match the current slot and a ready build.
CREATE OR REPLACE FUNCTION sgl_deploy_current(did bigint) RETURNS boolean
LANGUAGE sql STABLE AS $$
    SELECT EXISTS (
        SELECT 1 FROM deploys d JOIN slots sl ON sl.n = d.slot
        LEFT JOIN characters c ON c.id = d.character_id LEFT JOIN jobs j ON j.id = d.job_id
        WHERE d.id = did AND d.state IN ('pending', 'deployed')
          AND NOT EXISTS (SELECT 1 FROM deploys newer WHERE newer.slot = d.slot AND newer.id > d.id)
          AND ((d.kind = 'placeholder' AND sl.character_id IS NULL)
            OR (d.kind = 'character' AND sl.character_id = d.character_id AND c.slot = d.slot
                AND c.state = 'ready' AND j.state = 'ready' AND j.character_id = c.id))
    );
$$;

-- Account lifecycle: revocation metadata survives removal of application data.
ALTER TABLE links ADD COLUMN IF NOT EXISTS revoked_at timestamptz;
CREATE TABLE IF NOT EXISTS deleted_accounts (
    subject_hash text PRIMARY KEY,
    deleted_before bigint NOT NULL,
    reactivated boolean NOT NULL DEFAULT false
);
CREATE TABLE IF NOT EXISTS erased_links (
    link_id bigint PRIMARY KEY,
    session_id uuid,
    connection_id uuid
);
CREATE TABLE IF NOT EXISTS erased_events (
    bridge_sub text NOT NULL,
    event_key uuid NOT NULL,
    PRIMARY KEY (bridge_sub, event_key)
);
CREATE TABLE IF NOT EXISTS run_erases (
    uid uuid PRIMARY KEY,
    attempts integer NOT NULL DEFAULT 0,
    next_at timestamptz NOT NULL DEFAULT now(),
    last_error text,
    sent_at timestamptz
);
CREATE INDEX IF NOT EXISTS run_erases_due_idx ON run_erases (next_at) WHERE sent_at IS NULL;
