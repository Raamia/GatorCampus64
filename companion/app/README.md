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

The local worker starts at `http://localhost:8780`. The website uses Gator Pass for account access. The legacy native bridge integration remains separate. Build, sign in to, and use the macOS bridge by following [`../native-bridge/README.md`](../native-bridge/README.md). The bridge can refresh leaderboard snapshots into the native game's local save; the SGL64 mod displays them from its Mods menu.

## Verified leaderboards (hosted server)

The board at `/leaderboard` reads public, server-ranked results directly from the game API's `GET /leaderboards` every 30 seconds. It no longer needs a Field Board session or RecordRoom connection. Existing signed ingestion into RecordRooms and the legacy native bridge APIs remain available; stored `solo_runs` are preserved but the retired offline board is no longer shown on the website.

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


## One website account: Gator Pass

All website Sign in and Sign up buttons use Auth0, matching the in-game Gator
Pass account. Signup passes `screen_hint=signup` to Universal Login. The existing
allowed `/gatorize` OAuth callback remains unchanged; the SDK validates it once
and returns visitors to their original local page (including `/settings`).
Public pages and anonymous Gatorize drafts remain accessible without login.

`/settings` now owns identity display, sign-out, revoking game logins, confirmed
account deletion, recent reauthentication, and explicit registration after
deletion. Gatorize links to Settings instead of embedding account management.
Deletion still uses the API's existing authorization and recent-login checks.
It deletes game data, not the Auth0 identity-provider account.

Field Board login, manual linking, the offline-run panel, and the unused scaffold
integration-debug page are retired from the website. Existing DeepSpace records,
identity mappings, ingestion, and erasure routes remain intact for legacy data;
accounts are never merged by email. Existing linked offline data remains subject
to the existing erasure flow. Unlinked historical Field Board accounts are not
silently attached to a Gator Pass account.

Mission hints use the same Gator Pass bearer as the game API. The worker resolves
its subject through the API's verified `/me` endpoint before admitting requests
under the existing durable per-user/global budgets. Invalid credentials, deleted
accounts, and verification outages fail closed; anonymous catalog hints still
work. No user credential is forwarded to the upstream study service.

This change requires a companion deployment only, after anonymous Gatorize PR #7.
No Auth0 callback allowlist change or database migration is introduced here.
