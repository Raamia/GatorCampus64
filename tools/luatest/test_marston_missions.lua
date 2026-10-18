-- Unit + scenario tests for mods/sgl64/uf_marston_missions.lua (course 4, Marston Science Library, LEVEL_CCM) in the
-- offline multi-client coopdx simulation (sim.lua), plus the act-select / level-script contract for course 4
-- (docs/flow.md 5.1) against the real course.lua and, once built, the real levels/ccm/script.c.
-- Run: tools/luatest/run.sh   (or: lua tools/luatest/test_marston_missions.lua)
--
-- The engine names only these missions use are stubbed here, per client (prep below), and each one is checked to be a
-- real sm64coopdx v1.5.1 binding first: obj_init_animation + gObjectAnimations (the Toad librarians' standing
-- animation, the flying bookends) and hurt_and_set_mario_action (a flying book's hit); the rom-hack camera getters /
-- setters (levels.lua's interior camera, whole-mod test) record into c.cam.
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

local CCM, HUB = C.LEVEL_CCM, C.LEVEL_CASTLE_GROUNDS
local MS = { IDLE = 0, WAITING = 1, INTRO = 2, ACTIVE = 3, SUCCESS = 4, FAILED = 5, DONE = 6 }
local FILES = { "course.lua", "sgl_deepspace.lua", "sgl_hud.lua", "sgl_mission.lua", "uf_marston_missions.lua" }
local PTOP = 26

for _, n in ipairs({ "obj_init_animation", "hurt_and_set_mario_action" }) do assert(API[n] ~= nil, n .. " is a v1.5.1 binding") end

-- coopdx v1.5.1 romhack_camera_init_settings defaults; get -> c.cam, set (u32 / u8 integers) -> c.cam
local CAM_FIELDS = { { "zoomed_in_dist", "inDist" }, { "zoomed_out_dist", "outDist" }, { "zoomed_in_height", "inHeight" },
    { "zoomed_out_height", "outHeight" }, { "collisions", "collisions" } }
local function camera_stubs(c)
    c.cam = { inDist = 900, outDist = 1400, inHeight = 300, outHeight = 450, collisions = 0, sets = 0 }
    for _, f in ipairs(CAM_FIELDS) do
        c.stubs["camera_romhack_get_" .. f[1]] = function() return c.cam[f[2]] end
        c.stubs["camera_romhack_set_" .. f[1]] = function(v)
            assert(math.type(v) == "integer", "camera_romhack_set_" .. f[1] .. " takes an integer")
            c.cam[f[2]] = v
            c.cam.sets = c.cam.sets + 1
        end
    end
end

local function prep(c)
    local S = c.stubs
    S.obj_init_animation = function(o, i)
        assert(raw(o).oAnimations ~= nil and math.type(i) == "integer", "obj_init_animation(o with oAnimations, int)")
        raw(o)._anim = i
    end
    S.hurt_and_set_mario_action = function(m, action, arg, hurt)
        assert(math.type(action) == "integer" and math.type(arg) == "integer" and math.type(hurt) == "integer")
        raw(m).action = action
        raw(m).hurtCounter = hurt
        if raw(m).playerIndex == 0 then c.action = action end
        c.hurts = (c.hurts or 0) + 1
        return 1
    end
    S.gObjectAnimations = { toad_seg6_anims_0600FB58 = "ANIM:toad", bookend_seg5_anims_05002540 = "ANIM:bookend" }
    camera_stubs(c)
    local m = raw(c.ms[0])
    m.invincTimer, m.hurtCounter, m.flags = 0, 0, 0
    return c
end

-- connect players named A, B, ... (gi 0, 1, ...) with Marston built; they sync in the hub
local function world_with(names, opts)
    opts = opts or {}
    opts.files = opts.files or FILES
    opts.built = opts.built or { [HUB] = true, [C.LEVEL_BOB] = true, [CCM] = true }
    local w = Sim.new(opts)
    local cs = {}
    for _, n in ipairs(names) do table.insert(cs, prep(w:connect(n))) end
    w:step(3)
    return w, table.unpack(cs)
end

local function enter(w, c, act) w:warp(c, CCM, 1, act) end

local function at(c, p, dy)
    c.pos.x, c.pos.y, c.pos.z = p.x, p.y + (dy or 0), p.z
end

local function ctx_of(c) return Sim.ctx(c) end

local function state(c)
    local ctx = ctx_of(c)
    return ctx and ctx.s or nil
end

local function def_of(c, act) return c.env.sgl_mission_get(CCM, act) end

local function act_as(c, action, fvel)
    c.action = action
    raw(c.ms[0]).forwardVel = fvel or 0
end

local function d2(a, b) return math.sqrt((a.x - b.x) ^ 2 + (a.z - b.z) ^ 2) end

---------------------------------------------------------------------------------------------
-- registry, act names, act select, level script, coordinates
---------------------------------------------------------------------------------------------
test("registry: three Marston missions on acts 1/2/3, star ids act-1, titles = course.lua act names, acts 4-6 coming soon", function()
    local w, A = world_with({ "A" })
    local env = A.env
    local d1, d2_, d3 = def_of(A, 1), def_of(A, 2), def_of(A, 3)
    check(d1 and d1.id == "marston_climb" and d1.starId == 0 and d1.minPlayers == 1, "act 1 climb, star 0, solo")
    check(d2_ and d2_.id == "marston_quiet" and d2_.starId == 1 and d2_.minPlayers == 1, "act 2 quiet floor, star 1, solo")
    check(d3 and d3.id == "marston_booking" and d3.starId == 2 and d3.minPlayers == 2, "act 3 booking, star 2, 2+ players")
    local stage = env.sgl_stage_by_level(CCM)
    check(stage ~= nil and stage.key == "marston" and stage.door == 4 and stage.stars == 0 and stage.course == C.COURSE_CCM
        and stage.slot == "ccm" and stage.acts ~= nil, "course.lua: door 4 = MARSTON LIBRARY (zero stars, COURSE_CCM, slot ccm) with act names")
    for _, d in ipairs({ d1, d2_, d3 }) do
        check((d.bparams >> 24) == d.starId, d.id .. " bparams carry the star id")
        check(stage.acts[d.act] == d.title, d.id .. " title matches course.lua act " .. d.act .. " (" .. tostring(stage.acts[d.act]) .. ")")
        check(not env.sgl_act_is_soon(stage, d.act), d.id .. " act is not 'coming soon'")
        check(d.probes ~= nil and #d.probes >= 2, d.id .. " has geometry probes")
        check(#d.objective <= 60, d.id .. " objective fits the banner (" .. #d.objective .. " chars)")
        check(d.pointsFile ~= nil and d.pointsFile:find("uf_marston_missions.lua", 1, true) ~= nil, d.id .. " names its points file")
        check(not d.levelStar, d.id .. " spawns its own star")
    end
    for act = 4, 6 do
        check(env.sgl_mission_get(CCM, act) == nil, "act " .. act .. " has no mission yet")
        check(env.sgl_act_is_soon(stage, act) and stage.acts[act]:find("^COMING SOON") ~= nil,
            "act " .. act .. " is named COMING SOON: " .. tostring(stage.acts[act]))
    end
    for act = 1, 6 do
        check(not stage.acts[act]:find("[^A-Z0-9 '%.,%-&!%?]") and #stage.acts[act] <= 28,
            "act " .. act .. " name fits the act-select menu font: " .. stage.acts[act])
    end
    check(#env.SGL_MISSION_LIST == 3 and env.MARSTON_MISSION_ACTS.booking == 3, "3 Marston missions")
    check(env.sgl_party_location_text(CCM, 3) == "MARSTON LIBRARY - Act 3: STUDY ROOM BOOKING - 2P", "player-list location text")
    check(Sim.cmd(A, "mission", "list") and Sim.find(A.chat, "marston_booking: level " .. CCM .. " act 3 %(star 2%)") ~= nil,
        "/mission list shows the Marston missions")
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

test("levels/ccm/script.c (when built): warp contract for door 4, no level-script star for acts 1-3", function()
    local ls = Sim.level_script("ccm")
    if ls == nil then
        print("  (levels/ccm not built: skipped)")
        return
    end
    local function node(n)
        local wn = ls.warps[n]
        return wn and C[wn.level], wn and wn.node
    end
    local l0, n0 = node(0x0A)
    local l1, n1 = node(0xF0)
    local l2, n2 = node(0xF1)
    check(l0 == CCM and n0 == 0x0A, "CCM 0x0A = own entry spawn")
    check(l1 == HUB and n1 == 0x24, "CCM 0xF0 -> hub 0x24 (outside the Marston door)")
    check(l2 == HUB and n2 == 0x34, "CCM 0xF1 -> hub 0x34")
    for _, o in ipairs(ls.objects) do
        if o.bhv == "bhvStar" then
            check((o.acts & 0x07) == 0, string.format("no level-script star in acts 1-3 (found id %d, acts 0x%02X)",
                (o.bparams or 0) >> 24, o.acts))
        end
    end
end)

test("MARSTON_POINTS: inside s16, floors 6 m apart, lifts one floor each on railing tops, kiosks out of one player's reach", function()
    local w, A = world_with({ "A" })
    local P = A.env.MARSTON_POINTS
    local bad = 0
    local function each(v, name)
        if type(v) == "table" then
            for k, x in pairs(v) do each(x, name .. "." .. tostring(k)) end
        elseif type(v) == "number" and math.abs(v) > 32767 and not name:find("yaw") then
            bad = bad + 1
            print("  out of s16: " .. name .. " = " .. v)
        end
    end
    each(P, "MARSTON_POINTS")
    check(bad == 0, "every coordinate fits SM64's s16 range")
    check(P.y_f1 == -600 and P.y_f2 == 0 and P.y_f3 == 600 and P.y_f4 == 1200 and P.y_f5 == 1800, "floors 6 m apart, F2 = grade")
    check(P.spawn.y == P.y_f2 and P.climb_goal.y == P.y_f5 and P.quiet_start.y == P.y_f5, "spawn on F2, act 1 goal and act 2 start on F5")
    check(P.lift_a.bottom == P.y_f3 + P.rail and P.lift_a.top == P.y_f4 + P.rail and P.lift_b.bottom == P.y_f4 + P.rail
        and P.lift_b.top == P.y_f5 + P.rail, "lift A: F3 -> F4 railing tops, lift B: F4 -> F5")
    local a = P.atrium
    for _, lf in ipairs({ P.lift_a, P.lift_b }) do
        check(lf.x - lf.half >= a.x0 + 50 and lf.x + lf.half <= a.x1 - 50 and lf.z - lf.half >= a.z0 + 50 and lf.z + lf.half <= a.z1 - 50,
            "a lift deck stays 0.5 m inside the atrium void")
    end
    check(P.board_a.x > a.x1 and P.board_b.x < a.x0, "the boarding spots are on the balconies, outside the void")
    check(#P.stair_doors == 16, "16 stair / core / elevator doors closed in act 1 (F1-F4)")
    check(#P.books == 8, "8 textbooks")
    for _, b in ipairs(P.books) do
        check(b.y >= P.y_f5 and b.y <= P.y_f5 + 140, b.name .. ": on floor 5 or a piece of furniture")
    end
    for _, s in ipairs({ P.climb_star, P.quiet_star, P.room_star }) do
        local floor = (s == P.room_star) and P.y_f1 or P.y_f5
        check(s.y + 400 + 60 <= floor + P.clear, "a star's 4 m spawn hump stays under its 5.4 m ceiling")
    end
    -- kiosks: distinct floors, and each pair lit together needs two floors or a long run between them
    local floorOf = {}
    for i, k in ipairs(P.kiosks) do floorOf[i] = (k.y - P.y_f1) // 600 + 1 end
    check(floorOf[1] == 1 and floorOf[2] == 2 and floorOf[3] == 4 and floorOf[4] == 5, "kiosks on floors 1, 2, 4, 5")
    local def = def_of(A, 3)
    for n = 2, 4 do
        local mask = def.litMask(n)
        local count = 0
        for i = 1, 4 do if (mask >> (i - 1)) & 1 == 1 then count = count + 1 end end
        check(count == n, n .. " players: " .. n .. " kiosks lit")
    end
    check(def.litMask(2) == 0x9 and def.litMask(3) == 0xD and def.litMask(4) == 0xF, "lit sets 1F+5F, +4F, all")
    check(P.room_door.x0 == P.room_door.x1 and math.abs(P.room_door.z1 - P.room_door.z0) >= 150, "L129's door: a 1.8 m opening")
    check(P.room_star.x > P.room_door.x0 and d2(P.room_star, P.kiosks[1]) < 1200, "the act 3 star is inside L129, beside kiosk 1")
end)

---------------------------------------------------------------------------------------------
-- act 1: OUT-OF-ORDER ELEVATOR
---------------------------------------------------------------------------------------------
test("lifts: a pure function of the area timer (bottom, rise, top, fall), at most 12 units a frame after a timer jump", function()
    local w, A = world_with({ "A" })
    local env = A.env
    local L = env.SGL_MARSTON_LIFT
    local move = math.ceil(600 / L.SPEED)
    check(env.sgl_marston_lift_y(0, 700, 1300, 0) == 700 and env.sgl_marston_lift_y(L.WAIT - 1, 700, 1300, 0) == 700, "waits at the bottom")
    check(env.sgl_marston_lift_y(L.WAIT + move, 700, 1300, 0) == 1300, "reaches the top")
    check(env.sgl_marston_lift_y(L.WAIT + move + L.WAIT + move, 700, 1300, 0) == 700, "and comes back down")
    local prev, maxStep = nil, 0
    for t = 0, 2 * (L.WAIT + move) * 2 do
        local y = env.sgl_marston_lift_y(t, 700, 1300, 0)
        check(y >= 700 and y <= 1300, "within its travel")
        if prev ~= nil then maxStep = math.max(maxStep, math.abs(y - prev)) end
        prev = y
    end
    check(maxStep <= L.SPEED, "moves at most SPEED a frame")
    check(env.sgl_marston_lift_y(0, 1300, 1900, 160) ~= env.sgl_marston_lift_y(0, 1300, 1900, 0)
        or env.sgl_marston_lift_y(L.WAIT, 1300, 1900, 160) ~= 1300, "the offset shifts lift B's cycle")
    check(env.sgl_marston_lift_step(700, 1300) == 712 and env.sgl_marston_lift_step(1300, 700) == 1288
        and env.sgl_marston_lift_step(nil, 900) == 900 and env.sgl_marston_lift_step(1000, 1005) == 1005, "catch-up limit 12")
    -- the two lifts chain: lift A reaches F4 at its top; whoever steps off then and runs round the F4 balcony to
    -- board_b (~4-5 s, 120-160 frames) finds lift B at the bottom within 1 s, with time to board
    local la, lb = def_of(A, 1).lifts[1], def_of(A, 1).lifts[2]
    local tTop = nil
    for t = 0, 400 do
        if tTop == nil and env.sgl_marston_lift_y(t, la.bottom, la.top, la.offset) == la.top then tTop = t end
    end
    local worst = 0
    for run = 120, 160, 5 do
        local t, wait = tTop + run, 0
        while env.sgl_marston_lift_y(t + wait, lb.bottom, lb.top, lb.offset) ~= lb.bottom do wait = wait + 1 end
        local stay = 0
        while env.sgl_marston_lift_y(t + wait + stay, lb.bottom, lb.top, lb.offset) == lb.bottom do stay = stay + 1 end
        if wait > 30 or (wait == 0 and stay < 20) then worst = math.max(worst, wait + 1000) end
        worst = math.max(worst, wait)
    end
    check(tTop == 160 and worst <= 30, "lift B waits at F4 for a runner from lift A (worst wait " .. worst .. " frames)")
    -- the book cart: at lift A's side whenever lift A is at the top, at lift B's side whenever lift B is at the bottom,
    -- a 0.5 m hop from each, at most SPEED a frame, inside the void
    local ct = def_of(A, 1).cart
    local P = A.env.MARSTON_POINTS
    check(ct ~= nil and ct.top == la.top and ct.top == lb.bottom and ct.z == la.z, "the cart runs at the F4 railing tops")
    check(math.abs(la.x - ct.east) == la.half + 50 + ct.half and math.abs(ct.west - lb.x) == lb.half + 50 + ct.half,
        "0.5 m gaps to both lifts")
    check(ct.west - ct.half >= P.atrium.x0 + 50 and ct.east + ct.half <= P.atrium.x1 - 50, "inside the void")
    local okA, okB, maxDx, prevX = true, true, 0, nil
    for t = 0, 2 * ct.period do
        local x = env.sgl_marston_cart_x(t, ct.east, ct.west, ct.period, ct.offset)
        if env.sgl_marston_lift_y(t, la.bottom, la.top, la.offset) == la.top and x ~= ct.east then okA = false end
        if env.sgl_marston_lift_y(t, lb.bottom, lb.top, lb.offset) == lb.bottom and x ~= ct.west then okB = false end
        if prevX ~= nil then maxDx = math.max(maxDx, math.abs(x - prevX)) end
        prevX = x
    end
    check(okA and okB and maxDx <= L.SPEED, "the cart meets lift A at the top and lift B at the bottom, <= SPEED a frame")
end)

test("act 1 solo: barriers on every stair door, two lifts, route markers, milestones, the 5th floor -> one star -> DONE", function()
    local w, A = world_with({ "A" })
    local P = A.env.MARSTON_POINTS
    enter(w, A, 1)
    at(A, P.spawn)
    w:step(3)
    check(Sim.hud_has(A, "OUT%-OF%-ORDER ELEVATOR") and Sim.hud_has(A, "MARSTON LIBRARY %- ACT 1"), "act banner")
    check(Sim.find(A.console, "sleeps") == nil, "probes pass")
    local solids = Sim.objects_with(A, A.env.id_bhvSglMarstonSolid)
    check(#solids == 16, #solids .. " barrier collision boxes (16 doors)")
    local okCol = true
    for _, o in ipairs(solids) do
        if raw(o).collisionData ~= "COL:checkerboard_platform" then okCol = false end
    end
    check(okCol, "barriers use the vanilla checkerboard collision")
    local lifts = Sim.objects_with(A, A.env.id_bhvSglMarstonLift)
    check(#lifts == 3 and raw(lifts[1])._model == C.E_MODEL_CHECKERBOARD_PLATFORM, "two book-cart lifts and the book cart")
    check(ctx_of(A).objs.cart ~= nil and ctx_of(A).objs.lifts[3] == ctx_of(A).objs.cart, "the cart rides with the lifts")
    -- every door segment is covered by a barrier 0.3 m past both jambs, 5 m tall, centred on the door line
    local ctx = ctx_of(A)
    for i, d in ipairs(P.stair_doors) do
        local rec = ctx.objs.barriers[i]
        local o = raw(rec.o)
        local cx, cz = (d.x0 + d.x1) / 2, (d.z0 + d.z1) / 2
        local alongX = math.abs(d.x1 - d.x0) >= math.abs(d.z1 - d.z0)
        local width = alongX and math.abs(d.x1 - d.x0) or math.abs(d.z1 - d.z0)
        local half = o.header.gfx.scale.x * 256
        check(o.oPosX == cx and o.oPosZ == cz and half >= width / 2 + 29 and o.oFaceAngleYaw == (alongX and 0 or 0x4000),
            string.format("door %d covered (half %.0f for a %d-unit door)", i, half, width))
        local bottom = o.oPosY - 25 * o.header.gfx.scale.y
        check(math.abs(bottom - d.y) < 1 and 51 * o.header.gfx.scale.y >= 490, "door " .. i .. ": from the floor, 5 m tall")
    end
    w:seconds(3.5)
    check(state(A) == MS.ACTIVE and ctx.isLeader, "solo: active, leader")
    check(Sim.hud_has(A, "GRAND STAIR"), "marker: GRAND STAIR")
    -- by a closed door: the label
    local d = P.stair_doors[7]                         -- the core stair door on F2
    at(A, { x = d.x0 + 200, y = d.y, z = (d.z0 + d.z1) / 2 })
    w:step(2)
    check(Sim.hud_has(A, "CLOSED FOR RENOVATION"), "a closed stair door says so")
    at(A, P.shaft_door)
    w:step(2)
    check(Sim.hud_has(A, "OUT%-OF%-ORDER SHAFT"), "the shaft is marked on floor 2")
    at(A, P.board_a)
    w:step(3)
    check((ctx.f & 1) ~= 0 and Sim.hud_has(A, "BOOK%-CART LIFT"), "on F3: milestone 1, marker BOOK-CART LIFT")
    at(A, P.board_b)
    w:step(3)
    check((ctx.f & 2) ~= 0 and ctx.p == 12, "on F4: milestone 2, team best 12 m")
    -- standing on F5 outside the reading room does not count; inside it does
    at(A, { x = P.lift_b.x, y = P.y_f5, z = P.lift_b.z - 900 })
    w:step(2)
    check(state(A) == MS.ACTIVE, "F5 west wing: not the reading room yet")
    at(A, P.climb_goal)
    w:step(3)
    check(state(A) == MS.SUCCESS, "in the 5th-floor reading room: success")
    w:step(3)
    check(#A.starSpawns == 1 and Sim.stars_of(A, 0) == 1, "one spawned star (id 0)")
    local sp = A.starSpawns[1]
    check(sp and sp.x == P.climb_star.x and sp.y == P.climb_star.y and sp.z == P.climb_star.z, "star in the reading room")
    check(sp and sp.from.y == P.climb_star.y - 80 and sp.from.x == P.climb_star.x, "it rises out of the floor below it")
    local star = Sim.objects_with(A, C.id_bhvStarSpawnCoordinates)[1]
    Sim.run_hooks(A, C.HOOK_ON_INTERACT, A.ms[0], star, C.INTERACT_STAR_OR_KEY, true)
    raw(star).activeFlags = C.ACTIVE_FLAG_DEACTIVATED
    w:step(4)
    check(state(A) == MS.DONE and Sim.stars_of(A, 0) == 0, "DONE, no respawn")
end)

test("act 1: both lifts at the same height on two clients, carrying their rider (oVelY = the step), catching up after a timer jump", function()
    local w, A, B = world_with({ "A", "B" })
    local P = A.env.MARSTON_POINTS
    enter(w, A, 1); enter(w, B, 1)
    at(A, P.spawn); at(B, P.spawn)
    w:seconds(4)
    local function lifts(c)
        local ctx = ctx_of(c)
        return ctx.objs.lifts
    end
    local same, moved = true, false
    local ys = {}
    for _ = 1, 200 do
        w:step(1)
        for i = 1, 2 do
            local ra, rb = raw(lifts(A)[i].o), raw(lifts(B)[i].o)
            if ra.oPosY ~= rb.oPosY then same = false end
            if ra.oVelY ~= 0 then moved = true end
            if ys[i] ~= nil and math.abs(ra.oPosY - ys[i]) > 12 then same = false end
            ys[i] = ra.oPosY
        end
    end
    check(same, "both clients show both lifts at the same height, never more than 12 units a frame")
    local cartSame, cartMoved = true, false
    for _ = 1, 330 do
        w:step(1)
        local ra, rb = raw(ctx_of(A).objs.cart.o), raw(ctx_of(B).objs.cart.o)
        if ra.oPosX ~= rb.oPosX or ra.oPosY ~= rb.oPosY then cartSame = false end
        if ra.oVelX ~= 0 then cartMoved = true end
    end
    check(cartSame and cartMoved, "the book cart: the same on both clients, carrying its rider along X (oVelX = the step)")
    check(moved, "the lifts move (oVelY = the displacement, so the engine carries the rider)")
    local deckA = raw(lifts(A)[1].o).oPosY + PTOP
    check(deckA >= P.lift_a.bottom and deckA <= P.lift_a.top, "lift A's deck between the F3 and F4 railing tops")
    -- B's area timer jumps 4 s ahead: its lifts walk there at 12 units a frame instead of jumping
    B.areaTimerOffset = 120
    local maxStep = 0
    local prev = raw(lifts(B)[1].o).oPosY
    for _ = 1, 80 do
        w:step(1)
        local y = raw(lifts(B)[1].o).oPosY
        maxStep = math.max(maxStep, math.abs(y - prev))
        prev = y
    end
    check(maxStep <= 12, "after a timer jump the deck moves at most 12 units a frame (" .. maxStep .. ")")
end)

test("act 1: no barriers, lifts or books outside act 1; a stage that does not match keeps the mission offline", function()
    local w, A = world_with({ "A" })
    enter(w, A, 2)
    w:step(3)
    check(#Sim.objects_with(A, A.env.id_bhvSglMarstonSolid) == 0 and #Sim.objects_with(A, A.env.id_bhvSglMarstonLift) == 0,
        "act 2: no barriers, no lifts")
    enter(w, A, 4)
    w:step(5)
    check(Sim.hud_has(A, "COMING SOON %- NOTEBOOK PAGES") and #Sim.objects_with(A, A.env.id_bhvSglMarstonSolid) == 0,
        "act 4: coming soon, free roam, the stairs open")
    local w2, B = world_with({ "B" }, { floor = Sim.NO_FLOOR })
    enter(w2, B, 1)
    w2:step(5)
    check(Sim.find(B.console, "sleeps") ~= nil and #Sim.objects_with(B, B.env.id_bhvSglMarstonSolid) == 0,
        "without the Marston geometry: offline, no barriers spawned")
end)

test("act 1: down the book chute to the closed basement -> back to the lobby (no damage); acts 2-3 keep the basement open", function()
    local w, A = world_with({ "A" })
    local P = A.env.MARSTON_POINTS
    enter(w, A, 1)
    at(A, P.spawn)
    w:seconds(4)
    check(state(A) == MS.ACTIVE, "act 1 active")
    -- the chute's foot in the F1 sorting room (data/uf/marston_points.json circulation chute_bottom)
    at(A, { x = -2000, y = P.y_f1, z = -2170 })
    A.action = C.ACT_BUTT_SLIDE
    local hp = raw(A.ms[0]).health
    w:step(2)
    check(d2(A.pos, P.spawn) <= 90 and math.abs(A.pos.y - P.spawn.y) <= 30 and A.action == C.ACT_IDLE,
        string.format("sent back to the lobby (%.0f, %.0f, %.0f)", A.pos.x, A.pos.y, A.pos.z))
    check(raw(A.ms[0]).health == hp, "no damage")
    check(Sim.hud_has(A, "basement is closed"), "a toast says why")
    check(ctx_of(A).loc.basement == 1, "counted once")
    -- on F2 and F3 nothing happens
    at(A, P.board_a)
    w:step(3)
    check(d2(A.pos, P.board_a) < 1 and ctx_of(A).loc.basement == 1, "the F3 balcony is fine")
    -- act 3: the basement is where kiosk 1 and room L129 are
    enter(w, A, 3)
    at(A, P.kiosks[1])
    w:step(5)
    check(d2(A.pos, P.kiosks[1]) < 1, "act 3: standing on F1 is fine (no barriers, no lobby teleport)")
end)

test("act 1: flying books over the void at a player on a balcony: telegraph, hit (a wedge + knock-back), duck, punch", function()
    local w, A = world_with({ "A" })
    local P = A.env.MARSTON_POINTS
    local def = def_of(A, 1)
    enter(w, A, 1)
    at(A, P.spawn)
    w:seconds(4)
    check(state(A) == MS.ACTIVE, "active")
    local ctx = ctx_of(A)
    -- on the F2 court and on a lift: no books
    at(A, { x = P.board_a.x, y = P.y_f2, z = P.board_a.z })
    w:step(150)
    check(#ctx.objs.books == 0, "no books on the F2 court")
    -- out on the F3 balcony: a book after 3 s, over the void on the far side, at chest height + 0.3 m
    A.action = C.ACT_IDLE
    at(A, P.board_a)
    w:step(90)
    check(#ctx.objs.books == 1, "a flying book after 3 s on the balcony")
    local b = ctx.objs.books[1]
    check(b and not b.flying and b.x < P.atrium.x1 and b.x > P.atrium.x0 and b.y == P.board_a.y + 130, "it hovers over the void")
    check(b and raw(b.o)._model == C.E_MODEL_BOOKEND and raw(b.o)._anim == 0, "a bookend (animated)")
    check(Sim.hud_has(A, "BOOK!"), "marker BOOK!")
    -- standing still: it flies at me and hits
    local hit = nil
    for f = 1, 90 do
        w:step(1)
        if (A.hurts or 0) > 0 then hit = f break end
    end
    check(hit ~= nil and hit > 25, "it waits ~1 s, then hits (frame " .. tostring(hit) .. ")")
    check(A.action == C.ACT_BACKWARD_GROUND_KB and raw(A.ms[0]).hurtCounter == 4, "a knock-back and one wedge")
    w:step(3)
    check(#ctx.objs.books == 0, "the book is gone after its hit")
    -- the next one: duck under it
    A.action = C.ACT_CROUCHING
    local hurts = A.hurts
    for _ = 1, 210 + 60 + 30 do
        at(A, P.board_a)
        w:step(1)
    end
    check(A.hurts == hurts and (ctx.loc.hits or 0) == 1, "crouching: the books fly over")
    -- punch the next one away
    A.action = C.ACT_IDLE
    local whacked = false
    for _ = 1, 260 do
        at(A, P.board_a)
        local bk = ctx.objs.books[1]
        if bk ~= nil and bk.flying then
            -- meet it: stand where it is about to be and punch
            at(A, { x = bk.x + bk.vx * 2, y = P.board_a.y, z = bk.z + bk.vz * 2 })
            A.action = C.ACT_PUNCHING
        end
        w:step(1)
        if (ctx.loc.whacked or 0) > 0 then whacked = true break end
    end
    check(whacked and A.hurts == hurts, "a punch knocks the book away, no hit")
    -- riding lift A: none
    A.action = C.ACT_IDLE
    w:step(70)
    local lift = ctx.objs.lifts[1]
    local n0 = 0
    for _ = 1, 260 do
        A.pos.x, A.pos.y, A.pos.z = lift.x, lift.y + PTOP, lift.z
        w:step(1)
        n0 = n0 + #ctx.objs.books
    end
    check(n0 == 0, "no books at a player riding a lift")
    -- a book already in the air when its target steps onto a lift goes back to its shelf: no knock-back on a deck
    local hurts2, got = A.hurts, false
    for _ = 1, 300 do
        at(A, P.board_a)
        w:step(1)
        if #ctx.objs.books == 1 then got = true break end
    end
    check(got, "back on the balcony: a book again")
    A.pos.x, A.pos.y, A.pos.z = lift.x, lift.y + PTOP, lift.z
    w:step(2)
    check(#ctx.objs.books == 0 and (ctx.loc.liftSaves or 0) >= 1 and A.hurts == hurts2,
        "stepping onto a lift: the book flies back to its shelf, no hit")
    check(def.reachKind ~= nil and def.exposed ~= nil, "(kind exports)")
end)

test("act 1: flying-book hit test is pure: chest height, ducking, out of reach", function()
    local w, A = world_with({ "A" })
    local hits = A.env.sgl_marston_book_hits
    local p = { x = 0, y = 600, z = 0 }
    check(hits(p, C.ACT_IDLE, 50, 730, 0), "a book at chest height hits a standing player")
    check(not hits(p, C.ACT_CROUCHING, 50, 730, 0) and not hits(p, C.ACT_CRAWLING, 50, 730, 0), "ducking: it flies over")
    check(not hits(p, C.ACT_IDLE, 120, 730, 0), "1.2 m away: a miss")
    check(not hits(p, C.ACT_IDLE, 0, 820, 0), "over the head: a miss")
end)

---------------------------------------------------------------------------------------------
-- act 2: SHHH! LOST TEXTBOOKS
---------------------------------------------------------------------------------------------
test("noise: silent tiptoe / crouch / crawl / idle / fall; steps, running, jumps, punches, landings, crashes", function()
    local w, A = world_with({ "A" })
    local noise = A.env.sgl_marston_noise
    local N = A.env.SGL_MARSTON_NOISE
    check(noise(C.ACT_IDLE, 0) == 0 and noise(C.ACT_WALKING, 8) == 0, "standing and tiptoeing are silent")
    check(noise(C.ACT_CRAWLING, 10) == 0 and noise(C.ACT_CROUCHING, 0) == 0 and noise(C.ACT_FREEFALL, 0) == 0,
        "crawling, crouching and falling are silent")
    check(noise(C.ACT_WALKING, 15) == N.WALK and noise(C.ACT_WALKING, 30) == N.RUN, "steps 3 m, running 6 m")
    check(noise(C.ACT_JUMP, 20) == N.JUMP and noise(C.ACT_DOUBLE_JUMP, 0) == N.JUMP, "jumps")
    check(noise(C.ACT_PUNCHING, 0) == N.HIT and noise(C.ACT_JUMP_KICK, 0) == N.HIT, "punches and kicks")
    check(noise(C.ACT_JUMP_LAND, 0) == N.LAND and noise(C.ACT_FREEFALL_LAND, 0) == N.LAND, "landings")
    check(noise(C.ACT_GROUND_POUND_LAND, 0) == N.HARD and noise(C.ACT_DIVE_SLIDE, 0) == N.HARD, "ground pounds and dives crash")
    check(N.WALK < N.RUN and N.RUN <= N.LAND and N.LAND < N.HARD, "louder actions carry farther")
    -- marker tiers: how loud may I be at this distance
    local tier = A.env.sgl_marston_noise_tier
    check(tier(N.LAND + 1) == "RUN" and tier(N.LAND) == "WALK" and tier(N.WALK + 1) == "WALK" and tier(N.WALK) == "TIPTOE",
        "marker tiers: run beyond 7.5 m, walk beyond 3 m, tiptoe closer")
    local _, col = tier(100)
    check(col == A.env.SGL_HUD_RED and select(2, tier(2000)) == A.env.SGL_HUD_GREEN, "red close, green far")
    -- hold-L tiptoe: the stick capped at half tilt -> intendedMag 8, a silent walk
    local sx, sy, sm = A.env.sgl_marston_sneak_stick(64, 0, 64)
    local mag = ((sm / 64) ^ 2) * 64 / 2
    check(sm == 32 and sx == 32 and sy == 0 and mag <= N.WALK_V and noise(C.ACT_WALKING, mag) == 0,
        "the capped stick walks at intendedMag " .. mag .. ": silent")
    check(select(3, A.env.sgl_marston_sneak_stick(20, 0, 20)) == 20, "a small tilt is left alone")
end)

test("patrols: pure positions (loop and back-and-forth), the same Toads on two clients and for a late joiner", function()
    local w, A, B = world_with({ "A", "B" })
    local env = A.env
    local pts = { { x = 0, z = 0 }, { x = 100, z = 0 }, { x = 100, z = 100 } }
    local x, z = env.sgl_marston_patrol_pos(pts, false, 150)
    check(x == 100 and z == 50, "ping-pong: 150 along -> (100, 50)")
    local _, _, yawF = env.sgl_marston_patrol_pos(pts, false, 50)
    local xb, zb, yawB = env.sgl_marston_patrol_pos(pts, false, 350)
    check(xb == 50 and zb == 0 and ((yawB - yawF) & 0xFFFF) == 0x8000, "ping-pong: on the way back it faces back")
    local xl, zl = env.sgl_marston_patrol_pos(pts, true, 200 + 141.4213562 + 50)
    check(math.abs(xl - 50) < 0.01 and math.abs(zl - 0) < 0.01, "loop: wraps round the closing segment")
    local P = env.MARSTON_POINTS
    enter(w, A, 2); enter(w, B, 2)
    at(A, P.spawn); at(B, P.spawn)
    w:seconds(4)
    local ca, cb = ctx_of(A), ctx_of(B)
    local toads = Sim.objects_with(A, env.id_bhvSglMarstonProp)
    local nToad = 0
    for _, o in ipairs(toads) do if raw(o)._model == C.E_MODEL_TOAD then nToad = nToad + 1 end end
    check(nToad == 3 and raw(ca.objs.shushers[1].o)._anim == 6, "three Toad librarians (standing animation)")
    local same = true
    for _ = 1, 90 do
        w:step(1)
        for k = 1, 3 do
            local sa, sb = ca.objs.shushers[k], cb.objs.shushers[k]
            if sa.x ~= sb.x or sa.z ~= sb.z then same = false end
        end
    end
    check(same, "both clients see every Shusher at the same spot")
    local C3 = w:connect("C")
    prep(C3)
    w:step(3)
    enter(w, C3, 2)
    at(C3, P.spawn)
    w:step(5)
    local cc = ctx_of(C3)
    check(cc ~= nil and cc.objs.shushers ~= nil and cc.objs.shushers[2].x == ca.objs.shushers[2].x
        and cc.objs.shushers[2].z == ca.objs.shushers[2].z, "a late joiner's Shushers are in step at once")
end)

-- put client c `dist` units from Shusher k along `ang` (s16: 0 = its back... angle from its facing)
local function near_shusher(c, k, dist, rel, P)
    local sh = ctx_of(c).objs.shushers[k]
    local a = (sh.yaw + rel) & 0xFFFF
    local s, co = math.sin(a / 65536 * 2 * math.pi), math.cos(a / 65536 * 2 * math.pi)
    c.pos.x, c.pos.y, c.pos.z = sh.x + s * dist, P.y_f5, sh.z + co * dist
end

test("act 2: running near a Shusher -> SHHH!, back to the stairwell, no damage; the leader counts it; it pauses on both clients", function()
    local w, A, B = world_with({ "A", "B" })
    local P = A.env.MARSTON_POINTS
    enter(w, A, 2); enter(w, B, 2)
    at(A, P.quiet_start); at(B, P.quiet_start)
    w:seconds(4)
    check(state(A) == MS.ACTIVE, "active")
    local ca, cb = ctx_of(A), ctx_of(B)
    -- A runs 5 m behind Shusher 3 (the corridor): heard
    act_as(A, C.ACT_WALKING, 28)
    near_shusher(A, 3, 500, 0x8000, P)
    local health = A.health
    w:step(1)
    check(d2(A.pos, P.quiet_start) < 150 and A.pos.y == P.quiet_start.y + 20, "teleported back to the stairwell door")
    check(A.health == health and (A.hurts or 0) == 0, "no damage")
    check(A.action == C.ACT_IDLE, "standing")
    check(Sim.hud_has(A, "SHHH!"), "SHHH! on screen")
    w:step(3)
    check(ca.c == 1 and cb.c == 1, "the team's shush count is 1 on both clients")
    check(A.env.sgl_marston_units_of(ca.g, 3) == 2, "Shusher 3 gets 2 pause units (4 s)")
    check(Sim.find(B.hudLog, "A got shushed") ~= nil or Sim.hud_has(B, "A got shushed"), "B is told")
    -- both clients' Shusher 3 stand still for the pause, then walk on together
    local sa, sb = ca.objs.shushers[3], cb.objs.shushers[3]
    local x0, z0 = sa.x, sa.z
    w:step(60)
    check(sa.paused and sb.paused and sa.x == x0 and sa.z == z0, "Shusher 3 stands still (shushing) on A's client")
    check(sb.x == sa.x and sb.z == sa.z, "... and at the same spot on B's")
    w:step(90)
    check(not sa.paused and (sa.x ~= x0 or sa.z ~= z0), "after 4 s it walks on")
    check(sb.x == sa.x and sb.z == sa.z, "both clients agree again")
    -- after the 2.5 s grace period, running close behind Shusher 1 is heard too
    act_as(A, C.ACT_WALKING, 28)
    near_shusher(A, 1, 400, 0x8000, P)
    w:step(1)
    check(d2(A.pos, P.quiet_start) < 150 and ca.loc.shushed == 2, "running behind Shusher 1: caught again")
    -- ... but not during the grace period right after a catch
    act_as(A, C.ACT_WALKING, 28)
    near_shusher(A, 2, 400, 0x8000, P)
    w:step(1)
    check(d2(A.pos, P.quiet_start) > 150 and ca.loc.shushed == 2, "within 2.5 s of a catch: grace")
    w:step(75)
    act_as(A, C.ACT_WALKING, 28)
    near_shusher(A, 2, 400, 0x8000, P)
    w:step(1)
    check(ca.loc.shushed == 3, "grace over: caught")
end)

test("act 2: tiptoeing or crawling past a Shusher's back is safe; in front of it (2 m) or bumping it is not", function()
    local w, A = world_with({ "A" })
    local P = A.env.MARSTON_POINTS
    enter(w, A, 2)
    at(A, P.quiet_start)
    w:seconds(4)
    local ctx = ctx_of(A)
    local function safe_frames(action, fvel, dist, rel, frames)
        for _ = 1, frames do
            act_as(A, action, fvel)
            near_shusher(A, 2, dist, rel, P)
            w:step(1)
            if ctx.loc.shushed ~= nil and ctx.loc.shushed > 0 then return false end
        end
        return true
    end
    check(safe_frames(C.ACT_WALKING, 8, 180, 0x8000, 60), "tiptoeing 1.8 m behind it: safe")
    check(safe_frames(C.ACT_CRAWLING, 10, 150, 0x6000, 60), "crawling 1.5 m beside-behind it: safe")
    check(safe_frames(C.ACT_IDLE, 0, 300, 0, 30), "standing still 3 m in front of it: not seen (beyond 2.2 m)")
    check(not safe_frames(C.ACT_IDLE, 0, 180, 0, 2), "standing still 1.8 m in front of it: seen")
    w:step(80)
    local n = ctx.loc.shushed
    check(not safe_frames(C.ACT_IDLE, 0, 90, 0x8000, 2) and ctx.loc.shushed == n + 1, "bumping into its back: caught")
end)

test("act 2: a half-heard noise makes a Shusher stop and look at the noise on every client (a friend can lure it)", function()
    local w, A, B = world_with({ "A", "B" })
    local P = A.env.MARSTON_POINTS
    enter(w, A, 2); enter(w, B, 2)
    at(A, P.quiet_start); at(B, P.quiet_start)
    w:seconds(4)
    local ca, cb = ctx_of(A), ctx_of(B)
    -- A runs 8 m from Shusher 2 (out of its 6 m hearing, inside 1.6 x): "hm"
    act_as(A, C.ACT_WALKING, 28)
    near_shusher(A, 2, 800, 0x4000, P)
    local spot = { x = A.pos.x, z = A.pos.z }
    w:step(1)
    check((ca.loc.shushed or 0) == 0 and d2(A.pos, P.quiet_start) > 150, "not caught")
    act_as(A, C.ACT_IDLE, 0)
    w:step(4)
    check(A.env.sgl_marston_units_of(ca.g, 2) == 1, "the leader gives Shusher 2 one pause unit")
    w:step(25)
    local sa, sb = ca.objs.shushers[2], cb.objs.shushers[2]
    check(sa.paused and sb.paused, "it stops on both clients")
    local want = A.env.atan2s(spot.z - sb.z, spot.x - sb.x)
    local diff = ((sb.yaw - want + 0x8000) & 0xFFFF) - 0x8000
    check(math.abs(diff) < 0x400, "on B's client it turns to look at A's noise")
    -- B tiptoes 1.5 m in front of where it walked: it looks away (at A), so B is not seen
    local away = (sb.yaw + 0x8000) & 0xFFFF
    local s, c = math.sin(away / 65536 * 2 * math.pi), math.cos(away / 65536 * 2 * math.pi)
    B.pos.x, B.pos.y, B.pos.z = sb.x + s * 150, P.y_f5, sb.z + c * 150
    act_as(B, C.ACT_WALKING, 6)
    w:step(10)
    check((cb.loc.shushed or 0) == 0, "B sneaks past behind its back")
    -- the leader does not stack pauses from repeated noise within one pause (A again, then B, half-heard)
    act_as(A, C.ACT_WALKING, 28)
    near_shusher(A, 2, 800, 0x4000, P)
    w:step(1)
    act_as(A, C.ACT_IDLE, 0)
    act_as(B, C.ACT_WALKING, 28)
    near_shusher(B, 2, 800, 0xC000, P)
    w:step(1)
    act_as(B, C.ACT_IDLE, 0)
    w:step(3)
    check((cb.loc.shushed or 0) == 0, "(B half-heard, not caught)")
    check(A.env.sgl_marston_units_of(ca.g, 2) == 1, "no second unit within the same pause, from anyone")
    -- after the pause, a new noise gives a new unit
    w:step(80)
    act_as(B, C.ACT_WALKING, 28)
    near_shusher(B, 2, 800, 0xC000, P)
    w:step(1)
    act_as(B, C.ACT_IDLE, 0)
    w:step(3)
    check(A.env.sgl_marston_units_of(ca.g, 2) == 2, "a later noise: another pause unit")
end)

test("act 2: 8 shared textbooks (lost event re-sent) -> star at the west window desk; still shushing until DONE", function()
    local w, A, B = world_with({ "A", "B" })
    local P = A.env.MARSTON_POINTS
    enter(w, A, 2); enter(w, B, 2)
    at(A, P.quiet_start); at(B, P.quiet_start)
    w:seconds(4)
    local ca, cb = ctx_of(A), ctx_of(B)
    local books = Sim.objects_with(A, A.env.id_bhvSglMarstonProp)
    local nBook = 0
    for _, o in ipairs(books) do if raw(o)._model == C.E_MODEL_BREAKABLE_BOX_SMALL then nBook = nBook + 1 end end
    check(nBook == 8, "8 textbooks to find")
    check(Sim.hud_has(A, "Textbooks 0/8"), "panel: 0/8")
    -- the Shushers are parked for this test (nobody judges the book hunters)
    ca.objs.shushers, cb.objs.shushers = {}, {}
    local function quiet(c) act_as(c, C.ACT_IDLE, 0) end
    quiet(A); quiet(B)
    -- B finds book 1, but the event is lost (the leader A never hears it): B sends it again after 3 s
    at(B, P.books[1])
    local saved = w.deliver
    w.deliver = function(self)
        for i = #self.queue, 1, -1 do
            local msg = self.queue[i]
            if msg.kind == "packet" and msg.data.ev == "book" and msg.from == B then table.remove(self.queue, i) end
        end
        w.deliver = saved
        return saved(self)
    end
    for _ = 1, 3 do
        at(B, P.books[1])
        w:step(1)
    end
    check((ca.f & 1) == 0, "lost: the leader has not got it")
    at(B, P.spawn)
    w:step(95)
    check((ca.f & 1) ~= 0 and ca.p == 1, "re-sent: book 1 counted")
    for i = 2, 8 do
        local c = (i % 2 == 0) and A or B
        at(c, P.books[i])
        w:step(3)
        at(c, P.spawn)
    end
    w:step(3)
    check(ca.p == 8 and state(A) == MS.SUCCESS and state(B) == MS.SUCCESS, "all 8: success")
    w:step(3)
    check(#A.starSpawns == 1 and Sim.stars_of(A, 1) == 1 and Sim.stars_of(B, 1) == 1, "one star (id 1)")
    local sp = A.starSpawns[1]
    check(sp and sp.x == P.quiet_star.x and sp.z == P.quiet_star.z and sp.y == P.quiet_star.y, "by the west window desk")
    check(Sim.find(A.hudLog, "found the") ~= nil or Sim.find(B.hudLog, "found the") ~= nil, "friends' finds are announced")
    -- SUCCESS: the Shushers still catch noisy players on the way to the star
    local w2, C2 = world_with({ "C" })
    enter(w2, C2, 2)
    at(C2, P.quiet_start)
    w2:seconds(4)
    local cc = ctx_of(C2)
    act_as(C2, C.ACT_IDLE, 0)
    for i = 1, 8 do cc:send("book", { i = i, nm = "C" }) end
    w2:step(3)
    check(state(C2) == MS.SUCCESS and cc.p == 8, "solo: all 8 -> success")
    act_as(C2, C.ACT_WALKING, 28)
    near_shusher(C2, 1, 400, 0x8000, P)
    w2:step(1)
    check(d2(C2.pos, P.quiet_start) < 150, "after the 8th book the Shushers still send you back")
    local star = Sim.objects_with(C2, C.id_bhvStarSpawnCoordinates)[1]
    Sim.run_hooks(C2, C.HOOK_ON_INTERACT, C2.ms[0], star, C.INTERACT_STAR_OR_KEY, true)
    raw(star).activeFlags = C.ACTIVE_FLAG_DEACTIVATED
    w2:step(80)
    check(state(C2) == MS.DONE, "DONE")
    local n = cc.loc.shushed
    act_as(C2, C.ACT_WALKING, 28)
    near_shusher(C2, 1, 400, 0x8000, P)
    w2:step(2)
    check(cc.loc.shushed == n, "DONE: free roam, nobody shushes")
end)

test("act 2: holding L on the quiet floor caps the stick (keyboard tiptoe); markers coloured by safe loudness", function()
    local w, A = world_with({ "A" })
    local P = A.env.MARSTON_POINTS
    enter(w, A, 2)
    at(A, P.quiet_start)
    w:seconds(4)
    check(state(A) == MS.ACTIVE, "active")
    local function stick_after(pressed, y)
        A.pos.y = y
        A.stickMag = 64
        A.pressed = pressed
        w:step(1)
        A.stickMag = 0
        return A.lastInput.stickMag
    end
    check(stick_after(C.L_TRIG, P.y_f5) == 32, "L held on floor 5: half tilt")
    check(stick_after(0, P.y_f5) == 64, "without L: full tilt")
    check(stick_after(C.L_TRIG, P.y_f4) == 64, "L on floor 4: untouched")
    A.pos.y = P.y_f5
    -- the Shusher markers: red close by, green far away
    near_shusher(A, 1, 200, 0x8000, P)
    w:step(1)
    check(Sim.hud_has(A, "SHH TIPTOE") or Sim.hud_has(A, "%? TIPTOE"), "2 m from Shusher 1: TIPTOE")
    check(Sim.hud_has(A, "Librarian markers"), "the panel explains the colours")
    -- act 1: L does nothing
    local w1, B = world_with({ "B" })
    enter(w1, B, 1)
    at(B, P.spawn)
    w1:seconds(4)
    B.pos.y = P.y_f5
    B.stickMag, B.pressed = 64, C.L_TRIG
    w1:step(1)
    check(B.lastInput.stickMag == 64, "act 1: L leaves the stick alone")
end)

test("act 2: D-pad Down takes you to the quiet floor; the panel says so below floor 5", function()
    local w, A = world_with({ "A" })
    local P = A.env.MARSTON_POINTS
    enter(w, A, 2)
    at(A, P.spawn)
    w:seconds(4)
    check(Sim.hud_has(A, "QUIET FLOOR %(5F%)"), "marker: QUIET FLOOR (5F)")
    A.pressed = C.D_JPAD
    w:step(2)
    check(d2(A.pos, P.quiet_start) < 150 and math.abs(A.pos.y - P.y_f5) < 50, "D-pad Down: at the stairwell door on floor 5")
    check(Sim.find(A.hudLog, "The quiet floor") ~= nil or Sim.hud_has(A, "The quiet floor"), "toast: the quiet floor")
    A.pressed = C.D_JPAD
    local x, z = A.pos.x, A.pos.z
    w:step(1)
    check(A.pos.x == x and A.pos.z == z, "already there: nothing")
end)

---------------------------------------------------------------------------------------------
-- act 3: STUDY ROOM BOOKING - 2P
---------------------------------------------------------------------------------------------
local function kiosk_obj(c, i) return ctx_of(c).objs.kiosks[i] end

local function punch_at(c, k)
    at(c, k)
    c.pos.x = k.x + 120
    act_as(c, C.ACT_PUNCHING, 0)
end

local function code_of(c, i) return c.env.sgl_marston_code_of(ctx_of(c).o, i) end

-- punch kiosk i n times (15+ frames apart, the kiosk's repeat guard), every client of `who` = { {c, i, n}, ... } in
-- step; then wait for the read-out (1 s after the last punch)
local function punch_codes(w, P, who)
    local most = 0
    for _, e in ipairs(who) do most = math.max(most, e[3]) end
    for r = 1, most do
        for _, e in ipairs(who) do if r <= e[3] then punch_at(e[1], P.kiosks[e[2]]) end end
        w:step(2)
        for _, e in ipairs(who) do act_as(e[1], C.ACT_IDLE, 0) end
        w:step(14)
    end
    w:step(32)
end

-- book kiosk i from client c with the right code
local function book(w, P, c, i) punch_codes(w, P, { { c, i, code_of(c, i) } }) end

test("act 3 alone: waiting for a second player; kiosks 1F + 5F lit, the room locked; the LibCal two-person rule", function()
    local w, A = world_with({ "A" })
    local P = A.env.MARSTON_POINTS
    enter(w, A, 3)
    at(A, P.spawn)
    w:seconds(4)
    check(state(A) == MS.WAITING, "waiting")
    check(Sim.hud_has(A, "This act needs 2 players"), "needs 2 players")
    local ctx = ctx_of(A)
    check(not kiosk_obj(A, 1).body.off and kiosk_obj(A, 2).body.off and kiosk_obj(A, 3).body.off and not kiosk_obj(A, 4).body.off,
        "kiosks 1 and 4 solid, 2 and 3 gone")
    check(not ctx.objs.door.off, "room L129's lock is shut (solid)")
    check(raw(ctx.objs.door.o).collisionData == "COL:checkerboard_platform", "the lock has collision")
    check(code_of(A, 1) >= 1 and code_of(A, 1) <= 3 and code_of(A, 4) >= 1 and code_of(A, 4) <= 3
        and code_of(A, 2) == 0 and code_of(A, 3) == 0, "booking codes 1-3 on the lit kiosks only")
end)

test("act 3: a kiosk's screen shows the OTHER kiosks' codes; the right code books it, a wrong one buzzes", function()
    local w, A, B = world_with({ "A", "B" })
    local P = A.env.MARSTON_POINTS
    enter(w, A, 3); enter(w, B, 3)
    at(A, P.spawn); at(B, P.spawn)
    w:seconds(4)
    check(state(A) == MS.ACTIVE, "active")
    local ca, cb = ctx_of(A), ctx_of(B)
    check(ca.o == cb.o and ca.o ~= 0, "the same codes on both clients")
    check(Sim.hud_has(A, "Walk to a lit kiosk"), "away from the kiosks: walk to one")
    at(A, P.kiosks[1]); A.pos.x = A.pos.x + 120
    w:step(2)
    local k4 = string.format("5F WEST WING: punch %d time", code_of(A, 4))
    check(Sim.hud_has(A, k4), "A at kiosk 1 reads kiosk 4's code")
    check(not Sim.hud_has(A, "1F BY ROOM L129: punch"), "... but not its own")
    -- a wrong code
    local wrong = code_of(A, 1) % 3 + 1
    punch_codes(w, P, { { A, 1, wrong } })
    check(ca.f == 0 and (ca.loc.wrong or 0) == 1, "wrong code: not booked")
    check(Sim.find(A.hudLog, "Wrong code") ~= nil or Sim.hud_has(A, "Wrong code"), "toast: wrong code")
    check(Sim.find(B.hudLog, "A punched a wrong code") ~= nil or Sim.hud_has(B, "A punched a wrong code"), "B is told")
    -- the right one
    book(w, P, A, 1)
    check((ca.f & 1) ~= 0 and (cb.f & 1) ~= 0 and ca.c >= 3, "right code: kiosk 1 booked, the window open (both clients)")
    check(Sim.find(B.hudLog, "A booked kiosk 1F BY ROOM L129") ~= nil or Sim.hud_has(B, "A booked kiosk 1F BY ROOM L129"),
        "B is told")
end)

test("act 3 with 2 players: one kiosk alone expires after 4 s (new codes); both within 4 s -> L129 opens -> star inside", function()
    local w, A, B = world_with({ "A", "B" })
    local P = A.env.MARSTON_POINTS
    enter(w, A, 3); enter(w, B, 3)
    at(A, P.spawn); at(B, P.spawn)
    w:seconds(4)
    check(state(A) == MS.ACTIVE and state(B) == MS.ACTIVE, "active")
    local ca, cb = ctx_of(A), ctx_of(B)
    check(ca.a == 2 and Sim.hud_has(A, "all 2 kiosks within 4 s"), "2 kiosks to book")
    check(Sim.hud_has(A, "KIOSK 1F BY ROOM L129") and Sim.hud_has(A, "KIOSK 5F WEST WING"), "markers on the two lit kiosks")
    -- A books kiosk 1 alone
    book(w, P, A, 1)
    check((ca.f & 1) ~= 0 and Sim.hud_has(A, "BOOKING OPEN"), "kiosk 1 booked, the panel says the booking is open")
    -- punching it again does not refresh it
    w:seconds(1)
    punch_codes(w, P, { { A, 1, code_of(A, 1) } })
    local codes = ca.o
    w:seconds(2.5)
    check(ca.f == 0 and ca.p == 1, "4 s later: expired (re-punching did not extend it), 1 expired booking")
    check(Sim.find(A.hudLog, "Booking expired") ~= nil or Sim.hud_has(A, "Booking expired"), "toast: expired, new codes")
    check(code_of(A, 1) >= 1 and code_of(A, 4) >= 1, "fresh codes on the lit kiosks")
    check(state(A) == MS.ACTIVE, "still active (try again)")
    -- both together: booked
    punch_codes(w, P, { { A, 1, code_of(A, 1) }, { B, 4, code_of(B, 4) } })
    w:step(2)
    check(state(A) == MS.SUCCESS and state(B) == MS.SUCCESS, "both within 4 s: success")
    w:step(2)
    check(ca.objs.door.off and cb.objs.door.off, "room L129's lock opens on both clients")
    check(Sim.find(A.hudLog, "Room L129 is booked") ~= nil or Sim.hud_has(A, "Room L129 is booked"), "toast: booked")
    w:step(2)
    check(Sim.stars_of(A, 2) == 1 and Sim.stars_of(B, 2) == 1, "one star (id 2) on each client")
    local sp = A.starSpawns[1] or B.starSpawns[1]
    check(sp and sp.x == P.room_star.x and sp.z == P.room_star.z, "inside L129")
    local star = Sim.objects_with(B, C.id_bhvStarSpawnCoordinates)[1]
    Sim.run_hooks(B, C.HOOK_ON_INTERACT, B.ms[0], star, C.INTERACT_STAR_OR_KEY, true)
    w:step(4)
    check(state(A) == MS.DONE and state(B) == MS.DONE, "collected: DONE")
    check(codes ~= nil, "(codes read)")
end)

test("act 3: K1 then K4 5 s later is too slow; an unlit kiosk does not count", function()
    local w, A, B = world_with({ "A", "B" })
    local P = A.env.MARSTON_POINTS
    enter(w, A, 3); enter(w, B, 3)
    at(A, P.spawn); at(B, P.spawn)
    w:seconds(4)
    local ca = ctx_of(A)
    book(w, P, A, 1)
    w:seconds(4)
    book(w, P, B, 4)
    check(state(A) == MS.ACTIVE and ca.f == 8, "too slow: only kiosk 4 booked now")
    punch_codes(w, P, { { A, 2, 1 }, })     -- unlit with 2 players
    check(state(A) == MS.ACTIVE and ca.f == 8, "the 2F kiosk is not lit for 2 players: ignored")
end)

test("act 3: everyone at a kiosk -> the HUD counts in 3-2-1-PUNCH!", function()
    local w, A, B = world_with({ "A", "B" })
    local P = A.env.MARSTON_POINTS
    enter(w, A, 3); enter(w, B, 3)
    at(A, P.spawn); at(B, P.spawn)
    w:seconds(4)
    local ca = ctx_of(A)
    at(A, P.kiosks[1]); A.pos.x = A.pos.x + 150
    at(B, P.kiosks[4]); B.pos.x = B.pos.x + 150
    w:step(3)
    check(ca.g == 0x9 and ca.x == 3, "both ready: 3")
    check(Sim.hud_has(A, "ready"), "panel: ready")
    w:step(31)
    check(ca.x == 2, "2")
    w:step(30)
    check(ca.x == 1, "1")
    w:step(30)
    check(ca.x == 9 and Sim.hud_has(B, "PUNCH!"), "PUNCH!")
    w:step(50)
    check(ca.x == 0, "then quiet (no repeat while they stay)")
    B.pos.x = B.pos.x + 900
    w:step(3)
    B.pos.x = B.pos.x - 900
    w:step(3)
    check(ca.x == 3, "someone stepped off and back: counted in again")
end)

test("act 3: 3 players light 1F + 4F + 5F, 4 players all four; a booking needs every lit kiosk", function()
    local w, A, B, Cc = world_with({ "A", "B", "C" })
    local P = A.env.MARSTON_POINTS
    for _, c in ipairs({ A, B, Cc }) do enter(w, c, 3); at(c, P.spawn) end
    w:seconds(4)
    local ca = ctx_of(A)
    check(ca.a == 3 and not kiosk_obj(A, 3).body.off and kiosk_obj(A, 2).body.off, "3 players: kiosks 1, 3, 4")
    punch_codes(w, P, { { A, 1, code_of(A, 1) }, { B, 4, code_of(B, 4) } })
    check(state(A) == MS.ACTIVE and ca.f == 0x9, "two of three: not yet")
    book(w, P, Cc, 3)
    check(state(A) == MS.SUCCESS, "the third one: booked")
    local w4, A4, B4, C4, D4 = world_with({ "A", "B", "C", "D" })
    for _, c in ipairs({ A4, B4, C4, D4 }) do enter(w4, c, 3); at(c, P.spawn) end
    w4:seconds(4)
    local c4 = ctx_of(A4)
    check(c4.a == 4 and not kiosk_obj(A4, 2).body.off, "4 players: all four kiosks")
    punch_codes(w4, P, { { A4, 1, code_of(A4, 1) }, { B4, 2, code_of(B4, 2) }, { C4, 3, code_of(C4, 3) } })
    check(state(A4) == MS.ACTIVE and c4.f == 0x7, "three of four: not yet")
    book(w4, P, D4, 4)
    check(state(A4) == MS.SUCCESS, "all four: booked")
    -- a player leaving drops the count (and clears the open window)
    local w3, A3, B3, C3 = world_with({ "A", "B", "C" })
    for _, c in ipairs({ A3, B3, C3 }) do enter(w3, c, 3); at(c, P.spawn) end
    w3:seconds(4)
    w3:disconnect(C3)
    w3:step(3)
    check(ctx_of(A3).a == 2 and kiosk_obj(A3, 3).body.off, "a player leaves: back to 2 kiosks")
    check(code_of(A3, 3) == 0 and code_of(A3, 1) >= 1, "codes for the 2 lit kiosks only")
end)

test("act 3: D-pad Down only back to a kiosk you walked to; refused right after your own booking (no booking two alone)", function()
    local w, A, B = world_with({ "A", "B" })
    local P = A.env.MARSTON_POINTS
    enter(w, A, 3); enter(w, B, 3)
    at(A, P.spawn); at(B, P.kiosks[4])
    B.pos.x = B.pos.x + 150
    w:seconds(4)
    A.pressed = C.D_JPAD
    w:step(2)
    check(d2(A.pos, P.spawn) < 10, "no kiosk reached yet: D-pad Down refused (the first trip is on foot)")
    check(Sim.find(A.hudLog, "Walk to a lit kiosk first") ~= nil or Sim.hud_has(A, "Walk to a lit kiosk first"), "toast says so")
    -- walk to kiosk 1, leave, D-pad Down: back there
    at(A, P.kiosks[1]); A.pos.x = A.pos.x + 150
    w:step(2)
    at(A, P.spawn)
    w:step(2)
    check(Sim.hud_has(A, "D%-pad Down: back to a kiosk you have reached"), "panel: D-pad Down goes back")
    A.pressed = C.D_JPAD
    w:step(2)
    check(d2(A.pos, P.kiosks[1]) < 350 and math.abs(A.pos.y - P.kiosks[1].y) < 50, "back at kiosk 1")
    local k1 = P.kiosks[1]
    check(A.pos.z < k1.z - 100 and A.face.y == k1.yaw, "on kiosk 1's approach side (north of it, L127's glass is east), facing it")
    -- kiosk 4: walked to by B, never by A, and taken: never offered to A
    check(A.env.sgl_mission_get(CCM, 3).freeKiosk(ctx_of(A), A.pos, ctx_of(A).loc.reached) == 1, "only kiosk 1 is A's")
    book(w, P, A, 1)
    A.pos.x = A.pos.x + 900
    w:step(2)
    local x = A.pos.x
    A.pressed = C.D_JPAD
    w:step(2)
    check(A.pos.x == x, "right after booking kiosk 1: refused")
    check(state(A) == MS.ACTIVE, "(no booking)")
    w:seconds(6.5)
    A.pressed = C.D_JPAD
    w:step(2)
    check(d2(A.pos, P.kiosks[1]) < 350, "after the window + 2 s: allowed again")
end)

---------------------------------------------------------------------------------------------
-- whole mod
---------------------------------------------------------------------------------------------
test("whole mod: every file loads with the Marston missions; /campus marston 3 moves everyone; act 4 is coming soon", function()
    local built = Sim.built_on_disk()
    built[CCM] = true
    local w = Sim.new({ files = Sim.ALL_FILES, built = built })
    local H = prep(w:connect("Host"))
    local F = prep(w:connect("Friend"))
    for _, c in ipairs({ H, F }) do
        c.stubs.gObjectAnimations.sushi_seg5_anims_0500AE54 = "ANIM:sushi"
        c.stubs.gObjectAnimations.swoop_seg6_anims_060070D0 = "ANIM:swoop"
    end
    w:step(3)
    w:warp(H, HUB, 1, 0); w:warp(F, HUB, 1, 0)
    w:step(40)
    local has = false
    for _, f in ipairs(Sim.ALL_FILES) do if f == "uf_marston_missions.lua" then has = true end end
    check(has, "uf_marston_missions.lua is a mod file")
    local order = table.concat(Sim.ALL_FILES, " ")
    local a, b, c2 = order:find("sgl_mission.lua", 1, true), order:find("uf_lake_missions.lua", 1, true), order:find("uf_marston_missions.lua", 1, true)
    check(a ~= nil and b ~= nil and c2 ~= nil and a < b and b < c2,
        "it loads after sgl_mission.lua (strcmp order): " .. order)
    check(H.env.sgl_mission_get(CCM, 3) ~= nil and H.env.sgl_mission_get(C.LEVEL_JRB, 3) ~= nil, "Marston + Lake missions registered")
    local ok = pcall(Sim.cmd, H, "campus", "marston 3")
    w:step(5)
    if ok and H.level == CCM then
        check(H.act == 3 and F.level == CCM and F.act == 3, "/campus marston 3: everyone to Marston act 3")
        w:seconds(4)
        check(state(H) == MS.ACTIVE and ctx_of(H).a == 2, "the booking is on (2 kiosks)")
    else
        check(false, "/campus marston 3 did not warp (levels.lua key 'marston')")
    end
    -- levels.lua's interior camera: Marston's settings while in it (collision on), the player's own back in the hub
    check(H.cam.inDist == 650 and H.cam.outDist == 1000 and H.cam.inHeight == 220 and H.cam.outHeight == 330
        and H.cam.collisions == 1, "in Marston: the rom-hack camera is closer and lower, with collision")
    w:warp(H, CCM, 1, 4)
    w:step(5)
    check(Sim.hud_has(H, "COMING SOON %- NOTEBOOK PAGES"), "act 4: coming soon notice")
    local sets = H.cam.sets
    w:step(10)
    check(H.cam.sets == sets, "settings written once, not every frame")
    w:warp(H, HUB, 1, 0)
    w:step(5)
    check(H.cam.inDist == 900 and H.cam.outDist == 1400 and H.cam.inHeight == 300 and H.cam.outHeight == 450
        and H.cam.collisions == 0, "back in the hub: the player's own camera settings")
end)

print(string.format("\n%d checks passed, %d failed", passed, failed))
os.exit(failed == 0 and 0 or 1)
