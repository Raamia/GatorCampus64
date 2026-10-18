# Worker leases and server heartbeats

Follow-up to [backend remediation](backend_remediation.md), on
`feat/backend-leases-heartbeats`, based on remediation commit the reviewed revision.
Server/API/worker/bridge changes only; the mod, gameplay, assets and image model
are unchanged. Merge the remediation branch first, or retain its commits when
integrating this branch. Deployment is a separate operator action.

## Worker ownership and recovery

A claim writes a random `jobs.lease_token` and a `lease_expires_at` 120 seconds
in the future. Hostnames are diagnostic labels, so processes sharing a hostname
cannot revoke each other's work. A dedicated database connection renews every
30 seconds, independently of pipeline output. It has a 5-second connect timeout,
5-second lock timeout and 10-second statement timeout. Renewal failures cancel
that attempt rather than assume it still owns the job.

Progress, renewal and completion lock the character then the job, and check the
matching token, matching character, active state and wall-clock expiry after
locks are acquired. Terminal writes and recovery acquire the slot advisory lock
first, preserving the established lock order. A stale process cannot publish
artifacts, assign a slot, or overwrite a completed/failed result. Each poll sweeps
up to 100 expired jobs from all worker hosts, including pre-upgrade active jobs
with NULL leases; concurrent sweepers return each expiration only once.

Recovery marks both job and character failed, keeps the last step, and records
`Worker lease expired; please retry`. It attempts photo and build cleanup after
the transaction commits. It does not automatically rebuild the job: its photos
may already be gone. A retry is a new user submission with a new job ID, subject
to existing quotas. Do not manually reset failed jobs to queued or reuse their
storage prefixes; an old process may still be unwinding.

Lease loss is checked at pipeline progress boundaries, between uploads and every
second while reading a Blender/face subprocess. Cancellation kills the subprocess
group. A blocking model/storage call returns through its existing timeout before
cancellation is observed. Database fencing remains authoritative meanwhile.

Recovery requires a worker to reach its poll loop. With every worker down, a
replacement performs recovery when it starts; a busy worker sweeps after its
current job. Cleanup remains best effort. Durable storage cleanup and storage
lifecycle verification remain separate work, including the case where a process
or connection dies after committing failure but before deleting objects.

## Current server presence

The bridge posts a fresh `POST /presence` snapshot every 20 seconds on a dedicated
thread using its existing M2M token with `bridge` scope. The snapshot contains
session ID, observation time, game start time, version and current player list.
Online requires a running child that has emitted the existing mod `hello` event.
Shutdown attempts a final offline snapshot. No mod protocol changes are needed.

Presence never enters the durable event outbox. The API stores one current
snapshot per authenticated bridge subject in `server_presence`. Older/equal
observation timestamps do not overwrite a newer snapshot or renew its lifetime.
Requests older than 30 seconds or more than 5 seconds in the future are rejected;
keep bridge and database host clocks synchronized. Outage recovery sends the
current snapshot, not a backlog. `/status` uses the latest observation for the
existing single-server deployment and retains its existing response fields,
adding `last_heartbeat_at`. `last_event_at` remains historical receipt time.

`STATUS_STALE_SECS` defaults to 90; zero/negative values also use 90 so crashes
always expire. Configure at least 60 seconds to allow multiple heartbeat attempts.
Expired/offline presence returns an empty player list. Historical hello, join,
leave and exit events continue to be stored but never affect presence, including
when replayed after a restart. A healthy idle server remains online. This is
process presence, not a proof that game simulation or public UDP access works.
Only the intended game-host bridge should publish presence; multiple simultaneous
servers with distinct addresses would need an explicit server registry/status API.

## Coordinated rollout and rollback

1. Integrate with current main and the remediation branch; do not deploy this
   branch's older mod snapshot over newer main. Back up PostgreSQL and bridge
   state as described in [operations](operations.md).
2. Drain and stop all old workers. Stop the bridge/game during the API/bridge
   upgrade. Mixed worker versions are unsupported: old workers do not renew or
   check leases. Any leftover pre-upgrade active job will fail on the first sweep.
3. Apply `server/api/schema.sql` once through the configured API environment's
   `python -m sgl_api.schema`. It adds two nullable job columns, an active-job
   expiry index, and `server_presence`. Schema application is idempotent.
4. Start the matching API, bridge and workers. No new dependencies, secrets,
   machine scopes or mod files are required. Each active worker uses one extra
   database connection; include that in connection capacity planning.
5. Verify a consented generation through completion, a controlled worker kill
   and replacement, and idle status beyond 90 seconds. Verify offline expiry
   after a hard bridge stop and fresh players after reconnect. Verify historical
   event replay does not change presence. Do not inject test leaderboard runs.

The release updater does not apply the SQL migration. An API upgraded without
its bridge reports offline until a new heartbeat arrives. For rollback, stop new
workers before restoring the previous worker code, and roll back API/bridge as a
pair. Additive schema can remain. Old code restores hostname-based recovery and
event-based presence risks; preserve spool contents and event IDs throughout.

## Validation

**254 tests passed: 109 API, 84 bridge, and 61 worker.** `git diff --check` is clean.

Local regression tests use disposable real PostgreSQL, fake identity/storage
providers, and fake Blender for the API-to-worker integration. Coverage includes
expired/wrong-token writes, renewal after waiting on row locks, independent
renewal during quiet work, concurrent sweepers, immutable completion, silent
child cancellation, heartbeat authorization/expiry/reordering, and real
bridge-to-API presence with delayed event replay. No live deployment or manual
game-client testing is implied by these results.
