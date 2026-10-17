# SGL64 DeepSpace native bridge

This small macOS command-line helper syncs single-player run records after a game session and refreshes the online leaderboard cache used by the game. It keeps gameplay local and does not run a web game or a background service.

## Requirements

- macOS 13 or newer
- Xcode Command Line Tools with Swift Package Manager
- The deployed DeepSpace app with the `submitGameRun` and `getGameLeaderboard` actions
- SM64CoopDX with the SGL64 mod installed

Before deploying the app, allowlist the bridge's exact loopback redirect in `companion/app/wrangler.toml`:

```toml
NATIVE_AUTH_REDIRECT_URIS = "http://127.0.0.1:45173/callback"
```

Deploy the app through its normal DeepSpace workflow after making that change. This helper does not deploy the app. The callback listener binds only to `127.0.0.1`; it does not listen on the network.

## Build and sign in

From this directory:

```sh
brew install swift
SWIFT_TOOLCHAIN="$(brew --prefix swift)/Swift-6.4.xctoolchain/usr/bin/swift"
"$SWIFT_TOOLCHAIN" test
"$SWIFT_TOOLCHAIN" build -c release
BIN_DIR="$("$SWIFT_TOOLCHAIN" build --show-bin-path -c release)"
mkdir -p "$HOME/.local/bin"
cp "$BIN_DIR/sgl64-bridge" "$HOME/.local/bin/"
```

The explicit toolchain path is useful when the system SwiftPM toolchain is unavailable or mismatched. Configure the installed app URL and sign in with Google. This launches the system browser and uses PKCE; the long-lived session token is stored in macOS Keychain. The app URL is saved without credentials under `~/Library/Application Support/SGL64Bridge/config.json`.

```sh
sgl64-bridge login --app-url https://gator-field-board.app.space
```

## Sync after closing the game

Close SM64CoopDX before running sync. The helper refuses when it detects a process named `sm64coopdx`. It reads `pending_runs.txt` directly from the `.modfs` ZIP using `unzip -p`; it never extracts files to disk or modifies the archive. By default, it scans `~/Library/Application Support/sm64coopdx/sav` and requires exactly one matching ModFS. If there are multiple installed mods or archives, select the SGL64 archive explicitly:

```sh
sgl64-bridge sync
sgl64-bridge sync --modfs "$HOME/Library/Application Support/sm64coopdx/sav/<sgl64-mod>.modfs"
```

Successful run IDs are checkpointed per DeepSpace app and account in `~/Library/Application Support/SGL64Bridge/sync-checkpoints.json`. The checkpoint is local metadata, not a credential. If the helper exits after DeepSpace accepts a run but before saving the checkpoint, retrying is safe because the server treats each `(account, run ID)` as unique. Malformed outbox rows stop the sync and remain untouched.

The game outbox may grow over time; the bridge intentionally does not prune or rewrite it. The game does not make live network requests. To show the latest online scores in-game, close SM64CoopDX and refresh the local cache:

```sh
sgl64-bridge refresh-leaderboard
```

Launch the game, open the SGL64 mod menu, and choose **Reitz leaderboard**, **Marston leaderboard**, or **Stadium leaderboard**. The popup shows up to five scores from the last refresh. Refresh again while the game is closed to update the snapshot. The command updates only leaderboard keys in `~/Library/Application Support/sm64coopdx/sav/sgl64.sav`; it preserves other mod-storage settings and local run data.

You can still fetch a board directly in the terminal:

```sh
sgl64-bridge leaderboard reitz_rooftop
sgl64-bridge leaderboard marston_climb
```

Use a mission ID from the SGL64 mission catalog. Leaderboard results include unassisted runs.

## Session handling

```sh
sgl64-bridge logout
```

Logout asks DeepSpace to revoke the session, then removes the Keychain item. The bridge never prints tokens. If you change the app URL, run `login` again for that app.

## Scope and limitations

- This is a post-game sync tool. It does not connect to the game while it runs.
- Do not read or modify `.modfs` concurrently with SM64CoopDX. SM64CoopDX documents ModFS as a ZIP-backed save but does not promise external locking or atomic updates.
- OAuth requires the exact redirect URI allowlist above on the deployed worker. A different port or host will fail closed.
- The access token is kept in memory for each command; only the refreshable session token is persisted in Keychain.
- The bridge requires the macOS `unzip` command provided by the system.
