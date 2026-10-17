# Web platform: Gatorize Me, Gator Pass, hosted server

The online side of Super Gatorlator 64: a hosted game server, photo-to-character builds and accounts
linked inside the game. Built for the SwampHacks XII sponsor tracks **Best Use of Vultr**,
**Best Use of Auth0** and **Best Domain Name from GoDaddy Registry**. Code: `server/` and the
web-facing files in `mods/sgl64/` (§9).

## 1. Goal

Anyone can turn their photos into a playable N64-style gator and play it on our hosted
Super Gatorlator 64 server, with their account linked inside the game:

1. Open **gatorcamp.us**, log in (Auth0).
2. Upload 1-4 photos. A Vultr GPU job turns them into a character: spec → face → Blender build →
   export → validate → preview render. The page shows live progress and the 3D preview render.
3. The character goes into a guest slot on the hosted server, which reloads.
4. In the game, `/login` shows a QR code + device code. Scan it, approve on your phone, and you are
   linked and verified: your guest character is selected for you and your name tag gets a star.

Judges without an SM64 ROM still see the full result in the browser (step 2's preview); the team
plays step 4 on the expo laptops.

## 2. Track mapping

| Track | What we show | Products / features |
|---|---|---|
| Vultr | GPU job pipeline that produces game assets, deployed live to a game server we host | Cloud GPU, Cloud Compute, Managed PostgreSQL, Object Storage, VPC, Firewall, Serverless Inference (vision model) |
| Auth0 | Login from inside an N64 game (device flow), accounts that own characters, API scopes | Device Authorization Flow, Universal Login on a custom domain, social connections, a post-login Action, API access tokens, M2M |
| GoDaddy | gatorcamp.us (.us, a GoDaddy Registry TLD); subdomains route the whole system (www, api, login, play) | gatorcamp.us, DNS records |

## 3. Architecture

```
                 gatorcamp.us (.us, GoDaddy Registry)
   www. ─────────┐   api. ─────┐   login. ──── Auth0 custom domain   play. ─── A record, UDP 7777
                 ▼             ▼                                      ▼
  Browser ──► web (static) ─► api (FastAPI) ◄──► Postgres (Vultr Managed)
                                 │   ▲                ▲
                     signed URLs │   │ job status     │ claim jobs (SKIP LOCKED)
                                 ▼   │                │
                          Object Storage ◄──── gpu-worker (Vultr Cloud GPU)
                          (photos, builds,       VLM → character.json → sgl_face_gen →
                           previews, actors)     Blender build/export/validate → previews
                                 │
                                 ▼  (artifacts pulled on deploy)
   game-host (Vultr Cloud Compute) ─────────────────────────────────────────────
     sm64coopdx --headless --server 7777 --enable-mod sgl64 --savepath /srv/sgl
         │ stdout: "SGLEVT {json}"                ▲ sav/sgl64.modfs (inbox, mod_fs_reload)
         ▼                                        │
     bridge (Python) ──────────────────────────────┘ ── api (M2M token): device flow, linking,
                                                        guest roster, deploys
```

Four deployables in `server/` (Python 3.12+, like `tools/`):

| Dir | Runs on | Purpose |
|---|---|---|
| `server/api/` | Cloud Compute (with the game host for the demo; separate VM optional) | FastAPI: auth, uploads, jobs, guest roster, link codes |
| `server/worker/` | Cloud GPU | Claims build jobs, runs the character pipeline |
| `server/bridge/` | game host | Pipes the game's stdout, writes the modfs inbox, runs the Auth0 device flow, applies deploys |
| `server/web/` | static, served by Caddy on the API VM | Upload page, job progress, gallery, `/activate` helper, `/tv` expo view |
| `server/deploy/` | — | Caddyfile, systemd units, `provision.sh` / `provision_gpu.sh`, `vultr.py` + `create_managed.sh` (Vultr API), env examples |

Mod changes live in `mods/sgl64/` as usual (§7).

## 4. Domain and DNS (GoDaddy)

**gatorcamp.us** (.us is a GoDaddy Registry TLD; registered at Porkbun, nameservers at Porkbun).
The API, website and Caddyfile take the domain from one setting, `SGL_DOMAIN`.

| Record | Points to | Use |
|---|---|---|
| `@`, `www` | API VM | Website |
| `api` | API VM | REST API |
| `login` | Auth0 CNAME | Universal Login on our domain (Auth0 custom domain, 1 free) |
| `play` | game host A | `play.gatorcamp.us:7777` in coopdx Direct Connect |
| CAA (optional) | `letsencrypt.org` | Caddy's certificates only |

## 5. Gatorize Me (Vultr)

### 5.1 Job pipeline

States: `queued → spec → face → build → export → validate → preview → ready` (or `failed` with the
step and a log tail). Each step writes its state to Postgres; the web page polls `GET /jobs/{id}`
every 2 s (SSE later if wanted). `jobs.state` and `characters.state` take the same values and the
worker writes them together. `step` uses the same names plus `store` (the upload, under state
`preview`); it is `ready` on success and the failing step on failure. The exact SQL is the worker
contract in the header of `server/api/schema.sql`.

1. **Upload.** `POST /characters` (scope `create:character`) takes a display name (≤ 12 chars,
   printable ASCII, profanity-filtered), a consent checkbox, and 1-4 photos (JPEG/PNG, ≤ 8 MB each,
   EXIF stripped, longest side resized to 1024). Photos go to Object Storage under
   `photos/<job>/`; the job row is created `queued`.
2. **Spec (AI).** The worker sends the photos to a vision model with a strict JSON schema and gets
   a `character.json` (same format as `art/daniel/character.json`). The schema enums are the
   pipeline's real options, generated from the code so they can't drift:
   - `build.hair_style` ∈ keys of `sgl_heads.HAIR_STYLES` (6 today)
   - `build.accessories` ⊆ the **implemented** entries of `sgl_body.ACCESSORIES`
     (`shirt_collar`, `rolled_cuffs`, `hood_down`, `crossbody_strap`; `_todo` stubs excluded)
   - `build.sleeves` ∈ {long, short}, `build.legwear` ∈ {long_pants, shorts}
   - `colors.*` as `#RRGGBB`; `signature_traits` and `outfit` free text (≤ 200 chars each)

   Validation: schema check, then clamp/repair (unknown enum → default, bad hex → sampled colour).
   Colours are cross-checked against k-means samples from the photos (face crop for skin, top
   crop for hair) and replaced when the model's value is far off. `id` is assigned by the server,
   never by the model: every job builds under the neutral actor id **`sglguest`** (the slot is only
   known once the API slots the ready character, and may change on re-deploy); the deploy renames
   the export to `guest_<slot>` with `server/worker/actor_rename.py` (Fast64 derives every symbol
   from the id, see `server/worker/README.md`).
   Model: any OpenAI-compatible endpoint with image input (`VLM_BASE_URL`, `VLM_MODEL`): Vultr
   Serverless Inference (e.g. `qwen3.8-flash-next`, which takes images), or a local vLLM on the
   GPU (`docker compose --profile vllm`). Without a model the worker falls back to photo colours
   and defaults.
3. **Face.** `SGL_ART_DIR=<job>/art python3 tools/blender/sgl_face_gen.py sglguest
   <job>/art/sglguest/textures`: the existing procedural eyes (8 states) and mouth from the spec.
   No new AI here.
4. **Build + export + validate.** `BLENDER=<linux blender> tools/blender/run_blender.sh
   tools/blender/build_character.py -- sglguest --art-dir <job>/art --build-dir <job>/build
   --actors-dir <job>/actors`, then `validate_export.py` (also on a copy renamed to `guest_8`). No
   per-character module in `tools/blender/characters/` (optional there). Hard timeout 10 min.
5. **Preview.** The builder's previews (`<job>/build/previews/`) plus a 64×64 portrait from the
   head/front preview for the character-select card (deployed as `sgl_portrait_guest_<slot>.png`).
6. **Store.** Previews, `portrait.png`, `character.json`, `manifest.json` and the
   `actors/sglguest/` export are
   uploaded to `builds/<job>/`. Photos are **deleted** when the job ends (success or failure).
7. **Ready.** In one transaction the worker writes `jobs.artifacts` (the stored object keys:
   `build_id`, `prefix`, `manifest`, `character_json`, `portrait`, `previews[]`, `actor_dir`,
   `files[]`) and `characters.spec`, marks both rows `ready`, and calls `sgl_assign_slot()`
   (§5.2). If the owner deletes the character mid-job, the worker's next UPDATE affects 0 rows.
   The worker then stops and deletes `photos/<job>/` and `builds/<job>/`.

The worker claims jobs with `SELECT … FOR UPDATE SKIP LOCKED` (one Blender at a time per GPU VM;
more VMs scale horizontally). No separate queue service.

### 5.2 Guest slots

DynOS compiles actors when the mod loads, so a new character needs a mod reload. To keep that
bounded and the Lua static:

- The mod ships **8 guest slots**, `guest_1` … `guest_8`, each with a placeholder actor (a copy of
  `actors/donald`, the plainest friend, with every `donald_` symbol renamed `guest_<n>_` and grey hair)
  and a placeholder portrait (a "?" gator card with the slot number), so the mod always loads.
- A deploy overwrites `actors/guest_<n>/` and `textures/sgl_portrait_guest_<n>.png` in the server's
  installed mod and rewrites `mods/sgl64/guests.lua` (generated, display names + owner ids).
- Slot assignment happens **only when a character is ready**, never at claim, so a live gator is
  never evicted for a build that might fail. The worker calls `sgl_assign_slot()` in its ready
  transaction, and `sgl_sync_deploys()` (run on every `GET /deploys/pending`) slots any ready,
  never-evicted character that still has none. The rule is free slot first, else the least
  recently played unpinned slot whose character is finished. Pinned slots (team demo characters)
  are never evicted. An evicted character keeps its row (`evicted_at`) and is not re-slotted
  automatically.
  - Symbols: every build exports as the neutral actor `sglguest`; the deploy renames it to
    `guest_<n>` (`server/worker/actor_rename.py`), so the root GeoLayout is `guest_<n>_geo` (DynOS compiles `actors/guest_<n>/` into `guest_<n>_geo.bin`, which
    `smlua_model_util_get_id("guest_<n>_geo")` loads). Check with
    `tools/blender/validate_export.py actors/guest_<n> guest_<n>`.
  - Portrait: clients only download `textures/*.tex`, which DynOS generates on the host from a `.png`
    that is newer than its `.tex` (`dynos_bin_tex.cpp`), so a freshly written `.png` is enough. Safer:
    the deploy also writes `sgl_portrait_guest_<n>.tex` itself (u8 `2`, u8 name length, the name, s32
    PNG size little endian, the PNG bytes; the committed portraits are exactly this).
  - `guests.lua` format: one call, one line per slot, slots 1..8 in order. `characters.lua` defines
    `sgl_guests_register` and loads first (coopdx loads a mod's files in strcmp order:
    `characters` < `charselect` < `guests`), so the file keeps its name and the guests are in the
    friend list before any hook runs. Names: ≤ 12 printable ASCII characters (the mod strips colour
    codes and anything else); `owner` is the Auth0 `sub` or `nil`.
    ```lua
    sgl_guests_register({
        { slot = 1, name = "Guest 1", owner = nil },
        { slot = 2, name = "Alice", owner = "google-oauth2|1234" },
        -- ... through slot = 8
    })
    ```
- Size: the compiled mod must stay under coopdx's 35 MB download cap (`MAX_MOD_SIZE`, compiled
  `.bin/.lvl/.tex`). Measured on the server with all 8 placeholders: 11.6 MB (each guest actor
  compiles to about 40 KB).

