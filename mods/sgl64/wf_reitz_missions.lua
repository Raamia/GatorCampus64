-- Super Gatorlator 64: Reitz Union & Engineering Quad (course 2, LEVEL_WF, hub door 2 "The Hub") missions,
-- on the framework in sgl_mission.lua (docs/game_design.md 7.2, docs/flow.md 5).
--
--   act 1  ROOFTOP OF THE REITZ        reach (solo): climb the J. Wayne Reitz Union from the ravine side:
--                                      brick terraces -> sunshade awnings -> ballroom roof -> podium roof ->
--                                      the WINDOW-WASHER LIFT (a Lua platform on the tower's west face, its
--                                      deck 0.1 m from the parapet at the top; the cable pole and the tower's
--                                      east ledges also work) -> tower roof -> elevator penthouse (28.8 m),
--                                      where the mission spawns the star (the stage build places no
--                                      level-script star: data/uf/reitz_points.json stars = []). If
--                                      build_stage.py STAGE_STARS ever gets the reitz_eng act 1 entry
--                                      (landmark reitz_union, spot roof_star), set levelStar = true below.
--   act 2  MEAL SWIPE TOKENS           tokens (solo or together): 8 meal-swipe tokens (Gator Corner patio,
--                                      Engineering Plaza sculpture, Liberty Pond fountain, Bookstore awning,
--                                      ravine boardwalk, Weil Hall's roof ridge (24 m), Malachowsky's glass
--                                      stair (12 m), cooling-tower catwalk). Progress is shared by everyone in
--                                      the act; the star pops out where the 8th token was found.
--   act 3  REMOTE ROBOTICS LAB - 2P    co-op cranes (2+ players, design 7.2 act 2): in Malachowsky Hall's
--                                      7-storey atrium, a player on an operator console steers a crane
--                                      platform with the stick; the riders on it go up through 5 sensor
--                                      gates to the star ledge (28 m). Each gate is LOCKED until a rider
--                                      jumps and hits its "!" sensor box (hanging under the gate), then the
--                                      operator steers the crane under the gate's narrow gap (it moves every
--                                      round). Circling Amps guard two floors. The crane moves only while
--                                      someone is on its console, so one player cannot do it alone.
--                                      2-3 players: one crane, 1 / 2 riders must reach the ledge; 4+: a
--                                      second crane (east lane, east console) and 2 riders (3 with 5+); a
--                                      crane carries at most ceil(riders needed / cranes) riders up.
--                                      D-pad Down (or /mission start) takes you into the lab from anywhere.
--   acts 4-6 "COMING SOON - ..." in course.lua (design 7.2 acts 3, 4, 6): free roam, no star.
-- Act order (course.lua header): playable acts 1..3 with no gap, the solo-able ones first. Every star is
-- spawned by its mission (spawn_default_star from the controller loop, star id = act - 1): the level
-- script must NOT place a bhvStar for acts 2 and 3 (act 1: see above). Each mission checks the stage
-- geometry first (probes on REITZ_POINTS): if levels/wf is not the real Reitz stage they stay offline
-- (/mission force overrides).
--
-- File name: coopdx loads a mod's files in strcmp order of their names. This file must load AFTER
-- sgl_mission.lua (it registers missions at load, like swamp_missions.lua), and it sorts after
-- swamp_missions.lua too ("wf" = the stage's level slot, levels/wf). A name such as "reitz_missions.lua"
-- would load before sgl_mission.lua, when sgl_mission_register does not exist yet.
--
-- Networking of act 3 (design 7.2 risk "rider jitter"): the LEADER assigns each crane's operator (the
-- player on its console, kept while they stay on it; smallest globalIndex when several step on at once)
-- in the synced field o, so two players at the edge of one console can never both steer. Only that
-- player's client moves its copy from the local stick (camera-relative left/right, stick up/down = crane
-- up/down), keeps it out of the closed gates, and streams the position unreliably at 15 Hz
-- ({ sgl = "rlab" }); every other client accepts only the assigned operator's stream and glides its copy
-- toward the latest position (no extrapolation, so a rider is never carried past where the operator put
-- the crane). The leader parks the positions in the synced mission fields once a second (late joiners, a
-- new operator, a new leader start from there). Sensor hits are reliable events ("sens"); the leader ORs
-- them into g. Platforms are local Lua objects with the vanilla checkerboard-platform collision; each
-- frame they set oVel = their displacement, so the engine carries the player standing on them
-- (apply_platform_displacement).

