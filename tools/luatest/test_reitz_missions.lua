-- Unit + scenario tests for mods/sgl64/wf_reitz_missions.lua (course 2, Reitz Union & Engineering, LEVEL_WF)
-- in the offline multi-client coopdx simulation (sim.lua), plus the act-select / level-script contract for
-- course 2 (docs/flow.md 5.1) against the real course.lua and, once built, the real levels/wf/script.c.
-- Run: tools/luatest/run.sh   (or: lua tools/luatest/test_reitz_missions.lua)
--
-- The two engine names the Reitz platforms use are stubbed in sim.lua (both real sm64coopdx v1.5.1 names):
-- get_network_area_timer() (the window-washer lift's clock; c.areaTimerOffset skews one client) and
-- gGlobalObjectCollisionData.checkerboard_platform_seg8_collision_0800D710 (lift + crane collision).
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

-- the two engine names (see the header)
assert(API.get_network_area_timer ~= nil and API.get_network_area_timer[1] == 0, "get_network_area_timer() is a v1.5.1 API")

local WF, HUB = C.LEVEL_WF, C.LEVEL_CASTLE_GROUNDS
local MS = { IDLE = 0, WAITING = 1, INTRO = 2, ACTIVE = 3, SUCCESS = 4, FAILED = 5, DONE = 6 }
local FILES = { "course.lua", "sgl_deepspace.lua", "sgl_hud.lua", "sgl_mission.lua", "swamp_missions.lua", "wf_reitz_missions.lua" }
local PHX, PTOP, PBOT, PHZ = 256, 26, 25, 153      -- checkerboard platform collision (scale 1)

-- test stick: c.stick = { x, y } replaces the controller stick before every other hook sees it
local function install_stick(c)
    table.insert(c.hooks[C.HOOK_BEFORE_MARIO_UPDATE], 1, function(m)
        if raw(m).playerIndex == 0 and c.stick ~= nil then
            local ctl = m.controller
            ctl.stickX, ctl.stickY = c.stick[1], c.stick[2]
            ctl.stickMag = math.sqrt(c.stick[1] ^ 2 + c.stick[2] ^ 2)
        end
    end)
    return c
end

-- connect players named A, B, ... (gi 0, 1, ...) with the Reitz stage built; they sync in the hub
local function world_with(names, opts)
    opts = opts or {}
    opts.files = opts.files or FILES
    opts.built = opts.built or { [HUB] = true, [C.LEVEL_BOB] = true, [WF] = true }
    local w = Sim.new(opts)
    local cs = {}
    for _, n in ipairs(names) do
        table.insert(cs, install_stick(w:connect(n)))
    end
    w:step(3)
    return w, table.unpack(cs)
end

local function enter(w, c, act) w:warp(c, WF, 1, act) end

local function at(c, p, dy)
    c.pos.x, c.pos.y, c.pos.z = p.x, p.y + (dy or 0), p.z
end

local function ctx_of(c) return Sim.ctx(c) end

local function state(c)
    local ctx = ctx_of(c)
    return ctx and ctx.s or nil
end

local function def_of(c, act) return c.env.sgl_mission_get(WF, act) end

local function platforms(c) return Sim.objects_with(c, c.env.id_bhvSglReitzPlatform) end

---------------------------------------------------------------------------------------------
-- registry, act names, act select, level script
---------------------------------------------------------------------------------------------
test("registry: three Reitz missions on acts 1/2/3, star ids act-1, titles = course.lua act names, acts 4-6 coming soon", function()
    local w, A = world_with({ "A" })
    local env = A.env
    local d1, d2, d3 = def_of(A, 1), def_of(A, 2), def_of(A, 3)
    check(d1 and d1.id == "reitz_rooftop" and d1.starId == 0 and d1.minPlayers == 1, "act 1 rooftop, star 0, solo")
    check(d2 and d2.id == "reitz_tokens" and d2.starId == 1 and d2.minPlayers == 1, "act 2 tokens, star 1, solo")
    check(d3 and d3.id == "reitz_robotics" and d3.starId == 2 and d3.minPlayers == 2, "act 3 robotics, star 2, 2+ players")
    local stage = env.sgl_stage_by_level(WF)
    check(stage ~= nil and stage.key == "reitz" and stage.door == 2 and stage.stars == 2 and stage.acts ~= nil,
        "course.lua: door 2 = REITZ & ENGINEERING (2 stars) with act names")
    for _, d in ipairs({ d1, d2, d3 }) do
        check((d.bparams >> 24) == d.starId, d.id .. " bparams carry the star id")
        check(stage.acts[d.act] == d.title, d.id .. " title matches course.lua act " .. d.act .. " (" .. tostring(stage.acts[d.act]) .. ")")
        check(not env.sgl_act_is_soon(stage, d.act), d.id .. " act is not 'coming soon'")
        check(d.probes ~= nil and #d.probes >= 2, d.id .. " has geometry probes")
        check(#d.objective <= 60, d.id .. " objective fits the banner (" .. #d.objective .. " chars)")
        check(d.pointsFile ~= nil and d.pointsFile:find("wf_reitz_missions.lua", 1, true) ~= nil, d.id .. " names its points file")
    end
    for act = 4, 6 do
        check(env.sgl_mission_get(WF, act) == nil, "act " .. act .. " has no mission yet")
        check(env.sgl_act_is_soon(stage, act) and stage.acts[act]:find("^COMING SOON") ~= nil,
            "act " .. act .. " is named COMING SOON: " .. tostring(stage.acts[act]))
    end
    for act = 1, 6 do
        check(not stage.acts[act]:find("[^A-Z0-9 '%.,%-&!%?]") and #stage.acts[act] <= 28,
            "act " .. act .. " name fits the act-select menu font: " .. stage.acts[act])
    end
    -- the Swamp is untouched
    check(env.sgl_mission_get(C.LEVEL_BOB, 1).id == "swamp_skybox" and #env.SGL_MISSION_LIST == 6, "3 Swamp + 3 Reitz missions")
end)

test("act select (star_select.c): an empty save reaches acts 1, 2, 3 in turn; act 1 needs no second player", function()
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
    check(def_of(A, 1).minPlayers == 1 and def_of(A, 2).minPlayers == 1, "the solo acts come first")
end)

test("levels/wf/script.c (when built): warp contract for door 2, no level-script star for acts that spawn theirs", function()
    local ls = Sim.level_script("wf")
    if ls == nil then
        print("  (levels/wf not built: skipped)")
        return
    end
    local w, A = world_with({ "A" })
    local function node(n)
        local wn = ls.warps[n]
        return wn and C[wn.level], wn and wn.node
    end
    local l0, n0 = node(0x0A)
    local l1, n1 = node(0xF0)
    local l2, n2 = node(0xF1)
    check(l0 == WF and n0 == 0x0A, "WF 0x0A = own entry spawn")
    check(l1 == HUB and n1 == 0x22, "WF 0xF0 -> hub 0x22 (outside The Hub door)")
    check(l2 == HUB and n2 == 0x32, "WF 0xF1 -> hub 0x32")
    local starActs = 0
    for _, o in ipairs(ls.objects) do
        if o.bhv == "bhvStar" then
            for k = 1, 6 do
                if o.acts == (1 << (k - 1)) then starActs = starActs | (1 << (k - 1)) end
            end
        end
    end
    for k = 1, 3 do
        local d = def_of(A, k)
        local has = (starActs >> (k - 1)) & 1 == 1
        check((d.levelStar == true) == has, string.format("act %d: levelStar %s matches the level script (%s)", k,
            tostring(d.levelStar), has and "has a bhvStar" or "no bhvStar"))
    end
    -- the level's coins, act by act (bhvCoinFormation: bparam2 0 = line of 5 along the facing, 1.6 m apart;
    -- 2 = ring of 8, r 3 m; a Goomba drops one)
    local function coins_in(act)
        local out, n = {}, 0
        for _, o in ipairs(ls.objects) do
            if (o.acts >> (act - 1)) & 1 == 1 then
                local yaw = math.rad(o.ry or 0)
                if o.bhv == "bhvYellowCoin" then
                    out[#out + 1] = { x = o.x, y = o.y, z = o.z }
                elseif o.bhv == "bhvCoinFormation" then
                    local shape = (o.bparams >> 16) & 0xFF
                    for i = 0, (shape == 2 and 7 or 4) do
                        if shape == 2 then
                            local t = i * math.pi / 4
                            out[#out + 1] = { x = o.x + 300 * math.cos(t), y = o.y, z = o.z + 300 * math.sin(t) }
                        else
                            local l = 160 * (i - 2)
                            out[#out + 1] = { x = o.x + l * math.sin(yaw), y = o.y, z = o.z + l * math.cos(yaw) }
                        end
                    end
                elseif o.bhv == "bhvGoomba" then
                    n = n + 1
                end
            end
        end
        return out, #out + n
    end
    local P = A.env.REITZ_POINTS
    local tokAct = A.env.REITZ_MISSION_ACTS.tokens
    local tokCoins = coins_in(tokAct)
    local onToken = 0
    for _, t in ipairs(P.tokens) do
        for _, c in ipairs(tokCoins) do
            if (c.x - t.x) ^ 2 + (c.z - t.z) ^ 2 < 150 * 150 and c.y > t.y - 100 and c.y < t.y + 300 then
                onToken = onToken + 1
                print(string.format("  coin at (%d, %d, %d) on the %s token", c.x, c.y, c.z, t.name))
            end
        end
    end
    check(onToken == 0, "act " .. tokAct .. ": no level coin is drawn inside a meal-swipe token (stage_pickups REITZ_TOKEN_ACT)")
    for act = 1, 6 do
        local _, n = coins_in(act)
        check(n >= 120, string.format("act %d: %d coins (incl. Goombas) for the 100-coin star", act, n))
    end
    local _, n1 = coins_in(1)
    local _, n2 = coins_in(tokAct)
    check(n1 - n2 <= 5, "the token act only loses the coins on token spots (" .. (n1 - n2) .. ")")
end)

test("levels/wf area 2 (the Reitz Union interior, when built): entry node, exits, paired instant warps, elevator pads", function()
    local ls = Sim.level_script("wf")
    if ls == nil or ls.areaWarps[2] == nil then
        print("  (levels/wf has no area 2: skipped)")
        return
    end
    local a1, a2 = ls.areaWarps[1] or {}, ls.areaWarps[2]
    local e = a2[0x0A]
    check(e ~= nil and e.level == "LEVEL_WF" and e.area == 2 and e.node == 0x0A, "area 2 0x0A = its own (debug) entry spawn")
    check(ls.warps[0x0A] ~= nil and ls.warps[0x0A].area == 1, "the level's 0x0A (door entry, warp_to_level area 1) stays area 1's")
    for _, n in ipairs({ 0xF0, 0xF1 }) do
        local x, y = a1[n], a2[n]
        check(x ~= nil and y ~= nil and x.level == y.level and x.area == y.area and x.node == y.node,
            string.format("area 2 0x%02X = area 1's (pause exit / death lead outside The Hub door)", n))
    end
    -- INSTANT_WARP(index, area, dx, dy, dz) per area block: every door of area 1 leads into area 2 and back
    local f = assert(io.open(Sim.MOD .. "levels/wf/script.c", "r"))
    local src = f:read("a")
    f:close()
    local iw, cur = { [1] = {}, [2] = {} }, nil
    for line in src:gmatch("[^\n]+") do
        local an = line:match("^%s*AREA%(%s*(%d+)")
        if an then cur = tonumber(an) elseif line:match("^%s*END_AREA") then cur = nil end
        local i, a, x, y, z = line:match("INSTANT_WARP%(%s*([%wx]+)%s*,%s*([%wx]+)%s*,%s*(%-?%d+)%s*,%s*(%-?%d+)%s*,%s*(%-?%d+)")
        if i and cur and iw[cur] then
            iw[cur][tonumber(i)] = { area = tonumber(a), x = tonumber(x), y = tonumber(y), z = tonumber(z) }
        end
    end
    local n = 0
    for i, w1 in pairs(iw[1]) do
        n = n + 1
        local w2 = iw[2][i]
        check(w1.area == 2 and w2 ~= nil and w2.area == 1 and w2.x == -w1.x and w2.y == -w1.y and w2.z == -w1.z,
            string.format("instant warp %d: area 1 -> 2 and back with opposite offsets", i))
        for _, k in ipairs({ 1, 2 }) do
            local cf = io.open(Sim.MOD .. "levels/wf/area_" .. k .. "/collision.inc.c", "r")
            local col = cf and cf:read("a") or ""
            if cf then cf:close() end
            check(col:find("SURFACE_INSTANT_WARP_1" .. string.char(string.byte("B") + i), 1, true) ~= nil,
                string.format("area %d collision has the warp %d floor (SURFACE_INSTANT_WARP_1%s)", k, i, string.char(string.byte("B") + i)))
        end
    end
    check(n >= 1, n .. " door(s) of area 1 lead into the interior")
    -- elevator pads (bhvFadingWarp, bparam2 = its node): every pad's node leads to another pad of area 2 and back
    local pads = {}
    for _, o in ipairs(ls.objects) do
        if o.bhv == "bhvFadingWarp" then
            check(o.area == 2, "fading-warp pads only in area 2")
            pads[(o.bparams >> 16) & 0xFF] = o
        end
        if o.area == 2 then check(o.bhv ~= "bhvStar", "no level-script star in area 2") end
    end
    local np = 0
    for node, o in pairs(pads) do
        np = np + 1
        local wn = a2[node]
        check(wn ~= nil and wn.level == "LEVEL_WF" and wn.area == 2 and pads[wn.node] ~= nil and a2[wn.node] ~= nil
            and a2[wn.node].node == node, string.format("pad 0x%02X -> pad 0x%02X -> back", node, wn and wn.node or -1))
    end
    print(string.format("  area 2: %d instant-warp doors, %d elevator pads", n, np))
end)



-- act 3 helpers ------------------------------------------------------------------------------
local HEAD, GH = 280, 50      -- wf_reitz_missions.lua act 3 spec: rider headroom under a locked gate, half bar
local function cranes(c) return ctx_of(c).loc.cranes end
local function d3(c) return def_of(c, 3) end
local function lay(c, k) return d3(c).layouts(ctx_of(c))[k] end
local function gate_open(c, k, g) return d3(c).gateOpen(ctx_of(c), k, g) end

-- stand rider c on crane cr (dx along the deck from its centre)
local function ride(c, cr, P, dx)
    c.pos.x, c.pos.y, c.pos.z = cr.x + (dx or 0), cr.y + PTOP, P.crane_z
end

local function carry(riders, k, P)
    for _, r in ipairs(riders or {}) do ride(r, cranes(r)[k], P) end
end

-- hold the stick for n frames, then let it go
local function hold(w, c, sx, sy, n, riders, k, P)
    c.stick = { sx, sy }
    for _ = 1, n do
        w:step(1)
        carry(riders, k or 1, P)
    end
    c.stick = { 0, 0 }
    w:step(1)
    carry(riders, k or 1, P)
end

-- the operator steers crane k sideways until it is within 2 units of tx (or stops); riders ride along
local function steer_x(w, op, k, tx, riders, P)
    local still, lastMag = 0, 64
    for _ = 1, 600 do
        local cr = cranes(op)[k]
        local dx = tx - cr.x
        if math.abs(dx) <= 2 and lastMag <= 12 then break end
        local dirX = ctx_of(op).loc.dirX or -1
        -- the operator's stick is read in HOOK_BEFORE_MARIO_UPDATE and applied by the next frame's drive:
        -- half the distance per frame, so the frame of lag never overshoots
        local mag = math.min(64, math.max(10, math.abs(dx) * 64 / 18))
        lastMag = mag
        op.stick = { (dx > 0 and 1 or -1) * dirX * mag, 0 }
        local before = cr.x
        w:step(1)
        carry(riders, k, P)
        if cranes(op)[k].x == before then
            still = still + 1
            if still > 5 then break end
        else
            still = 0
        end
    end
    op.stick = { 0, 0 }
    w:step(3)
    carry(riders, k, P)
end

-- the operator pushes crane k up (dir 1) or down (dir -1) until it stops; riders ride along
local function steer_y(w, op, k, riders, P, dir)
    local still = 0
    for _ = 1, 900 do
        local before = cranes(op)[k].y
        op.stick = { 0, 64 * (dir or 1) }
        w:step(1)
        carry(riders, k, P)
        if cranes(op)[k].y == before then
            still = still + 1
            if still > 3 then break end
        else
            still = 0
        end
    end
    op.stick = { 0, 0 }
    w:step(3)
    carry(riders, k, P)
end

-- rider c walks along crane k's deck under gate g's "!" box and jumps into it, then lands
local function hit_box(w, c, k, g, P)
    local s = d3(c).sensorOf(lay(c, k), g)
    local cr = cranes(c)[k]
    c.pos.x, c.pos.y, c.pos.z = s.x, cr.y + PTOP + 40, P.crane_z
    w:step(1)
    c.pos.y = cr.y + PTOP
    w:step(2)
end

-- one gate: up until the locked gate stops the crane, line the deck up under the "!" box, the rider jumps
-- into it, then steer under the gap. -> the crane's deck top when it stopped
local function pass_gate(w, op, rider, k, g, P)
    local lane = d3(op).lanes[k]
    steer_y(w, op, k, { rider }, P)
    local stopTop = cranes(op)[k].y + PTOP
    local s = d3(op).sensorOf(lay(op, k), g)
    steer_x(w, op, k, math.max(lane.xMin, math.min(lane.xMax, s.x)), { rider }, P)
    hit_box(w, rider, k, g, P)
    w:step(3)
    steer_x(w, op, k, lay(op, k).gapX[g], { rider }, P)
    return stopTop
end

local function climb_all(w, op, rider, k, P)
    for g = 1, #P.gate_y do pass_gate(w, op, rider, k, g, P) end
    steer_y(w, op, k, { rider }, P)
end

test("REITZ_POINTS: inside s16 and the play zone; act 3 geometry fits the atrium (floors: check_reitz_points.py)", function()
    local w, A = world_with({ "A" })
    local P = A.env.REITZ_POINTS
    local n = 0
    local function inside(p, what)
        n = n + 1
        check(math.abs(p.x) <= 27000 and math.abs(p.z) <= 27000 and math.abs(p.y) <= 32767, what .. " inside the play zone")
    end
    for k, v in pairs(P) do
        if type(v) == "table" and v.x ~= nil then inside(v, k) end
    end
    for i, t in ipairs(P.tokens) do inside(t, "token " .. i .. " " .. t.name) end
    check(#P.tokens == 8 and n >= 21, "8 tokens + the named points (" .. n .. ")")
    -- act 3: the crane deck at the top is level with the ledge, 0.2 m short of it, inside the atrium
    local D = d3(A)
    local spec = D.spec
    check(D.lanes ~= nil and #D.lanes == 2, "two crane lanes")
    check(P.crane_z + PHZ < P.ledge.z0 and P.ledge.z0 - (P.crane_z + PHZ) <= 40, "crane deck stops 0.2 m from the ledge edge")
    check(P.crane_z - PHZ > P.atrium.z0, "crane inside the atrium (north)")
    check(spec.yMax + PTOP == P.ledge.y and spec.yMin - PBOT == P.atrium.y, "deck travels from the atrium floor to the ledge floor")
    check(P.lab_entry.x > P.atrium.x0 and P.lab_entry.x < P.atrium.x1 and P.lab_entry.z > P.atrium.z0
        and P.lab_entry.z < P.crane_z - PHZ - 300 and D.inLab(P.lab_entry), "D-pad Down lands inside the atrium, clear of the cranes")
    for _, c in ipairs({ P.console_1, P.console_2 }) do
        check((c.x - P.lab_entry.x) ^ 2 + (c.z - P.lab_entry.z) ^ 2 > (spec.consoleRadius + 200) ^ 2, "the lab entry is not on a console")
    end
    local open = function() return true end
    local shut = function() return false end
    for k, lane in ipairs(D.lanes) do
        check(lane.x0 >= P.atrium.x0 and lane.x1 <= P.atrium.x1 and lane.xMin < lane.xMax, "lane " .. k .. " inside the atrium")
        local cz = lane.console
        check(cz.x > P.atrium.x0 and cz.x < P.atrium.x1 and cz.z > P.atrium.z0 and cz.z < P.crane_z - PHZ - 300,
            "lane " .. k .. " console on the atrium floor, clear of the crane")
        -- every round's layout (the 5 patterns)
        local layouts = {}
        for r = 1, #spec.patterns do
            local L = D.layout(k, r)
            layouts[L.pattern] = true
            check(D.blocked(L, lane.start.x, lane.start.y, shut) == nil, string.format("lane %d round %d: the start is free", k, r))
            for g, y in ipairs(P.gate_y) do
                local tag = string.format("lane %d round %d gate %d", k, r, g)
                local gx = L.gapX[g]
                local top = y - GH - HEAD - PTOP                        -- highest crane y under a locked gate
                -- locked: the whole gate stops the crane HEAD below the bar, anywhere in the lane
                local stopsEverywhere = true
                for x = lane.xMin, lane.xMax, 8 do
                    if D.blocked(L, x, top, shut) ~= nil or D.blocked(L, x, top + 8, shut) == nil then stopsEverywhere = false end
                end
                check(stopsEverywhere, tag .. ": locked, it stops the deck 2.8 m under the bar everywhere")
                -- open: the crane fits the gap (+-0.54 m), not at the lane walls (no steering blind)
                check(D.blocked(L, gx, y, open) == nil and D.blocked(L, gx + 50, y, open) == nil
                    and D.blocked(L, gx - 50, y, open) == nil, tag .. ": open, the crane fits its gap")
                check(D.blocked(L, gx + 70, y, open) ~= nil and D.blocked(L, gx - 70, y, open) ~= nil, tag .. ": the gap is narrow")
                check(D.blocked(L, lane.xMin, y, open) ~= nil and D.blocked(L, lane.xMax, y, open) ~= nil,
                    tag .. ": hugging either lane wall does not fit through")
                -- the "!" box: under the bar (not over the gap), reachable from the deck of a crane at its travel end
                local s = D.sensorOf(L, g)
                check(math.abs(s.x - gx) >= 310 + 51 and s.x - 51 >= lane.x0 and s.x + 51 <= lane.x1, tag .. ": the ! box hangs under the bar")
                local cx = math.max(lane.xMin, math.min(lane.xMax, s.x))
                check(math.abs(s.x - cx) + 51 + 37 <= PHX, tag .. ": a rider on the deck can stand under the ! box")
                -- standing on the stopped deck the rider's head is under the box; a 2.2 m jump reaches it
                local deck = top + PTOP
                check(deck + 160 < s.y - 10 and deck + 160 + 220 > s.y, tag .. ": head under the box, a jump reaches it")
            end
        end
        local nl = 0
        for _ in pairs(layouts) do nl = nl + 1 end
        check(nl == #spec.patterns, "lane " .. k .. ": every pattern is used over 5 rounds")
    end
    check(D.layout(1, 7).gapX[1] ~= D.layout(1, 8).gapX[1] or D.layout(1, 7).gapX[2] ~= D.layout(1, 8).gapX[2],
        "the gaps move from one round to the next")
    check(D.layout(1, 3).pattern ~= D.layout(2, 3).pattern, "the two lanes differ in a round")
end)

---------------------------------------------------------------------------------------------
-- act 1: ROOFTOP OF THE REITZ
---------------------------------------------------------------------------------------------
test("act 1: solo climb, route marker, milestones, penthouse -> one spawned star; collect -> DONE", function()
    local w, A = world_with({ "A" })
    local P = A.env.REITZ_POINTS
    enter(w, A, 1)
    at(A, { x = 2400, y = 0, z = -6400 })                 -- the North Lawn, outside the tower zone
    w:step(3)
    check(Sim.hud_has(A, "ROOFTOP OF THE REITZ"), "act banner")
    check(Sim.find(A.console, "sleeps") == nil, "probes pass")
    w:seconds(3.5)
    local ctx = ctx_of(A)
    check(state(A) == MS.ACTIVE and ctx.isLeader, "solo: active, leader")
    check(Sim.hud_has(A, "CLIMB HERE"), "marker: CLIMB HERE (ravine terrace)")
    at(A, P.climb_start)
    w:step(3)
    check(Sim.hud_has(A, "AWNINGS") and not Sim.hud_has(A, "CLIMB HERE"), "on the terrace: AWNINGS")
    at(A, P.ballroom_roof)
    w:step(3)
    check(ctx.f == 1 and Sim.hud_has(A, "Ballroom roof reached"), "milestone: ballroom roof 13 m")
    check(Sim.hud_has(A, "WINDOW%-WASHER LIFT"), "on the ballroom roof: WINDOW-WASHER LIFT")
    at(A, P.podium_roof)
    w:step(3)
    check(ctx.f == 3 and ctx.p == 17, "podium roof 17 m")
    at(A, P.tower_roof)
    w:step(3)
    check(ctx.f == 7 and Sim.hud_has(A, "PENTHOUSE ROOF"), "tower roof: the goal marker")
    check(state(A) == MS.ACTIVE, "the tower roof (26.4 m) is not the goal")
    -- high but outside the Reitz Union (Malachowsky's roof) does not count
    at(A, { x = 3800, y = 3300, z = 24700 })
    w:step(3)
    check(ctx.p == 26, "Malachowsky's 33 m roof ignored (not the Reitz)")
    -- a jump beside the penthouse (3.5 m off its centre, feet below its roof) does not count
    at(A, { x = P.roof_goal.x, y = P.roof_goal.y - 60, z = P.roof_goal.z + 350 })
    w:step(3)
    check(state(A) == MS.ACTIVE, "beside the penthouse, below its roof: not yet")
    at(A, P.roof_goal)
    w:step(3)
    check(state(A) == MS.SUCCESS, "penthouse roof: success")
    w:step(3)
    check(#A.starSpawns == 1 and Sim.stars_of(A, 0) == 1, "one spawned star (id 0)")
    local sp = A.starSpawns[1]
    check(sp and sp.x == P.roof_star.x and sp.y == P.roof_star.y and sp.z == P.roof_star.z, "star on the penthouse, 1.2 m up")
    check(sp and sp.from.y == P.roof_star.y + 800, "it drops in from 8 m above")
    check(Sim.find(A.console, "has no star") == nil and Sim.find(A.console, "spawns its own") == nil, "no star warnings")
    local star = Sim.objects_with(A, C.id_bhvStarSpawnCoordinates)[1]
    Sim.run_hooks(A, C.HOOK_ON_INTERACT, A.ms[0], star, C.INTERACT_STAR_OR_KEY, true)
    raw(star).activeFlags = C.ACTIVE_FLAG_DEACTIVATED
    w:step(4)
    check(state(A) == MS.DONE and Sim.stars_of(A, 0) == 0, "DONE, no respawn")
end)

test("act 1: the window-washer lift shuttles podium roof <-> parapet top on the area timer, carrying its rider", function()
    local w, A, B = world_with({ "A", "B" })
    local env = A.env
    local P = env.REITZ_POINTS
    B.areaTimerOffset = 0
    enter(w, A, 1); enter(w, B, 1)
    w:step(3)
    local la, lb = platforms(A), platforms(B)
    check(#la == 1 and #lb == 1, "one lift on each client")
    local o = la[1]
    check(raw(o).collisionData == "COL:checkerboard_platform", "checkerboard platform collision")
    local sc = raw(o).header.gfx.scale
    check(math.abs(sc.x * PHX - 120) < 1 and math.abs(sc.z * PHZ - 160) < 1, "2.4 x 3.2 m deck (reitz_points platform_half_m)")
    check(raw(o).oPosX == P.lift_bottom.x and raw(o).oPosZ == P.lift_bottom.z, "on the track 1.3 m off the tower's west face")
    local lo, hi = P.lift_bottom.y + PBOT, P.lift_top.y - PTOP
    local seenLo, seenHi, maxStep, same, inTrack, velOk = false, false, 0, true, true, true
    local prev = raw(o).oPosY
    for _ = 1, 30 * 16 do
        w:step(1)
        local y = raw(o).oPosY
        if y < lo or y > hi then inTrack = false end
        if y == lo then seenLo = true end
        if y == hi then seenHi = true end
        maxStep = math.max(maxStep, math.abs(y - prev))
        if raw(o).oVelY ~= y - prev then velOk = false end
        prev = y
        if raw(lb[1]).oPosY ~= y then same = false end
    end
    check(inTrack, "the lift stays within its track")
    check(velOk, "oVelY = each frame's move (the engine carries the rider with it)")
    check(seenLo and seenHi, "it reaches the podium roof (deck 0.5 m up) and the parapet top (27.0 m)")
    check(maxStep <= 6, "smooth: at most 6 units per frame")
    check(same, "both clients show the lift at the same height (network area timer)")
    check(hi + PTOP == P.lift_top.y, "deck level with the parapet top")
    check(env.sgl_reitz_lift_y(0) == lo and env.sgl_reitz_lift_y(60 + 149 + 10) == hi, "sgl_reitz_lift_y: wait at the bottom, then up")
    -- the deck's east edge at the top is 0.1 m from the tower's west face (map x -456.0 = game 1400): a step across
    check(P.lift_top.x + 120 <= 1400 and 1400 - (P.lift_top.x + 120) <= 20, "deck edge 0.1 m from the parapet: no jump needed")
    -- a stall (join, area sync): the timer jumps 10 s; the deck never jumps more than 12 units per frame (a rider
    -- drops through a deck that moves > 78 units in one frame) and catches up with the timer
    local yb = raw(lb[1]).oPosY
    B.areaTimerOffset = 300
    local worst, caught = 0, nil
    for i = 1, 30 * 6 do
        w:step(1)
        local y = raw(lb[1]).oPosY
        worst = math.max(worst, math.abs(y - yb))
        if raw(lb[1]).oVelY ~= y - yb then velOk = false end
        yb = y
        if caught == nil and y == env.sgl_reitz_lift_y(w.frame + 300) then caught = i end
    end
    check(worst <= 12, "after a 10 s timer jump the deck moves at most 12 units per frame (" .. worst .. ")")
    check(caught ~= nil, "and catches up with the timer (" .. tostring(caught) .. " frames)")
    check(velOk, "oVelY still matches the move (carries the rider)")
    check(env.sgl_reitz_lift_step(100, 500) == 112 and env.sgl_reitz_lift_step(100, 95) == 95 and env.sgl_reitz_lift_step(nil, 500) == 500,
        "sgl_reitz_lift_step: at most 12 per frame, snaps on its first frame")
end)

---------------------------------------------------------------------------------------------
-- act 2: MEAL SWIPE TOKENS
---------------------------------------------------------------------------------------------
local function touch(w, c, t)
    at(c, t, 50)
    w:step(2)
end

test("act 2: solo token hunt, 8 tokens, shared count, the star pops out of the last token", function()
    local w, A = world_with({ "A" })
    local P = A.env.REITZ_POINTS
    enter(w, A, 2)
    w:step(3)
    local ctx = ctx_of(A)
    local toks = Sim.objects_with(A, A.env.id_bhvSglMissionFx)
    check(#toks == 8, "8 token objects")
    check(raw(toks[1])._model == C.E_MODEL_RED_COIN and raw(toks[1]).oPosY == P.tokens[1].y + 100, "red-coin tokens 1 m over their floor")
    check(P.tokens[6].y >= 2000 and P.tokens[7].y >= 1000, "the Weil and Malachowsky tokens are up their climbs (24 m, 12 m)")
    touch(w, A, P.tokens[1])
    check(ctx.f == 0 and state(A) == MS.INTRO, "no collecting during the intro")
    at(A, { x = 2400, y = 0, z = -6400 })
    w:seconds(3.5)
    check(state(A) == MS.ACTIVE, "active")
    check(Sim.hud_has(A, "Tokens 0/8") and Sim.hud_has(A, "next: "), "panel: Tokens 0/8 + the nearest one")
    check(Sim.hud_has(A, "BOOKSTORE AWNING"), "a marker / list names the tokens")
    touch(w, A, P.tokens[1])
    check(ctx.f == 1 and ctx.p == 1, "touching token 1 once the round is on: found")
    check(Sim.hud_has(A, "GATOR CORNER PATIO token! 1/8"), "toast")
    check((raw(toks[1]).header.gfx.node.flags & C.GRAPH_RENDER_INVISIBLE) ~= 0, "found token hidden")
    check((raw(toks[2]).header.gfx.node.flags & C.GRAPH_RENDER_INVISIBLE) == 0, "others visible")
    -- next to a token but 3 m too high does not count
    at(A, P.tokens[2], 400)
    w:step(2)
    check(ctx.f == 1, "too high above the sculpture: not yet")
    for _, i in ipairs({ 2, 4, 5, 6, 7, 8 }) do touch(w, A, P.tokens[i]) end
    check(ctx.p == 7 and state(A) == MS.ACTIVE, "7/8")
    check(Sim.hud_has(A, "next: LIBERTY POND FOUNTAIN"), "panel points at the last one")
    touch(w, A, P.tokens[3])
    check(state(A) == MS.SUCCESS and ctx.f == 255 and ctx.x == 3, "8/8: success; the leader noted the last token (3)")
    w:step(3)
    check(#A.starSpawns == 1 and Sim.stars_of(A, 1) == 1, "one star (id 1)")
    local sp = A.starSpawns[1]
    local t = P.tokens[3]
    check(sp.x == t.x and sp.y == t.y + 150 and sp.z == t.z, "star 1.5 m over the last token (the fountain float), not 200 m away")
    check(sp.from.y == t.y + 1000, "dropping in from 10 m")
    check(Sim.hud_has(A, "STAR"), "STAR marker")
end)

test("act 2: two players share the hunt; same token at once counts once; a lost event is sent again", function()
    local w, A, B = world_with({ "A", "B" })
    local P = A.env.REITZ_POINTS
    enter(w, A, 2); enter(w, B, 2)
    w:seconds(4)
    local ca, cb = ctx_of(A), ctx_of(B)
    check(state(A) == MS.ACTIVE and ca.isLeader, "A leads")
    touch(w, A, P.tokens[1])
    touch(w, B, P.tokens[2])
    w:step(2)
    check(ca.f == 3 and cb.f == 3 and cb.p == 2, "both see 2/8")
    check(Sim.hud_has(B, "A found the GATOR CORNER PATIO token") and Sim.hud_has(A, "B found the ENGINEERING PLAZA"), "toasts name the finder")
    -- both on token 3 in the same frame
    at(A, P.tokens[3], 50); at(B, P.tokens[3], 50)
    w:step(3)
    check(ca.p == 3 and ca.f == 7, "token 3 counted once")
    -- A (the leader) never gets B's next event, then leaves: B leads and sends it again
    A.hooks[C.HOOK_ON_PACKET_RECEIVE] = {}
    touch(w, B, P.tokens[4])
    w:step(2)
    check(ca.f & 8 == 0, "the leader missed it")
    w:disconnect(A)
    w:step(3)
    check(cb.isLeader, "B leads")
    check((cb.f & 8) == 0, "not in the synced bits yet")
    w:seconds(3.2)
    check((cb.f & 8) ~= 0 and cb.p == 4, "B's resend landed: 4/8")
    for i = 5, 8 do touch(w, B, P.tokens[i]) end
    check(state(B) == MS.SUCCESS and cb.x == 8, "B finishes the hunt at token 8")
    w:step(3)
    check(Sim.stars_of(B, 1) == 1, "one star")
    local sp = B.starSpawns[1]
    check(sp ~= nil and sp.x == P.tokens[8].x and sp.z == P.tokens[8].z, "on the cooling-tower catwalk, where B found the last one")
end)

test("act 2: /mission reset replays the hunt with a new star; after 8 stars in one visit the panel says re-enter", function()
    local w, A, B = world_with({ "A", "B" })
    local P = A.env.REITZ_POINTS
    enter(w, A, 2); enter(w, B, 2)
    w:seconds(4)
    local stars = 0
    for round = 1, 9 do
        for i = 1, 8 do touch(w, A, P.tokens[i]) end
        w:step(4)
        local ca = ctx_of(A)
        if round <= 8 then
            if Sim.stars_of(A, 1) == 1 and Sim.stars_of(B, 1) == 1 then stars = stars + 1 end
            -- grab it (gone everywhere), then replay
            local star = Sim.objects_with(A, C.id_bhvStarSpawnCoordinates)[1]
            Sim.run_hooks(A, C.HOOK_ON_INTERACT, A.ms[0], star, C.INTERACT_STAR_OR_KEY, true)
            for _, c in ipairs({ A, B }) do
                for _, o in ipairs(Sim.objects_with(c, C.id_bhvStarSpawnCoordinates)) do raw(o).activeFlags = C.ACTIVE_FLAG_DEACTIVATED end
            end
            w:step(3)
            Sim.cmd(B, "mission", "reset")
            w:seconds(4)
        else
            check(state(A) == MS.SUCCESS, "round 9 succeeds")
            w:seconds(2.5)
            check(Sim.stars_of(A, 1) == 0, "coopdx keeps 8 stars per level visit: no 9th")
            check(Sim.hud_has(A, "no more stars this visit: re%-enter the act"), "the panel says to re-enter the act")
            check(not Sim.hud_has(A, "Grab the star"), "no 'Grab the star' over nothing")
            check(Sim.find(A.console, "at most 8 per level visit") ~= nil, "console note")
        end
    end
    check(stars == 8, "8 rounds, 8 stars in one visit (" .. stars .. ")")
    -- a new visit clears coopdx's list
    w:warp(A, HUB, 1, 0); w:warp(B, HUB, 1, 0); w:step(3)
    enter(w, A, 2)
    w:seconds(4)
    for i = 1, 8 do touch(w, A, P.tokens[i]) end
    w:step(4)
    check(Sim.stars_of(A, 1) == 1, "re-entering the act: a star again")
end)

---------------------------------------------------------------------------------------------
-- act 3: REMOTE ROBOTICS LAB (co-op cranes)
---------------------------------------------------------------------------------------------
test("act 3 alone: waiting for a second player; the console does nothing; D-pad Down goes into the lab", function()
    local w, A = world_with({ "A" })
    local P = A.env.REITZ_POINTS
    enter(w, A, 3)
    at(A, { x = 2400, y = 0, z = -6400 })                 -- the North Lawn, 290 m from the lab
    w:step(5)
    check(state(A) == MS.WAITING, "waiting")
    check(Sim.hud_has(A, "only one online"), "alone online: invite a friend or exit")
    check(Sim.hud_has(A, "D%-pad Down: into the Robotics Lab"), "panel: D-pad Down into the lab")
    A.pressed = C.D_JPAD
    w:step(2)
    check(d3(A).inLab(A.pos) and math.abs(A.pos.x - P.lab_entry.x) <= 150 and math.abs(A.pos.z - P.lab_entry.z) <= 150,
        "D-pad Down: into the atrium by the consoles (" .. A.pos.x .. ", " .. A.pos.z .. ")")
    check(A.face.y == 0 and A.action == C.ACT_IDLE and Sim.hud_has(A, "Remote Robotics Lab"), "facing the cranes, standing")
    A.pressed = C.D_JPAD
    w:step(2)
    check(Sim.hud_has(A, "You are in the Robotics Lab"), "already there: no second teleport")
    at(A, P.console_1)
    hold(w, A, 0, 64, 30)
    check(cranes(A)[1].y == P.atrium.y + PBOT, "crane 1 still at the bottom")
    check(not ctx_of(A).loc.operating, "no operator while waiting")
end)

test("act 3: locked gates open when the rider jumps into the ! box; narrow gaps; the rider reaches the ledge -> star", function()
    local w, A, B = world_with({ "A", "B" })
    local env = A.env
    local P = env.REITZ_POINTS
    enter(w, A, 3); enter(w, B, 3)
    w:step(5)
    check(state(A) == MS.INTRO, "two players: intro")
    w:seconds(3.2)
    local ca, cb = ctx_of(A), ctx_of(B)
    check(state(A) == MS.ACTIVE and ca.isLeader, "active, A leads")
    check(ca.a == 1 and ca.f == 1, "2 players: one crane, one rider needed")
    check(#platforms(A) == 2 and #Sim.objects_with(A, env.id_bhvSglButton) == 2, "two cranes and two consoles spawned")
    check(#Sim.objects_with(A, env.id_bhvSglReitzProp) == 30, "per lane and gate: 2 bar pieces + a ! box (30)")
    check(#Sim.objects_with(A, env.id_bhvSglMissionFx) == 22, "2 locked-gap flames per gate + 2 console flames")
    check(#Sim.objects_with(A, C.id_bhvCirclingAmp) == 4, "4 sensor drones (circling Amps)")
    check(Sim.hud_has(A, "CONSOLE 1") and Sim.hud_has(A, "Crane 1 console: empty"), "markers / panel point at the console")
    check(Sim.hud_has(A, "Crane 2: off"), "crane 2 is off with 2 players")
    local c1 = cranes(A)[1]
    check(c1.x == 1050 and c1.y == PBOT, "crane 1 starts on the atrium floor, lane centre")
    -- the bars sit where this round's layout says, the box is yellow and visible, the gap flames are lit
    local g1 = ctx_of(A).objs.gates[1][1]
    local L1 = lay(A, 1)
    check(raw(g1.box).oPosX == L1.sensorX[1] and raw(g1.box).oAnimState == 3, "gate 1's ! box under its bar (yellow)")
    check((raw(g1.box).header.gfx.node.flags & C.GRAPH_RENDER_INVISIBLE) == 0
        and (raw(g1.flames[1]).header.gfx.node.flags & C.GRAPH_RENDER_INVISIBLE) == 0, "locked: box and gap flames shown")
    check(math.abs(raw(g1.flames[1]).oPosX - (L1.gapX[1] - 155)) < 1, "the flames fill the gap")
    -- nobody on the console: nothing moves
    hold(w, B, 0, 64, 10)
    check(c1.y == PBOT, "nobody on the console: no movement")
    -- A takes console 1: the leader assigns it (synced o)
    at(A, P.console_1)
    w:step(2)
    check(ca.loc.operating and ca.loc.opK == 1 and d3(A).opGi(ca, 1) == 0, "A operates crane 1 (o names A)")
    w:step(2)
    check(d3(B).opGi(cb, 1) == 0 and Sim.hud_has(B, "Crane 1: driven by A"), "B's panel names the operator")
    check(Sim.hud_has(A, "You drive crane 1") and Sim.hud_has(A, "Gate 1 locked: bring a rider under the ! box"), "A's panel: driving + task")
    -- B boards; up until locked gate 1 stops it 2.8 m below the bar
    ride(B, cranes(B)[1], P)
    steer_y(w, A, 1, { B }, P)
    check(c1.y + PTOP + HEAD <= P.gate_y[1] - GH and c1.y + PTOP + HEAD > P.gate_y[1] - GH - 8,
        "locked gate 1 stops the deck 2.8 m under its bar (y " .. c1.y .. ")")
    A.stick = { 0, 64 }
    w:step(1)
    check(A.lastInput.stickMag == 0, "the operator's own stick is zeroed while driving (stays on the console)")
    A.stick = { 0, 0 }
    w:step(1)
    check(Sim.hud_has(A, "Gate 1 is locked: rider, jump into the ! box"), "bump toast")
    check(cb.loc.riding == 1 and Sim.hud_has(B, "Riding crane 1") and Sim.hud_has(B, "jump into the ! box above"), "B: riding + task")
    -- the side view for the operator and the rider
    check(Sim.hud_has(A, "CRANE 1") and Sim.hud_has(A, "riders 1/1"), "A's side view of lane 1 (riders 1/1)")
    -- standing under the box does not open it; blind sideways at the locked gate does not help
    local s = d3(A).sensorOf(L1, 1)
    steer_x(w, A, 1, math.max(d3(A).lanes[1].xMin, math.min(d3(A).lanes[1].xMax, s.x)), { B }, P)
    B.pos.x = s.x
    w:step(5)
    check(not gate_open(A, 1, 1) and ca.g == 0, "standing under the box: still locked")
    -- B jumps into the box
    hit_box(w, B, 1, 1, P)
    w:step(2)
    check((ca.g & 1) ~= 0 and gate_open(A, 1, 1) and gate_open(B, 1, 1), "gate 1 open everywhere (synced g)")
    check(Sim.hud_has(B, "Sensor hit! Gate 1 is open") and Sim.hud_has(A, "B hit the sensor: gate 1"), "toasts")
    check((raw(g1.box).header.gfx.node.flags & C.GRAPH_RENDER_INVISIBLE) ~= 0
        and (raw(g1.flames[1]).header.gfx.node.flags & C.GRAPH_RENDER_INVISIBLE) ~= 0, "box and gap flames gone")
    -- still under the bar (not the gap): up is blocked until the crane lines up with the gap
    steer_y(w, A, 1, { B }, P)
    check(c1.y + PTOP + HEAD <= P.gate_y[1] - GH, "open gate, crane under the bar: still blocked")
    check(Sim.hud_has(A, "Gate 1 open: steer under the gap"), "panel: steer under the gap")
    steer_x(w, A, 1, L1.gapX[1], { B }, P)
    check(math.abs(c1.x - L1.gapX[1]) <= 4, "lined up with the gap (" .. c1.x .. ")")
    w:step(3)
    local cbc = cranes(B)[1]
    check(math.abs(cbc.x - c1.x) < 1 and cbc.y == c1.y, "B's copy followed the stream")
    -- the other four gates, then the top
    for g = 2, 5 do
        local top = pass_gate(w, A, B, 1, g, P)
        check(top + HEAD <= P.gate_y[g] - GH and top + HEAD > P.gate_y[g] - GH - 8, "gate " .. g .. " stopped it 2.8 m under")
        check(gate_open(A, 1, g), "gate " .. g .. " opened by the rider")
    end
    check(ca.g == 31, "all five gates of lane 1 open (g " .. ca.g .. ")")
    steer_y(w, A, 1, { B }, P)
    check(c1.y == P.ledge.y - PTOP and c1.y + PTOP == P.ledge.y, "deck level with the star ledge")
    check(cranes(B)[1].y == c1.y, "B's copy at the top too")
    check(Sim.hud_has(B, "At the top: riders, step south onto the ledge"), "rider told to step off")
    local plat = platforms(B)[1]
    check(raw(plat).oPosY == cranes(B)[1].y and raw(plat).oPosZ == P.crane_z, "B's platform object at the crane's position")
    check(state(A) == MS.ACTIVE, "not yet: the rider is on the crane, not the ledge")
    at(B, { x = cranes(B)[1].x, y = P.ledge.y, z = P.ledge.z0 + 100 })
    w:step(3)
    check(ca.c == 1, "1 rider on the ledge")
    check(state(A) == MS.SUCCESS and state(B) == MS.SUCCESS, "success")
    w:step(3)
    check(Sim.stars_of(A, 2) == 1 and Sim.stars_of(B, 2) == 1, "one star (id 2) each")
    local sp = A.starSpawns[1] or B.starSpawns[1]
    check(sp ~= nil and sp.z == P.robotics_star.z and sp.y == P.robotics_star.y, "star on the ledge")
    check(sp ~= nil and sp.from ~= nil and sp.from.y == P.atrium_floor.y + 100, "rising from the atrium floor")
    -- B lets go: B button, which Mario never sees (no punch)
    A.pressed = C.B_BUTTON
    w:step(1)
    check((A.lastInput.pressed & C.B_BUTTON) == 0 and (A.lastInput.buttons & C.B_BUTTON) == 0, "B is eaten: the operator does not punch")
    w:step(2)
    check(not ca.loc.operating and Sim.hud_has(A, "You let go"), "B lets go of the crane")
    A.stick = { 0, 64 }
    w:step(2)
    check(A.lastInput.stickMag > 0, "the stick moves Mario again")
    A.stick = nil
end)

test("act 3: one operator per console (assigned by the leader); another player's crane stream is ignored", function()
    local w, A, B, Cc = world_with({ "A", "B", "C" })
    local P = A.env.REITZ_POINTS
    for _, c in ipairs({ A, B, Cc }) do enter(w, c, 3) end
    w:seconds(4)
    local ca, cb = ctx_of(A), ctx_of(B)
    -- B steps on console 1 first: B drives
    at(B, P.console_1)
    w:step(4)
    check(d3(A).opGi(ca, 1) == 1 and cb.loc.operating, "B (gi 1) drives crane 1")
    -- A (gi 0, the leader) steps on the same console: B keeps it, A waits
    at(A, P.console_1, 10)
    w:step(4)
    check(cb.loc.operating and not ca.loc.operating and d3(A).opGi(ca, 1) == 1, "B keeps the console; A does not steal it")
    check(Sim.hud_has(A, "Console 1: B is driving"), "A's panel: B is driving")
    hold(w, B, 0, 64, 20)
    local y1 = cranes(B)[1].y
    w:step(3)
    check(y1 > PBOT and cranes(A)[1].y == y1 and cranes(Cc)[1].y == y1, "only B's stream moves the crane, everywhere")
    -- C sends a bogus position for crane 1: dropped (not the operator)
    Sim.run_hooks(A, C.HOOK_ON_PACKET_RECEIVE, { sgl = "rlab", ik = ca.key, r = ca.r, k = 1, x = 700, y = 2000, gi = Cc.gi })
    w:step(2)
    check(cranes(A)[1].y == y1 and cranes(A)[1].x ~= 700, "a non-operator's crane packet is ignored")
    -- B walks a little (inside the slack ring): still the operator
    B.pos.x = P.console_1.x + 330
    w:step(3)
    check(cb.loc.operating, "B 3.3 m out (slack 0.6 m): still driving")
    -- B walks off: A, still on the console, takes over
    B.pos.x = P.console_1.x + 800
    w:step(4)
    check(ca.loc.operating and d3(A).opGi(ca, 1) == 0 and not cb.loc.operating, "B off the console: A drives")
    local xa = cranes(A)[1].x
    hold(w, A, 64, 0, 10)
    w:step(3)
    check(cranes(A)[1].x ~= xa and cranes(B)[1].x == cranes(A)[1].x, "B sees A's stream now")
end)

test("act 3: 3 players = one crane, 2 riders; 4 players = two cranes, a crane lifts 1 rider (too heavy with 2)", function()
    local w, A, B, Cc, D = world_with({ "A", "B", "C", "D" })
    local P = A.env.REITZ_POINTS
    for _, c in ipairs({ A, B, Cc }) do enter(w, c, 3) end
    w:seconds(4)
    local ca = ctx_of(A)
    check(ca.a == 1 and ca.f == 2 and d3(A).capNow(ca) == 2, "3 players: one crane, 2 riders on the ledge, 2 may ride")
    at(Cc, P.console_2)
    hold(w, Cc, 0, 64, 20)
    check(cranes(Cc)[2].y == PBOT and not ctx_of(Cc).loc.operating, "console 2 does nothing with 3 players")
    -- A drives crane 1 with B and C on it: allowed (cap 2)
    at(A, P.console_1)
    w:step(3)
    ride(B, cranes(B)[1], P); ride(Cc, cranes(Cc)[1], P)
    hold(w, A, 0, 64, 10, { B, Cc }, 1, P)
    check(cranes(A)[1].y > PBOT, "two riders on crane 1 with 3 players: it rises")
    steer_y(w, A, 1, { B, Cc }, P, -1)
    -- one rider on the ledge is not enough
    at(B, P.ledge_star)
    at(Cc, { x = 2000, y = 0, z = 23000 })
    w:step(3)
    check(ca.c == 1 and state(A) == MS.ACTIVE, "1/2 riders: not yet")
    enter(w, D, 3)
    w:step(5)
    check(ca.a == 2 and ca.f == 2 and d3(A).capNow(ca) == 1, "4 players: two cranes, 2 riders, a crane lifts 1")
    -- two riders on crane 1 now: too heavy, it does not go up
    at(B, { x = 2000, y = 0, z = 23000 })
    ride(Cc, cranes(Cc)[1], P); ride(D, cranes(D)[1], P)
    local y0 = cranes(A)[1].y
    hold(w, A, 0, 64, 15, { Cc, D }, 1, P)
    check(cranes(A)[1].y == y0, "2 riders on crane 1 with 4 players: too heavy")
    check(Sim.hud_has(A, "Too heavy! Crane 1 lifts 1 rider"), "toast: too heavy")
    check(Sim.hud_has(A, "riders 2/1"), "the side view counts the riders")
    -- D gets off: it rises
    at(D, { x = 2600, y = 0, z = 23000 })
    hold(w, A, 0, 64, 10, { Cc }, 1, P)
    check(cranes(A)[1].y > y0, "one rider: it rises")
    -- console 2 drives crane 2 now
    at(D, P.console_2)
    w:step(4)
    hold(w, D, 0, 64, 20)
    check(cranes(D)[2].y > PBOT and ctx_of(D).loc.opK == 2, "console 2 drives crane 2 now")
    w:step(3)
    check(cranes(A)[2].y == cranes(D)[2].y, "the others see crane 2 move")
    check(Sim.hud_has(A, "Crane 2: driven by D"), "panel names crane 2's operator")
    -- two riders on the ledge: success
    at(Cc, P.ledge_star)
    at(B, { x = 2600, y = P.ledge.y, z = P.ledge_star.z })
    w:step(3)
    check(ca.c == 2 and state(A) == MS.SUCCESS, "2 riders on the ledge: success")
end)

test("act 3: late joiner gets the parked crane and the open gates; the leader leaving keeps the crane; reset = new layout", function()
    local w, A, B, Cc = world_with({ "A", "B", "C" })
    local P = A.env.REITZ_POINTS
    enter(w, A, 3); enter(w, B, 3)
    w:seconds(4)
    at(A, P.console_1)
    w:step(2)
    ride(B, cranes(B)[1], P)
    pass_gate(w, A, B, 1, 1, P)
    steer_y(w, A, 1, { B }, P)                      -- up through gate 1 to locked gate 2
    local c1 = cranes(A)[1]
    local L1 = lay(A, 1)
    check(c1.y + PTOP + HEAD <= P.gate_y[2] - GH and c1.y > P.gate_y[1], "crane 1 parked under gate 2 (y " .. c1.y .. ")")
    w:seconds(1.2)
    local packed = ctx_of(A).p
    check(packed > 0 and ctx_of(A).g == 1, "the leader parked it in p; gate 1 open in g")
    enter(w, Cc, 3)
    w:step(5)
    local cc = cranes(Cc)[1]
    check(math.abs(cc.x - c1.x) <= 10 and math.abs(cc.y - c1.y) <= 10, "late joiner starts from the parked position")
    local gC = ctx_of(Cc).objs.gates[1]
    check(gate_open(Cc, 1, 1) and not gate_open(Cc, 1, 2), "late joiner: gate 1 open, gate 2 locked")
    check((raw(gC[1].box).header.gfx.node.flags & C.GRAPH_RENDER_INVISIBLE) ~= 0
        and (raw(gC[2].box).header.gfx.node.flags & C.GRAPH_RENDER_INVISIBLE) == 0, "late joiner: box 1 gone, box 2 there")
    check(lay(Cc, 1).pattern == L1.pattern, "same layout everywhere (round " .. ctx_of(Cc).r .. ")")
    -- the leader (and operator) leaves: the crane stays, B leads
    w:disconnect(A)
    w:step(5)
    local cb = ctx_of(B)
    check(cb.isLeader, "B leads")
    check(math.abs(cranes(B)[1].x - c1.x) < 1 and cranes(B)[1].y == c1.y, "crane 1 stays where A left it")
    check(state(B) == MS.ACTIVE, "B + C keep going")
    -- B drives from where it is
    at(B, P.console_1)
    w:step(4)
    hold(w, B, 64, 0, 60)
    check(cranes(B)[1].x < c1.x, "B steers west (x " .. cranes(B)[1].x .. ")")
    w:step(3)
    check(cranes(Cc)[1].x == cranes(B)[1].x, "C sees it")
    -- /mission reset: back to the start, gates locked again, a new layout
    local r0 = cb.r
    Sim.cmd(Cc, "mission", "reset")
    w:seconds(4)
    check(cb.r == r0 + 1 and cb.g == 0, "new round, gates locked")
    check(cranes(B)[1].y == PBOT and cranes(Cc)[1].y == PBOT and cranes(B)[1].x == 1050, "reset: crane 1 back on the floor")
    check(lay(B, 1).pattern ~= L1.pattern, "the gaps moved (pattern " .. L1.pattern .. " -> " .. lay(B, 1).pattern .. ")")
    local gB = ctx_of(B).objs.gates[1][1]
    check(raw(gB.box).oPosX == lay(B, 1).sensorX[1] and (raw(gB.box).header.gfx.node.flags & C.GRAPH_RENDER_INVISIBLE) == 0,
        "the ! box moved to the new layout and is back")
end)

test("act 3: a sensor hit the leader never got is sent again; the operator can steer through at once", function()
    local w, A, B, Cc = world_with({ "A", "B", "C" })
    local P = A.env.REITZ_POINTS
    for _, c in ipairs({ A, B, Cc }) do enter(w, c, 3) end
    w:seconds(4)
    at(B, P.console_1)                               -- B drives, C rides, A leads
    w:step(4)
    check(ctx_of(B).loc.operating, "B drives")
    ride(Cc, cranes(Cc)[1], P)
    steer_y(w, B, 1, { Cc }, P)
    local s = d3(B).sensorOf(lay(B, 1), 1)
    steer_x(w, B, 1, math.max(d3(B).lanes[1].xMin, math.min(d3(B).lanes[1].xMax, s.x)), { Cc }, P)
    A.hooks[C.HOOK_ON_PACKET_RECEIVE] = {}          -- the leader hears nothing
    hit_box(w, Cc, 1, 1, P)
    w:step(3)
    check(ctx_of(A).g == 0, "the leader missed the hit")
    check(gate_open(B, 1, 1), "the operator heard it: gate 1 open for steering")
    steer_x(w, B, 1, lay(B, 1).gapX[1], { Cc }, P)
    hold(w, B, 0, 64, 30, { Cc }, 1, P)
    check(cranes(B)[1].y + PTOP > P.gate_y[1] - GH - HEAD, "B steers up into gate 1's gap")
    w:disconnect(A)
    w:step(3)
    check(ctx_of(B).isLeader and ctx_of(B).g == 0, "B leads; g not written yet")
    w:seconds(3.2)
    check(ctx_of(B).g == 1, "C's resend landed: gate 1 in g")
end)

test("act 3: a player leaving pauses it; the round's star needs the riders on the ledge, not the operator", function()
    local w, A, B = world_with({ "A", "B" })
    local P = A.env.REITZ_POINTS
    enter(w, A, 3); enter(w, B, 3)
    w:seconds(4)
    at(A, P.console_1)
    w:step(3)
    check(ctx_of(A).c == 0, "nobody on the ledge")
    w:warp(B, HUB, 1, 0)
    w:step(5)
    check(state(A) == MS.WAITING, "B left: waiting")
    check(not ctx_of(A).loc.operating, "no driving while waiting")
end)

test("act 3: D-pad Down into the lab (not while driving); the operator's crane marker sticks to the screen edge", function()
    local w, A, B = world_with({ "A", "B" })
    local P = A.env.REITZ_POINTS
    enter(w, A, 3); enter(w, B, 3)
    w:seconds(4)
    at(B, { x = 2400, y = 0, z = -6400 })
    w:step(2)
    check(Sim.hud_has(B, "D%-pad Down: into the Robotics Lab"), "panel hint outside the lab")
    Sim.cmd(B, "mission", "start")
    w:step(2)
    check(d3(B).inLab(B.pos), "/mission start: into the lab too")
    at(A, P.console_1)
    w:step(3)
    local x0 = A.pos.x
    A.pressed = C.D_JPAD
    w:step(2)
    check(A.pos.x == x0 and Sim.hud_has(A, "You are driving a crane"), "no teleport while driving")
    -- the crane off screen: an edge arrow labelled CRANE 1 (not hidden like the others)
    A.project = function(pos) return false, -300, 50 end
    w:step(2)
    local edge = false
    for _, d in ipairs(A.draw) do
        if d.k == "text" and d.s == "CRANE 1" and d.x < 200 then edge = true end
    end
    A.project = nil
    check(edge, "CRANE 1 edge label drawn while the crane is off screen")
    local rects = 0
    for _, d in ipairs(A.draw) do if d.k == "rect" then rects = rects + 1 end end
    check(rects >= 15, "the side view draws the lane (" .. rects .. " rects)")
end)

---------------------------------------------------------------------------------------------
-- whole mod: /campus, Study Group invite, coming soon, HUD
---------------------------------------------------------------------------------------------
test("whole mod: /campus reitz 3 starts the co-op lab; invite for act 1; coming-soon act 4; every HUD state renders", function()
    local w = Sim.new({ files = Sim.ALL_FILES, built = { [HUB] = true, [C.LEVEL_BOB] = true, [WF] = true }, stars = 2 })
    local H, F = install_stick(w:connect("Host")), install_stick(w:connect("Friend"))
    H.strStorage.friend = "josh"; F.strStorage.friend = "anh"
    w:step(3)
    w:warp(H, HUB, 1, 0); w:warp(F, HUB, 1, 0)
    w:step(40)
    -- door 2 is open with 2 stars
    w:warp(H, WF, 1, 1)
    w:step(5)
    check(Sim.find(F.popups, "Host.-started REITZ & ENGINEERING act 1: ROOFTOP OF THE REITZ") ~= nil, "Study Group invite")
    F.pressed = C.U_JPAD
    w:step(3)
    check(F.level == WF and F.act == 1, "D-pad Up joins act 1")
    w:seconds(4)
    check(state(H) == MS.ACTIVE and ctx_of(H).n == 2, "act 1 running for both")
    Sim.cmd(H, "campus", "reitz 3")
    w:step(5)
    check(H.act == 3 and F.act == 3, "/campus reitz 3 moves everyone")
    w:seconds(4)
    check(state(H) == MS.ACTIVE and ctx_of(H).def.id == "reitz_robotics", "the lab runs with every file loaded")
    at(H, H.env.REITZ_POINTS.console_1)
    w:step(2)
    hold(w, H, 0, 64, 20)
    w:step(3)
    check(cranes(H)[1].y > PBOT and cranes(F)[1].y == cranes(H)[1].y, "crane moves on both clients")
    Sim.cmd(H, "mission", "")
    check(Sim.find(H.chat, "REMOTE ROBOTICS LAB %- 2P %(reitz_robotics act 3%): active") ~= nil, "/mission status")
    check(Sim.find(H.chat, "o 1  g 0") ~= nil, "/mission status shows the operator field (o 1 = Host)")
    -- a coming-soon act
    Sim.cmd(H, "campus", "reitz 4 me")
    w:step(5)
    check(Sim.hud_has(H, "COMING SOON %- WIND TUNNEL") and ctx_of(H) == nil, "act 4: coming soon, no mission")
    -- every act renders in every state without errors
    for _, act in ipairs({ 1, 2, 3 }) do
        w:warp(H, WF, 1, act); w:warp(F, WF, 1, act)
        w:seconds(5)
        H.project = function() return false, -300, 50 end    -- markers behind the camera: edge arrows
        w:step(2)
        H.project = nil
        check(#H.hudText > 0, "act " .. act .. " HUD")
    end
end)

---------------------------------------------------------------------------------------------
-- whole mod: the interior rom-hack camera in wf area 2 only (levels.lua SGL_STAGE_CAMERA[LEVEL_WF].area)
---------------------------------------------------------------------------------------------
test("whole mod: the Reitz Union interior (wf area 2) gets the interior camera; area 1 keeps the player's own", function()
    local w = Sim.new({ files = Sim.ALL_FILES, built = { [HUB] = true, [C.LEVEL_BOB] = true, [WF] = true }, stars = 2 })
    local H = install_stick(w:connect("Host"))
    local FIELDS = { { "zoomed_in_dist", "inDist" }, { "zoomed_out_dist", "outDist" }, { "zoomed_in_height", "inHeight" },
        { "zoomed_out_height", "outHeight" }, { "collisions", "collisions" } }
    H.cam = { inDist = 900, outDist = 1400, inHeight = 300, outHeight = 450, collisions = 0 }
    for _, f in ipairs(FIELDS) do
        H.stubs["camera_romhack_get_" .. f[1]] = function() return H.cam[f[2]] end
        H.stubs["camera_romhack_set_" .. f[1]] = function(v)
            assert(math.type(v) == "integer", "camera value is an integer")
            H.cam[f[2]] = v
        end
    end
    local want = H.env.SGL_STAGE_CAMERA[WF]
    check(want ~= nil and want.area == 2, "SGL_STAGE_CAMERA[LEVEL_WF] is for area 2 only")
    w:step(3)
    w:warp(H, HUB, 1, 0); w:step(5)
    w:warp(H, WF, 1, 1); w:step(5)
    check(H.cam.inDist == 900 and H.cam.outHeight == 450 and H.cam.collisions == 0, "wf area 1 (campus): the player's camera")
    -- a door's instant warp: same level, area 2
    H.area = 2; w:refresh_views(); w:step(3)
    check(H.cam.inDist == want.inDist and H.cam.outDist == want.outDist and H.cam.inHeight == want.inHeight
        and H.cam.outHeight == want.outHeight and H.cam.collisions == 1, "inside the Reitz Union: the interior camera, collision on")
    H.area = 1; w:refresh_views(); w:step(3)
    check(H.cam.inDist == 900 and H.cam.outDist == 1400 and H.cam.outHeight == 450 and H.cam.collisions == 0,
        "back out on the campus: the player's own camera restored")
    H.area = 2; w:refresh_views(); w:step(3)
    w:warp(H, HUB, 1, 0); w:step(3)
    check(H.cam.inDist == 900 and H.cam.collisions == 0, "leaving the stage from inside: restored")
end)

print(string.format("\n%d checks passed, %d failed", passed, failed))
os.exit(failed == 0 and 0 or 1)