### 5.3 Deploy to the server

The bridge polls `GET /deploys/pending` (M2M). Each pending deploy is
`{id, slot, kind, character_id, job_id, name, owner, owner_sub, created, actor, build_id, prefix,
files[], artifacts}` plus a top-level `roster` of all 8 slots. For `kind: "character"`:
`actor` = `guest_<slot>`, `build_id` = `sglguest`, `prefix` = `builds/<job>/`, and `files[]` =
`{path, url}`, with presigned GET URLs and paths relative to `prefix`:
`actors/sglguest/geo.inc.c`, `actors/sglguest/geo_header.h`, `actors/sglguest/model.inc.c`,
`character.json`, `manifest.json`, `portrait.png`. The list comes from `jobs.artifacts`, falling
back to `manifest.json`. For `kind: "placeholder"` (slot freed), `files` is empty: restore the
shipped placeholder for `guest_<slot>`. When a build is `ready` and slotted:
1. download the files, rename the actor with `server/worker/actor_rename.py
   actors/sglguest <mod>/actors guest_<slot>`, copy `portrait.png` to
   `<mod>/textures/sgl_portrait_guest_<slot>.png`, regenerate `guests.lua`;
2. if players are online, announce "New gator <name> arrives in 60 s: the server will restart"
   via the inbox (§6.3), wait 60 s (or until empty);
