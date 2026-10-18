# Backend remediation

Implements the six prioritized findings in [the assessment](backend_assessment.md).
Changes are restricted to server/API/worker/bridge code and the companion's study
service integration. No mod source, gameplay, or assets changed. Nothing was
merged, pushed, or deployed as part of this work.

## Resulting behavior

| Finding | Fix |
| --- | --- |
| Late login completion | Both login paths check the current attempt and publish while holding the cancellation lock. Leave/join/reset invalidate attempts; pending player auth commands are removed on disconnect and the inbox is cleared on game exit. |
| Wrong account on delayed runs | The bridge creates a game-session UUID and a UUID per joined connection. `/links` stores these and its authenticated bridge subject, returning a link ID. Runs capture exact login references at bridge receipt. The API resolves those references rather than the newest login at delivery time. |
| Public privileged study proxy | Bearer-authenticated non-anonymous users are required for upstream calls. A shared Durable Object admits at most 30 calls per user and 500 globally per UTC hour, across all study endpoints and Worker isolates. Anonymous/quota-exhausted hint requests use the local catalog. Submitted reports are explicitly self-reported/unverified. |
| Deletion resets generation quota | `generation_admissions` stores job admission independently of deletable jobs, contains no photos/account identifiers, and retains one day of history. Admission checks precede image decoding and run in the same serialized transaction as job creation. |
| Database deadlock | Slot-changing transactions take `sgl_slots` first, then the character row, then its job. Claim/progress operations lock the character before the job. Delete, successful/failed completion, admin slot changes, and deploy queuing follow the order. |
| Lost/duplicate events | SQLite WAL with FULL synchronization stores each bridge event before delivery. Successful acknowledgements remove rows; retries preserve IDs. PostgreSQL uniqueness on bridge subject/event ID makes event, run, and outbox writes idempotent, including concurrent retries. Reusing an ID for different data returns 409. |

No mod protocol change is needed: identity and delivery fields are added after
the bridge reads game stdout. `events.at` remains receipt time; `occurred_at`
separately records the bridge timestamp. `sequence` preserves the producer order
in the event payload. Auth0 and DeepSpace remain separate account systems.

Legacy events can still be recorded but **cannot create ranked runs** without
session-bound identity references. Historical ranked results are unchanged.
The updated bridge refuses to publish a session-bound login if an older API
does not return a link ID. Upgrading only one side therefore does not silently
fall back to the unsafe account lookup.

## Deployment handoff

The audit began at the reviewed revision; `origin/main` advanced during remediation. The
upstream changes did not touch the backend files changed here. Integrate with
current main before release so an old audit snapshot is never deployed over
newer mod/assets work. Follow [operations](operations.md); the existing release
updater does not apply SQL or Cloudflare migrations for the operator.

1. Back up the database, bridge state (including any SQLite/WAL files), and
   existing service/configuration files. Arrange a quiet player/job window.
2. Stop/drain workers and the bridge for the coordinated lock-order/protocol
   upgrade. Stopping the bridge stops the game. Avoid mixed old/new worker
   locking conventions during rollout.
3. Apply `server/api/schema.sql` once with the API's schema command
   (`python -m sgl_api.schema` in the configured API environment). It adds the
   admission ledger, link context columns, event context/timestamp columns,
   delivery uniqueness index, and updated deploy-queue function. It backfills
   recent existing jobs into the admission ledger. It is idempotent.
4. Install/start the updated API, worker, and bridge. Keep
   `SGL_BRIDGE_STATE` on persistent writable storage (normally `/srv/sgl/bridge`).
   One bridge process may own its outbox; a second instance fails the file lock.
5. Deploy the companion with `STUDY_BUDGETS` / `StudyBudgetRoom`. Both the DO
   manifest and Wrangler migration `v2-study-budget` are included. A missing
   binding fails closed for upstream calls. No new credentials are required.
6. Verify login/cancel/reconnect, character creation/deletion, live run attribution,
   event replay during an API interruption, and study sign-in/quota behavior.
   Do not submit synthetic audit events to the production leaderboard.

Additive database columns/tables can remain if application code is rolled back,
but rolling the API/bridge back restores the original attribution/delivery risks.
Do not delete the outbox to roll back or to clear an alert.

## Outbox operation

`events.sqlite3` contains `outbox(id, envelope, error, created)`. Null `error`
means pending delivery. Non-null `error` means a permanent API rejection retained
for investigation. Retryable transport/429/5xx failures use exponential backoff.
Transient retries do not consume new event IDs. The database is owner-readable
only; the envelope contains server-side login references, not access tokens or
link codes.

The 20,000-row cap includes rejected rows. A full/unwritable outbox stops the game
and logs a critical error; previously accepted rows are preserved. The event that
cannot be committed is reported as a persistence failure and cannot be promised
delivery. Recover disk space/API compatibility before restarting. Inspect
rejections while the bridge is stopped; after correcting their cause, an operator
can clear the selected row's `error` to retry the original envelope. Preserve the
event ID and payload. Archive reviewed permanent rejections before removing any
rows. Do not overwrite payloads to reuse IDs.

## Validation

Final local results: **104 API, 82 bridge, 54 worker, and 44 companion tests
passed (284 total)**. API/worker suites used disposable real PostgreSQL; storage
and identity providers were local test doubles. Companion TypeScript checks and
the production Vite build passed. No live model inference or game-client session
was required for these backend regressions.

- Real Postgres API tests cover delayed hello/run delivery, wrong connection,
  legacy unranked behavior, concurrent duplicate submissions, deleted-job quotas,
  and slot-lock ordering during deletion.
- A real bridge/LoginService/durable-outbox/API integration test queues two
  accounts' runs, disconnects/restarts, reopens the spool, then verifies each run
  still belongs to its original account.
- Bridge tests cover cancellation during both HTTP login paths, replacement
  attempts, stale inbox cleanup, disk replay, overflow preservation, permanent
  rejection retention, exclusive spool ownership, and concurrent sender exclusion.
- Worker tests cover character-before-job locking and the real API/worker pipeline
  with fake Blender. Companion tests cover anonymous refusal, catalog fallback,
  global/user limits, concurrent admission, counter persistence, and missing-binding
  failure. Type checking and production build are included.

The full evidence is local tests, not a production rollout. Other assessment
follow-ups—worker leases, presence heartbeats, durable S3 cleanup, deployment
revalidation, live Auth0 configuration, and backup/restore drills—remain separate
work; they were not among the six prioritized remediation items.

Worker leases and presence heartbeats are implemented in the follow-up
[`feat/backend-leases-heartbeats` branch](backend_leases_heartbeats.md), with its
own schema and coordinated rollout requirements. The remaining operational
items above are still separate work.
