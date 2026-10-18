# Sponsor tracks and next backend work

Reviewed against `~/trimmed.pdf` (SwampHacks XII Hacker Guide,
printed pages 18–28), current main at the reviewed revision, and repository source. The PDF is
local input, not a committed asset. Estimates below are rough engineering time,
including focused checks, assuming access to any required provider account.
They are proposals, not implemented features or approved purchases.

## Where this project already fits

| Track | Evidence / strongest demo | Remaining requirement |
|---|---|---|
| Overall / Entertainment & Creative Technology | A playable co-op UF campus, original mission systems and personalized characters. | A reliable 2–3 minute presentation and a working game station. Overall considers every project; opt into additional tracks on Devpost. |
| Artificial Intelligence | Qwen structured appearance extraction, procedural geometry, validation/repair and likeness evaluations; guide-grounded Gemini NPC answers. | Public repo linked on Devpost with an explanatory README. Show evaluation results and failure cases. Do not describe procedural mesh presets as fine-tuned neural models. |
| DeepSpace | Real SDK auth, SQLite-backed RecordRoom collections, permissions, reactive leaderboard queries and signed server ingest. | The guide requires a live demo and explanation of SDK features, not hosting alone. Demonstrate an actual hosted result appearing in two browsers. |
| Best Use of Gemini API | In-character Albert/Alberta answers; guide retrieval supplies game context. | Demonstrate a real Gemini-backed response and distinguish it from direct guide or canned responses. Keep a fallback demo available. |
| Best Use of Vultr | Compute game/API host, Cloud GPU Qwen/Blender worker, Managed PostgreSQL and Object Storage. | Show the upload → job → preview → deployed guest path. Current documented inference uses GPU-hosted vLLM, not Vultr Serverless Inference. |
| GoDaddy Registry domain | `gatorcamp.us` uses the GoDaddy Registry `.us` TLD across web/API/game entry points. | Registration and DNS are at Porkbun. Confirm the guide's eligible registration requirement with organizers; do not claim registration through GoDaddy's retail registrar or a GoDaddy API integration. |
| Easy On The Eyes | Campus art, browser 3D previews, character identity and account flows. | Polish the judge path, small screens, loading/error states and demo transitions. Eligibility does not require another provider. |
| First Timers | No technical integration required. | Only if at least 50% of the team is attending its first hackathon. |

The guide prints the Devpost deadline as **Sunday, 8:00 AM EST**;
use the organizer's actual submission countdown as the deadline. It explicitly
says to opt into extra tracks and put all members on the team. Video is optional.
DeepSpace's credit claim/use deadline of October 28 is separate from submission.

## Best additional bets

| Priority | Addition | Smallest useful implementation | Effort / spend |
|---|---|---|---|
| 1 | **No-login character showcase** | Publish a small set of the approved synthetic character variants with rotatable models or existing renders; link to Gatorize. Show face/hair/body/outfit choices and a recorded real pipeline result. Clearly label samples and recordings. | 1–3 hours; existing hosting/assets, no inference spend for viewing. Benefits Entertainment, AI, Vultr and UX demos. |
| 2 | **AI evaluation card** | Publish aggregate schema validity, appearance accuracy and latency from the existing Qwen evaluation artifacts, plus a few synthetic failures and the design response. Add a compact guide/Gemini routing example. Keep private references and tokens out of the public report. | 1–2 hours; existing runs can supply evidence without new paid calls. Especially valuable because the AI track explicitly values technical depth and readable code. |
| 3 | **DEV Writing Challenge** | Draft a technical story: turning reference photos into an N64-compatible player, hosting co-op, phone login from the game, and realtime results. Include architecture, tradeoffs, code links and measured failures. | 1–2 hours; no new infrastructure. User/team review and publication still required. The guide describes monthly selection, not a guaranteed expo prize. |
| 4 | **Queue position and capacity feedback** | Show queued jobs ahead, measured approximate wait, and a clear admission-paused/full state. Reuse job timestamps and status APIs; distinguish model-ready from game-deployed. Avoid promising an exact ETA. | 2–4 hours; no extra provider. Improves the actual expo experience more than another sponsor logo. |
| 5 | **Tiger Data mission analytics** | Finish the existing optional study service: authenticated `/events` ingestion with idempotent IDs, time-series mission results, and `/analytics/:missionId` aggregates for completion time/retries/team size. Show a real trend in the app. Keep self-reported study events separate from verified hosted results. | Roughly 4–8 hours for a small demo; allow more for deployment and real-data validation. Requires a Tiger Data project/credentials and checking current trial limits/pricing. No provider price or free tier was verified here. |

