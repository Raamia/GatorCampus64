# server/bridge

This is the game host's bridge (docs/web_platform_spec.md §5.3, §6.2-§6.4, §7.1). It is a single Python 3.12 process that owns the headless sm64coopdx server.

- **Game process.** `GAME_CMD` defaults to the flags of `server/deploy/sgl-game.service` and runs under `stdbuf -oL`. The bridge reads stdout line by line and logs non-event lines to the journal. When the game exits, the bridge restarts it with a 5 s backoff that doubles up to 60 s while it keeps crashing, and sends an `exit` event to the API.
- **Events (game to bridge).** The game prints `SGLEVT {json}` lines (`mods/sgl64/sgl_bridge.lua`). Each event goes to `POST /events` through a bounded retry queue: 2000 items, the oldest dropped when full, exponential backoff, 4xx responses dropped. An API outage never blocks the pipe.
- **Login.** A `login_req` event starts the Auth0 device flow: `/oauth/device/code`, then polling `/oauth/token`, then ID token checks (RS256 via JWKS, `iss`, `aud` = the Gator Pass client id, `exp`), then `POST /links`, then an inbox `verified`. A `link_req` sends `POST /links {code}`. A `login_cancel` or a `leave` stops polling.
- **Inbox (bridge to game).** The bridge writes `<savepath>/sav/sgl64.modfs` atomically (temp file, then rename). The mod reloads it every second.
- **Deploys.** The bridge applies guest character deploys, with at most one game restart every 5 minutes.
- **NPC chat.** The bridge answers Albert and Alberta's `npc_ask` events with `tools/npc_bridge`'s code (game guide, then Gemini). See NPC chat below.

```
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q          # unit tests (no network, no game)
```

## Install on sgl-host

1. Copy the repo subset to `/opt/sgl`, keeping its layout:
   - `server/bridge/`
   - `server/worker/actor_rename.py`
   - `mods/sgl64/` (fallback source for the guest placeholders)
   - `tools/npc_bridge/` (NPC chat: `bridge.py`, `guide.py`, `game_guide.md`, `npcs.json`)

   Then `python3 -m venv /opt/sgl/server/bridge/.venv && /opt/sgl/server/bridge/.venv/bin/pip install -r /opt/sgl/server/bridge/requirements.txt`.
2. Copy `server/deploy/bridge.env.example` to `/etc/sgl/bridge.env` (mode 600) and fill in the Auth0, M2M and API values, plus `GEMINI_API_KEY` for NPC chat.
3. Copy `server/deploy/sgl-bridge.service` to `/etc/systemd/system/`, then run `systemctl daemon-reload && systemctl disable --now sgl-game && systemctl enable --now sgl-bridge`.
   **Once the bridge takes over, sgl-game stays disabled.** The bridge launches the game itself, and both units would bind UDP 7777; the unit also declares `Conflicts=sgl-game.service`.
   Logs for both the bridge and the game: `journalctl -u sgl-bridge -f`.

## Event format (game to bridge)

Each event is one line, `SGLEVT {"t":"<type>",...}`. `t` comes first, the other keys follow in sorted order, and the line is UTF-8. Only the headless host prints these lines (`network_is_server()` and `gServerSettings.headlessServer`). Clients relay to the host with a mod packet, and the host overwrites `name` with its own view of the player.

