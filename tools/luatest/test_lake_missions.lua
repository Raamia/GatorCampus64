-- Unit + scenario tests for mods/sgl64/uf_lake_missions.lua (course 3, Lake Alice, LEVEL_JRB) in the offline
-- multi-client coopdx simulation (sim.lua), plus the act-select / level-script contract for course 3
-- (docs/flow.md 5.1) against the real course.lua and, once built, the real levels/jrb/script.c.
-- Run: tools/luatest/run.sh   (or: lua tools/luatest/test_lake_missions.lua)
--
-- The engine names only the lake missions use are stubbed here, per client (prep below), and each one is
-- checked to be a real sm64coopdx v1.5.1 binding first: the lighting globals of gfx_pc.c (set_/get_lighting_color,
-- _ambient, _dir, set_/get_vertex_color, set_/get_fog_color, set_/get_fog_intensity, set_/get_skybox_color; u8
-- colour channels must be integers), obj_init_animation + gObjectAnimations (the swoop and sushi animations of
-- the bat and gator stand-ins) and hurt_and_set_mario_action (a big gator's bite).
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

local JRB, HUB = C.LEVEL_JRB, C.LEVEL_CASTLE_GROUNDS
local MS = { IDLE = 0, WAITING = 1, INTRO = 2, ACTIVE = 3, SUCCESS = 4, FAILED = 5, DONE = 6 }
local FILES = { "course.lua", "sgl_deepspace.lua", "sgl_hud.lua", "sgl_mission.lua", "swamp_chomp.lua", "swamp_missions.lua", "uf_lake_missions.lua" }
local PTOP = 26

-- the extra engine names (see the header), all real v1.5.1 bindings
local EXTRA = { "set_lighting_color", "set_lighting_color_ambient", "set_lighting_dir", "set_vertex_color", "set_fog_color",
    "set_fog_intensity", "set_skybox_color", "get_lighting_color", "get_lighting_color_ambient", "get_lighting_dir",
    "get_vertex_color", "get_fog_color", "get_fog_intensity", "get_skybox_color", "obj_init_animation",
    "hurt_and_set_mario_action" }
for _, n in ipairs(EXTRA) do assert(API[n] ~= nil, n .. " is a v1.5.1 binding") end

local DEFAULT_LIGHT = function()
    return { light = { 255, 255, 255 }, ambient = { 255, 255, 255 }, vertex = { 255, 255, 255 }, fog = { 255, 255, 255 },
        sky = { 255, 255, 255 }, dir = { 0, 0, 0 }, fogIntensity = 1.0, sets = 0 }
end

local function prep(c)
    local S = c.stubs
    c.light = DEFAULT_LIGHT()
    local L = c.light
    local function idx(i) assert(math.type(i) == "integer" and i >= 0 and i <= 2, "lighting index must be 0..2") end
    local function u8(v, what)
        assert(math.type(v) == "integer" and v >= 0 and v <= 255, what .. " must be an integer 0..255, got " .. tostring(v))
    end
    local function setter(key, what, both)
        return function(i, v)
            idx(i); u8(v, what)
            L[key][i + 1] = v
            if both then L.ambient[i + 1] = v end   -- coopdx: set_lighting_color also sets the ambient colour
            L.sets = L.sets + 1
        end
    end
    S.set_lighting_color = setter("light", "set_lighting_color", true)
    S.set_lighting_color_ambient = setter("ambient", "set_lighting_color_ambient")
    S.set_vertex_color = setter("vertex", "set_vertex_color")
    S.set_fog_color = setter("fog", "set_fog_color")
    S.set_skybox_color = setter("sky", "set_skybox_color")
    S.set_lighting_dir = function(i, v) idx(i); assert(type(v) == "number"); L.dir[i + 1] = v end
    S.set_fog_intensity = function(v) assert(type(v) == "number"); L.fogIntensity = v end
    S.get_lighting_color = function(i) idx(i); return L.light[i + 1] end
    S.get_lighting_color_ambient = function(i) idx(i); return L.ambient[i + 1] end
    S.get_vertex_color = function(i) idx(i); return L.vertex[i + 1] end
    S.get_fog_color = function(i) idx(i); return L.fog[i + 1] end
    S.get_skybox_color = function(i) idx(i); return L.sky[i + 1] end
    S.get_lighting_dir = function(i) idx(i); return L.dir[i + 1] end
    S.get_fog_intensity = function() return L.fogIntensity end
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
    S.gObjectAnimations = { swoop_seg6_anims_060070D0 = "ANIM:swoop", sushi_seg5_anims_0500AE54 = "ANIM:sushi" }
    local m = raw(c.ms[0])
    m.invincTimer, m.hurtCounter, m.flags = 0, 0, 0
    return c
end

-- connect players named A, B, ... (gi 0, 1, ...) with Lake Alice built; they sync in the hub
local function world_with(names, opts)
    opts = opts or {}
    opts.files = opts.files or FILES
    opts.built = opts.built or { [HUB] = true, [C.LEVEL_BOB] = true, [JRB] = true }
    local w = Sim.new(opts)
    local cs = {}
    for _, n in ipairs(names) do table.insert(cs, prep(w:connect(n))) end
    w:step(3)
    return w, table.unpack(cs)
end

local function enter(w, c, act) w:warp(c, JRB, 1, act) end

local function at(c, p, dy)
    c.pos.x, c.pos.y, c.pos.z = p.x, p.y + (dy or 0), p.z
end

local function ctx_of(c) return Sim.ctx(c) end

local function state(c)
    local ctx = ctx_of(c)
    return ctx and ctx.s or nil
end

local function def_of(c, act) return c.env.sgl_mission_get(JRB, act) end

local function lit(c)       -- the lighting differs from the vanilla defaults
    local d = DEFAULT_LIGHT()
    for _, k in ipairs({ "light", "ambient", "vertex", "fog", "sky" }) do
        for i = 1, 3 do if c.light[k][i] ~= d[k][i] then return true end end
    end
    return false
end

local function is_default_light(c)
    local d = DEFAULT_LIGHT()
    for _, k in ipairs({ "light", "ambient", "vertex", "fog", "sky", "dir" }) do
        for i = 1, 3 do if c.light[k][i] ~= d[k][i] then return false end end
    end
    return c.light.fogIntensity == 1.0
end

---------------------------------------------------------------------------------------------
-- registry, act names, act select, level script, coordinates
---------------------------------------------------------------------------------------------
test("registry: three Lake Alice missions on acts 1/2/3, star ids act-1, titles = course.lua act names, acts 4-6 coming soon", function()
    local w, A = world_with({ "A" })
    local env = A.env
    local d1, d2, d3 = def_of(A, 1), def_of(A, 2), def_of(A, 3)
    check(d1 and d1.id == "lake_boardwalk" and d1.starId == 0 and d1.minPlayers == 1, "act 1 boardwalk, star 0, solo")
    check(d2 and d2.id == "lake_gator_hop" and d2.starId == 1 and d2.minPlayers == 1, "act 2 gator hop, star 1, solo")
    check(d3 and d3.id == "lake_bat_census" and d3.starId == 2 and d3.minPlayers == 2, "act 3 bat census, star 2, 2+ players")
    local stage = env.sgl_stage_by_level(JRB)
    check(stage ~= nil and stage.key == "alice" and stage.door == 3 and stage.stars == 5 and stage.course == C.COURSE_JRB
        and stage.acts ~= nil, "course.lua: door 3 = LAKE ALICE (5 stars, COURSE_JRB) with act names")
    for _, d in ipairs({ d1, d2, d3 }) do
        check((d.bparams >> 24) == d.starId, d.id .. " bparams carry the star id")
        check(stage.acts[d.act] == d.title, d.id .. " title matches course.lua act " .. d.act .. " (" .. tostring(stage.acts[d.act]) .. ")")
        check(not env.sgl_act_is_soon(stage, d.act), d.id .. " act is not 'coming soon'")
        check(d.probes ~= nil and #d.probes >= 2, d.id .. " has geometry probes")
        check(#d.objective <= 60, d.id .. " objective fits the banner (" .. #d.objective .. " chars)")
        check(d.pointsFile ~= nil and d.pointsFile:find("uf_lake_missions.lua", 1, true) ~= nil, d.id .. " names its points file")
        check(not d.levelStar, d.id .. " spawns its own star")
    end
    for act = 4, 6 do
        check(env.sgl_mission_get(JRB, act) == nil, "act " .. act .. " has no mission yet")
        check(env.sgl_act_is_soon(stage, act) and stage.acts[act]:find("^COMING SOON") ~= nil,
            "act " .. act .. " is named COMING SOON: " .. tostring(stage.acts[act]))
    end
    for act = 1, 6 do
        check(not stage.acts[act]:find("[^A-Z0-9 '%.,%-&!%?]") and #stage.acts[act] <= 28,
            "act " .. act .. " name fits the act-select menu font: " .. stage.acts[act])
    end
    check(env.sgl_mission_get(C.LEVEL_BOB, 1).id == "swamp_skybox" and #env.SGL_MISSION_LIST == 6, "3 Swamp + 3 Lake missions")
    check(env.sgl_party_location_text(JRB, 3) == "LAKE ALICE - Act 3: BAT CENSUS AT DUSK - 2P", "player-list location text")
    check(Sim.cmd(A, "mission", "list") and Sim.find(A.chat, "lake_bat_census: level " .. JRB .. " act 3 %(star 2%)") ~= nil,
        "/mission list shows the lake missions")
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

test("levels/jrb/script.c (when built): warp contract for door 3, no level-script star for acts 1-3", function()
    local ls = Sim.level_script("jrb")
    if ls == nil then
        print("  (levels/jrb not built: skipped)")
        return
    end
    local function node(n)
        local wn = ls.warps[n]
        return wn and C[wn.level], wn and wn.node
    end
    local l0, n0 = node(0x0A)
    local l1, n1 = node(0xF0)
    local l2, n2 = node(0xF1)
    check(l0 == JRB and n0 == 0x0A, "JRB 0x0A = own entry spawn")
    check(l1 == HUB and n1 == 0x23, "JRB 0xF0 -> hub 0x23 (outside the Newell Hall door)")
    check(l2 == HUB and n2 == 0x33, "JRB 0xF1 -> hub 0x33")
    for _, o in ipairs(ls.objects) do
        if o.bhv == "bhvStar" then
            check((o.acts & 0x07) == 0, string.format("no level-script star in acts 1-3 (found id %d, acts 0x%02X)",
                (o.bparams or 0) >> 24, o.acts))
        end
    end
end)

test("LAKE_POINTS: inside s16, lily pads in route order, gator line spacing, posts far apart (sources: check_lake_points.py)", function()
    local w, A = world_with({ "A" })
    local P = A.env.LAKE_POINTS
    local bad = 0
    local function each(v, name)
        if type(v) == "table" then
            for k, x in pairs(v) do each(x, name .. "." .. tostring(k)) end
        elseif type(v) == "number" and math.abs(v) > 32767 and not name:find("yaw") then
            bad = bad + 1
            print("  out of s16: " .. name .. " = " .. v)
        end
    end
    each(P, "LAKE_POINTS")
    check(bad == 0, "every coordinate fits SM64's s16 range")
    check(P.water_y == -50, "water surface Y -50 (lake_alice_water WATER_Z -0.5 m)")
    check(#P.pads == 15 and P.pads[15].r >= 250, "15 lily pads, the last one big (lake centre)")
    for i = 2, #P.pads do
        local a, b = P.pads[i - 1], P.pads[i]
        local gap = math.sqrt((a.x - b.x) ^ 2 + (a.z - b.z) ^ 2) - a.r - b.r
        check(gap > 50 and gap < 300, string.format("pad %d -> %d edge gap %.1f m (a hop)", i - 1, i, gap / 100))
    end
    check(#P.gators >= 12 and #P.big_gators == 3, #P.gators .. " basking gators, 3 big gators")
    local G = A.env.SGL_LAKE_GATOR
    for i, g in ipairs(P.gators) do
        if i < #P.gators then
            check(g.bed < P.water_y - 150, "gator " .. i .. " floats over open water (bed " .. g.bed .. ")")
        end
        local top = A.env.sgl_lake_gator_top(g.bed, i, i * G.WAVE + G.UP + G.SINK + 5)
        check(top - 51 >= g.bed + 5, "gator " .. i .. ": its underside stays over the bed when it is under")
        if i > 1 then
            local a = P.gators[i - 1]
            local d = math.sqrt((a.x - g.x) ^ 2 + (a.z - g.z) ^ 2)
            check(d >= 600 and d <= 720, string.format("gators %d -> %d: %.2f m apart (4.4 m backs, ~2 m of water)", i - 1, i, d / 100))
        end
        for k, p in ipairs(P.pads) do
            local d = math.sqrt((p.x - g.x) ^ 2 + (p.z - g.z) ^ 2)
            if d < p.r + 250 then check(false, "gator " .. i .. " overlaps lily pad " .. k) end
        end
    end
    local g1, pad = P.gators[1], P.pads[15]
    local d1 = math.sqrt((g1.x - pad.x) ^ 2 + (g1.z - pad.z) ^ 2) - pad.r - 220
    check(d1 > 150 and d1 < 250, string.format("first gator %.1f m off the end pad's edge", d1 / 100))
    local dd = math.sqrt((P.deck.x - pad.x) ^ 2 + (P.deck.z - pad.z) ^ 2) - pad.r - P.deck_r
    check(dd > 100 and dd < 250, string.format("the deck is a hop (%.1f m) from the end pad", dd / 100))
    for i, g in ipairs(P.gators) do
        local d = math.sqrt((g.x - P.deck.x) ^ 2 + (g.z - P.deck.z) ^ 2)
        if d < P.deck_r * 1.09 + 250 then check(false, "gator " .. i .. " overlaps the deck") end
    end
    check(P.deck_star.y == P.deck.y + 120, "act 1 star 1.2 m over the deck")
    -- the pavilion roof covers +-2.3 m of the deck frame (u = towards the last lily pad): the star spawn rises 2.1 m
    -- over its target before it settles, so the star and the point it arcs in from stay 0.8 m outside the eave
    local ux, uz = P.pads[15].x - P.deck.x, P.pads[15].z - P.deck.z
    local ul = math.sqrt(ux * ux + uz * uz)
    ux, uz = ux / ul, uz / ul
    for _, k in ipairs({ "deck_star", "deck_star_from" }) do
        local dx, dz = P[k].x - P.deck.x, P[k].z - P.deck.z
        local u, v = dx * ux + dz * uz, -dx * uz + dz * ux
        check(math.max(math.abs(u), math.abs(v)) >= 230 + 80, string.format("%s outside the pavilion roof (deck frame %.1f, %.1f m)",
            k, u / 100, v / 100))
    end
    local ds = math.sqrt((P.deck_star.x - P.deck.x) ^ 2 + (P.deck_star.z - P.deck.z) ^ 2)
    check(ds < P.deck_r - 80, string.format("the act 1 star is over the deck (%.1f m from its centre)", ds / 100))
    -- act 1's lurking gators: open water off the pad line; act 2's big gators cover the line past the first two hops
    check(#P.lurk_gators == 2, "two lurking gators in act 1")
    for i, b in ipairs(P.lurk_gators) do
        local near = 1e9
        for _, p in ipairs(P.pads) do
            near = math.min(near, math.sqrt((p.x - b.x) ^ 2 + (p.z - b.z) ^ 2) - p.r)
        end
        check(near >= 590 and b.bed < P.water_y - 150, string.format("lurking gator %d: %.1f m from the nearest pad's edge, bed %d", i, near / 100, b.bed))
    end
    local G2 = A.env.SGL_LAKE_GATOR
    for k = 3, #P.gators - 1 do
        local g, best = P.gators[k], 1e9
        for _, b in ipairs(P.big_gators) do best = math.min(best, math.sqrt((g.x - b.x) ^ 2 + (g.z - b.z) ^ 2)) end
        check(best <= G2.LUNGE, string.format("gator %d is %.1f m from a big gator's home (a fall there can cost a bite)", k, best / 100))
    end
    local gn = P.gators[#P.gators]
    local dn = math.sqrt((gn.x - P.nest.x) ^ 2 + (gn.z - P.nest.z) ^ 2)
    check(dn < 1300, string.format("last gator %.1f m from the nest's centre", dn / 100))
    local st = { P.census_houses, P.census_gardens, P.census_boardwalk }
    for i = 1, 3 do
        for j = i + 1, 3 do
            local d = math.sqrt((st[i].x - st[j].x) ^ 2 + (st[i].z - st[j].z) ^ 2) / 100
            check(d >= 60, string.format("census posts %d and %d are %.0f m apart (one player cannot hold two)", i, j, d))
        end
    end
end)

---------------------------------------------------------------------------------------------
-- act 1: BOARDWALK WELCOME
---------------------------------------------------------------------------------------------
test("act 1: solo route boardwalk -> bog -> 15 lily pads -> the deck -> one spawned star clear of the pavilion roof; collect -> DONE", function()
    local w, A = world_with({ "A" })
    local P = A.env.LAKE_POINTS
    enter(w, A, 1)
    at(A, P.spawn_field)
    w:step(3)
    check(Sim.hud_has(A, "BOARDWALK WELCOME") and Sim.hud_has(A, "LAKE ALICE %- ACT 1"), "act banner")
    check(Sim.find(A.console, "sleeps") == nil, "probes pass")
    check(#Sim.objects_with(A, C.id_bhvSkeeter) == #P.skeeters and #P.skeeters == 5, "five Skeeters skate beside the pad line (local)")
    w:seconds(3.5)
    local ctx = ctx_of(A)
    check(state(A) == MS.ACTIVE and ctx.isLeader, "solo: active, leader")
    check(Sim.hud_has(A, "BOARDWALK"), "marker: BOARDWALK")
    check(not lit(A), "no dusk outside the bat census")
    at(A, P.boardwalk)
    w:step(3)
    check(ctx.p == 1 and (ctx.f & 1) ~= 0 and Sim.hud_has(A, "WEST BOG"), "on the boardwalk: milestone, marker WEST BOG")
    at(A, P.bog)
    w:step(3)
    check(ctx.p == 2 and (ctx.f & 2) ~= 0 and Sim.hud_has(A, "PAD 1"), "on the bog: marker PAD 1")
    for k = 1, 15 do
        at(A, P.pads[k])
        w:step(2)
    end
    check(ctx.p == 17 and (ctx.f & 4) ~= 0 and state(A) == MS.ACTIVE, "pad 15: halfway milestone passed, still active")
    check(Sim.hud_has(A, "OBSERVATION DECK"), "marker: OBSERVATION DECK")
    -- swimming beside the deck (0.8 m under the surface) does not count
    at(A, { x = P.deck.x, y = P.water_y - 80, z = P.deck.z + P.deck_r + 100 })
    w:step(3)
    check(state(A) == MS.ACTIVE, "a swimmer beside the deck: not yet")
    at(A, P.deck)
    w:step(3)
    check(state(A) == MS.SUCCESS and (ctx.f & 8) ~= 0, "standing on the deck: success")
    w:step(3)
    check(#A.starSpawns == 1 and Sim.stars_of(A, 0) == 1, "one spawned star (id 0)")
    local sp = A.starSpawns[1]
    check(sp and sp.x == P.deck_star.x and sp.y == P.deck_star.y and sp.z == P.deck_star.z, "star 1.2 m over the deck")
    check(sp and sp.from.x == P.deck_star_from.x and sp.from.y == P.deck_star_from.y and sp.from.z == P.deck_star_from.z,
        "it arcs in from over the water beyond the deck's far side")
    check(Sim.find(A.console, "spawns its own") == nil, "no level-script star warning")
    local star = Sim.objects_with(A, C.id_bhvStarSpawnCoordinates)[1]
    Sim.run_hooks(A, C.HOOK_ON_INTERACT, A.ms[0], star, C.INTERACT_STAR_OR_KEY, true)
    raw(star).activeFlags = C.ACTIVE_FLAG_DEACTIVATED
    w:step(4)
    check(state(A) == MS.DONE and Sim.stars_of(A, 0) == 0, "DONE, no respawn")
end)

test("act 1: two players share the route; the team best counts; one star for both", function()
    local w, A, B = world_with({ "A", "B" })
    local P = A.env.LAKE_POINTS
    enter(w, A, 1); enter(w, B, 1)
    at(A, P.spawn_field); at(B, P.spawn_field)
    w:seconds(4)
    check(state(A) == MS.ACTIVE and state(B) == MS.ACTIVE, "both active")
    at(B, P.pads[8])
    w:step(4)
    check(ctx_of(A).p == 10 and ctx_of(B).p == 10, "team best = B's pad 8 on both clients")
    check(Sim.hud_has(A, "you 0/15   team best 8/15"), "A's panel: own progress and the team's")
    at(B, P.deck)
    w:step(4)
    check(state(A) == MS.SUCCESS and state(B) == MS.SUCCESS, "B on the deck: success everywhere")
    w:step(3)
    check(Sim.stars_of(A, 0) == 1 and Sim.stars_of(B, 0) == 1, "exactly one star on each client (de-dup)")
end)

test("act 1: two big gators lurk beside the pad line: a swimmer near one is bitten, nobody on a pad is", function()
    local w, A = world_with({ "A" })
    local P = A.env.LAKE_POINTS
    enter(w, A, 1)
    at(A, P.spawn_field)
    w:seconds(4)
    check(state(A) == MS.ACTIVE, "active")
    local props = Sim.objects_with(A, A.env.id_bhvSglLakeProp)
    check(#props == #P.lurk_gators and raw(props[1])._model == C.E_MODEL_SUSHI and raw(props[1])._anim == 0,
        #props .. " gator stand-ins (sushi, animated) in act 1")
    local home = P.lurk_gators[1]
    local pk, pd = 1, 1e9
    for k, p in ipairs(P.pads) do
        local d = math.sqrt((p.x - home.x) ^ 2 + (p.z - home.z) ^ 2)
        if d < pd then pk, pd = k, d end
    end
    -- on the pad nearest to the first gator's home: safe
    A.action = C.ACT_IDLE
    for _ = 1, 120 do
        at(A, P.pads[pk])
        w:step(1)
    end
    check((A.hurts or 0) == 0, "on pad " .. pk .. " beside its home: no bite")
    -- in the water between that pad and the gator: chased and bitten
    A.action = C.ACT_WATER_IDLE
    at(A, { x = (home.x + P.pads[pk].x) / 2, y = -130, z = (home.z + P.pads[pk].z) / 2 })
    local bitten = nil
    for f = 1, 150 do
        w:step(1)
        if (A.hurts or 0) > 0 then bitten = f break end
    end
    check(bitten ~= nil, "a swimmer off the pads is bitten (after " .. tostring(bitten) .. " frames)")
    w:step(2)
    check(Sim.find(A.hudLog, "back onto the lily pads") ~= nil or Sim.hud_has(A, "back onto the lily pads"), "act 1's CHOMP toast")
    check(Sim.hud_has(A, "gators lurk here"), "panel: in the water, gators lurk")
    -- at the start of the route (the first pads, the bog): no gator goes for a swimmer there
    A.hurts = 0
    A.action = C.ACT_WATER_IDLE
    at(A, { x = P.pads[1].x, y = -130, z = P.pads[1].z + 300 })
    w:step(150)
    check(A.hurts == 0, "a swimmer by the first pad is left alone")
    -- the deck end too (act 1's goal)
    at(A, { x = P.deck.x, y = -130, z = P.deck.z + P.deck_r + 100 })
    w:step(150)
    check(A.hurts == 0, "a swimmer beside the deck is left alone")
end)

---------------------------------------------------------------------------------------------
-- act 2: GATOR HOP
---------------------------------------------------------------------------------------------
test("gators: the sinking wave (2.8 s up, 1.6 s under) is a pure function of the area timer; sunk backs stay over the bed", function()
    local w, A = world_with({ "A" })
    local env = A.env
    local G = env.SGL_LAKE_GATOR
    local top = env.sgl_lake_gator_top
    check(G.UP + G.SINK + G.UNDER + G.RISE == G.CYCLE, "the phases fill the cycle")
    local up, under, wob, maxStep = 0, 0, 0, 0
    local prev = top(-300, 1, G.WAVE - 1)
    for t = 0, G.CYCLE - 1 do
        local y, st, wb = top(-300, 1, t + G.WAVE)
        if st == "up" then up = up + 1 end
        if st == "under" then under = under + 1 end
        if wb then wob = wob + 1 end
        maxStep = math.max(maxStep, math.abs(y - prev))
        prev = y
    end
    check(up == 84 and under == 30 and wob == 20, string.format("up %d, under %d, wobble %d frames", up, under, wob))
    check(maxStep <= G.STEP, "at most " .. G.STEP .. " units per frame (a rider stays on)")
    check(top(-300, 1, G.WAVE) == -50 + G.SURF_LIFT, "an up gator's back 0.12 m over the water")
    check(select(1, top(-300, 1, G.WAVE + G.UP + G.SINK + 1)) == -50 - G.SINK_DEPTH, "under: 1.6 m down")
    check(select(1, top(-149, 1, G.WAVE + G.UP + G.SINK + 1)) == -149 + G.BED_CLEAR, "shallow: 0.4 m over the bed")
    local _, s1 = top(-300, 1, 1000)
    local _, s2 = top(-300, 2, 1000 + G.WAVE)
    check(s1 == s2, "gator k+1 runs WAVE frames behind gator k (the wave rolls toward the nest)")
end)

test("act 2: 17 gator platforms on every client, the same height everywhere, carrying their rider", function()
    local w, A, B = world_with({ "A", "B" })
    local P = A.env.LAKE_POINTS
    enter(w, A, 2); enter(w, B, 2)
    at(A, P.pads[15]); at(B, P.pads[15])
    w:step(4)
    local pa = Sim.objects_with(A, A.env.id_bhvSglLakePlatform)
    local pb = Sim.objects_with(B, B.env.id_bhvSglLakePlatform)
    check(#pa == #P.gators and #pb == #P.gators, #pa .. " gator platforms on A, " .. #pb .. " on B")
    local o = pa[1]
    check(raw(o).collisionData == "COL:checkerboard_platform", "checkerboard collision")
    local sc = raw(o).header.gfx.scale
    check(math.abs(sc.x * 256 - 80) < 1 and math.abs(sc.z * 153 - 220) < 1, "a 1.6 x 4.4 m back")
    check(raw(o).oFaceAngleYaw == P.gators[1].yaw, "turned along the line")
    check(#Sim.objects_with(A, A.env.id_bhvSglLakeProp) == #P.gators + 3, "a stand-in body per gator + 3 big gators")
    local same, velOk, seenUnder = true, true, false
    local prev = raw(o).oPosY
    for _ = 1, 160 do
        w:step(1)
        for k = 1, #pa do
            if raw(pa[k]).oPosY ~= raw(pb[k]).oPosY then same = false end
        end
        local y = raw(o).oPosY
        if raw(o).oVelY ~= y - prev then velOk = false end
        if y + PTOP <= -50 - 150 then seenUnder = true end
        prev = y
    end
    check(same, "every gator at the same height on both clients (network area timer)")
    check(velOk, "oVelY = each frame's move (the engine carries the rider)")
    check(seenUnder, "gator 1 goes under within a cycle")
end)

test("act 2: a gator frozen by a time stop (star cutscene) catches up at most 30 units a frame, carrying its rider", function()
    local w, A = world_with({ "A" })
    local env = A.env
    local P = env.LAKE_POINTS
    local G = env.SGL_LAKE_GATOR
    local f = env.sgl_lake_plat_follow
    local y1, d1 = f(0, 100)
    local y2, d2 = f(0, -10)
    local y3, d3 = f(0, 5000)
    check(y1 == 30 and d1 == 30 and y2 == -10 and d2 == -10, "follow: at most 30 units a frame")
    check(y3 == 5000 and d3 == 0, "a broken record (> 15 m off) is snapped to, carrying nobody")
    enter(w, A, 2)
    at(A, P.pads[15])
    w:seconds(4)
    local ctx = ctx_of(A)
    local o = Sim.objects_with(A, env.id_bhvSglLakePlatform)[1]
    local rec = ctx.objs.gators[1]
    -- just before gator 1 sinks, the surface-list objects freeze (time stop) while the controller ticks on
    for _ = 1, 400 do
        if (w.frame + 1 - G.WAVE) % G.CYCLE == G.UP - 2 then break end
        w:step(1)
    end
    local beh = A.behaviors[raw(o).behavior]
    local loop = beh.loop
    beh.loop = function() end
    w:step(40)
    local lag = raw(o).oPosY - rec.y
    check(lag > 100, string.format("frozen: the platform stayed up while its record went under (%.0f units)", lag))
    beh.loop = loop
    local maxStep, velOk = 0, true
    for _ = 1, 12 do
        local y0 = raw(o).oPosY
        w:step(1)
        local dy = raw(o).oPosY - y0
        maxStep = math.max(maxStep, math.abs(dy))
        if raw(o).oVelY ~= dy then velOk = false end
    end
    check(maxStep == 30, "it catches up at 30 units a frame (" .. maxStep .. "), no jump that would drop its rider")
    check(velOk, "oVelY = each step (the engine carries the rider down with it)")
    check(math.abs(raw(o).oPosY - rec.y) < 1, "back on its record")
end)

test("act 2: hop the gators in order (one may be skipped) to the nest -> star; swimming to the nest does not count", function()
    local w, A = world_with({ "A" })
    local P = A.env.LAKE_POINTS
    local N = #P.gators
    enter(w, A, 2)
    at(A, P.spawn_field)
    w:seconds(4)
    local ctx = ctx_of(A)
    check(state(A) == MS.ACTIVE, "active")
    check(Sim.hud_has(A, "START: LAKE DECK"), "marker: START: LAKE DECK (far from the line)")
    -- D-pad Down: onto the deck (the end pad is the first hop)
    A.pressed = C.D_JPAD
    w:step(2)
    local s = P.deck
    check(math.sqrt((A.pos.x - s.x) ^ 2 + (A.pos.z - s.z) ^ 2) < P.deck_r and A.pos.y == s.y + 20 and A.action == C.ACT_IDLE,
        "D-pad Down: on the deck")
    check(Sim.hud_has(A, "GATOR 1"), "marker: GATOR 1")
    -- swim to the nest first: nothing
    at(A, P.nest)
    w:step(4)
    check(state(A) == MS.ACTIVE and Sim.hud_has(A, "hop ALL the gators"), "on the nest without the hops: a hint, no star")
    local function stand(k)
        local rec = ctx.loc.gators[k]
        at(A, { x = P.gators[k].x, y = rec.top, z = P.gators[k].z })
        w:step(1)
        rec = ctx.loc.gators[k]
        at(A, { x = P.gators[k].x, y = rec.top, z = P.gators[k].z })
        w:step(1)
    end
    stand(1); stand(2)
    check(ctx.loc.prog == 2, "gators 1, 2")
    stand(4)
    check(ctx.loc.prog == 4, "gator 3 skipped (a long jump): 4 counts")
    stand(7)
    check(ctx.loc.prog == 4, "two skipped (swam ahead): gator 7 does not count")
    w:step(2)
    check(ctx.p == 4, "the leader's team best follows the hop events")
    for k = 5, N do stand(k) end
    check(ctx.loc.prog == N and Sim.hud_has(A, "NEST"), "all gators: marker NEST")
    at(A, P.nest)
    w:step(4)
    check(state(A) == MS.SUCCESS and ctx.x == 1, "on the nest after the line: success")
    w:step(3)
    local sp = A.starSpawns[1]
    check(#A.starSpawns == 1 and Sim.stars_of(A, 1) == 1 and sp.y == P.nest_star.y and sp.x == P.nest_star.x,
        "one star (id 1) over the nest")
end)

test("act 2: a hop event the leader never applied is sent again; a friend's nest is announced", function()
    local w, A, B = world_with({ "A", "B" })
    local P = A.env.LAKE_POINTS
    enter(w, A, 2); enter(w, B, 2)
    at(A, P.pads[15]); at(B, P.pads[15])
    w:seconds(4)
    local cb = ctx_of(B)
    -- B hops gator 1, but its event is lost on the way to A (the leader)
    local send = B.stubs.network_send
    B.stubs.network_send = function(rel, t)
        if t.ev == "hop" then return end
        return send(rel, t)
    end
    local rec = cb.loc.gators[1]
    at(B, { x = P.gators[1].x, y = rec.top, z = P.gators[1].z })
    w:step(2)
    B.stubs.network_send = send
    check(cb.loc.prog == 1 and ctx_of(A).p == 0, "B is on gator 1, the leader missed it")
    w:step(95)
    check(ctx_of(A).p == 1 and ctx_of(B).p == 1, "sent again after 3 s: team best 1")
    -- B finishes
    for k = 2, #P.gators do
        at(B, { x = P.gators[k].x, y = cb.loc.gators[k].top, z = P.gators[k].z })
        w:step(2)
    end
    at(B, P.nest)
    w:step(4)
    check(state(A) == MS.SUCCESS and Sim.hud_has(A, "B reached the gator nest"), "A: success, toast for B's nest")
end)

test("act 2: two players on one gator sink it at once (on both clients); other gators keep their wave", function()
    local w, A, B = world_with({ "A", "B" })
    local env = A.env
    local P = env.LAKE_POINTS
    local G = env.SGL_LAKE_GATOR
    enter(w, A, 2); enter(w, B, 2)
    at(A, P.pads[15]); at(B, P.pads[15])
    w:seconds(4)
    -- wait until gator 3 has just surfaced (it would stay up for ~2.5 s more)
    for _ = 1, 200 do
        local u = (w.frame + 1 - 3 * G.WAVE) % G.CYCLE
        if u == 2 then break end
        w:step(1)
    end
    w:step(1)
    local ca, cb = ctx_of(A), ctx_of(B)
    local g = P.gators[3]
    local surf = -50 + G.SURF_LIFT
    check(ca.loc.gators[3].top == surf and ca.loc.gators[3].state == "up", "gator 3 is up")
    for _ = 1, 3 do
        at(A, { x = g.x, y = ca.loc.gators[3].top, z = g.z })
        at(B, { x = g.x + 60, y = cb.loc.gators[3].top, z = g.z })
        w:step(1)
    end
    check(ca.loc.gators[3].force ~= nil and cb.loc.gators[3].force ~= nil, "both clients: forced sink")
    check(Sim.hud_has(A, "Two on one gator") or Sim.find(A.hudLog, "Too heavy") ~= nil or Sim.hud_has(A, "going under"),
        "the riders are told")
    for _ = 1, G.WOBBLE + G.SINK + 4 do
        at(A, { x = g.x, y = ca.loc.gators[3].top, z = g.z })
        at(B, { x = g.x + 60, y = cb.loc.gators[3].top, z = g.z })
        w:step(1)
    end
    local _, natural = env.sgl_lake_gator_top(g.bed, 3, w.frame)
    check(natural == "up", "its own cycle is still up")
    check(ca.loc.gators[3].top < surf - 100 and cb.loc.gators[3].top < surf - 100, "but it went under on both clients")
    check(ca.loc.gators[5].force == nil, "the other gators are not affected")
end)

test("act 2: big gators chase a swimmer and bite (a wedge, knocked back), rest, and leave gator riders alone", function()
    local w, A = world_with({ "A" })
    local env = A.env
    local P = env.LAKE_POINTS
    enter(w, A, 2)
    at(A, P.pads[15])
    w:seconds(4)
    local ctx = ctx_of(A)
    local home = P.big_gators[1]
    A.action = C.ACT_WATER_IDLE
    at(A, { x = home.x + 600, y = -130, z = home.z })
    local bitten = nil
    for f = 1, 90 do
        w:step(1)
        if (A.hurts or 0) > 0 then bitten = f break end
    end
    check(bitten ~= nil, "bitten within " .. tostring(bitten) .. " frames")
    w:step(2)
    check(raw(A.ms[0]).hurtCounter == env.SGL_LAKE_GATOR.BITE_HURT and A.action == C.ACT_BACKWARD_WATER_KB,
        "a wedge of damage, water knock-back")
    check(Sim.hud_has(A, "CHOMP") or Sim.find(A.hudLog, "CHOMP") ~= nil, "CHOMP! toast")
    check(raw(A.ms[0]).forwardVel < 0, "pushed back, away from the gator")
    -- back in the water at once: the gator rests first
    A.action = C.ACT_WATER_IDLE
    w:step(20)
    check(A.hurts == 1, "no second bite while it rests")
    -- standing on a gator back next to it: safe
    A.hurts = 0
    local g = P.gators[3]
    A.action = C.ACT_IDLE
    for _ = 1, 150 do
        at(A, { x = g.x, y = ctx.loc.gators[3].top, z = g.z })
        if ctx.loc.gators[3].top >= -50 then w:step(1) else break end
    end
    check(A.hurts == 0, "no bite on a gator's back")
    -- far from every home: no chase
    A.action = C.ACT_WATER_IDLE
    at(A, { x = P.pads[3].x, y = -130, z = P.pads[3].z })
    w:step(120)
    check(A.hurts == 0, "a swimmer far from the line is left alone")
    -- a star dance in the water (a cutscene) is never interrupted
    A.action = C.ACT_STAR_DANCE_WATER
    at(A, { x = home.x + 300, y = -130, z = home.z })
    w:step(120)
    check(A.hurts == 0 and A.action == C.ACT_STAR_DANCE_WATER, "no bite during a water star dance")
end)

---------------------------------------------------------------------------------------------
-- act 3: BAT CENSUS AT DUSK - 2P
---------------------------------------------------------------------------------------------
test("census numbers: target 600 + 300 per extra player (2..4); one post can never make it; two posts can", function()
    local w, A = world_with({ "A" })
    local d3 = def_of(A, 3)
    check(d3.targetFor(1) == 900 and d3.targetFor(2) == 900 and d3.targetFor(3) == 1200 and d3.targetFor(4) == 1500
        and d3.targetFor(8) == 1500, "targets 900 / 1200 / 1500 (min 2 players, max 4)")
    local DUR = d3.spec.duration
    for n = 2, 6 do
        local onePost = d3.rateFor({ math.min(n, 99), 0, 0 }) * DUR
        check(onePost < d3.targetFor(n), string.format("%d players on one post: %d < %d", n, onePost, d3.targetFor(n)))
    end
    check(d3.rateFor({ 1, 1, 0 }) * DUR >= d3.targetFor(2) * 1.2, "2 players, 2 posts: 20 % to spare")
    check(d3.rateFor({ 1, 1, 1 }) * DUR >= d3.targetFor(3) * 1.2, "3 players, 3 posts: 20 % to spare")
    check(d3.rateFor({ 2, 1, 1 }) * DUR >= d3.targetFor(4) * 1.2, "4 players: 20 % to spare")
    check(d3.rateFor({ 1, 0, 0 }) * DUR < 600, "one post alone never reaches even 600")
end)

test("act 3 alone: waiting for a second player under a dusk sky; leaving the act restores the lighting", function()
    local w, A = world_with({ "A" })
    local P = A.env.LAKE_POINTS
    check(is_default_light(A), "daylight in the hub")
    enter(w, A, 3)
    at(A, P.spawn_field)
    w:seconds(1)
    check(state(A) == MS.WAITING and Sim.hud_has(A, "This act needs 2 players"), "waiting, players-needed prompt")
    w:seconds(2.5)
    check(lit(A), "dusk lighting on arrival")
    local L = A.light
    check(L.light[1] == 255 and L.light[3] < 140 and L.ambient[3] > L.ambient[2], "sunset light, purple ambient")
    check(L.sky[3] < 255 and L.fog[1] < 255 and L.dir[2] < 0, "tinted sky, fog, dimmed light direction")
    local st = A.env.sgl_lake_dusk_state()
    check(st.applied and st.s == 1, "fully faded in after 2 s")
    -- another act of the same stage is daylight
    enter(w, A, 1)
    w:step(2)
    check(is_default_light(A), "act 1 of Lake Alice: the snapshot is back (daylight)")
    enter(w, A, 3)
    w:step(5)
    check(lit(A), "act 3 again: dusk again")
    w:warp(A, HUB, 1, 0)
    w:step(1)
    check(is_default_light(A) and not st.applied, "hub: lighting restored at once")
end)

test("act 3 with 2 players: posts -> countdown -> 90 s count at 2 Hz -> 900 bats -> star; night falls", function()
    local w, A, B = world_with({ "A", "B" })
    local P = A.env.LAKE_POINTS
    enter(w, A, 3); enter(w, B, 3)
    at(A, P.spawn_field); at(B, P.spawn_field)
    w:seconds(4)
    local ca, cb = ctx_of(A), ctx_of(B)
    check(state(A) == MS.ACTIVE and ca.isLeader and ca.x == 0 and ca.a == 900, "active, take your posts, target 900")
    check(Sim.hud_has(A, "staff 2%+ census posts") and Sim.hud_has(A, "POST: GARDENS"), "panel + markers of the empty posts")
    check(#Sim.objects_with(A, C.id_bhvSglButton or A.env.id_bhvSglButton) == 3, "three posts (purple switches)")
    -- D-pad Down: to the nearest free post
    A.pressed = C.D_JPAD
    w:step(2)
    check(ca.loc.station == 1, "A: D-pad Down onto the bat barns' post (nearest)")
    at(B, P.census_boardwalk)
    w:step(3)
    check((ca.f & 7) == 5 and ca.x == 1, "two posts staffed: countdown")
    w:seconds(3.2)
    check(ca.x == 2 and cb.x == 2, "counting on both clients")
    check(Sim.find(A.hudLog, "BATS OUT") ~= nil or Sim.hud_has(A, "BATS OUT"), "BATS OUT!")
    local q = A.music[#A.music]
    check(q ~= nil and (q & 0xFF) == C.SEQ_LEVEL_SPOOKY, "emergence music while counting")
    w:seconds(10)
    check(ca.p >= 120 and ca.p <= 140, "10 s at two posts: " .. ca.p .. " bats (13 per second)")
    check(cb.p == ca.p, "B sees the leader's count")
    check(#Sim.objects_with(A, A.env.id_bhvSglLakeBat) > 20, "a swarm of bats streams out of the barns")
    check(#Sim.objects_with(A, C.id_bhvSwoop) >= 1, "a Swooper dives at the counter")
    local nightBefore = A.light.light[1]
    w:seconds(40)
    check(A.light.light[1] < nightBefore, "night is falling")
    for _ = 1, 30 * 30 do
        w:step(1)
        if state(A) == MS.SUCCESS then break end
    end
    check(state(A) == MS.SUCCESS and ca.x == 3 and ca.p >= 900, "900 bats counted: success (" .. ca.p .. ")")
    check(ca.c < 90, "before the 90 s ran out (" .. ca.c .. " s)")
    w:step(3)
    local sp = A.starSpawns[1]
    check(#A.starSpawns == 1 and Sim.stars_of(A, 2) == 1 and sp.x == P.census_star.x and sp.y == P.census_star.y,
        "one star (id 2) over the barns' post")
    check(sp.from.x == P.bat_exit_2010.x and sp.from.y == P.bat_exit_2010.y, "it flies out of the 2010 bat barn")
    check(#Sim.objects_with(A, C.id_bhvSwoop) == 0, "the diving Swoopers are gone")
    w:step(10)
    check((A.music[#A.music] or 0) & 0xFF ~= C.SEQ_LEVEL_SPOOKY, "the emergence music stops")
end)

test("act 3: one post for both players falls short at 90 s -> try again; a knock-back stops the count", function()
    local w, A, B = world_with({ "A", "B" })
    local P = A.env.LAKE_POINTS
    enter(w, A, 3); enter(w, B, 3)
    at(A, P.census_houses); at(B, { x = P.census_houses.x + 100, y = 0, z = P.census_houses.z })
    w:seconds(4)
    local ca = ctx_of(A)
    check(ca.x == 0 and (ca.f & 7) == 1, "both on one post: it does not start")
    w:seconds(60)
    check(ca.x == 1 or ca.x == 2, "after 60 s with one post staffed the count starts anyway")
    w:seconds(4)
    -- B knocked back by a Swooper: not counted
    B.action = C.ACT_BACKWARD_AIR_KB
    w:step(4)
    check(A.env.sgl_lake_knocked_back(C.ACT_BACKWARD_AIR_KB) and def_of(A, 3).countersOf(ca.f, 1) == 1,
        "a knocked-back player does not count")
    check(Sim.find(B.hudLog, "Knocked off your post") ~= nil or Sim.hud_has(B, "Knocked off your post"), "B is told")
    B.action = C.ACT_IDLE
    w:step(4)
    check(def_of(A, 3).countersOf(ca.f, 1) == 2, "back on the post: two counters")
    for _ = 1, 30 * 95 do
        w:step(1)
        if state(A) == MS.FAILED then break end
    end
    check(state(A) == MS.FAILED and ca.p < 900, "90 s at one post: " .. ca.p .. " < 900 -> FAILED")
    w:seconds(4.5)
    check(ca.x == 0 and ca.p == 0 and (state(A) == MS.INTRO or state(A) == MS.ACTIVE), "a new round: take your posts")
    check(lit(A), "still dusk")
end)

test("act 3: /mission reset mid-count starts over at the posts, stops the music and clears the Swoopers", function()
    local w, A, B = world_with({ "A", "B" })
    local P = A.env.LAKE_POINTS
    enter(w, A, 3); enter(w, B, 3)
    at(A, P.census_houses); at(B, P.census_gardens)
    w:seconds(4 + 3.5 + 8)
    local ca = ctx_of(A)
    check(ca.x == 2 and (A.music[#A.music] or 0) & 0xFF == C.SEQ_LEVEL_SPOOKY, "counting, music on")
    check(#Sim.objects_with(A, C.id_bhvSwoop) >= 1, "a Swooper is out")
    Sim.cmd(B, "mission", "reset")
    w:step(4)
    check(ca.x == 0 and ca.p == 0, "a new round at the posts")
    check(#A.music == 0 or (A.music[#A.music] & 0xFF) ~= C.SEQ_LEVEL_SPOOKY, "the music stopped")
    check(#Sim.objects_with(A, C.id_bhvSwoop) == 0, "the Swoopers are gone")
    w:warp(A, HUB, 1, 0)
    w:step(2)
    check(is_default_light(A), "out of the act: daylight")
end)

test("act 3: 3 players need 1200, 4 need 1500; the leader leaving keeps the count and drops the target", function()
    local w, A, B, Cc = world_with({ "A", "B", "C" })
    local P = A.env.LAKE_POINTS
    enter(w, A, 3); enter(w, B, 3); enter(w, Cc, 3)
    at(A, P.census_houses); at(B, P.census_gardens); at(Cc, P.census_boardwalk)
    w:seconds(4)
    local cb = ctx_of(B)
    check(ctx_of(A).a == 1200 and cb.a == 1200, "3 players: 1200 bats")
    w:seconds(14)
    check(cb.x == 2 and cb.p > 150, "counting at three posts: " .. cb.p)
    local before = cb.p
    w:warp(A, HUB, 1, 0)      -- the leader leaves
    w:step(3)
    check(cb.isLeader and cb.p >= before, "B leads on from the synced count (" .. before .. " -> " .. cb.p .. ")")
    check(cb.a == 900, "the target drops to 900 for 2 players")
    w:seconds(2)
    check(cb.p > before + 15, "and the count goes on (" .. cb.p .. ")")
    -- 4 players
    local w2, D1, D2, D3, D4 = world_with({ "A", "B", "C", "D" })
    for _, c in ipairs({ D1, D2, D3, D4 }) do
        enter(w2, c, 3)
        at(c, P.spawn_field)
    end
    w2:seconds(4)
    check(ctx_of(D1).a == 1500, "4 players: 1500 bats")
end)

test("act 3: cosmetic bats fly out of the barns and vanish after 7 s; D-pad Down picks a free post", function()
    local w, A, B = world_with({ "A", "B" })
    local env = A.env
    local P = env.LAKE_POINTS
    local x0, y0, z0 = env.sgl_lake_bat_pos(100, 400, 200, 0x2000, 1.5, 0)
    local x1, y1, z1 = env.sgl_lake_bat_pos(100, 400, 200, 0x2000, 1.5, 150)
    check(math.abs(x0 - 100) < 200 and math.abs(z0 - 200) < 200, "a bat starts at its barn's exit")
    check(math.sqrt((x1 - x0) ^ 2 + (z1 - z0) ^ 2) > 2000 and y1 > y0, "and flies 20+ m out, climbing")
    enter(w, A, 3); enter(w, B, 3)
    at(A, P.census_gardens); at(B, P.spawn_field)
    w:seconds(4)
    B.pressed = C.D_JPAD
    w:step(2)
    check(ctx_of(B).loc.station == 1, "B: nearest free post (the bat barns', the gardens are taken)")
    w:seconds(5)
    local bats = Sim.objects_with(A, env.id_bhvSglLakeBat)
    check(#bats > 0 and raw(bats[1])._model == C.E_MODEL_SWOOP and raw(bats[1])._anim == 0, "swoop stand-ins, flying animation")
    local cnt = 0
    for _ = 1, 30 * 12 do
        w:step(1)
        cnt = math.max(cnt, #Sim.objects_with(A, env.id_bhvSglLakeBat))
    end
    check(cnt <= 40, "at most 40 bats at once (" .. cnt .. ")")
end)

test("act 3: Swoopers keep coming one at a time all count long, hit without damage, and are taken away after their pass", function()
    local w, A, B = world_with({ "A", "B" })
    local env = A.env
    local P = env.LAKE_POINTS
    local d3 = def_of(A, 3)
    enter(w, A, 3); enter(w, B, 3)
    at(A, P.census_houses); at(B, P.census_boardwalk)
    w:seconds(4 + 3.5)
    local ca = ctx_of(A)
    check(ca.x == 2, "counting")
    local first, n, maxAlive, dmgOk = {}, 0, 0, true
    for _ = 1, 30 * 45 do
        at(A, P.census_houses)
        w:step(1)
        local alive = Sim.objects_with(A, C.id_bhvSwoop)
        maxAlive = math.max(maxAlive, #alive)
        for _, o in ipairs(alive) do
            local r = raw(o)
            if first[r] == nil then
                first[r] = w.frame
                n = n + 1
            elseif r.oDamageOrCoinValue ~= 0 then
                dmgOk = false
            end
        end
    end
    check(n >= 4, n .. " Swoopers in 45 s (the first after 4 s on the post, then every 11 s)")
    check(maxAlive <= 2, "at most two at once (" .. maxAlive .. ")")
    check(dmgOk, "every Swooper hits for 0 damage (a knock-back only)")
    check(#Sim.objects_with(A, C.id_bhvMistParticleSpawner) >= n - 2, "each one leaves in a puff of mist")
    -- one that has flown off: taken away at once (after its first 2 s)
    for _ = 1, 30 * 12 do
        w:step(1)
        if #Sim.objects_with(A, C.id_bhvSwoop) > 0 then break end
    end
    local o = Sim.objects_with(A, C.id_bhvSwoop)[1]
    check(o ~= nil, "a new Swooper")
    w:step(70)
    if o ~= nil then
        raw(o).oPosX = P.census_houses.x + d3.spec.swoopLeash + 200
        w:step(2)
        check(raw(o).activeFlags == C.ACTIVE_FLAG_DEACTIVATED, "a Swooper 17 m from its post is taken away")
    end
end)

test("act 3: each client's bat swarm streams from both barns over that player's own post; each post's share shows", function()
    local w, A, B = world_with({ "A", "B" })
    local env = A.env
    local P = env.LAKE_POINTS
    local d3 = def_of(A, 3)
    local posts = { P.census_houses, P.census_gardens, P.census_boardwalk }
    for i, p in ipairs(posts) do
        for _, e in ipairs({ P.bat_exit_2010, P.bat_exit_2017 }) do
            local yaw, speed, climb, life = env.sgl_lake_bat_flight(e, p)
            local best, bestY, bestT = 1e9, nil, nil
            for t = 0, life do
                local x, y, z = env.sgl_lake_bat_pos(e.x, e.y, e.z, yaw, 1.3, t, speed, climb)
                local d = math.sqrt((x - p.x) ^ 2 + (z - p.z) ^ 2)
                if d < best then best, bestY, bestT = d, y, t end
            end
            check(best < 250 and bestY > p.y + 250 and bestY < p.y + 900 and bestT < life - 30 and speed <= 60,
                string.format("post %d: a bat passes %.1f m from it, %.1f m up, after %.1f s (life %.1f s)", i, best / 100,
                    (bestY - p.y) / 100, bestT / 30, life / 30))
        end
    end
    enter(w, A, 3); enter(w, B, 3)
    at(A, P.census_houses); at(B, P.census_gardens)
    w:seconds(4 + 3.5 + 6)
    check(ctx_of(B).x == 2, "counting")
    local bats, ok = Sim.objects_with(B, B.env.id_bhvSglLakeBat), true
    for _, o in ipairs(bats) do
        local r = raw(o)
        local want = B.env.atan2s(P.census_gardens.z - r.oHomeZ, P.census_gardens.x - r.oHomeX)
        local diff = ((r.oMoveAngleYaw - want + 0x8000) & 0xFFFF) - 0x8000
        if math.abs(diff) > d3.spec.spread then ok = false end
    end
    check(#bats > 10 and ok, #bats .. " of B's bats head for the Gardens post (B's own)")
    check(Sim.hud_has(A, "Bat barns %- counting   %+%d+") and Sim.hud_has(A, "Gardens %- counting   %+%d+"),
        "panel: each staffed post shows its share")
    check(not Sim.hud_has(A, "Boardwalk %- empty   %+"), "an empty post shows no share")
end)

test("dusk: Day Night Cycle DX hooks get our dusk while the act runs, nothing elsewhere", function()
    local w, A = world_with({ "A" })
    local hooks = {}
    local api = { dnc_hook_event = function(ev, fn) hooks[ev] = fn end,
        constants = { DNC_HOOK_SET_LIGHTING_COLOR = 0, DNC_HOOK_SET_AMBIENT_LIGHTING_COLOR = 1, DNC_HOOK_SET_LIGHTING_DIR = 2,
            DNC_HOOK_SET_FOG_COLOR = 3, DNC_HOOK_SET_FOG_INTENSITY = 4 } }
    rawset(A.env._G, "dayNightCycleApi", api)
    w:step(2)
    check(hooks[0] ~= nil and hooks[1] ~= nil and hooks[2] ~= nil and hooks[3] ~= nil and hooks[4] ~= nil, "five DNC hooks")
    check(hooks[0]({ r = 1, g = 2, b = 3 }) == nil, "in the hub: DNC keeps its own colours")
    enter(w, A, 3)
    w:seconds(3)
    local c = hooks[0]({ r = 1, g = 2, b = 3 })
    check(c ~= nil and c.r == A.light.light[1] and c.b == A.light.light[3], "in the census act: our dusk colour")
    local d = hooks[2]({ x = 0, y = 0, z = 0 })
    check(d ~= nil and d.y < 0, "and our light direction")
    w:warp(A, HUB, 1, 0)
    w:step(1)
    check(hooks[0]({ r = 1, g = 2, b = 3 }) == nil, "back in the hub: nil again")
    -- the API reached only through _G's metatable (not a raw field of this mod's _G): still found
    local w2, A2 = world_with({ "A" })
    local hooks2 = {}
    A2.stubs.dayNightCycleApi = { dnc_hook_event = function(ev, fn) hooks2[ev] = fn end, constants = api.constants }
    check(rawget(A2.env._G, "dayNightCycleApi") == nil, "(not a raw field)")
    w2:step(2)
    check(hooks2[0] ~= nil and hooks2[4] ~= nil, "found through the metatable lookup: five DNC hooks")
end)

---------------------------------------------------------------------------------------------
-- whole mod
---------------------------------------------------------------------------------------------
test("whole mod: every file loads with the lake missions; /campus alice 3 starts the census at dusk; act 4 is coming soon", function()
    local built = Sim.built_on_disk()
    built[JRB] = true
    local w = Sim.new({ files = Sim.ALL_FILES, built = built })
    local H = prep(w:connect("Host"))
    local F = prep(w:connect("Friend"))
    w:step(3)
    w:warp(H, HUB, 1, 0); w:warp(F, HUB, 1, 0)
    w:step(40)
    local has = false
    for _, f in ipairs(Sim.ALL_FILES) do if f == "uf_lake_missions.lua" then has = true end end
    check(has, "uf_lake_missions.lua is a mod file")
    check(H.env.sgl_mission_get(JRB, 3) ~= nil and H.env.sgl_mission_get(C.LEVEL_WF, 3) ~= nil, "lake + Reitz missions registered")
    local ok = pcall(Sim.cmd, H, "campus", "alice 3")
    w:step(5)
    if ok and H.level == JRB then
        check(H.act == 3 and F.level == JRB and F.act == 3, "/campus alice 3: everyone to Lake Alice act 3")
        w:seconds(4)
        check(state(H) == MS.ACTIVE and ctx_of(H).x == 0, "the census is on (take your posts)")
        check(lit(H) and lit(F), "dusk on both clients")
    else
        print("  (/campus alice not available in levels.lua: warping directly)")
        w:warp(H, JRB, 1, 3); w:warp(F, JRB, 1, 3)
        w:seconds(4)
        check(state(H) == MS.ACTIVE and lit(H), "the census is on at dusk")
    end
    w:warp(H, JRB, 1, 4)
    w:step(5)
    check(Sim.hud_has(H, "COMING SOON %- REGATTA"), "act 4: coming soon notice")
    check(is_default_light(H), "act 4: daylight")
end)

print(string.format("\n%d checks passed, %d failed", passed, failed))
os.exit(failed == 0 and 0 or 1)
