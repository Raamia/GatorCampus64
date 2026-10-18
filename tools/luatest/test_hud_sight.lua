-- Offline test of sgl_hud_in_sight (mods/sgl64/sgl_hud.lua): HUD labels drawn over the world (door labels in the
-- hub, NPC name tags and speech bubbles) are hidden when a wall stands between the camera and the label, because
-- HUD text is drawn on top of everything. Checks the ray, the 95% rule, the per-key cache, the fallbacks when the
-- API is missing, and that levels.lua and sgl_npc.lua call it. Run: lua tools/luatest/test_hud_sight.lua (run.sh).
local HERE = debug.getinfo(1, "S").source:match("^@(.*/)") or "./"
local MOD = HERE .. "../../mods/sgl64/"

local passed, failed = 0, 0
local function check(cond, what)
    if cond then
        passed = passed + 1
    else
        failed = failed + 1
        print("  FAIL " .. what)
    end
end

-- load sgl_hud.lua into a fresh environment with just the globals sgl_hud_in_sight uses
local frame = 0
local rayHit = nil          -- what the stubbed collision_find_surface_on_ray returns
local rays = 0
local function load_hud(env)
    env = env or {}
    setmetatable(env, { __index = _G })
    env.get_global_timer = function() return frame end
    env.hook_event = function() end           -- sgl_hud.lua registers its own hooks at load
    env.HOOK_ON_HUD_RENDER, env.HOOK_ON_LEVEL_INIT, env.HOOK_UPDATE = 1, 2, 3
    if env.collision_find_surface_on_ray == nil then
        env.collision_find_surface_on_ray = function(x, y, z, dx, dy, dz)
            rays = rays + 1
            return rayHit
        end
    end
    if env.gLakituState == nil then
        env.gLakituState = { curPos = { x = 0, y = 0, z = 0 }, curFocus = { x = 0, y = 0, z = 100 } }
    end
    local chunk = assert(loadfile(MOD .. "sgl_hud.lua", "t", env))
    chunk()
    return env
end

local H = load_hud()
local target = { x = 0, y = 0, z = 1000 }   -- 1000 units in front of the camera

rayHit = nil
check(H.sgl_hud_in_sight("a", target) == true, "nothing hit: visible")

frame = 10
rayHit = { surface = {}, hitPos = { x = 0, y = 0, z = 500 } }
check(H.sgl_hud_in_sight("b", target) == false, "a wall half way: hidden")

frame = 20
rayHit = { surface = {}, hitPos = { x = 0, y = 0, z = 970 } }
check(H.sgl_hud_in_sight("c", target) == true, "a hit at 97% (the label's own surroundings): visible")

frame = 30
rayHit = { surface = {}, hitPos = { x = 0, y = 0, z = 900 } }
check(H.sgl_hud_in_sight("d", target) == false, "a hit at 90%: hidden")

frame = 40
rayHit = { surface = {} }
check(H.sgl_hud_in_sight("e", target) == false, "a hit without a position: hidden")

-- cache: one ray per key every few frames
frame = 100
rayHit = nil
rays = 0
check(H.sgl_hud_in_sight("door1", target) == true, "cache: first answer visible")
rayHit = { surface = {}, hitPos = { x = 0, y = 0, z = 500 } }
frame = 102
check(H.sgl_hud_in_sight("door1", target) == true, "cache: same answer 2 frames later")
check(rays == 1, "cache: one ray for two calls within 4 frames (got " .. rays .. ")")
frame = 104
check(H.sgl_hud_in_sight("door1", target) == false, "cache: re-checked after 4 frames")
check(rays == 2, "cache: a second ray after 4 frames (got " .. rays .. ")")
check(H.sgl_hud_in_sight("npc:albert", target) == false, "cache: keys are independent")

-- fallbacks: without the API the labels behave as before (always drawn)
local noRay = load_hud({ collision_find_surface_on_ray = false })
noRay.collision_find_surface_on_ray = nil
check(noRay.sgl_hud_in_sight("x", target) == true, "no collision_find_surface_on_ray: visible")
local noCam = load_hud({ gLakituState = false })
noCam.gLakituState = nil
check(noCam.sgl_hud_in_sight("x", target) == true, "no gLakituState: visible")

-- the two world labels use it
local function read(name)
    local f = assert(io.open(MOD .. name))
    local s = f:read("a")
    f:close()
    return s
end
check(read("levels.lua"):find('sgl_hud_in_sight("door" .. i, pos)', 1, true) ~= nil, "levels.lua: door labels check sight")
check(read("sgl_npc.lua"):find('sgl_hud_in_sight("npc:" .. npc.id, head)', 1, true) ~= nil, "sgl_npc.lua: NPC name tags check sight")

print(string.format("%d checks passed, %d failed", passed, failed))
if failed > 0 then os.exit(1) end
