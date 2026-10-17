-- Integration tests: the WHOLE mod (every mods/sgl64/*.lua, in coopdx's load order) plus the REAL
-- generated level scripts (levels/castle_grounds, levels/bob, levels/wf, levels/jrb, levels/ccm, levels/bbh) in the
-- offline coopdx simulation.
-- The built stages are the ones on disk (Sim.built_on_disk), as in the game.
-- What it pins down (docs/flow.md):
--   * every file loads with strict globals in strcmp order; no two files register the same chat
--     command / mod menu button / behaviour; the hooks of all files coexist;
--   * hub doors (id_bhvSglDoor from the hub script): states, popups, the vanilla warp through hub
--     WARP_NODE 0x10+i -> stage node 0x0A, the return spawns 0x20+i / 0x30+i outside the door;
--   * the vanilla act select rule (star_select.c) against course.lua + the missions + the level-script
--     stars: playable acts are 1..n with no gap, the rest are "COMING SOON" and still exit cleanly;
--   * star ids = act - 1 everywhere; the act 1 star is the level script's;
--   * charselect.lua with characters.lua: auto-open, pick, remembered, the other HUDs stay hidden
--     under the menu; Study Group with a friend.
-- Run: tools/luatest/run.sh   (or: lua tools/luatest/test_flow.lua)
local HERE = debug.getinfo(1, "S").source:match("^@(.*/)") or "./"
local Sim = dofile(HERE .. "sim.lua")
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

local HUB, BOB, WF, JRB, CCM, BBH = C.LEVEL_CASTLE_GROUNDS, C.LEVEL_BOB, C.LEVEL_WF, C.LEVEL_JRB, C.LEVEL_CCM, C.LEVEL_BBH
local MS = { IDLE = 0, WAITING = 1, INTRO = 2, ACTIVE = 3, SUCCESS = 4, FAILED = 5, DONE = 6 }
local HUB_SCRIPT = assert(Sim.level_script("castle_grounds"), "levels/castle_grounds/script.c")
local BOB_SCRIPT = assert(Sim.level_script("bob"), "levels/bob/script.c")
local WF_SCRIPT = Sim.level_script("wf")      -- nil until course 2 is built
local JRB_SCRIPT = Sim.level_script("jrb")    -- nil until course 3 is built
local CCM_SCRIPT = Sim.level_script("ccm")    -- nil until course 4 is built
local BBH_SCRIPT = Sim.level_script("bbh")    -- nil until course 5 is built
-- the contract table of docs/flow.md section 2 (door -> slot, level, stars to open)
local CONTRACT = {
    { door = 1, slot = "bob", level = "LEVEL_BOB", stars = 0 },
    { door = 2, slot = "wf", level = "LEVEL_WF", stars = 2 },
    { door = 3, slot = "jrb", level = "LEVEL_JRB", stars = 5 },
    { door = 4, slot = "ccm", level = "LEVEL_CCM", stars = 8 },
    { door = 5, slot = "bbh", level = "LEVEL_BBH", stars = 11 },
    { door = 6, slot = "ttc", level = "LEVEL_TTC", stars = 14 },
}

local function full_world(opts)
    opts = opts or {}
    opts.files = Sim.ALL_FILES
    opts.built = opts.built or Sim.built_on_disk()
    return Sim.new(opts)
end

local function doors_of(script)
    local out = {}
    for _, o in ipairs(script.objects) do
        if o.bhv == "id_bhvSglDoor" then out[(o.bparams >> 24) & 0xFF] = o end
    end
    return out
end
local HUB_DOORS = doors_of(HUB_SCRIPT)

-- stand in front of hub door i, `out` units out from the facade, facing into the door
local function at_door(c, i, out)
    local d = HUB_DOORS[i]
    local yaw = math.floor(d.ry * 0x10000 / 360)
    local a = (yaw & 0xFFFF) / 65536 * 2 * math.pi
    c.pos.x = d.x + math.sin(a) * out
    c.pos.y = d.y
    c.pos.z = d.z + math.cos(a) * out
    c.face.y = (yaw + 0x8000) & 0xFFFF
end

local function state(c)
    local ctx = c.env.sgl_mission_ctx()
    return ctx and ctx.s or nil
end

local function menu_open(c) return c.env._G.sglCharSelectIsOpen ~= nil and c.env._G.sglCharSelectIsOpen() end

-- let a fresh client spawn in the hub, wait for charselect's first-spawn menu and pick friend `pick`
local function arrive_and_pick(w, c, pick)
    w:warp(c, HUB, 1, 0)
    w:step(30)
    check(menu_open(c), c.name .. ": character select opens by itself on the first spawn")
    for _ = 1, (pick or 1) - 1 do
        c.pressed = C.R_JPAD
        w:step(1)
    end
    c.pressed = C.A_BUTTON
    w:step(25)
    check(not menu_open(c), c.name .. ": menu closed after the pick")
end

-- the engine's half of a door / star / death warp: WARP_NODE lookup in the real level script
local function follow_node(script, node)
    local wn = script.warps[node]
    assert(wn ~= nil, "no WARP_NODE " .. string.format("0x%02X", node) .. " in " .. script.slot)
    return C[wn.level], wn.area, wn.node
end

