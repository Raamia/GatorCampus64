# Remaining work

## Operator work

- [x] Review/adopt release-tool baselines on both hosts. Both `host` and `gpu` are now adopted/managed by `server/deploy/release.py` (previously unmanaged/ad hoc); both are deployed at commit the reviewed revision. This also reconciles the installed game assets against a consolidated commit on both targets, so the earlier "no full mod manifest" gap is closed.
- [ ] Add a database backup procedure and verify restore into a separate database. **Note:** the Vultr Managed Database plan in use (`vultr-dbaas-hobbyist-cc-1-25-1`) does not support Vultr's own backup/fork/restore feature at all — confirmed via the Vultr API (`GET /databases/{id}/backups` returns "This plan does not support forking or restoring from backups"). Don't look for a plan setting; this needs a custom `pg_dump`-based procedure instead.
- [x] Configure the Auth0 SPA callback for the deployed DeepSpace `/gatorize` route, logout origin, and Web Origin. Confirmed set; in-game Gator Pass login (device flow: `/login` → QR code → phone approval → verified) tested end-to-end on the live hosted server and works.
- [x] Verify Auth0 `create:character` and `read:own` permission grants interactively. Confirmed present on the Auth0 API, along with `admin:slots` and `bridge`. (Namespaced nickname/UF claims still optional/not done.)
- [ ] Bind the preferred custom domain after the app flow is verified; update callback URLs, CORS and public configuration together. **Known gap:** `login.gatorcamp.us` (the Auth0 custom domain) does not resolve yet — direct check against `login.gatorcamp.us/.well-known/openid-configuration` fails to connect, while `gatorcamp.us` and `api.gatorcamp.us` both work. Login currently works through Auth0's raw tenant domain instead, which is functional but not the branded end state the platform spec describes.
- [ ] Add spending alerts and agree the exact Sunday shutdown/retention time. No paid fallback or spend cap is implemented yet. Still unaddressed; expo is 10-12 on the Sunday judging day, so shutdown timing needs an actual team decision, not just a default.
- [x] `GEMINI_API_KEY` set in production (`/etc/sgl/bridge.env` on `host`). NPC chat (Albert/Alberta) now gives real Gemini answers in prod, not just the static-guide + canned-fallback behavior.

## Product follow-up

- [ ] Character deletion and confirmation UI for reclaiming account/guest capacity.
- [ ] Optional expiring game-link code flow in the companion app.
- [ ] Decide whether to keep the legacy squad screen in primary navigation.
- [ ] Evaluate model likeness/latency on consented representative photos; readiness checks alone do not establish quality.

## Teammate acceptance (deferred)

- [ ] Browser Gator Pass login, consent/photo upload, refresh/return to an existing job, previews and failure states.
- [ ] Real character generation, guest-slot deployment and game restart.
- [x] In-game `/login`, account badge, generated character selection and multiplayer appearance. Tested end-to-end on the live hosted server (see Operator work above).
- [ ] Successful hosted run → API ranked result → signed DeepSpace ingestion → public leaderboard. **Partial:** the pipeline now has real test coverage on both ends (`companion/app/src/lib/leaderboard.test.ts`, `companion/app/tests/leaderboard.spec.ts`, plus the existing API/ingest-route tests) — ranking, tie-breaks, signing, and the page's empty/offline states are all verified in isolation. The actual live run-through (finish a mission on the hosted server and watch it land on the public board) still hasn't happened; isolated test coverage is not a substitute for that.
- [ ] Visual/mobile review of the new pages and native game handoff.
