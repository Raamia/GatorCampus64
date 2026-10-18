-- Unit + scenario tests for mods/sgl64/{sgl_hud,sgl_mission,swamp_missions}.lua.
-- Run: tools/luatest/run.sh   (or: lua tools/luatest/test_missions.lua)
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

local LEVEL_BOB, HUB = C.LEVEL_BOB, C.LEVEL_CASTLE_GROUNDS
local MS = { IDLE = 0, WAITING = 1, INTRO = 2, ACTIVE = 3, SUCCESS = 4, FAILED = 5, DONE = 6 }

local function at(c, p, dy)
    c.pos.x, c.pos.y, c.pos.z = p.x, p.y + (dy or 0), p.z
end

-- connect n players named A, B, ... (gi 0, 1, ...) and let them sync in the hub
local function world_with(names, opts)
    local w = Sim.new(opts)
    local cs = {}
    for _, n in ipairs(names) do table.insert(cs, w:connect(n)) end
    w:step(3)
    return w, table.unpack(cs)
end

local function enter(w, c, act)
    w:warp(c, LEVEL_BOB, 1, act)
end

local function state(c)
    local ctx = Sim.ctx(c)
    return ctx and ctx.s or nil
end

---------------------------------------------------------------------------------------------
-- pure helpers
---------------------------------------------------------------------------------------------
test("leader election: smallest synced globalIndex, host may be absent", function()
    local w, A = world_with({ "A" })
    local elect = A.env.sgl_elect_leader
    local li, gi = elect({ { li = 0, gi = 3, synced = true }, { li = 1, gi = 1, synced = true }, { li = 2, gi = 2, synced = true } })
    check(li == 1 and gi == 1, "picks gi 1")
    li, gi = elect({ { li = 0, gi = 3, synced = true }, { li = 1, gi = 1, synced = false }, { li = 2, gi = 2, synced = true } })
    check(li == 2 and gi == 2, "skips players still loading the area")
    li = elect({ { li = 0, gi = 5, synced = false } })
    check(li == nil, "nobody synced: no leader")
    li, gi = elect({ { li = 4, gi = 0, synced = true }, { li = 0, gi = 7, synced = true } })
    check(li == 4 and gi == 0, "host leads when present")
end)

test("hud helpers: times, fades", function()
    local w, A = world_with({ "A" })
    local f = A.env.sgl_hud_format_time
    check(f(0) == "0'00\"00", "zero")
    check(f(30 * 65 + 10) == "1'05\"33", "1'05\"33 got " .. f(30 * 65 + 10))
    check(f(30 * 70) == "1'10\"00", "par 70 s")
    check(A.env.sgl_hud_format_seconds(125) == "2'05", "seconds")
    local fade = A.env.sgl_hud_fade
    check(fade(0, 100) == 0 and fade(50, 100) == 1 and fade(100, 100) == 0 and fade(-1, 100) == 0, "fade edges")
end)

