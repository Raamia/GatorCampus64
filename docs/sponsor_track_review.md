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
| Best Use of Vultr | Six products: Cloud Compute (game/API host), Cloud GPU (`vcg-a16-6c-60g-16vram`, NVIDIA A16, runs the Qwen/vLLM + Blender worker), Managed PostgreSQL 17, S3-compatible Object Storage, a private VPC and a Firewall group — all in Atlanta. | Show the upload → GPU job → preview → deployed guest path. Inference runs self-hosted vLLM on the Cloud GPU today; the client is already wired for Vultr Serverless Inference via one env var if a suitable vision model is available there. |
| GoDaddy Registry domain | `gatorcamp.us` uses the GoDaddy Registry `.us` TLD across web/API/game entry points. | Registration and DNS are at Porkbun. Confirm the guide's eligible registration requirement with organizers; do not claim registration through GoDaddy's retail registrar or a GoDaddy API integration. |
| Easy On The Eyes | Campus art, browser 3D previews, character identity and account flows. | Polish the judge path, small screens, loading/error states and demo transitions. Eligibility does not require another provider. |
| First Timers | No technical integration required. | Only if at least 50% of the team is attending its first hackathon. |

The guide prints the Devpost deadline as **Sunday, 8:00 AM EST**;
use the organizer's actual submission countdown as the deadline. It explicitly
says to opt into extra tracks and put all members on the team. Video is optional.
DeepSpace's credit claim/use deadline of October 28 is separate from submission.

## Decisions after review

The project owner confirmed the following after reviewing these proposals:

- End-to-end generation, leaderboard delivery and account deletion are accepted.
- Servers will be shut down Tuesday night, October 20, after the LinkedIn post.
  No additional database/backup project or operational monitoring/capacity work
  is requested for this short-lived deployment. Existing app databases remain
  part of the running system until shutdown.
- **Approved:** the public, no-login character showcase.
- **Explain before implementing:** the AI evaluation card.
- **Maybe later:** a DEV technical write-up.
- **Declined:** queue position/ETA work and Tiger Data integration. Expected
  concurrency is roughly a dozen players; no extra provider is being added.

No infrastructure is shut down, deleted, or scheduled for deletion by this
branch. Merge and deployment remain with the deployment owner.

## Approved showcase

`/showcase` is a public, prerendered companion route outside the auth/data-provider
layout. It presents all 23 approved synthetic appearance studies with category
filters, lightweight rendered previews, and optional interactive 3D rotation.
It requires no login, photos, database calls, model inference or API credentials.
The landing page and navigation link to it. The ordinary Gatorize flow remains
available for visitors who want their own character.

Only fixed-spec synthetic GLBs and converted WebP posters are published. Source
references, photo-evaluation outputs and Blender work files are excluded. The
exporter is `tools/likeness/export_showcase.py`; source batch provenance is in
`companion/app/public/showcase/provenance.json`. The app bundles all public assets,
so neither the private Zion review server nor the generation worker is required
for viewing the showcase. Merged and deployed; live at [gatorcamp.us/showcase](https://gatorcamp.us/showcase).

## AI evaluation card — proposal, not implemented

A short public engineering page could explain four things:

1. **What the model does:** Qwen reads photos and selects face/hair/body/outfit
   profiles; the Blender builders produce geometry. Gemini separately answers
   mascot questions using guide retrieval where appropriate.
2. **What we tested:** use the existing fixed synthetic set and frozen labels,
   show the exact number of cases, and distinguish raw schema validity from
   label agreement. Synthetic results do not measure real-person resemblance.
3. **What happened:** report measured latency and per-category selection results
   from a specific existing run. Show one successful synthetic example and one
   failure, rather than publishing a cherry-picked accuracy claim.
4. **Why the design looks this way:** explain independent shape controls, schema
   validation, uncertain-feature handling and known face/body selection biases.

This is presentation of work already done, not another model, fine-tuning run,
paid benchmark or telemetry system. No private reference photos or model prose
about real subjects need to be published. Estimated effort remains 1–2 hours
using existing artifacts. Await the owner's decision before adding this page.

For example, the existing [synthetic diagnostic](gatorize_likeness.md#live-qwen-diagnostic)
returned valid raw structured responses for 23/23 requests, with no inference
failures and 9.104 seconds median latency. Label agreement was face 1/6, hair
5/8, visible body 1/5 and outfit 2/4; none of the 14 head crops produced the
expected unknown-body label. A card would present both the reliable response
format and these selection limitations, explicitly as synthetic diagnostics
rather than a real-person likeness score.

The optional DEV article can reuse this explanation and the README architecture,
with screenshots and code links. No article has been written or published.

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
