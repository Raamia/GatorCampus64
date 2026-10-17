-- GENERATED FILE: the hosted server's bridge rewrites it on every character deploy
-- (docs/web_platform_spec.md §5.2). Checked in with 8 placeholder slots so the mod always loads.
--
-- Format (keep it exactly one call, one line per slot, slots 1..8 in order):
--   sgl_guests_register({
--       { slot = <n>, name = "<display name, <= 12 printable ASCII chars>", owner = "<Auth0 sub>" or nil },
--   })
-- The model is actors/guest_<n>/ (DynOS: guest_<n>_geo), the card portrait
-- textures/sgl_portrait_guest_<n>.png. sgl_guests_register is defined in characters.lua, which loads
-- before this file (coopdx loads a mod's files in strcmp order: characters < charselect < guests), so
-- the guests are part of the friend list before any hook runs.

sgl_guests_register({
    { slot = 1, name = "Guest 1", owner = nil },
    { slot = 2, name = "Guest 2", owner = nil },
    { slot = 3, name = "Guest 3", owner = nil },
    { slot = 4, name = "Guest 4", owner = nil },
    { slot = 5, name = "Guest 5", owner = nil },
    { slot = 6, name = "Guest 6", owner = nil },
    { slot = 7, name = "Guest 7", owner = nil },
    { slot = 8, name = "Guest 8", owner = nil },
})