test("registry: three Swamp missions on acts 1/2/3 with star ids act-1, acts 4-6 coming soon", function()
    local w, A = world_with({ "A" })
    local env = A.env
    local d1, d2, d3 = env.sgl_mission_get(LEVEL_BOB, 1), env.sgl_mission_get(LEVEL_BOB, 2), env.sgl_mission_get(LEVEL_BOB, 3)
    check(d1 and d1.id == "swamp_skybox" and d1.starId == 0 and d1.levelStar, "act 1 skybox, star 0, level-script star")
    check(d2 and d2.id == "swamp_sprint" and d2.starId == 1 and d2.minPlayers == 1, "act 2 sprint, star 1, solo")
    check(d3 and d3.id == "swamp_chorus" and d3.starId == 2 and d3.minPlayers == 2, "act 3 chorus, star 2, 2+ players")
    for _, d in ipairs({ d1, d2, d3 }) do
        check((d.bparams >> 24) == d.starId, d.id .. " bparams carry the star id")
        check(d.star.y > -1000 and d.probes and #d.probes >= 1, d.id .. " star + probes")
    end
    -- the course.lua act names match the mission titles (act select = banner)
    local stage = env.sgl_stage_by_level(LEVEL_BOB)
    for _, d in ipairs({ d1, d2, d3 }) do
        check(stage.acts[d.act] == d.title, d.id .. " title matches course.lua act " .. d.act)
        check(not env.sgl_act_is_soon(stage, d.act), d.id .. " act is not 'coming soon'")
    end
    for act = 4, 6 do
        check(env.sgl_mission_get(LEVEL_BOB, act) == nil, "act " .. act .. " has no mission yet")
        check(env.sgl_act_is_soon(stage, act) and stage.acts[act]:find("^COMING SOON") ~= nil,
            "act " .. act .. " is named COMING SOON: " .. tostring(stage.acts[act]))
    end
    -- act names use the act-select menu font only (A-Z 0-9 space ' . , - & ! ?)
    for act = 1, 6 do
        check(not stage.acts[act]:find("[^A-Z0-9 '%.,%-&!%?]") and #stage.acts[act] <= 28,
            "act " .. act .. " name fits the menu font: " .. stage.acts[act])
    end
end)

---------------------------------------------------------------------------------------------
-- co-op buttons (act 3, POUND mode: 3 phrases of GA... TOR... CHOMP!)
---------------------------------------------------------------------------------------------
local function lit(c)
    local ctx = Sim.ctx(c)
    return ctx.def.currentMask(ctx)
end

-- everyone in `who` = { { client, point }, ... } onto their button, the count-in, then a ground pound in
-- the CHOMP! window
local function chorus_phrase(w, who)
    for _, cp in ipairs(who) do at(cp[1], cp[2], 60) end
    w:seconds(2.2)
    for _, cp in ipairs(who) do cp[1].action = C.ACT_GROUND_POUND_LAND end
    w:step(5)
    for _, cp in ipairs(who) do cp[1].action = C.ACT_IDLE end
    w:step(3)
end

-- two players win the chorus: NW + SE, NE + SW, NW + SE
local function chorus_win(w, A, B, P)
    chorus_phrase(w, { { A, P.button_nw }, { B, P.button_se } })
    chorus_phrase(w, { { A, P.button_ne }, { B, P.button_sw } })
    chorus_phrase(w, { { A, P.button_nw }, { B, P.button_se } })
end

test("act 3: host absent, two players, leader = smallest gi; 3 phrases of GA TOR CHOMP; star once each", function()
    local w, H, A, B = world_with({ "Host", "A", "B" })
    local P = A.env.SWAMP_POINTS
    enter(w, A, 3)
    w:step(5)
    check(state(A) == MS.WAITING, "alone: waiting for a study buddy")
    check(Sim.find(H.popups, "started THE SWAMP act 3") ~= nil, "hub host got the Study Group invite")
    check(Sim.hud_has(A, "a study buddy makes it the co%-op chorus"), "HUD prompt: solo game now, co-op with a study buddy")
    check(Sim.hud_has(A, "Join my study group"), "the prompt names the mod menu button (keyboard players)")
    enter(w, B, 3)
    w:step(5)
    local ctx = Sim.ctx(A)
    check(ctx.n == 2 and ctx.isLeader and not Sim.ctx(B).isLeader, "A (gi 1) leads, not the absent host")
    check(state(A) == MS.INTRO, "2 players: intro")
    w:seconds(3.2)
    check(state(A) == MS.ACTIVE and state(B) == MS.ACTIVE, "active after the intro")
    check(ctx.a == 2 and lit(A) == 5, "two buttons lit for two players: NW + SE")
    check(#Sim.objects_with(A, A.env.id_bhvSglButton) == 8, "four corner buttons (+ the 4 solo pads) spawned locally")
    at(A, P.button_nw, 60)
    at(B, P.button_sw, 60)        -- wrong corner: SW is not lit in phrase 1
    w:seconds(1.5)
    check(ctx.f == 1 and ctx.c == 0, "only NW held: no count-in")
    at(B, P.button_se, 60)
    w:seconds(1.2)
    check(ctx.f == 5 and ctx.c == 2, "NW + SE held: GA..., TOR...")
    check(Sim.hud_has(A, "TOR"), "chant on the HUD")
    w:seconds(1.0)
    check(ctx.c == 3 and Sim.hud_has(B, "CHOMP!") and Sim.hud_has(B, "POUND IT"), "CHOMP!: pound now (B's HUD too)")
    A.action = C.ACT_GROUND_POUND
    w:step(3)
    check(ctx.p == 1 and ctx.x == 0, "A's pound counted, B's still missing")
    B.action = C.ACT_GROUND_POUND_LAND
    w:step(3)
    A.action, B.action = C.ACT_IDLE, C.ACT_IDLE
    w:step(2)
    check(ctx.x == 1 and ctx.c == 0 and ctx.p == 0, "phrase 1 done")
    check(Sim.hud_has(A, "Phrase 1/3") or Sim.hud_has(A, "Phrase 2/3"), "phrase toast / panel")
    check(lit(A) == 10 and lit(B) == 10, "phrase 2 lights the other corners: NE + SW")
    check(state(A) == MS.ACTIVE, "still active")
    chorus_phrase(w, { { A, P.button_ne }, { B, P.button_sw } })
    check(ctx.x == 2 and lit(A) == 5, "phrase 2 done, back to NW + SE")
    chorus_phrase(w, { { A, P.button_nw }, { B, P.button_se } })
    check(state(A) == MS.SUCCESS and state(B) == MS.SUCCESS, "3 phrases: success")
    w:step(3)
    check(Sim.stars_of(A, 2) == 1 and Sim.stars_of(B, 2) == 1, "exactly one star (id 2) on each client")
    local sp = A.starSpawns[1]
    check(sp ~= nil and sp.y == P.field_center.y + 150 and sp.from.y == P.scoreboard_top.y, "star drops from the scoreboard to midfield")
    check(Sim.stars_of(H, 2) == 0, "no star in the hub")
    local own = A.starSpawns[1].star or B.starSpawns[1].star
    check(own ~= nil and raw(own).oStarSpawnExtCutsceneFlags == 1, "players on the corners get the star cutscene (58 m < 80 m)")
    check(Sim.hud_has(A, "STAR!"), "STAR! on the HUD")
end)

-- act 3 ALONE: the solo rhythm game (swamp_chomp.lua) on the 4 end-zone pads, same star
local function until_(w, f, max)
    for _ = 1, max do
        if f() then return true end
        w:step(1)
    end
    return f()
end

local function solo_pound(w, c, pad)
    at(c, pad, 0)
    c.action = C.ACT_GROUND_POUND_LAND
    w:step(2)
    c.action = C.ACT_IDLE
    w:step(2)
end

test("act 3 solo: alone, the rhythm game plays to GATOR GREAT! and the star; B plays again; 2 players = co-op", function()
    local w, H, A = world_with({ "Host", "A" })
    enter(w, A, 3)
    w:step(5)
    local ctx = Sim.ctx(A)
    local CH = A.env.SGL_CHOMP
    local pads = ctx.def.chompPads
    check(state(A) == MS.WAITING and ctx.def.minPlayers == 2, "the co-op chorus still waits for 2 players")
    local S = ctx.loc.solo
    check(S ~= nil and S.ph == 1 and Sim.hud_has(A, "Watch the pads"), "solo intro line")
    check(#Sim.objects_with(A, A.env.id_bhvSglButton) == 8, "4 corner buttons + 4 solo pads")
    local P = A.env.SWAMP_POINTS
    for _, p in ipairs(pads) do
        local dx, dz = p.x - P.button_nw.x, p.z - P.button_nw.z
        check(dx * dx + dz * dz > 1500 * 1500 and p.y == P.button_nw.y, "pad on the field, clear of the corners")
    end
    -- a wrong pad in the practice phrase: WRONG PAD, the same phrase again, no FAILED state
    check(until_(w, function() return ctx.loc.solo.ph == 4 end, 400), "practice: playback, countdown, your turn")
    S = ctx.loc.solo
    local want = CH.phrases[1][1]
    solo_pound(w, A, pads[want % 4 + 1])
    check(S.msg == "WRONG PAD" and S.misses == 1 and S.k == 1 and Sim.hud_has(A, "WRONG PAD"), "wrong pad told, retry")
    check(state(A) == MS.WAITING, "no FAILED state")
    -- a pound during the countdown is TOO EARLY
    check(until_(w, function() return S.ph == 3 end, 200), "countdown again")
    solo_pound(w, A, pads[want])
    check(S.msg == "TOO EARLY" and S.misses == 2, "too early")
    for k = 1, #CH.phrases do
        check(until_(w, function() return S.ph == 4 end, 400), "phrase " .. k .. ": your turn")
        check(S.k == k, "phrase " .. k)
        for _, p in ipairs(CH.phrases[k]) do solo_pound(w, A, pads[p]) end
        check(S.msg == "NICE!", "phrase " .. k .. " NICE!")
    end
    check(until_(w, function() return S.ph == 6 end, 100), "GATOR GREAT!")
    w:step(3)
    check(Sim.hud_has(A, "GATOR GREAT!") and Sim.hud_has(A, "Grade B"), "grade by misses (2 = B)")
    check(state(A) == MS.SUCCESS, "the act's mission succeeds")
    w:step(5)
    check(Sim.stars_of(A, 2) == 1, "exactly one star (id 2)")
    A.pressed = A.env.B_BUTTON
    w:step(2)
    check(ctx.loc.solo ~= S and ctx.loc.solo.won and ctx.loc.solo.ph == 1, "B: play again")
    w:seconds(2)
    check(Sim.stars_of(A, 2) == 1 and state(A) == MS.SUCCESS, "no second star")
    -- with a study buddy the co-op chorus runs (and the solo game stops)
    local w2, H2, X, Y = world_with({ "Host", "X", "Y" })
    enter(w2, X, 3); w2:step(5)
    check(Sim.ctx(X).loc.solo ~= nil, "X alone: solo")
    enter(w2, Y, 3); w2:step(5)
    check(state(X) == MS.INTRO and Sim.ctx(X).loc.solo == nil, "2 players: co-op intro, solo off")
    w2:seconds(3.2)
    check(state(X) == MS.ACTIVE and Sim.ctx(X).a == 2, "co-op chorus: 2 corners lit")
end)

test("act 3: off the beat - no pound in the CHOMP! window, or a player leaves a button: the phrase starts over", function()
    local w, H, A, B = world_with({ "Host", "A", "B" })
    local P = A.env.SWAMP_POINTS
    enter(w, A, 3); enter(w, B, 3)
    w:seconds(4)
    local ctx = Sim.ctx(A)
    at(A, P.button_nw, 60); at(B, P.button_se, 60)
    w:seconds(2.2)
    check(ctx.c == 3, "in the CHOMP! window")
    A.action = C.ACT_GROUND_POUND_LAND
    w:step(3)
    A.action = C.ACT_IDLE
    w:seconds(1.5)                 -- B never pounds
    check(ctx.p == 0 and ctx.x == 0 and ctx.c == 1, "window over: phrase 1 again (both still on: counting in anew)")
    check(Sim.hud_has(A, "Off the beat") and Sim.hud_has(B, "Off the beat"), "both told")
    -- an early pound does not carry over: the count starts again (both still on their buttons)
    w:seconds(1.2)
    check(ctx.c == 2, "counting in again")
    at(B, P.field_center, 0)      -- B leaves the button during TOR
    w:step(3)
    check(ctx.c == 0 and ctx.x == 0, "someone left a button: back to waiting")
    check(state(A) == MS.ACTIVE, "no FAILED state: just try again")
end)

test("act 3: one player cannot hold two buttons; 3 and 4 players light 3 and 4", function()
    local w, H, A, B, Cc, D = world_with({ "Host", "A", "B", "C", "D" })
    local P = A.env.SWAMP_POINTS
    for _, c in ipairs({ A, B, Cc }) do enter(w, c, 3) end
    w:seconds(4)
    check(Sim.ctx(A).a == 3 and lit(A) == 7, "3 players: 3 buttons (NW, NE, SE)")
    enter(w, D, 3)
    w:seconds(1)
    check(Sim.ctx(A).a == 4 and lit(A) == 15, "4 players: 4 buttons")
    -- a single player standing between two buttons holds neither
    at(A, { x = (P.button_nw.x + P.button_ne.x) / 2, y = -1000, z = P.button_nw.z })
    w:step(10)
    check(Sim.ctx(A).f == 0, "no button held from the middle")
end)

test("act 3: leader leaves during the count-in, next player takes over and finishes", function()
    local w, H, A, B, Cc = world_with({ "Host", "A", "B", "C" })
    local P = A.env.SWAMP_POINTS
    for _, c in ipairs({ A, B, Cc }) do enter(w, c, 3) end
    w:seconds(4)
    check(state(B) == MS.ACTIVE and Sim.ctx(B).a == 3, "3 lit")
    at(A, P.button_nw, 60); at(B, P.button_ne, 60); at(Cc, P.button_se, 60)
    w:seconds(1.4)
    check(Sim.ctx(B).c == 2, "counting in (TOR)")
    w:disconnect(A)
    w:step(3)
    check(Sim.ctx(B).isLeader, "B (gi 2) is the new leader")
    w:step(2)
    check(Sim.ctx(B).a == 2 and lit(B) == 5, "2 players left: NW + SE")
    check(state(B) == MS.ACTIVE, "still active")
    chorus_win(w, B, Cc, P)
    check(state(B) == MS.SUCCESS and state(Cc) == MS.SUCCESS, "finished under the new leader")
    w:step(2)
    check(Sim.stars_of(B, 2) == 1 and Sim.stars_of(Cc, 2) == 1, "one star each")
end)

test("act 3: a co-op mission pauses when a player leaves, the host joining takes the lead", function()
    local w, H, A, B = world_with({ "Host", "A", "B" })
    enter(w, A, 3); enter(w, B, 3)
    w:seconds(4)
    check(state(A) == MS.ACTIVE, "active")
    w:warp(B, HUB, 1, 0)
    w:step(5)
    check(state(A) == MS.WAITING, "back to waiting with 1 player")
    local r = Sim.ctx(A).r
    enter(w, H, 3)
    w:step(5)
    check(Sim.ctx(H).isLeader and not Sim.ctx(A).isLeader, "host (gi 0) leads once synced")
    check(Sim.ctx(H).r == r, "the host's arrival did not reset the round (not alone)")
    w:seconds(4)
    check(state(A) == MS.ACTIVE, "running again with the host")
end)

test("act 3 alone with nobody else online: the prompt says so and how to leave", function()
    local w, A = world_with({ "A" })
    enter(w, A, 3)
    w:step(5)
    check(state(A) == MS.WAITING, "waiting")
    check(Sim.hud_has(A, "Solo Gator Chomp") and Sim.hud_has(A, "EXIT COURSE"), "alone online: the solo game, or exit")
    check(not Sim.hud_has(A, "Friends got an invite"), "no talk of invites nobody got")
end)

test("stale state: first player back alone resets the instance", function()
    local w, A, B = world_with({ "A", "B" })
    local key = A.env.sgl_mission_sync_key(LEVEL_BOB, 1, 3, "s")
    w:set_sync_all(key, MS.SUCCESS)
    w:set_sync_all(A.env.sgl_mission_sync_key(LEVEL_BOB, 1, 3, "r"), 5)
    enter(w, A, 3)
    w:step(4)
    check(Sim.ctx(A).r == 6 and state(A) == MS.WAITING, "round 6, waiting")
    check(Sim.stars_of(A, 2) == 0, "no stale star")
    w:step(2)
    enter(w, B, 3)
    w:step(5)
    check(Sim.ctx(B).r == 6, "second player keeps the round")
end)

---------------------------------------------------------------------------------------------
-- climb (act 1)
---------------------------------------------------------------------------------------------
test("act 1: solo climb, milestones, roof -> the level script's star (no second star)", function()
    local w, A = world_with({ "A" })
    local P = A.env.SWAMP_POINTS
    enter(w, A, 1)
    check(Sim.stars_of(A, 0) == 1, "levels/bob/script.c places the act 1 star (id 0)")
    local st = Sim.objects_with(A, C.id_bhvStar)[1]
    check(st ~= nil and raw(st).oPosX == P.climb_star.x and raw(st).oPosY == P.climb_star.y and raw(st).oPosZ == P.climb_star.z,
        "SWAMP_POINTS.climb_star = the level-script star position")
    w:step(3)
    check(Sim.hud_has(A, "KICKOFF"), "act banner on arrival")
    check(Sim.find(A.console, "spawns its own") == nil and Sim.find(A.console, "has no star") == nil, "no star warning")
    w:seconds(3.5)
    local ctx = Sim.ctx(A)
    check(state(A) == MS.ACTIVE and ctx.isLeader, "solo: active, leader")
    at(A, P.climb_start)
    w:step(5)
    check(ctx.p == 20 and ctx.f == 1, "west rim: 20 m, milestone 1")
    check(Sim.hud_has(A, "West rim reached"), "milestone toast")
    at(A, P.climb_bgd)
    w:step(5)
    check(ctx.p == 44 and ctx.f == 3, "Bull Gator Deck 44 m")
    -- high but outside the tower zone does not count
    at(A, { x = 6510, y = 5560, z = 15477 })
    w:step(5)
    check(ctx.p == 44, "scoreboard height ignored (not the tower)")
    at(A, { x = P.climb_goal.x + 1000, y = P.climb_goal.y, z = P.climb_goal.z })
    w:step(3)
    check(state(A) == MS.SUCCESS, "on the roof: success")
    w:step(5)
    check(#A.starSpawns == 0 and Sim.stars_of(A, 0) == 1, "no spawned star: the level-script one is the star")
    check(Sim.hud_has(A, "STAR"), "STAR! / marker on the HUD")
    -- grab it: DONE, and nothing respawns after the static star is gone
    Sim.run_hooks(A, C.HOOK_ON_INTERACT, A.ms[0], st, C.INTERACT_STAR_OR_KEY, true)
    local outbox = A.modFs.files["pending_runs.txt"]
    check(outbox ~= nil and outbox.content:match("|swamp_skybox|%d+|0|0|0.1.0\n") ~= nil,
        "a completed solo act is saved to the local DeepSpace outbox")
    check(A.modFs.saves == 1, "the ModFS outbox is flushed to disk before networking")
    raw(st).activeFlags = C.ACTIVE_FLAG_DEACTIVATED
    w:step(5)
    check(state(A) == MS.DONE and #A.starSpawns == 0 and Sim.stars_of(A, 0) == 0, "DONE, no respawn")
end)

test("act 1 without a level-script star: the mission falls back to spawning it", function()
    local w, A = world_with({ "A" }, { levelScripts = false })
    local P = A.env.SWAMP_POINTS
    enter(w, A, 1)
    w:seconds(4)
    check(Sim.find(A.console, "has no star for act 1") ~= nil, "console warning")
    at(A, P.climb_goal)
    w:step(5)
    check(state(A) == MS.SUCCESS and #A.starSpawns == 1 and Sim.stars_of(A, 0) == 1, "one spawned star (id 0)")
end)

test("stage without the stadium floor (old placeholder): missions stay offline, no writes, no star", function()
    local w, A = world_with({ "A" }, { floor = Sim.NO_FLOOR })
    local writes = A.syncWrites
    enter(w, A, 1)
    w:seconds(5)
    local ctx = Sim.ctx(A)
    check(ctx ~= nil and ctx.dormant, "dormant")
    check(A.syncWrites == writes, "no sync writes")
    check(#A.starSpawns == 0, "no star")
    check(Sim.find(A.console, "sleeps") ~= nil, "console explains why")
    check(Sim.hud_has(A, "offline"), "HUD says offline")
    Sim.cmd(A, "mission", "force")
    w:warp(A, HUB, 1, 0); w:step(3); enter(w, A, 1); w:seconds(4)
    check(not Sim.ctx(A).dormant and state(A) == MS.ACTIVE, "/mission force runs it anyway")
end)

---------------------------------------------------------------------------------------------
-- race (act 2)
---------------------------------------------------------------------------------------------
local function run_course(w, c, P, secondsPerCp, skip)
    for i, cp in ipairs(P.sprint_checkpoints) do
        if i ~= skip then
            w:seconds(secondsPerCp)
            at(c, cp, 50)
            w:step(2)
        end
    end
end

test("act 2: solo race under par -> success, results, personal best", function()
    local w, A = world_with({ "A" })
    local P = A.env.SWAMP_POINTS
    enter(w, A, 2)
    w:seconds(4)
    local ctx = Sim.ctx(A)
    check(state(A) == MS.ACTIVE and ctx.a == 0, "lobby")
    check(Sim.hud_has(A, "START"), "start marker")
    at(A, P.sprint_start, 50)
    w:step(3)
    check(ctx.a == 1, "everyone in the box: countdown")
    A.pressed = C.A_BUTTON; A.stickMag = 64
    w:step(1)
    check(A.lastInput.buttons == 0 and A.lastInput.stickMag == 0, "inputs frozen during the countdown")
    w:seconds(3.1)
    check(ctx.a == 2 and ctx.f == 1, "racing, race 1")
    check(A.fanfares == 1, "race fanfare")
    -- skipping checkpoint 3 means the later ones do not count
    at(A, P.sprint_checkpoints[1], 50); w:step(2)
    at(A, P.sprint_checkpoints[2], 50); w:step(2)
    at(A, P.sprint_checkpoints[4], 50); w:step(2)
    check(ctx.loc.cp == 3, "checkpoint order enforced (still at 3)")
    at(A, P.sprint_checkpoints[3], 50); w:step(2)
    for i = 4, #P.sprint_checkpoints do
        w:seconds(4)
        at(A, P.sprint_checkpoints[i], 50)
        w:step(2)
    end
    check(ctx.loc.finished ~= nil and ctx.loc.finished < 70 * 30, "finished under par")
    w:step(3)
    check(state(A) == MS.SUCCESS, "success")
    w:step(2)
    check(#A.starSpawns == 1 and A.starSpawns[1].z == P.sprint_star.z, "star at the South Ramp terrace")
    check(A.storage["pb_swamp_stair_sprint"] == ctx.loc.finished, "personal best saved")
    check(Sim.hud_has(A, "STAIR SPRINT"), "results board")
    -- free races after the star: back to the lobby after the results
    w:seconds(7)
    check(ctx.a == 0 and state(A) == MS.SUCCESS, "lobby again, star kept")
end)

test("act 2: over par -> no star, FAILED, new round back in the lobby", function()
    local w, A = world_with({ "A" })
    local P = A.env.SWAMP_POINTS
    enter(w, A, 2)
    w:seconds(4)
    at(A, P.sprint_start, 50)
    w:seconds(3.3)
    local ctx = Sim.ctx(A)
    local r = ctx.r
    run_course(w, A, P, 8.5)
    check(ctx.loc.finished ~= nil and ctx.loc.finished > 70 * 30, "finished over par")
    w:step(3)
    check(state(A) == MS.ACTIVE and ctx.a == 3, "results (1 racer finished)")
    w:seconds(6.5)
    check(state(A) == MS.FAILED, "failed: nobody beat par")
    check(Sim.hud_has(A, "TRY AGAIN"), "TRY AGAIN")
    w:seconds(4.5)
    check(ctx.r == r + 1 and (state(A) == MS.INTRO or state(A) == MS.ACTIVE), "new round")
    w:seconds(3.5)
    check(state(A) == MS.ACTIVE and ctx.a == 0, "lobby again")
    check(#A.starSpawns == 0, "no star")
end)

test("act 2: two racers, results board shared, late box-joiner waits", function()
    local w, H, A, B = world_with({ "Host", "A", "B" })
    local P = A.env.SWAMP_POINTS
    enter(w, A, 2); enter(w, B, 2)
    w:seconds(4)
    at(A, P.sprint_start, 50)
    w:step(5)
    local ctx = Sim.ctx(A)
    check(ctx.a == 0 and ctx.c > 0, "one of two in the box: lobby wait countdown")
    w:seconds(10.5)
    check(ctx.a == 1, "countdown after the wait")
    at(B, P.sprint_start, 50)
    w:seconds(3.2)
    check(ctx.a == 2 and ctx.x == 2, "both race")
    run_course(w, A, P, 3)
    run_course(w, B, P, 0.3)
    w:step(5)
    local listA = ctx.loc.results and ctx.loc.results[1]
    local listB = Sim.ctx(B).loc.results and Sim.ctx(B).loc.results[1]
    check(listA and #listA == 2 and listB and #listB == 2, "both clients know both finishes")
    check(state(A) == MS.SUCCESS, "first finisher under par -> star")
    check(Sim.stars_of(A, 1) == 1 and Sim.stars_of(B, 1) == 1, "one star (id 1) each")
end)

---------------------------------------------------------------------------------------------
-- Study Group
---------------------------------------------------------------------------------------------
test("study group: invite popup, D-pad Up joins, /join <name>, no spam, zero-star join, unbuilt-stage refusal", function()
    local w, H, A, B = world_with({ "Host", "A", "B" })
    enter(w, A, 3)
    w:step(4)
    check(Sim.find(H.popups, "A.-started THE SWAMP act 3") ~= nil, "popup names the player and act")
    check(Sim.find(B.popups, "D%-pad Up or /join") ~= nil, "popup tells how to follow")
    check(#A.popups == 0, "no invite to yourself")
    check(Sim.hud_has(H, "D%-pad Up: join A"), "join prompt")
    local function invites(c)
        local n = 0
        for _, s in ipairs(c.popups) do if s:find("started") then n = n + 1 end end
        return n
    end
    local hPopups = invites(H)
    -- /join <name>; joining an instance that already has a player sends no new invite
    Sim.cmd(B, "join", "a")
    check(B.level == LEVEL_BOB and B.act == 3, "/join a follows A")
    w:step(4)
    check(invites(H) == hPopups, "B arriving where A is: no second invite")
    H.pressed = C.U_JPAD
    w:step(2)
    check(H.level == LEVEL_BOB and H.act == 3, "D-pad Up warped the host into act 3")
    w:warp(H, HUB, 1, 0); w:warp(B, HUB, 1, 0); w:step(3)
    w:warp(A, HUB, 1, 0); w:step(3)
    enter(w, A, 3); w:step(4)
    check(invites(H) == hPopups, "A re-entering within a minute: no invite spam (cooldown)")
    -- A built stage can be joined on a fresh save (with a real act 1: "coming soon" acts send no invites).
    w.built[C.LEVEL_WF] = true
    for _, c in ipairs({ H, A, B }) do c.env.sgl_stage_by_level(C.LEVEL_WF).acts = { "REITZ TEST ACT" } end
    w:warp(A, C.LEVEL_WF, 1, 1)
    w:step(4)
    check(Sim.find(B.popups, "REITZ") ~= nil, "invite for the other stage")
    check(Sim.hud_has(B, "D%-pad Up: join A"), "prompt shown")
    w:seconds(10.5)
    check(not Sim.hud_has(B, "D%-pad Up: join A"), "prompt gone after 10 s")
    Sim.cmd(B, "join", "")
    check(w.stars == 0, "save still has zero stars")
    check(B.level == C.LEVEL_WF and B.act == 1, "joins a built stage with zero stars")
    check(Sim.find(B.chat, "locked: it needs") == nil, "join has no star-lock message")
    w:warp(B, HUB, 1, 0)
    w.built[C.LEVEL_WF] = false
    w:step(3)
    Sim.cmd(B, "join", "")
    check(B.level == HUB, "unbuilt stage refused")
    check(Sim.find(B.chat, "REITZ & ENGINEERING is not built yet") ~= nil, "unbuilt-stage message")
    -- an unknown name
    Sim.cmd(H, "join", "zed")
    check(Sim.find(H.chat, "No player named 'zed'") ~= nil, "unknown name")
end)

test("study group: player list locations, mod menu button", function()
    local w, H, A = world_with({ "Host", "A" })
    enter(w, A, 2)
    w:step(20)
    local npA = H.nps[1]
    check(npA.overrideLocation:find("THE SWAMP %- Act 2: STADIUM STAIR SPRINT") ~= nil, "host sees A's mission in the list: " .. tostring(npA.overrideLocation))
    check(H.nps[0].overrideLocation == "Central Campus", "hub label")
    H.menu["Join my study group"]()
    check(H.level == LEVEL_BOB and H.act == 2, "mod menu joins the biggest group")
end)

---------------------------------------------------------------------------------------------
-- late joiner + collected star
---------------------------------------------------------------------------------------------
test("late joiner after success: star without cutscene; after collection: DONE, no respawn", function()
    local w, H, A, B, Cc, D = world_with({ "Host", "A", "B", "C", "D" })
    local P = A.env.SWAMP_POINTS
    enter(w, A, 3); enter(w, B, 3)
    w:seconds(4)
    chorus_win(w, A, B, P)
    check(state(A) == MS.SUCCESS, "success")
    enter(w, Cc, 3)
    w:step(5)
    check(state(Cc) == MS.SUCCESS, "late joiner sees success")
    check(Sim.stars_of(Cc, 2) == 1, "late joiner has the star (one)")
    local own = Cc.starSpawns[1]
    check(own ~= nil and (own.network or raw(own.star).oStarSpawnExtCutsceneFlags == 0), "no cutscene for the late joiner")
    -- A collects the star
    local star = Sim.objects_with(A, C.id_bhvStarSpawnCoordinates)[1]
    Sim.run_hooks(A, C.HOOK_ON_INTERACT, A.ms[0], star, C.INTERACT_STAR_OR_KEY, true)
    w:step(4)
    check(state(B) == MS.DONE, "DONE after the collection")
    enter(w, D, 3)
    w:step(5)
    check(Sim.stars_of(D, 2) == 0, "no respawn for later arrivals")
    check(Sim.hud_has(D, "Star collected"), "panel says collected")
    Sim.cmd(D, "mission", "reset")
    w:step(3)
    check(state(D) == MS.INTRO or state(D) == MS.WAITING, "/mission reset restarts it")
end)

test("replay: /mission reset after a collected star spawns the next round's star (round in the star bparams)", function()
    local w, A, B = world_with({ "A", "B" })
    local P = A.env.SWAMP_POINTS
    enter(w, A, 3); enter(w, B, 3)
    w:seconds(4)
    chorus_win(w, A, B, P)
    w:step(3)
    local r1 = Sim.ctx(A).r
    check(state(A) == MS.SUCCESS and Sim.stars_of(A, 2) == 1 and Sim.stars_of(B, 2) == 1, "round " .. r1 .. ": one star")
    local bp1 = (A.starSpawns[1] or B.starSpawns[1]).bparams
    check(bp1 == A.env.sgl_mission_star_bparams(Sim.ctx(A).def, r1) and (bp1 >> 24) == 2 and (bp1 & 0xFFFF) == r1,
        "star bparams: id 2 in the top byte, the round in the low 16 bits")
    -- A grabs it: gone on every client (packet_collect_star), DONE
    local star = Sim.objects_with(A, C.id_bhvStarSpawnCoordinates)[1]
    Sim.run_hooks(A, C.HOOK_ON_INTERACT, A.ms[0], star, C.INTERACT_STAR_OR_KEY, true)
    for _, c in ipairs({ A, B }) do
        for _, o in ipairs(Sim.objects_with(c, C.id_bhvStarSpawnCoordinates)) do raw(o).activeFlags = C.ACTIVE_FLAG_DEACTIVATED end
    end
    w:step(4)
    check(state(B) == MS.DONE and Sim.hud_has(B, "replay: /mission reset"), "DONE, the panel offers /mission reset")
    Sim.cmd(B, "mission", "reset")
    w:seconds(4)
    check(Sim.ctx(A).r == r1 + 1 and state(A) == MS.ACTIVE, "round " .. (r1 + 1) .. " running in the same visit")
    local nA, nB = #A.starSpawns, #B.starSpawns
    chorus_win(w, A, B, P)
    w:step(3)
    check(state(A) == MS.SUCCESS and Sim.stars_of(A, 2) == 1 and Sim.stars_of(B, 2) == 1,
        "the replayed round has its star (not swallowed by the per-visit de-dup)")
    check(#A.starSpawns + #B.starSpawns == nA + nB + 2, "spawned once, received once")
    check(Sim.hud_has(A, "Grab the star"), "Grab the star")
end)

---------------------------------------------------------------------------------------------
-- engine contract checks
---------------------------------------------------------------------------------------------
test("contract: spawn_default_star only from the controller loop; one controller per instance", function()
    local w, A = world_with({ "A" })
    enter(w, A, 1)
    w:step(5)
    local ok = pcall(A.env.spawn_default_star, 0, 0, 0)
    check(not ok, "the stub rejects calls outside an object loop (so the mods never do it)")
    check(#Sim.objects_with(A, A.env.id_bhvSglMission) == 1, "one controller")
    w:step(30)
    check(#Sim.objects_with(A, A.env.id_bhvSglMission) == 1, "still one controller")
    w:warp(A, HUB, 1, 0)
    w:step(3)
    check(Sim.ctx(A) == nil and #Sim.objects_with(A, A.env.id_bhvSglMission) == 0, "no controller in the hub")
end)

test("sync rule: concurrent writes converge to the smaller globalIndex", function()
    local w, A, B, Cc = world_with({ "A", "B", "C" })
    B.env.gGlobalSyncTable.sgltest = 1
    Cc.env.gGlobalSyncTable.sgltest = 2
    w:step(2)
    check(A.sync.sgltest == 1 and B.sync.sgltest == 1 and Cc.sync.sgltest == 1, "B (gi 1) wins over C (gi 2)")
end)

test("HUD: every state renders without errors", function()
    local w, H, A, B = world_with({ "Host", "A", "B" })
    local P = A.env.SWAMP_POINTS
    for _, act in ipairs({ 1, 2, 3 }) do
        enter(w, A, act); enter(w, B, act)
        w:seconds(5)
        at(A, P.sprint_start, 50); at(B, P.sprint_start, 50)
        w:seconds(5)
        Sim.cmd(A, "mission", "")
        check(Sim.find(A.chat, "players 2/") ~= nil, "status for act " .. act)
        w:warp(A, HUB, 1, 0); w:warp(B, HUB, 1, 0)
        w:step(3)
    end
    Sim.cmd(A, "mission", "list")
    check(Sim.find(A.chat, "swamp_sprint") ~= nil, "/mission list")
end)

test("integration: with levels.lua + main.lua loaded, /campus swamp 3 starts the co-op mission", function()
    local files = { "course.lua", "levels.lua", "main.lua", "sgl_deepspace.lua", "sgl_hud.lua",
        "sgl_mission.lua", "swamp_chomp.lua", "swamp_missions.lua" }
    local w = Sim.new({ files = files })
    local H, A = w:connect("Host"), w:connect("A")
    w:step(3)
    check(A.env.gLevelValues.entryLevel == HUB, "levels.lua loaded (entry level = hub)")
    Sim.cmd(H, "campus", "swamp 3")
    w:step(3)
    check(H.level == LEVEL_BOB and H.act == 3 and A.level == LEVEL_BOB and A.act == 3, "everyone warped into act 3")
    w:seconds(4)
    check(state(H) == MS.ACTIVE and Sim.ctx(H).isLeader, "mission running, host leads")
    check(Sim.find(H.popups, "Welcome to Super Gatorlator 64") ~= nil, "main.lua hooks still run")
    Sim.cmd(A, "campus", "hub me")
    w:step(5)
    check(A.level == HUB and state(H) == MS.WAITING, "A back in the hub: co-op mission waits")
end)

---------------------------------------------------------------------------------------------
-- fix round: the star, leaving together, the climb route, the race, the HUD kit
---------------------------------------------------------------------------------------------
test("act 1: a friend grabs the level-script star before the leader saw the roof: DONE, no stale marker, leave together", function()
    local w, A, B = world_with({ "A", "B" })           -- A (gi 0) leads
    local P = A.env.SWAMP_POINTS
    enter(w, A, 1); enter(w, B, 1)
    w:seconds(4)
    check(state(A) == MS.ACTIVE and Sim.ctx(A).isLeader, "active, A leads")
    -- B is already on the roof and grabs the star in the frame its position would reach the leader
    at(B, P.climb_goal)
    local st = Sim.objects_with(B, C.id_bhvStar)[1]
    Sim.run_hooks(B, C.HOOK_ON_INTERACT, B.ms[0], st, C.INTERACT_STAR_OR_KEY, true)
    raw(st).activeFlags = C.ACTIVE_FLAG_DEACTIVATED
    w:warp(B, HUB, 1, 0)                                 -- "Leave level": B dances and exits at once
    w:step(3)
    check(state(A) == MS.DONE, "leader: DONE straight from ACTIVE on the got event")
    check(Sim.hud_has(A, "Star collected by B"), "panel names the collector")
    check(not Sim.hud_has(A, "Grab the star") and not Sim.hud_has(A, "STAR  "), "no 'Grab the star' / STAR marker")
    check(Sim.hud_has(A, "B got the star!") and Sim.hud_has(A, "back to campus together"), "leave-together prompt")
    check(#A.starSpawns == 0, "nothing respawned")
    A.pressed = C.U_JPAD
    w:step(2)
    check(A.warpOps[1] == C.WARP_OP_EXIT, "D-pad Up = the pause menu's EXIT COURSE (WARP_OP_EXIT)")
    check(A.level == HUB and A.arrivalNode == 0x31, "through BOB 0xF1 to hub 0x31, outside the Auditorium")
end)

test("act 1: the level star vanishing (collected elsewhere, no event) also ends the round", function()
    local w, A, B = world_with({ "A", "B" })
    enter(w, A, 1); enter(w, B, 1)
    w:seconds(4)
    local st = Sim.objects_with(A, C.id_bhvStar)[1]
    raw(st).activeFlags = C.ACTIVE_FLAG_DEACTIVATED      -- packet_collect_star deleted A's copy
    w:step(12)
    check(state(A) == MS.DONE and state(B) == MS.DONE, "leader saw the star go: DONE for everyone")
    check(Sim.hud_has(A, "Star collected"), "panel says collected")
    check(not Sim.hud_has(A, "got the star!"), "no leave prompt without a collector event")
end)

test("act 1: the marker walks the climb route; the panel stays compact once under way", function()
    local w, A = world_with({ "A" })
    local P = A.env.SWAMP_POINTS
    enter(w, A, 1)
    at(A, { x = 6651, y = 0, z = -11298 })              -- the spawn, outside the tower zone
    w:seconds(3.5)
    check(Sim.hud_has(A, "CLIMB HERE"), "at the spawn: CLIMB HERE (west rim)")
    check(Sim.hud_has(A, "West rim 20 m"), "panel open at the start")
    w:seconds(6)
    check(not Sim.hud_has(A, "West rim 20 m") and Sim.hud_has(A, "goal 66 m"), "compact panel: just the height line")
    at(A, P.climb_start)
    w:step(3)
    check(Sim.hud_has(A, "LEDGES") and not Sim.hud_has(A, "CLIMB HERE"), "on the west rim: LEDGES")
    check(Sim.hud_has(A, "+ West rim 20 m"), "a milestone opens the panel up again")
    at(A, P.climb_bgd)
    w:step(3)
    check(Sim.hud_has(A, "CAMERA DECKS / POLE"), "on the Bull Gator Deck: CAMERA DECKS / POLE")
    at(A, { x = P.climb_decks.x, y = 6200, z = P.climb_decks.z })
    w:step(3)
    check(Sim.hud_has(A, "PRESS BOX ROOF") and not Sim.hud_has(A, "CAMERA DECKS"), "on the decks: the roof marker")
    w:seconds(6)
    check(not Sim.hud_has(A, "Bull Gator Deck 44 m"), "compact again")
    at(A, P.climb_goal)
    w:step(3)
    check(state(A) == MS.SUCCESS, "roof: success")
end)

test("act 2: a racer who leaves does not stall the race; no finish 45 s after the first one ends it", function()
    local w, H, A, B = world_with({ "Host", "A", "B" })
    local P = A.env.SWAMP_POINTS
    enter(w, A, 2); enter(w, B, 2)
    w:seconds(4)
    at(A, P.sprint_start, 50); at(B, P.sprint_start, 50)
    w:seconds(3.3)
    local ctx = Sim.ctx(A)
    check(ctx.a == 2 and ctx.x == 2, "two racers at the gun")
    run_course(w, A, P, 3)
    w:step(3)
    check(ctx.a == 2, "A finished, B still running: race goes on")
    w:warp(B, HUB, 1, 0)                                 -- B gives up and leaves
    w:step(5)
    check(ctx.a == 3, "B left: results right away (not the 150 s timeout)")
    -- second race: both stay, B never finishes
    enter(w, B, 2)
    w:seconds(6)
    at(A, P.sprint_start, 50); at(B, P.sprint_start, 50)
    w:seconds(14)
    check(ctx.a == 2, "race 2 under way")
    run_course(w, A, P, 2)
    local t0 = ctx.c
    w:seconds(44)
    check(ctx.a == 2, "B gets 45 s after the first finish")
    w:seconds(2)
    check(ctx.a == 3, "then the results (" .. t0 .. " s + 45 s)")
end)

test("act 2: D-pad Down / /mission start = back to the start box (not while racing); race music; gold time", function()
    local w, A = world_with({ "A" })
    local P = A.env.SWAMP_POINTS
    enter(w, A, 2)
    w:seconds(4)
    local ctx = Sim.ctx(A)
    at(A, P.field_center, 0)
    w:step(2)
    check(Sim.hud_has(A, "teleport there"), "lobby panel offers the teleport")
    A.pressed = C.D_JPAD
    w:step(2)
    local dx, dz = A.pos.x - P.sprint_start.x, A.pos.z - P.sprint_start.z
    check(dx * dx + dz * dz <= 700 * 700 and A.action == C.ACT_IDLE, "D-pad Down: in the start box")
    w:seconds(3.3)
    check(ctx.a == 2 and A.fanfares == 1, "racing")
    local seq = (4 << 8) | C.SEQ_LEVEL_SLIDE
    check(A.music[1] == seq, "race music queued at GO (SEQUENCE_ARGS(4, SEQ_LEVEL_SLIDE))")
    local px = A.pos.x
    Sim.cmd(A, "mission", "start")
    check(A.pos.x == px, "no teleport while racing")
    w:step(1)
    check(Sim.hud_has(A, "finish first"), "told to finish first")
    run_course(w, A, P, 3.5)                              -- ~31.5 s: gold
    w:step(2)
    check(#A.music == 0 and Sim.find(A.musicLog, "stop " .. seq) ~= nil, "music stopped at the finish")
    check(Sim.hud_has(A, "GOLD TIME"), "gold toast")
    check(Sim.hud_has(A, "Gold 0'45"), "results board footer shows the gold time")
    w:seconds(1)
    Sim.cmd(A, "mission", "start")
    w:step(1)
    dx, dz = A.pos.x - P.sprint_start.x, A.pos.z - P.sprint_start.z
    check(dx * dx + dz * dz <= 700 * 700, "/mission start after the finish: back in the box")
    w:warp(A, HUB, 1, 0)
    w:step(2)
    check(#A.music == 0, "leaving the act leaves no race music behind")
end)

test("hud kit: off-screen markers stick to the edge; banners and prompts fit 4:3", function()
    local w, A = world_with({ "A" })
    local env = A.env
    local W, H = 427, 240
    local x, y, ux = env.sgl_hud_edge_point(2000, 120, true, W, H, 12, 40, W - 12, H - 36)
    check(math.abs(x - (W - 12)) < 1e-6 and math.abs(y - 120) < 1e-6 and ux == 1, "far right: right edge, same height")
    x, y = env.sgl_hud_edge_point(-50, 0, false, W, H, 12, 40, W - 12, H - 36)
    check(math.abs(x - 12) < 1e-6 and y > H / 2, "behind the camera on the left: left edge, low")
    x, y = env.sgl_hud_edge_point(W / 2, -900, true, W, H, 12, 40, W - 12, H - 36)
    check(math.abs(y - 40) < 1e-6, "far above: top edge, under the vanilla HUD row")
    check(env.sgl_hud_fit(300, 320) == 1 and env.sgl_hud_fit(608, 320) < 0.51, "fit scale")
    enter(w, A, 1)
    w:seconds(4)
    A.project = function() return false, -300, 50 end   -- everything behind the camera
    w:step(1)
    check(Sim.hud_has(A, "CLIMB HERE"), "the route marker still shows, on the edge")
end)

print(string.format("\n%d checks passed, %d failed", passed, failed))
os.exit(failed == 0 and 0 or 1)
