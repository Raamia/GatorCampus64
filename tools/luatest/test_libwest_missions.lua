-- Unit + scenario tests for mods/sgl64/uf_west_library_missions.lua (course 5, Library West After Dark, LEVEL_BBH) in
-- the offline multi-client coopdx simulation (sim.lua), plus the act-select / level-script contract for course 5
-- (docs/flow.md 5.1) against the real course.lua and, once built, the real levels/bbh/script.c.
-- Run: tools/luatest/run.sh   (or: lua tools/luatest/test_libwest_missions.lua)
--
-- The engine names only these missions use are stubbed here, per client (prep below), and each one is checked to be a
-- real sm64coopdx v1.5.1 binding first: hurt_and_set_mario_action (a Boo's touch), collision_find_surface_on_ray (the
-- lantern's line of sight: c.walls = { { x0, z0, x1, z1 }, ... } are the vertical walls a ray hits), the lighting
-- engine's le_add_light / le_set_light_pos / le_remove_light (the optional lantern light) and the rom-hack camera
-- getters / setters (levels.lua, whole-mod test). MarioState.marioBodyState is a plain table per player (the role
-- model states). The fix-round tests stub gLakituState (curPos / curFocus) per client for the act 3 nametag hook and
-- make spawn_non_sync_object return nil for some models (a full object pool).
local HERE = debug.getinfo(1, "S").source:match("^@(.*/)") or "./"
local Sim = dofile(HERE .. "sim.lua")
local API = dofile(HERE .. "coopdx_api_v151.lua")
local C = Sim.C
local raw = Sim.raw

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

local BBH, HUB = C.LEVEL_BBH, C.LEVEL_CASTLE_GROUNDS
local MS = { IDLE = 0, WAITING = 1, INTRO = 2, ACTIVE = 3, SUCCESS = 4, FAILED = 5, DONE = 6 }
local PH = { SETUP = 0, HIDE = 1, SEEK = 2, OVER = 3, NEXT = 4 }
local FILE = "uf_west_library_missions.lua"
local FILES = { "course.lua", "sgl_deepspace.lua", "sgl_hud.lua", "sgl_mission.lua", FILE }
local PTOP = 26

for _, n in ipairs({ "hurt_and_set_mario_action", "collision_find_surface_on_ray", "le_add_light", "le_set_light_pos",
    "le_remove_light", "obj_init_animation" }) do
    assert(API[n] ~= nil, n .. " is a v1.5.1 binding")
end

-- coopdx v1.5.1 romhack_camera_init_settings defaults (levels.lua's interior camera, whole-mod test)
local CAM_FIELDS = { { "zoomed_in_dist", "inDist" }, { "zoomed_out_dist", "outDist" }, { "zoomed_in_height", "inHeight" },
    { "zoomed_out_height", "outHeight" }, { "collisions", "collisions" } }

-- does the segment (ax, az) -> (bx, bz) cross the wall segment w? -> t along a -> b, or nil
local function cross(ax, az, bx, bz, w)
    local rx, rz = bx - ax, bz - az
    local sx, sz = w.x1 - w.x0, w.z1 - w.z0
    local den = rx * sz - rz * sx
    if math.abs(den) < 1e-9 then return nil end
    local t = ((w.x0 - ax) * sz - (w.z0 - az) * sx) / den
    local u = ((w.x0 - ax) * rz - (w.z0 - az) * rx) / den
    if t >= 0 and t <= 1 and u >= 0 and u <= 1 then return t end
    return nil
end

local function prep(c)
    local S = c.stubs
    S.hurt_and_set_mario_action = function(m, action, arg, hurt)
        assert(math.type(action) == "integer" and math.type(arg) == "integer" and math.type(hurt) == "integer")
        raw(m).action = action
        raw(m).hurtCounter = hurt
        if raw(m).playerIndex == 0 then c.action = action end
        c.hurts = (c.hurts or 0) + 1
        c.lastHurt = hurt
        return 1
    end
    S.collision_find_surface_on_ray = function(x, y, z, dx, dy, dz)
        assert(type(x) == "number" and type(dz) == "number", "collision_find_surface_on_ray(numbers)")
        c.rays = (c.rays or 0) + 1
        local best = nil
        for _, wl in ipairs(c.walls or {}) do
            local t = cross(x, z, x + dx, z + dz, wl)
            if t ~= nil and (best == nil or t < best) then best = t end
        end
        if best ~= nil then
            return { surface = { type = 0 }, hitPos = { x = x + dx * best, y = y + dy * best, z = z + dz * best } }
        end
        return { surface = nil, hitPos = { x = x + dx, y = y + dy, z = z + dz } }
    end
    c.lights, c.lightN = 0, 0
    S.le_add_light = function(x, y, z, r, g, b, radius, intensity)
        assert(type(x) == "number" and math.type(r) == "integer" and type(radius) == "number" and type(intensity) == "number")
        c.lights = c.lights + 1
        c.lightN = c.lightN + 1
        return c.lightN
    end
    S.le_set_light_pos = function(id, x, y, z) assert(math.type(id) == "integer" and type(z) == "number") end
    S.le_remove_light = function(id)
        assert(math.type(id) == "integer")
        c.lights = c.lights - 1
    end
    S.obj_init_animation = function(o, i) assert(math.type(i) == "integer") end
    S.gObjectAnimations = { toad_seg6_anims_0600FB58 = "ANIM:toad", bookend_seg5_anims_05002540 = "ANIM:bookend",
        sushi_seg5_anims_0500AE54 = "ANIM:sushi", swoop_seg6_anims_060070D0 = "ANIM:swoop" }
    c.cam = { inDist = 900, outDist = 1400, inHeight = 300, outHeight = 450, collisions = 0, sets = 0 }
    for _, f in ipairs(CAM_FIELDS) do
        S["camera_romhack_get_" .. f[1]] = function() return c.cam[f[2]] end
        S["camera_romhack_set_" .. f[1]] = function(v)
            assert(math.type(v) == "integer")
            c.cam[f[2]] = v
            c.cam.sets = c.cam.sets + 1
        end
    end
    for i = 0, C.MAX_PLAYERS - 1 do raw(c.ms[i]).marioBodyState = { modelState = 0 } end
    local m = raw(c.ms[0])
    m.invincTimer, m.hurtCounter, m.flags = 0, 0, 0
    return c
end

-- connect players named A, B, ... (gi 0, 1, ...) with Library West built; they sync in the hub
local function world_with(names, opts)
    opts = opts or {}
    opts.files = opts.files or FILES
    opts.built = opts.built or { [HUB] = true, [C.LEVEL_BOB] = true, [BBH] = true }
    local w = Sim.new(opts)
    local cs = {}
    for _, n in ipairs(names) do table.insert(cs, prep(w:connect(n))) end
    w:step(3)
    return w, table.unpack(cs)
end

local function enter(w, c, act) w:warp(c, BBH, 1, act) end

local function at(c, p, dy)
    c.pos.x, c.pos.y, c.pos.z = p.x, p.y + (dy or 0), p.z
end

local function ctx_of(c) return Sim.ctx(c) end

local function state(c)
    local ctx = ctx_of(c)
    return ctx and ctx.s or nil
end

local function def_of(c, act) return c.env.sgl_mission_get(BBH, act) end

local function act_as(c, action, fvel)
    c.action = action
    raw(c.ms[0]).forwardVel = fvel or 0
end

local function d2(a, b) return math.sqrt((a.x - b.x) ^ 2 + (a.z - b.z) ^ 2) end

local function popcount(v)
    local n = 0
    while v > 0 do
        n = n + (v & 1)
        v = v >> 1
    end
    return n
end

-- my view of another client's Mario (its local index on my client)
local function view(c, other) return c.ms[c.liOf[other.gi]] end

local function props_with_model(c, model)
    local out = {}
    for _, o in ipairs(Sim.objects_with(c, c.env.id_bhvSglLibwestProp)) do
        if raw(o)._model == model then table.insert(out, o) end
    end
    return out
end

local function hidden(o) return (raw(o).header.gfx.node.flags & C.GRAPH_RENDER_INVISIBLE) ~= 0 end

---------------------------------------------------------------------------------------------
-- registry, act names, act select, level script, coordinates
---------------------------------------------------------------------------------------------
test("registry: three Library West missions on acts 1/2/3, star ids act-1, titles = course.lua act names, acts 4-6 coming soon", function()
    local w, A = world_with({ "A" })
    local env = A.env
    local d1, d2_, d3 = def_of(A, 1), def_of(A, 2), def_of(A, 3)
    check(d1 and d1.id == "libwest_allnighter" and d1.starId == 0 and d1.minPlayers == 1, "act 1 all-nighter, star 0, solo")
    check(d2_ and d2_.id == "libwest_coffee" and d2_.starId == 1 and d2_.minPlayers == 1, "act 2 coffee run, star 1, solo")
    check(d3 and d3.id == "libwest_hideseek" and d3.starId == 2 and d3.minPlayers == 2, "act 3 hide and seek, star 2, 2+ players")
    local stage = env.sgl_stage_by_level(BBH)
    check(stage ~= nil and stage.key == "libwest" and stage.door == 5 and stage.course == C.COURSE_BBH and stage.slot == "bbh"
        and stage.acts ~= nil, "course.lua: door 5 = LIBRARY WEST AFTER DARK (COURSE_BBH, slot bbh) with act names")
    for _, d in ipairs({ d1, d2_, d3 }) do
        check((d.bparams >> 24) == d.starId, d.id .. " bparams carry the star id")
        check(stage.acts[d.act] == d.title, d.id .. " title matches course.lua act " .. d.act .. " (" .. tostring(stage.acts[d.act]) .. ")")
        check(not env.sgl_act_is_soon(stage, d.act), d.id .. " act is not 'coming soon'")
        check(d.probes ~= nil and #d.probes >= 3, d.id .. " has geometry probes")
        check(#d.objective <= 60, d.id .. " objective fits the banner (" .. #d.objective .. " chars)")
        check(d.pointsFile ~= nil and d.pointsFile:find(FILE, 1, true) ~= nil, d.id .. " names its points file")
        check(not d.levelStar, d.id .. " spawns its own star")
    end
    for act = 4, 6 do
        check(env.sgl_mission_get(BBH, act) == nil, "act " .. act .. " has no mission yet")
        check(env.sgl_act_is_soon(stage, act) and stage.acts[act]:find("^COMING SOON") ~= nil,
            "act " .. act .. " is named COMING SOON: " .. tostring(stage.acts[act]))
    end
    for act = 1, 6 do
        check(not stage.acts[act]:find("[^A-Z0-9 '%.,%-&!%?]") and #stage.acts[act] <= 28,
            "act " .. act .. " name fits the act-select menu font: " .. stage.acts[act])
    end
    check(#env.SGL_MISSION_LIST == 3 and env.LIBWEST_MISSION_ACTS.hideseek == 3, "3 Library West missions")
    check(env.sgl_party_location_text(BBH, 3) == "LIBRARY WEST AFTER DARK - Act 3: QUIET HOURS HIDE & SEEK - 2P",
        "player-list location text")
    check(Sim.cmd(A, "mission", "list") and Sim.find(A.chat, "libwest_hideseek: level " .. BBH .. " act 3 %(star 2%)") ~= nil,
        "/mission list shows the Library West missions")
end)

test("act select (star_select.c): an empty save reaches acts 1, 2, 3 in turn; the solo acts come first", function()
    local w, A = world_with({ "A" })
    local flags, playable = 0, 0
    for k = 1, 6 do
        if def_of(A, k) ~= nil then
            check(playable == k - 1, "playable acts have no gap (act " .. k .. ")")
            playable = k
        end
    end
    check(playable == 3, "3 playable acts")
    for k = 1, playable do
        local acts = Sim.selectable_acts(flags)
        check(acts[#acts] == k, "act " .. k .. " selectable after acts 1.." .. (k - 1))
        flags = flags | (1 << (k - 1))
    end
    check(def_of(A, 1).minPlayers == 1 and def_of(A, 2).minPlayers == 1 and def_of(A, 3).minPlayers == 2,
        "the co-op act is last, so it never holds up a solo player")
end)

test("levels/bbh/script.c (when built): warp contract for door 5, no level-script star for acts 1-3", function()
    local ls = Sim.level_script("bbh")
    if ls == nil then
        print("  (levels/bbh not built: skipped)")
        return
    end
    local function node(n)
        local wn = ls.warps[n]
        return wn and C[wn.level], wn and wn.node
    end
    local l0, n0 = node(0x0A)
    local l1, n1 = node(0xF0)
    local l2, n2 = node(0xF1)
    check(l0 == BBH and n0 == 0x0A, "BBH 0x0A = own entry spawn")
    check(l1 == HUB and n1 == 0x25, "BBH 0xF0 -> hub 0x25 (outside the Library West door)")
    check(l2 == HUB and n2 == 0x35, "BBH 0xF1 -> hub 0x35")
    for _, o in ipairs(ls.objects) do
        if o.bhv == "bhvStar" then
            check((o.acts & 0x07) == 0, string.format("no level-script star in acts 1-3 (found id %d, acts 0x%02X)",
                (o.bparams or 0) >> 24, o.acts))
        end
    end
    -- Ambient Goombas were removed map-wide while the UF-rivalry replacement is being made.
    local w, A = world_with({ "A" })
    local goombas = 0
    for _, o in ipairs(ls.objects) do
        if o.bhv == "bhvGoomba" then goombas = goombas + 1 end
    end
    check(goombas == 0, string.format("no Goombas remain in the Library West level script (%d found)", goombas))
end)

test("LIBWEST_POINTS: inside s16, floors 6 m apart, star humps under the ceilings, the arena, ladders beside their ranges", function()
    local w, A = world_with({ "A" })
    local env = A.env
    local P = env.LIBWEST_POINTS
    local bad = 0
    local function each(v, name)
        if type(v) == "table" then
            for k, x in pairs(v) do each(x, name .. "." .. tostring(k)) end
        elseif type(v) == "number" and math.abs(v) > 32767 then
            bad = bad + 1
            print("  out of s16: " .. name .. " = " .. v)
        end
    end
    each(P, "LIBWEST_POINTS")
    check(bad == 0, "every coordinate fits SM64's s16 range")
    for k = 1, 6 do check(P["y_f" .. k] == (k - 1) * 600, "floor " .. k .. " at " .. (k - 1) * 6 .. " m") end
    check(P.spawn.y == P.y_f1 and P.climb_goal.y == P.y_f6 and P.run_start.y == P.y_f6 and P.desk.y == P.y_f2,
        "spawn on F1, the climb's goal and the coffee desk on F6, the librarian's desk on F2")
    -- a spawned star rises from starFrom to star: its hump peaks at their middle + 4 m (+ the star's size)
    for act = 1, 3 do
        local d = def_of(A, act)
        local floor = P["y_f" .. (math.floor(d.starFrom.y / 600) + 1)]
        local peak = (d.star.y + d.starFrom.y) / 2 + 400 + 60
        check(peak <= floor + P.clear, string.format("act %d: the star's hump (%.0f) stays under the ceiling (%d)", act, peak,
            floor + P.clear))
        check(d.star.y >= d.starFrom.y and d2(d.star, d.starFrom) < 200, "act " .. act .. ": the star rises close to its spot")
    end
    check(#P.stair_doors == 7, "7 act 1 barriers (the F1-F3 doors of the west and east stair halls)")
    for _, dr in ipairs(P.stair_doors) do
        check(dr.y <= P.y_f3 and (dr.x0 == dr.x1 or dr.z0 == dr.z1), "barrier door on F1-F3, axis-aligned")
        check(env.sgl_libwest_climb_route ~= nil, "route function exported")
    end
    check(#P.boos1 == 7 and #P.boos2 == 4 and #P.ladders == 4 and #P.hide_spots == 8, "7 + 4 Boos, 4 ladders, 8 hiding spots")
    for _, b in ipairs(P.boos2) do
        check(b.y % 600 == 300 and (b.y // 600) >= 1 and (b.y // 600) <= 4, b.name .. ": a turn landing between 2F and 6F")
    end
    for _, ld in ipairs(P.ladders) do
        check(ld.x1 - ld.x0 >= 400 and (ld.y == P.y_f2 + 150 or ld.y == P.y_f3 + 150), "a ladder track >= 4 m with its step 1.5 m up")
    end
    -- hide and seek: releases and spots inside the arena on F1-F3, the desk outside
    check(env.sgl_libwest_in_arena(P.release_w, 0x2) and env.sgl_libwest_in_arena(P.release_e, 0x2), "releases in the 2F arena")
    check(not env.sgl_libwest_in_arena(P.desk, 0x7), "the librarian's desk is outside the arena")
    for _, s in ipairs(P.hide_spots) do
        local k = s.y // 600 + 1
        check(env.sgl_libwest_in_arena(s, 1 << (k - 1)) and not env.sgl_libwest_in_arena(s, 0x7 & ~(1 << (k - 1))),
            s.name .. ": in the arena on its own floor only")
    end
    check(not env.sgl_libwest_in_arena({ x = 0, y = P.y_f4, z = -2000 }, 0x7), "the roof terrace is out of bounds")
end)

---------------------------------------------------------------------------------------------
-- act 1: ALL-NIGHTER
---------------------------------------------------------------------------------------------
test("act 1 solo: barriers on the 7 stair doors + the 5F staff doors, ladders, Boos; the route; the window -> one star -> DONE", function()
    local w, A = world_with({ "A" })
    local env = A.env
    local P = env.LIBWEST_POINTS
    enter(w, A, 1)
    at(A, P.spawn)
    w:step(3)
    check(Sim.hud_has(A, "ALL%-NIGHTER") and Sim.hud_has(A, "LIBRARY WEST AFTER DARK %- ACT 1"), "act banner")
    check(Sim.find(A.console, "sleeps") == nil, "probes pass")
    local solids = Sim.objects_with(A, env.id_bhvSglLibwestSolid)
    check(#solids == 9, #solids .. " barrier collision boxes (7 stair doors below 4F + the 2 staff-only doors on 5F)")
    local ctx = ctx_of(A)
    local doors = {}
    for _, d in ipairs(P.stair_doors) do table.insert(doors, d) end
    for _, d in ipairs(P.staff_doors) do table.insert(doors, d) end
    for i, d in ipairs(doors) do
        local rec = ctx.objs.barriers[i]
        check(rec.label == (i <= 7 and "CLOSED FOR CLEANING" or "STAFF ONLY"), "door " .. i .. " label " .. tostring(rec.label))
        local o = raw(rec.o)
        local cx, cz = (d.x0 + d.x1) / 2, (d.z0 + d.z1) / 2
        local alongX = math.abs(d.x1 - d.x0) >= math.abs(d.z1 - d.z0)
        local width = alongX and math.abs(d.x1 - d.x0) or math.abs(d.z1 - d.z0)
        local half = o.header.gfx.scale.x * 256
        check(o.collisionData == "COL:checkerboard_platform" and o.oPosX == cx and o.oPosZ == cz and half >= width / 2 + 29
            and o.oFaceAngleYaw == (alongX and 0 or 0x4000), string.format("door %d covered (half %.0f for %d)", i, half, width))
        local bottom = o.oPosY - 25 * o.header.gfx.scale.y
        check(math.abs(bottom - d.y) < 1 and 51 * o.header.gfx.scale.y >= 490, "door " .. i .. ": from the floor, 5 m tall")
    end
    local ladders = Sim.objects_with(A, env.id_bhvSglLibwestLadder)
    check(#ladders == 4 and raw(ladders[1])._model == C.E_MODEL_CHECKERBOARD_PLATFORM
        and raw(ladders[1]).collisionData == "COL:checkerboard_platform", "4 rolling ladders (checkerboard collision)")
    check(#ctx.objs.boos == 7 and #props_with_model(A, rawget(A.env, "SGL_KNIGHT_GHOST_MODEL") or C.E_MODEL_BOO) == 7,
        "7 sleepy Knight ghosts (the Boos' stand-in model)")
    w:seconds(3.5)
    check(state(A) == MS.ACTIVE and ctx.isLeader, "solo: active, leader")
    check(Sim.hud_has(A, "ESCALATOR UP"), "lobby: marker ESCALATOR UP")
    -- by a closed door: the label
    local dr = P.stair_doors[2]                        -- the west hall's F2 door
    at(A, { x = dr.x0 - 200, y = dr.y, z = (dr.z0 + dr.z1) / 2 })
    w:step(2)
    check(Sim.hud_has(A, "CLOSED FOR CLEANING"), "a closed stair door says so")
    at(A, P.esc_top)
    w:step(3)
    check((ctx.f & 1) ~= 0 and Sim.hud_has(A, "STAIR TO THE ROOF"), "on 2F: milestone 1, marker to a north stair")
    check(Sim.hud_has(A, "OUT%-OF%-ORDER SHAFT"), "the out-of-order elevator shaft is marked on 2F (the wall-kick alternative)")
    at(A, { x = P.door_nw.x - 200, y = P.y_f3, z = P.door_nw.z })
    w:step(2)
    check(Sim.hud_has(A, "NW STAIR TO THE ROOF"), "on 3F by the NW stair: that stair")
    at(A, { x = (P.hall_nw.x0 + P.hall_nw.x1) / 2, y = P.y_f2 + 300, z = (P.hall_nw.z0 + P.hall_nw.z1) / 2 })
    w:step(2)
    check(Sim.hud_has(A, "ROOF DOOR"), "inside the NW stair tower: ROOF DOOR")
    at(A, { x = 0, y = P.y_f4, z = -1500 })            -- the north roof terrace
    w:step(3)
    check((ctx.f & 2) ~= 0 and Sim.hud_has(A, "4TH FLOOR DOOR"), "on the roof terrace: milestone 2, marker 4TH FLOOR DOOR")
    at(A, { x = 0, y = P.y_f4, z = 1200 })             -- inside the tower's 4th floor
    w:step(2)
    check(Sim.hud_has(A, "STAIRS UP TO 6F"), "on the quiet floor: STAIRS UP TO 6F")
    at(A, { x = P.land_w.x, y = P.y_f5, z = P.land_w.z })
    w:step(2)
    check(Sim.hud_has(A, "6TH FLOOR") and Sim.hud_has(A, "STAFF ONLY"), "in the west stair hall at 5F: 6TH FLOOR; its door STAFF ONLY")
    at(A, P.f6_door_w)
    w:step(3)
    check((ctx.f & 4) ~= 0 and Sim.hud_has(A, "THE BIG WINDOW") and state(A) == MS.ACTIVE, "on 6F: milestone 3, the goal marker")
    check(ctx.p == 30, "team best 30 m")
    at(A, P.climb_goal)
    w:step(3)
    check(state(A) == MS.SUCCESS, "at the big window: success")
    w:step(3)
    check(#A.starSpawns == 1 and Sim.stars_of(A, 0) == 1, "one spawned star (id 0)")
    local sp = A.starSpawns[1]
    check(sp and sp.x == P.climb_star.x and sp.y == P.climb_star.y and sp.z == P.climb_star.z, "star at the big window")
    check(sp and sp.from.y == P.y_f6 and sp.from.x == P.climb_star.x, "it rises out of the floor below it")
    local star = Sim.objects_with(A, C.id_bhvStarSpawnCoordinates)[1]
    Sim.run_hooks(A, C.HOOK_ON_INTERACT, A.ms[0], star, C.INTERACT_STAR_OR_KEY, true)
    raw(star).activeFlags = C.ACTIVE_FLAG_DEACTIVATED
    w:step(4)
    check(state(A) == MS.DONE and Sim.stars_of(A, 0) == 0, "DONE, no respawn")
end)

test("act 1 route (pure): the forced climb, including the 1st-floor stacks and the halls above 4F", function()
    local w, A = world_with({ "A" })
    local env = A.env
    local P = env.LIBWEST_POINTS
    local R = env.sgl_libwest_climb_route
    local function label(p) local _, l = R(p) return l end
    check(label(P.spawn) == "ESCALATOR UP", "the lobby -> the escalator")
    check(label({ x = 0, y = 0, z = -2000 }):find("STAIR") ~= nil and R({ x = 0, y = 0, z = -2000 }).y == P.y_f1,
        "the 1st-floor stacks (reached down a north stair) -> back to a north stair, not the lobby's escalator")
    check(label({ x = -2500, y = P.y_f2, z = -1500 }) == "NW STAIR TO THE ROOF", "west stacks -> NW stair")
    check(label({ x = 2500, y = P.y_f2, z = -1500 }) == "NE STAIR TO THE ROOF", "east stacks -> NE stair")
    local pos, l = R({ x = (P.hall_ne.x0 + P.hall_ne.x1) / 2, y = P.y_f3 + 300, z = (P.hall_ne.z0 + P.hall_ne.z1) / 2 })
    check(l == "ROOF DOOR" and pos.y == P.y_f4 and pos.x == P.door_ne.x, "NE tower -> its roof door on the terrace")
    check(label({ x = -2500, y = P.y_f4, z = 2400 }) == "STAIRS UP TO 6F", "the quiet floor's west part -> a stair hall")
    pos = R({ x = 2500, y = P.y_f4, z = 2400 })
    check(pos == P.f4_door_e, "the quiet floor's east part -> the east hall")
    check(label({ x = 3500, y = P.y_f4, z = 2400 }) == "4TH FLOOR DOOR", "the east roof terrace -> the tower door")
    pos, l = R({ x = P.land_e.x, y = P.y_f4 + 300, z = P.land_e.z })
    check(l == "6TH FLOOR" and pos == P.f6_door_e, "in the east hall above 4F -> its 6th-floor door")
    check(R(P.climb_goal) == nil, "on 6F: the goal")
end)

test("rolling ladders: a pure function of the area timer, the same on two clients, carrying their rider, catching up", function()
    local w, A, B = world_with({ "A", "B" })
    local env = A.env
    local L = env.SGL_LIBWEST_LADDER
    local x0, x1 = -890, -190
    local a, b = x0 + L.HALF_X, x1 - L.HALF_X
    local move = math.ceil((b - a) / L.SPEED)
    check(env.sgl_libwest_ladder_x(0, x0, x1, 0) == a and env.sgl_libwest_ladder_x(L.WAIT - 1, x0, x1, 0) == a, "waits at one end")
    check(env.sgl_libwest_ladder_x(L.WAIT + move, x0, x1, 0) == b, "reaches the other end")
    check(env.sgl_libwest_ladder_x(2 * (L.WAIT + move), x0, x1, 0) == a, "and comes back")
    local prev, maxStep, inside = nil, 0, true
    for t = 0, 4 * (L.WAIT + move) do
        local x = env.sgl_libwest_ladder_x(t, x0, x1, 0)
        if x < a or x > b then inside = false end
        if prev ~= nil then maxStep = math.max(maxStep, math.abs(x - prev)) end
        prev = x
    end
    check(inside and maxStep <= L.SPEED, "inside its track (deck within the range's length), <= SPEED a frame")
    check(env.sgl_libwest_ladder_step(100, 200) == 112 and env.sgl_libwest_ladder_step(nil, 150) == 150, "catch-up limit 12")
    local P = env.LIBWEST_POINTS
    enter(w, A, 1); enter(w, B, 1)
    at(A, P.spawn); at(B, P.spawn)
    w:seconds(4)
    local same, moved = true, false
    for _ = 1, 300 do
        w:step(1)
        for i = 1, 4 do
            local ra, rb = raw(ctx_of(A).objs.ladders[i].o), raw(ctx_of(B).objs.ladders[i].o)
            if ra.oPosX ~= rb.oPosX then same = false end
            if ra.oVelX ~= 0 then moved = true end
            if ra.oPosY + PTOP ~= P.ladders[i].y or ra.oPosZ ~= P.ladders[i].z then same = false end
        end
    end
    check(same and moved, "both clients show every ladder at the same place, its step at 1.5 m, moving (oVelX = the step)")
    B.areaTimerOffset = 200
    local maxB, prevB = 0, raw(ctx_of(B).objs.ladders[1].o).oPosX
    for _ = 1, 60 do
        w:step(1)
        local x = raw(ctx_of(B).objs.ladders[1].o).oPosX
        maxB = math.max(maxB, math.abs(x - prevB))
        prevB = x
    end
    check(maxB <= 12, "after a timer jump a ladder moves at most 12 units a frame (" .. maxB .. ")")
end)

test("sleepy Boos (pure): doze far away, chase a turned back, freeze see-through when faced, leash, touch", function()
    local w, A = world_with({ "A" })
    local env = A.env
    local B = env.SGL_LIBWEST_BOO
    local step = env.sgl_libwest_boo_step
    local b = { hx = 0, hy = 0, hz = 0, x = 0, y = B.HOVER, z = 0, alpha = 255 }
    step(b, { x = 5000, y = 0, z = 0 }, 0, true)
    check(not b.awake and b.x == 0 and b.z == 0, "far away: dozing at home")
    -- Mario 6 m east facing east: his back is turned -> the Boo drifts after him
    step(b, { x = 600, y = 0, z = 0 }, 0x4000, true)
    check(b.awake and not b.shy and math.abs(b.x - B.SPEED) < 1, "back turned: it drifts after him at SPEED")
    check(b.alpha == 255, "solid")
    local x = b.x
    for _ = 1, 30 do step(b, { x = 600, y = 0, z = 0 }, 0xC000, true) end   -- facing west, at the Boo
    check(b.shy and b.x == x and b.alpha == B.SHY_ALPHA, "faced: it freezes and fades to see-through")
    check(not step(b, { x = 600, y = 0, z = 0 }, 0xC000, false).awake, "a player who cannot be chased (cutscene, dead) wakes nobody")
    for _ = 1, 400 do step(b, { x = 850, y = 0, z = 0 }, 0x4000, true) end
    check(math.abs(b.x - B.LEASH) < 1, "it never strays more than its leash from home (" .. b.x .. ")")
    check(b.y >= B.LOW and b.y <= B.HIGH, "within its floor band")
    check(not step({ hx = 0, hy = 0, hz = 0, x = 0, y = 120, z = 0, alpha = 255 }, { x = 600, y = 1200, z = 0 }, 0x4000, true).awake,
        "a player two floors away wakes nobody")
    check(env.sgl_libwest_boo_touches({ x = 50, y = 80, z = 0 }, { x = 0, y = 0, z = 0 }), "touching at 0.5 m")
    check(not env.sgl_libwest_boo_touches({ x = 200, y = 80, z = 0 }, { x = 0, y = 0, z = 0 }), "not at 2 m")
end)

test("act 1 Boos in the stage: a turned back is touched (a wedge + knock-back), facing it is safe, a punch shoos it for 15 s", function()
    local w, A = world_with({ "A" })
    local env = A.env
    local P = env.LIBWEST_POINTS
    enter(w, A, 1)
    at(A, P.spawn)
    w:seconds(4)
    local ctx = ctx_of(A)
    local boo = ctx.objs.boos[6]                       -- QUIET FLOOR
    -- 3 m east of it, facing it: safe
    at(A, { x = boo.hx + 300, y = boo.hy, z = boo.hz })
    A.face.y = 0xC000
    A.hurts = 0
    w:seconds(2)
    check(boo.shy and (A.hurts or 0) == 0, "faced: frozen and harmless")
    boo.x, boo.y, boo.z = A.pos.x - 80, A.pos.y + 80, A.pos.z      -- right in front of me, see-through
    w:step(5)
    check(boo.shy and boo.alpha < 200 and (A.hurts or 0) == 0, "a see-through Boo touching me does not hurt")
    -- back turned: it comes and touches
    A.face.y = 0x4000
    for _ = 1, 120 do
        w:step(1)
        if (A.hurts or 0) > 0 then break end
    end
    check(A.hurts == 1 and A.lastHurt == 4 and A.action == C.ACT_BACKWARD_GROUND_KB, "touched: one wedge and a knock-back")
    w:step(2)                                          -- (a toast fades in from its 2nd frame)
    check(Sim.find(A.hudLog, "Knight ghost") ~= nil or Sim.hud_has(A, "Knight ghost"), "toast says what it was")
    check(ctx.loc.booHits == 1 and (boo.backoff or 0) > 0, "then it backs off")
    -- a punch from close while it is visible
    act_as(A, C.ACT_IDLE)
    w:seconds(3)
    boo.x, boo.y, boo.z, boo.alpha, boo.backoff = A.pos.x + 100, A.pos.y + 80, A.pos.z, 255, 0
    act_as(A, C.ACT_PUNCHING)
    w:step(2)
    check(boo.gone > 0 and hidden(boo.o) and ctx.loc.booShoos == 1, "punched: shooed away (hidden)")
    act_as(A, C.ACT_IDLE)
    w:seconds(env.SGL_LIBWEST_BOO.RESPAWN / 30 + 0.5)
    check(boo.gone == 0 and not hidden(boo.o), "back home after 15 s")
end)

test("act 1: nothing of it in the other acts; a stage that does not match keeps the missions offline", function()
    local w, A = world_with({ "A" })
    local env = A.env
    enter(w, A, 2)
    w:step(5)
    check(#Sim.objects_with(A, env.id_bhvSglLibwestSolid) == 2 and #Sim.objects_with(A, env.id_bhvSglLibwestLadder) == 0,
        "act 2: only the 2 staff-only doors (no cleaning barriers), no ladders")
    enter(w, A, 3)
    w:step(5)
    check(#Sim.objects_with(A, env.id_bhvSglLibwestSolid) == 2 and #props_with_model(A, C.E_MODEL_BOO) == 0,
        "act 3: the 2 staff-only doors, no Boos")
    enter(w, A, 2)
    w:step(5)
    check(#ctx_of(A).objs.boos == 4, "act 2: its 4 stairwell Boos")
    enter(w, A, 4)
    w:step(5)
    check(Sim.hud_has(A, "COMING SOON %- GHOST HUNT") and #Sim.objects_with(A, env.id_bhvSglLibwestSolid) == 0
        and #props_with_model(A, C.E_MODEL_BOO) == 0, "act 4: coming soon, free roam, no objects of ours")
    local w2, B = world_with({ "B" }, { floor = Sim.NO_FLOOR })
    for act = 1, 3 do
        enter(w2, B, act)
        w2:step(5)
        check(Sim.find(B.console, "sleeps") ~= nil and #Sim.objects_with(B, B.env.id_bhvSglLibwestSolid) == 0
            and #props_with_model(B, C.E_MODEL_BOO) == 0, "act " .. act .. " on a stage without Library West: offline, nothing spawned")
    end
end)

---------------------------------------------------------------------------------------------
-- act 2: COFFEE RUN
---------------------------------------------------------------------------------------------
local function coffee_go(w, cs)
    local P = cs[1].env.LIBWEST_POINTS
    for _, c in ipairs(cs) do enter(w, c, 2) end
    w:seconds(4)
    for _, c in ipairs(cs) do at(c, P.run_start, 20) end
    w:step(3)
    w:seconds(3.2)
end

test("act 2 solo: desk -> stairs -> escalator -> the cup -> back up -> desk under par: star at the desk, PB, cup over the head", function()
    local w, A = world_with({ "A" })
    local env = A.env
    local P = env.LIBWEST_POINTS
    enter(w, A, 2)
    w:seconds(4)
    local ctx = ctx_of(A)
    check(state(A) == MS.ACTIVE and ctx.a == 0 and Sim.hud_has(A, "YOUR DESK %(START%)"), "lobby: the start marker")
    at(A, P.run_start, 20)
    w:step(3)
    check(ctx.a == 1, "in the box: countdown")
    w:seconds(3.2)
    check(ctx.a == 2 and ctx.loc.racing and A.fanfares == 1, "racing")
    check(A.music[1] == ((4 << 8) | C.SEQ_LEVEL_SLIDE), "race music")
    w:step(1)
    check(Sim.hud_has(A, "STAIRS DOWN") and Sim.hud_has(A, "TIME"), "at the desk: STAIRS DOWN, the race timer")
    local function goto_(p, dy, frames) at(A, p, dy); w:step(frames or 2) end
    goto_({ x = P.land_e.x, y = P.y_f4, z = P.land_e.z })
    check(Sim.hud_has(A, "DOWN TO 2F"), "in the east stair hall: DOWN TO 2F")
    goto_({ x = P.land_e.x, y = P.y_f2, z = P.land_e.z })
    check(Sim.hud_has(A, "OUT TO 2F"), "at its 2nd-floor landing: OUT TO 2F")
    goto_(P.f2_door_e)
    check(Sim.hud_has(A, "ESCALATOR DOWN"), "on 2F: ESCALATOR DOWN")
    goto_(P.esc_foot)
    check(Sim.hud_has(A, "COFFEE"), "in the lobby: the coffee marker")
    w:seconds(8)
    goto_(P.cup_stand)
    check(ctx.loc.cp == 2, "the cup is checkpoint 1")
    check(Sim.find(A.hudLog, "Coffee! Now back up") ~= nil or Sim.hud_has(A, "Coffee! Now back up"), "toast: back up")
    local cups = props_with_model(A, C.E_MODEL_BITS_WARP_PIPE)
    local over = false
    for _, o in ipairs(cups) do
        if raw(o).oPosX == A.pos.x and math.abs(raw(o).oPosY - (A.pos.y + 190)) < 1 and not hidden(o) then over = true end
    end
    check(over and #cups >= 2, "a cup over my head (and the counter's own cup)")
    goto_(P.esc_foot)
    check(Sim.hud_has(A, "ESCALATOR UP"), "with the cup in the lobby: ESCALATOR UP")
    goto_(P.esc_top)
    check(Sim.hud_has(A, "STAIRS UP"), "on 2F: a stair hall up")
    goto_({ x = P.land_w.x, y = P.y_f4, z = P.land_w.z })
    check(Sim.hud_has(A, "UP TO 6F"), "in the west hall: UP TO 6F")
    goto_({ x = P.land_w.x, y = P.y_f6, z = P.land_w.z })
    check(Sim.hud_has(A, "OUT TO 6F"), "at its 6th-floor landing: OUT TO 6F")
    goto_(P.f6_door_w)
    check(Sim.hud_has(A, "YOUR DESK"), "on 6F: YOUR DESK")
    w:seconds(10)
    goto_(P.run_start, 20, 3)
    check(ctx.loc.finished ~= nil and ctx.loc.finished < 60 * 30, "finished under par (" .. tostring(ctx.loc.finished) .. ")")
    w:step(3)
    check(state(A) == MS.SUCCESS, "success")
    w:step(2)
    local sp = A.starSpawns[1]
    check(#A.starSpawns == 1 and sp.x == P.run_start.x and sp.y == P.run_start.y + 80 and sp.from.y == P.run_start.y,
        "the star at the desk, rising out of the floor")
    check(A.storage["sgl_lw_coffee_pb"] == ctx.loc.finished, "personal best saved")
    check(Sim.hud_has(A, "COFFEE RUN %- RACE 1"), "results board")
    local stillOver = false
    for _, o in ipairs(props_with_model(A, C.E_MODEL_BITS_WARP_PIPE)) do
        if raw(o).oPosX == A.pos.x and not hidden(o) then stillOver = true end
    end
    check(not stillOver, "no cup over the head after the finish")
end)

test("act 2 with a friend: a race; the friend sees my cup; the stairwell Boos only knock back; over par -> no star", function()
    local w, A, B = world_with({ "A", "B" })
    local env = A.env
    local P = env.LIBWEST_POINTS
    coffee_go(w, { A, B })
    local ctx = ctx_of(A)
    check(ctx.a == 2 and ctx.x == 2, "both race")
    at(A, P.cup_stand)
    w:step(3)
    local seen = false
    for _, o in ipairs(props_with_model(B, C.E_MODEL_BITS_WARP_PIPE)) do
        local mA = view(B, A)
        if raw(o).oPosX == mA.pos.x and math.abs(raw(o).oPosY - (mA.pos.y + 190)) < 1 and not hidden(o) then seen = true end
    end
    check(seen and ctx_of(B).loc.cups[A.gi] == 1, "B draws a cup over A")
    check(Sim.find(B.hudLog, "A has the coffee") ~= nil or Sim.hud_has(B, "A has the coffee"), "B is told")
    -- a stairwell Boo: knock-back, no damage
    local boo = ctx_of(B).objs.boos[1]
    at(B, { x = boo.hx, y = boo.hy, z = boo.hz + 150 })
    B.face.y = 0x0000                                  -- facing south, away from it (it is north)
    B.hurts = 0
    for _ = 1, 90 do
        w:step(1)
        if (B.hurts or 0) > 0 then break end
    end
    check(B.hurts == 1 and B.lastHurt == 0 and B.action == C.ACT_BACKWARD_GROUND_KB, "a stairwell Boo knocks back, no wedge")
    -- over par: nobody gets the star
    w:seconds(61)
    at(A, P.run_start, 20)
    w:step(3)
    check(ctx.loc.finished ~= nil and ctx.loc.finished > 60 * 30, "A finishes over par")
    w:seconds(1)
    check(state(A) == MS.ACTIVE and #A.starSpawns == 0, "no star over par")
    local list = ctx.loc.results[1]
    check(list ~= nil and #list == 1 and list[1].name == "A" and #ctx_of(B).loc.results[1] == 1, "the finish is on both boards")
    check(ctx_of(B).loc.cups[A.gi] == nil, "B drops A's cup at A's finish")
end)

test("act 2 route (pure): down to the lobby, back up; the 1st-floor stacks send you back up", function()
    local w, A = world_with({ "A" })
    local env = A.env
    local P = env.LIBWEST_POINTS
    local R = env.sgl_libwest_coffee_route
    local function label(p, cp) local _, l = R(p, cp) return l end
    check(label(P.run_start, 1) == "STAIRS DOWN" and R(P.run_start, 2) == nil, "the desk: down for the cup, the finish with it")
    check(label({ x = 0, y = P.y_f3, z = 600 }, 1) == "STAIRS DOWN", "3F: stairs down")
    check(label(P.esc_top, 1) == "ESCALATOR DOWN" and R(P.cup_stand, 1) == nil, "2F: escalator down; lobby: the cup")
    check(label({ x = -500, y = 0, z = -1500 }, 1) == "BACK UP TO 2F" and label({ x = 2500, y = 0, z = 2000 }, 2) == "BACK UP TO 2F",
        "the 1st-floor stacks (down the stairs too far) -> back up to 2F")
    check(label(P.cup_stand, 2) == "ESCALATOR UP", "with the cup in the lobby: up the escalator")
    check(label(P.f2_door_w, 2) == "WEST STAIRS UP" and label(P.f2_door_e, 2) == "EAST STAIRS UP", "2F: the nearer stair hall")
    check(label({ x = 0, y = P.y_f4, z = 1200 }, 2) == "STAIRS UP", "4F: stairs up")
end)

---------------------------------------------------------------------------------------------
-- act 3: QUIET HOURS HIDE & SEEK
---------------------------------------------------------------------------------------------
-- everyone into act 3 at the desk; until the round is set up (HIDE)
local function hns_world(names, opts)
    local w, A = world_with(names, opts)
    local cs = {}
    for _, n in ipairs(names) do table.insert(cs, w:client(n)) end
    local P = A.env.LIBWEST_POINTS
    for _, c in ipairs(cs) do enter(w, c, 3) end
    for _, c in ipairs(cs) do at(c, P.desk) end
    w:seconds(4.2)
    return w, cs, P
end

local function role(c, of)
    local ctx = ctx_of(c)
    return ctx.def.roleOf(ctx, (of or c).gi)
end

local function seeker_of(cs)
    local s, hs = nil, {}
    for _, c in ipairs(cs) do
        if role(cs[1], c) == "seeker" then s = c else table.insert(hs, c) end
    end
    return s, hs
end

local function to_seek(w, cs)
    local ctx = ctx_of(cs[1])
    local guard = 0
    while ctx.a ~= PH.SEEK and guard < 40 * 30 do
        w:step(1)
        guard = guard + 1
    end
end

test("act 3 alone: waiting for a second player (the invite), nothing assigned", function()
    local w, A = world_with({ "A" })
    enter(w, A, 3)
    w:seconds(4)
    local ctx = ctx_of(A)
    check(state(A) == MS.WAITING and ctx.p == 0, "WAITING, no roles")
    check(Sim.hud_has(A, "This act needs 2 players"), "the lone-player prompt")
end)

test("act 3 with 2 players: roles, 2F only, 25 s; the librarian at the desk, frozen, screen dark, metal + lantern; the hider released", function()
    local w, cs, P = hns_world({ "A", "B" })
    local A = cs[1]
    local ctx = ctx_of(A)
    check(state(A) == MS.ACTIVE and ctx.a == PH.HIDE, "set up: hiding")
    check(popcount(ctx.p) == 2 and popcount(ctx.o) == 1 and ctx.f == 0, "2 players: one night librarian, one hider")
    check((ctx.g & 7) == 0x2 and ctx.c >= 24 and ctx.c <= 25, "the 2nd floor's stacks only, 25 s to hide")
    local S, hs = seeker_of(cs)
    local H = hs[1]
    check(S ~= nil and H ~= nil and role(S) == "seeker" and role(H) == "hider", "roles agree on both clients")
    w:step(2)
    check(d2(S.pos, P.desk) <= 100 and math.abs(S.pos.y - P.desk.y) <= 30 and S.face.y == 0, "librarian at the desk, facing south")
    local rel = d2(H.pos, P.release_w) <= 100 and P.release_w or (d2(H.pos, P.release_e) <= 100 and P.release_e or nil)
    check(rel ~= nil and H.face.y == 0x8000, "hider at a corridor into the stacks, facing north")
    S.pressed = C.A_BUTTON; S.stickMag = 64
    w:step(1)
    check(S.lastInput.buttons == 0 and S.lastInput.stickMag == 0, "the librarian is frozen while counting")
    H.pressed = C.A_BUTTON
    w:step(1)
    check(H.lastInput.buttons ~= 0, "the hider is not")
    check(Sim.hud_has(S, "TONIGHT'S NIGHT LIBRARIAN") and Sim.hud_has(S, "no peeking"), "the librarian's screen: counting")
    local dark = false
    for _, d in ipairs(S.draw) do if d.k == "rect" and d.w >= 400 and d.h >= 230 and d.col[4] >= 200 then dark = true end end
    check(dark, "a dark overlay covers the librarian's screen")
    check(Sim.hud_has(H, "HIDE! %d+") and Sim.hud_has(H, "You: HIDER"), "the hider's HUD")
    -- lantern + metal on both clients
    for _, c in ipairs(cs) do
        local sm = (c == S) and c.ms[0] or view(c, S)
        local flames = 0
        for _, o in ipairs(Sim.objects_with(c, c.env.id_bhvSglMissionFx)) do
            if raw(o)._model == C.E_MODEL_RED_FLAME and math.abs(raw(o).oPosY - (sm.pos.y + 150)) < 1 and not hidden(o) then flames = flames + 1 end
        end
        check(flames == 1, c.name .. ": one lantern over the librarian")
        raw(sm).marioBodyState.modelState = 0
        local hm = (c == H) and c.ms[0] or view(c, H)
        raw(hm).marioBodyState.modelState = 0
        w:step(1)
        check((raw(sm).marioBodyState.modelState & C.MODEL_STATE_METAL) ~= 0, c.name .. ": the librarian is drawn metal")
        check(raw(hm).marioBodyState.modelState == 0, c.name .. ": the hider looks normal")
    end
    to_seek(w, cs)
    w:step(1)
    check(ctx.a == PH.SEEK and ctx.c >= 119 and ctx.c <= 120, "then 120 s of quiet hours (2 players)")
    check(Sim.hud_has(S, "READY OR NOT!") and Sim.hud_has(S, "NIGHT LIBRARIAN"), "READY OR NOT!")
    S.pressed = C.A_BUTTON
    w:step(1)
    check(S.lastInput.buttons ~= 0, "the librarian moves again")
end)

test("act 3: a touch finds the hider -> the librarians win -> star on the circulation desk; board and tallies", function()
    local w, cs, P = hns_world({ "A", "B" })
    local S, hs = seeker_of(cs)
    local H = hs[1]
    to_seek(w, cs)
    at(H, { x = -2000, y = P.y_f2, z = -2000 })
    at(S, { x = -2000 + 100, y = P.y_f2, z = -2000 })
    w:step(3)
    local ctx = ctx_of(S)
    local bit = 1 << H.gi
    check((ctx.f & bit) ~= 0 and (ctx.o & bit) ~= 0, "found: the hider joins the librarians")
    check(ctx.a == PH.OVER and (ctx.g >> 4) == S.env.SGL_LIBWEST_WIN.FOUND, "no hiders left: the librarians win")
    w:step(3)
    check(state(S) == MS.SUCCESS and state(H) == MS.SUCCESS, "SUCCESS on both clients")
    local lead = cs[1]                                  -- the leader spawns first (the other client gets it by packet)
    local sp = lead.starSpawns[1]
    check(#S.starSpawns == 1 and #H.starSpawns == 1 and Sim.stars_of(S, 2) == 1 and Sim.stars_of(H, 2) == 1, "one star on each client")
    check(sp.from ~= nil and sp.x == P.desk_star.x and sp.y == P.desk_star.y and sp.z == P.desk_star.z, "the star on the desk")
    check(sp.from.x == P.desk.x and sp.from.y == P.desk.y and sp.from.z == P.desk.z, "rising from the patron side")
    check(Sim.find(H.hudLog, "FOUND by") ~= nil or Sim.hud_has(H, "FOUND by"), "the hider is told who found them")
    check(Sim.hud_has(S, "QUIET HOURS %- ROUND 1") and Sim.hud_has(S, "Librarian: " .. S.name), "results board")
    check(S.storage["sgl_lw_hns_librarian"] == 1 and S.storage["sgl_lw_hns_rounds"] == 1, "librarian tally +1")
    check((H.storage["sgl_lw_hns_hider"] or 0) == 0 and H.storage["sgl_lw_hns_rounds"] == 1, "hider: a round, no win")
    Sim.cmd(S, "mission", "reset")                     -- another round: the panel shows the tally
    w:seconds(4.5)
    check(ctx_of(S).a == PH.HIDE and Sim.hud_has(S, "Your record: hider wins 0, librarian wins 1"), "panel shows the tally")
end)

test("act 3: the lantern beam finds a hider held in it 0.5 s; shelves block it; crouching shrinks it; behind it is dark", function()
    local w, cs, P = hns_world({ "A", "B" })
    local S, hs = seeker_of(cs)
    local H = hs[1]
    to_seek(w, cs)
    local ctx = ctx_of(S)
    local bit = 1 << H.gi
    local base = { x = -2000, y = P.y_f2, z = -2000 }
    at(S, base)
    S.face.y = 0x4000                                   -- facing east
    -- 5 m behind the librarian: dark
    at(H, { x = base.x - 500, y = base.y, z = base.z })
    w:seconds(1)
    check((ctx.f & bit) == 0, "5 m behind: not found")
    -- 5 m ahead, behind a shelf: the ray hits it
    S.walls = { { x0 = base.x + 250, z0 = base.z - 300, x1 = base.x + 250, z1 = base.z + 300 } }
    at(H, { x = base.x + 500, y = base.y, z = base.z + 50 })
    w:seconds(1)
    check((ctx.f & bit) == 0 and (S.rays or 0) > 0, "behind a shelf: not found (line of sight)")
    S.walls = nil
    -- crouching at 5 m: out of the shrunken beam; at 2.5 m: in it
    act_as(H, C.ACT_CROUCHING)
    w:seconds(1)
    check((ctx.f & bit) == 0, "crouching 5 m ahead: not found")
    check(Sim.hud_has(H, "The librarian is near %(5 m%)") and not Sim.hud_has(H, "IN THE LIGHT!"), "the hider is warned (near, not lit)")
    at(H, { x = base.x + 250, y = base.y, z = base.z + 50 })
    local found, spotted = nil, false
    for f = 1, 40 do
        w:step(1)
        if Sim.hud_has(S, "SPOTTED %d+%%") then spotted = true end
        if (ctx.f & bit) ~= 0 then found = f break end
    end
    check(spotted, "the librarian sees SPOTTED n% over a hider in the beam")
    check(found ~= nil and found >= 15, "crouching 2.5 m ahead: found after the beam held 0.5 s (" .. tostring(found) .. " frames)")
    check(ctx_of(H).loc.found[H.gi] ~= nil and ctx_of(H).loc.found[H.gi].how == 2, "found by the lantern")
end)

test("act 3: the hider sees IN THE LIGHT! and the librarian's distance; noise is heard (NOISE marker), tiptoeing is not", function()
    local w, cs, P = hns_world({ "A", "B" })
    local S, hs = seeker_of(cs)
    local H = hs[1]
    to_seek(w, cs)
    local base = { x = -2000, y = P.y_f2, z = -2000 }
    at(S, base)
    S.face.y = 0x4000
    raw(view(H, S)).faceAngle.y = 0x4000               -- the hider's view of the librarian's facing
    at(H, { x = base.x + 450, y = base.y, z = base.z })
    w:step(3)
    check(ctx_of(H).loc.lit and Sim.hud_has(H, "IN THE LIGHT!"), "in the beam: the hider sees it")
    at(H, { x = base.x, y = base.y, z = base.z + 650 })   -- beside the librarian, 6.5 m
    S.face.y = 0x8000
    w:seconds(1)
    check(Sim.hud_has(H, "The librarian is near %(7 m%)") or Sim.hud_has(H, "The librarian is near %(6 m%)"), "near: the distance")
    -- tiptoeing 6.5 m away: silent; running: heard
    act_as(H, C.ACT_WALKING, 8)
    w:seconds(1)
    check(#ctx_of(S).loc.pings == 0, "tiptoeing: nothing heard")
    act_as(H, C.ACT_WALKING, 30)
    w:step(3)
    check(#ctx_of(S).loc.pings == 0, "running 6.5 m away (radius 6 m): not heard")
    at(H, { x = base.x, y = base.y, z = base.z + 500 })
    w:step(3)
    check(#ctx_of(S).loc.pings == 1 and Sim.hud_has(S, "NOISE"), "running 5 m away: heard, a NOISE marker")
    check(Sim.hud_has(H, "they heard that"), "the hider knows")
    w:step(10)
    check(#ctx_of(S).loc.pings == 1, "at most one noise a second")
end)

test("act 3: staying put 45 s ends in a sneeze heard 20 m away (warned at 35 s); the chime tells floor and side every 30 s", function()
    local w, cs, P = hns_world({ "A", "B" })
    local S, hs = seeker_of(cs)
    local H = hs[1]
    to_seek(w, cs)
    at(H, { x = -2600, y = P.y_f2, z = -2600 })
    at(S, { x = -1000, y = P.y_f2, z = -2600 })         -- 16 m away
    S.face.y = 0x8000                                   -- facing north, not at the hider
    w:seconds(29.5)
    local guard = 0
    while ctx_of(S).loc.chime == nil and guard < 90 do
        w:step(1)
        guard = guard + 1
    end
    check(ctx_of(S).loc.chime ~= nil and ctx_of(S).loc.chime.text == "2F WEST", "the 30 s chime: 2F WEST")
    check(Sim.hud_has(S, "CHIME! Hiders: 2F WEST"), "shown to the librarian")
    w:seconds(5.5)
    check(Sim.hud_has(H, "Dusty! You'll sneeze in"), "warned after 35 s in one spot")
    w:seconds(10.5)
    check(ctx_of(H).loc.sneezes == 1, "sneezed after 45 s")
    local pg = ctx_of(S).loc.pings[#ctx_of(S).loc.pings]
    check(pg ~= nil and pg.sn and math.abs(pg.pos.x - H.pos.x) < 2, "the librarian 16 m away heard the sneeze (ACHOO! marker)")
    check((ctx_of(S).f & (1 << H.gi)) == 0, "a sneeze alone does not find anyone")
end)

test("act 3: quiet hours run out -> the hiders win; the star appears anyway; the hider's tally", function()
    local w, cs, P = hns_world({ "A", "B" })
    local S, hs = seeker_of(cs)
    local H = hs[1]
    to_seek(w, cs)
    at(S, { x = -1000, y = P.y_f2, z = -2600 })
    for k = 1, 5 do
        at(H, { x = -2600 + (k % 2) * 400, y = P.y_f2, z = -2600 })   -- moves now and then (no sneeze)
        w:seconds(24.5)
    end
    w:seconds(2)
    local ctx = ctx_of(H)
    check(ctx.a == PH.OVER and (ctx.g >> 4) == H.env.SGL_LIBWEST_WIN.TIME, "time: the hiders win")
    check(state(H) == MS.SUCCESS and #H.starSpawns == 1, "every completed round puts the star out")
    check(H.storage["sgl_lw_hns_hider"] == 1 and (S.storage["sgl_lw_hns_librarian"] or 0) == 0, "hider tally +1")
    check(Sim.hud_has(H, "SAFE"), "the board: SAFE")
end)

test("act 3: leaving the stacks for 4 s counts as found (reported by the hider's own client)", function()
    local w, cs, P = hns_world({ "A", "B" })
    local S, hs = seeker_of(cs)
    local H = hs[1]
    to_seek(w, cs)
    at(S, { x = -1000, y = P.y_f2, z = -2600 })
    at(H, { x = 0, y = P.y_f3, z = -2000 })             -- 3F: out of the 2-player arena (2F only)
    w:seconds(2)
    check((ctx_of(S).f & (1 << H.gi)) == 0 and Sim.hud_has(H, "BACK TO THE STACKS"), "warned with a countdown")
    w:seconds(2.5)
    check((ctx_of(S).f & (1 << H.gi)) ~= 0 and ctx_of(S).loc.found[H.gi].how == 3, "4 s out: found")
end)

test("act 3 with 3 players: 2F-3F, one librarian; the found hider joins the hunt; a lost tag is sent again", function()
    local w, cs, P = hns_world({ "A", "B", "C" })
    local A = cs[1]
    local ctx = ctx_of(A)
    check((ctx.g & 7) == 0x6 and popcount(ctx.o) == 1 and ctx.c >= 29, "3 players: 2F + 3F, one librarian, 30 s to hide")
    local S, hs = seeker_of(cs)
    to_seek(w, cs)
    check(ctx.c >= 149, "150 s of quiet hours")
    local H1, H2 = hs[1], hs[2]
    at(H1, { x = -2500, y = P.y_f2, z = -2500 })
    at(H2, { x = 2500, y = P.y_f3, z = -2500 })
    at(S, { x = -2400, y = P.y_f2, z = -2500 })
    -- the tag packet is lost: step without delivering it
    w.frame = w.frame + 1
    w:refresh_views()
    for _, c in ipairs(w.clients) do w:step_client(c) end
    local keep, dropped = {}, 0
    for _, msg in ipairs(w.queue) do
        if msg.kind == "packet" and msg.data.ev == "tag" then dropped = dropped + 1 else table.insert(keep, msg) end
    end
    w.queue = keep
    w:deliver()
    check(dropped == 1 or ctx_of(S).isLeader, "the tag event was dropped (unless the librarian leads)")
    at(S, { x = -1000, y = P.y_f2, z = -1500 })         -- away again
    w:seconds(2)
    local bit = 1 << H1.gi
    check((ctx.f & bit) ~= 0 and (ctx.o & bit) ~= 0, "re-sent after 1.5 s: applied, H1 is a librarian now")
    check(role(H1) == "seeker" and ctx.a == PH.SEEK, "the round goes on with H1 hunting")
    raw(view(H1, H2)).faceAngle.y = 0
    at(H1, { x = 2400, y = P.y_f3, z = -2500 })
    w:step(3)
    check((ctx.f & (1 << H2.gi)) ~= 0 and ctx.a == PH.OVER and (ctx.g >> 4) == 1, "H1 finds H2: the librarians win")
end)

test("act 3: the librarian rotates on /mission reset; a librarian who leaves hands the round to the hiders", function()
    local w, cs, P = hns_world({ "A", "B" })
    local S1 = seeker_of(cs)
    local S, hs = seeker_of(cs)
    to_seek(w, cs)
    at(hs[1], { x = -2000, y = P.y_f2, z = -2000 })
    at(S, { x = -1900, y = P.y_f2, z = -2000 })
    w:step(4)
    check(state(cs[1]) == MS.SUCCESS, "round 1 over")
    Sim.cmd(cs[1], "mission", "reset")
    w:seconds(4.5)
    local S2 = seeker_of(cs)
    check(ctx_of(cs[1]).a == PH.HIDE and S2 ~= S1, "a new round: the other player counts")
    -- 3 players, the librarian leaves mid-round
    local w3, cs3 = hns_world({ "A", "B", "C" })
    local L3 = seeker_of(cs3)
    to_seek(w3, cs3)
    local stay = nil
    for _, c in ipairs(cs3) do if c ~= L3 then stay = c end end
    w3:disconnect(L3)
    w3:step(5)
    check(ctx_of(stay).a == PH.OVER and (ctx_of(stay).g >> 4) == stay.env.SGL_LIBWEST_WIN.NO_LIBRARIAN, "the librarian left: hiders win")
end)

test("act 3: a late joiner watches (see-through, never tagged); 4 players: 1F-3F; 5+: two librarians (pure)", function()
    local w, cs, P = hns_world({ "A", "B" })
    local S, hs = seeker_of(cs)
    to_seek(w, cs)
    local D = prep(w:connect("D"))
    w:step(3)
    enter(w, D, 3)
    w:seconds(1)
    at(D, { x = -2000, y = P.y_f2, z = -2000 })
    at(S, { x = -1950, y = P.y_f2, z = -2000 })
    at(hs[1], { x = 2500, y = P.y_f2, z = -2500 })
    w:step(3)
    check(role(D) == "watch" and (ctx_of(S).f & (1 << D.gi)) == 0 and ctx_of(S).loc.sent[D.gi] == nil,
        "the late joiner is not in the round: never tagged (not even tried)")
    check(Sim.hud_has(D, "Watching"), "they are told")
    raw(view(S, D)).marioBodyState.modelState = 0
    w:step(1)
    check((raw(view(S, D)).marioBodyState.modelState & C.MODEL_STATE_NOISE_ALPHA) ~= 0, "drawn see-through on the others' screens")
    local env = S.env
    check(env.sgl_libwest_hns_floors(4) == 0x7 and env.sgl_libwest_hns_floors(3) == 0x6 and env.sgl_libwest_hns_floors(2) == 0x2,
        "arena floors: 2 -> 2F, 3 -> 2F-3F, 4+ -> 1F-3F")
    check(env.sgl_libwest_hns_seeker_count(4) == 1 and env.sgl_libwest_hns_seeker_count(5) == 2
        and env.sgl_libwest_hns_seeker_count(9) == 3, "librarians: 1 up to 4 players, 2 up to 8, then 3")
    local s5 = env.sgl_libwest_hns_seekers({ 0, 1, 2, 3, 7 }, 4)
    check(#s5 == 2 and s5[1] == 7 and s5[2] == 0, "5 players: two librarians, rotating (wraps round)")
    check(env.sgl_libwest_hns_section({ x = -2500, y = 1200, z = 0 }) == "3F WEST"
        and env.sgl_libwest_hns_section({ x = 0, y = 0, z = 0 }) == "1F MIDDLE", "chime sections")
    local n, label = env.sgl_libwest_noise(C.ACT_WALKING, 8)
    check(n == 0 and label == "quiet", "tiptoe is silent")
    check(env.sgl_libwest_noise(C.ACT_CRAWLING, 20) == 0 and env.sgl_libwest_noise(C.ACT_JUMP, 0) == 650
        and env.sgl_libwest_noise(C.ACT_GROUND_POUND_LAND, 0) == 1100, "crawling silent, a jump 6.5 m, a ground pound 11 m")
    local w4, cs4 = hns_world({ "A", "B", "C", "D" })
    check((ctx_of(cs4[1]).g & 7) == 0x7 and popcount(ctx_of(cs4[1]).o) == 1, "4 players: 1F-3F, one librarian")
end)

test("act 3: the optional lantern light (le_add_light) follows each librarian and is removed when the act is left", function()
    local w, cs, P = hns_world({ "A", "B" })
    for _, c in ipairs(cs) do c.env.SGL_LIBWEST_HNS.leLight = true end
    w:step(2)
    for _, c in ipairs(cs) do check(c.lights == 1, c.name .. ": one light (one librarian)") end
    w:warp(cs[1], HUB, 1, 0)
    w:step(3)
    check(cs[1].lights == 0, "left the act: its light removed")
    for _, c in ipairs(cs) do c.env.SGL_LIBWEST_HNS.leLight = false end
end)

---------------------------------------------------------------------------------------------
-- fix round (technical + fun reviews): nametags, the drawn beam, quiet-hours music, hide-phase bounds, the next round,
-- act 1's way back to the lobby, faster act 1 Boos, a full object pool
---------------------------------------------------------------------------------------------
local function lakitu(c)
    -- a camera 10 m south of and 5 m over the stage origin, looking north (coopdx LakituState curPos / curFocus)
    c.stubs.gLakituState = { curPos = { x = 0, y = 500, z = 1000 }, curFocus = { x = 0, y = 400, z = 0 } }
end

local function behind_camera(c, pos)
    local ls = c.stubs.gLakituState
    local cp, cf = ls.curPos, ls.curFocus
    return (pos.x - cp.x) * (cf.x - cp.x) + (pos.y - cp.y) * (cf.y - cp.y) + (pos.z - cp.z) * (cf.z - cp.z) < 0
end

local function tag_of(c, li)
    return Sim.run_hooks(c, C.HOOK_ON_NAMETAGS_RENDER, li, { x = 0, y = 0, z = 0 })
end

test("act 3: nametags of the round's players are hidden while hiding and seeking (not watchers', not after the round)", function()
    local w, cs, P = hns_world({ "A", "B" })
    for _, c in ipairs(cs) do lakitu(c) end
    local S, hs = seeker_of(cs)
    local H = hs[1]
    check(ctx_of(S).a == PH.HIDE, "hiding")
    for _, c in ipairs(cs) do
        for _, other in ipairs(cs) do
            local li = (other == c) and 0 or c.liOf[other.gi]
            local r = tag_of(c, li)
            check(type(r) == "table" and r.name == "" and r.pos ~= nil and behind_camera(c, r.pos),
                c.name .. ": " .. other.name .. "'s tag hidden while hiding (empty, behind the camera)")
        end
    end
    to_seek(w, cs)
    local r = tag_of(S, S.liOf[H.gi])
    check(type(r) == "table" and r.name == "" and behind_camera(S, r.pos), "the librarian sees no tag over the hider while seeking")
    -- a late joiner is not in the round: their tag stays
    local D = prep(w:connect("D"))
    lakitu(D)
    w:step(3)
    enter(w, D, 3)
    w:seconds(1)
    check(role(D) == "watch" and tag_of(S, S.liOf[D.gi]) == nil, "a watcher's tag is drawn as usual")
    -- the round ends: tags are back
    at(H, { x = -2000, y = P.y_f2, z = -2000 })
    at(S, { x = -1900, y = P.y_f2, z = -2000 })
    w:step(4)
    check(ctx_of(S).a == PH.OVER and tag_of(S, S.liOf[H.gi]) == nil and tag_of(H, H.liOf[S.gi]) == nil, "after the round: tags back")
    -- other acts: never
    local w1, A, B = world_with({ "A", "B" })
    lakitu(A)
    enter(w1, A, 1); enter(w1, B, 1)
    w1:seconds(5)
    check(tag_of(A, A.liOf[B.gi]) == nil, "act 1: tags untouched")
    check(A.stubs.gServerSettings.nametags == nil, "the server setting is never written")
end)

test("act 3: the lantern's beam is drawn while seeking (sparkles on its axis and 6 m edges), on every client, and only then", function()
    local w, cs, P = hns_world({ "A", "B" })
    local S, hs = seeker_of(cs)
    local env = S.env
    local function sparkles(c)
        local out = {}
        for _, o in ipairs(Sim.objects_with(c, c.env.id_bhvSglMissionFx)) do
            if raw(o)._model == C.E_MODEL_SPARKLES and not hidden(o) then table.insert(out, o) end
        end
        return out
    end
    w:step(2)
    check(#sparkles(S) == 0 and #sparkles(hs[1]) == 0, "counting: no beam")
    to_seek(w, cs)
    at(S, { x = -2000, y = P.y_f2, z = -2000 })
    S.face.y = 0x4000
    raw(view(hs[1], S)).faceAngle.y = 0x4000            -- (the sim syncs positions, not facings)
    w:step(2)
    local pts = env.sgl_libwest_hns_beam(S.pos, S.face.y)
    check(#pts == 5, "5 beam points")
    for _, c in ipairs(cs) do
        local sp = sparkles(c)
        local hit = 0
        for _, p in ipairs(pts) do
            for _, o in ipairs(sp) do
                if math.abs(raw(o).oPosX - p.x) < 2 and math.abs(raw(o).oPosZ - p.z) < 2 and math.abs(raw(o).oPosY - p.y) < 2 then
                    hit = hit + 1
                    break
                end
            end
        end
        check(#sp == 5 and hit == 5, c.name .. ": the beam's 5 sparkles where the librarian faces")
    end
    -- the drawn beam is the catch cone: its axis points and (just inside) its edges are in the light; past the edge not
    local base = { x = 0, y = 0, z = 0 }
    for i, p in ipairs(env.sgl_libwest_hns_beam(base, 0x4000)) do
        local q = { x = p.x * 0.98, y = 0, z = p.z * 0.98 }
        check(env.sgl_libwest_hns_catch(base, 0x4000, q, false) == "light", "beam point " .. i .. " is lit")
    end
    local edge = env.sgl_libwest_hns_beam(base, 0x4000)[4]
    local ang = math.atan(edge.z, edge.x) * 1.25
    check(env.sgl_libwest_hns_catch(base, 0x4000, { x = 580 * math.cos(ang), y = 0, z = 580 * math.sin(ang) }, false) == nil,
        "a little past the drawn edge: dark")
    -- turning moves it
    S.face.y = 0
    raw(view(hs[1], S)).faceAngle.y = 0
    w:step(2)
    local p3 = env.sgl_libwest_hns_beam(S.pos, 0)[3]
    local moved = false
    for _, o in ipairs(sparkles(hs[1])) do
        if math.abs(raw(o).oPosZ - p3.z) < 2 and math.abs(raw(o).oPosX - p3.x) < 2 then moved = true end
    end
    check(moved, "it follows the librarian's facing on the hider's screen")
    -- round over: gone
    at(hs[1], { x = S.pos.x + 50, y = P.y_f2, z = S.pos.z })
    w:step(4)
    check(ctx_of(S).a == PH.OVER and #sparkles(S) == 0 and #sparkles(hs[1]) == 0, "after the round: no beam")
end)

test("act 3: quiet-hours music while hiding and seeking; the level music after the round and when leaving", function()
    local QUIET = (4 << 8) | C.SEQ_EVENT_PIRANHA_PLANT
    local w, cs, P = hns_world({ "A", "B" })
    local S, hs = seeker_of(cs)
    w:step(2)
    for _, c in ipairs(cs) do check(c.music[#c.music] == QUIET, c.name .. ": the lullaby while hiding") end
    to_seek(w, cs)
    w:step(2)
    for _, c in ipairs(cs) do check(c.music[#c.music] == QUIET and #c.music == 1, c.name .. ": still (once) while seeking") end
    at(hs[1], { x = -2000, y = P.y_f2, z = -2000 })
    at(S, { x = -1900, y = P.y_f2, z = -2000 })
    w:step(4)
    for _, c in ipairs(cs) do check(#c.music == 0, c.name .. ": the round over, the level music is back") end
    Sim.cmd(S, "mission", "reset")
    w:seconds(4.5)
    check(#S.music == 1, "the next round: the lullaby again")
    w:warp(S, HUB, 1, 0)
    w:step(3)
    check(#S.music == 0, "left the act mid-round: stopped")
end)

test("act 3: a hider outside the stacks while hiding is warned (no count yet); after the star the next round counts in", function()
    local w, cs, P = hns_world({ "A", "B" })
    local S, hs = seeker_of(cs)
    local H = hs[1]
    w:step(3)
    at(H, { x = 0, y = P.y_f3, z = -2000 })            -- 3F: outside the 2-player arena
    w:seconds(6)
    local ctx = ctx_of(S)
    check(ctx.a == PH.HIDE and Sim.hud_has(H, "OUT OF BOUNDS") and Sim.hud_has(H, "THE STACKS"), "warned while hiding")
    check((ctx.f & (1 << H.gi)) == 0 and ctx_of(H).loc.sent[H.gi] == nil, "no tag while hiding")
    at(H, { x = -2000, y = P.y_f2, z = -2000 })
    w:step(2)
    check(not Sim.hud_has(H, "OUT OF BOUNDS"), "back in the stacks: no warning")
    -- a round: found, SUCCESS (the star on the desk)
    to_seek(w, cs)
    at(S, { x = -1900, y = P.y_f2, z = -2000 })
    w:step(4)
    check(state(S) == MS.SUCCESS and ctx.a == PH.OVER, "round over, the star is out")
    local r0 = ctx.r
    H.pressed = C.D_JPAD
    w:step(3)
    check(ctx_of(S).r == r0 and Sim.hud_has(H, "Grab the star"), "D-pad Down with the star still out: grab it first")
    check(Sim.hud_has(S, "then the next round"), "the panel says so")
    -- the star collected -> DONE -> NEXT: 20 s, then the next round with the other librarian
    -- collected: the "got" event, and coopdx deletes every copy (packet_collect_star)
    local function collect(c, o)
        Sim.run_hooks(c, C.HOOK_ON_INTERACT, c.ms[0], o, C.INTERACT_STAR_OR_KEY, true)
        for _, cc in ipairs(cs) do
            for _, so in ipairs(Sim.objects_with(cc, C.id_bhvStarSpawnCoordinates)) do raw(so).activeFlags = C.ACTIVE_FLAG_DEACTIVATED end
        end
    end
    local who = nil
    for _, c in ipairs(cs) do if Sim.objects_with(c, C.id_bhvStarSpawnCoordinates)[1] ~= nil then who = c break end end
    collect(who, Sim.objects_with(who, C.id_bhvStarSpawnCoordinates)[1])
    w:step(3)
    ctx = ctx_of(S)
    check(state(S) == MS.DONE and ctx.a == PH.NEXT and ctx.c >= 19 and ctx.c <= 20, "DONE: the next round in 20 s")
    check(Sim.hud_has(S, "Next round in"), "the panel counts it")
    w:seconds(19)
    check(state(S) == MS.DONE and ctx_of(S).a == PH.NEXT, "still counting at 19 s")
    w:seconds(2)
    check(ctx_of(S).r == r0 + 1, "then a new round by itself")
    w:seconds(4.5)
    local S2 = seeker_of(cs)
    check(ctx_of(S).a == PH.HIDE and S2 ~= nil and S2 ~= S, "hiding again, the librarian rotated")
    -- D-pad Down in DONE: now
    to_seek(w, cs)
    local S3, hs3 = seeker_of(cs)
    at(hs3[1], { x = -2000, y = P.y_f2, z = -2000 })
    at(S3, { x = -1900, y = P.y_f2, z = -2000 })
    w:step(4)
    local c2 = nil
    for _, c in ipairs(cs) do
        for _, o in ipairs(Sim.objects_with(c, C.id_bhvStarSpawnCoordinates)) do
            if ((raw(o).oBehParams >> 24) & 0xFF) == 2 and (raw(o).oBehParams & 0xFFFF) == ((r0 + 1) & 0xFFFF) then c2 = c2 or { c, o } end
        end
    end
    check(c2 ~= nil, "round 2's own star")
    if c2 ~= nil then
        collect(c2[1], c2[2])
        w:step(3)
        local r1 = ctx_of(S).r
        H.pressed = C.D_JPAD
        w:step(3)
        check(ctx_of(S).r == r1 + 1, "D-pad Down after the star: the next round at once")
    end
end)

test("act 1: D-pad Down twice gets you back to the lobby (once only asks); act 1 Boos chase at 12, act 2's at the default 7", function()
    local w, A = world_with({ "A" })
    local P = A.env.LIBWEST_POINTS
    enter(w, A, 1)
    at(A, P.spawn)
    w:seconds(4)
    local pit = { x = -875, y = 0, z = 1260 }          -- the bottom of car A's shaft
    at(A, pit)
    A.pressed = C.D_JPAD
    w:step(2)
    check(d2(A.pos, pit) < 1 and Sim.hud_has(A, "D%-pad Down again"), "one press: only asks")
    w:seconds(3)
    A.pressed = C.D_JPAD
    w:step(2)
    check(d2(A.pos, pit) < 1, "a second press after 2 s asks again")
    A.pressed = C.D_JPAD
    w:step(2)
    check(d2(A.pos, P.spawn) <= 100 and A.face.y == 0x8000, "two presses: back at the lobby spawn, facing the escalators")
    local ctx = ctx_of(A)
    check(ctx.objs.boos[1].speed == 12, "act 1 Boos: speed 12")
    local env = A.env
    local b = { hx = 0, hy = 0, hz = 0, x = 0, y = env.SGL_LIBWEST_BOO.HOVER, z = 0, alpha = 255, speed = 12 }
    env.sgl_libwest_boo_step(b, { x = 600, y = 0, z = 0 }, 0x4000, true)
    check(math.abs(b.x - 12) < 1, "a turned back: 12 units a frame")
    local w2, B = world_with({ "B" })
    enter(w2, B, 2)
    w2:seconds(4)
    check(ctx_of(B).objs.boos[1].speed == nil and env.SGL_LIBWEST_BOO.SPEED == 7, "act 2's stairwell Boos: the default 7")
end)

test("a full object pool (spawn_non_sync_object -> nil) never breaks the lanterns, the beam or the cups", function()
    local w, cs, P = hns_world({ "A", "B" })
    for _, c in ipairs(cs) do
        local real = c.stubs.spawn_non_sync_object
        c.stubs.spawn_non_sync_object = function(bhv, model, x, y, z, setup)
            if model == C.E_MODEL_RED_FLAME or model == C.E_MODEL_SPARKLES or model == C.E_MODEL_BITS_WARP_PIPE then return nil end
            return real(bhv, model, x, y, z, setup)
        end
        for _, o in ipairs(Sim.objects_with(c, c.env.id_bhvSglMissionFx)) do raw(o).activeFlags = C.ACTIVE_FLAG_DEACTIVATED end
    end
    w:step(3)
    to_seek(w, cs)
    w:seconds(1)
    check(ctx_of(cs[1]).a == PH.SEEK, "act 3 runs on with no flames or sparkles")
    local w2, A = world_with({ "A" })
    local real = A.stubs.spawn_non_sync_object
    A.stubs.spawn_non_sync_object = function(bhv, model, x, y, z, setup)
        if model == C.E_MODEL_BITS_WARP_PIPE and A.level == BBH and ctx_of(A) ~= nil and ctx_of(A).loc.racing then return nil end
        return real(bhv, model, x, y, z, setup)
    end
    local P2 = A.env.LIBWEST_POINTS
    enter(w2, A, 2)
    w2:seconds(4)
    at(A, P2.run_start, 20)
    w2:seconds(4)
    at(A, P2.cup_stand)
    w2:step(3)
    w2:seconds(1)
    check(ctx_of(A).loc.cp == 2, "act 2: the cup taken, no cup object to wear, no error")
end)

test("HUD: every act and state renders without errors (panels, markers, boards)", function()
    local w, A, B = world_with({ "A", "B" })
    for act = 1, 6 do
        enter(w, A, act); enter(w, B, act)
        local P = A.env.LIBWEST_POINTS
        at(A, P.spawn); at(B, P.desk)
        for _ = 1, 12 do w:seconds(1) end
        check(#A.hudLog > 0, "act " .. act .. " renders")
    end
end)

---------------------------------------------------------------------------------------------
-- whole mod
---------------------------------------------------------------------------------------------
test("whole mod: every file loads with the Library West missions; /campus libwest 3 starts a round; act 4 is coming soon", function()
    local built = Sim.built_on_disk()
    built[BBH] = true
    local w = Sim.new({ files = Sim.ALL_FILES, built = built })
    local H = prep(w:connect("Host"))
    local F = prep(w:connect("Friend"))
    w:step(3)
    w:warp(H, HUB, 1, 0); w:warp(F, HUB, 1, 0)
    w:step(40)
    local idx = {}
    for i, f in ipairs(Sim.ALL_FILES) do idx[f] = i end
    check(idx[FILE] ~= nil, FILE .. " is a mod file")
    check(idx[FILE] > idx["sgl_mission.lua"] and idx[FILE] > idx["swamp_missions.lua"]
        and idx[FILE] > (idx["uf_marston_missions.lua"] or 0), "it loads after the framework and the other courses' files (strcmp)")
    check(H.env.sgl_mission_get(BBH, 3) ~= nil and H.env.sgl_mission_get(C.LEVEL_CCM, 3) ~= nil, "Library West + Marston missions")
    local ok = pcall(Sim.cmd, H, "campus", "libwest 3")
    w:step(5)
    if ok and H.level == BBH then
        check(H.act == 3 and F.level == BBH and F.act == 3, "/campus libwest 3: everyone to Library West act 3")
        w:seconds(4.5)
        check(state(H) == MS.ACTIVE and ctx_of(H).a == PH.HIDE and popcount(ctx_of(H).p) == 2, "a round is set up")
    else
        check(false, "/campus libwest 3 did not warp (levels.lua key 'libwest')")
    end
    w:warp(H, BBH, 1, 4)
    w:step(5)
    check(Sim.hud_has(H, "COMING SOON %- GHOST HUNT"), "act 4: coming soon notice")
end)

print(string.format("\n%d checks passed, %d failed", passed, failed))
os.exit(failed == 0 and 0 or 1)
