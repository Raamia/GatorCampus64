# Web platform spec: Gatorize Me, Gator Pass, hosted server

Status: draft. Owner: networking / web (Adi).
Targets the SwampHacks XII sponsor tracks **Best Use of Vultr**, **Best Use of Auth0** and
**Best Domain Name from GoDaddy Registry**. DeepSpace is shelved (see §11).

## 1. Goal

Anyone can turn their photos into a playable N64-style gator and play it on our hosted
Super Gatorlator 64 server, with their account linked inside the game:

1. Open **chooseyourgator.select**, log in (Auth0).
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
| Vultr | GPU job pipeline that produces game assets, deployed live to a game server we host | Cloud GPU, Cloud Compute, Managed PostgreSQL, Object Storage, Firewall, (Serverless Inference if it has a vision model) |
| Auth0 | Login from inside an N64 game (device flow), accounts that own characters, API scopes | Device Authorization Flow, Universal Login on a custom domain, social connections, a post-login Action, API access tokens, M2M |
| GoDaddy | The TLD finishes the in-game menu title "CHOOSE YOUR GATOR!"; subdomains route the whole system | chooseyourgator.select + chompwith.us, DNS records |

## 3. Architecture

```
                 chooseyourgator.select (GoDaddy Registry, registered at Porkbun)
   www. ─────────┐ api. ─────┐ login. ──── Auth0 custom domain play. ─── A record, UDP 7777
                 ▼ ▼ ▼
  Browser ──► web (static) ─► api (FastAPI) ◄──► Postgres (Vultr Managed)
                                 │ ▲ ▲
                     signed URLs │ │ job status │ claim jobs (SKIP LOCKED)
                                 ▼ │ │
                          Object Storage ◄──── gpu-worker (Vultr Cloud GPU)
                          (photos, builds, VLM → character.json → sgl_face_gen →
                           previews, actors) Blender build/export/validate → previews
                                 │
                                 ▼ (artifacts pulled on deploy)
   game-host (Vultr Cloud Compute) ─────────────────────────────────────────────
     sm64coopdx --headless --server 7777 --enable-mod sgl64 --savepath /srv/sgl
         │ stdout: "SGLEVT {json}" ▲ sav/sgl64.modfs (inbox, mod_fs_reload)
         ▼ │
     bridge (Python) ──────────────────────────────┘ ── api (M2M token): device flow, linking,
                                                        guest roster, deploys
```

Four deployables, all in a new top-level `server/` directory (Python 3.12, matching `tools/`):

| Dir | Runs on | Purpose |
|---|---|---|
| `server/api/` | Cloud Compute (with the game host for the demo; separate VM optional) | FastAPI: auth, uploads, jobs, guest roster, link codes |
| `server/worker/` | Cloud GPU | Claims build jobs, runs the character pipeline |
| `server/bridge/` | game host | Pipes the game's stdout, writes the modfs inbox, runs the Auth0 device flow, applies deploys |
| `server/web/` | static, served by Caddy on the API VM | Upload page, job progress, gallery, `/activate` helper, `/tv` expo view |
| `server/deploy/` | — | Caddyfile, systemd units, `provision.sh`, `.env.example` |

Mod changes live in `mods/sgl64/` as usual (§7).

## 4. Domain and DNS (GoDaddy)

Claim through `mlh.link/GoDaddyRegistry` → Porkbun with the MLH code (free 1 year, premium names
refuse the code). Primary: **chooseyourgator.select**. Second teammate claims **chompwith.us**.
Fallbacks if refused: gatorlator.courses, herewegators.club. **Not.co** (no longer GoDaddy Registry).

| Record | Points to | Use |
|---|---|---|
| `@`, `www` | API VM | Website |
| `api` | API VM | REST API |
| `login` | Auth0 CNAME | Universal Login on our domain (Auth0 custom domain, 1 free) |
| `play` | game host A | `play.chooseyourgator.select:7777` in coopdx Direct Connect |
| `_sm64coopdx._udp.play` | SRV 0 0 7777 play | Server advertisement (documented; coopdx itself takes host:port) |
| `play` TXT | `sgl64=<mod version>; coopdx=v1.5.1` | Version check from `dig` |
| `chompwith.us/<code>` | 302 → `chooseyourgator.select/join/<code>` | Short invite links |
| CAA | `letsencrypt.org` | Caddy's certificates only |

## 5. Gatorize Me (Vultr)

### 5.1 Job pipeline

States: `queued → spec → face → build → export → validate → preview → ready` (or `failed` with the
step and a log tail). Each step writes its state to Postgres; the web page polls `GET /jobs/{id}`
every 2 s (SSE later if wanted).

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
   Model: Vultr Serverless Inference if it offers a vision model (keeps it all on Vultr); otherwise
   an open VLM (Qwen2.5-VL-7B class) served with vLLM on the same GPU. Decide in spike S3.
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

The worker claims jobs with `SELECT … FOR UPDATE SKIP LOCKED` (one Blender at a time per GPU VM;
more VMs scale horizontally). No separate queue service.

### 5.2 Guest slots

