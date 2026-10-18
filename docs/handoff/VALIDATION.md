# Targeted validation

- Context/docs: verify paths, current-task <=100 lines and `git diff --check`.
- Website: from companion/app run `npm run validate`, `npm run lint`, `npm run build`.
  Then check the affected route in browser, mobile overflow and navigation.
- Lua: `luac -p <changed-file>` and `tools/luatest/run.sh` for behavioral changes.
  The checker targets sm64coopdx v1.5.1; tests cannot prove live camera rendering.
- Geometry: use tools/blender/validate_level.py through the documented tools venv.
- Backend: run pytest from the changed server package using its venv.
  Database fixtures truncate tables: use SGL_TEST_DATABASE_URL pointing to a disposable test database, never production.
- Do not install packages or run broad suites just to validate documentation.
- Do not claim live hosted verification, deployment or tests that were not run.
