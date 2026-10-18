-- Offline test of mods/sgl64/sgl_campus_npcs.lua (the students walking the hub's sidewalks) in the multi-client
-- simulator: every client in the hub spawns the same 24 students in the same places, they walk along the generated
-- sidewalk links (sgl_campus_npc_routes.lua) and keep moving, a player arriving later sees them exactly where the
-- others do (each client fast-forwards from the epoch's start), they only exist in the hub, and /crowd off|on hides
-- and restores them. Run: lua tools/luatest/test_campus_npcs.lua (run.sh).
local HERE = debug.getinfo(1, "S").source:match("^@(.*/)") or "./"
local Sim = dofile(HERE .. "sim.lua")
local C = Sim.C

local passed, failed = 0, 0
local current = "?"

local function check(cond, what)
    if cond then
        passed = passed + 1
    else
        failed = failed + 1
        print("  FAIL [" .. current .. "] " .. what)
    end
    return cond
end

local function test(name, fn)
    current = name
    local before = failed
    local ok, err = xpcall(fn, debug.traceback)
    if not ok then
        failed = failed + 1
        print("  ERROR [" .. name .. "] " .. tostring(err))
    end
    print((failed == before and "PASS " or "FAIL ") .. name)
end

local HUB = C.LEVEL_CASTLE_GROUNDS

-- a host and a friend; clock.t drives get_time() on both (tick() keeps it in step with the frames)
local function setup()
    local w = Sim.new({ files = Sim.ALL_FILES, built = Sim.built_on_disk() })
    local H = w:connect("Host")
    local F = w:connect("Friend")
    local clock = { t = 1800000000 }
    for _, c in ipairs({ H, F }) do c.stubs.get_time = function() return clock.t end end
    local function tick(seconds)
        for _ = 1, seconds do
            w:step(30)
            clock.t = clock.t + 1
        end
    end
    return w, H, F, clock, tick
end

local function students(c) return Sim.objects_with(c, c.env.id_bhvSglCrowd) end

local function positions(c)
    local out = {}
    for _, o in ipairs(students(c)) do
        local s = Sim.raw(o)
        out[s.oBehParams] = { s.oPosX, s.oPosY, s.oPosZ }
    end
    return out
end

-- distance from (x, z) to the nearest sidewalk link
local function off_route(c, x, z)
    local R = c.env.SGL_CAMPUS_ROUTES
    local best = math.huge
    for _, l in ipairs(R.links) do
        local a, b = R.nodes[l[1]], R.nodes[l[2]]
        local dx, dz = b[1] - a[1], b[3] - a[3]
        local t = ((x - a[1]) * dx + (z - a[3]) * dz) / (dx * dx + dz * dz)
        t = math.max(0, math.min(1, t))
        local px, pz = a[1] + dx * t - x, a[3] + dz * t - z
        best = math.min(best, math.sqrt(px * px + pz * pz))
    end
    return best
end

test("every client in the hub sees the same 24 students on the sidewalks", function()
    local w, H, F, _, tick = setup()
    w:warp(H, HUB, 1, 0)
    w:warp(F, HUB, 1, 0)
    tick(2)
    check(#H.env.SGL_CROWD == 24, "24 students load (got " .. #H.env.SGL_CROWD .. ")")
    check(#students(H) == 24 and #students(F) == 24, "24 student objects on each client")
    local ph, pf = positions(H), positions(F)
    local same = true
    for k, p in pairs(ph) do
        local q = pf[k]
        if q == nil or math.abs(p[1] - q[1]) > 0.01 or math.abs(p[3] - q[3]) > 0.01 then same = false end
    end
    check(same, "host and friend place every student identically")
    local worst = 0
    for _, p in pairs(ph) do worst = math.max(worst, off_route(H, p[1], p[3])) end
    check(worst <= 36, string.format("every student is on a sidewalk link (worst %.0f units off)", worst))
    for _, o in ipairs(students(H)) do
        local info = Sim.raw(o).header.gfx.animInfo
        if not check(info.curAnim ~= nil and info.animYTrans == 189, "students play Mario's animations") then break end
    end
end)

test("they keep walking, and stay on the sidewalks", function()
    local w, H, _, _, tick = setup()
    w:warp(H, HUB, 1, 0)
    tick(1)
    local before = positions(H)
    tick(20)
    local after = positions(H)
    local moved, worst = 0, 0
    for k, p in pairs(after) do
        local q = before[k]
        if math.abs(p[1] - q[1]) + math.abs(p[3] - q[3]) > 200 then moved = moved + 1 end
        worst = math.max(worst, off_route(H, p[1], p[3]))
    end
    check(moved >= 18, "most students walked somewhere in 20 s (" .. moved .. " of 24)")
    check(worst <= 36, string.format("still on the sidewalks (worst %.0f units off)", worst))
end)

test("a player arriving later sees them where everyone else does", function()
    local w, H, F, _, tick = setup()
    w:warp(H, HUB, 1, 0)
    w:warp(F, C.LEVEL_BOB, 1, 1)
    tick(1)
    check(#students(F) == 0, "no students outside the hub")
    tick(95)
    w:warp(F, HUB, 1, 0)
    w:step(1)   -- both spawned / stepped this frame
    local ph, pf = positions(H), positions(F)
    local worst = 0
    for k, p in pairs(ph) do
        local q = pf[k]
        worst = math.max(worst, q and math.abs(p[1] - q[1]) + math.abs(p[3] - q[3]) or math.huge)
    end
    check(worst < 20, string.format("late arrival matches the host (worst %.1f units apart)", worst))
end)

test("/crowd off hides them and /crowd on brings them back", function()
    local w, H, F, _, tick = setup()
    w:warp(H, HUB, 1, 0)
    w:warp(F, HUB, 1, 0)
    tick(1)
    check(Sim.cmd(H, "crowd", "off") == true, "/crowd off accepted")
    w:step(1)
    check(#students(H) == 0, "no students after /crowd off")
    check(#students(F) == 24, "only the local client hides them")
    check(Sim.cmd(H, "crowd", "on") == true, "/crowd on accepted")
    w:step(1)
    check(#students(H) == 24, "24 students after /crowd on")
    check(Sim.cmd(H, "crowd", "sideways") == false, "unknown argument shows the usage")
end)

print(string.format("test_campus_npcs: %d passed, %d failed", passed, failed))
os.exit(failed == 0 and 0 or 1)
