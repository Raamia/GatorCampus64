-- Tests for verified leaderboards, game side (docs/web_platform_spec.md 10): the headless host's own
-- timing of mission rounds and its "run" event (sgl_bridge.lua + sgl_mission.lua round_clock), the
-- "leaderboard" inbox command and the leaderboard menu (sgl_deepspace.lua, live rows + .sav fallback),
-- and that the solo outbox is never written on a headless host.
-- Run: tools/luatest/run.sh   (or: lua tools/luatest/test_runs.lua)
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

local FILES = { "course.lua", "sgl_bridge.lua", "sgl_deepspace.lua", "sgl_hud.lua", "sgl_mission.lua", "swamp_chomp.lua", "swamp_missions.lua" }
local LEVEL_BOB, HUB = C.LEVEL_BOB, C.LEVEL_CASTLE_GROUNDS
local MS = { IDLE = 0, WAITING = 1, INTRO = 2, ACTIVE = 3, SUCCESS = 4, FAILED = 5, DONE = 6 }

-- host "Campus" (gi 0) + players (gi 1, 2, ...); headless = the host runs with --headless
local function world(names, headless, opts)
    local w = Sim.new(opts or { files = FILES })
    local cs = { w:connect("Campus") }
    for _, n in ipairs(names) do cs[#cs + 1] = w:connect(n) end
    for _, c in ipairs(cs) do
        c.prints, c.sent = {}, {}
        c.stubs.print = function(s) table.insert(c.prints, s) end
        c.stubs.mod_fs_hide_errors = function() end
        c.stubs.mod_fs_reload = function()
            if c.inbox == nil then return nil end
            return { files = { ["inbox.json"] = { size = #c.inbox, data = c.inbox } } }
        end
        c.stubs.mod_fs_get_file = function(fs, name) return fs.files[name] end
        c.stubs.mod_fs_file_rewind = function() return true end
        c.stubs.mod_fs_file_read_string = function(f) return f.data end
        local send_to = c.stubs.network_send_to
        c.stubs.network_send_to = function(li, reliable, t)
            table.insert(c.sent, t)
            if c.dropRuns and t.sgl == "br" then return end       -- a lost report
            return send_to(li, reliable, t)
        end
        if headless then c.stubs.gServerSettings.headlessServer = 1 end
    end
    w:step(3)
    return w, table.unpack(cs)
end

local function at(c, p, dy) c.pos.x, c.pos.y, c.pos.z = p.x, p.y + (dy or 0), p.z end
local function enter(w, c, act) w:warp(c, LEVEL_BOB, 1, act) end
local function state(c) local ctx = Sim.ctx(c) return ctx and ctx.s or nil end

local function runs(H)
    local out = {}
    for _, line in ipairs(H.prints) do
        local json = line:match("^SGLEVT (.*)$")
        if json then
            local ev = H.env.sgl_json_decode(json)
            if ev.t == "run" then out[#out + 1] = ev end
        end
    end
    return out
end

local function sent_runs(c)
    local n = 0
    for _, t in ipairs(c.sent) do if t.sgl == "br" then n = n + 1 end end
    return n
end

local function primitives_only(ev)
    for k, v in pairs(ev) do
        if type(v) == "table" then return false end
    end
    return true
end

local function run_course(w, c, P, secondsPerCp)
    for _, cp in ipairs(P.sprint_checkpoints) do
        w:seconds(secondsPerCp)
        at(c, cp, 50)
        w:step(2)
    end
end

local function chorus_phrase(w, who)
    for _, cp in ipairs(who) do at(cp[1], cp[2], 60) end
    w:seconds(2.2)
    for _, cp in ipairs(who) do cp[1].action = C.ACT_GROUND_POUND_LAND end
    w:step(5)
    for _, cp in ipairs(who) do cp[1].action = C.ACT_IDLE end
    w:step(3)
end

local function chorus_win(w, A, B, P)
    chorus_phrase(w, { { A, P.button_nw }, { B, P.button_se } })
    chorus_phrase(w, { { A, P.button_ne }, { B, P.button_sw } })
    chorus_phrase(w, { { A, P.button_nw }, { B, P.button_se } })
end

---------------------------------------------------------------------------------------------
-- run events
---------------------------------------------------------------------------------------------
test("run: solo climb timed by the host, the leader's own count alongside, one event per round", function()
    local w, H, A = world({ "A" }, true)
    local P = A.env.SWAMP_POINTS
    enter(w, A, 1)
    w:seconds(3.5)
    check(state(A) == MS.ACTIVE, "active")
    w:seconds(6)
    at(A, P.climb_goal)
    w:step(3)
    check(state(A) == MS.SUCCESS, "success")
    w:step(3)
    local list = runs(H)
    check(#list == 1, "one run event: " .. #list)
    local r = list[1] or {}
    local own = Sim.ctx(A).rc
    check(r.mission == "swamp_skybox" and r.level == LEVEL_BOB and r.act == 1, "mission, level, act")
    check(r.players == 1 and r.gi1 == 1 and r.name1 == "A" and r.gi2 == nil, "players + flattened gi1 / name1")
    check(r.retries == 0 and math.type(r.round) == "integer", "retries 0, round")
    check(own.full and r.client_frames == own.frames, "client_frames = the leader's own count " .. tostring(r.client_frames))
    check(type(r.frames) == "number" and math.abs(r.frames - own.frames) <= 2 and r.frames > 6 * 30,
        "host frames ~ the active time: " .. tostring(r.frames) .. " vs " .. own.frames)
    check(r.gi == nil and r.name == nil, "no host gi / name on the event")
    check(primitives_only(r), "fields are primitives")
    check(sent_runs(A) == 1 and #A.prints == 0, "the client sent one report, printed nothing")
    -- star collected: SUCCESS -> DONE in the same round, no second run
    local st = Sim.objects_with(A, C.id_bhvStar)[1]
    Sim.run_hooks(A, C.HOOK_ON_INTERACT, A.ms[0], st, C.INTERACT_STAR_OR_KEY, true)
    raw(st).activeFlags = C.ACTIVE_FLAG_DEACTIVATED
    w:seconds(5)
    check(state(A) == MS.DONE and #runs(H) == 1, "DONE: still one run")
    -- the solo outbox: written on the player's machine, never on the headless host
    check(A.modFs.files["pending_runs.txt"] ~= nil and H.modFs.saves == 0 and H.modFs.files["pending_runs.txt"] == nil,
        "outbox on the client only")
end)

test("run: the host uses its own clock (a client cannot shift it), co-op pauses excluded, longest full count", function()
    local w, H, A, B = world({ "A", "B" }, true)
    local P = A.env.SWAMP_POINTS
    enter(w, A, 3); enter(w, B, 3)
    w:seconds(4)
    check(state(A) == MS.ACTIVE, "active")
    w:seconds(2)
    w:warp(B, HUB, 1, 0)                    -- pause: back to WAITING
    w:step(5)
    check(state(A) == MS.WAITING, "paused")
    w:seconds(5)
    enter(w, B, 3)
    w:seconds(4)
    check(state(A) == MS.ACTIVE and state(B) == MS.ACTIVE, "running again")
    H.clockSkew = 45                         -- the host's own clock moves 1.5 s on its own mid-round
    chorus_win(w, A, B, P)
    check(state(A) == MS.SUCCESS, "success")
    w:step(3)
    local list = runs(H)
    check(#list == 1, "one run: " .. #list)
    local r = list[1] or {}
    local a, b = Sim.ctx(A).rc, Sim.ctx(B).rc
    check(r.mission == "swamp_chorus" and r.act == 3 and r.players == 2, "co-op run, 2 players")
    check(r.gi1 == 1 and r.name1 == "A" and r.gi2 == 2 and r.name2 == "B", "both players, sorted by gi")
    check(b.frames < a.frames, "B (back mid-round) counted less than A")
    check(r.client_frames == a.frames, "client_frames = the longest full count (A's): " .. tostring(r.client_frames))
    check(math.abs(r.frames - (a.frames + 45)) <= 2, "host frames = A's active time + the host clock's own jump: "
        .. tostring(r.frames) .. " vs " .. a.frames)
    check(r.frames < a.frames + 45 + 5 * 30, "the 5 s pause is not counted")
    -- dedupe: another round of the same visit is a new run, the same round never twice
    local star = Sim.objects_with(A, C.id_bhvStarSpawnCoordinates)[1]
    Sim.run_hooks(A, C.HOOK_ON_INTERACT, A.ms[0], star, C.INTERACT_STAR_OR_KEY, true)
    w:step(4)
    check(#runs(H) == 1, "the collected star adds no run")
    Sim.cmd(B, "mission", "reset")
    w:seconds(4)
    chorus_win(w, A, B, P)
    w:step(6)
    list = runs(H)
    check(#list == 2 and list[2].round == r.round + 1 and list[2].retries == 0, "the replayed round: its own run")
end)

test("run: races are timed from GO to the winning finish; a failed round counts as a retry", function()
    local w, H, A = world({ "A" }, true)
    local P = A.env.SWAMP_POINTS
    enter(w, A, 2)
    w:seconds(4)
    at(A, P.sprint_start, 50)
    w:seconds(3.3)
    local ctx = Sim.ctx(A)
    check(ctx.a == 2, "racing")
    run_course(w, A, P, 8.5)                 -- over par
    w:seconds(7)
    check(state(A) == MS.FAILED and #runs(H) == 0, "over par: FAILED, no run")
    w:seconds(4.5)
    w:seconds(4)
    check(state(A) == MS.ACTIVE and ctx.a == 0, "new round, lobby")
    w:seconds(12)                            -- dawdle in the lobby: not part of the race time
    at(A, P.sprint_start, 50)
    w:seconds(3.3)
    check(ctx.a == 2, "racing again")
    run_course(w, A, P, 4)
    w:step(4)
    check(state(A) == MS.SUCCESS, "under par: success")
    local list = runs(H)
    check(#list == 1, "one run: " .. #list)
    local r = list[1] or {}
    check(r.mission == "swamp_sprint" and r.retries == 1 and r.players == 1 and r.name1 == "A", "mission, 1 retry, player")
    check(r.client_frames == ctx.loc.finished, "client_frames = the race time " .. tostring(r.client_frames))
    check(math.abs(r.frames - ctx.loc.finished) <= 3, "host frames ~ the race time (GO -> finish), not the lobby: "
        .. tostring(r.frames) .. " vs " .. tostring(ctx.loc.finished))
    check(sent_runs(A) == 0, "races need no extra report (the fin event carries the time)")
end)

test("run: a lost report -> the host waits 3 s, then sends the run without client_frames", function()
    local w, H, A = world({ "A" }, true)
    A.dropRuns = true
    local P = A.env.SWAMP_POINTS
    enter(w, A, 1)
    w:seconds(5)
    at(A, P.climb_goal)
    w:step(3)
    check(state(A) == MS.SUCCESS, "success")
    w:step(80)
    check(#runs(H) == 0, "still waiting")
    w:step(15)
    local r = runs(H)[1]
    check(r ~= nil and r.client_frames == nil and r.frames > 0, "sent without client_frames")
end)

test("run: no run when the host did not see the round start", function()
    local w, H, A = world({ "A" }, false)
    local P = A.env.SWAMP_POINTS
    enter(w, A, 1)
    w:seconds(4)
    check(state(A) == MS.ACTIVE, "active before the host's watch starts")
    for _, c in ipairs({ H, A }) do c.stubs.gServerSettings.headlessServer = 1 end
    w:seconds(2)
    at(A, P.climb_goal)
    w:seconds(4)
    check(state(A) == MS.SUCCESS and #runs(H) == 0, "not reported")
end)

test("run: inert without a headless host (no prints, no reports)", function()
    local w, H, A = world({ "A" }, false)
    local P = A.env.SWAMP_POINTS
    enter(w, A, 1)
    w:seconds(5)
    at(A, P.climb_goal)
    w:seconds(4)
    check(state(A) == MS.SUCCESS, "success")
    check(#H.prints == 0 and sent_runs(A) == 0, "nothing printed, nothing sent")
end)

test("outbox: never written on a headless host, still written by its clients and offline", function()
    local w, H, A = world({ "A" }, true)
    local run = { runId = "sgl_1_1", missionId = "swamp_skybox", elapsedFrames = 300, retries = 0 }
    check(H.env.sgl_deepspace_queue_run(run) == false and H.modFs.saves == 0, "headless host: refused, nothing saved")
    check(A.env.sgl_deepspace_queue_run(run) == true and A.modFs.saves == 1, "its client: saved")
    local w2, H2 = world({}, false)
    check(H2.env.sgl_deepspace_queue_run(run) == true and H2.modFs.saves == 1, "a normal host / offline: saved")
end)

---------------------------------------------------------------------------------------------
-- leaderboard command + menu
---------------------------------------------------------------------------------------------
local function hud_find(c, text)
    for _, s in ipairs(c.hudText) do
        if s:find(text, 1, true) then return s end
    end
    return nil
end

local function press(w, c, button)
    c.pressed = button
    w:step(1)
    w:step(1)
end

test("leaderboard: broadcast to everyone, targeted re-send to one player; fields checked", function()
    local w, H, A, B = world({ "A", "B" }, true)
    local enc = H.env.sgl_json_encode
    H.inbox = enc({ seq = 2, cmds = {
        { seq = 1, t = "leaderboard", mission = "swamp_sprint", n = 2, name1 = "Alice + Bob", frames1 = 1200,
          name2 = "\\#ff0000\\Carl", frames2 = 1500, at = 1800000000 - 200 },
        { seq = 2, t = "leaderboard", mission = "reitz_crane", n = 1, name1 = "Dana", frames1 = 900, at = 1800000000, gi = 2 },
    } })
    w:step(31)
    local a, b = A.env.sgl_deepspace_live_board("swamp_sprint"), B.env.sgl_deepspace_live_board("swamp_sprint")
    check(a ~= nil and b ~= nil, "broadcast reached A and B")
    check(a and #a.rows == 2 and a.rows[1].name == "Alice + Bob" and a.rows[1].frames == 1200, "rows in order")
    check(a and a.rows[2].name == "Carl" and a.at == 1800000000 - 200, "colour codes stripped, at kept")
    check(A.env.sgl_deepspace_live_board("reitz_crane") == nil and B.env.sgl_deepspace_live_board("reitz_crane") ~= nil,
        "a command with gi goes to that player only")
    local f = A.env.sgl_deepspace_on_leaderboard
    check(f({ mission = "bad id!", n = 1, name1 = "x", frames1 = 1 }) == false, "bad mission id rejected")
    check(f({ mission = "m1", n = 9, name1 = "a", frames1 = 10, name2 = "b", frames2 = 0, name3 = 5, frames3 = 3,
        name4 = "d", frames4 = 40, name5 = "e", frames5 = 50, name6 = "f", frames6 = 60 }) == true, "accepted")
    local m1 = A.env.sgl_deepspace_live_board("m1")
    check(#m1.rows == 3 and m1.rows[3].name == "e", "n clamped to 5, bad rows skipped")
    f({ mission = "m1", n = 0, at = 5 })
    check(#A.env.sgl_deepspace_live_board("m1").rows == 0, "n = 0 empties the board")
end)

test("leaderboard menu: live rows with age, every mission with rows listed, .sav snapshot offline", function()
    local w, H, A = world({ "A" }, true)
    -- the macOS helper's snapshot (mod_storage) for Reitz
    A.storage["sgl_ds_lb_reitz_rooftop_count"] = 1
    A.strStorage["sgl_ds_lb_reitz_rooftop_1"] = "GATOR-AB12|900|2"
    Sim.cmd(A, "leaderboard")
    w:step(3)
    check(hud_find(A, "CAMPUS BOARDS") and hud_find(A, "Reitz rooftop") and hud_find(A, "Skybox Climb"), "offline list")
    check(hud_find(A, "LIVE") == nil and hud_find(A, "1/") == nil, "no live marks, no scrolling with 4 boards")
    press(w, A, C.A_BUTTON)
    w:step(1)
    check(hud_find(A, "REITZ ROOFTOP") and hud_find(A, "OFFLINE SNAPSHOT"), "offline board")
    check(hud_find(A, "#1  GATOR-AB12    0M30.0S   R2") ~= nil, "snapshot row with retries")
    press(w, A, C.B_BUTTON)
    -- live boards arrive while the list is open
    local f = A.env.sgl_deepspace_on_leaderboard
    f({ mission = "swamp_sprint", n = 1, name1 = "Alice + Bob", frames1 = 1200, at = 1800000000 - 200 })
    f({ mission = "swamp_chorus", n = 1, name1 = "Eve + Finn", frames1 = 2400, at = 1800000000 })
    f({ mission = "zz_unknown", n = 1, name1 = "Zed", frames1 = 100 })
    f({ mission = "swamp_empty", n = 0 })
    w:step(2)
    check(hud_find(A, "LIVE") ~= nil, "live mark on the list")
    check(hud_find(A, "1/6") ~= nil, "6 boards (the offline 4 incl. the live sprint, + chorus + an unknown id; "
        .. "empty live boards not added): the list scrolls")
    local list = A.env.sgl_deepspace_board_list()
    check(#list == 6 and list[5].missionId == "swamp_chorus" and list[5].label == "Gator Chomp Chorus"
        and list[6].missionId == "zz_unknown" and list[6].label == "zz_unknown",
        "extra boards after the offline four: registered missions (title), then unknown ids")
    -- down twice through the 2x2 grid to the live chorus board (row 5: the list scrolls), open it
    for _ = 1, 2 do press(w, A, C.D_JPAD) end
    check(hud_find(A, "5/6") ~= nil and hud_find(A, "Gator Chomp Chorus") ~= nil
        and hud_find(A, "Reitz rooftop") == nil, "scrolled: row 5 visible, row 1 not")
    press(w, A, C.A_BUTTON)
    w:step(1)
    check(hud_find(A, "GATOR CHOMP CHORUS") and hud_find(A, "LIVE  UPDATED JUST NOW"), "live board + age")
    check(hud_find(A, "#1  Eve + Finn    1M20.0S") ~= nil, "live row (no retries)")
    press(w, A, C.B_BUTTON)
    press(w, A, C.U_JPAD)   -- back to the sprint (row 3, live: its .sav snapshot is not used)
    press(w, A, C.A_BUTTON)
    w:step(1)
    check(hud_find(A, "STADIUM STAIR SPRINT") and hud_find(A, "LIVE  UPDATED 3M AGO"), "3 minutes old")
    check(hud_find(A, "#1  Alice + Bob    0M40.0S") ~= nil, "live row")
    press(w, A, C.START_BUTTON)
    check(hud_find(A, "CAMPUS BOARDS") == nil, "START closes it")
end)

print(string.format("\n%d checks passed, %d failed", passed, failed))
if failed > 0 then os.exit(1) end