DynOS compiles actors when the mod loads, so a new character needs a mod reload. To keep that
bounded and the Lua static:

- The mod ships **8 guest slots**, `guest_1` … `guest_8`, each with a placeholder actor (a recoloured
  default gator) and a placeholder portrait, so the mod always loads.
- A deploy overwrites `actors/guest_<n>/` and `textures/sgl_portrait_guest_<n>.png` in the server's
  installed mod and rewrites `mods/sgl64/guests.lua` (generated, display names + owner ids).
- Slot assignment: free slot first, else the least recently played unpinned slot. Pinned slots
  (team demo characters) are never evicted.
- Size check before deploy: compiled mod must stay under coopdx's 35 MB download cap
  (`MAX_MOD_SIZE`, compiled `.bin/.lvl/.tex`). **Measure the current mod first** (spike S1).

### 5.3 Deploy to the server

The bridge polls `GET /deploys/pending` (M2M). When a build is `ready` and slotted:
1. download artifacts, write them into the installed mod, regenerate `guests.lua`;
2. if players are online, announce "New gator <name> arrives in 60 s: the server will restart"
   via the inbox (§6.3), wait 60 s (or until empty);
3. restart the `sgl-game` systemd unit; clients rejoin and download the changed mod;
4. report `deployed` to the API. Deploys are batched: at most one restart per 5 min.

## 6. Hosted server + bridge (Vultr)

### 6.1 Game host

- Vultr Cloud Compute, Miami or Atlanta, Ubuntu 24.04, 2 vCPU / 4 GB (headless coopdx uses about
  a core). Firewall group: UDP 7777, TCP 22 (team IPs), TCP 80/443 if the API shares the VM.
- coopdx v1.5.1 Linux build (release or built from source with the headless option) plus SDL2 and
  libGL runtime libs. `sm64coopdx --headless --server 7777 --enable-mod sgl64 --savepath
  /srv/sgl --playername "Campus" --no-discord --skip-update-check`, as the `sgl-game` systemd unit
  with `StandardOutput=` piped to the bridge (bridge launches the game as its child).
- **ROM:** a team member's own `baserom.us.z64`, copied by hand to `/srv/sgl/` with mode 600.
  Never in the repo, an image, Object Storage or a backup.

### 6.2 Game → bridge (events)

The mod prints one line per event to stdout: `SGLEVT {"t":"...",...}` (a small JSON encoder in
`sgl_bridge.lua`). Only the headless host prints (`network_is_server()`); clients send what the
host needs via `network_send_to(0, …)`. Events for this spec:

| `t` | Fields | From |
|---|---|---|
| `hello` | mod version | host, on load |
| `join` / `leave` | gi, name | host hooks |
| `login_req` | gi, name | `/login` on a client → host |
| `link_req` | gi, name, code | `/link <code>` on a client → host (fallback, §7.2) |
| `char` | gi, friend id | character pick changes |
| `fin` | gi, race, frames | existing race `fin` event (for the optional leaderboard, §10) |

### 6.3 Bridge → game (inbox)

The bridge writes `sav/sgl64.modfs` (a zip; write a temp file, then rename). The mod calls
`mod_fs_reload()` every 30 frames, reads `inbox.json`, and acts on commands with a sequence number
higher than the last one it handled:

| Command | Effect |
|---|---|
| `login_code {gi, user_code, uri, expires}` | Sent to that player only: QR + code on their HUD |
| `verified {gi, nickname, guest_slot?}` | Broadcast: star name tag; if the user owns a slot, select it on that client |
| `login_failed {gi, reason}` | To that player: expired / denied |
| `announce {text, secs}` | Popup for everyone (deploy warnings) |

The modfs file layout (`properties.json` optional) is the main unknown: spike S2 makes the mod
save a modfs once and copies its exact format.

### 6.4 Bridge process

Python, one process, owns the game process: reads stdout lines, parses `SGLEVT`, forwards events to
the API with an M2M token, runs the device flow (§7.1) for `login_req`, writes the inbox, applies
deploys (§5.3). Restarts the game if it exits. Logs everything else from the game's stdout to the
journal.

## 7. Auth0 (Gator Pass)

### 7.1 Login from inside the game (device flow)

Auth0 application **"Gator Pass"**: type Native, token endpoint auth None, Device Code grant on.

1. Player types `/login`. Client sends `login_req` to the host; host prints it.
2. Bridge `POSThttps://login.chooseyourgator.select/oauth/device/code` (client_id, scope
   `openid profile email`, audience `https://api.chooseyourgator.select`).
3. Inbox `login_code` → the player's HUD: QR of `verification_uri_complete`, plus
   "login.chooseyourgator.select/activate  ABCD-EFGH". QR drawn with `djui_hud_render_rect` from a
   pure-Lua encoder (speedata/luaqrcode, MIT, vendored as `sgl_qr.lua`).
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

- The website uses Universal Login (Authorization Code + PKCE) on `login.chooseyourgator.select`.
- API audience `https://api.chooseyourgator.select`, scopes `create:character`, `read:own`,
  `admin:slots`, `bridge`. The bridge uses an M2M application with only `bridge`.
