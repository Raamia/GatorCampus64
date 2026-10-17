-- Super Gatorlator 64: Library West After Dark (course 5, LEVEL_BBH, hub door 5 "Library West") missions, on the
-- framework in sgl_mission.lua (docs/game_design.md 7.5, docs/flow.md 5). An INTERIOR stage at night: six floors 6 m
-- apart (F1 the lobby + stacks at Y 0 ... F6 the graduate floor at Y 3000), a three-storey base whose roof (Y 1800)
-- is a walkable terrace round the tower's 4th floor (data/uf/libwest_layout.json, docs/libwest_layout.md).
--
--   act 1  ALL-NIGHTER                 solo (design 7.5 act 1): climb from the lobby to the 6th floor's big window. The
--                                      night custodial crew has the west and east stair halls "closed for cleaning"
--                                      below the 4th floor (act-1-only barriers on their seven F1-F3 doors), so the
--                                      route is the stopped escalator -> the 2nd-floor stacks (rolling library
--                                      ladders slide along the tall ranges: a step up onto their tops) -> the NW or NE
--                                      stair tower -> its roof door -> across the dark north roof terrace -> the
--                                      tower's north door -> the quiet 4th floor -> a stair hall up to the 6th floor
--                                      (its 5th-floor door is staff only) -> the big window over the Plaza, where the
--                                      mission spawns the star. Sleepy Boos haunt the way: they drift after you while
--                                      your back is turned and freeze, see-through, while you face them; a touch is a
--                                      wedge + a knock-back; a punch from close sends one away for 15 s. Skilled
--                                      players may wall-kick up the out-of-order elevator shaft instead (car A: the
--                                      build leaves it open on every floor, as at Marston).
--   act 2  COFFEE RUN                  solo-friendly race (design 7.5 act 5): an all-nighter on the 6th floor needs
--                                      coffee. From your desk in the grad reading room run down a stair hall to the
--                                      2nd floor, down the stopped escalator, grab a cup at the lobby's coffee counter
--                                      and bring it back up to the desk. Par 1'00 (gold 0'45) for the star; with
--                                      friends it is a race (results board, personal best). Boos haunt the stair
--                                      halls' turn landings (a knock-back, no damage: it costs time). The HUD marker
--                                      walks the way (STAIRS DOWN / ESCALATOR DOWN / COFFEE / ESCALATOR UP / STAIRS UP
--                                      / YOUR DESK); carriers wear the cup over their head on every client.
--   act 3  QUIET HOURS HIDE & SEEK - 2P co-op / competitive, 2+ players (design 7.5 act 2): one player is the night
--                                      librarian (drawn metal, a lantern over the head; 5-8 players: two, 9+: three),
--                                      rotating each round. The librarian counts at the circulation desk with the
--                                      screen dark (25-30 s) while the hiders spread through the stacks of the north
--                                      wing (2 players: the 2nd floor only; 3: 2F-3F; 4+: 1F-3F, linked by the NW and
--                                      NE stair halls). Then 120 s (2 players) / 150 s (design) of quiet hours: a
--                                      librarian finds a hider by touch, or by holding them in the lantern's beam for
--                                      half a second (6 m ahead, 3 m if they crouch; shelves block it). Found hiders
--                                      join the librarians. Hiders who run, jump or land near a librarian are heard
--                                      (a NOISE marker on the librarian's screen), a hider who stays put 45 s sneezes
--                                      (heard 20 m away), every 30 s the library chime tells the librarians which
--                                      floor and side each hider is on, and leaving the stacks for 4 s counts as
--                                      found. Hiders see a "librarian near" warning and when the beam is on them.
--                                      Every completed round (2+ players) puts the star on the circulation desk; the
--                                      results board shows who survived, and each player's mod_storage keeps a tally.
--   acts 4-6 "COMING SOON - ..." in course.lua (design 7.5 acts 3 Ghost of Finals Past, 4 Lights Out, 6 Glowing
--                                      Books): free roam, no star.
-- In all three acts the 5th floor's two stair doors are closed by "STAFF ONLY" barriers (the build leaves those doors
-- open so that a later act, design 7.5's Lights Out / Coffee Run from the break room, can use the staff floor).
-- Act order (course.lua header): playable acts 1..3 with no gap, the solo ones first. Every star is spawned by its
-- mission (spawn_default_star from the controller loop, star id = act - 1): the level script must NOT place a bhvStar
-- for acts 1-3. Each mission checks the stage geometry first (probes on LIBWEST_POINTS): if levels/bbh is not the real
-- Library West (vanilla Big Boo's Haunt, or a build that moved things) they stay offline (/mission force overrides)
-- and spawn nothing (no barriers, ladders, Boos).
--
-- File name: coopdx loads a mod's files in strcmp order of their names and this file registers missions at load, so
-- it must sort AFTER sgl_mission.lua (docs/flow.md 7 step 9). "uf_west_library_missions.lua" sorts after
-- uf_marston_missions.lua and before wf_reitz_missions.lua ("uf_libwest_..." would load between the Lake Alice and
-- Marston files, which test_marston_missions.lua's load-order check rejects; "bbh_..." would load before the
-- framework).
--
-- The BBH slot: nothing here uses vanilla Big Boo's Haunt behaviours. The Boos are this file's own Lua behaviour on the
-- vanilla Boo MODEL (E_MODEL_BOO: ghostly late-night stand-ins, on purpose), local to each client like Marston's
-- flying books; no bhvBoo / bhvGhostHuntBoo / bhvMerryGoRound* object is spawned and no star position of
-- gLevelValues.starPositions is used (the missions spawn their own stars). Music, rooms, the BBH camera and any other
-- slot leak belong to the stage build and levels.lua.
--
-- Networking: the rolling ladders are pure functions of get_network_area_timer() (identical on every client of the
-- area, like the Marston lifts). Boos are local per client and only ever react to the local player. The coffee run is
-- the framework's race kind (local timing, reliable "fin" events) plus a reliable "cup" event so every client draws a
-- cup over a carrier. Hide and seek: the leader assigns the roles and runs the phase clock in synced fields; tagging is
-- judged on the LIBRARIAN's client (touch / beam, line of sight by a collision ray) and sent as a reliable "tag" event
-- the leader validates (re-sent after 1.5 s while unapplied); leaving the stacks is reported by the hider's own
-- client; noises and sneezes are reliable "noise" events that each librarian's client turns into markers when it is
-- within earshot. Roles show as model states (metal librarians, see-through spectators) set every frame for every
-- player on every client, as the bundled hide-and-seek mod does.

---------------------------------------------------------------------------------------------
-- ALL Library West mission coordinates, in game units (area 1 of LEVEL_BBH). Swap values here only.
-- Source: data/uf/libwest_points.json once the stage build writes it (points measured on the BUILT collision); until
-- then data/uf/libwest_layout.json (the layout research, map metres: its "missions" anchors and its geometry) through
-- its transform (centre (38.9, 285.6) m):
--   X = (x - 38.9) * 100,  Y = z * 100,  Z = -(y - 285.6) * 100.
-- Y is the floor (Mario's feet) at a standing point: F1 0 (= the hub's grade, the lobby), F2 600, F3 1200, F4 1800 (and
-- the base's roof terraces), F5 2400 (staff), F6 3000 (6 m storeys, 5.4 m clear under a 0.6 m slab; the real storeys
-- are about 4.2 m, docs/libwest_layout.md 4).
-- tools/luatest/check_libwest_points.py recomputes every value (derived ones with its RULES), fails on drift > 0.5 m,
-- checks the layout (walkable floor, props, columns, barriers on every door, the ladder decks beside their ranges, the
-- star humps under the ceilings, the arena) and, once levels/bbh exists, the built collision; --print prints fresh
-- values and their sources.
-- (The table is built by a local function so its numbers are that function's constants, not the main chunk's: with
-- more than 256 main-chunk constants luac stops using SETTABUP for globals, which tools/luatest/check_globals.lua reads.)
---------------------------------------------------------------------------------------------
local function libwest_points() return {
    spawn = { x = 0, y = 0, z = 2320 },                         -- missions.spawn (0x0A: the vestibule, facing the escalators)
    zone = { x0 = -4020, x1 = 3990, z0 = -3447, z1 = 3150 },    -- bounding box of the F1-F3 outline (heights count here)
    y_f1 = 0,                                                   -- floors[].z_game_m
    y_f2 = 600,
    y_f3 = 1200,
    y_f4 = 1800,
    y_f5 = 2400,
    y_f6 = 3000,
    clear = 540,                                                -- clear_height_game_m (5.4 m under every slab)
    hall_w = { x0 = -2010, x1 = -1310, z0 = 1710, z1 = 2710 },  -- the west stair hall (vertical.stair_w, F1-F6)
    hall_e = { x0 = 1280, x1 = 1980, z0 = 1710, z1 = 2710 },    -- the east stair hall (F1-F6)
    hall_nw = { x0 = -2390, x1 = -1630, z0 = -3300, z1 = -2280 },  -- the NW stair tower (F1-F3 + the roof door)
    hall_ne = { x0 = 1630, x1 = 2380, z0 = -3290, z1 = -2280 },    -- the NE stair tower
    land_w = { x = -1660, y = 0, z = 1840 },                    -- the west hall's floor landing (Y: any floor)
    land_e = { x = 1630, y = 0, z = 1840 },                     -- the east hall's floor landing
    tower = { x0 = -2860, x1 = 2830, z0 = 280, z1 = 2710 },     -- the 4th floor's plate (inside = not on a terrace)
    lobby = { x0 = -1310, x1 = 1280, z0 = 1440, z1 = 2710 },    -- the 1st floor's lobby (the Plaza Hall: cafe, vestibule,
                                                                --   coffee bar) ...
    esc_band = { x0 = -330, x1 = 310, z0 = 1010, z1 = 2050 },   -- ... and the escalators (the rest of F1 is the stacks)

    -- act 1 (design 1): the climb
    climb_goal = { x = 0, y = 3000, z = 2460 },                 -- F6 at the big window (a 2.5 m goal disc)
    climb_star = { x = 0, y = 3080, z = 2570 },                 -- the layout's act 1 star spot, 0.8 m up (the 4 m spawn
                                                                --   hump stays under the 5.4 m ceiling)
    esc_foot = { x = 160, y = 0, z = 2100 },                    -- the up escalator's foot (route marker)
    esc_top = { x = -10, y = 600, z = 890 },                    -- the escalators' top landing on F2
    door_nw = { x = -2110, y = 600, z = -2200 },                -- 0.8 m in front of the NW stair door (F2; the same
                                                                --   spot on F3, and on the roof terrace at Y 1800)
    door_ne = { x = 2080, y = 600, z = -2200 },                 -- ... of the NE stair door
    tower_door = { x = -10, y = 1800, z = 100 },                -- 1.8 m out on the terrace from the 4th floor's north door
    f4_door_w = { x = -1180, y = 1800, z = 1770 },              -- 1.3 m into F4 from the west hall's east door (by its
                                                                --   north part: a column stands off its middle)
    f4_door_e = { x = 1150, y = 1800, z = 1770 },               -- ... from the east hall's west door
    f6_door_w = { x = -1180, y = 3000, z = 1770 },              -- the same on F6 (the grad reading room)
    f6_door_e = { x = 1150, y = 3000, z = 1770 },
    stair_doors = {                                             -- act 1 barriers: every F1-F3 door of the west and
                                                                --   east stair halls (vertical[].game.doors)
        { x0 = -2010, z0 = 1945, x1 = -2010, z1 = 1730, y = 0 },
        { x0 = -2010, z0 = 1945, x1 = -2010, z1 = 1730, y = 600 },
        { x0 = -2010, z0 = 1945, x1 = -2010, z1 = 1730, y = 1200 },
        { x0 = -1310, z0 = 1945, x1 = -1310, z1 = 1730, y = 1200 },
        { x0 = 1980, z0 = 1945, x1 = 1980, z1 = 1730, y = 0 },
        { x0 = 1330, z0 = 1710, x1 = 1570, z1 = 1710, y = 600 },
        { x0 = 1280, z0 = 1945, x1 = 1280, z1 = 1730, y = 1200 },
    },
    staff_doors = {                                             -- acts 1-3: the 5th floor's stair doors ("STAFF ONLY";
                                                                --   the build leaves them open for the missions to lock)
        { x0 = -1310, z0 = 1945, x1 = -1310, z1 = 1730, y = 2400 },
        { x0 = 1280, z0 = 1945, x1 = 1280, z1 = 1730, y = 2400 },
    },
    shaft_door = { x = -875, y = 600, z = 1050 },               -- elevator car A (out of order, open on every floor: a
                                                                --   wall-kick shaft F1-F6), 0.7 m out of its F2 door
    boos1 = {                                                   -- act 1 sleepy Boos (y = the floor under their home)
        { x = -1060, y = 600, z = -1760, name = "STACKS WEST" },
        { x = 1030, y = 600, z = -1760, name = "STACKS EAST" },
        { x = -2010, y = 1500, z = -3170, name = "NW STAIRWELL" },
        { x = 2000, y = 1500, z = -3160, name = "NE STAIRWELL" },
        { x = 10, y = 1800, z = -1090, name = "ROOF TERRACE" },
        { x = -890, y = 1800, z = 970, name = "QUIET FLOOR" },
        { x = 510, y = 3000, z = 1900, name = "GRAD READING ROOM" },
    },
    ladders = {                                                 -- act 1 rolling ladders: track ends x0..x1 along the
                                                                --   south face of a 3.6 m range, deck centre z, step y
        { x0 = -890, x1 = -190, z = -1640, y = 750 },
        { x0 = 1210, x1 = 1900, z = -1640, y = 750 },
        { x0 = -1930, x1 = -1240, z = -1640, y = 1350 },
        { x0 = 160, x1 = 860, z = -2520, y = 1350 },
    },

    -- act 2 (design 5): the coffee run
    run_start = { x = 0, y = 3000, z = 1940 },                  -- your desk: the grad reading room aisle (start + finish)
    cup = { x = 995, y = 110, z = 1960 },                       -- the cup on the lobby's coffee counter (top 1.1 m; the
                                                                --   built counter: libwest_points.json act5_cup)
    cup_stand = { x = 870, y = 0, z = 1960 },                   -- where a runner stands to grab it
    f2_door_w = { x = -2140, y = 600, z = 1840 },               -- 1.3 m out of the west hall's F2 door (west)
    f2_door_e = { x = 1450, y = 600, z = 1580 },                -- 1.3 m out of the east hall's F2 door (north)
    boos2 = {                                                   -- act 2 Boos on the stair halls' turn landings
        { x = -1660, y = 900, z = 2580, name = "WEST STAIRWELL 2-3F" },
        { x = -1660, y = 2100, z = 2580, name = "WEST STAIRWELL 4-5F" },
        { x = 1630, y = 1500, z = 2580, name = "EAST STAIRWELL 3-4F" },
        { x = 1630, y = 2700, z = 2580, name = "EAST STAIRWELL 5-6F" },
    },

    -- act 3 (design 2): quiet hours hide and seek
    desk = { x = -90, y = 600, z = 300 },                       -- the night librarian counts here (circulation desk)
    desk_star = { x = -90, y = 725, z = 170 },                  -- the star: on the circulation counter (design)
    release_w = { x = -1100, y = 600, z = -300 },               -- hiders start in the west ...
    release_e = { x = 1070, y = 600, z = -300 },                -- ... or the east corridor into the stacks
    arena_neck = { x0 = -2280, x1 = 2260, z0 = -1030, z1 = -200 },  -- the arena: the neck ...
    arena_wing = { x0 = -3410, x1 = 3410, z0 = -3447, z1 = -1000 }, -- ... and the north wing (floors 1-3)
    hide_spots = {                                              -- the layout's hiding spots (tips; tests)
        { x = -15, y = 0, z = -1130, name = "1F COMPACT STACKS" },
        { x = -10, y = 0, z = -3200, name = "1F CURVED GLASS BAY" },
        { x = -3150, y = 0, z = -2030, name = "1F WEST WINDOWS" },
        { x = 2077, y = 600, z = -2120, name = "2F NE STAIR AISLE" },
        { x = 3130, y = 600, z = -2540, name = "2F EAST WINDOW SEATS" },
        { x = 1810, y = 1200, z = -1530, name = "3F MICROFORM CABINETS" },
        { x = -2630, y = 1200, z = -1970, name = "3F OVERSIZED FOLIOS" },
        { x = 570, y = 1200, z = -580, name = "3F BLOOMBERG TERMINAL" },
    },
} end
LIBWEST_POINTS = libwest_points()

