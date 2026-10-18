# Explicit Field Board / Gator Pass linking

Branch: `feat/backend-identity-linking`, stacked on `feat/backend-account-lifecycle` .

## User behavior

Gatorize Me now has account settings: link/unlink the current Field Board and Gator Pass accounts, revoke game logins, delete Gator data with typed confirmation, sign in again, or explicitly register a new local Gator account. The Field Board settings page correctly labels its separate identity. Provider accounts stay intact.

Linking requires both sessions. The companion verifies the Field Board bearer, derives its subject exclusively from the verified token, and signs the action, subject and SHA-256 of the exact Gator bearer. The API independently verifies that Gator token and the signed proof, its five-minute window and one-time nonce. The signing key is HMAC-derived with `sgl-identity-v1` from the existing shared ingest secret, separating identity proofs from leaderboard messages. Tokens are never logged, persisted, or followed across redirects. The destination is the app's fixed public API configuration.

The mapping is one-to-one. Conflicts require explicit unlinking of the existing pair; there is no email/name matching or automatic merge. Unlinking requires the currently linked pair, preserves existing data and prevents subsequent Gator deletion from acting on the unlinked Field Board account.

## Linked deletion

Deleting a linked Gator account queues `account_erases` alongside verified run erasure. The companion removes that Field Board user's app-scoped offline results created on or before deletion, in bounded pages. Failed/partial requests retry; successful work is rechecked daily. Newer results and other users' records remain. SHA-256 user/run tombstones prevent deleted IDs from being resubmitted. Offline creation now goes through the authenticated server action; direct client record creation is disabled. The action checks tombstones before and after creation, and the durable retry covers an interrupted cross-room operation. This remains eventual cleanup, not a distributed transaction.

The delivery queue retains the destination DeepSpace user ID and cutoff for reliable retries. Remote tombstones retain hashes only. Include all queues/tombstones in recovery procedures. Do not restore old leaderboard data without replaying deletion records.

Study analytics contain mission aggregates without account IDs; linking cannot reconstruct historical ownership. Squad event streams live in independent rooms with no global user-to-room index. Those historical room records are outside this account deletion endpoint, as are the provider profile and provider account. The hourly study admission counter is abuse-control state, not restored/deleted with Gator characters. A newly submitted, previously unseen offline ID after deletion is new app data; this flow does not disable the retained DeepSpace account.

## Rollout

Merge the parent branch first. Apply the additive API schema (`identity_links`, `identity_nonces`, `account_erases`) before starting the updated API. Roll out companion schema/routes and API together; until both are ready, linking fails closed and queued cleanup retries. Requires the same existing `DEEPSPACE_INGEST_SECRET` at both ends, API `DEEPSPACE_APP_URL`, working public API HTTPS, and correct Auth0 browser callback/origin configuration. No new secret, mod change, merge or deployment is performed by this branch.

Check `account_erases` and `run_erases` for pending failures during acceptance. Test with two disposable accounts: link each, reject a cross-pair link, unlink/relink, delete one, confirm its shared/solo results disappear while the other user's solo run remains, and confirm both provider accounts still work. Confirm a fresh explicit registration cannot use pre-deletion tokens.

## Validation

Companion: 51 tests and TypeScript validation passed; production build passed with the existing bundle-size warning. Includes authenticated proof construction, domain-separated signatures, outage behavior, 101-row cleanup pagination, unrelated/newer record preservation and run replay rejection. API/worker: all 186 tests passed using real disposable PostgreSQL, including proof replay/tampering, ownership conflicts, unlink preservation and signed deletion retries.