3. stop the game (the bridge's child process), swap the staged files in, start it again; clients
   rejoin and download the changed mod;
4. report `deployed` to the API (`POST /deploys/{id}` `{"state": "deployed"}`, or `"failed"` with
   an `error`). Deploys are batched: at most one restart per 5 min.

## 6. Hosted server + bridge (Vultr)

### 6.1 Game host

- Vultr Cloud Compute (dedicated CPU) in Atlanta, Debian 13, 2 vCPU / 8 GB: headless coopdx uses
  about a core and about 3 GB once the levels are compiled. The API, Caddy and the bridge share
  the VM. Firewall (Vultr group + ufw): UDP 7777, TCP 80/443, TCP 22. The GPU worker and the
  managed Postgres sit on the same VPC (MTU 1450).
- coopdx v1.5.1 Linux release (it has `--headless`) plus SDL2/GL runtime libs (`provision.sh`).
  `sgl-bridge.service` runs the bridge, which launches `sm64coopdx --headless --server 7777
  --enable-mod sgl64 --savepath /srv/sgl --playername Campus --no-discord --skip-update-check` as
  its child. `sgl-game.service` runs the game alone, without the bridge.
- **ROM:** a team member's own `baserom.us.z64`, copied by hand to `/srv/sgl/` with mode 600.
  Never in the repo, an image, Object Storage or a backup.

### 6.2 Game → bridge (events)

The mod prints one line per event to stdout: `SGLEVT {"t":"...", ...}` (a small JSON encoder in
`sgl_bridge.lua`). Only the headless host prints (`network_is_server()` and
`gServerSettings.headlessServer`); clients relay to the host's local index
(`network_local_index_from_global(0)`). `server/bridge/README.md` has the exact fields.

| `t` | Fields | From |
|---|---|---|
| `hello` | version, proto | host, on load |
| `join` / `leave` | gi, name | host hooks |
| `login_req` | gi, name | `/login` on a client → host |
| `link_req` | gi, name, code | `/link <code>` on a client → host (fallback, §7.2) |
| `login_cancel` | gi | a waiting login closed on a client |
| `char` | gi, name, friend (id, e.g. `guest_3`), index | character pick changes |
| `fin` | gi, name, race, frames, level, act | race finish |
| `run` | see §10.1 | a mission round succeeded (verified leaderboards) |
| `exit` | code | added by the bridge when the game process ends |

### 6.3 Bridge → game (inbox)

The bridge writes `sav/sgl64.modfs` (a zip; write a temp file, then rename). The mod calls
`mod_fs_reload()` every 30 frames, reads `inbox.json`, and acts on commands with a sequence number
higher than the last one it handled:

| Command | Effect |
|---|---|
| `login_code {gi, user_code, uri, page, expires}` | Sent to that player only: QR + code on their HUD |
| `verified {gi, name, nickname, guest_slot?, uf?, resend?}` | Broadcast: star name tag; if the user owns a slot, select it on that client. Re-sent with `resend` to late joiners (marks only) |
| `login_failed {gi, reason}` | To that player: expired / denied / invalid_token / bad_code / unavailable / error |
| `announce {text, secs}` | Popup for everyone (deploy warnings) |

The modfs archive is a plain zip with an optional `properties.json` (format checked against
coopdx v1.5.1's `mod_fs.cpp`; `server/bridge/README.md` lists what is verified).

### 6.4 Bridge process

Python, one process, owns the game process: reads stdout lines, parses `SGLEVT`, forwards events to
the API with an M2M token, runs the device flow (§7.1) for `login_req`, writes the inbox, applies
deploys (§5.3). Restarts the game if it exits. Logs everything else from the game's stdout to the
journal.

## 7. Auth0 (Gator Pass)

### 7.1 Login from inside the game (device flow)

Auth0 application **"Gator Pass"**: type Native, token endpoint auth None, Device Code grant on.

1. Player types `/login`. Client sends `login_req` to the host; host prints it.
2. Bridge `POST https://login.gatorcamp.us/oauth/device/code` (client_id, scope
   `openid profile email`, audience `https://api.gatorcamp.us`).
3. Inbox `login_code` → the player's HUD: QR of `verification_uri_complete`, plus
   "login.gatorcamp.us/activate  ABCD-EFGH". QR drawn with `djui_hud_render_rect` from a
   pure-Lua encoder (speedata/luaqrcode, BSD-3-Clause, vendored as `sgl_qr.lua`; EC level M,
   version 4 for the usual 55-character URI).
4. Bridge polls `/oauth/token` at the returned interval (`authorization_pending`, `slow_down`,
   `expired_token`, `access_denied`).
5. On success: validate the ID token (issuer, audience, exp, JWKS), then `POST /links` to the API
   with `{sub, coopdx name, gi}`. The API returns the user's nickname and owned guest slot, and the
   bridge sends `verified`.

The link lives for the session on the host (keyed by global index + name); it is re-asked after a
reconnect. Social logins: Google, GitHub, Discord. **Each needs our own OAuth client ID/secret**
(Auth0's dev keys don't work with the device flow). Passwordless email code as the fallback.

### 7.2 Fallback: link from the web

If the device-flow UI is a problem on some client, the website shows a 6-character code after
login (`POST /link-codes`) and the player types `/link K7Q2XF`. Same result, no QR.

### 7.3 Web login and the API

- The website uses Universal Login (Authorization Code + PKCE) on `login.gatorcamp.us`.
- API audience `https://api.gatorcamp.us`, scopes `create:character`, `read:own`,
  `admin:slots`, `bridge`. The bridge uses an M2M application with only `bridge`.
- Post-login Action: adds `https://gatorcamp.us/uf: true` when the verified email ends in
  `@ufl.edu` (a "Gator" badge on the site and in game; nothing gated on it), and rate-limit
  metadata.
- Roles: `admin` (team) gets `admin:slots`, which allows pinning slots, deleting characters and
  forcing a deploy.

### 7.4 Limits

- Free plan: 25k MAU, unlimited social connections, 1 custom domain, Actions. New tenants get a
  22-day trial of paid features.
- One character in progress per user, 3 per user total, 20 jobs per hour overall (GPU budget).

## 8. API (FastAPI)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/characters` | `create:character` | Upload photos + name, creates a job |
| GET | `/jobs/{id}` | owner | State, step, log tail, preview URLs |
| GET | `/characters` | public | Gallery: ready characters (name, previews, slot, deployed?) |
| DELETE | `/characters/{id}` | owner or admin | Delete, free its slot |
| POST | `/link-codes` | user | §7.2 code |
| POST | `/links` | `bridge` | Device-flow or code link from the bridge |
| POST | `/events` | `bridge` | Game events (stored; future leaderboard) |
| GET | `/deploys/pending` | `bridge` | Builds waiting for the server |
| POST | `/deploys/{id}` | `bridge` | Mark deployed / failed |
| GET | `/status` | public | Server online, players, version (for `/tv`) |

Postgres tables (`server/api/schema.sql` is the source of truth): `users(sub, nickname,
email_uf)`, `characters(id, owner_sub, name, slot, state, step, spec jsonb, created, deployed_at,
evicted_at)`, `jobs(id, character_id, state, step, log, error, photos text[], artifacts jsonb,
attempts, created, started, finished, worker)`, `slots(n, character_id, pinned, last_played,
assigned_at)`, `links(sub, coopdx_name, gi, via, linked_at)`, `link_codes(code, sub, expires_at,
used_at)`, `events(id, t, payload jsonb, at)`, `deploys(id, slot, kind, character_id, job_id,
state, error)`.

`GET /jobs/{id}` returns `state`, `step`, `step_index` (position in `pipeline`; `store` counts as
`preview`), `log`, `error`, `slot`, `deployed`, and presigned `previews[]` (`{name, url}` for
`builds/<job>/previews/*.png`) and `portrait` (`builds/<job>/portrait.png`). `POST /events`
accepts the bridge's `{t, payload, at}` with the fields repeated at the top level (top level wins).

Object Storage: private bucket; the API hands out short-lived presigned GET URLs for previews.

## 9. Mod changes (`mods/sgl64/`)

| File | Change |
|---|---|
| `sgl_bridge.lua` (new) | JSON encode, `SGLEVT` printing on the host, client→host relay, inbox polling via `mod_fs_reload()` |
| `sgl_qr.lua` (new) | Vendored QR encoder (`sgl_qr_encode`) + a HUD draw helper (`sgl_qr_draw`) |
| `sgl_login.lua` (new) | `/login [cancel]`, `/link <code>`; QR/code panel (B closes it); verified marks: a gold `*` before the name tag (`HOOK_ON_NAMETAGS_RENDER`), "GATOR PASS" as the player-list description, `*` on the charselect name-tag pills; selects the owned guest slot |
| `guests.lua` (generated) | Guest slot names/owners as one `sgl_guests_register({...})` call (§5.2); checked in with 8 placeholders |
| `characters.lua` | Defines `sgl_guests_register`: appends the guest slots to `FRIENDS` (ids `guest_<n>`, models `guest_<n>_geo`) |
| `charselect.lua` | Pages of 10 cards: page 2 "GUEST GATORS"; L / R turn the page, D-pad left / right run across pages |
| `actors/guest_1..8/`, `textures/sgl_portrait_guest_*.png` + `.tex` | Placeholders |

All network-facing behaviour is inert offline: without a headless host nothing prints and the inbox
never appears. `tools/luatest` gets tests for the JSON encoder, inbox sequencing and the guest list
(`test_bridge.lua`: events and inbox; `test_qr.lua`: the QR encoder against known vectors;
`test_login.lua`: guest slots, charselect pages and `sgl_login.lua` against the real bridge).

## 10. Verified leaderboards

Leaderboard times come from the hosted server, never from a file on a player's machine. The mission
`id` from each `sgl_mission_register` definition (e.g. `swamp_sprint`, `reitz_rooftop`) is the key
everywhere: the mod, the API, the DeepSpace app (`companion/app/src/data/mission-catalog.json`).

### 10.1 Game → API: the `run` event

When a mission round ends in success with every player still in the act, the headless host prints

| `t` | Fields |
|---|---|
| `run` | `mission`, `frames` (host-measured: the host's clock from the round going active to success), `client_frames` (the leader's own count, for a sanity check), `retries`, `level`, `act`, `players` (count), then `gi1`, `name1`, `gi2`, `name2`, … (flattened: event fields stay primitives) |

The host measures time itself from the mission state it already receives; a client can only shift a
result by its network delay. The API rejects a run whose `frames` and `client_frames` differ by more
than 2 s, or that beats the mission's floor (`par`/gold-derived minimum in the API's mission table).

### 10.2 API

- `runs(id, mission, frames, client_frames, retries, players, subs text[], names text[], coop,
  created)`. A run is **ranked** when every player in it is linked (Gator Pass, §7); others are
  stored but shown as unverified.
- `GET /leaderboards` (public): `{missions: [{mission, title, rows: [{rank, names, frames}]}]}`,
  top 5 per mission, best run per player set. `GET /leaderboards/{mission}?limit=` (public, ≤ 50).
- Each ranked run is pushed to the DeepSpace app (§10.4).

### 10.3 Bridge → game: the `leaderboard` inbox command

The bridge fetches `GET /leaderboards` at start, every 60 s and after each accepted `run`, and
broadcasts one command per mission whose rows changed (and to each joining player):

| Command | Fields |
|---|---|
| `leaderboard` | `mission`, `n` (rows), `name1`, `frames1`, … `name5`, `frames5`, `at` (Unix time) |

The in-game leaderboard menu (`sgl_deepspace.lua`) shows these rows; offline it falls back to the
`.sav` snapshot the macOS helper writes. The solo outbox moves to its own ModFS file name so it never
shares a write with the inbox (`inbox.json` stays the bridge's).

### 10.4 DeepSpace app

The Gator Field Board is the web display: the API calls a server-only action (`ingestVerifiedRun`,
authenticated with a shared HMAC secret, not a user session) for each ranked run. The public
`submitGameRun` action no longer feeds the leaderboard: runs it receives are kept as unverified
"offline" runs and listed separately.

## 11. Not built

A live spectator map and crowd voting (DeepSpace realtime). The bridge's event stream (§6.2) is
where they would plug in.

## 12. Risks

- **ROM on the server**: own dump only, private, documented as such; judges can't join without one.
- **Device flow**: phishable by design; codes expire in 15 min, the page shows the requesting
  player's coopdx name.
- **Client trust**: in-game badges can be spoofed by a modified client; the API is the source of
  truth for links and ownership.
- **Photos of people**: consent checkbox, photos deleted after the build, characters deletable by
  their owner, admin delete for anything inappropriate.
- **Restart on deploy** interrupts play: batched, announced, skipped while a mission is running if
  possible.
- **Pipeline flakiness**: Fast64's SceneProperties upgrade crashed Blender (every load on Linux);
  `sgl_blender.setup_fast64` works around it, and `run_blender.sh` still retries crashes.
  Untested hair presets may look rough; the prompt can bias the model toward the reviewed presets.