| t | fields |
|---|---|
| hello | version, proto (on the host's first update) |
| join / leave | gi, name |
| char | gi, name, friend (friend id, e.g. "daniel" or "guest_3", "" = none), index (FRIENDS index, 0 = none) |
| fin | gi, name, race (the race's pbKey), frames, level, act |
| login_req | gi, name |
| link_req | gi, name, code |
| login_cancel | gi, name (optional; sent by sgl_login.lua if it wants) |
| npc_ask | session, seq, npc (albert, alberta), player, text, stats ("k=v;k=v", see sgl_npc.lua my_stats). Answered here, not sent to the API |
| exit | code (added by the bridge when the game process ends, not printed by the game) |

`POST /events` body: `{t, payload, at}` plus a copy of the payload's fields at the top level, because server/api reads `friend` from the top level.

## Inbox format (bridge to game)

`sgl64.modfs` holds `inbox.json`:

```json
{"seq": 12, "cmds": [{"seq": 12, "t": "login_code", "gi": 3, "user_code": "ABCD-EFGH", "uri": "...", "page": "...", "expires": 900}]}
```

- **seq.** Every command gets the next seq, counting up for the life of the bridge process. The mod runs commands whose seq is above the last one it ran, in seq order. If the top-level seq drops below that (the bridge restarted), the mod resets its counter.
- **Pruning.** Commands are kept for 180 s, at most 64 of them.
- **Game restart.** When the game (re)starts, the bridge empties `cmds` but keeps `seq`, so a fresh game never replays old commands.
- **Values.** Fields are JSON primitives only, because the mod forwards them in coopdx packets. A field set to `None` is left out, so it reads as nil in Lua.

| t | fields | routing on the host |
|---|---|---|
| login_code | gi, user_code, uri (verification_uri_complete, for the QR), page (verification_uri), expires (s) | to player gi |
| verified | gi, name, nickname, guest_slot?, uf?, resend? | broadcast (+ host); re-broadcast for every linked player with resend=true when someone joins |
| login_failed | gi, reason (expired, denied, invalid_token, bad_code, unavailable, error) | to player gi |
| announce | text, secs | broadcast; built-in popup + chat line |

Mod API (`sgl_bridge.lua`):

- `sglBridgeEmit(t, fields)` works on the host or on any client. It returns false offline or when there is no headless host.
- `sglBridgeOnCommand(name, fn)` registers `fn(fields)` on the clients a command is routed to.

## ModFS format: what was verified and what was assumed

I verified these points against the v1.5.1 source (`src/pc/mods/mod_fs.cpp`, `mod.c`, `fs.c`):

- **Path.** The file is `fs_get_write_path("sav")/<mod relativePath minus .lua>.modfs`. The write path is `--savepath`, and a directory mod's relativePath is its directory name, which gives `/srv/sgl/sav/sgl64.modfs`.
- **Archive.** The file is a plain ZIP read with miniz `mz_zip_reader_init_mem`. Every non-directory entry is a file except `properties.json`, which is optional. Its keys are `isPublic` and `files.<path>.{isText,isPublic,compressionLevel}`, the same structure that `mod_fs_write` dumps.
- **File names.** Paths follow the `mod_fs_check_filepath` rules: `.json` is allowed and `properties.json` is reserved.
- **Text detection.** Text mode is detected automatically (no control characters other than whitespace), so `inbox.json` is written ASCII-only.
- **Reload.** `mod_fs_reload()` with no argument drops the cached object and re-reads the file for the active mod. It works during hooks, because `gLuaActiveMod` is set there.
- **Missing file.** If the file is missing, the call returns nil without raising an error.
- **Empty file.** Reading an empty file does raise an error, so the mod checks `size > 0` and wraps reads in `mod_fs_hide_errors`.
- **Output buffering.** Lua `print` flushes stdout (`lua_writeline` calls fflush), so SGLEVT lines arrive immediately even through a pipe.
- **Headless detection.** `headlessServer` is set in `network_init` for `--headless` servers and is sent to joiners in the join packet.
- **Test coverage.** `tests/test_modfs_miniz.py` compiles coopdx's own miniz and reads the bridge's archive with the same calls as `mod_fs_read`. It is skipped unless `/tmp/sm64coopdx` (or `SM64COOPDX_SRC`) and a C compiler are present.

Checked on the live server (sgl-host): the game starts under the bridge with the inbox in place, the bridge (user `sgl`) writes it with mode 644, and the game's `hello` event reaches the bridge. Still to confirm with a client connected: a replaced inbox is picked up on the next reload and its popup appears.

## NPC chat (Albert and Alberta)

On a player's machine, `tools/npc_bridge/bridge.py` reads the mod's questions from `sav/sgl64.modfs` (`npc_out.txt`). On this server that file is the bridge's inbox. The bridge rewrites the whole file, and the mod reloads it every second, so a second writer would lose questions and could put back a stale `inbox.json` with login codes in it. So on a headless host, `sgl_npc.lua` writes nothing there. It prints each question as an `npc_ask` event instead, and `sglbridge/npc.py` answers it:

1. **Queue.** The event goes on a queue (32 at most, the newest dropped when full). `npc_ask` events are not forwarded to `POST /events`, because player chat does not belong in the API.
2. **Answer.** One `npc` thread answers questions one at a time with `tools/npc_bridge/bridge.py`'s `Bridge.handle()`, the same code as the local helper. Game questions are answered from `game_guide.md` with the asker's live stats, and everything else goes to Gemini (`GEMINI_API_KEY`, `SGL_NPC_MODEL`). Without a key, non-guide questions get a canned line from `npcs.json`.
3. **Reply.** The reply goes to `<savepath>/sav/sgl64_npc.modfs` (`replies.txt`, a public modfs), the file the mod already polls. The host relays it to every player. A game restart (new session) drops the queue, and the mod ignores replies from an old session.

Setup: copy `tools/npc_bridge/` to `/opt/sgl` (install step 1), put `GEMINI_API_KEY=<key>` in `/etc/sgl/bridge.env`, then run `systemctl restart sgl-bridge`. The key stays in that root-owned mode-600 file and is never committed. At start the journal shows `NPC chat on (Gemini gemini-3.8-flash; game guide: N entries; ...)`, and then one line per question with its route (`[guide: my-stars 1.00]`, `[ai]`). Game questions the guide couldn't answer well are appended to `$SGL_BRIDGE_STATE/npc_unanswered.log` (`/srv/sgl/bridge/`, since `/opt` is read-only under `ProtectSystem=strict`). If the mascots answer "ask me again in a bit", check the journal for `NPC chat off`, Gemini HTTP errors or a full queue. They also give that answer if the game runs as plain `sgl-game.service` without the bridge.

## Deploys (spec §5.3)

The bridge polls `GET /deploys/pending` (`{"deploys": [...], "roster": [...]}`). Each item looks like `{id, slot, kind, name, owner_sub, files: [{path, url}]}`. The file URLs are presigned, so the bridge needs no S3 credentials. A single zip `artifacts_url` is also accepted. Each deploy is handled in four steps:

1. **Stage the files.** Download them into a temp dir (`previews/` is skipped) and validate the paths.
2. **Rename the actor.** Run `server/worker/actor_rename.py <dl>/actors/sglguest <staging>/actors guest_<slot>`, using `slot` from the deploy. The portrait (`portrait.png`) becomes `textures/sgl_portrait_guest_<slot>.png`. `character.json` is not installed.
3. **Warn players.** If players are online, send an `announce` and wait up to 60 s or until the server is empty.
4. **Restart.** The game is stopped while the bridge swaps in `actors/guest_<n>/` and the png, deletes the stale `actors/guest_<n>_geo.bin` and `textures/sgl_portrait_guest_<n>.tex`, and regenerates `guests.lua`. Then the game starts again, and the bridge reports `POST /deploys/{id} {state, error}`.

A build that can't be staged is reported `failed`. A download outage leaves the deploy pending.

- **Placeholders.** `kind: "placeholder"` restores the slot from a pristine snapshot that the bridge takes of the installed placeholders at first start (`<state>/placeholders/`), falling back to `SGL_PLACEHOLDER_MOD`.
- **guests.lua.** The file is generated in the format `characters.lua` reads: one `sgl_guests_register({ { slot = n, name = "...", owner = "<sub>" or nil }, ... })` call covering 8 slots. The format is isolated in `render_guests_lua()`.
- **Roster.** The bridge keeps its own roster in `<state>/roster.json`.
