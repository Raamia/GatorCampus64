-- Offline multi-client coverage for the shared player-local campus crowd budget.
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

local function setup(count, dedicated)
    math.randomseed(7421)
    local w = Sim.new({ files = Sim.ALL_FILES, built = Sim.built_on_disk() })
    local clients = {}
    for i = 1, count do
        local c = w:connect("Player " .. i)
        c.stubs.gServerSettings.headlessServer = dedicated and 1 or 0
        c.stubs.mod_fs_hide_errors = function() end
        c.stubs.mod_fs_reload = function() return nil end
        c.stubs.print = function() end
        w:warp(c, HUB, 1, 0)
        c.pos.x, c.pos.z = 8320, -4440
        clients[i] = c
    end
    return w, table.unpack(clients)
end

local function students(c) return Sim.objects_with(c, c.env.id_bhvSglCrowd) end
local function positions(c)
    local out = {}
    for _, o in ipairs(students(c)) do out[o.oBehParams] = { o.oPosX, o.oPosY, o.oPosZ } end
    return out
end
local function farthest_from(c)
    local worst = 0
    for _, o in ipairs(students(c)) do
        worst = math.max(worst, math.sqrt((o.oPosX - c.pos.x)^2 + (o.oPosZ - c.pos.z)^2))
    end
    return worst
end
local function total(w)
    local n = 0
    for _, c in ipairs(w.clients) do if c.connected then n = n + #students(c) end end
    return n
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