-- which act each mission is (star id = act - 1). Keep in step with the act names in course.lua
-- (tools/luatest/test_libwest_missions.lua checks that every mission title equals its course.lua act name).
LIBWEST_MISSION_ACTS = { allnighter = 1, coffee = 2, hideseek = 3 }

---------------------------------------------------------------------------------------------
if sgl_mission_register == nil then
    log_to_console("[SGL] uf_west_library_missions.lua: sgl_mission.lua is not loaded", CONSOLE_MESSAGE_ERROR)
    return
end

local P = LIBWEST_POINTS
local POINTS_FILE = "uf_west_library_missions.lua (LIBWEST_POINTS)"

local function up(p, dy)
    return { x = p.x, y = p.y + dy, z = p.z }
end

local function at_y(p, y)
    return { x = p.x, y = y, z = p.z }
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

local function dist3(p, q)
    return math.sqrt((p.x - q.x) ^ 2 + (p.y - q.y) ^ 2 + (p.z - q.z) ^ 2)
end

local function clamp(v, lo, hi)
    if v < lo then return lo end
    if v > hi then return hi end
    return v
end

local function popcount(v)
    local n = 0
    while v > 0 do
        n = n + (v & 1)
        v = v >> 1
    end
    return n
end

-- signed difference of two s16 angles
local function angle_diff(a, b)
    return ((math.floor(a) - math.floor(b) + 0x8000) & 0xFFFF) - 0x8000
end

-- a synced number as text ("25", never "25.0": sync-table numbers may arrive as floats)
local function int_text(v)
    return string.format("%d", math.floor(v or 0))
end

local function in_rect(p, r)
    return p.x >= r.x0 and p.x <= r.x1 and p.z >= r.z0 and p.z <= r.z1
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

local function in_cutscene(m)
    return (m.action & ACT_GROUP_MASK) == ACT_GROUP_CUTSCENE
end

-- a player who may be teleported (D-pad Down, a hide-and-seek round start): alive, not in a cutscene, holding or
-- riding nothing
local function can_teleport(m)
    return alive(m) and not in_cutscene(m) and m.heldObj == nil and m.riddenObj == nil
end

local function teleport(m, p, faceYaw)
    local a = (gNetworkPlayers[0].globalIndex % 8) * math.pi / 4      -- players land side by side
    m.pos.x, m.pos.y, m.pos.z = p.x + math.sin(a) * 80, p.y + 20, p.z + math.cos(a) * 80
    m.vel.x, m.vel.y, m.vel.z = 0, 0, 0
    m.forwardVel = 0
    m.faceAngle.y = faceYaw
    set_mario_action(m, ACT_IDLE, 0)
    if m.area ~= nil and m.area.camera ~= nil then soft_reset_camera(m.area.camera) end
end

local LIBWEST_DOUBLE_PRESS = 60   -- frames: a second D-pad Down within 2 s confirms a teleport back to the start

-- a punch, a kick or a dive (what sends a Boo away)
local PUNCHES = {}
for _, a in ipairs({ ACT_PUNCHING, ACT_MOVE_PUNCHING, ACT_JUMP_KICK, ACT_DIVE }) do PUNCHES[a] = true end

local function punching(m)
    return alive(m) and PUNCHES[m.action] == true
end

-- crouching / crawling (hide and seek: a smaller target for the lantern)
local DUCKING = {}
for _, a in ipairs({ ACT_CROUCHING, ACT_START_CROUCHING, ACT_STOP_CROUCHING, ACT_CRAWLING, ACT_START_CRAWLING,
    ACT_STOP_CRAWLING, ACT_CROUCH_SLIDE }) do DUCKING[a] = true end

-- the knock-back actions (a hit already in progress)
local KNOCKBACK = {}
for _, a in ipairs({ ACT_BACKWARD_GROUND_KB, ACT_FORWARD_GROUND_KB, ACT_HARD_BACKWARD_GROUND_KB, ACT_HARD_FORWARD_GROUND_KB,
    ACT_SOFT_BACKWARD_GROUND_KB, ACT_SOFT_FORWARD_GROUND_KB, ACT_BACKWARD_AIR_KB, ACT_FORWARD_AIR_KB,
    ACT_HARD_BACKWARD_AIR_KB, ACT_HARD_FORWARD_AIR_KB }) do
    KNOCKBACK[a] = true
end

-- can a Boo hit the local player now (not mid-hit, not invincible, not in a cutscene or intangible)
local function hittable(m)
    return alive(m) and (m.invincTimer or 0) == 0 and not KNOCKBACK[m.action] and not in_cutscene(m)
        and (m.action & ACT_FLAG_INTANGIBLE) == 0
end

---------------------------------------------------------------------------------------------
-- local objects. Ladders: Lua platforms with the vanilla checkerboard-platform collision (5.12 x 0.51 x 3.07 m at scale
-- 1), scaled to a 1.4 x 0.7 m step, moved by Lua with oVel = the displacement so the engine carries the rider (as the
-- Marston lifts). Solids: the same collision scaled into a box (the act 1 barriers), switched off by not loading it.
-- Props: visuals only (outline boxes, Boos, coffee cups).
---------------------------------------------------------------------------------------------
local PHX, PTOP, PBOT, PHZ = 256, 26, 25, 153     -- checkerboard collision at scale 1: half x, deck top, underside, half z
local BOX_UNIT = 51           -- the "!" box models are 51 units at scale 1, origin at the bottom centre
local PLAT_SNAP = 200         -- a jump farther than this per frame (reset, late join) carries nobody
local sRec = {}
local sRecNext = 0

local function new_rec(rec)
    sRecNext = (sRecNext % 250) + 1
    rec.idx = sRecNext
    sRec[rec.idx] = rec
    return rec
end

local function rec_of(o)
    local rec = sRec[o.oBehParams & 0xFF]
    if rec == nil or rec.o ~= o then return nil end
    return rec
end

local function ladder_init(o)
    o.oFlags = OBJ_FLAG_UPDATE_GFX_POS_AND_ANGLE | OBJ_FLAG_ACTIVE_FROM_AFAR
    o.collisionData = gGlobalObjectCollisionData.checkerboard_platform_seg8_collision_0800D710
    o.oCollisionDistance = 1500
    o.oDrawingDistance = 20000
    o.oIntangibleTimer = -1
end

local function ladder_loop(o)
    local rec = rec_of(o)
    if rec == nil then
        obj_mark_for_deletion(o)
        return
    end
    if rec.drive ~= nil then rec.drive(rec) end
    local dx = rec.x - o.oPosX
    if math.abs(dx) > PLAT_SNAP then dx = 0 end
    o.oVelX, o.oVelY, o.oVelZ = dx, 0, 0          -- the engine carries the rider along by the step
    o.oPosX = rec.x
    load_object_collision_model()
end

id_bhvSglLibwestLadder = hook_behavior(nil, OBJ_LIST_SURFACE, true, ladder_init, ladder_loop, "bhvSglLibwestLadder")

local function solid_init(o)
    o.oFlags = OBJ_FLAG_UPDATE_GFX_POS_AND_ANGLE | OBJ_FLAG_ACTIVE_FROM_AFAR
    o.collisionData = gGlobalObjectCollisionData.checkerboard_platform_seg8_collision_0800D710
    o.oCollisionDistance = 1200
    o.oDrawingDistance = 20000
    o.oIntangibleTimer = -1
end

local function solid_loop(o)
    local rec = rec_of(o)
    if rec == nil then
        obj_mark_for_deletion(o)
        return
    end
    if not rec.off then load_object_collision_model() end
end

id_bhvSglLibwestSolid = hook_behavior(nil, OBJ_LIST_SURFACE, true, solid_init, solid_loop, "bhvSglLibwestSolid")

local function prop_init(o)
    o.oFlags = OBJ_FLAG_UPDATE_GFX_POS_AND_ANGLE | OBJ_FLAG_ACTIVE_FROM_AFAR
    o.oDrawingDistance = 20000
    o.oIntangibleTimer = -1
end

local function prop_loop(o)
end

id_bhvSglLibwestProp = hook_behavior(nil, OBJ_LIST_DEFAULT, true, prop_init, prop_loop, "bhvSglLibwestProp")

local function spawn_prop(model, x, y, z, setup)
    return spawn_non_sync_object(id_bhvSglLibwestProp, model, x, y, z, setup)
end

local function poof(o, id)
    if obj_ok(o, id or id_bhvSglLibwestProp) then
        spawn_non_sync_object(id_bhvMistParticleSpawner, E_MODEL_MIST, o.oPosX, o.oPosY, o.oPosZ, nil)
    end
end

-- a solid box: bottom centre (x, y, z), length `len` along its local x, height h, thickness t, yaw; with a visual
-- box model of the same size (origin at its bottom centre) when model is given
local function spawn_box(x, y, z, len, h, t, yaw, model, animState)
    local rec = new_rec({ x = x, y = y, z = z, off = false })
    local sy = h / (PTOP + PBOT)
    rec.o = spawn_non_sync_object(id_bhvSglLibwestSolid, E_MODEL_NONE, x, y + PBOT * sy, z, function(obj)
        obj.oBehParams = rec.idx
        obj.oFaceAngleYaw, obj.oMoveAngleYaw = yaw, yaw
        obj_scale_xyz(obj, (len / 2) / PHX, sy, (t / 2) / PHZ)
    end)
    if model ~= nil then
        rec.vis = spawn_prop(model, x, y, z, function(obj)
            obj.oFaceAngleYaw = yaw
            obj_scale_xyz(obj, len / BOX_UNIT, h / BOX_UNIT, t / BOX_UNIT)
            obj.oAnimState = animState or 0
        end)
    end
    return rec
end

-- a door segment { x0, z0, x1, z1, y } -> centre x, z, length (+ 2 margin), yaw (axis-aligned doors)
local function door_box(d, margin)
    local cx, cz = (d.x0 + d.x1) / 2, (d.z0 + d.z1) / 2
    local dx, dz = math.abs(d.x1 - d.x0), math.abs(d.z1 - d.z0)
    if dx >= dz then return cx, cz, dx + 2 * margin, 0 end
    return cx, cz, dz + 2 * margin, 0x4000
end

