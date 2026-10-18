# Durable cleanup and deploy revalidation

Branch `feat/backend-cleanup-deploy-safety` builds on the reviewed revision
(`feat/backend-leases-heartbeats`). Integrate its prerequisite branches first.
This changes only backend/server code and tests; no mod sources or assets change.

## Durable object cleanup

`storage_cleanup` holds `(job_id, kind)` intents without a foreign key, account
identifier, or image content. API uploads commit both photo/build intents before
writing any object. Database triggers enqueue cleanup when a job is inserted,
changes state or is deleted, including cascades. Thus failed uploads, worker
completion, lease expiry and deletion retain cleanup intent across crashes.

The API runs a cleanup loop every 30 seconds, processing up to 20 due prefixes.
It deletes photos only for absent/terminal jobs, and builds only for absent/failed
jobs. A transaction holds the queue row lock during storage deletion; competing
API processes use SKIP LOCKED. API uploads and worker build uploads share a per-job
advisory lock with the cleaner. Worker uploads also recheck their lease before
each object write, so an old worker cannot recreate objects after deletion.
S3 HTTP success with per-object `Errors` is treated as failure, on both API and
worker clients. Failed deletes retry indefinitely with exponential backoff capped
at one hour. Prefix deletion is idempotent.

Successful intents remain as tombstones, revisited daily to catch late objects
from older processes. They are not silently pruned: monitor queue size and oldest
eligible due work as history grows. Multiple API instances can drain in parallel.
Compact historical tombstones only after separately establishing that their
writers cannot return. Existing immediate pipeline cleanup remains as an early
attempt; the durable cleaner supplies retries. Cleanup needs an available API,
database and object store; no new daemon or credentials are required.

The migration backfills jobs still in PostgreSQL. It cannot discover historical
orphaned objects whose jobs were already deleted. A separately reviewed bucket
inventory is needed for those. Versioned-bucket noncurrent versions, lifecycle
rules and independent backups also need operator retention policy; deleting a
current object does not prove that all storage versions/backups were erased.

Useful read-only checks:

```sql
SELECT kind, count(*), min(next_at), max(failures)
FROM storage_cleanup WHERE last_error IS NOT NULL GROUP BY kind;
SELECT q.kind, count(*), min(q.next_at)
FROM storage_cleanup q WHERE q.next_at <= now()
AND NOT EXISTS (SELECT 1 FROM jobs j WHERE j.id = q.job_id
  AND (j.state NOT IN ('ready','failed') OR (q.kind = 'builds' AND j.state = 'ready')))
GROUP BY q.kind;
```

## Deployment safety

The bridge reports its locally installed deploy IDs before polling. The API
reconciles mismatches and queues a new generation when the desired character
was not installed, including after a lost acknowledgement and placeholder rollback.
Before modifying files, the bridge stages pristine fallback placeholders, finishes
the restart countdown, stops the game, then asks `/deploys/check` which staged IDs
are still current. Stale IDs are replaced by placeholders and never installed.
An API outage prevents staged installation. A missing fallback prevents any swap.

The API's current-deploy check requires the newest deploy generation for that
slot, matching slot ownership, and a ready character/job; placeholders require
an empty slot. Acknowledgements take the slot advisory lock and recheck this
predicate. An unchanged successful acknowledgement is idempotent; superseded,
deleted or evicted work returns 409. Completion is acknowledged while the game
is stopped. Rejection or an uncertain acknowledgement restores placeholders and
clears local deploy IDs; the next reconciliation retries the intended state.
If rollback itself fails, the bridge stops the game instead of starting a partial
install. Restoring a placeholder removes a stale personalized portrait even when
the pristine source has no portrait.

This is reconciliation across PostgreSQL and a filesystem, not a distributed
transaction. A deletion after a valid acknowledgement queues corrective work
normally. Process/power loss during filesystem replacement still requires the
existing operational recovery procedure; it is not an atomic filesystem release.

## Rollout

Drain workers, stop the bridge/game, back up PostgreSQL and bridge state, apply
`server/api/schema.sql` once, then update API/worker/bridge together. The SQL adds
the cleanup table/index/triggers and deploy validation function. The release
updater does not run the migration. The bridge now requires `/deploys/check` and
`/deploys/reconcile`; old APIs cause it to leave staged work unapplied. Preserve
the installed roster and pristine placeholder sources.

Verify controlled storage failure/recovery, character deletion during a restart
countdown, a repeated deploy acknowledgement, and a worker lease loss during an
upload in staging. Monitor cleanup errors and pending deploys. Roll application
versions back together if necessary; leave durable cleanup rows intact. Nothing
in this branch performs a production deployment or deletes production objects.

## Validation

Regression suites passed: 115 API, 89 bridge and 62 worker tests (266 total).
After the final rejected-upload cleanup refinement, all 21 upload/cleanup tests
were rerun against real PostgreSQL and passed. Coverage includes durable retries,
partial S3 deletion failures, uncertain upload responses, cascades, writer locks,
ready-build retention, stale-worker upload fencing, stale deployment IDs,
acknowledgement reconciliation, missing fallbacks and failed rollback shutdown.
`git diff --check` is clean. Tests use disposable PostgreSQL and fake storage/game
services; this is merge readiness, not evidence of a production rollout.