- Post-login Action: adds `https://chooseyourgator.select/uf: true` when the verified email ends in
  `@ufl.edu` (a "Gator" badge on the site and in game; nothing gated on it), and rate-limit
  metadata.
- Roles: `admin` (team) gets `admin:slots`, which allows pinning slots, deleting characters and
  forcing a deploy.

### 7.4 Limits

- Free plan: 25k MAU, unlimited social connections, 1 custom domain, Actions. New tenants get a
  22-day trial of paid features. Create the tenant before the weekend's work starts.
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

Postgres tables: `users(sub, nickname, email_uf)`, `characters(id, owner_sub, name, slot, state,
step, spec jsonb, created, deployed_at)`, `jobs(id, character_id, state, step, log, started,
finished, worker)`, `slots(n, character_id, pinned, last_played)`, `links(sub, coopdx_name, gi,
linked_at)`, `events(id, t, payload jsonb, at)`.

Object Storage: private bucket; the API hands out short-lived presigned GET URLs for previews.

## 9. Mod changes (`mods/sgl64/`)

| File | Change |
|---|---|
| `sgl_bridge.lua` (new) | JSON encode, `SGLEVT` printing on the host, client→host relay, inbox polling via `mod_fs_reload()` |
| `sgl_qr.lua` (new) | Vendored QR encoder + a HUD draw helper |
| `sgl_login.lua` (new) | `/login`, `/link`; QR/code panel; verified name-tag star |
| `guests.lua` (generated) | Guest slot names/owners; checked in with 8 placeholders |
| `characters.lua` | Append the guest slots from `guests.lua` to `FRIENDS` |
| `charselect.lua` | A second page ("GUEST GATORS") when there are more than 10 cards |
| `actors/guest_1..8/`, `textures/sgl_portrait_guest_*.png` | Placeholders |

All network-facing behaviour is inert offline: without a headless host nothing prints and the inbox
never appears. `tools/luatest` gets tests for the JSON encoder, inbox sequencing and the guest list.

## 10. Optional: verified leaderboard

If the core is done: the host already sees each race's `fin`. Store it via `/events`, rank only
linked (`sub`) players, show the board on the site and `/tv`, and push the top 3 back through the
inbox for the results board. Same Auth0 + Vultr pieces; no new infrastructure.

## 11. Shelved

DeepSpace (live map, crowd voting, spectator realtime). The bridge's event stream (§6.2) is the
hook for it if we come back.

## 12. Spikes (do these first, each ≤ 1-2 h)

| # | Question | Pass when |
|---|---|---|
| S1 | Does headless coopdx v1.5.1 run our mod on a Linux VM, and how big is the compiled mod? | A laptop joins `play.…:7777`, sees the hub; compiled size noted vs the 35 MB cap |
| S2 | Can an outside process write `sgl64.modfs` and the mod read it after `mod_fs_reload()`? | A bridge-written `inbox.json` shows a popup in game |
| S3 | Vision model choice: Vultr Serverless Inference vision support, else vLLM on the GPU | Valid `character.json` from 3 test photos, schema-clean |
| S4 | Does the character pipeline run headless on Linux (Blender + Fast64-Gart + template from `tools/vendor/`)? | `build_character.py -- daniel` reproduces `mods/sgl64/actors/daniel/` (export validates) on the GPU VM |
| S5 | Does a client re-download the mod after the server's guest actors change? | Rejoin after a restart shows the new model |

## 13. Build order

1. Accounts: Vultr credits (mlh.link/vultr), Auth0 tenant, domain claim. DNS for `play`, `api`, `www`.
2. Spikes S1, S2, S4 in parallel; S3 and S5 next.
3. Game host + bridge (events out, inbox in), `sgl_bridge.lua`.
4. Gator Pass: device flow, `sgl_login.lua`, QR, verified star.
5. Worker + API + web upload/progress page; guest slots + deploy.
6. Expo polish: `/tv`, QR codes on a printed star, `chompwith.us` redirects, README section.
7. Optional leaderboard (§10).

## 14. Risks

- **ROM on the server**: own dump only, private, documented as such; judges can't join without one.
- **Device flow**: phishable by design; codes expire in 15 min, the page shows the requesting
  player's coopdx name.
- **Client trust**: in-game badges can be spoofed by a modified client; the API is the source of
  truth for links and ownership.
- **Photos of people**: consent checkbox, photos deleted after the build, characters deletable by
  their owner, admin delete for anything inappropriate.
- **Restart on deploy** interrupts play: batched, announced, skipped while a mission is running if
  possible.
- **Pipeline flakiness**: Blender's ~1-in-14 Fast64 segfault is retried by `run_blender.sh`.
  Untested hair presets may look rough; S3 can bias the model toward the reviewed presets.

## 15. Open questions

- Linux Blender version that matches the Fast64-Gart build in `tools/vendor/`.
- Vultr credit amount and GPU availability in Miami/Atlanta.
- Whether one project may claim prizes in several MLH tracks at this event (ask the MLH coach).