-- barriers over door segments (an outline box 0.3 m past both jambs, 5 m tall), each with its HUD label
local function spawn_barriers(ctx, list, label)
    ctx.objs.barriers = ctx.objs.barriers or {}
    for _, d in ipairs(list or {}) do
        local cx, cz, len, yaw = door_box(d, 30)
        local rec = spawn_box(cx, d.y, cz, len, 500, 40, yaw, E_MODEL_EXCLAMATION_BOX_OUTLINE, 0)
        rec.door = d
        rec.label = label
        table.insert(ctx.objs.barriers, rec)
    end
end

-- the nearest barrier on my floor within 7 m: its label over it
local function barriers_hud(ctx, m)
    local best, bestD = nil, nil
    for _, rec in ipairs(ctx.objs.barriers or {}) do
        local d = dist2_xz(m.pos, rec)
        if math.abs(m.pos.y - rec.y) < 300 and d <= 700 * 700 and (bestD == nil or d < bestD) then best, bestD = rec, d end
    end
    if best ~= nil then sgl_hud_marker(up(best, 280), best.label, SGL_HUD_RED, nil, true) end
end

---------------------------------------------------------------------------------------------
-- Rolling library ladders (act 1): a 1.4 x 0.7 m step 1.5 m up (a standing single jump peaks at 2.2 m), sliding along
-- the south face of a 3.6 m range between the track's ends: WAIT frames at each end, SPEED units a frame between
-- them. Deck centre X at network area time t (pure). From the step a single jump reaches the range's top.
---------------------------------------------------------------------------------------------
SGL_LIBWEST_LADDER = { WAIT = 45, SPEED = 4, CATCH_UP = 12, HALF_X = 70, HALF_Z = 35 }
local LADDER = SGL_LIBWEST_LADDER

function sgl_libwest_ladder_x(t, x0, x1, offset)
    local a, b = x0 + LADDER.HALF_X, x1 - LADDER.HALF_X
    local move = math.ceil((b - a) / LADDER.SPEED)
    local u = (math.floor(t) + (offset or 0)) % (2 * (LADDER.WAIT + move))
    if u < LADDER.WAIT then return a end
    u = u - LADDER.WAIT
    if u < move then return math.min(b, a + u * LADDER.SPEED) end
    u = u - move
    if u < LADDER.WAIT then return b end
    u = u - LADDER.WAIT
    return math.max(a, b - u * LADDER.SPEED)
end

-- a deck that jumped with the area timer (a stall) catches up at most CATCH_UP units a frame, carrying its rider
function sgl_libwest_ladder_step(x, target)
    if x == nil then return target end
    return x + clamp(target - x, -LADDER.CATCH_UP, LADDER.CATCH_UP)
end

local function spawn_ladders(ctx, list)
    ctx.objs.ladders = {}
    for i, ld in ipairs(list or {}) do
        local offset = (i - 1) * 97
        local x0 = sgl_libwest_ladder_x(get_network_area_timer(), ld.x0, ld.x1, offset)
        local rec = new_rec({ x = x0, y = ld.y - PTOP, z = ld.z, half = LADDER.HALF_X, top = ld.y, ld = ld })
        rec.drive = function(r)
            local want = sgl_libwest_ladder_x(get_network_area_timer(), ld.x0, ld.x1, offset)
            r.x = sgl_libwest_ladder_step(r.started and r.x or nil, want)
            r.started = true
        end
        rec.o = spawn_non_sync_object(id_bhvSglLibwestLadder, E_MODEL_CHECKERBOARD_PLATFORM, x0, rec.y, ld.z, function(obj)
            obj.oBehParams = rec.idx
            obj_scale_xyz(obj, LADDER.HALF_X / PHX, 1, LADDER.HALF_Z / PHZ)
        end)
        ctx.objs.ladders[i] = rec
    end
end

---------------------------------------------------------------------------------------------
-- Sleepy Boos (acts 1 and 2): the vanilla Boo model on this file's prop behaviour, local to each client, reacting to the
-- local player only (like Marston's flying books). A Boo dozes at its home; within WAKE of its home (and BAND of its
-- floor) it drifts after the player while their back is turned (SPEED units a frame, or the Boo's own `speed`: act 1's
-- spec.booSpeed, never more than its leash from home) and freezes, fading to see-through and harmless, while they face
-- it (LOOK_HALF either side of their facing).
-- Touching a solid Boo is a knock-back and `hurt` (4 = one wedge); then it backs off home for BACKOFF frames. A punch,
-- kick or dive within PUNCH_R while it is visible enough sends it away (a puff) for RESPAWN frames.
---------------------------------------------------------------------------------------------
SGL_LIBWEST_BOO = { WAKE = 900, BAND = 400, LEASH = 500, SPEED = 7, HOME_SPEED = 3, HOVER = 120, LOW = 40, HIGH = 260,
    CHEST = 80, LOOK_HALF = 0x2AAA, FADE = 15, SHY_ALPHA = 60, HIT_R = 110, HIT_ALPHA = 200, PUNCH_R = 180,
    PUNCH_ALPHA = 110, RESPAWN = 450, BACKOFF = 60, SCALE = 1.0 }
local BOO = SGL_LIBWEST_BOO

-- one frame of a Boo b = { hx, hy, hz (home; hy = the floor), x, y, z, alpha, leash, speed } against the local player at
-- pos facing yaw; live = the player can be chased. Pure (tools/luatest checks it); updates and returns b.
function sgl_libwest_boo_step(b, pos, yaw, live, cfg)
    cfg = cfg or BOO
    local leash = b.leash or cfg.LEASH
    local dx, dz = pos.x - b.hx, pos.z - b.hz
    local awake = live and math.abs(pos.y - b.hy) < cfg.BAND and dx * dx + dz * dz <= cfg.WAKE * cfg.WAKE
    local looked = false
    if awake then
        looked = math.abs(angle_diff(atan2s(b.z - pos.z, b.x - pos.x), yaw)) <= cfg.LOOK_HALF
    end
    local tx, ty, tz, speed = b.hx, b.hy + cfg.HOVER, b.hz, cfg.HOME_SPEED
    if (b.backoff or 0) > 0 then
        b.backoff = b.backoff - 1
        speed = cfg.SPEED
    elseif awake and not looked then
        tx, ty, tz, speed = pos.x, pos.y + cfg.CHEST, pos.z, b.speed or cfg.SPEED
    elseif awake then
        speed = 0
    end
    if speed > 0 then
        local mx, my, mz = tx - b.x, ty - b.y, tz - b.z
        local d = math.sqrt(mx * mx + my * my + mz * mz)
        if d > 1 then
            local s = math.min(speed, d) / d
            b.x, b.y, b.z = b.x + mx * s, b.y + my * s, b.z + mz * s
        end
        -- the leash (horizontal) and its floor band
        local hx, hz = b.x - b.hx, b.z - b.hz
        local hd = math.sqrt(hx * hx + hz * hz)
        if hd > leash then
            b.x, b.z = b.hx + hx / hd * leash, b.hz + hz / hd * leash
        end
        b.y = clamp(b.y, b.hy + cfg.LOW, b.hy + cfg.HIGH)
    end
    b.shy = awake and looked
    b.awake = awake
    local want = b.shy and cfg.SHY_ALPHA or 255
    if b.alpha < want then b.alpha = math.min(want, b.alpha + cfg.FADE) else b.alpha = math.max(want, b.alpha - cfg.FADE) end
    return b
end

-- does a solid Boo touch the player at pos? Pure.
function sgl_libwest_boo_touches(b, pos, cfg)
    cfg = cfg or BOO
    return dist2_xz(b, pos) <= cfg.HIT_R * cfg.HIT_R and b.y >= pos.y - 40 and b.y <= pos.y + 200
end

local function spawn_boos(ctx, list, hurt, speed)
    ctx.objs.boos = {}
    for i, h in ipairs(list or {}) do
        local b = { hx = h.x, hy = h.y, hz = h.z, x = h.x, y = h.y + BOO.HOVER, z = h.z, alpha = 255, name = h.name,
            gone = 0, hurt = hurt or 4, i = i, speed = speed }
        b.o = spawn_prop(E_MODEL_BOO, b.x, b.y, b.z, function(obj)
            obj_scale(obj, BOO.SCALE)
            obj.oOpacity = 255
        end)
        ctx.objs.boos[i] = b
    end
end

local function boos_tick(ctx, m)
    local L = ctx.loc
    local live = ctx.s ~= SGL_MS_IDLE and ctx.s ~= SGL_MS_WAITING and alive(m) and not in_cutscene(m)
    for _, b in ipairs(ctx.objs.boos or {}) do
        local o = b.o
        local ok = obj_ok(o, id_bhvSglLibwestProp)
        if b.gone > 0 then
            b.gone = b.gone - 1
            if b.gone == 0 then
                b.x, b.y, b.z, b.alpha, b.backoff = b.hx, b.hy + BOO.HOVER, b.hz, 0, 0
                if ok then poof(o) end
            end
            if ok then set_hidden(o, b.gone > 0) end
        else
            local wasAwake = b.awake
            sgl_libwest_boo_step(b, m.pos, m.faceAngle.y, live)
            if b.awake and not wasAwake and not b.shy and ctx.age - (b.laughAt or -9999) > 150 then
                b.laughAt = ctx.age
                play_sound(SOUND_OBJ_BOO_LAUGH_SHORT, gGlobalSoundSource)
            end
            local dy = m.pos.y + BOO.CHEST - b.y
            if punching(m) and dist2_xz(b, m.pos) + dy * dy <= BOO.PUNCH_R * BOO.PUNCH_R and b.alpha >= BOO.PUNCH_ALPHA then
                play_sound(SOUND_OBJ_DEFAULT_DEATH, gGlobalSoundSource)
                sgl_hud_toast("Boo! ...shooed back to sleep", 2, SGL_HUD_GREEN)
                if ok then poof(o) end
                b.gone = BOO.RESPAWN
                L.booShoos = (L.booShoos or 0) + 1
            elseif not b.shy and b.alpha >= BOO.HIT_ALPHA and hittable(m) and sgl_libwest_boo_touches(b, m.pos) then
                m.faceAngle.y = atan2s(b.z - m.pos.z, b.x - m.pos.x)
                local air = (m.action & ACT_GROUP_MASK) == ACT_GROUP_AIRBORNE
                hurt_and_set_mario_action(m, air and ACT_BACKWARD_AIR_KB or ACT_BACKWARD_GROUND_KB, 0, b.hurt)
                play_sound(SOUND_OBJ_BOO_LAUGH_LONG, gGlobalSoundSource)
                sgl_hud_toast(b.hurt > 0 and "A sleepy Boo! (face it to freeze it, punch it to shoo it)"
                    or "A Boo blocks the stairwell! (face it to freeze it)", 3, SGL_HUD_RED)
                b.backoff = BOO.BACKOFF
                L.booHits = (L.booHits or 0) + 1
                L.expandUntil = ctx.age + 150
            end
            if ok then
                set_hidden(o, false)
                local wob = math.sin(ctx.age * 0.15 + b.i)
                o.oPosX, o.oPosY, o.oPosZ = b.x, b.y + wob * 10, b.z
                local face = atan2s(m.pos.z - b.z, m.pos.x - b.x)
                o.oFaceAngleYaw = b.shy and ((face + 0x8000) & 0xFFFF) or (face & 0xFFFF)
                o.oOpacity = math.floor(clamp(b.alpha, 0, 255))
                obj_scale_xyz(o, BOO.SCALE * (1 + 0.04 * wob), BOO.SCALE * (1 - 0.04 * wob), BOO.SCALE * (1 + 0.04 * wob))
            end
        end
    end
end

local function boos_hud(ctx, m)
    for _, b in ipairs(ctx.objs.boos or {}) do
        if b.gone == 0 and b.awake and not b.shy and math.abs(m.pos.y - b.hy) < BOO.BAND then
            sgl_hud_marker({ x = b.x, y = b.y + 90, z = b.z }, "BOO!", SGL_HUD_RED, nil, true)
        end
    end
end

---------------------------------------------------------------------------------------------
-- ALL-NIGHTER kind (act 1): the framework's reach kind (goal, milestones, team best) plus spec = { reach = <reach
-- spec without route>, barriers = { door segments } ("CLOSED FOR CLEANING"), staffDoors = { door segments } ("STAFF
-- ONLY"), shaft = {x,y,z} (the out-of-order elevator shaft's marker), ladders = { rows }, boos = { rows }, booHurt,
-- booSpeed, start = {x,y,z}, startYaw }. D-pad Down twice within 2 s (def.toStart): back to the start (the lobby), for a
-- player who is stuck or lost (a single press only asks, so a stray press never costs the climb).
-- The HUD marker walks the forced route by where the local player is (sgl_libwest_climb_route below): F1 -> the
-- escalator; F2 / F3 -> the nearer NW / NE stair door; inside those towers -> the roof
-- door; on the roof terrace -> the tower's north door; inside the 4th floor -> the nearer west / east stair hall; in
-- a hall above F4 -> its 6th-floor door; on F6 -> the big window.
---------------------------------------------------------------------------------------------
local function nearer(p, a, b)
    if dist2_xz(p, a) <= dist2_xz(p, b) then return a, true end
    return b, false
end

-- where the act 1 marker points from position p -> pos, label (nil: the goal)
local function in_lobby(p)
    return in_rect(p, P.lobby) or in_rect(p, P.esc_band)
end