**Tiger Data is the only new sponsor integration I would consider in the remaining
hackathon window.** `companion/app/src/server/study-routes.ts` already validates,
authenticates and rate-limits these proxy routes, and `src/lib/study-api.ts`
contains the client contract. However, no Tiger Data service, schema migration or
hypertable implementation was found in this repository. The optional external
service's deployment is unverified. Those hooks alone do not establish a Tiger
Data integration. Keep the existing Vultr PostgreSQL transactional database;
analytics can be a separate sink. Do not migrate the core backend for this track.

For the first version, event-time buckets and SQL aggregates are enough to make
useful analytics; add a Timescale hypertable/continuous aggregate where supported
and demonstrate it with real data. Synthetic chart fixtures must be labeled.
Avoid forwarding account identifiers, player names, photos or squad codes.

## Backend priorities before more features

The prior backend branches are represented in main: session-bound identities,
durable/idempotent event delivery, generation admission accounting, consistent
slot locks, worker leases, presence heartbeats, durable storage cleanup, deploy
revalidation, account erasure and explicit Auth0/DeepSpace linking. Reimplementing
those would duplicate work. Existing deletion preserves provider accounts and
removes associated Gator leaderboard runs, per the selected policy.

1. **Finish coordinated deployment acceptance.** Record the deployed commits,
   schema/bindings and execute one consented character build through guest install,
   a real hosted run through signed leaderboard delivery, and two-account
   link/revoke/delete checks. Read-only health probes do not cover these. See
   [the operations checklist](backend_operations_validation.md). Another agent
   owns merges/deployment; this review did not change production.
2. **Operational backups and recovery.** A synthetic schema restore tool exists,
   but a scheduled encrypted production `pg_dump`, off-host retention and a
   restore of an actual backup still need evidence. The documented Vultr hobbyist
   DB plan lacks provider backup/fork support. Preserve deletion tombstones and
   reconcile post-backup erasures before restoring service. Budget 2–4 hours for
   scheduling/checks plus the real drill; use existing storage if suitable.
3. **Cost and overload control.** Generation already has per-user and global-hour
   admission limits; study proxies already have per-user/global budgets. These
   are not a dollar cap or a GPU shutdown policy. Add an operator generation pause,
   bounded queue admission, a shared NPC inference budget and visible capacity
   errors; agree an exact post-expo shutdown/retention time. Alerts alone do not
   stop charges. Roughly 2–4 hours for application controls, plus operator setup.
4. **Actionable operational metrics.** Add protected summaries of oldest queued
   job, worker lease age, cleanup failures, deploy age, bridge outbox rejections
   and DeepSpace delivery backlog; alert on persistent age/failure thresholds.
   Existing health/status endpoints and SQL checks are the starting point.
   Expose aggregate public availability only, never account data. Roughly 2–4 hours.
5. **Retention and recovery completeness.** Review old orphan objects, noncurrent
   S3 versions, bridge/event history, cleanup tombstones and backup retention.
   Current-job cleanup is implemented; those historical stores need an explicit
   policy and inventory. Plan 1–2 hours of investigation before deletion work.

The NPC work also needs an integration decision: main includes the smaller
packet-size crash fix, while `fix/npc-interaction-errors` (`2a24f33`)
contains broader sender attribution, history isolation and timeout fixes. That
branch requires a coordinated patched engine/server/client rollout and direct
connections. Do not deploy its Lua alone or count a full local build as a live
multiplayer acceptance test. Keep this separate from the documentation branch.

## Tracks I would skip

- **Nessie:** a campus budget/meal-plan simulator is possible, but it would need a
  useful financial workflow and real Nessie API use. It is a product detour, not
  a quick backend improvement.
- **Solana:** an on-chain completion certificate needs wallet UX, transaction
  submission and verification. A token or wallet button alone adds little value
  to this game; avoid it under the current deadline.
- **PlanIT Control:** the guide asks for construction-site environmental data,
  warnings and historical ML hazard forecasts. This game does not meet that scope.
- **Roblox Studio:** the guide requires Roblox Studio and Luau core logic; this
  native coopdx project does not qualify through ordinary Lua alone.
- **Hardware:** only worth entering with an actual physical-device interaction.
- **Least Vibe Coded:** the repo explicitly documents substantial AI-assisted
  development. Do not misrepresent that as minimal AI-generated code.

## What was checked in this review

Source inspection covered the API/worker/bridge, companion SDK wiring, schemas,
leaderboard subscriptions, identity linking, study proxies and operational docs.
The DeepSpace [data model](https://docs.deep.space/concepts/data-model) and
[realtime documentation](https://docs.deep.space/concepts/realtime-sync) confirm
the SDK terminology used in the README.

Read-only `server/deploy/check_public.py` passed for both the app.space and
`https://gatorcamp.us` origins: public API health, anonymous/invalid-token refusal,
Auth0 discovery/JWKS/PKCE/device-grant advertisement, companion pages and CORS.
The server reported online with zero players during the checks. This does not
prove the authenticated flows, model quality, live run ingestion, DNS registration
eligibility or which commit every deployed service runs.
