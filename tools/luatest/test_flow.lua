-- Integration tests: the WHOLE mod (every mods/sgl64/*.lua, in coopdx's load order) plus the REAL
-- generated level scripts (levels/castle_grounds, levels/bob) in the offline coopdx simulation.
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

local HUB, BOB = C.LEVEL_CASTLE_GROUNDS, C.LEVEL_BOB
local MS = { IDLE = 0, WAITING = 1, INTRO = 2, ACTIVE = 3, SUCCESS = 4, FAILED = 5, DONE = 6 }
local HUB_SCRIPT = assert(Sim.level_script("castle_grounds"), "levels/castle_grounds/script.c")
local BOB_SCRIPT = assert(Sim.level_script("bob"), "levels/bob/script.c")
-- the contract table of docs/flow.md section 2 (door -> slot, level, stars to open)
local CONTRACT = {
    { door = 1, slot = "bob", level = "LEVEL_BOB", stars = 0 },
    { door = 2, slot = "wf", level = "LEVEL_WF", stars = 2 },
    { door = 3, slot = "jrb", level = "LEVEL_JRB", stars = 8 },
    { door = 4, slot = "ccm", level = "LEVEL_CCM", stars = 5 },
    { door = 5, slot = "bbh", level = "LEVEL_BBH", stars = 14 },
    { door = 6, slot = "ttc", level = "LEVEL_TTC", stars = 20 },
}

local function full_world(opts)
    opts = opts or {}
    opts.files = Sim.ALL_FILES
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

    -- doors: 6 objects from the hub script; only The Swamp is built
    local doors = Sim.objects_with(H, env.id_bhvSglDoor)
    check(#doors == 6, "six hub doors")
    local models = {}
    for _, o in ipairs(doors) do models[(raw(o).oBehParams >> 24) & 0xFF] = raw(o)._model end
    check(models[1] == C.E_MODEL_STAR, "Auditorium door: gold star (open)")
    check(models[5] == C.E_MODEL_TRANSPARENT_STAR and models[2] == C.E_MODEL_TRANSPARENT_STAR, "unbuilt stages: see-through star")
    local flames = Sim.objects_with(H, env.id_bhvSglDoorFx)
    local shown = 0
    for _, f in ipairs(flames) do
        if (raw(f).header.gfx.node.flags & C.GRAPH_RENDER_INVISIBLE) == 0 then shown = shown + 1 end
    end
    check(#flames == 12 and shown == 10, "two flames per door, hidden only at the open door (" .. shown .. " shown)")

    -- Library West: coming soon
    at_door(H, 5, 50)
    w:step(3)
    check(Sim.find(H.popups, "LIBRARY WEST AFTER DARK.-coming soon %(opens at 14 stars%)") ~= nil, "Library West: coming soon popup")
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
