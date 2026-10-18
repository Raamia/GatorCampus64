# GatorCampus 64 companion UX contract

## Business context

| Rule | Source | UI consequence |
|---|---|---|
| The game remains playable when the companion or a service is unavailable. | `../README.md`; `../docs/flow.md` | Every companion action is optional. Static mission hints remain available offline. |
| The Lua mod is authoritative for in-game state and has no supported outbound HTTP bridge in sm64coopdx v1.5.1. | `../tools/luatest/coopdx_api_v151.lua`; engine version recorded in `../docs/flow.md` | The companion never claims to record a result itself; it points players at the hosted server (verified) or the native companion's offline sync. |
| Verified leaderboard times come only from the hosted game server's API (`ingestVerifiedRun`, HMAC-signed; `../../docs/web_platform_spec.md` §10.4). | `src/server/ingest-routes.ts`, `src/schemas/verified-runs-schema.ts` | The Leaderboards page ranks only `verified_runs`. Runs from `submitGameRun` are shown below it as "Offline · unverified" (signed-in players only) and never ranked with it. |
| Only real mission definitions may be shown or recommended. | `src/data/mission-catalog.json`, checked against `../mods/sgl64/*_missions.lua` | IDs, title, and objective must match the Lua sources. |
| Do not send names or personal details to Gemini or analytics. | User-supplied SwampHacks terminal handoff | The optional study/dispatcher service receives only a mission ID; no account email, name, or free text. |
| The study dispatcher is a privileged upstream call, not a public write. | `docs/backend_assessment.md` finding 3; `src/server/study-routes.ts`, `src/lib/study-api.ts` | Only signed-in users may call it (`studyFetch` attaches the Gator Pass bearer token); it is budget-limited per user and globally, and falls back to the authored static hint on any failure, timeout, or exhausted budget. |

There is no squad feature: everyone plays on the one hosted server, so a separate squad-coordination layer was redundant and has been removed, along with the manual player-reported result form it carried. Results come from exactly two places: the hosted server's verified pipeline (Gator Pass `/login`), or the native companion's offline sync (`solo_runs`, unverified, signed-in only).

## Flow ledger

| Flow | Source | Behavior |
|---|---|---|
| Select mission | Game registry and catalog | Set the selected mission locally (component state only; no event is written) and call the dispatcher for a route hint. |
| Ask dispatcher | Static catalog and optional service | Submit only the selected mission ID. A signed-in call may receive a service-generated hint; an anonymous or budget-exhausted call always falls back to the authored static hint. Validate the returned shape before using it. |
| Leaderboards | `verified_runs` (public) and `solo_runs` (signed in) | Pick a mission; the verified board shows the best run per team (names, time, retries, co-op). Offline runs follow in a separate, labelled list. |

## Canonical UI ownership

- The home page owns one responsive mission-board shell and the shared mission card component; it holds no server-synced state of its own (selection and hint are local to the page).
- Native text and number inputs own their platform behavior; no custom select or date picker is used.
- Inline banners own network/service errors. The scaffold's shared toast provider owns write acknowledgements that are not tied to a field.

## Resilience

- Mission catalog and authored hints are local build assets.
- Gemini timeout, missing key, malformed JSON, an unsupported mission ID, a missing/expired auth token, or an exhausted study budget all fall back to the authored static hint; the mission board stays fully usable either way.
- A DeepSpace disconnect on the Leaderboards page keeps the last received board visible and offers a reconnect status.
- Empty states explain the next action. Loading UI reserves the final panel geometry.
