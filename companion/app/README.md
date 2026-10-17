# Gator Field Board

A DeepSpace backend for Super Gatorlator 64. The game remains native and authoritative; DeepSpace stores signed-in players' self-reported solo run results and serves mission leaderboards. The Lua mod currently saves completed runs to a local ModFS outbox. A macOS OAuth/sync bridge is still required before those local results reach DeepSpace; the game does not make network requests.

## Local setup

Use Node 24 and npm 11, then run:

```sh
npm install
npx deepspace auth whoami --json
npx deepspace dev start
```

The first DeepSpace CLI sign-in opens a browser and requires the account owner to accept DeepSpace's Terms of Service. No credentials belong in this repository. The scaffold uses the DeepSpace account's app namespace when the first app command registers the app. Keep the GitHub repository as the source of truth; do not run `npx deepspace push`.

The local worker starts at `http://localhost:8780`. Anonymous visitors can view a squad room. Signed-in DeepSpace members can append reports to its isolated record room. Squad codes are random 12-character invite codes stored locally and are not sent to the optional service.

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
