# Study Group HQ UX Contract

## Business context

| Rule | Source | UI consequence |
|---|---|---|
| The game remains playable when the companion or a service is unavailable. | `../README.md`; `../docs/flow.md` | Every companion action is optional. Static mission hints remain available offline. |
| The Lua mod is authoritative for in-game state and has no supported outbound HTTP bridge in sm64coopdx v1.5.1. | `../tools/luatest/coopdx_api_v151.lua`; engine version recorded in `../docs/flow.md` | Submitted results are labeled player reported. |
| Verified leaderboard times come only from the hosted game server's API (`ingestVerifiedRun`, HMAC-signed; `../../docs/web_platform_spec.md` §10.4). | `src/server/ingest-routes.ts`, `src/schemas/verified-runs-schema.ts` | The Leaderboards page ranks only `verified_runs`. Runs from `submitGameRun` are shown below it as "Offline · unverified" (signed-in players only) and never ranked with it. |
| Only real mission definitions may be shown or recommended. | `src/data/mission-catalog.json`, checked against `../mods/sgl64/*_missions.lua` | IDs, title, and objective must match the Lua sources. |
| Do not send names or personal details to Gemini or analytics. | User-supplied SwampHacks terminal handoff | The optional service receives only mission ID or anonymized result fields; no account email or squad code. |

## Scope and access

- Creating and joining a squad uses a random 12-character code with a 32-symbol alphabet. The code is a bearer invite to that squad's isolated DeepSpace record room.
- Anonymous visitors may view a room but cannot write. Signed-in members can append events. The event collection does not allow updates or deletes.
- Squad codes stay in local component state and local storage; they are not placed in the URL or sent to Vultr, Gemini, or Tiger Data.
- Result records contain only mission ID, event kind, team size, elapsed seconds, retries, and a user-entered display nickname. The UI asks users not to enter personal information.

## Flow ledger

| Flow | Source | Behavior |
|---|---|---|
| Create squad | User action | Generate a code locally, connect to its room, then display the share code. |
| Join squad | User action | Normalize and validate the code, then mount that room and subscribe to its events. |
| Select mission | Game registry and catalog | Append a mission-selected event for the exact supported mission ID. |
| Ask dispatcher | Static catalog and optional service | Submit only the selected mission ID and authored hint. Validate returned ID and response type; otherwise show the static hint. |
| Record result | Player report | Save an append-only event to DeepSpace, then attempt the optional anonymized service mirror. A mirror failure leaves the board usable. |
| Leaderboards | `verified_runs` (public) and `solo_runs` (signed in) | Pick a mission; the verified board shows the best run per team (names, time, retries, co-op). Offline runs follow in a separate, labelled list. |
| Recap | DeepSpace records | Show the latest player-reported run and total. |

## Canonical UI ownership

- The page owns one responsive Study Group HQ shell and shared mission card component.
- Native text and number inputs own their platform behavior; no custom select or date picker is used.
- Inline banners own network/service errors. The scaffold's shared toast provider owns write acknowledgements that are not tied to a field.
- The squad room is the server-owned source of shared board state. Browser local storage only restores the current user's last joined code and nickname.

## Resilience

- Mission catalog and authored hints are local build assets.
- A DeepSpace disconnect keeps the last received board visible, disables writes while the room is unavailable, and offers a reconnect status.
- Gemini timeout, missing key, malformed JSON, or unsupported mission ID uses the authored hint.
- Vultr/Tiger Data outage does not undo a saved DeepSpace result and never blocks play.
- Empty states explain the next action. Loading UI reserves the final panel geometry.
