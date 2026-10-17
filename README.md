# Super Gatorlator 64

Our school in Super Mario 64, with online co-op and playable versions of our friends. Built as mods for [sm64coopdx](https://github.com/coop-deluxe/sm64coopdx).

## Setup (macOS)

1. Download `sm64coopdx_macOS_ARM.zip` from the [sm64coopdx releases page](https://github.com/coop-deluxe/sm64coopdx/releases) and unzip `sm64coopdx.app` into this folder.
2. Launch it once and drag your own **US** Super Mario 64 ROM (`.z64`) onto the window. ROMs are not included in this repo.
3. Install our mods:
   ```bash
   ./install-mods.sh
   ```
4. Restart the game, choose **Host**, open **Mods**, enable **Super Gatorlator 64**, and start the game.

## Layout

- `mods/sgl64/` holds the main mod (Lua scripts, plus models and levels later).
- `install-mods.sh` copies `mods/` into the game's mods folder.

## Testing

In game, type `/school` in chat. It should reply with "Super Gatorlator 64 is working!"
