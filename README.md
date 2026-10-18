# Super Gatorlator 64

**The University of Florida campus as a co-op Super Mario 64 game, with our friends — and you —
as playable characters.** Built for SwampHacks XII on [sm64coopdx](https://github.com/coop-deluxe/sm64coopdx),
the open-source PC port of SM64 with online co-op. Real UF buildings rebuilt at true 1:1 scale from
OpenStreetMap data; 10 real friends turned into low-poly N64-style characters from their photos; a
hub and 5 stages with 15 missions, solo and co-op.

The game runs natively (it needs your own SM64 ROM — see [`docs/development.md`](docs/development.md)),
but the character pipeline and accounts run entirely in the browser, so judges without a ROM can
still see the full result.

## SwampHacks XII sponsor tracks

| Track | What we're showing | Try it |
|---|---|---|
| **Best Use of Vultr** | A Cloud GPU job pipeline — photos in, playable N64 character out — deployed live to a game server we host (Cloud Compute, Managed PostgreSQL, Object Storage, Serverless Inference) | Upload photos on the dashboard below and watch the build |
| **Best Use of Auth0** | Logging in from *inside an N64 game* via the OAuth Device Authorization Flow (QR code + phone), plus Universal Login on the web and scoped API access | Type `/login` after connecting to the hosted server |
| **Best Domain Name from GoDaddy Registry** | `gatorcamp.us` (a GoDaddy Registry `.us` TLD) with subdomains routing the whole system — web, API, Auth0's custom login domain, and the game server | Visit [gatorcamp.us](https://gatorcamp.us) |

Full architecture and track-by-track detail: [`docs/web_platform_spec.md`](docs/web_platform_spec.md).

## See it in two minutes

**In a browser, no ROM needed:**
1. Open the [Gator Field Board dashboard](https://gator-field-board-mlh.app.space) and sign in with Gator Pass (Auth0).
2. Upload 1–4 photos on **Gatorize Me**. Watch the pipeline run live: a Vultr Cloud GPU job reads the
   photos, builds a 3D character in Blender, and you get an interactive preview you can rotate — same
   model the game will use.

**In the game (expo laptops, or your own sm64coopdx + ROM):**
1. **Join → Direct Connect → `play.gatorcamp.us`, port `7777`.** The mod downloads automatically — no
   repo or install needed.
2. Type **`/login`**. A QR code appears; scan it, approve on your phone, and you're linked — gold `*`
   on your name tag, and your Gatorize Me character selected for you if you made one.

## What's in the game

- **10 playable friends**, each built from 1–4 photos: hand-drawn pixel-art faces (8 eye states + a
  mouth), a signature outfit, and every one of Mario's original moves.
- **A hub (Plaza of the Americas) and 5 stages**, true to UF's real scale: The Swamp (Ben Hill Griffin
  Stadium), Reitz Union + Engineering (an 8-floor enterable interior), Lake Alice, Marston Science
  Library (a full interior from real floor plans), Library West After Dark.
- **15 missions**, two solo and one co-op per stage — races, climbs, a rhythm minigame, crane
  operators who carry riders, stealth past patrolling librarians, a dusk bat census, nighttime
  hide-and-seek.
- **Albert and Alberta**, two roaming alligator mascots who answer game questions instantly from a
  written guide, and anything else via Gemini, in character.
- **Campus rivals**: every Goomba wears a USF Bull or FSU Seminole, and Library West's ghosts are UCF
  Knights.

Full writeup, the build-time numbers, and how it was built with Claude Code's multi-agent workflows:
[`docs/project_overview.md`](docs/project_overview.md).

## How the online side fits together

```
                 gatorcamp.us (.us, GoDaddy Registry)
   www. ─────────┐   api. ─────┐   login. ──── Auth0 custom domain   play. ─── A record, UDP 7777
                 ▼             ▼                                      ▼
  Browser ──► web (static) ─► api (FastAPI) ◄──► Postgres (Vultr Managed)
                                 │   ▲                ▲
                     signed URLs │   │ job status     │ claim jobs
                                 ▼   │                │
                          Object Storage ◄──── gpu-worker (Vultr Cloud GPU)
                                 │                     VLM → Blender build/export/validate
                                 ▼  (artifacts pulled on deploy)
   game-host (Vultr Cloud Compute): sm64coopdx --headless, piped through a Python bridge
                                    that runs the Auth0 device flow and applies deploys
```

Full diagram, every deployable, and the database schema: [`docs/web_platform_spec.md`](docs/web_platform_spec.md).

## Repo layout

- `mods/sgl64/` — the game mod (Lua, character models, levels, textures).
- `tools/` — everything that builds the mod offline: campus generation from OpenStreetMap, the
  photo→character Blender pipeline, the NPC guide, and the offline test harness.
- `server/` — the online side: `api/` (FastAPI + Postgres), `worker/` (the Vultr GPU character
  pipeline), `bridge/` (the headless game host + Auth0 device flow), `web/` (the static site),
  `deploy/` (provisioning, systemd, Caddy).
- `companion/app/` — the Gator Field Board dashboard (squad coordination, leaderboards, the Gatorize
  Me web upload flow).
- `docs/` — design and spec documents; start with `project_overview.md` and `web_platform_spec.md`.

Full file-by-file breakdown: [`docs/development.md`](docs/development.md) → Layout.

## Run it yourself / contribute

macOS setup, installing the mod locally, configuring NPC chat (Gemini), and the full manual test
script live in [`docs/development.md`](docs/development.md).

## Credits

Map data © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors (ODbL), which
requires attribution. Built on [sm64coopdx](https://github.com/coop-deluxe/sm64coopdx), the
[coopdx character template](https://github.com/coop-deluxe/character-template), [Fast64](https://github.com/Fast-64/fast64)
and [Fast64-Gart](https://github.com/ManIsCat2/Fast64-Gart). This project requires your own SM64 ROM
and does not distribute Nintendo assets.