---------------------------------------------------------------------------------------------
-- ALL Reitz mission coordinates, in game units (area 1 of LEVEL_WF). Swap values here only.
-- Source: data/uf/reitz_points.json (written by tools/campus/build_stage.py reitz_eng from the BUILT
-- collision; "game" = [X, floor Y, Z]; its actN_ keys use the DESIGN act numbers: design 5 = course act 2,
-- design 2 = course act 3), point names in the comments. The JSON follows the stage's landmark modules
-- (tools/campus/landmarks/reitz_reitz_union.py, reitz_malachowsky.py, reitz_weil_eng_clocktower.py) through
-- the stages.json transform of the reitz_eng window (centre (-470, -293) m):
--   X = (x + 470) * 100,  Y = z * 100,  Z = -(y + 293) * 100.
-- Y is the FLOOR (Mario's feet) at the point; the ground is Y 0 everywhere (the campus is flat).
-- tools/luatest/check_reitz_points.py fails on drift > 0.5 m against the JSON (or the modules without
-- it); --print prints fresh values.
---------------------------------------------------------------------------------------------
REITZ_POINTS = {
    -- act 1: the J. Wayne Reitz Union (module reitz_union)
    roof_goal      = { x = 3350,  y = 2880, z = -3000 },   -- rooftop_goal_penthouse: elevator penthouse roof, 28.8 m
    roof_star      = { x = 3350,  y = 3000, z = -3000 },   -- rooftop_star_target: the act 1 star, 1.2 m up
    roof_zone      = { x0 = -5350, x1 = 11050, z0 = -5150, z1 = 4400 },  -- act1_rooftop.climb_zone (footprint bbox)
    climb_start    = { x = -2939, y = 150,  z = -875 },    -- rooftop_start_ravine_terrace (1.5 m, ravine side)
    climb_awning   = { x = -2210, y = 1110, z = -1156 },   -- rooftop_climb_05: the last copper awning (11.1 m)
    ballroom_roof  = { x = -2081, y = 1320, z = -1494 },   -- rooftop_climb_06: ballroom roof (13.2 m)
    podium_roof    = { x = 1000,  y = 1760, z = -3200 },   -- rooftop_podium_west (17.6 m)
    tower_roof     = { x = 3400,  y = 2640, z = -3700 },   -- rooftop_tower_roof_center (deck 26.4 m)
    lift_bottom    = { x = 1270,  y = 1760, z = -3100 },   -- rooftop_lift_bottom: window-washer lift track foot (podium roof)
    lift_top       = { x = 1270,  y = 2700, z = -3100 },   -- rooftop_lift_top: track top = tower parapet top (27.0 m)

    -- act 2: the eight meal-swipe tokens (act5_meal_swipe_tokens.red_coins, design order; floor points, the
    -- token floats 1 m above)
    tokens = {
        { x = -17800, y = 76,   z = -17600, name = "GATOR CORNER PATIO" },      -- token_gator_corner_patio (patio table, 0.76 m)
        { x = -11597, y = 400,  z = -22231, name = "ENGINEERING PLAZA SCULPTURE" }, -- token_engineering_plaza_sculpture (girder, 4.0 m)
        { x = 10063,  y = 30,   z = 4281,   name = "LIBERTY POND FOUNTAIN" },   -- token_liberty_pond_fountain (float, 0.3 m)
        { x = 6051,   y = 300,  z = 6092,   name = "BOOKSTORE AWNING" },        -- token_bookstore_awning (east entrance canopy, 3.0 m)
        { x = -7283,  y = 45,   z = 6990,   name = "RAVINE BOARDWALK" },        -- token_ravine_boardwalk (deck 0.45 m)
        { x = 725,    y = 2400, z = -24542, name = "WEIL ROOF RIDGE" },         -- token_weil_roof_ridge (Weil roof run, 24 m)
        { x = 4075,   y = 1200, z = 21685,  name = "MALACHOWSKY GLASS STAIR" }, -- token_malachowsky_glass_stair (glass box, 12 m)
        { x = -3667,  y = 1000, z = -14451, name = "COOLING TOWER CATWALK" },   -- token_cooling_tower_catwalk (roof deck, 10.0 m)
    },
    token_star     = { x = 8500,  y = 0,    z = -10200 },  -- token_star_north_lawn: North Lawn hub (fallback star spot)

    -- act 3: Malachowsky Hall's atrium (module malachowsky_hall)
    atrium         = { x0 = 400, x1 = 3000, z0 = 22400, z1 = 24100, y = 0, ceil = 3220 },  -- act2_robotics_lab.atrium_box
    ledge          = { x0 = 400, x1 = 3000, z0 = 23750, z1 = 24100, y = 2800 },            -- act2_robotics_lab.star_ledge_box (28.0 m)
    ledge_star     = { x = 1700,  y = 2800, z = 23925 },   -- robotics_star_ledge: L7 ledge floor (28.0 m)
    robotics_star  = { x = 1700,  y = 2920, z = 23925 },   -- robotics_star_target: the act 3 star, 1.2 m over the ledge
    atrium_floor   = { x = 1700,  y = 0,    z = 23250 },   -- robotics_atrium_center (the star rises from here)
    console_1      = { x = 1000,  y = 0,    z = 22650 },   -- robotics_console (west)
    console_2      = { x = 2400,  y = 0,    z = 22650 },   -- robotics_console mirrored across the atrium centre (east)
    lab_entry      = { x = 1700,  y = 0,    z = 22700 },   -- atrium centre x, console row + 0.5 m: D-pad Down lands here
    crane_z        = 23577,                                -- crane plane: ledge north edge (23750) - platform half depth (153) - 20
    gate_y         = { 500, 960, 1420, 1880, 2340 },       -- malachowsky markers.levels_m floors 5.0 / 9.6 / 14.2 / 18.8 / 23.4 m (sensor gates)
}

-- which act each mission is (star id = act - 1). Keep in step with the act names in course.lua
-- (tools/luatest/test_reitz_missions.lua checks that every mission title equals its course.lua act name).
REITZ_MISSION_ACTS = { rooftop = 1, tokens = 2, robotics = 3 }

---------------------------------------------------------------------------------------------
if sgl_mission_register == nil then
    log_to_console("[SGL] wf_reitz_missions.lua: sgl_mission.lua is not loaded", CONSOLE_MESSAGE_ERROR)
    return
end

local P = REITZ_POINTS

local function up(p, dy)
    return { x = p.x, y = p.y + dy, z = p.z }
end

local function probe(p, name)
    return { x = p.x, y = p.y, z = p.z, name = name }
end

local function alive(m)
    return m ~= nil and m.health > 0xFF
end

local function dist2_xz(p, q)
    local dx, dz = p.x - q.x, p.z - q.z
    return dx * dx + dz * dz
end

local function popcount(v)
    local n = 0
    while v > 0 do
        n = n + (v & 1)
        v = v >> 1
    end
    return n
end

local function clamp(v, lo, hi)
    if v < lo then return lo end
    if v > hi then return hi end
    return v
end

local function set_hidden(o, hidden)
    local flags = o.header.gfx.node.flags
    if hidden then
        o.header.gfx.node.flags = flags | GRAPH_RENDER_INVISIBLE
    else
        o.header.gfx.node.flags = flags & ~GRAPH_RENDER_INVISIBLE
    end
end

local function obj_ok(o, id)
    if o == nil or o.activeFlags == ACTIVE_FLAG_DEACTIVATED then return false end
    local r = obj_has_behavior_id(o, id)   -- an integer in v1.5.1 (0 is truthy in Lua)
    return r == true or r == 1
end

-- local index of the connected player with this globalIndex (or nil)
local function local_of_gi(gi)
    if gi == nil or gi < 0 then return nil end
    for i = 0, MAX_PLAYERS - 1 do
        local np = gNetworkPlayers[i]
        if np ~= nil and np.connected and np.globalIndex == gi then return i end
    end
    return nil
end

---------------------------------------------------------------------------------------------
-- Lua platforms (window-washer lift, robotics cranes): vanilla checkerboard-platform collision
-- (5.12 x 0.51 x 3.07 m at scale 1), moved by Lua. A record in sPlat (index in oBehParams & 0xFF) holds
-- the wanted position (x, y, z) or a drive(rec) function that sets it. Each frame the platform jumps
-- there and sets oVel = the displacement, so the engine carries the player standing on it.
---------------------------------------------------------------------------------------------
local PHX, PTOP, PBOT, PHZ = 256, 26, 25, 153     -- half width (x), deck top, underside, half depth (z)
local PLAT_SNAP = 200            -- a jump farther than this per frame (reset, late join) carries nobody
local sPlat = {}
local sPlatNext = 0

local function plat_init(o)
    o.header.gfx.shadowInvisible = true
    o.oFlags = OBJ_FLAG_UPDATE_GFX_POS_AND_ANGLE | OBJ_FLAG_ACTIVE_FROM_AFAR
    o.collisionData = gGlobalObjectCollisionData.checkerboard_platform_seg8_collision_0800D710
    o.oCollisionDistance = 4000
    o.oDrawingDistance = 20000
    o.oIntangibleTimer = -1
end

local function plat_loop(o)
    local rec = sPlat[o.oBehParams & 0xFF]
    if rec == nil then
        obj_mark_for_deletion(o)
        return
    end
    if rec.drive ~= nil then rec.drive(rec) end
    local dx, dy, dz = rec.x - o.oPosX, rec.y - o.oPosY, rec.z - o.oPosZ
    if math.abs(dx) > PLAT_SNAP or math.abs(dy) > PLAT_SNAP or math.abs(dz) > PLAT_SNAP then
        dx, dy, dz = 0, 0, 0
    end
    o.oVelX, o.oVelY, o.oVelZ = dx, dy, dz
    o.oPosX, o.oPosY, o.oPosZ = rec.x, rec.y, rec.z
    load_object_collision_model()
end

id_bhvSglReitzPlatform = hook_behavior(nil, OBJ_LIST_SURFACE, true, plat_init, plat_loop, "bhvSglReitzPlatform")

-- -> the record (its object is rec.o)
local function spawn_platform(x, y, z, sx, sz, drive)
    sPlatNext = (sPlatNext % 250) + 1
    local idx = sPlatNext
    local rec = { x = x, y = y, z = z, drive = drive, idx = idx }
    sPlat[idx] = rec
    rec.o = spawn_non_sync_object(id_bhvSglReitzPlatform, E_MODEL_CHECKERBOARD_PLATFORM, x, y, z, function(obj)
        obj.oBehParams = idx
        obj_scale_xyz(obj, sx or 1, 1, sz or 1)
    end)
    return rec
end

-- visual-only scenery (sensor-gate bars, "!" sensor boxes): no billboard, no collision, no interaction
local function prop_init(o)
    -- Gate meshes are stretched by several storeys; their vanilla square shadows scale too.
    o.header.gfx.shadowInvisible = true
    o.oFlags = OBJ_FLAG_UPDATE_GFX_POS_AND_ANGLE | OBJ_FLAG_ACTIVE_FROM_AFAR
    o.oDrawingDistance = 20000
    o.oIntangibleTimer = -1
end

local function prop_loop(o)
end

id_bhvSglReitzProp = hook_behavior(nil, OBJ_LIST_DEFAULT, true, prop_init, prop_loop, "bhvSglReitzProp")

---------------------------------------------------------------------------------------------
-- TOKENS kind (act 2): spec = { tokens = { { x, y (floor), z, name }, ... }, radius, below, above, lift
-- (draw height over the floor), scale }. Anyone in the act collects a token by touching it; the collector
-- sends a reliable "tok" event, the leader ORs it into f (found bits) and p (count) and remembers the
-- token found last in x (the star pops out there, starAt); all found -> SUCCESS.
-- An event that a leaving leader never applied is sent again after 3 s (the next leader applies it).
---------------------------------------------------------------------------------------------
local function kind_tokens(spec)
    local K = {}
    local toks = spec.tokens
    local nTok = #toks
    local ALL = (1 << nTok) - 1
    local R, BELOW, ABOVE, LIFT = spec.radius or 160, spec.below or 100, spec.above or 250, spec.lift or 100
    local RESEND = 90

    local function touching(p, t)
        return dist2_xz(p, t) <= R * R and p.y >= t.y - BELOW and p.y <= t.y + ABOVE
    end
    K.touching = touching

    local function found(ctx)
        return (ctx.f | (ctx.loc.mine or 0) | (ctx.loc.seen or 0)) & ALL
    end
    K.found = found

    local function sound_for(n)
        return SOUND_MENU_COLLECT_RED_COIN + (clamp(n - 1, 0, 7) << 16)
    end

    -- nearest token not found yet (local view) -> index, distance in m
    local function nearest(ctx, pos)
        local got = found(ctx)
        local best, bestD = nil, nil
        for i, t in ipairs(toks) do
            if (got & (1 << (i - 1))) == 0 then
                local dx, dy, dz = t.x - pos.x, t.y - pos.y, t.z - pos.z
                local d = math.sqrt(dx * dx + dy * dy + dz * dz)
                if bestD == nil or d < bestD then best, bestD = i, d end
            end
        end
        return best, bestD and math.floor(bestD / 100 + 0.5) or nil
    end
    K.nearest = nearest

    K.onReset = function(ctx)
        ctx:set("f", 0)
        ctx:set("p", 0)
        ctx:set("x", 0)
    end

    K.leaderTick = function(ctx)
        if (ctx.f & ALL) == ALL then ctx:succeed() end
    end

    K.onEvent = function(ctx, ev, data)
        if ev ~= "tok" or data.r ~= ctx.r or math.type(data.i) ~= "integer" or data.i < 1 or data.i > nTok then return end
        local bit = 1 << (data.i - 1)
        if ctx.isLeader and (ctx.s == SGL_MS_ACTIVE or ctx.s == SGL_MS_INTRO) and (ctx.f & bit) == 0 then
            local f = ctx.f | bit
            ctx:set("f", f)
            ctx:set("p", popcount(f & ALL))
            if (f & ALL) == ALL then
                ctx:set("x", data.i)       -- written before the state: every client knows where the star goes
                ctx:succeed()
            end
        end
        local L = ctx.loc
        if data.gi ~= gNetworkPlayers[0].globalIndex and ((L.seen or 0) & bit) == 0 and ((L.mine or 0) & bit) == 0 then
            L.seen = (L.seen or 0) | bit
            local n = popcount(found(ctx))
            sgl_hud_toast(string.format("%s found the %s token! %d/%d", data.nm or "?", toks[data.i].name, n, nTok), 3, SGL_HUD_GREEN)
            play_sound(sound_for(n), gGlobalSoundSource)
            L.expandUntil = ctx.age + 150
        end
    end

    -- the star pops out of the token found last (x, synced by the leader with the final count): 1.5 m over
    -- its floor, dropping in from 10 m above. Unknown for 2 s (a lost write): the North Lawn fallback.
    K.starAt = function(ctx)
        local t = toks[ctx.x]
        if t == nil then
            if ctx.stateAge < 60 then return nil end
            return up(spec.fallbackStar, 150), up(spec.fallbackStar, 1500)
        end
        return up(t, 150), up(t, 1000)
    end

    K.spawnLocal = function(ctx)
        ctx.objs.tokens = {}
        for i, t in ipairs(toks) do
            ctx.objs.tokens[i] = spawn_non_sync_object(id_bhvSglMissionFx, E_MODEL_RED_COIN, t.x, t.y + LIFT, t.z,
                function(obj) obj_scale(obj, spec.scale or 1.5) end)
        end
    end

    K.localTick = function(ctx)
        local L = ctx.loc
        L.mine = L.mine or 0
        L.seen = L.seen or 0
        L.sentAt = L.sentAt or {}
        local m = gMarioStates[0]
        if ctx.s == SGL_MS_ACTIVE and alive(m) then
            local got = found(ctx)
            for i, t in ipairs(toks) do
                local bit = 1 << (i - 1)
                if (got & bit) == 0 and touching(m.pos, t) then
                    L.mine = L.mine | bit
                    got = got | bit
                    L.sentAt[i] = ctx.age
                    local n = popcount(got)
                    play_sound(sound_for(n), gGlobalSoundSource)
                    sgl_hud_toast(string.format("%s token! %d/%d", t.name, n, nTok), 3, SGL_HUD_GOLD)
                    L.expandUntil = ctx.age + 150
                    ctx:send("tok", { i = i, nm = gNetworkPlayers[0].name })
                end
            end
            -- not in the synced bits yet after 3 s (the leader left before applying it): send it again
            for i = 1, nTok do
                local bit = 1 << (i - 1)
                if (L.mine & bit) ~= 0 and (ctx.f & bit) == 0 and L.sentAt[i] ~= nil and ctx.age - L.sentAt[i] >= RESEND then
                    L.sentAt[i] = ctx.age
                    ctx:send("tok", { i = i, nm = gNetworkPlayers[0].name })
                end
            end
        end
        local got = found(ctx)
        for i, o in ipairs(ctx.objs.tokens or {}) do
            if obj_ok(o, id_bhvSglMissionFx) then set_hidden(o, (got & (1 << (i - 1))) ~= 0) end
        end
    end

    K.panel = function(ctx)
        local got = found(ctx)
        local n = popcount(got)
        local i, d = nearest(ctx, gMarioStates[0].pos)
        local head = string.format("Tokens %d/%d", n, nTok)
        if i ~= nil then head = head .. string.format("   next: %s %d m", toks[i].name, d) end
        local lines = { { head, SGL_HUD_WHITE } }
        for k, t in ipairs(toks) do
            local have = (got & (1 << (k - 1))) ~= 0
            table.insert(lines, { (have and "+ " or "- ") .. t.name, have and SGL_HUD_GREEN or SGL_HUD_GREY, 0.26 })
        end
        return lines
    end

    K.hud = function(ctx)
        if ctx.s ~= SGL_MS_ACTIVE and ctx.s ~= SGL_MS_INTRO then return end
        local m = gMarioStates[0]
        local got = found(ctx)
        local near = nearest(ctx, m.pos)
        for i, t in ipairs(toks) do
            if (got & (1 << (i - 1))) == 0 and i ~= near then
                sgl_hud_marker({ x = t.x, y = t.y + LIFT + 60, z = t.z }, "", SGL_HUD_ORANGE, nil, true)
            end
        end
        if near ~= nil then
            local t = toks[near]
            sgl_hud_marker({ x = t.x, y = t.y + LIFT + 60, z = t.z }, t.name, SGL_HUD_GOLD, m)
        end
    end
    return K
end

---------------------------------------------------------------------------------------------
-- CRANES kind (act 3, co-op): spec = {
--   lanes = { { x0, x1, console = {x,y,z}, start = {x, y} }, ... },
--   gateY = { y, ... } (bar centres), gateHalf (half thickness), gapWidth, headroom (room kept for a rider
--   under a closed bar), sensorSize, sensorReach (how far the "!" box sits past the crane's travel),
--   gapSlots = { t, ... } (gap centres as fractions of the crane's travel), patterns = { { slot per gate },
--   ... } (one is picked per round and lane), planeZ, yMin, yMax, speedX, speedY (units per frame at full
--   stick), ledge = { x0, x1, z0, z1, y }, consoleRadius, consoleHeight, consoleSlack (an operator keeps the
--   console this far past its radius), drones = { { lane, y } }, minPlayers (2), entry = {x,y,z} (D-pad Down) }
-- Fields: a = cranes in use (1 for 2-3 players, 2 for 4+), f = riders needed on the ledge, c = riders on the
-- ledge now, p / x = parked position of crane 1 / 2 (packed, 0 = at its start), o = operators (5 bits per
-- crane: globalIndex + 1, 0 = nobody), g = gates opened (bit (k - 1) * 8 + (gate - 1)).
-- Gate g of lane k this round: a bar across the lane with a gapWidth gap at gapX[g] (never at the lane's
-- edge, so steering blind against a wall does not work) and a "!" sensor box hanging under the bar away
-- from the gap. Locked: the gap is shut too (red flames); the crane stops headroom below the bar, so a
-- rider standing on it has the "!" box just above their head; jumping into it opens the gate.
---------------------------------------------------------------------------------------------
SGL_REITZ_CRANE_PACKET = "rlab"
local CRANE_FIELDS = { "p", "x" }
local MARIO_H = 160              -- Mario's height (rider hits the "!" box with the top of his head)

local function kind_cranes(spec)
    local K = { minPlayers = spec.minPlayers or 2, tickAfterSuccess = true, spec = spec }
    local lanes = spec.lanes
    local nLanes = #lanes
    local nGates = #spec.gateY
    local GH, GAP = spec.gateHalf or 50, spec.gapWidth or 620
    local HEAD = spec.headroom or 280
    local BOX = spec.sensorSize or 102
    local REACH = spec.sensorReach or 100
    local SX, SY = spec.speedX or 9, spec.speedY or 7
    local X0 = spec.packX0 or 0
    local SLACK = spec.consoleSlack or 60
    local ledge = spec.ledge
    local slots = spec.gapSlots or { 0.17, 0.5, 0.83 }
    local patterns = spec.patterns or { { 3, 1, 2, 3, 1 } }
    local RESEND = 90

    -- The ROM-hack override forces BOSS_FIGHT back to ROM_HACK. Freeze the engine
    -- camera while driving and write an explicit, wide side view instead.
    local viewFields = { "pos", "focus", "curPos", "curFocus", "goalPos", "goalFocus" }
    local function copy_vec(dst, src)
        if dst ~= nil then dst.x, dst.y, dst.z = src.x, src.y, src.z end
    end
    local function restore_operator_camera(ctx)
        local L = ctx.operatorCamera
        if L == nil or not L.cameraTracking then return end
        local ls = gLakituState
        if ls ~= nil then
            for key, value in pairs(L.cameraView or {}) do copy_vec(ls[key], value) end
        end
        local cam = L.cameraObj
        if cam ~= nil and L.cameraMode ~= nil then set_camera_mode(cam, L.cameraMode, 1) end
        set_override_fov(0)
        if not L.cameraWasFrozen then camera_unfreeze() end
        ctx.operatorCamera = nil
    end

    local function track_operator_camera(ctx, k)
        ctx.operatorCamera = ctx.operatorCamera or {}
        local L = ctx.operatorCamera
        local m = gMarioStates[0]
        local cam = m ~= nil and m.area ~= nil and m.area.camera or nil
        local rec = ctx.objs.cranes and ctx.objs.cranes[k]
        local ls = gLakituState
        if cam == nil or rec == nil or rec.o == nil or ls == nil then return end
        if not L.cameraTracking then
            L.cameraTracking = true
            L.cameraObj, L.cameraMode = cam, cam.mode or cam.defMode
            L.cameraWasFrozen = camera_is_frozen()
            L.cameraView = {}
            for _, key in ipairs(viewFields) do
                local v = ls[key]
                if v ~= nil then L.cameraView[key] = { x = v.x, y = v.y, z = v.z } end
            end
        end
        camera_freeze()
        set_override_fov(75)
        -- Keep the full lane width and the next gate visible; pan up with the deck.
        local lane = lanes[k]
        local crane = ctx.loc.cranes and ctx.loc.cranes[k] or rec
        local cy = math.max(spec.yMin + 450, math.min(spec.yMax - 150, crane.y + 220))
        local focus = { x = (lane.x0 + lane.x1) / 2, y = cy, z = spec.planeZ }
        local pos = { x = focus.x, y = cy + 330, z = spec.atrium.z0 + 160 }
        for _, key in ipairs(viewFields) do
            copy_vec(ls[key], key:find("[Pp]os") and pos or focus)
        end
        copy_vec(cam.pos, pos)
        copy_vec(cam.focus, focus)
        cam.yaw = 0x8000
    end

    for _, lane in ipairs(lanes) do
        lane.xMin = lane.x0 + PHX + 20
        lane.xMax = lane.x1 - PHX - 20
    end
    K.lanes = lanes

    local function cranes_for(n)
        return clamp(n >= 4 and 2 or 1, 1, nLanes)
    end
    K.cranesFor = cranes_for

    local function need_for(n)
        return clamp(n - cranes_for(n), 1, 3)
    end
    K.needFor = need_for

    -- the gates of lane k in round r (the same on every client): { gapX = {...}, sensorX = {...},
    -- pattern = index, bars = { { x0, x1, y0, y1, gate, shutter } } } (shutter = the gap, solid while locked)
    local function layout(k, r)
        local lane = lanes[k]
        local pi = ((math.floor(r or 0) + 2 * (k - 1)) % #patterns) + 1
        local pat = patterns[pi]
        local lay = { gapX = {}, sensorX = {}, pattern = pi, bars = {} }
        for g, y in ipairs(spec.gateY) do
            local s = pat[((g - 1) % #pat) + 1]
            local cx = math.floor(lane.xMin + (lane.xMax - lane.xMin) * slots[s] + 0.5)
            lay.gapX[g] = cx
            -- the "!" box: past the crane's travel on the side away from the gap (a middle gap alternates)
            local east = s == 1 or (s ~= #slots and g % 2 == 0)
            lay.sensorX[g] = east and (lane.xMax + REACH) or (lane.xMin - REACH)
            local y0, y1 = y - GH, y + GH
            if cx - GAP / 2 > lane.x0 then
                table.insert(lay.bars, { x0 = lane.x0, x1 = cx - GAP / 2, y0 = y0, y1 = y1, gate = g })
            end
            if cx + GAP / 2 < lane.x1 then
                table.insert(lay.bars, { x0 = cx + GAP / 2, x1 = lane.x1, y0 = y0, y1 = y1, gate = g })
            end
            table.insert(lay.bars, { x0 = cx - GAP / 2, x1 = cx + GAP / 2, y0 = y0, y1 = y1, gate = g, shutter = true })
        end
        return lay
    end
    K.layout = layout

    local function gate_bit(k, g)
        return 1 << ((k - 1) * 8 + (g - 1))
    end
    K.gateBit = gate_bit

    -- opened gates of lane k: the synced bits (late joiners, resends) + hits seen as events, mine or
    -- another rider's, before the leader's write arrives (the operator can steer through at once)
    local function gate_open(ctx, k, g)
        local bit = gate_bit(k, g)
        local L = ctx.loc
        return ((ctx.g | (L.hitBits or 0) | (L.heard or 0)) & bit) ~= 0
    end
    K.gateOpen = gate_open

    -- the crane box (platform + a rider's headroom) at (x, y) overlaps a bar of its lane -> the bar, else nil
    local function blocked(lay, x, y, openFn)
        local ax0, ax1, ay0, ay1 = x - PHX, x + PHX, y - PBOT, y + PTOP + HEAD
        for _, b in ipairs(lay.bars) do
            if ax0 < b.x1 and b.x0 < ax1 and ay0 < b.y1 and b.y0 < ay1 then
                if not (b.shutter and openFn ~= nil and openFn(b.gate)) then return b end
            end
        end
        return nil
    end
    K.blocked = blocked

    local function pack(x, y)
        return 1 + clamp(math.floor((x - X0) / 10 + 0.5), 0, 1023) + clamp(math.floor(y / 10 + 0.5), 0, 1023) * 1024
    end
    local function unpack(v)
        v = v - 1
        return X0 + (v % 1024) * 10, (v // 1024) * 10
    end
    K.pack, K.unpack = pack, unpack

    local function on_console(p, c, slack)
        local r = spec.consoleRadius + (slack or 0)
        return dist2_xz(p, c) <= r * r and p.y >= c.y - 100 and p.y <= c.y + spec.consoleHeight
    end
    K.onConsole = on_console

    local function on_ledge(p)
        return p.x >= ledge.x0 and p.x <= ledge.x1 and p.z >= ledge.z0 and p.z <= ledge.z1
            and p.y >= ledge.y - 60 and p.y <= ledge.y + 400
    end
    K.onLedge = on_ledge

    local function on_crane(p, cr)
        return math.abs(p.x - cr.x) <= PHX + 40 and math.abs(p.z - spec.planeZ) <= PHZ + 40
            and p.y >= cr.y + PTOP - 60 and p.y <= cr.y + PTOP + 300
    end
    K.onCrane = on_crane

    local function in_lab(p)
        local a = spec.atrium
        return a ~= nil and p.x >= a.x0 and p.x <= a.x1 and p.z >= a.z0 and p.z <= a.z1 and p.y <= a.y + 400
    end
    K.inLab = in_lab

    local function cranes_now(ctx)
        return clamp(ctx.a > 0 and ctx.a or cranes_for(ctx.n), 1, nLanes)
    end

    local function need_now(ctx)
        return ctx.f > 0 and ctx.f or need_for(ctx.n)
    end

    -- a crane carries at most this many riders up (so with 4+ players the second crane is worth driving)
    local function cap_now(ctx)
        return math.max(1, math.ceil(need_now(ctx) / cranes_now(ctx)))
    end
    K.capNow = cap_now

    -- globalIndex of crane k's assigned operator (synced field o), or -1
    local function op_gi(ctx, k)
        return ((ctx.o >> ((k - 1) * 5)) & 31) - 1
    end
    K.opGi = op_gi

    -- the sensor box of gate g (bottom y, x, z)
    local function sensor_of(lay, g)
        return { x = lay.sensorX[g], y = spec.gateY[g] - GH - BOX, z = spec.planeZ }
    end
    K.sensorOf = sensor_of

    -- the next gate above crane k (deck below its bar) -> gate index, or nil above the last one
    local function next_gate(cr)
        for g, y in ipairs(spec.gateY) do
            if cr.y + PTOP <= y - GH + 1 then return g end
        end
        return nil
    end
    K.nextGate = next_gate

    -- local crane state (ctx.loc.cranes: positions this client shows; tx / ty = streamed target)
    local function crane_state(ctx)
        local L = ctx.loc
        if L.cranes == nil then
            L.cranes = {}
            for k, lane in ipairs(lanes) do
                local v = ctx:get(CRANE_FIELDS[k])
                local x, y = lane.start.x, lane.start.y
                if v > 0 then x, y = unpack(v) end
                x, y = clamp(x, lane.xMin, lane.xMax), clamp(y, spec.yMin, spec.yMax)
                L.cranes[k] = { x = x, y = y, tx = x, ty = y }
            end
        end
        return L.cranes
    end
    K.craneState = crane_state

    -- this round's gate layouts (local, recomputed when the round changes)
    local function layouts(ctx)
        local L = ctx.loc
        if L.lays == nil then
            L.lays = {}
            for k = 1, nLanes do L.lays[k] = layout(k, ctx.r) end
        end
        return L.lays
    end
    K.layouts = layouts

    local function riders_on(ctx, cr)
        local n = 0
        for _, li in ipairs(ctx.players) do
            local m = gMarioStates[li]
            if alive(m) and on_crane(m.pos, cr) then n = n + 1 end
        end
        return n
    end
    K.ridersOn = riders_on

    K.needPlayers = function(ctx) return K.minPlayers end

    K.onReset = function(ctx)
        ctx:set("a", cranes_for(ctx.n))
        ctx:set("f", need_for(ctx.n))
        ctx:set("c", 0)
        ctx:set("p", 0)
        ctx:set("x", 0)
        ctx:set("o", 0)
        ctx:set("g", 0)
    end

    -- leader: who drives which crane (kept while on the console + slack; else the smallest globalIndex
    -- standing on it), riders on the ledge, the parked positions, success
    K.leaderTick = function(ctx)
        local N = cranes_for(ctx.n)
        if N ~= ctx.a then ctx:set("a", N) end
        local need = need_for(ctx.n)
        if need ~= ctx.f then ctx:set("f", need) end
        local o = 0
        local live = ctx.s == SGL_MS_ACTIVE or ctx.s == SGL_MS_SUCCESS or ctx.s == SGL_MS_DONE
        for k = 1, nLanes do
            local pick = -1
            if live and k <= N then
                local c = lanes[k].console
                local cur = op_gi(ctx, k)
                local cli = local_of_gi(cur)
                local keep = false
                if cli ~= nil then
                    for _, li in ipairs(ctx.players) do
                        if li == cli then
                            local m = gMarioStates[li]
                            keep = alive(m) and on_console(m.pos, c, SLACK)
                        end
                    end
                end
                if keep then
                    pick = cur
                else
                    for _, li in ipairs(ctx.players) do
                        local m = gMarioStates[li]
                        if alive(m) and on_console(m.pos, c) then
                            local g = gNetworkPlayers[li].globalIndex
                            if pick < 0 or g < pick then pick = g end
                        end
                    end
                end
            end
            o = o | ((pick + 1) << ((k - 1) * 5))
        end
        if o ~= ctx.o then ctx:set("o", o) end
        local count = 0
        for _, li in ipairs(ctx.players) do
            local m = gMarioStates[li]
            if alive(m) and on_ledge(m.pos) then count = count + 1 end
        end
        if count ~= ctx.c then ctx:set("c", count) end
        if ctx.second and ctx.loc.cranes ~= nil then
            for k, cr in ipairs(ctx.loc.cranes) do
                local v = pack(cr.x, cr.y)
                if v ~= ctx[CRANE_FIELDS[k]] then ctx:set(CRANE_FIELDS[k], v) end
            end
        end
        if count >= need then ctx:succeed() end
    end

    -- a rider hit a gate's "!" box: the leader opens it for everyone
    K.onEvent = function(ctx, ev, data)
        if ev ~= "sens" or data.r ~= ctx.r or math.type(data.k) ~= "integer" or math.type(data.g) ~= "integer" then return end
        if data.k < 1 or data.k > nLanes or data.g < 1 or data.g > nGates then return end
        local bit = gate_bit(data.k, data.g)
        if ctx.isLeader and (ctx.s == SGL_MS_ACTIVE or ctx.s == SGL_MS_SUCCESS or ctx.s == SGL_MS_DONE)
            and (ctx.g & bit) == 0 then
            ctx:set("g", ctx.g | bit)
        end
        local L = ctx.loc
        local new = ((L.heard or 0) & bit) == 0 and ((L.hitBits or 0) & bit) == 0
        L.heard = (L.heard or 0) | bit
        if data.gi ~= gNetworkPlayers[0].globalIndex and new then
            sgl_hud_toast(string.format("%s hit the sensor: gate %d of crane %d is open!", data.nm or "?", data.g, data.k), 3,
                SGL_HUD_GREEN)
            play_sound(SOUND_GENERAL2_RIGHT_ANSWER, gGlobalSoundSource)
            L.expandUntil = ctx.age + 150
        end
    end

    local function stick(v)
        if math.abs(v) < 8 then return 0 end
        return clamp(v / 64, -1, 1)
    end

    local function bump_toast(ctx, key, text)
        local L = ctx.loc
        if L.bumpKey ~= key or ctx.age - (L.bumpToastAge or -1000) > 150 then
            L.bumpKey = key
            L.bumpToastAge = ctx.age
            sgl_hud_toast(text, 3, SGL_HUD_ORANGE)
        end
    end

    -- move crane k as its operator: x first, then y; a bar / a locked gap / too many riders stop the move
    local function drive(ctx, k, cr, m)
        local lay = layouts(ctx)[k]
        local L = ctx.loc
        local inp = L.input or {}
        local camYaw = inp.camYaw or ((m.faceAngle.y + 0x8000) & 0xFFFF)
        -- stick right = screen right (the engine's intendedYaw rule); only its east-west part moves the crane
        local rx = sins((atan2s(0, 64) + camYaw) & 0xFFFF)
        if math.abs(rx) >= 0.3 then L.dirX = rx > 0 and 1 or -1 end
        local dx = stick(inp.sx or 0) * SX * (L.dirX or 1)
        local dy = stick(inp.sy or 0) * SY
        local openFn = function(g) return gate_open(ctx, k, g) end
        local bump, why = nil, nil
        if dx ~= 0 then
            local nx = clamp(cr.x + dx, lanes[k].xMin, lanes[k].xMax)
            local b = blocked(lay, nx, cr.y, openFn)
            if b == nil then cr.x = nx else bump = b end
        end
        if dy > 0 and riders_on(ctx, cr) > cap_now(ctx) then
            dy = 0
            why = "heavy"
        end
        if dy ~= 0 then
            local ny = clamp(cr.y + dy, spec.yMin, spec.yMax)
            local b = blocked(lay, cr.x, ny, openFn)
            if b == nil then cr.y = ny else bump = b end
        end
        cr.tx, cr.ty = cr.x, cr.y
        if (bump ~= nil or why ~= nil) and ctx.age - (L.bumpAge or -100) > 30 then
            L.bumpAge = ctx.age
            play_sound(SOUND_MENU_CAMERA_BUZZ, gGlobalSoundSource)
            if why == "heavy" then
                local cap = cap_now(ctx)
                bump_toast(ctx, "heavy", string.format("Too heavy! Crane %d lifts %d rider%s - use the other crane", k, cap,
                    cap == 1 and "" or "s"))
            elseif bump.shutter or not gate_open(ctx, k, bump.gate) then
                bump_toast(ctx, "lock" .. bump.gate, string.format("Gate %d is locked: rider, jump into the ! box", bump.gate))
            else
                bump_toast(ctx, "gap" .. bump.gate, string.format("Gate %d: steer the crane under its gap", bump.gate))
            end
        end
    end

    local function send_pos(ctx, k, cr, reliable)
        network_send(reliable, { sgl = SGL_REITZ_CRANE_PACKET, ik = ctx.key, r = ctx.r, k = k,
            x = math.floor(cr.x + 0.5), y = math.floor(cr.y + 0.5), gi = gNetworkPlayers[0].globalIndex })
    end

    -- other clients' copies glide toward the streamed target (never past it)
    local function follow(cr)
        local maxStep = math.max(SX, SY) * 1.5
        local dx, dy = cr.tx - cr.x, cr.ty - cr.y
        local d = math.sqrt(dx * dx + dy * dy)
        if d <= maxStep or d > 1500 then
            cr.x, cr.y = cr.tx, cr.ty
        else
            cr.x, cr.y = cr.x + dx / d * maxStep, cr.y + dy / d * maxStep
        end
    end

    -- props: per lane and gate, the two bar pieces (stretched "!" outline boxes), the locked gap (two red
    -- flames) and the "!" sensor box; placed for this round's layout by place_props
    K.spawnLocal = function(ctx)
        ctx.objs.cranes, ctx.objs.consoles, ctx.objs.gates, ctx.objs.amps = {}, {}, {}, {}
        local cr = crane_state(ctx)
        for k, lane in ipairs(lanes) do
            ctx.objs.cranes[k] = spawn_platform(cr[k].x, cr[k].y, spec.planeZ, 1, 1, nil)
            local c = lane.console
            local o = spawn_non_sync_object(id_bhvSglButton, E_MODEL_PURPLE_SWITCH, c.x, c.y, c.z, nil)
            local fx = spawn_non_sync_object(id_bhvSglMissionFx, E_MODEL_RED_FLAME, c.x, c.y + 250, c.z,
                function(obj) obj_scale(obj, 4) end)
            ctx.objs.consoles[k] = { o = o, fx = fx, squish = SGL_BUTTON_SCALE }
            ctx.objs.gates[k] = {}
            for g = 1, nGates do
                local y = spec.gateY[g]
                local rec = { bars = {}, flames = {} }
                for j = 1, 2 do
                    rec.bars[j] = spawn_non_sync_object(id_bhvSglReitzProp, E_MODEL_EXCLAMATION_BOX_OUTLINE, lane.x0,
                        y - GH, spec.planeZ, nil)
                    rec.flames[j] = spawn_non_sync_object(id_bhvSglMissionFx, E_MODEL_RED_FLAME, lane.x0, y - 40,
                        spec.planeZ, function(obj) obj_scale(obj, 3) end)
                end
                rec.box = spawn_non_sync_object(id_bhvSglReitzProp, E_MODEL_EXCLAMATION_BOX, lane.x0, y - GH - BOX,
                    spec.planeZ, function(obj)
                        obj_scale(obj, BOX / 51)
                        obj.oAnimState = 3            -- the yellow "!" box
                    end)
                ctx.objs.gates[k][g] = rec
            end
        end
        -- sensor drones: vanilla circling Amps (radius 2 m) at mid-storey heights in each lane
        for _, d in ipairs(spec.drones or {}) do
            local lane = lanes[d.lane]
            if lane ~= nil then
                table.insert(ctx.objs.amps, spawn_non_sync_object(id_bhvCirclingAmp, E_MODEL_AMP, (lane.x0 + lane.x1) / 2,
                    d.y, spec.planeZ, function(obj) obj.oBehParams2ndByte = 0 end))
            end
        end
    end

    -- move the gate props to this round's layout (bars), show / hide the locked-gap flames and the boxes
    local function place_props(ctx)
        local L = ctx.loc
        local lays = layouts(ctx)
        for k, list in ipairs(ctx.objs.gates or {}) do
            local lay = lays[k]
            for g, rec in ipairs(list) do
                if not L.placed then
                    local j = 0
                    for _, b in ipairs(lay.bars) do
                        if b.gate == g and not b.shutter then
                            j = j + 1
                            local o = rec.bars[j]
                            if obj_ok(o, id_bhvSglReitzProp) then
                                o.oPosX = (b.x0 + b.x1) / 2
                                obj_scale_xyz(o, (b.x1 - b.x0) / 51, (b.y1 - b.y0) / 51, 2 * PHZ / 51)
                                set_hidden(o, false)
                            end
                        end
                    end
                    for jj = j + 1, 2 do
                        if obj_ok(rec.bars[jj], id_bhvSglReitzProp) then set_hidden(rec.bars[jj], true) end
                    end
                    for jj, fl in ipairs(rec.flames) do
                        if obj_ok(fl, id_bhvSglMissionFx) then
                            fl.oPosX = lay.gapX[g] + (jj == 1 and -1 or 1) * GAP / 4
                        end
                    end
                    if obj_ok(rec.box, id_bhvSglReitzProp) then rec.box.oPosX = lay.sensorX[g] end
                end
                local open = gate_open(ctx, k, g)
                for _, fl in ipairs(rec.flames) do
                    if obj_ok(fl, id_bhvSglMissionFx) then set_hidden(fl, open) end
                end
                if obj_ok(rec.box, id_bhvSglReitzProp) then set_hidden(rec.box, open) end
            end
        end
        L.placed = true
    end

    -- the local rider jumps into a locked gate's "!" box -> open it (event to the leader, resent after 3 s)
    local function sensor_tick(ctx, m, cranes)
        local L = ctx.loc
        L.hitBits = L.hitBits or 0
        L.hitAt = L.hitAt or {}
        local N = cranes_now(ctx)
        local live = ctx.s == SGL_MS_ACTIVE or ctx.s == SGL_MS_SUCCESS or ctx.s == SGL_MS_DONE
        if live and alive(m) then
            local lays = layouts(ctx)
            for k = 1, N do
                if on_crane(m.pos, cranes[k]) then
                    for g = 1, nGates do
                        if not gate_open(ctx, k, g) then
                            local s = sensor_of(lays[k], g)
                            if math.abs(m.pos.x - s.x) <= BOX / 2 + 40 and math.abs(m.pos.z - s.z) <= BOX / 2 + 40
                                and m.pos.y + MARIO_H >= s.y - 10 and m.pos.y <= s.y + BOX then
                                local bit = gate_bit(k, g)
                                L.hitBits = L.hitBits | bit
                                L.hitAt[bit] = ctx.age
                                play_sound(SOUND_GENERAL_OPEN_IRON_DOOR, gGlobalSoundSource)
                                sgl_hud_toast(string.format("Sensor hit! Gate %d is open - steer under the gap", g), 3, SGL_HUD_GOLD)
                                L.expandUntil = ctx.age + 150
                                ctx:send("sens", { k = k, g = g, nm = gNetworkPlayers[0].name })
                            end
                        end
                    end
                end
            end
        end
        for bit, at in pairs(L.hitAt) do
            if (ctx.g & bit) == 0 and ctx.age - at >= RESEND and ctx.s == SGL_MS_ACTIVE then
                L.hitAt[bit] = ctx.age
                local idx = 0
                while (1 << idx) ~= bit do idx = idx + 1 end
                ctx:send("sens", { k = idx // 8 + 1, g = idx % 8 + 1, nm = gNetworkPlayers[0].name })
            end
        end
    end

    K.localTick = function(ctx)
        local L = ctx.loc
        local cranes = crane_state(ctx)
        local live = ctx.s == SGL_MS_ACTIVE or ctx.s == SGL_MS_SUCCESS or ctx.s == SGL_MS_DONE
        local N = cranes_now(ctx)
        local m = gMarioStates[0]
        local me = gNetworkPlayers[0].globalIndex
        L.ops = L.ops or {}
        L.letGo = L.letGo or {}
        place_props(ctx)
        -- who operates which crane (the leader's assignment), and am I one of them
        local myK, waitK = nil, nil
        for k = 1, nLanes do
            local gi = (live and k <= N) and op_gi(ctx, k) or -1
            L.ops[k] = local_of_gi(gi)
            local onIt = live and k <= N and alive(m) and on_console(m.pos, lanes[k].console, SLACK)
            if not onIt then L.letGo[k] = nil end      -- off console k: B let go of it, armed again next time
            if onIt and gi == me and not L.letGo[k] then
                myK = k
            elseif onIt and on_console(m.pos, lanes[k].console) and not L.letGo[k] then
                waitK = k
            end
        end
        L.waitK = waitK
        -- operator input, captured in HOOK_BEFORE_MARIO_UPDATE (end of file) before the engine sees it
        local inp = L.input or {}
        if myK ~= nil and inp.b then
            L.letGo[myK] = true
            myK = nil
            sgl_hud_toast("You let go of the crane", 2, SGL_HUD_WHITE)
        end
        inp.b = false
        if myK ~= L.opK then
            if L.opK ~= nil and cranes[L.opK] ~= nil then send_pos(ctx, L.opK, cranes[L.opK], true) end
            if myK ~= nil then
                track_operator_camera(ctx, myK)
                play_sound(SOUND_GENERAL2_PURPLE_SWITCH, gGlobalSoundSource)
                L.dirX = nil
                L.sendAge = nil
            else
                restore_operator_camera(ctx)
            end
            L.opK = myK
        end
        if myK ~= nil then track_operator_camera(ctx, myK) else restore_operator_camera(ctx) end
        L.operating = myK ~= nil and alive(m)
        for k, cr in ipairs(cranes) do
            if k == myK then
                local px, py = cr.x, cr.y
                drive(ctx, k, cr, m)
                -- 15 Hz while it moves, at once when it stops (its resting spot), else once a second
                local unsent = cr.lastSentX ~= math.floor(cr.x + 0.5) or cr.lastSentY ~= math.floor(cr.y + 0.5)
                local moving = cr.x ~= px or cr.y ~= py
                if (unsent and (ctx.age % 2 == 0 or not moving)) or ctx.age - (L.sendAge or -100) >= 30 then
                    L.sendAge = ctx.age
                    cr.lastSentX, cr.lastSentY = math.floor(cr.x + 0.5), math.floor(cr.y + 0.5)
                    send_pos(ctx, k, cr, false)
                end
            else
                follow(cr)
            end
            local rec = ctx.objs.cranes and ctx.objs.cranes[k]
            if rec ~= nil then rec.x, rec.y, rec.z = cr.x, cr.y, spec.planeZ end
        end
        -- consoles: lit (red flame) while their crane is in use, blue flame + squished when someone drives
        for k, rec in ipairs(ctx.objs.consoles or {}) do
            local inUse = live and k <= N
            local held = inUse and L.ops[k] ~= nil
            if obj_ok(rec.o, id_bhvSglButton) then
                local target = held and SGL_BUTTON_PRESSED_Y or SGL_BUTTON_SCALE
                rec.squish = rec.squish + (target - rec.squish) * 0.35
                obj_scale_xyz(rec.o, SGL_BUTTON_SCALE, rec.squish, SGL_BUTTON_SCALE)
            end
            if obj_ok(rec.fx, id_bhvSglMissionFx) then
                if inUse then
                    local want = held and E_MODEL_BLUE_FLAME or E_MODEL_RED_FLAME
                    if rec.model ~= want then
                        obj_set_model_extended(rec.fx, want)
                        rec.model = want
                    end
                    set_hidden(rec.fx, false)
                else
                    set_hidden(rec.fx, true)
                end
            end
        end
        -- riding / on the ledge (local, for the HUD), and the "!" sensors
        L.riding = nil
        for k = 1, nLanes do
            if alive(m) and on_crane(m.pos, cranes[k]) then L.riding = k end
        end
        sensor_tick(ctx, m, cranes)
        local onLedge = alive(m) and on_ledge(m.pos)
        if onLedge and not L.wasOnLedge and live then
            sgl_hud_toast("On the star ledge!", 3, SGL_HUD_GREEN)
            play_sound(SOUND_MENU_COLLECT_SECRET, gGlobalSoundSource)
            L.expandUntil = ctx.age + 150
        end
        L.wasOnLedge = onLedge
    end

    K.onLeave = function(ctx)
        restore_operator_camera(ctx)
    end

    -- what crane k needs next -> text for the panel / diagram
    local function task_text(ctx, k, rider)
        local cr = ctx.loc.cranes and ctx.loc.cranes[k]
        if cr == nil then return "" end
        local g = next_gate(cr)
        if g == nil then
            if cr.y < spec.yMax then return "Past the gates: up to the star ledge!" end
            return "At the top: riders, step south onto the ledge!"
        end
        if not gate_open(ctx, k, g) then
            if rider then return string.format("Gate %d locked: jump into the ! box above", g) end
            return string.format("Gate %d locked: bring a rider under the ! box", g)
        end
        return string.format("Gate %d open: steer under the gap, then up", g)
    end
    K.taskText = task_text

    K.panel = function(ctx)
        local L = ctx.loc
        local N = cranes_now(ctx)
        local need = need_now(ctx)
        local lines = { { string.format("Riders on the star ledge: %d/%d", ctx.c, need), SGL_HUD_WHITE } }
        for k = 1, nLanes do
            if k <= N then
                local li = L.ops and L.ops[k]
                if li ~= nil then
                    table.insert(lines, { string.format("Crane %d: driven by %s", k, ctx:name_of(li)), SGL_HUD_GREEN, 0.28 })
                else
                    table.insert(lines, { string.format("Crane %d console: empty - stand on it!", k), SGL_HUD_ORANGE, 0.28 })
                end
            else
                table.insert(lines, { string.format("Crane %d: off (needs 4 players)", k), SGL_HUD_GREY, 0.26 })
            end
        end
        local m = gMarioStates[0]
        if L.operating and L.opK ~= nil then
            table.insert(lines, { string.format("You drive crane %d: stick moves it, B lets go", L.opK), SGL_HUD_GOLD, 0.28 })
            table.insert(lines, { task_text(ctx, L.opK, false), SGL_HUD_WHITE, 0.26 })
        elseif alive(m) and on_ledge(m.pos) then
            table.insert(lines, { "You are on the star ledge!", SGL_HUD_GREEN, 0.28 })
        elseif L.riding ~= nil then
            table.insert(lines, { string.format("Riding crane %d", L.riding), SGL_HUD_GOLD, 0.28 })
            table.insert(lines, { task_text(ctx, L.riding, true), SGL_HUD_WHITE, 0.26 })
        elseif L.waitK ~= nil then
            local li = L.ops and L.ops[L.waitK]
            table.insert(lines, { li ~= nil and string.format("Console %d: %s is driving", L.waitK, ctx:name_of(li))
                or string.format("Console %d: connecting...", L.waitK), SGL_HUD_GREY, 0.26 })
        elseif in_lab(m.pos) then
            table.insert(lines, { "Drive from a console, or ride a crane", SGL_HUD_GREY, 0.26 })
        else
            table.insert(lines, { "D-pad Down: into the Robotics Lab", SGL_HUD_GREY, 0.26 })
        end
        return lines
    end

    -- side view of crane k's lane (operator and riders), complementing the tracking camera once it
    -- climbs, so this is their view of it. Bars grey, a locked gap red, "!" boxes yellow, the crane blue,
    -- riders green (you white), Amps red, the star ledge gold.
    local function draw_lab(ctx, k)
        local L = ctx.loc
        local cr = L.cranes and L.cranes[k]
        if cr == nil then return end
        local lane = lanes[k]
        local lay = layouts(ctx)[k]
        local W, H = sgl_hud_setup(FONT_NORMAL)
        local top = ledge.y + 250
        local sc = math.min(130 / top, 80 / (lane.x1 - lane.x0))      -- about 64 x 130 (clear of the camera icon)
        local w, h = (lane.x1 - lane.x0) * sc, top * sc
        local ox, oy = W - w - 12, 46
        local function px(x) return ox + (x - lane.x0) * sc end
        local function py(y) return oy + (top - y) * sc end
        sgl_hud_reserve_right()
        sgl_hud_rect(ox - 4, oy - 14, w + 8, h + 30, 10, 22, 70, 170)
        sgl_hud_text("CRANE " .. k, ox, oy - 12, 0.26, SGL_HUD_BLUE, 1)
        sgl_hud_rect(ox, py(0), w, 1, 160, 160, 170, 220)                                   -- atrium floor
        sgl_hud_rect(ox, py(ledge.y), w, 2, 255, 215, 0, 230)                               -- star ledge
        for _, b in ipairs(lay.bars) do
            local bw = (b.x1 - b.x0) * sc
            if b.shutter then
                if not gate_open(ctx, k, b.gate) then
                    sgl_hud_rect(px(b.x0), py(b.y1), bw, math.max(2, (b.y1 - b.y0) * sc), 255, 70, 50, 220)
                end
            else
                sgl_hud_rect(px(b.x0), py(b.y1), bw, math.max(2, (b.y1 - b.y0) * sc), 190, 190, 200, 230)
            end
        end
        for g = 1, nGates do
            if not gate_open(ctx, k, g) then
                local s = sensor_of(lay, g)
                local bs = math.max(3, BOX * sc)
                sgl_hud_rect(px(s.x) - bs / 2, py(s.y + BOX), bs, bs, 255, 215, 0, 255)
            end
        end
        for _, a in ipairs(ctx.objs.amps or {}) do
            if obj_ok(a, id_bhvCirclingAmp) and a.oPosX >= lane.x0 and a.oPosX <= lane.x1 then
                sgl_hud_rect(px(a.oPosX) - 1.5, py(a.oPosY) - 1.5, 3, 3, 255, 90, 90, 255)
            end
        end
        sgl_hud_rect(px(cr.x - PHX), py(cr.y + PTOP), 2 * PHX * sc, math.max(2, (PTOP + PBOT) * sc), 90, 150, 255, 255)
        for _, li in ipairs(ctx.players) do
            local mm = gMarioStates[li]
            if alive(mm) and mm.pos.x >= lane.x0 and mm.pos.x <= lane.x1 and math.abs(mm.pos.z - spec.planeZ) <= 600
                and mm.pos.y > spec.yMin then
                local col = li == 0 and SGL_HUD_WHITE or SGL_HUD_GREEN
                sgl_hud_rect(px(mm.pos.x) - 1.5, py(mm.pos.y + MARIO_H), 3, math.max(3, MARIO_H * sc), col[1], col[2], col[3], 255)
            end
        end
        local cap = cap_now(ctx)
        local n = riders_on(ctx, cr)
        sgl_hud_text(string.format("riders %d/%d", n, cap), ox, oy + h + 3, 0.24, n > cap and SGL_HUD_RED or SGL_HUD_GREY, 1)
    end
    K.drawLab = draw_lab

    K.hud = function(ctx)
        if ctx.s ~= SGL_MS_ACTIVE then return end
        local L = ctx.loc
        local m = gMarioStates[0]
        local cranes = L.cranes
        if cranes == nil then return end
        local N = cranes_now(ctx)
        local ledgeMark = { x = (ledge.x0 + ledge.x1) / 2, y = ledge.y + 150, z = (ledge.z0 + ledge.z1) / 2 }
        local k = (L.operating and L.opK) or L.riding
        if k ~= nil then
            local cr = cranes[k]
            local lay = layouts(ctx)[k]
            local g = next_gate(cr)
            if g == nil then
                sgl_hud_marker(ledgeMark, "STAR LEDGE", SGL_HUD_GOLD, m)
            elseif not gate_open(ctx, k, g) then
                local s = sensor_of(lay, g)
                sgl_hud_marker({ x = s.x, y = s.y + BOX / 2, z = s.z }, "! BOX", SGL_HUD_GOLD, m)
            else
                sgl_hud_marker({ x = lay.gapX[g], y = spec.gateY[g], z = spec.planeZ }, "GAP", SGL_HUD_ORANGE, m)
            end
            if L.operating then
                sgl_hud_marker({ x = cr.x, y = cr.y + PTOP + 40, z = spec.planeZ }, "CRANE " .. k, SGL_HUD_BLUE, nil)
            end
            draw_lab(ctx, k)
            return
        end
        if on_ledge(m.pos) then return end
        for j = 1, N do
            if L.ops == nil or L.ops[j] == nil then
                local c = lanes[j].console
                sgl_hud_marker({ x = c.x, y = c.y + 200, z = c.z }, "CONSOLE " .. j, SGL_HUD_RED, m)
            end
            local cr = cranes[j]
            sgl_hud_marker({ x = cr.x, y = cr.y + PTOP + 60, z = spec.planeZ }, "CRANE " .. j, SGL_HUD_BLUE, m)
        end
    end

    -- D-pad Down / /mission start: into the lab (the atrium floor by the consoles), from anywhere in the
    -- stage, in any state (also while waiting for a second player); not while driving, riding or up high
    K.toStart = function(ctx, m)
        local L = ctx.loc
        if L.operating then
            sgl_hud_toast("You are driving a crane - B lets go first", 2, SGL_HUD_ORANGE)
            return false
        end
        if m.health <= 0xFF or (m.action & ACT_GROUP_MASK) == ACT_GROUP_CUTSCENE or m.heldObj ~= nil
            or m.riddenObj ~= nil or L.riding ~= nil or on_ledge(m.pos) then
            return false
        end
        if in_lab(m.pos) then
            sgl_hud_toast("You are in the Robotics Lab", 2, SGL_HUD_WHITE)
            return false
        end
        local e = spec.entry
        local a = (gNetworkPlayers[0].globalIndex % 8) * math.pi / 4      -- players land side by side
        m.pos.x, m.pos.y, m.pos.z = e.x + math.sin(a) * 150, e.y + 20, e.z + math.cos(a) * 100
        m.vel.x, m.vel.y, m.vel.z = 0, 0, 0
        m.forwardVel = 0
        m.faceAngle.y = 0                                                   -- south: the cranes and the ledge
        set_mario_action(m, ACT_IDLE, 0)
        if m.area ~= nil and m.area.camera ~= nil then soft_reset_camera(m.area.camera) end
        play_sound(SOUND_MENU_EXIT_PIPE, gGlobalSoundSource)
        sgl_hud_toast("Remote Robotics Lab (Malachowsky Hall)", 2, SGL_HUD_WHITE)
        return true
    end
    return K
end

---------------------------------------------------------------------------------------------
-- act 1: ROOFTOP OF THE REITZ (+ the window-washer lift)
---------------------------------------------------------------------------------------------
local LIFT_BOTTOM = P.lift_bottom.y + PBOT       -- resting on the podium roof
local LIFT_TOP = P.lift_top.y - PTOP             -- its deck level with the parapet top (27.0 m)
local LIFT_WAIT = 60                             -- frames at each end
local LIFT_SPEED = 6                             -- units per frame (1.8 m/s)
local LIFT_CATCH_UP = 2 * LIFT_SPEED             -- at most this far per frame toward the timer's height

-- the lift's height at network area time t (the same on every client in the area)
function sgl_reitz_lift_y(t)
    local travel = LIFT_TOP - LIFT_BOTTOM
    local move = math.ceil(travel / LIFT_SPEED)
    local u = t % (2 * (LIFT_WAIT + move))
    if u < LIFT_WAIT then return LIFT_BOTTOM end
    u = u - LIFT_WAIT
    if u < move then return math.min(LIFT_TOP, LIFT_BOTTOM + u * LIFT_SPEED) end
    u = u - move
    if u < LIFT_WAIT then return LIFT_TOP end
    u = u - LIFT_WAIT
    return math.max(LIFT_BOTTOM, LIFT_TOP - u * LIFT_SPEED)
end

-- the lift's next height: toward the timer's height, but never more than LIFT_CATCH_UP per frame. The
-- network area timer follows the clock, so a stall (a join, an area sync) makes it jump; a deck that
-- jumped with it (> 78 units) would drop its rider through it (find_floor only looks 78 units up).
function sgl_reitz_lift_step(y, target)
    if y == nil then return target end
    return y + clamp(target - y, -LIFT_CATCH_UP, LIFT_CATCH_UP)
end

local rooftopKind = sgl_mission_kind_reach({
    goal = P.roof_goal,
    goalRadius = 320,           -- on the 7 x 6 m elevator penthouse roof (its half depth is 3 m)
    goalBelow = 40,             -- feet at its roof, not a jump up beside it
    goalLabel = "PENTHOUSE ROOF",
    zone = P.roof_zone,
    ground = 0,
    milestones = {
        { name = "Ballroom roof", y = P.ballroom_roof.y },
        { name = "Podium roof", y = P.podium_roof.y },
        { name = "Tower roof", y = P.tower_roof.y },
    },
    -- the marker walks the climb: ravine terraces -> awnings -> the lift on the tower's west face -> goal
    route = {
        { pos = P.climb_start, label = "CLIMB HERE", doneY = 100 },
        { pos = P.climb_awning, label = "AWNINGS", doneY = P.ballroom_roof.y - 50 },
        { pos = P.lift_bottom, label = "WINDOW-WASHER LIFT", doneY = P.tower_roof.y - 50 },
    },
})

sgl_mission_register({
    id = "reitz_rooftop",
    pointsFile = "wf_reitz_missions.lua (REITZ_POINTS)",
    level = LEVEL_WF,
    act = REITZ_MISSION_ACTS.rooftop,
    title = "ROOFTOP OF THE REITZ",
    objective = "Climb the Reitz Union to its penthouse roof, 28.8 m!",
    star = P.roof_star,             -- spawned on the penthouse (the level script has no star for act 1)
    starFrom = up(P.roof_star, 800),
    probes = { probe(P.roof_goal, "the Reitz penthouse roof"), probe(P.climb_start, "the ravine terrace") },
    compactPanel = true,
    kind = rooftopKind,
    -- the window-washer lift (reitz_reitz_union.py markers.window_washer_lift): a 2.4 x 3.2 m deck shuttling
    -- between the podium roof and the parapet top on the network area timer, so every client agrees; at
    -- the top its east edge is 0.1 m from the parapet (step across onto the tower roof)
    spawnLocal = function(ctx)
        ctx.objs.lift = spawn_platform(P.lift_bottom.x, LIFT_BOTTOM, P.lift_bottom.z, 1.2 * 100 / PHX, 1.6 * 100 / PHZ,
            function(rec)
                rec.y = sgl_reitz_lift_step(rec.started and rec.y or nil, sgl_reitz_lift_y(get_network_area_timer()))
                rec.started = true
            end)
    end,
})

---------------------------------------------------------------------------------------------
-- act 2: MEAL SWIPE TOKENS
---------------------------------------------------------------------------------------------
sgl_mission_register({
    id = "reitz_tokens",
    pointsFile = "wf_reitz_missions.lua (REITZ_POINTS)",
    level = LEVEL_WF,
    act = REITZ_MISSION_ACTS.tokens,
    title = "MEAL SWIPE TOKENS",
    objective = "Find the 8 meal-swipe tokens around the quad!",
    star = up(P.token_star, 150),   -- (fallback; the star pops out of the last token found: starAt)
    starFrom = up(P.token_star, 1500),
    probes = { probe(P.tokens[7], "the Malachowsky glass stair"), probe(P.tokens[2], "the Engineering Plaza sculpture") },
    compactPanel = true,
    kind = kind_tokens({
        tokens = P.tokens,
        radius = 160,               -- touch the token (1.6 m around it) ...
        below = 100,                -- ... from 1 m below its floor point (swimming up to the fountain float)
        above = 250,                -- ... to 2.5 m above it
        lift = 100,                 -- drawn 1 m above the floor point
        scale = 1.5,
        fallbackStar = P.token_star,
    }),
})

---------------------------------------------------------------------------------------------
-- act 3 (co-op): REMOTE ROBOTICS LAB - 2P
---------------------------------------------------------------------------------------------
local A = P.atrium
local LANE_MID = (A.x0 + A.x1) // 2
sgl_mission_register({
    id = "reitz_robotics",
    pointsFile = "wf_reitz_missions.lua (REITZ_POINTS)",
    level = LEVEL_WF,
    act = REITZ_MISSION_ACTS.robotics,
    title = "REMOTE ROBOTICS LAB - 2P",
    objective = "One drives the crane, one rides it up to the ledge!",
    star = P.robotics_star,
    starFrom = up(P.atrium_floor, 100),
    starCutsceneRange = 5000,       -- the whole atrium sees the star rise to the ledge
    probes = { probe(P.ledge_star, "the atrium star ledge"), probe(P.console_1, "the atrium floor") },
    kind = kind_cranes({
        lanes = {
            -- west lane (crane 1, west console)
            { x0 = A.x0, x1 = LANE_MID, console = P.console_1, start = { x = (A.x0 + LANE_MID) // 2, y = A.y + PBOT } },
            -- east lane (crane 2, east console, 4+ players)
            { x0 = LANE_MID, x1 = A.x1, console = P.console_2, start = { x = (LANE_MID + A.x1) // 2, y = A.y + PBOT } },
        },
        gateY = P.gate_y,
        gateHalf = 50,              -- the sensor gates are 1 m thick
        gapWidth = 620,             -- 6.2 m gaps (the platform is 5.12 m wide: +-0.54 m to line up)
        gapSlots = { 0.17, 0.5, 0.83 },  -- gap centres along the crane's travel (never at a lane wall)
        -- gap slot of gates 1..5 (1 west, 2 middle, 3 east); round r, lane k uses ((r + 2(k-1)) % 5) + 1
        patterns = { { 3, 1, 2, 3, 1 }, { 1, 3, 2, 1, 3 }, { 2, 1, 3, 2, 3 }, { 3, 2, 1, 3, 2 }, { 1, 2, 3, 1, 2 } },
        headroom = 280,             -- a locked gate stops the deck 2.8 m under its bar: the 1 m "!" box hangs
        sensorSize = 102,           -- just over a standing rider's head (jump into it)
        sensorReach = 100,          -- the box sits 1 m past the crane's travel: the rider walks to the deck's end
        planeZ = P.crane_z,
        yMin = A.y + PBOT,          -- resting on the atrium floor (deck 0.5 m up)
        yMax = P.ledge.y - PTOP,    -- deck level with the star ledge
        speedX = 9,                 -- 2.7 m/s sideways
        speedY = 7,                 -- 2.1 m/s up / down
        packX0 = A.x0,
        ledge = P.ledge,
        atrium = P.atrium,
        entry = P.lab_entry,
        consoleRadius = 300,        -- stand on the switch (vanilla purple switch at scale 1.5)
        consoleHeight = 400,
        consoleSlack = 60,          -- the operator keeps the console up to 3.6 m out
        drones = {                  -- at the riders' height while the crane waits under gates 3 and 5
            { lane = 1, y = 1190 }, { lane = 1, y = 2110 },
            { lane = 2, y = 1190 }, { lane = 2, y = 2110 },
        },
        minPlayers = 2,
    }),
})

---------------------------------------------------------------------------------------------
-- act 3 hooks: the operator's stick and B (read before the engine sees them, then cleared so the operator
-- stays on the console and B does not punch) and the crane position stream
---------------------------------------------------------------------------------------------
local sRobotics = sgl_mission_get(LEVEL_WF, REITZ_MISSION_ACTS.robotics)

local function robotics_ctx()
    local ctx = sgl_mission_ctx()
    if ctx == nil or ctx.def ~= sRobotics or ctx.dormant then return nil end
    return ctx
end

local function on_before_mario_update(m)
    if m.playerIndex ~= 0 or sRobotics == nil then return end
    local ctx = robotics_ctx()
    if ctx == nil or not ctx.loc.operating then return end
    local c = m.controller
    local inp = ctx.loc.input or {}
    ctx.loc.input = inp
    inp.sx, inp.sy = c.stickX, c.stickY
    if (c.buttonPressed & B_BUTTON) ~= 0 then inp.b = true end
    local cam = m.area ~= nil and m.area.camera or nil
    inp.camYaw = cam ~= nil and (cam.yaw & 0xFFFF) or nil
    c.stickX, c.stickY, c.stickMag = 0, 0, 0
    c.rawStickX, c.rawStickY = 0, 0
    c.buttonPressed = c.buttonPressed & ~B_BUTTON
    c.buttonDown = c.buttonDown & ~B_BUTTON
end

-- a crane position: only from that crane's assigned operator (synced field o), or from anyone while it has
-- none (the last, reliable position of an operator who just let go)
local function on_packet_receive(data)
    if data.sgl ~= SGL_REITZ_CRANE_PACKET then return end
    local ctx = robotics_ctx()
    if ctx == nil or data.ik ~= ctx.key or data.r ~= ctx.r or math.type(data.k) ~= "integer" then return end
    if type(data.x) ~= "number" or type(data.y) ~= "number" then return end
    local cranes = sRobotics.craneState(ctx)
    local cr = cranes[data.k]
    if cr == nil or (ctx.loc.operating and ctx.loc.opK == data.k) then return end
    local op = sRobotics.opGi(ctx, data.k)
    if op >= 0 and data.gi ~= op then return end
    cr.tx, cr.ty = data.x, data.y
end

hook_event(HOOK_BEFORE_MARIO_UPDATE, on_before_mario_update)
hook_event(HOOK_ON_PACKET_RECEIVE, on_packet_receive)
