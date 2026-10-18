# Account lifecycle and leaderboard erasure

Branch: `feat/backend-account-lifecycle`, stacked on `feat/backend-cleanup-deploy-safety` .

## Behavior

- `DELETE /links` with a Gator Pass user bearer revokes all existing game links and unused link codes. Historical leaderboard results remain. The bridge polls `/links/check` with heartbeats and stops rebroadcasting revoked identities; ranking rejects revoked links immediately.
- `DELETE /account` with a user access token issued within five minutes and JSON `{"confirm":"DELETE"}` removes the local user, characters, jobs, links, codes, associated events and leaderboard runs (including shared runs containing this player). Provider accounts in Auth0 and DeepSpace remain intact. The response is 202: object cleanup, placeholder deployment and remote leaderboard erasure are durable asynchronous work.
- A solo run by someone else remains even when the deleted player was online as a spectator. Captured spectator identity metadata is stripped from stored run events. Historical events are associated only through trustworthy link/connection references or known session/player aliases; older anonymous events cannot always be attributed.
- `POST /account/register` explicitly creates a fresh local account after signing in with a token issued after deletion. It restores no previous data. The deletion cutoff remains so older tokens cannot become valid again. Normal sign-in does not silently recreate a deleted account.

Minimal revocation metadata (subject hashes, link/connection IDs, event keys and run UUIDs) remains to prevent delayed uploads from recreating removed records. This metadata must be included in backups and restored alongside application data. A provider-issued timestamp is checked; this does not require a fresh password challenge or MFA.

## Remote deletion

`run_erases` survives removal of runs. The API pusher signs deletion messages over the existing ingest protocol, retries failures indefinitely and rechecks successful deletion daily. The companion stores private `erased_runs` tombstones before deleting verified results and rejects late resurrection. The `RUN_INGEST` Durable Object serializes ingest and erasure across Worker isolates. This is eventual cleanup across separate stores, not an atomic cross-service transaction. Existing leaderboard caches and already-open game clients can retain a display until refresh/reconnect.

Deploy the companion's `v3-run-ingest` migration/binding and schema before the API begins delivering erasure messages, then the API/schema and bridge. Existing pending queues remain retryable across rollout. Do not drop tombstones on rollback. Inspect `run_erases.sent_at`, `last_error`, `next_at`, `storage_cleanup`, and pending placeholder deployments to confirm completion; never treat HTTP 202 as all bytes already removed. Historical orphan objects and versioned bucket retention retain the limitations documented in `backend_cleanup_deploy_safety.md`.

## Scope and limitations

This branch supplies backend endpoints; no mod code changes. The mod has no command to remove its verification star, so that display can remain until reconnect even though server authorization has been revoked. Auth0-owned Gator data and its verified leaderboard mirror are covered. Separate DeepSpace study/solo data cannot be reliably attributed without an explicit identity link; the next branch handles that association. Provider accounts are never deleted.

## Validation

- Full API/worker suites: 181 passed; added legacy-event deletion case subsequently passed with all five account tests.
- Bridge: 91 passed, including server-generated departure references and stale revocation responses racing a replacement login.
- Companion: 47 tests plus TypeScript validation; production build passed (existing bundle size warning).
- Real PostgreSQL fixtures used; remote ingest tests cover signed deletion, replay, late ingest and serialized concurrent ingestion/deletion. Live deployment/interactive acceptance remains the merging agent's responsibility.