---------------------------------------------------------------------------------------------
test("load: every mod file in coopdx order, strict globals, no duplicate registrations", function()
    local names = table.concat(Sim.ALL_FILES, " ")
    check(#Sim.ALL_FILES >= 8, "found the mod files: " .. names)
    check(names:find("characters.lua charselect.lua course.lua levels.lua main.lua sgl_hud.lua sgl_mission.lua swamp_missions.lua", 1, true) ~= nil,
        "strcmp load order: " .. names)
    local w = full_world()
    local H = w:connect("Host")      -- loading errors (undefined global at load, duplicate command) throw here
    w:step(3)
    for _, cmd in ipairs({ "char", "campus", "school", "mission", "join" }) do
        check(H.commands[cmd] ~= nil, "/" .. cmd .. " registered")
    end
    check(H.menu["Choose your friend"] ~= nil and H.menu["Join my study group"] ~= nil, "both mod menu buttons")
    check(H.env.gLevelValues.entryLevel == HUB and H.env.gLevelValues.exitCastleLevel == HUB
        and H.env.gLevelValues.exitCastleWarpNode == 0x0A, "entry / exit-to-castle = hub Plaza 0x0A")
    check(H.env.gServerSettings.skipIntro == 1, "intro skipped (hub replaces Peach's castle grounds)")
    check(type(H.env._G.sglFriends) == "table" and #H.env._G.sglFriends == 10, "characters.lua exports 10 friends")
    check(H.env._G.sglOpenCharSelect ~= nil and H.env._G.sglOnFriendSet ~= nil, "charselect.lua exports its hooks")
end)

test("contract: hub doors, warp nodes and return spawns match course.lua (all six doors)", function()
    local w = full_world()
    local H = w:connect("Host")
    w:step(2)
    for _, k in ipairs(CONTRACT) do
        local stage = H.env.sgl_stage_by_door(k.door)
        check(stage ~= nil and stage.slot == k.slot and stage.level == C[k.level] and stage.stars == k.stars,
            "course.lua door " .. k.door .. " = " .. k.slot .. " / " .. k.stars .. " stars")
        local d = HUB_DOORS[k.door]
        check(d ~= nil and ((d.bparams >> 16) & 0xFF) == 0x10 + k.door, "hub door object " .. k.door .. " uses node 0x1" .. k.door)
        local lv, area, node = follow_node(HUB_SCRIPT, 0x10 + k.door)
        check(lv == C[k.level] and area == 1 and node == 0x0A, "hub 0x1" .. k.door .. " -> " .. k.level .. " 0x0A")
        for _, base in ipairs({ 0x20, 0x30 }) do
            local lv2, _, node2 = follow_node(HUB_SCRIPT, base + k.door)
            check(lv2 == HUB and node2 == base + k.door, string.format("hub 0x%02X is a spawn node", base + k.door))
        end
        local stageScript = Sim.level_script(k.slot)
        if stageScript ~= nil then
            check(stageScript.warps[0x0A] ~= nil, k.slot .. ": entry node 0x0A")
            local lv3, _, n3 = follow_node(stageScript, 0xF0)
            local lv4, _, n4 = follow_node(stageScript, 0xF1)
            check(lv3 == HUB and n3 == 0x20 + k.door and lv4 == HUB and n4 == 0x30 + k.door,
                k.slot .. ": 0xF0 -> hub 0x2" .. k.door .. ", 0xF1 -> hub 0x3" .. k.door)
        end
    end
    -- the hub spawn objects behind those nodes
    w:warp(H, HUB, 1, 0)
    for i = 1, 6 do
        local s2, s3 = H.levelSpawns[0x20 + i], H.levelSpawns[0x30 + i]
        check(s2 and s2.bhv == "bhvPaintingStarCollectWarp" and s3 and s3.bhv == "bhvPaintingDeathWarp",
            "door " .. i .. ": star return + death return spawn objects")
        -- the return spot is outside the door trigger (1.5 m), so arriving never re-enters the door
        local d = HUB_DOORS[i]
        local dist = math.sqrt((s2.x - d.x) ^ 2 + (s2.z - d.z) ^ 2)
        check(dist > 200 and dist < 400, string.format("door %d return spawn %.1f m out", i, dist / 100))
    end
    check(H.levelSpawns[0x0A] and H.levelSpawns[0x0A].bhv == "bhvSpinAirborneWarp", "hub Plaza spawn 0x0A")
    w:warp(H, BOB, 1, 1)
    check(H.levelSpawns[0x0A] and H.levelSpawns[0x0A].bhv == "bhvSpinAirborneWarp", "BOB entry spawn 0x0A")
end)

test("acts: vanilla act select reaches every playable act in order; the rest are COMING SOON", function()
    local w = full_world()
    local H = w:connect("Host")
    w:step(2)
    local env = H.env
    -- sanity of the act select model (star_select.c)
    local function same(a, b) return table.concat(a, ",") == table.concat(b, ",") end
    check(same(Sim.selectable_acts(0), { 1 }), "no stars: act 1")
    check(same(Sim.selectable_acts(0x01), { 1, 2 }), "act 1 star: acts 1, 2")
    check(same(Sim.selectable_acts(0x04), { 1, 3 }), "only act 3 (via /join): acts 1 and 3, not 2")
    check(same(Sim.selectable_acts(0x07), { 1, 2, 3, 4 }), "acts 1-3: up to 4")
    check(same(Sim.selectable_acts(0x40), { 1 }), "the 100-coin star opens nothing")
    for _, stage in ipairs(env.SGL_STAGES) do
        local slot = Sim.level_script(stage.slot)
        if slot ~= nil then
            local starActs = 0
            for _, o in ipairs(slot.objects) do
                if o.bhv == "bhvStar" then
                    check(((o.bparams >> 24) & 0xFF) <= 6, stage.slot .. ": level-script star id 0..6")
                    -- a level-script star of act k must have id k - 1
                    for k = 1, 6 do
                        if o.acts == (1 << (k - 1)) then
                            check((o.bparams >> 24) == k - 1, stage.slot .. ": act " .. k .. " star has id " .. (k - 1))
                            starActs = starActs | (1 << (k - 1))
                        end
                    end
                end
            end
            local lastPlayable, gap = 0, false
            for k = 1, 6 do
                local def = env.sgl_mission_get(stage.level, k)
                local playable = def ~= nil or (starActs >> (k - 1)) & 1 == 1
                if def ~= nil then
                    check(def.starId == k - 1, stage.name .. " act " .. k .. ": mission star id " .. (k - 1))
                    check(not def.levelStar or (starActs >> (k - 1)) & 1 == 1,
                        stage.name .. " act " .. k .. ": levelStar mission has its level-script star")
                    check(def.levelStar or (starActs >> (k - 1)) & 1 == 0,
                        stage.name .. " act " .. k .. ": a mission that spawns its star has no level-script one")
                end
                if playable then
                    if lastPlayable ~= k - 1 then gap = true end
                    lastPlayable = k
                    check(not env.sgl_act_is_soon(stage, k), stage.name .. " act " .. k .. " is playable: not named COMING SOON")
                else
                    check(env.sgl_act_is_soon(stage, k), stage.name .. " act " .. k .. " has nothing: named COMING SOON")
                end
            end
            check(not gap, stage.name .. ": playable acts are 1.." .. lastPlayable .. " with no gap (act select would stop at a gap)")
            -- walk the act select from an empty save: every playable act becomes selectable in turn
            local flags = 0
            for k = 1, lastPlayable do
                local acts = Sim.selectable_acts(flags)
                check(acts[#acts] == k, stage.name .. ": act " .. k .. " selectable after acts 1.." .. (k - 1))
                flags = flags | (1 << (k - 1))
            end
            -- the first act is solo-able (a new player is never stuck at the door)
            local d1 = env.sgl_mission_get(stage.level, 1)
            check(d1 == nil or d1.minPlayers == 1, stage.name .. ": act 1 needs no second player")
        end
    end
end)

test("single player: hub -> character select -> door -> act 1 -> star -> back outside the Auditorium", function()
    local w = full_world()
    local H = w:connect("Host")
    w:step(3)
    arrive_and_pick(w, H, 4)                                     -- 4th card: Anh
    check(Sim.find(H.popups, "University of Florida") == nil, "no door hint while the menu was up (it would be missed)")
    w:seconds(2)
    check(Sim.find(H.popups, "Walk into the University Auditorium door to enter THE SWAMP") ~= nil,
        "door hint once the menu is gone")
    check(Sim.hud_has(H, "NEXT: THE SWAMP") and Sim.hud_has(H, "UNIVERSITY AUDITORIUM door"), "hub NEXT panel")
    local env = H.env
    check(H.strStorage.friend == "anh" and env.gPlayerSyncTable[0].friend == 4, "pick saved + synced (Anh)")
    w:step(2)
    check(raw(H.ms[0].marioObj)._model == env._G.sglFriends[4].model, "characters.lua swapped the model")
    check(H.ms[0].numLives == 4, "4 lives")

    -- doors: 6 objects from the hub script; with 0 stars only The Swamp's opens (Reitz is built but locked)
    local doors = Sim.objects_with(H, env.id_bhvSglDoor)
    check(#doors == 6, "six hub doors")
    local models = {}
    for _, o in ipairs(doors) do models[(raw(o).oBehParams >> 24) & 0xFF] = raw(o)._model end
    check(models[1] == C.E_MODEL_STAR, "Auditorium door: gold star (open)")
    check(models[5] == C.E_MODEL_TRANSPARENT_STAR and models[2] == C.E_MODEL_TRANSPARENT_STAR, "locked / unbuilt stages: see-through star")
    local flames = Sim.objects_with(H, env.id_bhvSglDoorFx)
    local shown = 0
    for _, f in ipairs(flames) do
        if (raw(f).header.gfx.node.flags & C.GRAPH_RENDER_INVISIBLE) == 0 then shown = shown + 1 end
    end
    check(#flames == 12 and shown == 10, "two flames per door, hidden only at the open door (" .. shown .. " shown)")

    -- Library West: built (Course 5) and LOCKED at 0 stars (coming soon while levels/bbh is not built)
    at_door(H, 5, 50)
    w:step(3)
    if BBH_SCRIPT ~= nil then
        check(Sim.find(H.popups, "Locked!.-LIBRARY WEST AFTER DARK needs 11 stars %(you have 0%)") ~= nil, "Library West: locked popup (11 stars)")
    else
        check(Sim.find(H.popups, "LIBRARY WEST AFTER DARK.-coming soon %(opens at 11 stars%)") ~= nil, "Library West: coming soon popup")
    end
    check(H.action ~= C.ACT_DISAPPEARED and H.level == HUB, "stays in the hub")
    -- Century Tower: not built yet, coming soon
    at_door(H, 6, 50)
    w:step(3)
    check(Sim.find(H.popups, "CENTURY TOWER.-coming soon %(opens at 14 stars%)") ~= nil, "Century Tower: coming soon popup (14 stars)")
    check(H.action ~= C.ACT_DISAPPEARED and H.level == HUB, "stays in the hub")

    -- the Auditorium door label, then walk in
    at_door(H, 1, 600)
    w:step(2)
    check(Sim.hud_has(H, "THE SWAMP") and Sim.hud_has(H, "Walk in!"), "door label: THE SWAMP / Walk in!")
    at_door(H, 1, 50)
    w:step(2)
    local m = H.ms[0]
    check(H.action == C.ACT_DISAPPEARED and raw(m).actionArg == (C.WARP_OP_WARP_OBJECT << 16) + 2,
        "vanilla warp-object entry (ACT_DISAPPEARED, WARP_OP_WARP_OBJECT)")
    local used = raw(m).usedObj
    check(used ~= nil and ((raw(used).oBehParams >> 16) & 0xFF) == 0x11, "usedObj carries hub node 0x11")
    local lv, area, node = follow_node(HUB_SCRIPT, 0x11)
    check(lv == BOB and area == 1 and node == 0x0A, "hub 0x11 -> BOB 0x0A")

    -- act select (vanilla): only act 1 with an empty save
    local acts = Sim.selectable_acts(w.starFlags[C.COURSE_BOB] or 0)
    check(#acts == 1 and acts[1] == 1, "act select offers act 1 only")
    H.action = C.ACT_IDLE
    w:warp(H, lv, area, acts[1])
    w:step(5)
    check(Sim.hud_has(H, "KICKOFF"), "act 1 banner")
    check(Sim.stars_of(H, 0) == 1, "the level-script act 1 star is there")
    check(Sim.find(H.console, "spawns its own") == nil and Sim.find(H.console, "has no star") == nil, "no star warning")
    w:seconds(3.5)
    check(state(H) == MS.ACTIVE, "mission active")
    local P = env.SWAMP_POINTS
    H.pos.x, H.pos.y, H.pos.z = P.climb_goal.x, P.climb_goal.y, P.climb_goal.z
    w:step(4)
    check(state(H) == MS.SUCCESS and #H.starSpawns == 0, "roof reached: success, no extra star")
    local star = Sim.objects_with(H, C.id_bhvStar)[1]
    Sim.run_hooks(H, C.HOOK_ON_INTERACT, H.ms[0], star, C.INTERACT_STAR_OR_KEY, true)
    -- the engine: save the star (id 0 -> bit 0), star dance, exit through BOB 0xF0
    w.starFlags[C.COURSE_BOB] = (w.starFlags[C.COURSE_BOB] or 0) | (1 << ((raw(star).oBehParams >> 24) & 0xFF))
    w:step(3)
    check(state(H) == MS.DONE, "mission DONE")
    local lv2, a2, n2 = follow_node(BOB_SCRIPT, 0xF0)
    check(lv2 == HUB and n2 == 0x21, "BOB 0xF0 -> hub 0x21")
    w:warp(H, lv2, a2, 0)
    local sp = H.levelSpawns[n2]
    H.pos.x, H.pos.y, H.pos.z = sp.x, sp.y - 80, sp.z
    H.face.y = sp.yaw
    w:step(5)
    check(H.action ~= C.ACT_DISAPPEARED, "landing outside the Auditorium does not re-enter the door")
    check(H.env.sgl_total_stars() == 1, "1 star")
    -- next visit: act select offers act 2 (the race)
    acts = Sim.selectable_acts(w.starFlags[C.COURSE_BOB])
    check(acts[#acts] == 2 and env.sgl_mission_get(BOB, 2).id == "swamp_sprint", "act 2 = STADIUM STAIR SPRINT")

    -- death return: BOB 0xF1 -> hub 0x31 (same spot outside the Auditorium)
    local lv3, _, n3 = follow_node(BOB_SCRIPT, 0xF1)
    check(lv3 == HUB and n3 == 0x31 and H.levelSpawns[0x31].x == H.levelSpawns[0x21].x, "BOB 0xF1 -> hub 0x31")
    -- lives are topped up in the hub
    H.ms[0].numLives = 2
    w:step(2)
    check(H.ms[0].numLives == 4, "hub tops lives back up to 4")
end)

test("door 2: The Hub (2 stars) -> Reitz & Engineering act 1 -> star -> back outside The Hub door", function()
    if WF_SCRIPT == nil then
        print("  (levels/wf not built: skipped)")
        return
    end
    -- 1 star: built but LOCKED
    local w = full_world({ starFlags = { [C.COURSE_BOB] = 0x01 } })
    local H = w:connect("Host")
    H.strStorage.friend = "josh"
    w:step(3)
    w:warp(H, HUB, 1, 0)
    w:seconds(2)
    local env = H.env
    check(env.sgl_stage_ready(env.sgl_stage_by_door(2)), "levels/wf is ours: course 2 is built")
    check(Sim.hud_has(H, "NEXT: THE SWAMP"), "1 star: the hint still points at The Swamp (act 2)")
    at_door(H, 2, 600)
    w:step(2)
    check(Sim.hud_has(H, "REITZ & ENGINEERING") and Sim.hud_has(H, "LOCKED %- 2 stars %(you have 1%)"), "door 2 label: LOCKED")
    at_door(H, 2, 50)
    w:step(3)
    check(Sim.find(H.popups, "Locked!.-REITZ & ENGINEERING needs 2 stars %(you have 1%)") ~= nil, "locked popup")
    check(H.action ~= C.ACT_DISAPPEARED and H.level == HUB, "a locked door does not open")

    -- 2 stars (Swamp acts 1 + 2), alone: open, and the hint skips The Swamp's co-op act 3
    w = full_world({ starFlags = { [C.COURSE_BOB] = 0x03 } })
    H = w:connect("Host")
    H.strStorage.friend = "josh"
    w:step(3)
    w:warp(H, HUB, 1, 0)
    w:seconds(2)
    env = H.env
    check(Sim.find(H.popups, "Walk into The Hub door to enter REITZ & ENGINEERING!") ~= nil,
        "first hub visit: 'Walk into The Hub door' (no 'the The Hub')")
    check(Sim.hud_has(H, "NEXT: REITZ & ENGINEERING") and Sim.hud_has(H, "THE HUB door"),
        "alone with Swamp acts 1-2: NEXT points at Reitz (Swamp act 3 needs 2 players)")
    local doors = Sim.objects_with(H, env.id_bhvSglDoor)
    local model2
    for _, o in ipairs(doors) do
        if ((raw(o).oBehParams >> 24) & 0xFF) == 2 then model2 = raw(o)._model end
    end
    check(model2 == C.E_MODEL_STAR, "door 2: gold star (open)")
    at_door(H, 2, 600)
    w:step(2)
    check(Sim.hud_has(H, "REITZ & ENGINEERING") and Sim.hud_has(H, "Walk in!"), "door 2 label: Walk in!")
    at_door(H, 2, 50)
    w:step(2)
    local m = H.ms[0]
    check(H.action == C.ACT_DISAPPEARED and raw(m).actionArg == (C.WARP_OP_WARP_OBJECT << 16) + 2, "door 2: vanilla warp-object entry")
    local used = raw(m).usedObj
    check(used ~= nil and ((raw(used).oBehParams >> 16) & 0xFF) == 0x12, "usedObj carries hub node 0x12")
    local lv, area, node = follow_node(HUB_SCRIPT, 0x12)
    check(lv == WF and area == 1 and node == 0x0A, "hub 0x12 -> WF 0x0A")
    local acts = Sim.selectable_acts(w.starFlags[C.COURSE_WF] or 0)
    check(#acts == 1 and acts[1] == 1, "act select offers act 1 only")
    H.action = C.ACT_IDLE
    w:warp(H, lv, area, acts[1])
    local sp0 = H.levelSpawns[0x0A]
    check(sp0 and sp0.bhv == "bhvSpinAirborneWarp", "WF entry spawn 0x0A (spin-in)")
    H.pos.x, H.pos.y, H.pos.z = sp0.x, sp0.y - 100, sp0.z
    w:step(5)
    check(Sim.hud_has(H, "REITZ & ENGINEERING %- ACT 1") and Sim.hud_has(H, "ROOFTOP OF THE REITZ"), "act 1 banner")
    check(Sim.stars_of(H, 0) == 0, "no level-script star: the mission spawns act 1's")
    check(#Sim.objects_with(H, env.id_bhvSglReitzPlatform) == 1, "the window-washer lift is there")
    Sim.cmd(H, "campus", "where")
    -- the spawn in campus map metres (stages.json reitz_eng centre (-470, -293): x = X/100 - 470, y = -Z/100 - 293)
    local mx, my = sp0.x / 100 - 470, -sp0.z / 100 - 293
    check(Sim.find(H.chat, string.format("campus map: %.1f m east, %.1f m north", mx, my):gsub("%-", "%%-"):gsub("%.", "%%.")) ~= nil,
        string.format("/campus where: campus map metres at the spawn (%.1f, %.1f)", mx, my))
    check(math.abs(mx - (-398.0)) < 0.6 and math.abs(my - (-200.0)) < 0.6, "WF spawn on the North Lawn NE of the Reitz Union")
    w:seconds(3.5)
    check(state(H) == MS.ACTIVE, "mission active")
    local P = env.REITZ_POINTS
    H.pos.x, H.pos.y, H.pos.z = P.roof_goal.x, P.roof_goal.y, P.roof_goal.z
    w:step(4)
    check(state(H) == MS.SUCCESS, "penthouse roof: success")
    w:step(3)
    check(#H.starSpawns == 1 and Sim.stars_of(H, 0) == 1, "one star, id 0")
    local star = Sim.objects_with(H, C.id_bhvStarSpawnCoordinates)[1]
    Sim.run_hooks(H, C.HOOK_ON_INTERACT, H.ms[0], star, C.INTERACT_STAR_OR_KEY, true)
    w.starFlags[C.COURSE_WF] = (w.starFlags[C.COURSE_WF] or 0) | (1 << ((raw(star).oBehParams >> 24) & 0xFF))
    raw(star).activeFlags = C.ACTIVE_FLAG_DEACTIVATED
    w:step(3)
    check(state(H) == MS.DONE, "mission DONE")
    -- star exit: WF 0xF0 -> hub 0x22, outside The Hub door
    local lv2, a2, n2 = follow_node(WF_SCRIPT, 0xF0)
    check(lv2 == HUB and n2 == 0x22, "WF 0xF0 -> hub 0x22")
    w:warp(H, lv2, a2, 0)
    local sp = H.levelSpawns[n2]
    check(sp ~= nil and sp.bhv == "bhvPaintingStarCollectWarp", "hub 0x22 is a star-return spawn")
    local d = HUB_DOORS[2]
    check(math.sqrt((sp.x - d.x) ^ 2 + (sp.z - d.z) ^ 2) < 400, "0x22 is right outside The Hub door")
    H.pos.x, H.pos.y, H.pos.z = sp.x, sp.y - 80, sp.z
    H.face.y = sp.yaw
    w:step(5)
    check(H.action ~= C.ACT_DISAPPEARED, "landing outside The Hub does not re-enter the door")
    check(env.sgl_total_stars() == 3, "3 stars")
    acts = Sim.selectable_acts(w.starFlags[C.COURSE_WF])
    check(acts[#acts] == 2 and env.sgl_mission_get(WF, 2).id == "reitz_tokens", "next visit: act 2 = MEAL SWIPE TOKENS")
    -- death / Exit course: WF 0xF1 -> hub 0x32, the same spot
    local lv3, _, n3 = follow_node(WF_SCRIPT, 0xF1)
    check(lv3 == HUB and n3 == 0x32 and H.levelSpawns[0x32].bhv == "bhvPaintingDeathWarp"
        and H.levelSpawns[0x32].x == sp.x and H.levelSpawns[0x32].z == sp.z, "WF 0xF1 -> hub 0x32 (same spot)")
    -- with a friend online the co-op Swamp act 3 is doable again: the hint goes back to The Swamp
    check(env.sgl_next_stage().key == "reitz", "alone: next = Reitz")
    w:connect("Friend")
    w:step(3)
    check(env.sgl_next_stage().key == "swamp", "2 players online: next = The Swamp (its co-op act 3)")
end)

test("door 3: Newell Hall (5 stars) -> Lake Alice act 1 -> star -> back outside the Newell Hall door", function()
    if JRB_SCRIPT == nil then
        print("  (levels/jrb not built: skipped)")
        return
    end
    -- 4 stars (Swamp acts 1-3, Reitz act 1): built but LOCKED
    local w = full_world({ starFlags = { [C.COURSE_BOB] = 0x07, [C.COURSE_WF] = 0x01 } })
    local H = w:connect("Host")
    H.strStorage.friend = "josh"
    w:step(3)
    w:warp(H, HUB, 1, 0)
    w:seconds(2)
    local env = H.env
    check(env.sgl_stage_ready(env.sgl_stage_by_door(3)), "levels/jrb is ours: course 3 is built")
    check(env.sgl_total_stars() == 4, "4 stars")
    check(env.sgl_next_stage() ~= env.sgl_stage_by_door(3), "Lake Alice locked: the NEXT stage is not Lake Alice")
    at_door(H, 3, 600)
    w:step(2)
    check(Sim.hud_has(H, "LAKE ALICE") and Sim.hud_has(H, "LOCKED %- 5 stars %(you have 4%)"), "door 3 label: LOCKED")
    at_door(H, 3, 50)
    w:step(3)
    check(Sim.find(H.popups, "Locked!.-LAKE ALICE needs 5 stars %(you have 4%)") ~= nil, "locked popup")
    check(H.action ~= C.ACT_DISAPPEARED and H.level == HUB, "a locked door does not open")

    -- 6 stars (every playable act of courses 1-2): open, and the hint points at Newell Hall
    w = full_world({ starFlags = { [C.COURSE_BOB] = 0x07, [C.COURSE_WF] = 0x07 } })
    H = w:connect("Host")
    H.strStorage.friend = "josh"
    -- Lake Alice's gator stand-ins (act 1's lurking gators, act 2's line) read gObjectAnimations (a real v1.5.1
    -- global: smlua_cobject.c exposes gGlobalObjectAnimations under that name; the sushi field is in
    -- smlua_anim_utils.h) and call obj_init_animation: the stubs of test_lake_missions.lua's prep, which tests
    -- the acts themselves.
    H.stubs.gObjectAnimations = { swoop_seg6_anims_060070D0 = "ANIM:swoop", sushi_seg5_anims_0500AE54 = "ANIM:sushi" }
    H.stubs.obj_init_animation = function(o, i) raw(o)._anim = i end
    w:step(3)
    w:warp(H, HUB, 1, 0)
    w:seconds(2)
    env = H.env
    check(env.sgl_total_stars() == 6, "6 stars")
    check(Sim.find(H.popups, "Walk into the Newell Hall door to enter LAKE ALICE!") ~= nil, "first hub visit: door hint names Newell Hall")
    check(Sim.hud_has(H, "NEXT: LAKE ALICE") and Sim.hud_has(H, "NEWELL HALL door"), "hub NEXT panel: Lake Alice")
    local model3
    for _, o in ipairs(Sim.objects_with(H, env.id_bhvSglDoor)) do
        if ((raw(o).oBehParams >> 24) & 0xFF) == 3 then model3 = raw(o)._model end
    end
    check(model3 == C.E_MODEL_STAR, "door 3: gold star (open)")
    at_door(H, 3, 600)
    w:step(2)
    check(Sim.hud_has(H, "LAKE ALICE") and Sim.hud_has(H, "Walk in!"), "door 3 label: Walk in!")
    at_door(H, 3, 50)
    w:step(2)
    local m = H.ms[0]
    check(H.action == C.ACT_DISAPPEARED and raw(m).actionArg == (C.WARP_OP_WARP_OBJECT << 16) + 2, "door 3: vanilla warp-object entry")
    local used = raw(m).usedObj
    check(used ~= nil and ((raw(used).oBehParams >> 16) & 0xFF) == 0x13, "usedObj carries hub node 0x13")
    local lv, area, node = follow_node(HUB_SCRIPT, 0x13)
    check(lv == JRB and area == 1 and node == 0x0A, "hub 0x13 -> JRB 0x0A")
    local acts = Sim.selectable_acts(w.starFlags[C.COURSE_JRB] or 0)
    check(#acts == 1 and acts[1] == 1, "act select offers act 1 only")
    H.action = C.ACT_IDLE
    w:warp(H, lv, area, acts[1])
    local sp0 = H.levelSpawns[0x0A]
    check(sp0 and sp0.bhv == "bhvSpinAirborneWarp", "JRB entry spawn 0x0A (spin-in)")
    H.pos.x, H.pos.y, H.pos.z = sp0.x, sp0.y - 100, sp0.z
    w:step(5)
    check(Sim.hud_has(H, "LAKE ALICE %- ACT 1") and Sim.hud_has(H, "BOARDWALK WELCOME"), "act 1 banner")
    check(Sim.stars_of(H, 0) == 0, "no level-script star: the mission spawns act 1's")
    local P = env.LAKE_POINTS
    check(sp0.x == P.spawn_field.x and sp0.z == P.spawn_field.z, "LAKE_POINTS.spawn_field = the level script's spawn")
    Sim.cmd(H, "campus", "where")
    -- the spawn in campus map metres (stages.json lake_alice centre (-1760, -660): x = X/100 - 1760, y = -Z/100 - 660)
    local mx, my = sp0.x / 100 - 1760, -sp0.z / 100 - 660
    check(Sim.find(H.chat, string.format("campus map: %.1f m east, %.1f m north", mx, my):gsub("%-", "%%-"):gsub("%.", "%%.")) ~= nil,
        string.format("/campus where: campus map metres at the spawn (%.1f, %.1f)", mx, my))
    check(math.abs(mx - (-1893.0)) < 0.6 and math.abs(my - (-541.0)) < 0.6, "JRB spawn on the bat-house field (shore module spawn_field)")
    w:seconds(3.5)
    check(state(H) == MS.ACTIVE, "mission active")
    H.pos.x, H.pos.y, H.pos.z = P.deck.x, P.deck.y, P.deck.z
    w:step(4)
    check(state(H) == MS.SUCCESS, "on the lake-centre deck: success")
    w:step(3)
    check(#H.starSpawns == 1 and Sim.stars_of(H, 0) == 1, "one star, id 0")
    local star = Sim.objects_with(H, C.id_bhvStarSpawnCoordinates)[1]
    Sim.run_hooks(H, C.HOOK_ON_INTERACT, H.ms[0], star, C.INTERACT_STAR_OR_KEY, true)
    w.starFlags[C.COURSE_JRB] = (w.starFlags[C.COURSE_JRB] or 0) | (1 << ((raw(star).oBehParams >> 24) & 0xFF))
    raw(star).activeFlags = C.ACTIVE_FLAG_DEACTIVATED
    w:step(3)
    check(state(H) == MS.DONE, "mission DONE")
    -- star exit: JRB 0xF0 -> hub 0x23, outside the Newell Hall door
    local lv2, a2, n2 = follow_node(JRB_SCRIPT, 0xF0)
    check(lv2 == HUB and n2 == 0x23, "JRB 0xF0 -> hub 0x23")
    w:warp(H, lv2, a2, 0)
    local sp = H.levelSpawns[n2]
    check(sp ~= nil and sp.bhv == "bhvPaintingStarCollectWarp", "hub 0x23 is a star-return spawn")
    local d = HUB_DOORS[3]
    check(math.sqrt((sp.x - d.x) ^ 2 + (sp.z - d.z) ^ 2) < 400, "0x23 is right outside the Newell Hall door")
    H.pos.x, H.pos.y, H.pos.z = sp.x, sp.y - 80, sp.z
    H.face.y = sp.yaw
    w:step(5)
    check(H.action ~= C.ACT_DISAPPEARED, "landing outside Newell Hall does not re-enter the door")
    check(env.sgl_total_stars() == 7, "7 stars")
    acts = Sim.selectable_acts(w.starFlags[C.COURSE_JRB])
    check(acts[#acts] == 2 and env.sgl_mission_get(JRB, 2).id == "lake_gator_hop", "next visit: act 2 = GATOR HOP")
    check(env.sgl_next_stage().key == "alice", "the hint stays on Lake Alice (act 2)")
    -- death / Exit course: JRB 0xF1 -> hub 0x33, the same spot
    local lv3, _, n3 = follow_node(JRB_SCRIPT, 0xF1)
    check(lv3 == HUB and n3 == 0x33 and H.levelSpawns[0x33].bhv == "bhvPaintingDeathWarp"
        and H.levelSpawns[0x33].x == sp.x and H.levelSpawns[0x33].z == sp.z, "JRB 0xF1 -> hub 0x33 (same spot)")
    -- /campus alice 2 from the host: straight into act 2 (the door lock and act select skipped, as for the other stages)
    Sim.cmd(H, "campus", "alice 2")
    w:step(3)
    check(H.level == JRB and H.act == 2, "/campus alice 2 -> Lake Alice act 2")
end)

test("door 4: Marston (8 stars) -> Marston Science Library act 1 -> star -> back outside the Marston door", function()
    if CCM_SCRIPT == nil then
        print("  (levels/ccm not built: skipped)")
        return
    end
    -- the engine names the Marston props use (Toad librarians, flying bookends, a book's hit): stubbed per client as in
    -- test_marston_missions.lua's prep, which tests the acts themselves
    local function marston_stubs(c)
        c.stubs.gObjectAnimations = { toad_seg6_anims_0600FB58 = "ANIM:toad", bookend_seg5_anims_05002540 = "ANIM:bookend",
            swoop_seg6_anims_060070D0 = "ANIM:swoop", sushi_seg5_anims_0500AE54 = "ANIM:sushi" }
        c.stubs.obj_init_animation = function(o, i) raw(o)._anim = i end
        c.stubs.hurt_and_set_mario_action = function(m, action) raw(m).action = action return 1 end
        -- levels.lua's interior camera (coopdx v1.5.1 rom-hack camera getters / setters): recorded in c.cam
        c.cam = { zoomed_in_dist = 900, zoomed_out_dist = 1400, zoomed_in_height = 300, zoomed_out_height = 450, collisions = 0 }
        for f in pairs(c.cam) do
            c.stubs["camera_romhack_get_" .. f] = function() return c.cam[f] end
            c.stubs["camera_romhack_set_" .. f] = function(v) assert(math.type(v) == "integer"); c.cam[f] = v end
        end
    end
    -- 7 stars (every playable act of courses 1-2, Lake Alice act 1): built but LOCKED
    local w = full_world({ starFlags = { [C.COURSE_BOB] = 0x07, [C.COURSE_WF] = 0x07, [C.COURSE_JRB] = 0x01 } })
    local H = w:connect("Host")
    H.strStorage.friend = "josh"
    marston_stubs(H)
    -- the door signposts (rewritten on every hub visit) take their star counts from course.lua
    local signs = {}
    H.stubs.smlua_text_utils_dialog_replace = function(id, _, _, _, _, text) signs[id] = text end
    w:step(3)
    w:warp(H, HUB, 1, 0)
    w:seconds(2)
    local env = H.env
    local function sign_says(building, line)
        for _, t in pairs(signs) do
            if t:find(building, 1, true) == 1 and t:find(line, 1, true) ~= nil then return true end
        end
        return false
    end
    check(sign_says("MARSTON SCIENCE LIBRARY", "Opens at 8 stars.") and sign_says("MARSTON SCIENCE LIBRARY", "Walk into the door"),
        "Marston's signpost: opens at 8 stars, walk in (built)")
    check(sign_says("NEWELL HALL", "Opens at 5 stars.") and sign_says("THE HUB", "Opens at 2 stars."),
        "Newell Hall's and The Hub's signposts match their doors (5 and 2 stars)")
    check(env.sgl_stage_ready(env.sgl_stage_by_door(4)), "levels/ccm is ours: course 4 is built")
    check(env.sgl_total_stars() == 7, "7 stars")
    check(env.sgl_next_stage() ~= env.sgl_stage_by_door(4), "Marston locked: the NEXT stage is not Marston")
    at_door(H, 4, 600)
    w:step(2)
    check(Sim.hud_has(H, "MARSTON LIBRARY") and Sim.hud_has(H, "LOCKED %- 8 stars %(you have 7%)"), "door 4 label: LOCKED")
    at_door(H, 4, 50)
    w:step(3)
    check(Sim.find(H.popups, "Locked!.-MARSTON LIBRARY needs 8 stars %(you have 7%)") ~= nil, "locked popup")
    check(H.action ~= C.ACT_DISAPPEARED and H.level == HUB, "a locked door does not open")

    -- 9 stars (every playable act of courses 1-3): open, and the hint points at the Marston door
    w = full_world({ starFlags = { [C.COURSE_BOB] = 0x07, [C.COURSE_WF] = 0x07, [C.COURSE_JRB] = 0x07 } })
    H = w:connect("Host")
    H.strStorage.friend = "josh"
    marston_stubs(H)
    w:step(3)
    w:warp(H, HUB, 1, 0)
    w:seconds(2)
    env = H.env
    check(env.sgl_total_stars() == 9, "9 stars")
    check(Sim.find(H.popups, "Walk into the Marston Science Library door to enter MARSTON LIBRARY!") ~= nil,
        "first hub visit: door hint names the Marston Science Library door")
    check(Sim.hud_has(H, "NEXT: MARSTON LIBRARY") and Sim.hud_has(H, "MARSTON SCIENCE LIBRARY door"), "hub NEXT panel: Marston")
    local model4
    for _, o in ipairs(Sim.objects_with(H, env.id_bhvSglDoor)) do
        if ((raw(o).oBehParams >> 24) & 0xFF) == 4 then model4 = raw(o)._model end
    end
    check(model4 == C.E_MODEL_STAR, "door 4: gold star (open)")
    at_door(H, 4, 600)
    w:step(2)
    check(Sim.hud_has(H, "MARSTON LIBRARY") and Sim.hud_has(H, "Walk in!"), "door 4 label: Walk in!")
    at_door(H, 4, 50)
    w:step(2)
    local m = H.ms[0]
    check(H.action == C.ACT_DISAPPEARED and raw(m).actionArg == (C.WARP_OP_WARP_OBJECT << 16) + 2, "door 4: vanilla warp-object entry")
    local used = raw(m).usedObj
    check(used ~= nil and ((raw(used).oBehParams >> 16) & 0xFF) == 0x14, "usedObj carries hub node 0x14")
    local lv, area, node = follow_node(HUB_SCRIPT, 0x14)
    check(lv == CCM and area == 1 and node == 0x0A, "hub 0x14 -> CCM 0x0A")
    local acts = Sim.selectable_acts(w.starFlags[C.COURSE_CCM] or 0)
    check(#acts == 1 and acts[1] == 1, "act select offers act 1 only")
    H.action = C.ACT_IDLE
    w:warp(H, lv, area, acts[1])
    local sp0 = H.levelSpawns[0x0A]
    check(sp0 and sp0.bhv == "bhvSpinAirborneWarp", "CCM entry spawn 0x0A (spin-in)")
    H.pos.x, H.pos.y, H.pos.z = sp0.x, sp0.y - 100, sp0.z
    w:step(5)
    check(Sim.hud_has(H, "MARSTON LIBRARY %- ACT 1") and Sim.hud_has(H, "OUT%-OF%-ORDER ELEVATOR"), "act 1 banner")
    check(Sim.stars_of(H, 0) == 0, "no level-script star: the mission spawns act 1's")
    local P = env.MARSTON_POINTS
    check(sp0.x == P.spawn.x and sp0.z == P.spawn.z and sp0.y - 100 == P.spawn.y, "MARSTON_POINTS.spawn = the level script's spawn")
    Sim.cmd(H, "campus", "where")
    -- the spawn in campus map metres (stages.json marston centre (-59.6, -98.9): x = X/100 - 59.6, y = -Z/100 - 98.9)
    local mx, my = sp0.x / 100 - 59.6, -sp0.z / 100 - 98.9
    check(Sim.find(H.chat, string.format("campus map: %.1f m east, %.1f m north", mx, my):gsub("%-", "%%-"):gsub("%.", "%%.")) ~= nil,
        string.format("/campus where: campus map metres at the spawn (%.1f, %.1f)", mx, my))
    check(math.abs(mx - (-67.5)) < 0.6 and math.abs(my - (-83.8)) < 0.6, "CCM spawn in the Marston lobby (layout entrance.spawn)")
    w:seconds(3.5)
    check(state(H) == MS.ACTIVE, "mission active")
    check(H.cam.zoomed_in_dist == env.SGL_STAGE_CAMERA[CCM].inDist and H.cam.collisions == 1,
        "inside Marston: the interior rom-hack camera (closer, collision on)")
    check(#Sim.objects_with(H, env.id_bhvSglMarstonSolid) == #P.stair_doors, "act 1: the stair barriers stand")
    H.pos.x, H.pos.y, H.pos.z = P.climb_goal.x, P.climb_goal.y, P.climb_goal.z
    w:step(4)
    check(state(H) == MS.SUCCESS, "in the 5th-floor reading room: success")
    w:step(3)
    check(#H.starSpawns == 1 and Sim.stars_of(H, 0) == 1, "one star, id 0")
    local star = Sim.objects_with(H, C.id_bhvStarSpawnCoordinates)[1]
    Sim.run_hooks(H, C.HOOK_ON_INTERACT, H.ms[0], star, C.INTERACT_STAR_OR_KEY, true)
    w.starFlags[C.COURSE_CCM] = (w.starFlags[C.COURSE_CCM] or 0) | (1 << ((raw(star).oBehParams >> 24) & 0xFF))
    raw(star).activeFlags = C.ACTIVE_FLAG_DEACTIVATED
    w:step(3)
    check(state(H) == MS.DONE, "mission DONE")
    -- star exit: CCM 0xF0 -> hub 0x24, outside the Marston door
    local lv2, a2, n2 = follow_node(CCM_SCRIPT, 0xF0)
    check(lv2 == HUB and n2 == 0x24, "CCM 0xF0 -> hub 0x24")
    w:warp(H, lv2, a2, 0)
    local sp = H.levelSpawns[n2]
    check(sp ~= nil and sp.bhv == "bhvPaintingStarCollectWarp", "hub 0x24 is a star-return spawn")
    local d = HUB_DOORS[4]
    check(math.sqrt((sp.x - d.x) ^ 2 + (sp.z - d.z) ^ 2) < 400, "0x24 is right outside the Marston door")
    H.pos.x, H.pos.y, H.pos.z = sp.x, sp.y - 80, sp.z
    H.face.y = sp.yaw
    w:step(5)
    check(H.action ~= C.ACT_DISAPPEARED, "landing outside Marston does not re-enter the door")
    check(H.cam.zoomed_in_dist == 900 and H.cam.zoomed_out_height == 450 and H.cam.collisions == 0,
        "back in the hub: the player's own camera settings")
    check(env.sgl_total_stars() == 10, "10 stars")
    acts = Sim.selectable_acts(w.starFlags[C.COURSE_CCM])
    check(acts[#acts] == 2 and env.sgl_mission_get(CCM, 2).id == "marston_quiet", "next visit: act 2 = SHHH! LOST TEXTBOOKS")
    check(env.sgl_next_stage().key == "marston", "the hint stays on Marston (act 2)")
    -- death / Exit course: CCM 0xF1 -> hub 0x34, the same spot
    local lv3, _, n3 = follow_node(CCM_SCRIPT, 0xF1)
    check(lv3 == HUB and n3 == 0x34 and H.levelSpawns[0x34].bhv == "bhvPaintingDeathWarp"
        and H.levelSpawns[0x34].x == sp.x and H.levelSpawns[0x34].z == sp.z, "CCM 0xF1 -> hub 0x34 (same spot)")
    -- /campus marston 2 from the host: straight into act 2 (the door lock and act select skipped, as for the other stages)
    Sim.cmd(H, "campus", "marston 2")
    w:step(3)
    check(H.level == CCM and H.act == 2, "/campus marston 2 -> Marston act 2")
    check(#Sim.objects_with(H, env.id_bhvSglMarstonSolid) == 0, "act 2: no stair barriers")
end)

test("door 5: Library West (11 stars) -> Library West After Dark act 1 -> star -> back outside the Library West door", function()
    if BBH_SCRIPT == nil then
        print("  (levels/bbh not built: skipped)")
        return
    end
    -- the engine names the Library West missions use (a Boo's touch, the act 3 lantern's ray, the optional lantern light)
    -- and levels.lua's interior camera: stubbed per client as in test_libwest_missions.lua's prep, which tests the acts
    local function libwest_stubs(c)
        c.stubs.hurt_and_set_mario_action = function(m, action) raw(m).action = action return 1 end
        c.stubs.collision_find_surface_on_ray = function(x, y, z, dx, dy, dz)
            return { surface = nil, hitPos = { x = x + dx, y = y + dy, z = z + dz } }
        end
        c.stubs.obj_init_animation = function(o, i) raw(o)._anim = i end
        c.stubs.gObjectAnimations = { toad_seg6_anims_0600FB58 = "ANIM:toad", bookend_seg5_anims_05002540 = "ANIM:bookend",
            swoop_seg6_anims_060070D0 = "ANIM:swoop", sushi_seg5_anims_0500AE54 = "ANIM:sushi" }
        c.cam = { zoomed_in_dist = 900, zoomed_out_dist = 1400, zoomed_in_height = 300, zoomed_out_height = 450, collisions = 0 }
        for f in pairs(c.cam) do
            c.stubs["camera_romhack_get_" .. f] = function() return c.cam[f] end
            c.stubs["camera_romhack_set_" .. f] = function(v) assert(math.type(v) == "integer"); c.cam[f] = v end
        end
        for i = 0, C.MAX_PLAYERS - 1 do raw(c.ms[i]).marioBodyState = { modelState = 0 } end
        local m = raw(c.ms[0])
        m.invincTimer, m.hurtCounter, m.flags = 0, 0, 0
    end
    -- 10 stars, alone (acts 1-2 + the 100-coin star of courses 1-3, Marston act 1): built but LOCKED
    local SOLO = 0x43
    local w = full_world({ starFlags = { [C.COURSE_BOB] = SOLO, [C.COURSE_WF] = SOLO, [C.COURSE_JRB] = SOLO,
        [C.COURSE_CCM] = 0x01 } })
    local H = w:connect("Host")
    H.strStorage.friend = "josh"
    libwest_stubs(H)
    local signs = {}
    H.stubs.smlua_text_utils_dialog_replace = function(id, _, _, _, _, text) signs[id] = text end
    w:step(3)
    w:warp(H, HUB, 1, 0)
    w:seconds(2)
    local env = H.env
    local function sign_says(building, line)
        for _, t in pairs(signs) do
            if t:find(building, 1, true) == 1 and t:find(line, 1, true) ~= nil then return true end
        end
        return false
    end
    check(sign_says("LIBRARY WEST", "Opens at 11 stars.") and sign_says("LIBRARY WEST", "Walk into the door"),
        "Library West's signpost: opens at 11 stars, walk in (built)")
    check(sign_says("CENTURY TOWER", "Opens at 14 stars.") and sign_says("CENTURY TOWER", "Coming soon!"),
        "Century Tower's signpost: opens at 14 stars, coming soon (the star curve 0 / 2 / 5 / 8 / 11 / 14)")
    check(env.sgl_stage_ready(env.sgl_stage_by_door(5)), "levels/bbh is ours: course 5 is built")
    check(env.sgl_total_stars() == 10, "10 stars")
    check(env.sgl_next_stage() ~= env.sgl_stage_by_door(5), "Library West locked: the NEXT stage is not Library West")
    at_door(H, 5, 600)
    w:step(2)
    check(Sim.hud_has(H, "LIBRARY WEST AFTER DARK") and Sim.hud_has(H, "LOCKED %- 11 stars %(you have 10%)"), "door 5 label: LOCKED")
    at_door(H, 5, 50)
    w:step(3)
    check(Sim.find(H.popups, "Locked!.-LIBRARY WEST AFTER DARK needs 11 stars %(you have 10%)") ~= nil, "locked popup")
    check(H.action ~= C.ACT_DISAPPEARED and H.level == HUB, "a locked door does not open")

    -- 12 stars, alone (acts 1-2 + the 100-coin star of courses 1-4: what a solo player can earn): open, the hint skips
    -- the four co-op act 3s and points at the Library West door
    w = full_world({ starFlags = { [C.COURSE_BOB] = SOLO, [C.COURSE_WF] = SOLO, [C.COURSE_JRB] = SOLO, [C.COURSE_CCM] = SOLO } })
    H = w:connect("Host")
    H.strStorage.friend = "josh"
    libwest_stubs(H)
    w:step(3)
    w:warp(H, HUB, 1, 0)
    w:seconds(2)
    env = H.env
    check(env.sgl_total_stars() == 12, "12 stars (solo)")
    check(Sim.find(H.popups, "Walk into the Library West door to enter LIBRARY WEST AFTER DARK!") ~= nil,
        "first hub visit: door hint names the Library West door")
    check(Sim.hud_has(H, "NEXT: LIBRARY WEST AFTER DARK") and Sim.hud_has(H, "LIBRARY WEST door"), "hub NEXT panel: Library West")
    local model5
    for _, o in ipairs(Sim.objects_with(H, env.id_bhvSglDoor)) do
        if ((raw(o).oBehParams >> 24) & 0xFF) == 5 then model5 = raw(o)._model end
    end
    check(model5 == C.E_MODEL_STAR, "door 5: gold star (open)")
    at_door(H, 5, 600)
    w:step(2)
    check(Sim.hud_has(H, "LIBRARY WEST AFTER DARK") and Sim.hud_has(H, "Walk in!"), "door 5 label: Walk in!")
    at_door(H, 5, 50)
    w:step(2)
    local m = H.ms[0]
    check(H.action == C.ACT_DISAPPEARED and raw(m).actionArg == (C.WARP_OP_WARP_OBJECT << 16) + 2, "door 5: vanilla warp-object entry")
    local used = raw(m).usedObj
    check(used ~= nil and ((raw(used).oBehParams >> 16) & 0xFF) == 0x15, "usedObj carries hub node 0x15")
    local lv, area, node = follow_node(HUB_SCRIPT, 0x15)
    check(lv == BBH and area == 1 and node == 0x0A, "hub 0x15 -> BBH 0x0A")
    local acts = Sim.selectable_acts(w.starFlags[C.COURSE_BBH] or 0)
    check(#acts == 1 and acts[1] == 1, "act select offers act 1 only")
    H.action = C.ACT_IDLE
    w:warp(H, lv, area, acts[1])
    local sp0 = H.levelSpawns[0x0A]
    check(sp0 and sp0.bhv == "bhvSpinAirborneWarp", "BBH entry spawn 0x0A (spin-in)")
    check(sp0 and sp0.yaw == 0x8000, "BBH spawn faces north (into the building, up the escalators)")
    H.pos.x, H.pos.y, H.pos.z = sp0.x, sp0.y - 100, sp0.z
    w:step(5)
    check(Sim.hud_has(H, "LIBRARY WEST AFTER DARK %- ACT 1") and Sim.hud_has(H, "ALL%-NIGHTER"), "act 1 banner")
    check(Sim.stars_of(H, 0) == 0, "no level-script star: the mission spawns act 1's")
    check(Sim.find(H.console, "sleeps") == nil, "the mission's geometry probes pass on the real spawn")
    local P = env.LIBWEST_POINTS
    check(sp0.x == P.spawn.x and sp0.z == P.spawn.z and sp0.y - 100 == P.spawn.y, "LIBWEST_POINTS.spawn = the level script's spawn")
    Sim.cmd(H, "campus", "where")
    -- the spawn in campus map metres (stages.json library_west_interior centre (38.9, 285.6): x = X/100 + 38.9, y = -Z/100 + 285.6)
    local mx, my = sp0.x / 100 + 38.9, -sp0.z / 100 + 285.6
    check(Sim.find(H.chat, string.format("campus map: %.1f m east, %.1f m north", mx, my):gsub("%-", "%%-"):gsub("%.", "%%.")) ~= nil,
        string.format("/campus where: campus map metres at the spawn (%.1f, %.1f)", mx, my))
    check(math.abs(mx - 38.9) < 0.6 and math.abs(my - 262.4) < 0.6, "BBH spawn in the vestibule (layout entrance.spawn)")
    -- the hub door the player walked through and the spawn are the same place on the campus map (the warp is a teleport)
    local d5 = HUB_DOORS[5]
    local hx, hy = d5.x / 100 - 45, -d5.z / 100 + 98
    check(math.abs(hx - mx) < 1.5 and math.abs(hy - my) < 5, string.format("spawn %.1f m from the hub's door 5 on the map",
        math.sqrt((hx - mx) ^ 2 + (hy - my) ^ 2)))
    w:seconds(3.5)
    check(state(H) == MS.ACTIVE, "mission active")
    local camBBH = env.SGL_STAGE_CAMERA[BBH]
    check(camBBH ~= nil and H.cam.zoomed_in_dist == camBBH.inDist and H.cam.zoomed_out_height == camBBH.outHeight
        and H.cam.collisions == 1, "inside Library West: the interior rom-hack camera (SGL_STAGE_CAMERA[LEVEL_BBH], collision on)")
    check(#Sim.objects_with(H, env.id_bhvSglLibwestSolid) == #P.stair_doors + #P.staff_doors,
        "act 1: the stair barriers and the 5th floor's staff-only doors stand")
    for _, p in ipairs({ P.esc_top, { x = 0, y = P.y_f4, z = -1500 }, P.f6_door_w, P.climb_goal }) do
        H.pos.x, H.pos.y, H.pos.z = p.x, p.y, p.z
        w:step(3)
    end
    check(state(H) == MS.SUCCESS, "at the 6th floor's big window: success")
    w:step(3)
    check(#H.starSpawns == 1 and Sim.stars_of(H, 0) == 1, "one star, id 0")
    local star = Sim.objects_with(H, C.id_bhvStarSpawnCoordinates)[1]
    Sim.run_hooks(H, C.HOOK_ON_INTERACT, H.ms[0], star, C.INTERACT_STAR_OR_KEY, true)
    w.starFlags[C.COURSE_BBH] = (w.starFlags[C.COURSE_BBH] or 0) | (1 << ((raw(star).oBehParams >> 24) & 0xFF))
    raw(star).activeFlags = C.ACTIVE_FLAG_DEACTIVATED
    w:step(3)
    check(state(H) == MS.DONE, "mission DONE")
    -- star exit: BBH 0xF0 -> hub 0x25, outside the Library West door
    local lv2, a2, n2 = follow_node(BBH_SCRIPT, 0xF0)
    check(lv2 == HUB and n2 == 0x25, "BBH 0xF0 -> hub 0x25")
    w:warp(H, lv2, a2, 0)
    local sp = H.levelSpawns[n2]
    check(sp ~= nil and sp.bhv == "bhvPaintingStarCollectWarp", "hub 0x25 is a star-return spawn")
    check(math.sqrt((sp.x - d5.x) ^ 2 + (sp.z - d5.z) ^ 2) < 400, "0x25 is right outside the Library West door")
    H.pos.x, H.pos.y, H.pos.z = sp.x, sp.y - 80, sp.z
    H.face.y = sp.yaw
    w:step(5)
    check(H.action ~= C.ACT_DISAPPEARED, "landing outside Library West does not re-enter the door")
    check(H.cam.zoomed_in_dist == 900 and H.cam.zoomed_out_height == 450 and H.cam.collisions == 0,
        "back in the hub: the player's own camera settings")
    check(env.sgl_total_stars() == 13, "13 stars")
    acts = Sim.selectable_acts(w.starFlags[C.COURSE_BBH])
    check(acts[#acts] == 2 and env.sgl_mission_get(BBH, 2).id == "libwest_coffee", "next visit: act 2 = COFFEE RUN")
    check(env.sgl_next_stage().key == "libwest", "the hint stays on Library West (act 2)")
    -- death / Exit course: BBH 0xF1 -> hub 0x35, the same spot
    local lv3, _, n3 = follow_node(BBH_SCRIPT, 0xF1)
    check(lv3 == HUB and n3 == 0x35 and H.levelSpawns[0x35].bhv == "bhvPaintingDeathWarp"
        and H.levelSpawns[0x35].x == sp.x and H.levelSpawns[0x35].z == sp.z, "BBH 0xF1 -> hub 0x35 (same spot)")
    -- /campus libwest 2 from the host: straight into act 2 (the door lock and act select skipped, as for the other stages)
    Sim.cmd(H, "campus", "libwest 2")
    w:step(3)
    check(H.level == BBH and H.act == 2, "/campus libwest 2 -> Library West act 2")
    w:step(3)
    check(#Sim.objects_with(H, env.id_bhvSglLibwestSolid) == #P.staff_doors, "act 2: only the staff-only doors, no stair barriers")
    -- the level's Goombas: none in act 3's hide-and-seek arena in act 3 (OBJECT_WITH_ACTS), all four in acts 1 and 2
    local function goombas(act)
        local n = 0
        for _, o in ipairs(BBH_SCRIPT.objects) do
            if o.bhv == "bhvGoomba" and (o.acts & (1 << (act - 1))) ~= 0 then n = n + 1 end
        end
        return n
    end
    check(goombas(1) == 4 and goombas(2) == 4 and goombas(3) == 1, string.format(
        "Goombas: 4 in acts 1-2, only the one outside the hide-and-seek arena in act 3 (%d / %d / %d)", goombas(1), goombas(2), goombas(3)))
end)

test("coming soon acts: free roam notice, no mission, no star, no invite; exit works", function()
    local w = full_world({ starFlags = { [C.COURSE_BOB] = 0x07 } })
    local H, F = w:connect("Host"), w:connect("Friend")
    w:step(3)
    arrive_and_pick(w, H, 1)
    arrive_and_pick(w, F, 2)
    local acts = Sim.selectable_acts(0x07)
    check(acts[#acts] == 4, "acts 1-3 starred: act 4 is offered")
    local popups = #F.popups
    w:warp(H, BOB, 1, 4)
    w:step(5)
    check(Sim.hud_has(H, "COMING SOON %- MASCOT"), "banner names the act")
    check(Sim.hud_has(H, "EXIT COURSE"), "notice says how to leave")
    check(H.env.sgl_mission_ctx() == nil and #Sim.objects_with(H, H.env.id_bhvSglMission) == 0, "no mission controller")
    check(Sim.stars_of(H, 3) == 0 and #H.starSpawns == 0, "no star")
    w:step(3)
    local invites = 0
    for k = popups + 1, #F.popups do if F.popups[k]:find("started") then invites = invites + 1 end end
    check(invites == 0, "no Study Group invite for a coming-soon act")
    -- Pause > EXIT COURSE is the engine's (BOB 0xF1); /campus hub works as well
    Sim.cmd(H, "campus", "hub me")
    w:step(3)
    check(H.level == HUB and not Sim.hud_has(H, "COMING SOON"), "back in the hub, notice gone")
end)

test("with a friend: invite, D-pad Up joins the act, co-op act 3 with every file loaded", function()
    local w = full_world()
    local H, F = w:connect("Host"), w:connect("Friend")
    w:step(3)
    arrive_and_pick(w, H, 3)
    arrive_and_pick(w, F, 7)
    check(H.env.gPlayerSyncTable[0].friend == 3 and F.env.gPlayerSyncTable[0].friend == 7, "each picked a friend")
    -- Host walks into the Auditorium: the friend in the hub gets an invite
    at_door(H, 1, 50)
    w:step(2)
    check(H.action == C.ACT_DISAPPEARED, "host enters the door")
    H.action = C.ACT_IDLE
    w:warp(H, BOB, 1, 1)
    w:step(5)
    check(Sim.find(F.popups, "Host.-started THE SWAMP act 1") ~= nil, "friend got the Study Group invite")
    check(Sim.hud_has(F, "D%-pad Up: join Host"), "join prompt")
    F.pressed = C.U_JPAD
    w:step(3)
    check(F.level == BOB and F.act == 1, "D-pad Up: the friend is in the host's act (no act select needed)")
    w:step(5)
    local ctx = H.env.sgl_mission_ctx()
    check(ctx ~= nil and ctx.n == 2 and ctx.isLeader, "same instance, host leads")
    -- the character select menu eats the pad while open: no accidental join / movement
    Sim.cmd(H, "campus", "hub")                                  -- everyone back to the Plaza
    w:step(5)
    check(H.level == HUB and F.level == HUB, "/campus hub brings everyone back")
    Sim.cmd(F, "char", "")
    w:step(1)
    check(menu_open(F), "/char opens the menu")
    w:warp(H, BOB, 1, 1)
    w:step(5)
    check(not Sim.hud_has(F, "D%-pad Up: join"), "invite prompt hidden under the menu")
    F.pressed = C.U_JPAD
    w:step(2)
    check(F.level == HUB, "D-pad Up moves the menu cursor, not a join")
    F.pressed = C.B_BUTTON
    w:step(2)
    check(not menu_open(F), "B closes the menu")
    check(F.env.gPlayerSyncTable[0].friend == 7, "closing keeps the pick")
    -- co-op act 3 straight from /campus (act select would need acts 1-2 first)
    Sim.cmd(H, "campus", "swamp 3")
    w:step(5)
    check(H.level == BOB and H.act == 3 and F.level == BOB and F.act == 3, "both in act 3")
    w:seconds(4)
    check(state(H) == MS.ACTIVE and H.env.sgl_mission_ctx().a == 2, "chorus active, 2 buttons lit")
    local P = H.env.SWAMP_POINTS
    local function on(c, p) c.pos.x, c.pos.y, c.pos.z = p.x, p.y + 60, p.z end
    for _, pair in ipairs({ { P.button_nw, P.button_se }, { P.button_ne, P.button_sw }, { P.button_nw, P.button_se } }) do
        on(H, pair[1]); on(F, pair[2])
        w:seconds(2.2)                                           -- GA... TOR... CHOMP!
        H.action, F.action = C.ACT_GROUND_POUND_LAND, C.ACT_GROUND_POUND_LAND
        w:step(5)
        H.action, F.action = C.ACT_IDLE, C.ACT_IDLE
        w:step(3)
    end
    check(state(H) == MS.SUCCESS and state(F) == MS.SUCCESS, "three phrases pounded together: success")
    w:step(3)
    check(Sim.stars_of(H, 2) == 1 and Sim.stars_of(F, 2) == 1, "one star (id 2) for each")
    -- the friend grabs it and leaves ("Leave level"); the host follows with D-pad Up
    local star = Sim.objects_with(F, C.id_bhvStarSpawnCoordinates)[1]
    Sim.run_hooks(F, C.HOOK_ON_INTERACT, F.ms[0], star, C.INTERACT_STAR_OR_KEY, true)
    w:step(3)
    check(Sim.hud_has(H, "Friend got the star!"), "host: leave-together prompt")
    H.pressed = C.U_JPAD
    w:step(2)
    check(H.level == HUB and H.arrivalNode == 0x31 and H.warpOps[1] == C.WARP_OP_EXIT,
        "D-pad Up: the pause menu's exit, BOB 0xF1 -> outside the Auditorium (hub 0x31)")
    -- only the host moves everyone: the friend's /campus moves the friend
    w:warp(F, HUB, 1, 0)
    w:step(3)
    Sim.cmd(F, "campus", "swamp 2")
    w:step(3)
    check(F.level == BOB and F.act == 2 and H.level == HUB, "a friend's /campus swamp 2 moves only the friend")
    check(Sim.find(F.chat, "Only the host moves everyone") ~= nil, "and says so")
end)

test("character select: remembered pick, overlay hides the other HUDs", function()
    local w = full_world()
    local H = w:connect("Host")
    H.strStorage.friend = "josh"                                 -- a pick saved by an earlier session
    w:step(3)
    w:warp(H, HUB, 1, 0)
    w:step(30)
    check(not menu_open(H), "no auto-open when a pick is saved")
    check(H.env.gPlayerSyncTable[0].friend == 5, "saved pick re-applied (Josh)")
    check(Sim.find(H.popups, "Playing as .-Josh") ~= nil, "popup names the friend")
    w:seconds(1)
    check(Sim.hud_has(H, "NEXT: THE SWAMP"), "no menu to wait for: the NEXT panel shows after 1.5 s")
    at_door(H, 1, 600)
    w:step(2)
    check(Sim.hud_has(H, "Walk in!"), "door label visible")
    H.pressed = C.L_TRIG | C.START_BUTTON                        -- L + START
    w:step(2)
    check(menu_open(H), "L + START opens the menu")
    check(not Sim.hud_has(H, "Walk in!") and not Sim.hud_has(H, "NEXT: THE SWAMP"), "door label and NEXT panel hidden under it")
    check(not Sim.hud_has(H, "Super Gatorlator 64 loaded"), "no debug-looking 'loaded' banner any more")
    check(Sim.hud_has(H, "A / click: choose") and Sim.hud_has(H, "JOSH"), "menu drawn (footer, cursor on Josh)")
    H.pressed = C.START_BUTTON
    w:step(2)
    check(not menu_open(H) and Sim.hud_has(H, "Walk in!") and Sim.hud_has(H, "NEXT: THE SWAMP"), "START closes it, labels back")
    -- a mission HUD is hidden too
    w:warp(H, BOB, 1, 2)
    w:seconds(4)
    check(Sim.hud_has(H, "STADIUM STAIR SPRINT"), "race panel")
    Sim.cmd(H, "char", "")
    w:step(2)
    check(not Sim.hud_has(H, "STADIUM STAIR SPRINT"), "mission panel hidden under the menu")
end)

print(string.format("\n%d checks passed, %d failed", passed, failed))
os.exit(failed == 0 and 0 or 1)