test("two players split 24 students; all stay on sidewalks and animate", function()
    local w, H, F = setup(2)
    w:step(120)
    check(#H.env.SGL_CROWD == 40, "40 models remain available for variety")
    check(#students(H) == 12 and #students(F) == 12, "12 local students per player, 24 total")
    check(H.env.sgl_crowd_quota() == 12 and F.env.sgl_crowd_quota() == 12, "equal allocation")
    for _, c in ipairs({H, F}) do
        check(farthest_from(c) <= c.env.SGL_CROWD_AROUND.recycle, "students are nearby")
        for _, o in ipairs(students(c)) do
            check(off_route(c, o.oPosX, o.oPosZ) <= 36, "on a safe sidewalk link")
            local info = Sim.raw(o).header.gfx.animInfo
            check(info.curAnim ~= nil and info.animYTrans == 189, "Mario-rigged animations")
        end
    end
end)

test("one player is capped at 12; growth is at most two per half second", function()
    local w, H = setup(1)
    w:step(1)
    check(#students(H) <= 2, "bounded initial spawn")
    w:step(14)
    check(#students(H) <= 2, "no per-frame spawn burst")
    w:step(150)
    check(#students(H) == 12, "solo cap leaves excess budget unused")
    check(Sim.cmd(H, "crowd", "budget 36"), "host can choose a busier budget")
    w:step(60)
    check(#students(H) == 12, "higher server budget still respects solo cap")
end)

test("joins and departures rebalance without rebuilding retained students", function()
    local w, H, F = setup(2)
    w:step(120)
    local retained = students(H)[1]
    local J = w:connect("Late arrival")
    w:warp(J, HUB, 1, 0)
    J.pos.x, J.pos.z = -1350, 16700
    check(J.env.sgl_crowd_quota() == 0, "late arrival waits for host roster")
    w:step(150)
    check(#students(H) == 8 and #students(F) == 8 and #students(J) == 8, "three equal shares")
    check(total(w) == 24, "total budget preserved after join")
    check(H.env.SGL_CROWD[retained.oBehParams].obj == retained, "retained object keeps its walk")
    check(farthest_from(J) <= J.env.SGL_CROWD_AROUND.hard, "late arrival spawns by their own position")
    w:disconnect(F)
    w:step(150)
    check(#students(H) == 12 and #students(J) == 12, "departure returns equal shares to survivors")
end)

test("twelve human players get two each, headless host gets none", function()
    local w = setup(13, true)
    w:step(120)
    check(#students(w.clients[1]) == 0, "headless process spawns no crowd")
    for i = 2, 13 do
        local c = w.clients[i]
        check(c.env.sgl_crowd_quota() == 2 and #students(c) == 2, "player " .. i .. " gets two")
    end
    check(total(w) == 24, "24 across the entire server")
end)

test("stage visits, local off, and no-path positions do not give others extra shares", function()
    local w, H, F = setup(2)
    w:step(120)
    w:warp(F, C.LEVEL_BOB, 1, 1)
    w:step(60)
    check(#students(F) == 0 and #students(H) == 12, "no students in stages; visitor remains in denominator")
    w:warp(F, HUB, 2, 0)
    w:step(60)
    check(#students(F) == 0, "no outdoor crowd in an unsupported hub area")
    w:warp(F, HUB, 1, 0)
    F.pos.x, F.pos.z = 8320, -4440
    w:step(120)
    check(#students(F) == 12, "return repopulates near the player")
    check(Sim.cmd(F, "crowd", "off"), "local toggle accepted")
    w:step(60)
    check(#students(F) == 0 and #students(H) == 12, "off is local and does not increase host share")
    Sim.cmd(F, "crowd", "on")
    F.pos.x, F.pos.z = 1000000, 1000000
    w:step(120)
    check(#students(F) == 0, "no fallback crowd when far from all sidewalks")
    F.pos.x, F.pos.z = 8320, -4440
    w:step(120)
    check(#students(F) == 12, "recovers when player returns to sidewalks")
end)

test("walking and teleporting keep the crowd near the player", function()
    local w, H = setup(1)
    w:step(120)
    local before = positions(H)
    w:step(600)
    local moved = 0
    for k, p in pairs(positions(H)) do
        local q = before[k]
        if q and math.abs(p[1]-q[1]) + math.abs(p[3]-q[3]) > 100 then moved = moved + 1 end
        check(off_route(H, p[1], p[3]) <= 36, "walking stays on sidewalks")
    end
    check(moved >= 6, "students loiter and stroll rather than freezing")
    H.pos.x, H.pos.z = 8391, -16043
    w:step(120)
    check(#students(H) > 0 and farthest_from(H) <= H.env.SGL_CROWD_AROUND.hard, "relocates to Library West")
    w:step(900)
    check(farthest_from(H) <= H.env.SGL_CROWD_AROUND.hard + 70, "no map-wide drift over time")
    H.pos.y = 10000
    w:step(30)
    check(#students(H) == 0, "no distant crowd beneath a player on a roof")
end)

test("hidden spawning never falls back into view and hard leash removes visible distant NPCs", function()
    local w, H = setup(1)
    w:step(120)
    local cam = H.stubs.gLakituState
    -- From far west all campus paths fall inside the forward cone.
    cam.curPos.x, cam.curPos.z = -1000000, 0
    cam.curFocus.x, cam.curFocus.z = 0, 0
    H.pos.x, H.pos.z = 8391, -16043
    w:step(120)
    check(#students(H) == 0, "old visible crowd removed; no in-view respawn fallback")
    cam.curFocus.x = -2000000
    w:step(120)
    check(#students(H) == 12, "turning away allows hidden spawns")
end)

test("host controls budgets; clients cannot change them; rounding never exceeds budget", function()
    local w, H, F, J = setup(3)
    w:step(120)
    local allocation = H.env.gGlobalSyncTable.sglCrowdAllocation
    Sim.cmd(F, "crowd", "budget 40")
    w:step(30)
    check(H.env.gGlobalSyncTable.sglCrowdAllocation == allocation, "non-host command leaves allocation alone")
    check(Sim.cmd(H, "crowd", "budget 41") == false, "reject over maximum")
    check(Sim.cmd(H, "crowd", "budget -1") == false, "reject negative")
    check(Sim.cmd(H, "crowd", "budget 1.5") == false, "reject fractional")
    check(Sim.cmd(H, "crowd", "sideways") == false, "reject unknown command")
    Sim.cmd(H, "crowd", "budget 10")
    w:step(60)
    check(#students(H) == 3 and #students(F) == 3 and #students(J) == 3, "equal floor division, one unused")
    Sim.cmd(H, "crowd", "budget 0")
    w:step(30)
    check(total(w) == 0, "zero disables crowd for everyone")
    Sim.cmd(H, "crowd", "budget 2")
    w:step(60)
    check(total(w) == 0, "less budget than players does not privilege any player")
    Sim.cmd(H, "crowd", "budget 12")
    w:step(120)
    check(total(w) == 12, "budget restored without warp")
end)

print(string.format("test_campus_npcs: %d passed, %d failed", passed, failed))
os.exit(failed == 0 and 0 or 1)