local function climb_route(p)
    if p.y < P.y_f2 - 50 then
        if in_lobby(p) then return P.esc_foot, "ESCALATOR UP" end
        local d, west = nearer(p, P.door_nw, P.door_ne)         -- the 1st-floor stacks: back up a north stair
        return at_y(d, P.y_f1), west and "NW STAIR" or "NE STAIR"
    end
    if p.y < P.y_f4 - 50 then
        if in_rect(p, P.hall_nw) then return at_y(P.door_nw, P.y_f4), "ROOF DOOR" end
        if in_rect(p, P.hall_ne) then return at_y(P.door_ne, P.y_f4), "ROOF DOOR" end
        local fy = (p.y < P.y_f3 - 50) and P.y_f2 or P.y_f3
        local d, west = nearer(p, P.door_nw, P.door_ne)
        return at_y(d, fy), west and "NW STAIR TO THE ROOF" or "NE STAIR TO THE ROOF"
    end
    if in_rect(p, P.hall_w) then return P.f6_door_w, "6TH FLOOR" end
    if in_rect(p, P.hall_e) then return P.f6_door_e, "6TH FLOOR" end
    if p.y < P.y_f5 - 50 then
        if in_rect(p, P.tower) then
            local d = nearer(p, P.f4_door_w, P.f4_door_e)
            return d, "STAIRS UP TO 6F"
        end
        return P.tower_door, "4TH FLOOR DOOR"
    end
    if p.y < P.y_f6 - 50 then
        return nearer(p, P.f6_door_w, P.f6_door_e), "6TH FLOOR"
    end
    return nil
end
sgl_libwest_climb_route = climb_route

local function kind_allnighter(spec)
    local R = sgl_mission_kind_reach(spec.reach)
    local K = {}
    for k, v in pairs(R) do K[k] = v end
    K.reachKind = R
    K.routeOf = climb_route

    K.spawnLocal = function(ctx)
        spawn_barriers(ctx, spec.barriers, "CLOSED FOR CLEANING")
        spawn_barriers(ctx, spec.staffDoors, "STAFF ONLY")
        spawn_ladders(ctx, spec.ladders)
        spawn_boos(ctx, spec.boos, spec.booHurt or 4, spec.booSpeed)
    end

    K.localTick = function(ctx)
        R.localTick(ctx)
        boos_tick(ctx, gMarioStates[0])
    end

    K.toStart = function(ctx, m)
        if spec.start == nil then return end
        local L = ctx.loc
        if L.downAt == nil or ctx.age - L.downAt > LIBWEST_DOUBLE_PRESS then
            L.downAt = ctx.age
            sgl_hud_toast("D-pad Down again: back to the lobby", 2, SGL_HUD_WHITE)
            return
        end
        L.downAt = nil
        if not can_teleport(m) then
            sgl_hud_toast("Not now (land first, let go of what you hold)", 2, SGL_HUD_ORANGE)
            return
        end
        teleport(m, spec.start, spec.startYaw or 0)
        play_sound(SOUND_MENU_EXIT_PIPE, gGlobalSoundSource)
        sgl_hud_toast("Back in the lobby", 2, SGL_HUD_WHITE)
    end

    K.panel = function(ctx)
        local lines = R.panel(ctx)
        table.insert(lines, { "Stair halls closed for cleaning below 4F: take a NW / NE stair to the roof", SGL_HUD_GREY, 0.24 })
        table.insert(lines, { "Rolling ladders in the stacks step you onto the tall ranges", SGL_HUD_GREY, 0.24 })
        table.insert(lines, { "...or wall-kick up the out-of-order elevator shaft", SGL_HUD_GREY, 0.24 })
        table.insert(lines, { "Sleepy Boos: face them to freeze them, punch to shoo them", SGL_HUD_ORANGE, 0.24 })
        table.insert(lines, { "Stuck? D-pad Down twice: back to the lobby", SGL_HUD_GREY, 0.24 })
        return lines
    end

    K.hud = function(ctx)
        local m = gMarioStates[0]
        if ctx.s ~= SGL_MS_ACTIVE and ctx.s ~= SGL_MS_INTRO then return end
        local pos, label = climb_route(m.pos)
        if pos ~= nil then
            sgl_hud_marker(up(pos, 150), label, SGL_HUD_ORANGE, m)
        else
            sgl_hud_marker(spec.reach.goal, spec.reach.goalLabel or "GOAL", SGL_HUD_GOLD, m)
        end
        barriers_hud(ctx, m)
        local sh = spec.shaft
        if sh ~= nil and m.pos.y >= P.y_f2 - 50 and m.pos.y < P.y_f6 - 50 and math.abs(m.pos.y - sh.y) < 300
            and dist2_xz(m.pos, sh) <= 1500 * 1500 then
            sgl_hud_marker(up(sh, 250), "OUT-OF-ORDER SHAFT (wall kick)", SGL_HUD_GREY, nil, true)
        end
        boos_hud(ctx, m)
    end
    return K
end

---------------------------------------------------------------------------------------------
-- COFFEE kind (act 2): the framework's race kind (start box = your desk, checkpoint 1 = the cup, finish = your desk;
-- par, gold, results board, personal best, race music) plus spec = { race = <race spec>, boos = { rows }, booHurt }.
-- Its HUD replaces the race's checkpoint marker with the route on the floors between (route_of below); a runner who
-- reached the cup gets a cup over the head, on every client (a reliable "cup" event), until the finish.
---------------------------------------------------------------------------------------------
local CUP_MODEL = E_MODEL_BITS_WARP_PIPE    -- a green warp pipe scaled to a 0.35 m to-go cup (unbranded)
local CUP_SCALE = 0.12

-- where the act 2 marker points from position p, for checkpoint cp (1 = the cup, 2 = the desk) -> pos, label (nil:
-- the checkpoint itself)
local function coffee_route(p, cp)
    local inW, inE = in_rect(p, P.hall_w), in_rect(p, P.hall_e)
    if p.y < P.y_f2 - 50 and not in_lobby(p) and not (inW or inE) then
        return at_y(nearer(p, P.land_w, P.land_e), P.y_f1), "BACK UP TO 2F"  -- the 1st-floor stacks (not the lobby)
    end
    if cp <= 1 then
        if p.y < P.y_f2 - 50 and not (inW or inE) then return nil end         -- the lobby: the cup
        if inW or inE then
            if p.y < P.y_f2 + 300 then return inW and P.f2_door_w or P.f2_door_e, "OUT TO 2F" end
            return at_y(inW and P.land_w or P.land_e, P.y_f2), "DOWN TO 2F"
        end
        if p.y < P.y_f3 - 50 then return P.esc_top, "ESCALATOR DOWN" end
        local fy = P.y_f1 + 600 * math.floor((p.y - P.y_f1 + 50) / 600)
        local land = nearer(p, P.land_w, P.land_e)
        return at_y(land, fy), "STAIRS DOWN"
    end
    if p.y < P.y_f2 - 50 and not (inW or inE) then return P.esc_foot, "ESCALATOR UP" end
    if inW or inE then
        if p.y >= P.y_f6 - 50 then return inW and P.f6_door_w or P.f6_door_e, "OUT TO 6F" end
        return at_y(inW and P.land_w or P.land_e, P.y_f6), "UP TO 6F"
    end
    if p.y >= P.y_f6 - 50 then return nil end                                  -- the 6th floor: your desk
    if p.y < P.y_f3 - 50 then
        local d, west = nearer(p, P.f2_door_w, P.f2_door_e)
        return d, west and "WEST STAIRS UP" or "EAST STAIRS UP"
    end
    local fy = P.y_f1 + 600 * math.floor((p.y - P.y_f1 + 50) / 600)
    return at_y(nearer(p, P.land_w, P.land_e), fy), "STAIRS UP"
end
sgl_libwest_coffee_route = coffee_route

