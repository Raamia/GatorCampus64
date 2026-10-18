# Public pipeline status

`GET /pipeline/status` is unauthenticated and read-only. It returns at most the
12 newest jobs, ordered by creation time, with only a 12-character opaque job
label, allowlisted state/current step, total elapsed seconds (including queue),
step intervals `{step, seconds, running}`, and allowlisted GPU readings.
`observed_at` is the UTC snapshot time; running durations are measured at that time. The SQL transaction is read-only.
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
The `gpu` array contains up to eight workers seen in the last 24 hours, each with
an opaque `id`, `observed_at`, `available`, and up to 16 `gpus`. Devices expose only
`index`, `utilization_gpu_pct`, `memory_used_mib`, and `memory_total_mib`. Unknown
metrics are null; zero is a measured value. Hardware names, hostnames, raw logs,
driver errors and process data never appear. Readings older than 30 seconds are
marked stale in the UI, independently of the API's own polling timestamp.

The worker reports every ten seconds while idle or building, using bounded local
`nvidia-smi` queries on an independent thread/DB connection. These are device-wide
samples, not per-job attribution or peak values. No remote model endpoint is queried.
No historical readings are invented for old jobs.
Apply the normal API schema migration before serving the new endpoint. Existing
workers automatically produce timings through their existing state writes.
GPU rollout order: apply the idempotent `worker_gpu_status` table addition, deploy
the API, restart the GPU worker after its current job, then deploy the website.
The website accepts older API responses without GPU fields during rollout.
Sampler failures do not fail character jobs; old readings become stale. Existing
job/upload formats and worker model settings are unchanged.

JPEG intake also accepts MPO containers, used by some iPhone HDR JPEGs. Only the
primary frame is decoded, oriented, resized and re-encoded as plain RGB JPEG;
auxiliary images and EXIF/GPS/MPF metadata are discarded. The existing upload and
pixel-size limits still apply. This does not add HEIC decoding.


# Anonymous Gatorize drafts

The companion can create and preview a character without an account. It stores
32 random bytes (64 lowercase hex characters) in browser local storage before
uploading and sends `Authorization: Guest <key>` to `POST /characters`,
`GET /drafts`, `GET /jobs/{id}`, and `DELETE /characters/{id}`. The API stores
only the SHA-256 hash, checks ownership and expiry on each private request, and
never accepts an invalid Bearer token as an anonymous request. Keep this key
out of URLs and logs. Clearing browser storage loses access to unclaimed drafts.

Drafts expire 24 hours after creation. They are absent from the public gallery
and cannot receive a game slot, even when the existing worker calls
`sgl_assign_slot`. The cleanup loop deletes expired terminal drafts and queues
artifact deletion; active builds can finish first. Existing photo cleanup still
runs when processing ends. The public pipeline remains an allowlisted operational
projection without names, photos, raw IDs, or credentials.

After a user chooses **Sign in to use in game**, the companion preserves that
intent across the Gator Pass redirect. `POST /characters/{id}/claim` requires a
verified human Bearer token with `create:character` and JSON
`{"draft_token":"<key>"}`. A ready draft becomes account-owned atomically;
its key and expiry are cleared, account quotas are checked, and normal slot and
deploy handling begins. Retrying a successful claim by the same account is safe.
Signing in alone does not automatically claim all drafts. Signed-in creation
continues to use the existing account-owned flow.

Per-browser draft limits use the existing active/total settings. Browser keys
are not identities and can be rotated; the durable global hourly admission cap
is shared by anonymous and signed-in generation and survives character deletion.

Deployment order: apply `server/api/schema.sql` to the API/worker database,
then release the API, then the companion. The migration is idempotent, preserves
existing owned characters, and updates slot assignment/reconciliation before
anonymous uploads become possible. No worker or game-server binary change is
needed. Do not roll back to old slot functions while anonymous rows remain.
