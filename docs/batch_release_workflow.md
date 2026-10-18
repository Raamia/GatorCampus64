# Proposed batch release workflow

This is a design for extending the existing operator tooling, not an implemented
command. PR review and merging remain a deliberate batch operation. Once a batch
is merged, one release command should handle routine preparation and verification.

## Observed production baseline

Read-only inspection on 2026-10-17 (America/New_York) found:

- `root@64.177.55.205` records commit
  `13273d1186aa9788306fd4a480e6b53002ac5b79`, release
  `20261018T012030Z-13273d1186aa`, with 727 managed files.
- Managed hashes match. API and bridge services are active, localhost API health
  passes, and UDP 7777 is listening.
- Public API health, anonymous/invalid-token denial, Auth0 discovery, companion
  routes, and browser CORS checks pass.
- Public `/status` reports `online: false`. Process/socket liveness is therefore
  insufficient release acceptance; the cause of offline presence is unresolved.
  Its empty player list must not be interpreted as proof of an idle game.
- Locally known `origin/main` is `a0b9753`; its changes after the host commit are
  confined to `companion/app`. This does not establish the deployed website
  version. A fresh remote fetch was blocked by an approval-service failure.

No production files, services, PRs, or branches were changed by the inspection.

## Existing mechanism

`server/deploy/release.py` reads SSH inventory from ignored `.env` data and
packages regular tracked files with `git archive`. Host deployments map source
into `/opt/sgl-api`, `/opt/sgl`, and `/srv/sgl/mods/sgl64`. GPU deployments map
source into `/opt/sgl64`. The website deploys separately through DeepSpace.

The updater preserves secrets, virtualenvs, saves, ROMs, and installed guest
characters. It checks managed source drift, snapshots overwritten source and the
previous manifest, installs files, restarts services, and checks liveness.
It has a source rollback command. It does not provision infrastructure, migrate
the database, install changed dependencies, or restore database contents.

Today the operator still chooses the commit, checks freshness, runs tests,
checks occupancy, decides which targets need a release, arranges configuration
and state backups, invokes deployment, and gathers evidence. The host updater
restarts both API and bridge even when their source is unchanged. No deployment
lock or automatic fresh-presence gate is apparent in the updater.

## Proposed operator interface

Illustrative commands, to be implemented:

```sh
python3 server/deploy/batch.py plan
python3 server/deploy/batch.py deploy --plan <saved-plan.json>
```

The plan should fetch `origin/main`, pin its full SHA, record each target's
installed release, classify changed source, and emit a short human summary plus
machine-readable evidence. Deployment should reject a stale or modified plan.
It must not merge PRs, switch a developer's working branch, or deploy uncommitted
files. Use an isolated checkout of the pinned commit for validation and release.

The deployment command should:

1. Acquire a lock shared by deploy and rollback on each target. Recheck source
   drift and expected baseline after acquiring it.
2. Run the required tests/builds for the changed components from the pinned
   checkout. Missing dependencies and skipped mandatory checks are failures.
3. Select affected targets using explicit path/dependency rules and artifact
   hashes. Website-only changes must not restart the game; unchanged artifacts
   should produce a successful no-op. Shared character-generation code can
   affect both host and GPU, so directory names alone are insufficient.
4. Stop for schema, runtime dependency, service-unit, or configuration changes
   requiring a prepared migration/provisioning procedure. Do not silently ship
   source that depends on an unapplied migration.
5. Before interruption, require fresh online game presence and zero connected
   players, or fresh worker state with no active jobs for a GPU release.
   Unknown/offline presence blocks automatic restart. Recheck immediately before
   activation; a guaranteed quiet window ultimately needs admission/drain support.
6. Create the applicable configuration/state backups and retain recovery paths;
   use the existing source snapshot mechanism. Database changes require their
   own backup and migration procedure.
7. Invoke the existing updater, initially retaining its conservative service
   restart behavior. Selective service restarts can follow once dependencies are
   encoded and tested. Record the website release identifier and source SHA too.
8. Require matching source hashes, stable services, API/auth checks, and fresh
   online game presence. Verify the affected website routes or worker behavior
   for their respective targets. Record a release receipt with commit, targets,
   checks, backup locations, timestamps, and recovery command.

Automatic rollback should be limited to explicitly source-only releases whose
dependencies and schema are unchanged. Otherwise report the failed phase and
recovery evidence for operator action. Do not automatically rewind player saves
or database contents. Keep partial multi-target release status explicit.

## Implementation order and validation

First add a read-only JSON inspection/plan interface to the existing release
tool and a strict presence acceptance check. Then add locking, no-op detection,
target selection, and the wrapper that runs validation and deployment. Keep
GitHub merges and deployment independent so a batch can be reviewed before
activation and deployment failure never implies reverting unrelated merges.

Test the safety boundaries with local temporary deployment trees and mocked
SSH/services: stale plans, concurrent deployment, dirty input, unknown presence,
occupied hosts, unchanged artifacts, website-only batches, shared worker paths,
schema/dependency changes, source drift, preserved guest assets, interrupted
installation, failed activation, and rollback. Validate the final workflow on an
isolated target before adopting it for production.
