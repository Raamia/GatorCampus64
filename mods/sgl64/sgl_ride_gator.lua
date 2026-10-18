-- GatorCampus 64: the ride gator. Koopa shells are drawn as a saddled alligator (actors/koopa_shell replaces
-- the vanilla koopa_shell_geo; tools/actors/make_ride_gator.py), and bhvKoopaShell keeps the ride: jump on to
-- ride, A to hop, Z to get off, it floats on water. While nobody rides it, the vanilla shell spins in place; a
-- spinning gator looks wrong, so this loop (it runs after the native one each frame) undoes the spin and points
-- the gator where it's headed, with a lazy head sway. Ridden, the native loop already faces it along the rider.

SGL_RIDE_GATOR_SWAY_SPEED = 0x180   -- angle units per frame of the idle sway
SGL_RIDE_GATOR_SWAY = 0x900         -- how far the idle sway turns the head either way (about 12.7 degrees)

local function ride_gator_loop(o)
    if o.oAction ~= 0 then return end
    local sway = math.floor(sins((o.oTimer * SGL_RIDE_GATOR_SWAY_SPEED) & 0xFFFF) * SGL_RIDE_GATOR_SWAY)
    o.oFaceAngleYaw = (o.oMoveAngleYaw + sway) & 0xFFFF
end

hook_behavior(id_bhvKoopaShell, OBJ_LIST_LEVEL, false, nil, ride_gator_loop)
