# Super Gatorlator 64 Companion

The web companion for Super Gatorlator 64, a native SM64CoopDX campus game. It supports squad mission planning, player-reported offline run logs, and verified leaderboards populated by the hosted game server. Offline scores remain separate from ranked runs. The Lua mod saves completed runs to a local ModFS outbox, and `companion/native-bridge/` provides a macOS OAuth/sync CLI that uploads them after the game closes. The game does not make network requests.

## Local setup

Use Node 24 and npm 11, then run:

```sh
npm install
npx deepspace auth whoami --json
npx deepspace dev start
```

The first DeepSpace CLI sign-in opens a browser and requires the account owner to accept DeepSpace's Terms of Service. No credentials belong in this repository. The scaffold uses the DeepSpace account's app namespace when the first app command registers the app. Keep the GitHub repository as the source of truth; do not run `npx deepspace push`.

The local worker starts at `http://localhost:8780`. The existing browser UI still contains an older squad-room prototype; it is separate from the native single-player game integration. Build, sign in to, and use the macOS bridge by following [`../native-bridge/README.md`](../native-bridge/README.md). The bridge can refresh leaderboard snapshots into the native game's local save; the SGL64 mod displays them from its Mods menu.

## Verified leaderboards (hosted server)

The board at `/leaderboard` ranks only **verified** runs (`docs/web_platform_spec.md` §10.4): runs timed by the hosted game server and pushed by its API (`server/api`) when every player was logged in with Gator Pass. The API calls `POST /api/actions/ingestVerifiedRun` (`src/server/ingest-routes.ts`), signed with a shared secret; it is not a user action and needs no DeepSpace account. Runs synced with `submitGameRun` (the macOS bridge) are self-reported: they stay in `solo_runs`, are listed under the verified board as "Offline · unverified" and are never ranked with it. `getGameLeaderboard` returns the verified board in `rows` and offline runs in `offlineRows`.

Turning it on (one shared random secret, e.g. `openssl rand -hex 32`):

1. App: `npx deepspace secrets set DEEPSPACE_INGEST_SECRET=<secret>`, then `npx deepspace deploy` (secrets apply at deploy). Without the secret the ingest route answers 503.
2. API (`/etc/sgl/api.env`): `DEEPSPACE_APP_URL=https://<app>.app.space` and `DEEPSPACE_INGEST_SECRET=<secret>`, then restart `sgl-api`. Ranked runs stored before that wait in the API's `run_pushes` outbox and are sent once it is configured.

## Optional sponsor service

The game works without a DeepSpace deployment. `src/server/study-routes.ts` proxies minimal mission hints, anonymized result mirrors, and aggregate requests when both service variables are configured:

- `VULTR_SERVICE_URL`: base URL of the separately hosted service
- `VULTR_SERVICE_TOKEN`: bearer token shared with that service

Set these only in DeepSpace's secret manager for the app. Do not commit `.dev.vars`, API keys, database URLs, or tokens. Without them the mission board uses its catalog hints and keeps results in DeepSpace.

Gemini and Tiger Data credentials belong only on the service host. The service should accept mission IDs for hint generation and anonymized event fields for reporting. Never forward squad codes, account identifiers, or names.

## Checks

```sh
npm run type-check
npm run build
python3 ../../tools/check_mission_catalog.py
```

The catalog checker compares the committed JSON catalog with the registered mission definitions in the game mod.