local function kind_coffee(spec)
    local R = sgl_mission_kind_race(spec.race)
    local K = {}
    for k, v in pairs(R) do K[k] = v end
    K.raceKind = R
    K.routeOf = coffee_route
    local race = spec.race
    local cps = race.checkpoints

    local function cup_of(ctx)
        ctx.loc.cups = ctx.loc.cups or {}     -- [globalIndex] = race number of a carrier
        return ctx.loc.cups
    end

    K.spawnLocal = function(ctx)
        R.spawnLocal(ctx)
        spawn_barriers(ctx, spec.staffDoors, "STAFF ONLY")
        spawn_boos(ctx, spec.boos, spec.booHurt or 0)
        local c = cps[1]
        ctx.objs.counterCup = spawn_prop(CUP_MODEL, c.x, c.y, c.z, function(obj) obj_scale(obj, CUP_SCALE) end)
        ctx.objs.cups = {}
    end

    K.localTick = function(ctx)
        local L = ctx.loc
        local before = L.racing and L.cp or nil
        R.localTick(ctx)
        local m = gMarioStates[0]
        local me = gNetworkPlayers[0].globalIndex
        if before == 1 and L.racing and L.cp == 2 then
            sgl_hud_toast("Coffee! Now back up to your desk on 6F", 3, SGL_HUD_GOLD)
            ctx:send("cup", { race = ctx.f, nm = gNetworkPlayers[0].name })
        end
        boos_tick(ctx, m)
        -- cups over the carriers' heads (me: while I race with it)
        local cups = cup_of(ctx)
        if L.racing and (L.cp or 1) >= 2 then cups[me] = ctx.f elseif cups[me] ~= nil and not L.racing then cups[me] = nil end
        local shown = {}
        for _, li in ipairs(ctx.players) do
            local gi = gNetworkPlayers[li].globalIndex
            if cups[gi] ~= nil and cups[gi] == ctx.f and ctx.a == SGL_RACE_RACING then
                local mm = gMarioStates[li]
                local o = ctx.objs.cups[gi]
                if not obj_ok(o, id_bhvSglLibwestProp) then
                    o = spawn_prop(CUP_MODEL, mm.pos.x, mm.pos.y + 190, mm.pos.z, function(obj) obj_scale(obj, CUP_SCALE) end)
                    ctx.objs.cups[gi] = o
                end
                if o ~= nil then           -- nil: the object pool is full (try again next frame)
                    o.oPosX, o.oPosY, o.oPosZ = mm.pos.x, mm.pos.y + 190, mm.pos.z
                    set_hidden(o, false)
                    shown[gi] = true
                end
            end
        end
        for gi, o in pairs(ctx.objs.cups or {}) do
            if not shown[gi] and obj_ok(o, id_bhvSglLibwestProp) then set_hidden(o, true) end
        end
        local cc = ctx.objs.counterCup
        if obj_ok(cc, id_bhvSglLibwestProp) then cc.oFaceAngleYaw = (cc.oFaceAngleYaw + 0x100) & 0xFFFF end
    end

    K.onEvent = function(ctx, ev, data)
        if ev == "cup" then
            if data.r == ctx.r and type(data.race) == "number" then
                cup_of(ctx)[data.gi] = data.race
                if data.gi ~= gNetworkPlayers[0].globalIndex then
                    sgl_hud_toast((data.nm or "A friend") .. " has the coffee!", 2, SGL_HUD_WHITE)
                end
            end
            return
        end
        if ev == "fin" and type(data.gi) == "number" then cup_of(ctx)[data.gi] = nil end
        R.onEvent(ctx, ev, data)
    end

    K.panel = function(ctx)
        local lines = R.panel(ctx)
        local L = ctx.loc
        if L.racing then
            local _, label = coffee_route(gMarioStates[0].pos, L.cp or 1)
            table.insert(lines, { "Way: " .. (label or ((L.cp or 1) <= 1 and "COFFEE COUNTER" or "YOUR DESK")), SGL_HUD_GOLD, 0.28 })
        else
            table.insert(lines, { "Down a stair hall to 2F, the escalator to the lobby, the cup, and back up", SGL_HUD_GREY, 0.24 })
        end
        table.insert(lines, { "Shortcut down: hop the 2F balcony rail into the lobby (6 m, no damage)", SGL_HUD_GREY, 0.24 })
        table.insert(lines, { "Boos haunt the stairwell landings: face them to freeze them", SGL_HUD_ORANGE, 0.24 })
        return lines
    end

    -- the race HUD with route markers (the framework race kind's hud draws the checkpoint marker only)
    K.hud = function(ctx)
        local L = ctx.loc
        local phase = ctx.a
        local me = gMarioStates[0]
        local live = ctx.s == SGL_MS_ACTIVE or ctx.s == SGL_MS_SUCCESS or ctx.s == SGL_MS_DONE
        if not live then return end
        if phase == SGL_RACE_LOBBY or phase == SGL_RACE_COUNTDOWN then
            if not K.inStartBox(me.pos) then sgl_hud_marker(race.start, "YOUR DESK (START)", SGL_HUD_GOLD, me) end
        end
        if phase == SGL_RACE_COUNTDOWN and ctx.c > 0 then sgl_hud_big(int_text(ctx.c), SGL_HUD_GOLD, 3) end
        if L.racing then
            local cp = L.cp or 1
            local pos, label = coffee_route(me.pos, cp)
            if pos ~= nil then
                sgl_hud_marker(up(pos, 150), label, SGL_HUD_ORANGE, me)
            else
                local c = cps[cp]
                sgl_hud_marker({ x = c.x, y = c.y + 150, z = c.z }, cp >= #cps and "YOUR DESK" or "COFFEE", SGL_HUD_BLUE, me)
            end
            if L.goAge ~= nil and L.goAge < 30 then sgl_hud_big("GO!", SGL_HUD_GREEN, 3) end
            sgl_hud_timer(L.frames or 0, djui_hud_get_screen_width() - 92, 34, "TIME")
        end
        local showBoard = phase == SGL_RACE_RESULTS or (L.finishAge ~= nil and L.finishAge < 240)
        if showBoard and L.race ~= nil and L.results ~= nil and L.results[L.race] ~= nil and #L.results[L.race] > 0 then
            local rows = {}
            for _, r in ipairs(L.results[L.race]) do table.insert(rows, { r.name, r.fr, r.fr <= race.par * 30 }) end
            local W = sgl_hud_setup(FONT_NORMAL)
            sgl_hud_board((race.title or "RACE") .. " - RACE " .. int_text(L.race), rows, W - 166, 84,
                "Par " .. sgl_hud_format_time(race.par * 30) .. "   Gold " .. sgl_hud_format_time(race.gold * 30))
        end
        barriers_hud(ctx, me)
        boos_hud(ctx, me)
    end
    return K
end

---------------------------------------------------------------------------------------------
-- HIDE AND SEEK (act 3). Pure helpers first (tools/luatest checks them).
---------------------------------------------------------------------------------------------
SGL_LIBWEST_PH = { SETUP = 0, HIDE = 1, SEEK = 2, OVER = 3, NEXT = 4 }   -- NEXT: the star collected, the next round counts in
SGL_LIBWEST_HNS = {
    HIDE_ONE = 25, HIDE_MORE = 30,    -- seconds to hide: one floor / more floors
    SEEK_TWO = 120, SEEK = 150,       -- seconds of quiet hours: 2 players / 3+ (design 7.5: 150 s rounds)
    OVER = 10,                        -- results (seconds)
    TOUCH = 140, TOUCH_DY = 160,      -- a librarian finds a hider by touch ...
    LIGHT = 600, LIGHT_LOW = 300,     -- ... or in the lantern's beam: 6 m ahead (3 m for a crouching / crawling hider)
    LIGHT_HALF = 0x0E00,              -- ... 20 degrees either side of the librarian's facing
    LIGHT_DY = 400,                   -- ... up to 4 m above or below (range tops)
    SPOT = 15,                        -- ... held in it for 0.5 s
    NEAR = 800, NEAR_DY = 300,        -- a hider's "librarian near" warning
    OOB = 120,                        -- 4 s out of the stacks = found
    CHIME = 30, CHIME_SHOW = 150,     -- the chime: every 30 s of seeking, shown 5 s
    STILL_R = 250, SNEEZE_WARN = 1050, SNEEZE = 1350, SNEEZE_R = 2000,   -- 45 s within 2.5 m: a sneeze heard 20 m away
    NOISE_EVERY = 30, PING = 60,      -- a hider's noise event at most once a second; a marker for 2 s
    RESEND = 45,                      -- an unapplied tag is sent again after 1.5 s
    WALK = 300, RUN = 600, JUMP = 650, HIT = 600, LAND = 750, HARD = 1100, WALK_V = 10, RUN_V = 20,   -- noise radii
    LANTERN_UP = 150,                 -- the lantern flame over a librarian's head
    leLight = false,                  -- also a point light (le_add_light) on every librarian: off until it has been
                                      --   seen in the game (the lighting engine changes the whole stage's look)
    beamFx = true,                    -- the beam drawn while seeking: sparkles along its axis (2, 4, 6 m) and at its two
    BEAM_Y = 60,                      --   6 m edges, 0.6 m over the librarian's feet, on every client (fun review: an
                                      --   invisible cone made dodging luck, not skill)
    NEXT = 20,                        -- after the star is collected (DONE) the next round starts in 20 s (D-pad Down: now)
    music = SEQ_EVENT_PIRANHA_PLANT,  -- quiet hours (hiding + seeking): the piranha plant's lullaby instead of the busy
                                      --   Big Boo's Haunt theme, so steps, jumps and the chime carry; nil = level music
    MUSIC_PRIORITY = 4,               -- SEQUENCE_ARGS(4, seq): over the level music (the race kind's way)
}
local HNS = SGL_LIBWEST_HNS
local PH = SGL_LIBWEST_PH
local HOW_TOUCH, HOW_LIGHT, HOW_OUT = 1, 2, 3
SGL_LIBWEST_WIN = { FOUND = 1, TIME = 2, NO_LIBRARIAN = 3, NO_HIDER = 4 }
local WIN = SGL_LIBWEST_WIN

function sgl_libwest_hns_seeker_count(n)
    if n <= 4 then return 1 end
    if n <= 8 then return 2 end
    return 3
end

-- the librarians of a round: gis sorted ascending, k = the round counter (rotates who seeks)
function sgl_libwest_hns_seekers(gis, k)
    local n = #gis
    local out = {}
    if n == 0 then return out end
    local start = math.floor(k) % n
    for i = 0, sgl_libwest_hns_seeker_count(n) - 1 do
        table.insert(out, gis[((start + i) % n) + 1])
    end
    return out
end

-- the arena floors (bit 0 = F1, bit 1 = F2, bit 2 = F3) for n players: 2 -> F2, 3 -> F2 + F3, 4+ -> F1-F3
function sgl_libwest_hns_floors(n)
    if n <= 2 then return 0x2 end
    if n == 3 then return 0x6 end
    return 0x7
end

function sgl_libwest_hns_hide_seconds(floors)
    return (floors & 0x7) == 0x2 and HNS.HIDE_ONE or HNS.HIDE_MORE
end

function sgl_libwest_hns_seek_seconds(n)
    return n <= 2 and HNS.SEEK_TWO or HNS.SEEK
end

-- floor index (1..6) of a height
local function floor_index(y)
    return clamp(math.floor((y - P.y_f1 + 100) / 600) + 1, 1, 6)
end

-- is p inside the stacks arena on one of the floors of the mask?
function sgl_libwest_in_arena(p, floors)
    if not (in_rect(p, P.arena_neck) or in_rect(p, P.arena_wing)) then return false end
    for k = 1, 3 do
        if (floors & (1 << (k - 1))) ~= 0 then
            local fy = P["y_f" .. k]
            if p.y >= fy - 100 and p.y < fy + P.clear then return true end
        end
    end
    return false
end

-- "2F WEST" / "3F MIDDLE" / "1F EAST": where a hider is, for the chime
function sgl_libwest_hns_section(p)
    local side = (p.x < -1100) and "WEST" or ((p.x > 1100) and "EAST" or "MIDDLE")
    return floor_index(p.y) .. "F " .. side
end

-- can a librarian at spos facing syaw find a hider at hpos (low = crouching / crawling)? -> "touch", "light" or nil.
-- Pure geometry; the caller adds the line of sight.
function sgl_libwest_hns_catch(spos, syaw, hpos, low)
    local dx, dy, dz = hpos.x - spos.x, hpos.y - spos.y, hpos.z - spos.z
    local d = math.sqrt(dx * dx + dz * dz)
    if d <= HNS.TOUCH and math.abs(dy) <= HNS.TOUCH_DY then return "touch" end
    if math.abs(dy) > HNS.LIGHT_DY or d > (low and HNS.LIGHT_LOW or HNS.LIGHT) then return nil end
    if math.abs(angle_diff(atan2s(dz, dx), syaw)) <= HNS.LIGHT_HALF then return "light" end
    return nil
end

-- the drawn beam (HNS.beamFx) of a librarian at pos facing yaw: 3 points along the axis (2, 4, 6 m = HNS.LIGHT) and
-- the two edges of the 6 m reach (+-LIGHT_HALF), BEAM_Y up. Pure.
function sgl_libwest_hns_beam(pos, yaw)
    local out = {}
    for _, d in ipairs({ HNS.LIGHT / 3, HNS.LIGHT * 2 / 3, HNS.LIGHT }) do
        table.insert(out, { x = pos.x + sins(yaw) * d, y = pos.y + HNS.BEAM_Y, z = pos.z + coss(yaw) * d })
    end
    for _, s in ipairs({ -1, 1 }) do
        local a = (yaw + s * HNS.LIGHT_HALF) & 0xFFFF
        table.insert(out, { x = pos.x + sins(a) * HNS.LIGHT, y = pos.y + HNS.BEAM_Y, z = pos.z + coss(a) * HNS.LIGHT })
    end
    return out
end

-- How loud is a hider's action (units of hearing radius), and its label. Pure. Silent: standing, tiptoeing (forward
-- speed <= WALK_V), crouching and crawling, falling; steps; running; jumps; punches; landings; crashes.
local NOISE_KIND = nil
local function noise_kinds()
    local k = {}
    for _, a in ipairs({ ACT_GROUND_POUND, ACT_GROUND_POUND_LAND, ACT_DIVE, ACT_DIVE_SLIDE, ACT_BUTT_SLIDE, ACT_BUTT_SLIDE_AIR,
        ACT_SLIDE_KICK, ACT_SLIDE_KICK_SLIDE, ACT_HARD_BACKWARD_GROUND_KB, ACT_HARD_FORWARD_GROUND_KB }) do k[a] = "hard" end
    for _, a in ipairs({ ACT_JUMP_LAND, ACT_FREEFALL_LAND, ACT_DOUBLE_JUMP_LAND, ACT_SIDE_FLIP_LAND, ACT_HOLD_JUMP_LAND,
        ACT_HOLD_FREEFALL_LAND, ACT_TRIPLE_JUMP_LAND, ACT_LONG_JUMP_LAND, ACT_BACKFLIP_LAND, ACT_JUMP_LAND_STOP,
        ACT_DOUBLE_JUMP_LAND_STOP, ACT_FREEFALL_LAND_STOP, ACT_SIDE_FLIP_LAND_STOP, ACT_HOLD_JUMP_LAND_STOP,
        ACT_HOLD_FREEFALL_LAND_STOP, ACT_TRIPLE_JUMP_LAND_STOP, ACT_LONG_JUMP_LAND_STOP, ACT_BACKFLIP_LAND_STOP,
        ACT_AIR_THROW_LAND, ACT_TWIRL_LAND }) do k[a] = "land" end
    for _, a in ipairs({ ACT_PUNCHING, ACT_MOVE_PUNCHING, ACT_JUMP_KICK }) do k[a] = "hit" end
    for a in pairs(DUCKING) do k[a] = "quiet" end
    for _, a in ipairs({ ACT_FREEFALL, ACT_HOLD_FREEFALL }) do k[a] = "quiet" end
    return k
end

function sgl_libwest_noise(action, forwardVel)
    NOISE_KIND = NOISE_KIND or noise_kinds()
    local kind = NOISE_KIND[action]
    if kind == "hard" then return HNS.HARD, "CRASH!" end
    if kind == "land" then return HNS.LAND, "landing" end
    if kind == "hit" then return HNS.HIT, "punch" end
    if kind == "quiet" then return 0, "quiet" end
    local group = action & ACT_GROUP_MASK
    if group == ACT_GROUP_AIRBORNE then return HNS.JUMP, "jump" end
    if group == ACT_GROUP_MOVING then
        local v = math.abs(forwardVel or 0)
        if v > HNS.RUN_V then return HNS.RUN, "running" end
        if v > HNS.WALK_V then return HNS.WALK, "steps" end
    end
    return 0, "quiet"
end

-- line of sight between two players (from a's head height ay to b at height by): a collision ray (coopdx
-- collision_find_surface_on_ray: walls, floors and ceilings, static and object collision; shelves block it)
local function line_of_sight(a, ay, b, by)
    local dx, dy, dz = b.x - a.x, (b.y + by) - (a.y + ay), b.z - a.z
    local hit = collision_find_surface_on_ray(a.x, a.y + ay, a.z, dx, dy, dz)
    if hit == nil or hit.surface == nil then return true end
    local hp = hit.hitPos
    if hp == nil then return false end
    local f = ((hp.x - a.x) ^ 2 + (hp.y - a.y - ay) ^ 2 + (hp.z - a.z) ^ 2) / math.max(1, dx * dx + dy * dy + dz * dz)
    return f >= 0.9 * 0.9
end
sgl_libwest_line_of_sight = line_of_sight

---------------------------------------------------------------------------------------------
-- HIDE AND SEEK kind: spec = { desk, deskYaw, releaseW, releaseE, spots } (LIBWEST_POINTS).
-- Synced fields: a = phase (SGL_LIBWEST_PH), c = seconds left in the phase, x = game number (a new one at every round
-- set-up; it also rotates the librarian), p = the round's players (globalIndex bits), o = librarians (bits: the
-- starting ones + every hider found, who joins them), f = hiders found (bits), g = arena floors (bits 0-2) | outcome
-- << 4 (SGL_LIBWEST_WIN). The leader: SETUP (assigns everything once 2+ players are here) -> HIDE (the librarians
-- counting) -> SEEK -> OVER (SUCCESS: the star on the circulation desk). /mission reset plays another round.
---------------------------------------------------------------------------------------------
local function my_gi() return gNetworkPlayers[0].globalIndex end

local function role_of(ctx, gi)
    local b = 1 << gi
    if (ctx.p & b) == 0 then return "watch" end
    if (ctx.o & b) ~= 0 then return "seeker" end
    return "hider"
end

local function present_mask(ctx)
    local mask = 0
    for _, li in ipairs(ctx.players) do mask = mask | (1 << gNetworkPlayers[li].globalIndex) end
    return mask
end

local function name_of_gi(ctx, gi)
    for i = 0, MAX_PLAYERS - 1 do
        local np = gNetworkPlayers[i]
        if np ~= nil and np.connected and np.globalIndex == gi then return np.name end
    end
    local L = ctx.loc
    return (L.names and L.names[gi]) or "?"
end

local function kind_hideseek(spec)
    local K = { minPlayers = 2, tickAfterSuccess = true }
    K.needPlayers = function(ctx) return 2 end
    K.roleOf = role_of

    local function seek_total(ctx) return sgl_libwest_hns_seek_seconds(popcount(ctx.p)) end
    local function elapsed(ctx) return math.max(0, seek_total(ctx) - ctx.c) end

    K.onReset = function(ctx)
        for _, f in ipairs({ "a", "c", "p", "o", "f", "g" }) do ctx:set(f, 0) end
    end
    K.onStart = function(ctx)
        ctx:set("a", PH.SETUP)
        for _, f in ipairs({ "c", "p", "o", "f", "g" }) do ctx:set(f, 0) end
    end

    local function finish(ctx, win)
        ctx:set("g", (ctx.g & 0xF) | (win << 4))
        ctx:set("c", HNS.OVER)
        ctx:set("a", PH.OVER)
        ctx:succeed()                 -- every completed round (2+ players) puts the star on the desk
    end

    K.leaderTick = function(ctx)
        if ctx.s ~= SGL_MS_ACTIVE then
            -- after a round (tickAfterSuccess): once its star is collected (DONE; also a stale star grabbed mid-round)
            -- the next round counts in by itself, rotating the librarian; D-pad Down (K.toStart) starts it at once.
            -- Not while the star is still out (SUCCESS): grabbing it in the next round would end that round.
            if ctx.s == SGL_MS_DONE then
                if ctx.a ~= PH.NEXT then
                    ctx:set("c", HNS.NEXT)
                    ctx:set("a", PH.NEXT)
                elseif ctx.c <= 0 then
                    sgl_mission_reset(ctx)
                elseif ctx.second then
                    ctx:set("c", ctx.c - 1)
                end
            end
            return
        end
        if ctx.a == PH.SETUP then
            local gis = {}
            for _, li in ipairs(ctx.players) do table.insert(gis, gNetworkPlayers[li].globalIndex) end
            table.sort(gis)
            if #gis < 2 then return end
            local pm, om = 0, 0
            for _, gi in ipairs(gis) do pm = pm | (1 << gi) end
            for _, gi in ipairs(sgl_libwest_hns_seekers(gis, ctx.r + ctx.x)) do om = om | (1 << gi) end
            local floors = sgl_libwest_hns_floors(#gis)
            ctx:set("p", pm)
            ctx:set("o", om)
            ctx:set("f", 0)
            ctx:set("g", floors)
            ctx:set("c", sgl_libwest_hns_hide_seconds(floors))
            ctx:set("x", ctx.x + 1)
            ctx:set("a", PH.HIDE)
            return
        end
        local present = present_mask(ctx)
        if ctx.a == PH.HIDE then
            if ctx.second and ctx.c > 0 then ctx:set("c", ctx.c - 1) end
            if ctx.c <= 0 then
                ctx:set("c", seek_total(ctx))
                ctx:set("a", PH.SEEK)
            end
            return
        end
        if ctx.a == PH.SEEK then
            if ctx.second and ctx.c > 0 then ctx:set("c", ctx.c - 1) end
            local hiders = ctx.p & present & ~ctx.o
            local seekers = ctx.o & present
            if hiders == 0 then
                finish(ctx, ctx.f ~= 0 and WIN.FOUND or WIN.NO_HIDER)
            elseif seekers == 0 then
                finish(ctx, WIN.NO_LIBRARIAN)
            elseif ctx.c <= 0 then
                finish(ctx, WIN.TIME)
            end
        end
    end

    -- per-game local state (ctx.loc is per framework round; a game is one round set-up, ctx.x)
    local function game_loc(ctx)
        local L = ctx.loc
        if L.game ~= ctx.x then
            L.game = ctx.x
            L.placed, L.found, L.pings, L.beam, L.sent, L.names = false, {}, {}, {}, {}, L.names or {}
            L.over, L.oob, L.anchor, L.still, L.sneezes = nil, 0, nil, 0, 0
            L.chime, L.chimeEl, L.heardAt, L.lit, L.near, L.noise, L.litAt = nil, nil, nil, false, nil, nil, nil
        end
        return L
    end
    K.gameLoc = game_loc

    -- quiet-hours music (HNS.music) while a round is hiding / seeking, on the background music queue (the level music
    -- comes back when it is stopped: the race kind's way)
    local musicOn = false
    local function set_music(on)
        if HNS.music == nil or on == musicOn then return end
        musicOn = on
        local seq = (HNS.MUSIC_PRIORITY << 8) | HNS.music
        if on then play_music(SEQ_PLAYER_LEVEL, seq, 0) else stop_background_music(seq) end
    end
    K.musicOn = function() return musicOn end

    local function tag(ctx, L, gi, how)
        if L.sent[gi] ~= nil then return end
        L.sent[gi] = ctx.age
        L.sentHow = L.sentHow or {}
        L.sentHow[gi] = how
        ctx:send("tag", { t = gi, how = how, gx = ctx.x, el = elapsed(ctx), nm = gNetworkPlayers[0].name })
    end

    K.onEvent = function(ctx, ev, data)
        if data.r ~= ctx.r or data.gx ~= ctx.x then return end
        local L = game_loc(ctx)
        local me = my_gi()
        if ev == "tag" then
            -- (numbers may arrive as integral floats: math.tointeger takes both)
            local t, how, gi = math.tointeger(data.t), math.tointeger(data.how), math.tointeger(data.gi)
            if t == nil or gi == nil or t < 0 or t >= MAX_PLAYERS or gi < 0 or gi >= MAX_PLAYERS then return end
            data.gi = gi
            local bit, from = 1 << t, 1 << gi
            local legal = (ctx.p & bit) ~= 0 and (ctx.o & bit) == 0
                and ((ctx.o & from) ~= 0 or (how == HOW_OUT and data.gi == t))
            if ctx.isLeader and ctx.s == SGL_MS_ACTIVE and ctx.a == PH.SEEK and legal and (ctx.f & bit) == 0 then
                ctx:set("f", ctx.f | bit)
                ctx:set("o", ctx.o | bit)
            end
            if (ctx.p & bit) ~= 0 and L.found[t] == nil and (legal or (ctx.f & bit) ~= 0) then
                L.found[t] = { by = data.nm or "?", byGi = data.gi, el = data.el or 0, how = how }
                L.expandUntil = ctx.age + 150
                local who = name_of_gi(ctx, t)
                if how == HOW_OUT then
                    sgl_hud_toast(t == me and "You left the stacks - FOUND! Now help the librarian"
                        or (who .. " left the stacks - found!"), 3, SGL_HUD_ORANGE)
                elseif t == me then
                    sgl_hud_toast("FOUND by " .. (data.nm or "?") .. "! You're a librarian now - find the others", 4, SGL_HUD_RED)
                    play_sound(SOUND_MENU_CAMERA_BUZZ, gGlobalSoundSource)
                elseif data.gi == me then
                    sgl_hud_toast("Found " .. who .. "!" .. (how == HOW_LIGHT and " (lantern)" or ""), 3, SGL_HUD_GOLD)
                    play_sound(SOUND_GENERAL2_RIGHT_ANSWER, gGlobalSoundSource)
                else
                    sgl_hud_toast((data.nm or "?") .. " found " .. who .. "!", 3, SGL_HUD_WHITE)
                end
            end
        elseif ev == "noise" then
            if data.gi == me or role_of(ctx, me) ~= "seeker" or ctx.a ~= PH.SEEK then return end
            if type(data.px) ~= "number" or type(data.py) ~= "number" or type(data.pz) ~= "number" or type(data.rad) ~= "number" then return end
            local pos = { x = data.px, y = data.py, z = data.pz }
            local m = gMarioStates[0]
            if dist3(m.pos, pos) > data.rad then return end
            table.insert(L.pings, { pos = pos, age = ctx.age, sn = data.sn == 1 })
            while #L.pings > 6 do table.remove(L.pings, 1) end
            play_sound(data.sn == 1 and SOUND_MARIO_COUGHING1 or SOUND_MENU_MESSAGE_APPEAR, gGlobalSoundSource)
            if data.sn == 1 then sgl_hud_toast("ACHOO! Somebody sneezed nearby", 2, SGL_HUD_GOLD) end
        end
    end

    K.spawnLocal = function(ctx)
        spawn_barriers(ctx, spec.staffDoors, "STAFF ONLY")
        ctx.objs.lanterns = {}      -- [globalIndex] = flame object over that librarian
        ctx.objs.lights = {}        -- [globalIndex] = le light id (HNS.leLight)
        ctx.objs.beams = {}         -- [globalIndex] = { sparkle objects } along that librarian's beam (HNS.beamFx)
        musicOn = false             -- a fresh act visit: the level music is playing
    end

    -- D-pad Down after a round: the next round now (once the star is collected; any player)
    K.toStart = function(ctx, m)
        if ctx.s == SGL_MS_DONE and ctx.a >= PH.OVER then
            if ctx.age - (ctx.loc.nextAt or -9999) > 60 then
                ctx.loc.nextAt = ctx.age
                ctx:send("reset", {})
            end
        elseif ctx.s == SGL_MS_SUCCESS then
            sgl_hud_toast("Grab the star on the circulation desk first", 2, SGL_HUD_ORANGE)
        end
    end

    local function any_seeker_within(ctx, pos, r)
        for _, li in ipairs(ctx.players) do
            if li ~= 0 and (ctx.o & (1 << gNetworkPlayers[li].globalIndex)) ~= 0 and dist3(gMarioStates[li].pos, pos) <= r then
                return true
            end
        end
        return false
    end

    -- the local librarian's eyes: touch, or the lantern's beam held for SPOT frames, with a line of sight
    local function seeker_tick(ctx, L, m)
        if not alive(m) or in_cutscene(m) then return end
        for _, li in ipairs(ctx.players) do
            if li ~= 0 then
                local gi = gNetworkPlayers[li].globalIndex
                local bit = 1 << gi
                if (ctx.p & bit) ~= 0 and (ctx.o & bit) == 0 and (ctx.f & bit) == 0 then
                    local tm = gMarioStates[li]
                    local low = DUCKING[tm.action] == true
                    local how = alive(tm) and sgl_libwest_hns_catch(m.pos, m.faceAngle.y, tm.pos, low) or nil
                    if how ~= nil and not line_of_sight(m.pos, 120, tm.pos, low and 40 or 80) then how = nil end
                    if how == "touch" then
                        tag(ctx, L, gi, HOW_TOUCH)
                    elseif how == "light" then
                        L.beam[gi] = (L.beam[gi] or 0) + 1
                        if L.beam[gi] >= HNS.SPOT then tag(ctx, L, gi, HOW_LIGHT) end
                    else
                        L.beam[gi] = 0
                    end
                end
            end
        end
    end

    -- the local hider: out of the stacks, noise, the sneeze, and the warnings (my view of the librarians)
    local function hider_tick(ctx, L, m)
        local me = my_gi()
        if not alive(m) then return end
        if not sgl_libwest_in_arena(m.pos, ctx.g & 0x7) then
            L.oob = L.oob + 1
            if L.oob >= HNS.OOB then tag(ctx, L, me, HOW_OUT) end
        else
            L.oob = 0
        end
        local rad, label = sgl_libwest_noise(m.action, m.forwardVel)
        L.noise = label
        if rad > 0 and ctx.age - (L.noiseAt or -9999) >= HNS.NOISE_EVERY and any_seeker_within(ctx, m.pos, rad) then
            L.noiseAt = ctx.age
            L.heardAt = ctx.age
            ctx:send("noise", { px = math.floor(m.pos.x), py = math.floor(m.pos.y), pz = math.floor(m.pos.z), rad = rad, gx = ctx.x })
        end
        -- dusty shelves: staying put (2.5 m) for 45 s ends in a sneeze
        local a = L.anchor
        if a == nil or dist2_xz(m.pos, a) > HNS.STILL_R * HNS.STILL_R or math.abs(m.pos.y - a.y) > 200 then
            L.anchor = { x = m.pos.x, y = m.pos.y, z = m.pos.z }
            L.still = 0
        else
            L.still = L.still + 1
        end
        if L.still >= HNS.SNEEZE then
            L.still = 0
            L.sneezes = L.sneezes + 1
            play_sound(SOUND_MARIO_COUGHING1, gGlobalSoundSource)
            sgl_hud_toast("ACHOO! The dust got you - the librarian may have heard", 3, SGL_HUD_ORANGE)
            ctx:send("noise", { px = math.floor(m.pos.x), py = math.floor(m.pos.y), pz = math.floor(m.pos.z), rad = HNS.SNEEZE_R,
                sn = 1, gx = ctx.x })
        end
        -- warnings
        L.lit, L.near = false, nil
        local low = DUCKING[m.action] == true
        for _, li in ipairs(ctx.players) do
            if li ~= 0 and (ctx.o & (1 << gNetworkPlayers[li].globalIndex)) ~= 0 then
                local sm = gMarioStates[li]
                if alive(sm) then
                    if sgl_libwest_hns_catch(sm.pos, sm.faceAngle.y, m.pos, low) == "light" and line_of_sight(sm.pos, 120, m.pos, low and 40 or 80) then
                        L.lit = true
                        L.litAt = ctx.age
                    end
                    local d = math.sqrt(dist2_xz(sm.pos, m.pos))
                    if math.abs(sm.pos.y - m.pos.y) < HNS.NEAR_DY and d <= HNS.NEAR and (L.near == nil or d < L.near) then L.near = d end
                end
            end
        end
    end

    -- the lantern's beam, drawn (HNS.beamFx): sparkles at 2, 4 and 6 m along a librarian's facing and at the beam's two
    -- 6 m edges (+-LIGHT_HALF), BEAM_Y over the librarian's feet; hidden when off. Pure positions: sgl_libwest_hns_beam.
    local function beam_update(ctx, gi, mm, on)
        ctx.objs.beams = ctx.objs.beams or {}
        local list = ctx.objs.beams[gi]
        if list == nil then
            if not on then return end
            list = {}
            ctx.objs.beams[gi] = list
        end
        local pts = on and sgl_libwest_hns_beam(mm.pos, mm.faceAngle.y) or {}
        for i = 1, math.max(#pts, #list) do
            local p = pts[i]
            local o = list[i]
            if p ~= nil then
                if not obj_ok(o, id_bhvSglMissionFx) then
                    o = spawn_non_sync_object(id_bhvSglMissionFx, E_MODEL_SPARKLES, p.x, p.y, p.z, function(obj)
                        obj_scale(obj, 1.3)
                        obj.oAnimState = i * 2
                    end)
                    list[i] = o
                end
                if o ~= nil then
                    o.oPosX, o.oPosY, o.oPosZ = p.x, p.y, p.z
                    set_hidden(o, false)
                end
            elseif obj_ok(o, id_bhvSglMissionFx) then
                set_hidden(o, true)
            end
        end
    end

    local function lanterns_update(ctx)
        local want = {}
        local on = (ctx.s == SGL_MS_ACTIVE) and (ctx.a == PH.HIDE or ctx.a == PH.SEEK) and ctx.p ~= 0
        if on then
            for _, li in ipairs(ctx.players) do
                local gi = gNetworkPlayers[li].globalIndex
                if (ctx.o & (1 << gi)) ~= 0 then want[gi] = gMarioStates[li] end
            end
        end
        for gi, mm in pairs(want) do
            local yaw = mm.faceAngle.y
            local x, y, z = mm.pos.x + sins(yaw) * 60, mm.pos.y + HNS.LANTERN_UP, mm.pos.z + coss(yaw) * 60
            local o = ctx.objs.lanterns[gi]
            if not obj_ok(o, id_bhvSglMissionFx) then
                o = spawn_non_sync_object(id_bhvSglMissionFx, E_MODEL_RED_FLAME, x, y, z, function(obj) obj_scale(obj, 1.6) end)
                ctx.objs.lanterns[gi] = o
            end
            if o ~= nil then               -- nil: the object pool is full (try again next frame)
                o.oPosX, o.oPosY, o.oPosZ = x, y, z
                set_hidden(o, false)
            end
            beam_update(ctx, gi, mm, HNS.beamFx and ctx.a == PH.SEEK)
            if HNS.leLight then
                local id = ctx.objs.lights[gi]
                if id == nil then
                    id = le_add_light(x + sins(yaw) * 200, y - 60, z + coss(yaw) * 200, 255, 220, 150, 900, 2.0)
                    ctx.objs.lights[gi] = id
                end
                le_set_light_pos(id, x + sins(yaw) * 200, y - 60, z + coss(yaw) * 200)
            end
        end
        for gi, o in pairs(ctx.objs.lanterns) do
            if want[gi] == nil and obj_ok(o, id_bhvSglMissionFx) then set_hidden(o, true) end
        end
        for gi in pairs(ctx.objs.beams or {}) do
            if want[gi] == nil then beam_update(ctx, gi, nil, false) end
        end
        for gi, id in pairs(ctx.objs.lights) do
            if want[gi] == nil then
                le_remove_light(id)
                ctx.objs.lights[gi] = nil
            end
        end
    end

    local function tally(ctx, L)
        local me = my_gi()
        local bit = 1 << me
        if (ctx.p & bit) == 0 then return end
        local win = ctx.g >> 4
        local startSeekers = ctx.o & ~ctx.f
        local rounds = mod_storage_load_number("sgl_lw_hns_rounds", 0) + 1
        mod_storage_save_number("sgl_lw_hns_rounds", rounds)
        if (startSeekers & bit) ~= 0 then
            if win == WIN.FOUND or win == WIN.NO_HIDER then
                mod_storage_save_number("sgl_lw_hns_librarian", mod_storage_load_number("sgl_lw_hns_librarian", 0) + 1)
                L.won = true
            end
        elseif (ctx.f & bit) == 0 and (win == WIN.TIME or win == WIN.NO_LIBRARIAN) then
            mod_storage_save_number("sgl_lw_hns_hider", mod_storage_load_number("sgl_lw_hns_hider", 0) + 1)
            L.won = true
        end
    end

    K.localTick = function(ctx)
        local L = game_loc(ctx)
        local m = gMarioStates[0]
        local me = my_gi()
        local role = role_of(ctx, me)
        local active = ctx.s == SGL_MS_ACTIVE
        -- remember the players' names (the results board names players who left)
        if ctx.p ~= 0 and ctx.age % 30 == 0 then
            for _, li in ipairs(ctx.players) do L.names[gNetworkPlayers[li].globalIndex] = gNetworkPlayers[li].name end
        end
        if active and ctx.a == PH.HIDE and ctx.p ~= 0 then
            if not L.placed then
                if role == "watch" then
                    L.placed = true
                elseif can_teleport(m) then
                    if role == "seeker" then
                        teleport(m, spec.desk, spec.deskYaw or 0)
                    else
                        local rank = 0      -- hiders alternate between the west and the east corridor
                        for gi = 0, me - 1 do
                            if (ctx.p & (1 << gi)) ~= 0 and (ctx.o & (1 << gi)) == 0 then rank = rank + 1 end
                        end
                        teleport(m, (rank % 2 == 0) and spec.releaseW or spec.releaseE, 0x8000)
                    end
                    play_sound(SOUND_MENU_EXIT_PIPE, gGlobalSoundSource)
                    L.placed = true
                end
            end
            if role == "seeker" then ctx.freeze = true end   -- counting at the desk (the framework clears the pad)
        end
        if active and ctx.a == PH.SEEK then
            if L.seekAt == nil then
                L.seekAt = ctx.age
                play_sound(SOUND_GENERAL2_RIGHT_ANSWER, gGlobalSoundSource)
            end
            if role == "seeker" then seeker_tick(ctx, L, m) elseif role == "hider" then hider_tick(ctx, L, m) end
            -- unapplied tags: send again (the leader may have left before it saw them)
            local again = {}
            for gi, at in pairs(L.sent) do
                if (ctx.f & (1 << gi)) == 0 and ctx.age - at >= HNS.RESEND and (L.sentHow[gi] == HOW_OUT or role == "seeker") then
                    table.insert(again, gi)
                end
            end
            for _, gi in ipairs(again) do
                L.sent[gi] = nil
                tag(ctx, L, gi, L.sentHow[gi])
            end
            -- the chime: every CHIME s the librarians hear where the hiders are (floor + side)
            local el = elapsed(ctx)
            if el > 0 and el % HNS.CHIME == 0 and L.chimeEl ~= el then
                L.chimeEl = el
                if role == "seeker" then
                    local seen, list = {}, {}
                    for _, li in ipairs(ctx.players) do
                        local gi = gNetworkPlayers[li].globalIndex
                        if (ctx.p & (1 << gi)) ~= 0 and (ctx.o & (1 << gi)) == 0 then
                            local s = sgl_libwest_hns_section(gMarioStates[li].pos)
                            if not seen[s] then
                                seen[s] = true
                                table.insert(list, s)
                            end
                        end
                    end
                    table.sort(list)
                    if #list > 0 then
                        L.chime = { text = table.concat(list, ", "), age = ctx.age }
                        play_sound(SOUND_MENU_STAR_SOUND, gGlobalSoundSource)
                    end
                elseif role == "hider" then
                    sgl_hud_toast("The quiet-hours chime: the librarian knows your floor and side!", 3, SGL_HUD_ORANGE)
                    L.expandUntil = ctx.age + 150
                end
            end
        end
        set_music(active and ctx.p ~= 0 and (ctx.a == PH.HIDE or ctx.a == PH.SEEK))
        -- a hider outside the stacks while hiding: warned now (no count yet; it starts at READY OR NOT)
        L.hideOut = active and ctx.a == PH.HIDE and role == "hider" and alive(m)
            and not sgl_libwest_in_arena(m.pos, ctx.g & 0x7)
        if ctx.a >= PH.OVER and ctx.p ~= 0 and L.over == nil then
            L.over = ctx.age
            tally(ctx, L)
            local win = ctx.g >> 4
            local text = (win == WIN.FOUND and "Every hider found - the night librarians win!")
                or (win == WIN.NO_HIDER and "No hiders left - the night librarians win!")
                or (win == WIN.NO_LIBRARIAN and "The librarian went home - the hiders win!")
                or "Quiet hours are over - the hiders win!"
            sgl_hud_toast(text, 4, SGL_HUD_GOLD)
        end
        lanterns_update(ctx)
    end

    K.onLeave = function(ctx)
        for gi, id in pairs(ctx.objs.lights or {}) do
            le_remove_light(id)
            ctx.objs.lights[gi] = nil
        end
        set_music(false)
    end

    K.panel = function(ctx)
        local L = game_loc(ctx)
        local me = my_gi()
        local role = role_of(ctx, me)
        local lines = {}
        local floors = ctx.g & 0x7
        local fl = (floors == 0x2 and "2F") or (floors == 0x6 and "2F-3F") or "1F-3F"
        local hidersLeft = popcount(ctx.p & present_mask(ctx) & ~ctx.o)
        local hidersAll = popcount(ctx.p & ~(ctx.o & ~ctx.f))
        if ctx.p == 0 then
            table.insert(lines, { "Picking tonight's librarian...", SGL_HUD_WHITE })
        elseif ctx.a == PH.HIDE then
            table.insert(lines, { string.format("HIDE! %d s - the librarian is counting", ctx.c), SGL_HUD_ORANGE })
        elseif ctx.a == PH.SEEK then
            table.insert(lines, { string.format("Quiet hours %s   hiders left %d/%d", sgl_hud_format_seconds(ctx.c), hidersLeft,
                hidersAll), SGL_HUD_WHITE })
        elseif ctx.a == PH.OVER then
            table.insert(lines, { L.won and "You won this round!" or "Round over", L.won and SGL_HUD_GREEN or SGL_HUD_WHITE })
            if ctx.s == SGL_MS_SUCCESS then
                table.insert(lines, { "Grab the star on the desk - then the next round", SGL_HUD_GREY, 0.26 })
            end
        elseif ctx.a == PH.NEXT then
            table.insert(lines, { string.format("Next round in %d s - D-pad Down: now", math.max(0, math.floor(ctx.c))),
                SGL_HUD_GOLD })
        end
        if role == "seeker" then
            table.insert(lines, { "You: NIGHT LIBRARIAN (stacks " .. fl .. ")", SGL_HUD_GOLD, 0.3 })
            table.insert(lines, { "Touch a hider, or hold them in your lantern light", SGL_HUD_GREY, 0.26 })
            if L.chime ~= nil then table.insert(lines, { "Last chime: " .. L.chime.text, SGL_HUD_ORANGE, 0.28 }) end
        elseif role == "hider" then
            if (ctx.f & (1 << me)) ~= 0 then
                table.insert(lines, { "You were found", SGL_HUD_RED, 0.3 })
            else
                table.insert(lines, { "You: HIDER (stacks " .. fl .. " only)", SGL_HUD_GREEN, 0.3 })
                local noise = L.noise or "quiet"
                table.insert(lines, { "Noise: " .. noise:upper(), noise == "quiet" and SGL_HUD_GREEN or SGL_HUD_ORANGE, 0.28 })
                if L.still >= HNS.SNEEZE_WARN then
                    table.insert(lines, { string.format("Dusty! You'll sneeze in %d s - move!", math.max(0, (HNS.SNEEZE - L.still) // 30)),
                        SGL_HUD_RED, 0.28 })
                end
                table.insert(lines, { "Tiptoe or crawl (Z) near the librarian; crouch to shrink in the light", SGL_HUD_GREY, 0.24 })
                local spot = spec.spots and spec.spots[((ctx.x + me) % #spec.spots) + 1]
                if spot ~= nil and ctx.a == PH.HIDE then table.insert(lines, { "Idea: " .. spot.name, SGL_HUD_GREY, 0.24 }) end
            end
        else
            table.insert(lines, { "Watching - you're in the next round", SGL_HUD_GREY, 0.28 })
        end
        local hw = mod_storage_load_number("sgl_lw_hns_hider", 0)
        local lw = mod_storage_load_number("sgl_lw_hns_librarian", 0)
        table.insert(lines, { string.format("Your record: hider wins %d, librarian wins %d", hw, lw), SGL_HUD_GREY, 0.24 })
        return lines
    end

    local function board(ctx, L)
        local rows = {}
        local total = seek_total(ctx)
        local startSeekers = ctx.o & ~ctx.f
        local libs = {}
        for gi = 0, MAX_PLAYERS - 1 do
            local bit = 1 << gi
            if (ctx.p & bit) ~= 0 then
                if (startSeekers & bit) ~= 0 then
                    table.insert(libs, name_of_gi(ctx, gi))
                else
                    local f = L.found[gi]
                    local found = (ctx.f & bit) ~= 0
                    local el = (found and f ~= nil) and f.el or total
                    table.insert(rows, { name_of_gi(ctx, gi) .. (found and "" or "  SAFE"), el * 30, not found })
                end
            end
        end
        table.sort(rows, function(a, b) return a[2] > b[2] end)
        local W = sgl_hud_setup(FONT_NORMAL)
        sgl_hud_board("QUIET HOURS - ROUND " .. int_text(ctx.x), rows, W - 166, 84, "Librarian: " .. table.concat(libs, ", "))
    end

    K.hud = function(ctx)
        local L = game_loc(ctx)
        local m = gMarioStates[0]
        local me = my_gi()
        local role = role_of(ctx, me)
        if ctx.p == 0 then return end
        local W, H = sgl_hud_setup(FONT_NORMAL)
        if ctx.s == SGL_MS_ACTIVE and ctx.a == PH.HIDE then
            if role == "seeker" then
                -- eyes closed: the counting librarian's screen goes dark
                sgl_hud_rect(0, 0, W, H, 4, 6, 14, 235)
                sgl_hud_text_center("YOU ARE TONIGHT'S NIGHT LIBRARIAN", W / 2, H / 2 - 46, 0.4, SGL_HUD_GOLD, 1)
                sgl_hud_big(int_text(ctx.c), SGL_HUD_WHITE, 3, 1, H / 2 - 22)
                sgl_hud_text_center("counting... no peeking!", W / 2, H / 2 + 26, 0.3, SGL_HUD_GREY, 1)
            elseif role == "hider" then
                sgl_hud_big("HIDE! " .. int_text(ctx.c), SGL_HUD_ORANGE, 1.6)
                if L.hideOut then
                    -- out of the round's stacks while hiding: at READY OR NOT the 4 s count starts
                    local fl = ((ctx.g & 0x7) == 0x2 and "2F") or ((ctx.g & 0x7) == 0x6 and "2F-3F") or "1F-3F"
                    sgl_hud_text_center("OUT OF BOUNDS - hide in the stacks (" .. fl .. ")", W / 2, 120, 0.36, SGL_HUD_RED, 1)
                    sgl_hud_marker(up(nearer(m.pos, spec.releaseW, spec.releaseE), 150), "THE STACKS", SGL_HUD_GOLD, m)
                end
            end
            return
        end
        if ctx.s == SGL_MS_ACTIVE and ctx.a == PH.SEEK then
            if L.seekAt ~= nil and ctx.age - L.seekAt < 45 then sgl_hud_big("READY OR NOT!", SGL_HUD_GOLD, 1.8) end
            if role == "seeker" then
                for _, pg in ipairs(L.pings) do
                    if ctx.age - pg.age < HNS.PING then
                        sgl_hud_marker(up(pg.pos, 120), pg.sn and "ACHOO!" or "NOISE", pg.sn and SGL_HUD_RED or SGL_HUD_ORANGE, m)
                    end
                end
                if L.chime ~= nil and ctx.age - L.chime.age < HNS.CHIME_SHOW then
                    sgl_hud_prompt("CHIME! Hiders: " .. L.chime.text, "the quiet-hours chime tells the librarians every 30 s")
                end
                for _, li in ipairs(ctx.players) do
                    local gi = gNetworkPlayers[li].globalIndex
                    if li ~= 0 and (ctx.o & (1 << gi)) ~= 0 then
                        sgl_hud_marker(up(gMarioStates[li].pos, 200), "LIBRARIAN", SGL_HUD_GREY, nil, true)
                    elseif li ~= 0 and (L.beam[gi] or 0) > 0 and (ctx.f & (1 << gi)) == 0 then
                        -- the beam is on a hider: keep facing them
                        sgl_hud_marker(up(gMarioStates[li].pos, 200),
                            string.format("SPOTTED %d%%", math.min(100, math.floor(L.beam[gi] * 100 / HNS.SPOT))), SGL_HUD_GOLD, nil, true)
                    end
                end
            elseif role == "hider" and (ctx.f & (1 << me)) == 0 then
                if L.lit then
                    sgl_hud_big("IN THE LIGHT!", SGL_HUD_RED, 1.5)
                elseif L.near ~= nil then
                    sgl_hud_prompt(string.format("The librarian is near (%d m)", math.floor(L.near / 100 + 0.5)),
                        "keep still and quiet, or slip away")
                end
                if L.oob > 0 then
                    sgl_hud_big("BACK TO THE STACKS " .. math.max(0, (HNS.OOB - L.oob) // 30 + 1), SGL_HUD_RED, 1.3, 1, 120)
                    sgl_hud_marker(up(nearer(m.pos, spec.releaseW, spec.releaseE), 150), "THE STACKS", SGL_HUD_GOLD, m)
                end
                if L.heardAt ~= nil and ctx.age - L.heardAt < 30 then
                    sgl_hud_text_center("they heard that...", W / 2, 120, 0.32, SGL_HUD_ORANGE, 1)
                end
            end
        end
        if ctx.a >= PH.OVER and L.over ~= nil and ctx.age - L.over < 300 then board(ctx, L) end
        if ctx.a == PH.NEXT and ctx.c > 0 and ctx.c <= HNS.NEXT - 10 then
            -- (the first 10 s belong to the framework's "leave together" prompt in the same spot)
            sgl_hud_prompt("Next round in " .. int_text(ctx.c) .. " s", "D-pad Down: start it now (the librarian rotates)")
        end
    end
    return K
end

-- roles as model states, every frame for every player (the bundled hide-and-seek mod's way): librarians metal, players
-- outside the round see-through
local function hns_models(m)
    local ctx = sgl_mission_ctx()
    if ctx == nil or ctx.def == nil or ctx.def.id ~= "libwest_hideseek" or ctx.dormant then return end
    if gNetworkPlayers[0].currLevelNum ~= ctx.def.level or ctx.s ~= SGL_MS_ACTIVE or ctx.p == 0 then return end
    if ctx.a ~= PH.HIDE and ctx.a ~= PH.SEEK then return end
    local np = gNetworkPlayers[m.playerIndex]
    local bs = m.marioBodyState
    if np == nil or not np.connected or bs == nil then return end
    local bit = 1 << np.globalIndex
    if (ctx.o & bit) ~= 0 then
        bs.modelState = bs.modelState | MODEL_STATE_METAL
    elseif (ctx.p & bit) == 0 then
        bs.modelState = bs.modelState | MODEL_STATE_NOISE_ALPHA
    end
end

-- Nametags (fix round): coopdx v1.5.1 draws every player's nametag through walls and floors at any distance (nametags.c:
-- no occlusion, no distance cut; only crouching / crawling players are skipped), which gives every hider away. While a
-- round is hiding / seeking, the tags of the round's players are hidden on every client: HOOK_ON_NAMETAGS_RENDER
-- returns an empty name and a position behind the camera (nametags.c projects the returned pos again and skips the
-- tag when djui_hud_world_pos_to_screen_pos fails, i.e. behind the camera). Nothing global is changed (the bundled
-- hide-and-seek mod sets gServerSettings.nametags = 0, which a joining client would inherit from the host).
function sgl_libwest_hns_hide_tag(playerIndex)
    local ctx = sgl_mission_ctx()
    if ctx == nil or ctx.def == nil or ctx.def.id ~= "libwest_hideseek" or ctx.dormant then return false end
    if gNetworkPlayers[0].currLevelNum ~= ctx.def.level or ctx.s ~= SGL_MS_ACTIVE or ctx.p == 0 then return false end
    if ctx.a ~= PH.HIDE and ctx.a ~= PH.SEEK then return false end
    local np = gNetworkPlayers[playerIndex]
    if np == nil or not np.connected then return false end
    return (ctx.p & (1 << np.globalIndex)) ~= 0
end

local function hns_nametag(playerIndex, pos)
    if not sgl_libwest_hns_hide_tag(playerIndex) then return nil end
    local out = { name = "" }
    local ls = gLakituState
    if ls ~= nil and ls.curPos ~= nil and ls.curFocus ~= nil then
        local cp, cf = ls.curPos, ls.curFocus
        out.pos = { x = cp.x + (cp.x - cf.x) * 4, y = cp.y + (cp.y - cf.y) * 4, z = cp.z + (cp.z - cf.z) * 4 }
    end
    return out
end

---------------------------------------------------------------------------------------------
-- act 1: ALL-NIGHTER
---------------------------------------------------------------------------------------------
sgl_mission_register({
    id = "libwest_allnighter",
    pointsFile = POINTS_FILE,
    level = LEVEL_BBH,
    act = LIBWEST_MISSION_ACTS.allnighter,
    title = "ALL-NIGHTER",
    objective = "Climb to the 6th floor's big window - mind the Boos!",
    star = P.climb_star,            -- spawned at the big window over the Plaza (no level-script star)
    starFrom = at_y(P.climb_star, P.y_f6),   -- rising out of the floor below it (the 4 m hump stays under 5.4 m)
    starCutsceneRange = 3000,
    probes = { probe(P.spawn, "the 1st-floor vestibule"), probe(P.tower_door, "the north roof terrace"),
        probe(P.climb_goal, "the 6th floor's big window") },
    compactPanel = true,
    kind = kind_allnighter({
        reach = {
            goal = P.climb_goal,
            goalRadius = 250,       -- at the window (the aisle between the window desk and the reading tables) ...
            goalBelow = 50,         -- ... with the feet on floor 6
            goalLabel = "THE BIG WINDOW",
            zone = P.zone,
            ground = P.y_f1,        -- 0 m = the lobby
            milestones = {
                { name = "2nd-floor stacks", y = P.y_f2 },
                { name = "the roof terrace", y = P.y_f4 },
                { name = "6th floor", y = P.y_f6 },
            },
        },
        barriers = P.stair_doors,   -- {} opens the west / east stair halls below 4F (barriers: 0.3 m past both jambs,
                                    --   5 m tall, 0.4 m thick)
        staffDoors = P.staff_doors, -- the 5th floor stays staff only
        shaft = P.shaft_door,       -- the out-of-order elevator shaft: a wall-kick alternative (marked from 2F)
        ladders = P.ladders,        -- {} removes the rolling ladders
        boos = P.boos1,             -- {} removes the Boos
        booHurt = 4,                -- a Boo's touch: one wedge + a knock-back
        booSpeed = 12,              -- they chase a turned back at 12 units a frame (default SPEED 7: the fun review
                                    --   found act 1's Boos too slow to matter; a runner still outpaces them)
        start = P.spawn,            -- D-pad Down twice: back to the lobby (stuck in the shaft pit, lost, ...)
        startYaw = 0x8000,
    }),
})

---------------------------------------------------------------------------------------------
-- act 2: COFFEE RUN
---------------------------------------------------------------------------------------------
sgl_mission_register({
    id = "libwest_coffee",
    pointsFile = POINTS_FILE,
    level = LEVEL_BBH,
    act = LIBWEST_MISSION_ACTS.coffee,
    title = "COFFEE RUN",
    objective = "Coffee from the lobby, back to your 6th-floor desk!",
    star = up(P.run_start, 80),     -- at your desk, 0.8 m up
    starFrom = P.run_start,
    starCutsceneRange = 2500,
    probes = { probe(P.run_start, "the 6th-floor reading room"), probe(P.cup_stand, "the lobby's coffee counter"),
        probe(P.esc_top, "the 2nd-floor arrival hall") },
    kind = kind_coffee({
        race = {
            start = P.run_start,
            startRadius = 170,      -- the aisle between the reading tables and the group rooms
            startLabel = "YOUR DESK (6F READING ROOM)",
            checkpoints = {
                { x = P.cup.x, y = P.cup.y, z = P.cup.z, name = "THE COFFEE COUNTER (LOBBY)", r = 170 },
                { x = P.run_start.x, y = P.run_start.y, z = P.run_start.z, name = "YOUR DESK (6F)", r = 200 },
            },
            cpRadius = 200,
            cpBelow = 150,          -- the cup is on a 1.1 m counter: standing in front of it counts
            cpAbove = 300,
            par = 60,               -- design 7.5: beat par 60 s
            gold = 45,
            timeout = 180,
            lobbyWait = 10,
            countdown = 3,
            resultsSeconds = 8,
            finishGrace = 45,
            pbKey = "sgl_lw_coffee_pb",
            title = "COFFEE RUN",
            music = SEQ_LEVEL_SLIDE,    -- Koopa-the-Quick race music while racing
        },
        boos = P.boos2,
        booHurt = 0,                -- stairwell Boos only knock you back (a race: it costs time, never a life)
        staffDoors = P.staff_doors, -- the 5th floor stays staff only
    }),
})

---------------------------------------------------------------------------------------------
-- act 3 (co-op / competitive): QUIET HOURS HIDE & SEEK - 2P
---------------------------------------------------------------------------------------------
sgl_mission_register({
    id = "libwest_hideseek",
    pointsFile = POINTS_FILE,
    level = LEVEL_BBH,
    act = LIBWEST_MISSION_ACTS.hideseek,
    title = "QUIET HOURS HIDE & SEEK - 2P",
    objective = "Hide in the stacks, or find them all as the librarian!",
    star = P.desk_star,             -- on the circulation desk counter (design 7.5)
    starFrom = P.desk,              -- from the patron side of the desk (the hump clears the 5.4 m ceiling)
    starCutsceneRange = 2500,
    probes = { probe(P.desk, "the circulation desk"), probe(P.release_w, "the stacks' west corridor"),
        probe(P.hide_spots[8], "the 3rd-floor reading counters") },
    kind = kind_hideseek({
        desk = P.desk,
        deskYaw = 0x0000,           -- counting faces south, away from the stacks
        releaseW = P.release_w,
        releaseE = P.release_e,
        spots = P.hide_spots,
        staffDoors = P.staff_doors, -- the 5th floor stays staff only (out of bounds anyway)
    }),
})

hook_event(HOOK_MARIO_UPDATE, hns_models)
hook_event(HOOK_ON_NAMETAGS_RENDER, hns_nametag)
