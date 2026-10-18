# Backend operational validation and recovery

Branch: `chore/backend-operations-validation`, stacked on `feat/backend-identity-linking`. No merge, push, deployment, provider-account change or production data write is performed by this branch.

## Live observations

Read-only `release.py verify host` and `verify gpu` passed. Both hosts report commit the reviewed revision with matching managed source hashes. Host release: `reviewed-release`, 459 files. GPU release: `reviewed-release`, 1361 files. API/bridge services were active, game UDP 7777 present and worker container running. This release includes the backend audit fixes; it predates the newer leases, cleanup and account branches. Liveness is not an inference or generation acceptance test.

Public HTTPS checks passed for API health, rejection of anonymous/invalid-bearer `/me`, `/status`, companion `/home` and `/gatorize`, and upload CORS from both the app.space and custom-domain origins. Both app.space and `https://gatorcamp.us/gatorize` responded over HTTPS. The probe's explicit `sgl-operations-check/1.0` user agent avoids Cloudflare's rejection of the default Python user agent (HTTP 403 / error 1010).

Auth0 discovery issuer and RSA signing keys match browser configuration; S256 PKCE and the device grant are advertised. Remote boolean-only configuration checks confirmed matching API/bridge issuer/domain/audience, configured bridge device and M2M clients, configured API storage/database/DeepSpace delivery, and schema-on-startup disabled. These checks reveal no credentials. Discovery does **not** prove client-level grant settings, callbacks, logout allowlists, permitted scopes, successful user consent or an authenticated workflow.

## Repeatable checks

From the repository root:

```sh
python3 server/deploy/release.py verify host
python3 server/deploy/release.py verify gpu
python3 server/deploy/check_config.py
python3 server/deploy/check_public.py
python3 server/deploy/check_public.py --origin https://gatorcamp.us
python3 server/deploy/restore_drill.py
```

The first three use the existing ignored SSH inventory. Public checks use no credentials. The restore drill requires Docker and an already-present `postgres:16-alpine` image. It creates a uniquely named container with no network or host mounts, seeds synthetic data, dumps/restores inside that container, checks all table contents, reapplies the schema, checks sequence continuity, exercises cascades/placeholder deployment and verifies deletion tombstones survive. It removes its container and volume on exit. It accepts no database URL, production backup, or production credentials.

Executed drill: 20 tables matched, 45,955-byte custom-format dump; SHA-256 `86cb2ddcd255c4ba5aa7c8af3edd7d2a90a6c6e90c08c3a54b5617b8e11e57e9`. All restore/migration/sequence/cleanup checks passed. Hash/size change between runs because synthetic UUIDs/timestamps change. This proves the current schema can round-trip; it does **not** prove an existing production backup is complete or recoverable. Object storage and DeepSpace stores are not part of a PostgreSQL dump.

Auth0 outage regression tests cover a cold cache failing closed, a warm cache continuing valid signed logins during a discovery outage, and rejection of unknown signing keys and expired tokens. Existing bridge tests cover device-flow transport outages, timeout, cancellation and stale login publication. All 31 targeted auth-outage/device-flow tests passed. The outage was simulated locally; production connectivity was never interrupted.

## Actual backup and recovery drill

Before merging-agent deployment:

1. Record source commit, database/schema version, backup UTC timestamp and retention owner. Confirm a recent database backup exists; an old source/config snapshot is not a database backup.
2. Take a PostgreSQL custom-format backup using a configured service/passfile and a role with adequate read privileges. Keep credentials out of command arguments, logs and the repository. Store it encrypted outside the production host and record its checksum. Check managed-provider backup/PITR retention separately.
3. Restore that backup into a **new, isolated** PostgreSQL instance. Do not point API, workers, bridge or queue pushers at it and do not give it outbound provider credentials. Use matching PostgreSQL client/version, `pg_restore --exit-on-error --single-transaction --no-owner --no-acl`, then apply the matching schema and review warnings.
4. Verify row counts, foreign keys, function/trigger definitions, slot/job relationships and sequence state. Verify `deleted_accounts`, `erased_links`, `erased_events`, `run_erases`, `account_erases` and `storage_cleanup` are present when introduced by the backed-up schema. Test restoration using the same privacy and retention rules as production.
5. Reconcile deletions performed **after** the backup before serving any restored data. A database rollback must never silently restore deleted accounts, photos or leaderboard runs. Keep deletion delivery records available beyond the backup retention horizon. Do not start pushers until tombstones and current erasure queues have been reconciled with the provider stores.
6. Check recoverability of still-required object artifacts separately. Restoring a job row cannot restore its S3 objects. Respect object deletion/version retention; do not restore old photos simply because their job appears in a snapshot. Review the bridge roster, generated guest files and saves separately from pristine source.
7. Record elapsed restore time, final snapshot age (RPO), failures and checksum in the operator record. Destroy the isolated copy under the same data-retention policy. A successful synthetic drill is not a substitute for this run.

## Post-deploy acceptance requiring real sessions

Use two disposable/consented test identities and a quiet hosted-game window. Another agent owns merge/deploy; an interactive tester owns browser/game sign-in.

- Browser sign-in/out and callback on both intended origins; expired token and canceled login behavior; Gator Pass device login and link-code login in game.
- Confirm one player cannot view/delete another player's characters or link the other's provider pair. Link each Field Board/Gator Pass pair explicitly; confirm conflicts, unlink and re-link behavior.
- Submit one shared verified run and one unrelated solo run. Revoke links, verify later runs cannot rank under them, and reconnect to clear the mod's cached badge.
- Delete one Gator account; confirm database data and associated verified/offline results are removed, unrelated/newer results remain, objects are cleaned and deployed guests become placeholders. Watch `run_erases`, `account_erases`, `storage_cleanup` and deploy queues until work is delivered. Confirm provider accounts still sign in. Explicitly register again and verify pre-deletion tokens remain rejected.
- Verify a consented generation and matching guest deploy with the new lease/revalidation protocol. Do not declare inference readiness from container state alone.

Pending inputs/evidence: completed merged deployment, interactive testers/test accounts, and an isolated production-backup recovery target. No production restore or account deletion should be improvised as a health check.


## In-game login configuration regression

If `/login` receives Auth0 `Unauthorized or unknown client`, inspect the bridge's
effective environment as well as `/etc/sgl/bridge.env`. A combined line such as
`AUTH0_CLIENT_ID=<native-id> AUTH0_AUDIENCE=<audience>` makes systemd include the
second assignment in the client ID. A shell-style checker that keeps only the
first token can miss this. Keep one assignment per line and comments on their
own lines. `check_config.py` now compares the running bridge's client ID against
the file and validates its shape, domain and audience, emitting booleans only.

After backing up and correcting the file, restart `sgl-bridge` to load the new
environment (this also restarts the game). Verify device-code issuance and an
`authorization_pending` token-poll response using the running native app client.
Tenant discovery alone does not prove a particular client's device grant works;
the website's SPA client may correctly disallow that grant. A player must still
approve a login to verify the authenticated end-to-end flow.
