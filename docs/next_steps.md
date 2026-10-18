# Remaining work

## Operator work

- [ ] Review/adopt release-tool baselines on both hosts; record manifests and rehearse recovery on staging files.
- [ ] Add a database backup procedure and verify restore into a separate database.
- [ ] Reconcile installed game assets against the consolidated commit, preserving guest roster and state. Earlier bridge deployments did not establish a full mod manifest.
- [ ] Configure the Auth0 SPA callback for the deployed DeepSpace `/gatorize` route, logout origin, and Web Origin.
- [ ] Verify Auth0 `create:character` and `read:own` permission grants interactively; optionally add namespaced nickname/UF claims.
- [ ] Bind the preferred custom domain after the app flow is verified; update callback URLs, CORS and public configuration together.
- [ ] Add spending alerts and agree the exact Sunday shutdown/retention time. No paid fallback or spend cap is implemented yet.

## Product follow-up

- [ ] Character deletion and confirmation UI for reclaiming account/guest capacity.
- [ ] Optional expiring game-link code flow in the companion app.
- [ ] Decide whether to keep the legacy squad screen in primary navigation.
- [ ] Evaluate model likeness/latency on consented representative photos; readiness checks alone do not establish quality.

## Teammate acceptance (deferred)

- [ ] Browser Gator Pass login, consent/photo upload, refresh/return to an existing job, previews and failure states.
- [ ] Real character generation, guest-slot deployment and game restart.
- [ ] In-game `/login`, account badge, generated character selection and multiplayer appearance.
- [ ] Successful hosted run → API ranked result → signed DeepSpace ingestion → public leaderboard.
- [ ] Visual/mobile review of the new pages and native game handoff.
