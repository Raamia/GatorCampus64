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
        local camera = { zoomed_in_dist = 900, zoomed_out_dist = 1400,
            zoomed_in_height = 300, zoomed_out_height = 450, collisions = 0 }
        for field in pairs(camera) do
            c.stubs["camera_romhack_get_" .. field] = function() return camera[field] end
            c.stubs["camera_romhack_set_" .. field] = function(v) camera[field] = v end
        end
        w:warp(c, HUB, 1, 0)
        c.pos.x, c.pos.z = 8320.25, -4440.5 -- engine Vec3f coordinates, including negative cells
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
    check(#students(F) > 0 and #students(F) <= 12 and #students(H) == 12, "stage visitor keeps the same budget")
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

test("a teleport repopulates even when every candidate is in front of the camera", function()
    local w, H = setup(1)
    w:step(120)
    local cam = H.stubs.gLakituState
    -- From far west all campus paths fall inside the forward cone.
    cam.curPos.x, cam.curPos.z = -1000000, 0
    cam.curFocus.x, cam.curFocus.z = 0, 0
    H.pos.x, H.pos.z = 8391, -16043
    w:step(120)
    check(#students(H) == 12 and farthest_from(H) < 3800, "arrival fallback repopulates at the destination")
    Sim.cmd(H, "crowd", "off")
    w:step(1)
    Sim.cmd(H, "crowd", "on")
    w:step(120)
    check(#students(H) == 0, "after arrival, ordinary spawning still waits for hidden nodes")
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

test("/campus marston follows the actual command and repopulates on the arrival floor", function()
    local w, H, F = setup(2)
    w:step(120)
    check(Sim.cmd(F, "campus", "marston 1 me"), "demo command accepted")
    check(F.level == C.LEVEL_CCM, "command enters Marston")
    -- The simulator does not apply Mario's spawn position automatically.
    F.pos.x, F.pos.y, F.pos.z = -790.5, 0.0, -1510.25
    w:step(120)
    check(#students(F) > 0 and #students(F) <= 12, "Marston arrival has a bounded crowd")
    check(#students(H) == 12 and total(w) <= 24, "hub player retains their share")
    for _, o in ipairs(students(F)) do check(o.oPosY == 0, "arrival crowd stays on the lobby floor") end
    -- Elevator / mission teleport within the same level, with no level-init hook.
    F.pos.x, F.pos.y, F.pos.z = 456, 1800, -2080
    w:step(120)
    check(#students(F) > 0, "crowd follows an upstairs teleport")
    for _, o in ipairs(students(F)) do check(o.oPosY == 1800, "no crowd remains on other floors") end
    check(F.env.sgl_campus_warp("hub", 0, true), "map button uses the same travel function")
    F.pos.x, F.pos.y, F.pos.z = 8320, 0, -4440
    w:step(120)
    check(#students(F) == 12, "return to hub recovers original sidewalk crowd")
end)

test("Reitz instant area transition without level init replaces outdoor routes", function()
    local w, H = setup(1)
    w:warp(H, C.LEVEL_WF, 1, 1)
    H.pos.x, H.pos.y, H.pos.z = 7200, 0, -9300
    w:step(120)
    check(#students(H) > 0, "Reitz outdoor arrival has students")
    -- Model an instant warp: area/position changes but no HOOK_ON_LEVEL_INIT.
    H.area = 2
    local route
    for _, r in ipairs(H.env.SGL_CROWD_AREAS) do
        if r.level == C.LEVEL_WF and r.area == 2 then route = r end
    end
    local n = route.nodes[1]
    H.pos.x, H.pos.y, H.pos.z = n[1], n[2], n[3]
    w:refresh_views()
    w:step(120)
    check(#students(H) > 0 and #students(H) <= 12, "door arrival has interior students")
    for _, o in ipairs(students(H)) do check(o.oPosY == n[2], "indoor crowd is on destination floor") end
end)

test("all demo stage arrivals have nearby routes", function()
    local w, H = setup(1)
    for _, stage in ipairs({{"swamp", "bob"}, {"reitz", "wf"}, {"alice", "jrb"}, {"libwest", "bbh"}}) do
        check(H.env.sgl_campus_warp(stage[1], 1, true), "map travel to " .. stage[1])
        for _, obj in ipairs(Sim.level_script(stage[2]).objects) do
            if obj.bhv == "bhvSpinAirborneWarp" and obj.area == 1 then
                H.pos.x, H.pos.y, H.pos.z = obj.x, obj.y - 100, obj.z
                break
            end
        end
        w:step(120)
        check(#students(H) > 0 and #students(H) <= 12, "crowd at " .. stage[1] .. " arrival")
    end
end)

test("indoor routing respects room walls, separate floors and moving obstacles", function()
    local w, H = setup(1)
    -- Two disconnected rooms on one floor and an overlapping upstairs room.
    -- The nearest room is blocked by a wall; the visible room is farther away.
    H.env.SGL_CROWD_AREAS = {{level = C.LEVEL_CCM, area = 1, indoor = true,
        nodes = {{200,0,0},{400,0,0},{0,0,400},{0,0,600},{0,600,400},{0,600,600}},
        links = {{1,2},{3,4},{5,6}}}}
    local blockAll = false
    H.stubs.collision_find_surface_on_ray = function(x,y,z,dx,dy,dz)
        if (blockAll and not (x == 0 and z == 0)) or (x == 0 and z == 0 and dx > 0) then
            return {surface = {}}
        end
        return {surface = nil}
    end
    w:warp(H, C.LEVEL_CCM, 1, 1)
    H.pos.x, H.pos.y, H.pos.z = 0,0,0
    w:step(120)
    check(#students(H) > 0 and #students(H) <= 2, "small room limits crowd density below quota")
    for _, o in ipairs(students(H)) do
        check(o.oPosX == 0 and o.oPosY == 0 and o.oPosZ >= 400 and o.oPosZ <= 600,
            "only reachable same-floor room receives students")
    end
    blockAll = true
    w:step(6)
    local before = positions(H)
    w:step(30)
    check(#students(H) > 0, "obstacle pauses students rather than removing them")
    for k, p in pairs(positions(H)) do
        check(p[1] == before[k][1] and p[3] == before[k][3], "walker stops for a newly blocking obstacle")
    end
    blockAll = false
    H.stubs.gLakituState.curPos.x = -1000000
    H.stubs.gLakituState.curFocus.x = 0
    H.pos.x, H.pos.z = 600, 0 -- short doorway move, below the teleport threshold
    w:step(120)
    check(#students(H) > 0, "crowd follows a change of room without a warp hook")
    for _, o in ipairs(students(H)) do
        check(o.oPosZ == 0 and o.oPosX >= 200 and o.oPosX <= 400,
            "old unreachable room is retired even when within the distance leash")
    end
end)

print(string.format("test_campus_npcs: %d passed, %d failed", passed, failed))
os.exit(failed == 0 and 0 or 1)
