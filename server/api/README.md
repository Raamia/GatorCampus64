# Public pipeline status

`GET /pipeline/status` is unauthenticated and read-only. It returns at most the
12 newest jobs, ordered by creation time, with only a 12-character opaque job
label, allowlisted state/current step, total elapsed seconds (including queue),
and step intervals `{step, seconds, running}`. `observed_at` is the UTC snapshot
time; running durations are measured at that time. The SQL transaction is read-only.
A five-second per-process cache with a refresh lock bounds database polling;
responses also use `Cache-Control: public, max-age=5`, like the public leaderboards.
There is no user-selected limit, account lookup, storage request, photo, raw log,
error detail, hostname, or user/character ID in the response.

The idempotent schema adds `jobs.step_history` and a transition trigger. It
records actual database-observed step boundaries (including repeated build
attempts and terminal failures), keeps at most 64 intervals, and ignores repeated
progress writes. Old rows have no invented history; intervals begin with the next
observed transition. Deleting a job deletes its history with the existing row.
The in-process cache retains anonymous snapshots for up to five seconds; HTTP
caches can retain a response another five seconds. Open pages retain the last
snapshot until their next successful refresh.

The companion's `/pipeline` page is public, prerenders a loading shell, polls
without credentials every ten seconds, and retains a clearly marked frozen
snapshot on outages. It does not claim that job activity measures GPU utilization.
GPU numbers can be added later by explicitly projecting allowlisted telemetry;
this release does not read manifests or depend on `feat/gpu-telemetry-evidence`.
Apply the normal API schema migration before serving the new endpoint. Existing
workers automatically produce timings through their existing state writes.
