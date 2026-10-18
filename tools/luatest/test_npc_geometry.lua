-- Live geometry regressions with explicit floors/walls rather than permissive engine stubs.
local HERE = debug.getinfo(1, "S").source:match("^@(.*/)") or "./"
local floor, obstacle
local env = setmetatable({
    gNetworkPlayers = { [0] = { currLevelNum = 1, currAreaIndex = 1 } },
    SGL_NPC_EXCLUSIONS = {}, SGL_NPC_SPOTS = {}, HOOK_ON_HUD_RENDER = 1,
    hook_event = function() end, hook_chat_command = function() end,
    find_floor_height = function(x,y,z) return floor(x,y,z) end,
    collision_find_surface_on_ray = function(x,y,z,dx,dy,dz)
        return { surface = obstacle(x,y,z,dx,dy,dz) and {} or nil }
    end,
}, { __index = _G })
assert(loadfile(HERE .. '../../mods/sgl64/sgl_ambient_geometry.lua', 't', env))()
local count = 0
local function check(value, label) assert(value, label); count = count+1 end
local function reset()
    floor = function() return 0 end
    obstacle = function() return false end
    env.SGL_NPC_EXCLUSIONS = {}
end
local function safe(x,y,z) return env.sgl_npc_safe_position(x,y,z,40,200) end
reset()
check(safe(0,0,0) == 0, 'flat floor supports body')
floor = function(x) return x*0.2 end
check(safe(100,20,0) == 20, 'gentle slope follows real height')
check(math.abs(env.sgl_npc_safe_step(0,0,0,6,0,40,200)-1.2) < 1e-6, 'walking follows slope')
floor = function() return 600 end
check(safe(0,0,0) == nil, 'upper floor cannot replace intended floor')
floor = function() return -11000 end
check(safe(0,0,0) == nil, 'missing floor never spawns')
floor = function() return 100 end
check(safe(0,100,0) == 100, 'map-derived raised anchor is accepted')
check(safe(0,0,0) == nil, 'stale raised anchor is rejected')
floor = function() return -100 end
check(safe(0,-100,0) == -100, 'map-derived lowered anchor is accepted')
reset()
floor = function(x) return x > 25 and -11000 or 0 end
check(safe(0,0,0) == nil, 'footprint must not overhang cliff')
floor = function(x) return x*0.6 end
check(safe(0,0,0) == nil, 'steep slope rejected')
reset()
obstacle = function(x,y,z,dx,dy) return dy > 0 and y < 150 and y+dy >= 150 end
check(safe(0,0,0) == nil, 'low ceiling rejected')
reset()
obstacle = function(x,y,z,dx) return dx ~= 0 and (x-10)*(x+dx-10) <= 0 end
check(safe(0,0,0) == nil, 'wall inside footprint rejected')
reset()
-- A thin diagonal obstacle can miss endpoint body diameters but intersects a sweep ray.
obstacle = function(x,y,z,dx,dy,dz) return dx == 6 and dz == 0 end
check(safe(6,0,0) == 0, 'endpoint clear')
check(env.sgl_npc_safe_step(0,0,0,6,0,40,200) == nil, 'swept body stops at obstacle')
reset()
env.SGL_NPC_EXCLUSIONS = {{level=1, area=1, bounds={-10,-10,-10,10,200,10}}}
check(safe(0,0,0) == nil, 'visual-only exclusion volume blocks placement')
env.SGL_NPC_EXCLUSIONS[1].area = 2
check(safe(0,0,0) == 0, 'exclusions scoped to area')
reset()
floor = function(x) return x > 15 and x < 25 and -11000 or 0 end
check(env.sgl_npc_safe_step(0,0,0,60,0,10,200) == nil, 'sweep cannot jump floor gap')
check(env.sgl_npc_safe_step(0,0,0,1000,0,40,200) == nil, 'teleport is not a walking step')
print('NPC geometry: ' .. count .. ' checks passed')
