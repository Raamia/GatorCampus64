# Remaining work

For the current backend priorities, sponsor eligibility and scoped feature proposals,
see the [ track/backend review](sponsor_track_review.md). The historical
operator observations below are snapshots, not a current deployment manifest.

## Operator work

- [x] Review/adopt release-tool baselines on both hosts. Both `host` and `gpu` are now adopted/managed by `server/deploy/release.py` (previously unmanaged/ad hoc); both are deployed at commit the reviewed revision. This also reconciles the installed game assets against a consolidated commit on both targets, so the earlier "no full mod manifest" gap is closed.
- [ ] Schedule production backups and verify a real backup in an isolated restore target. A [synthetic restore drill and runbook](backend_operations_validation.md) already exist; they do not establish production recoverability. **Note:** the Vultr Managed Database plan in use (`vultr-dbaas-hobbyist-cc-1-25-1`) does not support Vultr's own backup/fork/restore feature at all — confirmed via the Vultr API (`GET /databases/{id}/backups` returns "This plan does not support forking or restoring from backups"). Don't look for a plan setting; this needs a custom `pg_dump`-based procedure instead.
- [x] Configure the Auth0 SPA callback for the deployed DeepSpace `/gatorize` route, logout origin, and Web Origin. Confirmed set; in-game Gator Pass login (device flow: `/login` → QR code → phone approval → verified) tested end-to-end on the live hosted server and works.
- [x] Verify Auth0 `create:character` and `read:own` permission grants interactively. Confirmed present on the Auth0 API, along with `admin:slots` and `bridge`. (Namespaced nickname/UF claims still optional/not done.)
- [x] Public reachability and upload CORS checked for both `gatorcamp.us` and the app.space origin with `server/deploy/check_public.py`.
- [ ] Decide whether to finish the optional branded Auth0 login domain. The checked-in browser configuration uses the working tenant domain; earlier operator checks found `login.gatorcamp.us` unresolved. Changing the issuer requires coordinated API/bridge/browser configuration and acceptance, so it is not necessary merely to demonstrate Auth0.
- [ ] Add spending alerts and agree the exact Sunday shutdown/retention time. Application admission limits exist, but they do not cap the cloud bill or stop idle GPU charges; expo is 10-12 on the Sunday judging day, so shutdown timing needs an actual team decision, not just a default.
- [x] `GEMINI_API_KEY` set in production (`/etc/sgl/bridge.env` on `host`). NPC chat (Albert/Alberta) now gives real Gemini answers in prod, not just the static-guide + canned-fallback behavior.

## Product follow-up

- [x] Account settings, character deletion, typed account-delete confirmation, game-link revocation and explicit Field Board/Gator Pass linking are implemented. See [identity linking](backend_identity_linking.md); two-account live acceptance remains below.
- [ ] Optional expiring game-link code flow in the companion app.
- [ ] Decide whether to keep the legacy squad screen in primary navigation.
- [x] First likeness batch and Qwen validation completed and accepted; see [likeness evidence and limitations](gatorize_likeness.md). Optional next step: a public synthetic showcase and aggregate evaluation card, rather than further tuning to specific photos.

## Teammate acceptance (deferred)

- [ ] Browser Gator Pass login, consent/photo upload, refresh/return to an existing job, previews and failure states.
- [ ] Real character generation, guest-slot deployment and game restart.
- [ ] Two-account link/unlink, game-login revocation and Gator data deletion through asynchronous object/leaderboard cleanup; provider accounts must remain intact.
- [x] In-game `/login`, account badge, generated character selection and multiplayer appearance. Tested end-to-end on the live hosted server (see Operator work above).
- [ ] Successful hosted run → API ranked result → signed DeepSpace ingestion → public leaderboard. **Partial:** the pipeline now has real test coverage on both ends (`companion/app/src/lib/leaderboard.test.ts`, `companion/app/tests/leaderboard.spec.ts`, plus the existing API/ingest-route tests) — ranking, tie-breaks, signing, and the page's empty/offline states are all verified in isolation. The actual live run-through (finish a mission on the hosted server and watch it land on the public board) still hasn't happened; isolated test coverage is not a substitute for that.
- [ ] Visual/mobile review of the new pages and native game handoff.
