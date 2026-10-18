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
    check(#H.env.SGL_CROWD == 64, "64 resident slots reuse the existing model library")
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
    -- Use a node on the regenerated outdoor route graph; the old coordinate is no longer
    -- within the graph's spawn radius after the Marston/plaza map rebuild.
    J.pos.x, J.pos.z = -2830, 12497
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
    check(#students(F) <= 12 and #students(H) == 12, "stage visitor stays within their share")
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

test("blocked students wait on safe ground without despawning", function()
    local w, H = setup(1)
    w:step(120)
    local before = students(H)
    check(#before == 12, "crowd populated")
    H.env.sgl_npc_safe_step = function() return nil end
    H.env.sgl_npc_safe_position = function(x, y, z) return y end
    w:step(360)
    local after = students(H)
    check(#after == #before, "blocked crowd stays present")
    local kept = {}
    for _, o in ipairs(after) do kept[o] = true end
    for _, o in ipairs(before) do check(kept[o], "same student survives blocked movement") end
end)

test("outdoor stage visits respect crowd limits, and returning to the hub restores them", function()
    local w, H, F = setup(2)
    w:step(120)
    check(#students(F) == 12, "hub has students before entering a building")
    for _, stage in ipairs({"reitz", "swamp", "alice"}) do
        check(F.env.sgl_campus_warp(stage, 0, true), "travel to " .. stage)
        w:step(120)
        check(#students(F) <= 12, stage .. " uses bounded outdoor walkers")
        F.pos.x, F.pos.y, F.pos.z = 456, 1800, -2080
        w:step(120)
        check(#students(F) <= 12, "teleport respects crowd cap in " .. stage)
        check(#students(H) == 12, "hub player's budget remains stable")
    end
    check(F.env.sgl_campus_warp("hub", 0, true), "return to hub")
    F.pos.x, F.pos.y, F.pos.z = 8320, 0, -4440
    w:step(120)
    check(#students(F) == 12, "outdoor sidewalk crowd returns")
end)

test("area changes immediately clear crowds and generated routes cannot bypass policy", function()
    local w, H = setup(1)
    w:step(120)
    check(#students(H) == 12, "initial hub crowd")
    H.env.SGL_CROWD_AREAS = {{level = HUB, area = 2, indoor = false,
        nodes = H.env.SGL_CAMPUS_ROUTES.nodes, links = H.env.SGL_CAMPUS_ROUTES.links}}
    H.area = 2
    w:refresh_views()
    w:step(1)
    check(#students(H) == 0, "area transition clears existing crowd immediately")
    w:step(120)
    check(#students(H) == 0, "generated route does not enable unsupported hub area")
    for _, area in ipairs({1, 1}) do
        w:warp(H, C.LEVEL_WF, area, 0)
        H.pos.x, H.pos.y, H.pos.z = 7200, 0, -9300
        w:step(120)
        check(#students(H) == 0, "Reitz area " .. area .. " stays crowd-free")
    end
end)

test("indoor residents persist on every floor until the building is left", function()
    for _, building in ipairs({{C.LEVEL_CCM, 1, 5, 4}, {C.LEVEL_BBH, 1, 6, 4}, {C.LEVEL_WF, 2, 8, 8}}) do
        local w, H = setup(1)
        -- Engine collision stub: generated graph supplies the intended floor.
        H.env.sgl_npc_safe_position = function(x, y, z) return y end
        w:warp(H, building[1], building[2], 0)
        w:step(600)
        local before, heights = students(H), {}
        for _, o in ipairs(before) do heights[o.oPosY] = (heights[o.oPosY] or 0) + 1 end
        local floors = 0
        for _, n in pairs(heights) do
            check(n >= (building[4] == 8 and 6 or 4) and n <= building[4], "configured residents per floor: " .. n)
            floors = floors + 1
        end
        check(floors == building[3], "all building floors populated")
        H.pos.x, H.pos.y, H.pos.z = 5000, 1800, 5000
        w:step(600)
        local retained = {}
        for _, o in ipairs(students(H)) do retained[o] = true end
        for _, o in ipairs(before) do check(retained[o], "same resident after elevator/camera/distance change") end
        Sim.cmd(H, "crowd", "off")
        w:step(30)
        check(#students(H) == 0, "explicit crowd off clears residents")
        Sim.cmd(H, "crowd", "on")
        w:step(600)
        check(#students(H) == #before, "explicit crowd on restores residents")
        w:warp(H, HUB, 1, 0)
        H.pos.x, H.pos.y, H.pos.z = 8320, 0, -4440
        w:step(120)
        local outside = {}
        for _, o in ipairs(students(H)) do outside[o] = true end
        for _, o in ipairs(before) do check(not outside[o], "indoor resident removed on exit") end
        check(#students(H) == 12, "outdoor crowd resumes")
    end
end)

test("Reitz exterior has walkers and food court has residents", function()
    local w, H = setup(1)
    w:warp(H, C.LEVEL_WF, 1, 0)
    H.pos.x, H.pos.y, H.pos.z = 7200, 0, -9300
    w:step(150)
    check(#students(H) > 0 and #students(H) <= 12, "Reitz/Malachowsky exterior populated")
    local before = positions(H)
    w:step(60)
    local moved = false
    for k, p in pairs(positions(H)) do
        if before[k] and (p[1] ~= before[k][1] or p[3] ~= before[k][3]) then moved = true end
    end
    check(moved, "outdoor students walk")
    H.env.sgl_npc_safe_position = function(x,y,z) return y end
    w:warp(H, C.LEVEL_WF, 2, 0)
    w:step(600)
    local food = 0
    for _, o in ipairs(students(H)) do
        if o.oPosY == 600 and (o.oPosX-3200)^2 + (o.oPosZ-2500)^2 < 1600^2 then food = food + 1 end
    end
    check(food >= 4, "at least four residents in food court vicinity")
    local exclusions = H.env.SGL_NPC_EXCLUSIONS
    check(exclusions and #exclusions >= 11, "food vendor exclusions loaded")
    for _, o in ipairs(students(H)) do
        for _, box in ipairs(exclusions or {}) do
            local b = box.bounds
            if box.level == C.LEVEL_WF and box.area == 2 then
                check(not (o.oPosX >= b[1] and o.oPosX <= b[4]
                    and o.oPosY >= b[2] and o.oPosY <= b[5]
                    and o.oPosZ >= b[3] and o.oPosZ <= b[6]),
                    "resident stays clear of service counters")
            end
        end
    end
end)

test("unsafe indoor positions do not enter a spawn retry loop", function()
    local w, H = setup(1)
    local probes = 0
    H.env.sgl_npc_safe_position = function() probes = probes + 1; return nil end
    w:warp(H, C.LEVEL_CCM, 1, 0)
    w:step(600)
    check(#students(H) == 0, "unsafe floor never spawns")
    local before = probes
    w:step(600)
    check(probes == before, "no endless retry on rejected positions")
end)

print(string.format("test_campus_npcs: %d passed, %d failed", passed, failed))
os.exit(failed == 0 and 0 or 1)
