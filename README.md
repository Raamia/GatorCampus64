# Super Gatorlator 64

**The University of Florida, rebuilt as a co-op Super Mario 64 playground. Starring our friends—and you.**

Explore a campus at real-world scale, race through libraries, ride gators, and turn your photos into a playable N64-style character. Built for **SwampHacks XII**: five stages, 16 solo/co-op missions, a campus minimap, and Albert and Alberta as your guides.

**[Website](https://gatorcamp.us) · [Make your character](https://gatorcamp.us/gatorize) · [Character showcase](https://gatorcamp.us/showcase) · [Live leaderboard](https://gatorcamp.us/leaderboard)**

## Jump in

1. **Download [sm64coopdx v1.5.1](https://github.com/coop-deluxe/sm64coopdx/releases/tag/v1.5.1)** for your OS. Unzip, launch, and import a **US Super Mario 64 ROM (`.z64`)** when prompted.
2. **Join → Direct Connect:** enter **`play.gatorcamp.us`**, port **`7777`**. If DNS fails, use `64.177.55.205`. The server downloads the mod for you.
3. **Pick a character and explore.** Press **Enter** for chat; `/char` changes your character, `/campus marston` takes you straight to the library, and `/albert what can I do here?` gets you started.

**Keyboard:** WASD moves · L jumps · K crouches · arrow keys turn the camera · Space pauses. Controllers work too.

**Play as yourself:** upload 1–4 photos at [Gatorize Me](https://gatorcamp.us/gatorize). Once your character is built and deployed, type `/login` in-game and approve the QR/device code on your phone to link it. You can start playing with the existing cast while it builds.

**Just browsing?** The [showcase](https://gatorcamp.us/showcase) opens immediately, with 23 character studies and interactive 3D previews. No account or game installation needed.

## Under the hood

| What you see | What we built |
|---|---|
| **A playable UF campus** | OpenStreetMap and real floor plans become Blender/Fast64 levels, with custom Lua missions, co-op systems, and minimaps. [World & game design](docs/project_overview.md) |
| **Photos → playable characters** | Qwen vision selects structured appearance profiles; procedural Blender builders generate, rig, export, and validate the character. Our **AI** work includes schema repair, explicit failure handling, and [evaluations with documented limitations](docs/gatorize_likeness.md). |
| **Talking mascots · Gemini** | Guide retrieval answers known game questions directly and grounds related Gemini responses; open-ended conversation stays in character. [NPC bridge](tools/npc_bridge/bridge.py) |
| **Gator Pass · Auth0** | Browser login uses PKCE; in-game login uses the device flow. The API validates tokens, while the game bridge authenticates separately. [Authentication](server/api/sgl_api/auth.py) |
| **Live Field Board · DeepSpace** | SDK auth, SQLite-backed RecordRooms, permissions, and reactive queries power the companion. Signed server ingestion supplies verified leaderboard results. [Realtime queries](companion/app/src/pages/%28app%29/leaderboard.tsx) · [Ingestion](companion/app/src/server/ingest-routes.ts) |
| **The running system · Vultr** | Cloud Compute hosts the game/API; a Cloud GPU runs Qwen and Blender. Managed PostgreSQL, Object Storage, a private VPC, and Firewall complete the deployment. [Infrastructure](server/deploy/vultr.py) |
| **One address · GoDaddy Registry** | `gatorcamp.us` brings the website, API, and game together on the Registry's `.us` domain, registered through Porkbun. [Domain routing](docs/web_platform_spec.md#4-domain-and-dns-godaddy) |

## Build locally

[Game setup & controls](docs/development.md) · [API](server/api/README.md) · [GPU worker](server/worker/README.md) · [Architecture](docs/web_platform_spec.md)

Built on [sm64coopdx](https://github.com/coop-deluxe/sm64coopdx), [Fast64](https://github.com/Fast-64/fast64), and the [coopdx character template](https://github.com/coop-deluxe/character-template). Map data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), ODbL. ROMs are not included in this repository.
