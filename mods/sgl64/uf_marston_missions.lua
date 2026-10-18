-- Super Gatorlator 64: Marston Science Library (course 4, LEVEL_CCM, hub door 4 "Marston") missions, on the
-- framework in sgl_mission.lua (docs/game_design.md 7.3, docs/flow.md 5). An INTERIOR stage: five floors 6 m apart
-- (F1 the basement at Y -600, F2 the entrance floor at Y 0 ... F5 at Y 1800), a 13 x 15 m atrium open from the
-- F2 court to a skylight (data/uf/marston_layout.json, docs/marston_layout.md).
--
--   act 1  OUT-OF-ORDER ELEVATOR      solo (design 7.3 act 1): the elevator is out of order and the stair halls are
--                                     "closed for renovation" (act-1-only barriers in front of every stair, core
--                                     and elevator 2 door of floors 1-4). Climb from the F2 lobby up the atrium:
--                                     the grand stair to the F3 balcony, a book-cart lift on the atrium's east side
--                                     to F4, around the F4 balcony, a second lift on the west side to F5 (Lua
--                                     platforms on the network area timer, like the Reitz window-washer lift), then
--                                     the 5th-floor north reading room, where the mission spawns the star. Flying
--                                     overdue books swoop across the atrium at anyone on the F3 / F4 balconies (duck
--                                     or punch them). Skilled players can wall-kick up the out-of-order elevator
--                                     shaft instead (stage geometry: open on F2-F5). The basement is closed as well:
--                                     whoever slides down the F2 book chute to F1 is sent back to the lobby. The lifts
--                                     chain (lift B waits at F4 when a runner from lift A gets there) and are a safe
--                                     zone from the books.
--   act 2  SHHH! LOST TEXTBOOKS       solo-friendly (design 7.3 acts 2 + 4): 8 lost textbooks on the silent 5th
--                                     floor while three Shushers (Toad librarians, local copies on the network area
--                                     timer) patrol it. Running, jumping, landing and punching make noise; tiptoeing
--                                     (stick tilted a little, or hold L: keyboard Left Shift) and crawling (Z) are
--                                     silent; each Shusher's marker is coloured by how loud you may be at your
--                                     distance (green run, white walk, red tiptoe). A Shusher who hears you
--                                     (or sees you right in front of it, or bumps into you) sends you back to the
--                                     stairwell: never any damage. Found books stay found (shared); the star waits
--                                     at the west window desk, still on the quiet floor. Co-op: a Shusher that half-
--                                     hears a player stops and turns to look at them (on every client), so a friend
--                                     can lure it while another sneaks past.
--   act 3  STUDY ROOM BOOKING - 2P    co-op, 2-4 players (design 7.3 act 3): booking kiosks on different floors
--                                     (2 players: 1F + 5F, 3: 1F + 4F + 5F, 4: all four). Each kiosk's screen shows
--                                     the OTHER kiosks' LibCal-style booking codes (1-3 punches), so the players
--                                     swap codes; book every lit kiosk (its code) within 4 s of the first to open
--                                     glass room L129 on floor 1: its door opens and the star is inside. When
--                                     everyone stands at a kiosk the HUD counts them in. The first trip to a kiosk is
--                                     on foot (D-pad Down only returns you to one you have reached).
--   acts 4-6 "COMING SOON - ..." in course.lua (design 7.3 acts 4, 5, 6): free roam, no star.
-- Act order (course.lua header): playable acts 1..3 with no gap, the solo ones first. Every star is spawned by its
-- mission (spawn_default_star from the controller loop, star id = act - 1): the level script must NOT place a bhvStar
-- for acts 1-3. Each mission checks the stage geometry first (probes on MARSTON_POINTS): if levels/ccm is not the
-- real Marston interior they stay offline (/mission force overrides), and then spawn nothing (no barriers, lifts).
--
-- File name: coopdx loads a mod's files in strcmp order of their names. This file registers missions at load, so it
-- must sort AFTER sgl_mission.lua (docs/flow.md 7 step 9): "uf_marston_missions.lua" sorts after sgl_mission.lua,
-- swamp_missions.lua and uf_lake_missions.lua ("ccm_..." or "marston_..." would load before the framework).
--
-- The CCM slot: nothing here depends on vanilla Cool, Cool Mountain. Every object is this file's own Lua behaviour
-- or a vanilla model on it (no penguins, snowmen, slide or snow behaviours are spawned); music, terrain, snowfall, fog
-- and the areas belong to the stage build (levels/ccm: SEQ_LEVEL_INSIDE_CASTLE, TERRAIN_STONE, ENVFX_MODE_NONE, area 1
-- only, so no slide area and none of CCM's area-2 camera triggers) and the camera to levels.lua (rom-hack camera).
--
-- Networking: the lifts and the Shushers' patrols are pure functions of get_network_area_timer() (identical on every
-- client of the area). A Shusher pauses (to shush someone, or to look at a noise) through the synced field g: pause
-- units per Shusher, written by the leader on "shh" / "hm" events; each client spends them one frame at a time, so the
-- copies agree again once the pause is over (a late joiner starts in step). Each player is judged only by their own
-- client against their own copies (noise is local, as design 7.3 says). Textbooks: reliable "book" events, the leader
-- ORs them into f (re-sent after 3 s while unapplied, like the Reitz tokens). Kiosks: reliable "kiosk" events, the
-- LEADER timestamps them on receipt (design 7.3) and books the room when every lit kiosk is within the window.

---------------------------------------------------------------------------------------------
-- ALL Marston mission coordinates, in game units (area 1 of LEVEL_CCM). Swap values here only.
-- Source: data/uf/marston_points.json once the stage build writes it (points measured on the BUILT collision);
-- until then data/uf/marston_layout.json (the layout research, map metres: its "missions" anchors and its geometry)
-- through the stages.json transform of the marston window (centre (-59.6, -98.9) m):
--   X = (x + 59.6) * 100,  Y = z * 100,  Z = -(y + 98.9) * 100.
-- Y is the floor (Mario's feet) at a standing point: F1 -600, F2 0 (= the hub's grade), F3 600, F4 1200, F5 1800
-- (6 m storeys, 5.4 m clear under a 0.6 m slab; real storeys are ~4.2 m, docs/marston_layout.md 11).
-- tools/luatest/check_marston_points.py recomputes every value (derived ones with its RULES), fails on drift > 0.5 m,
-- checks the layout (walkable floor, props, columns, patrol clearance, lifts inside the void, barriers on every door,
-- kiosk distances, star humps under the ceilings) and, once levels/ccm exists, the built collision; --print prints
-- fresh values and their sources.
-- (The table is built by a local function so its numbers are that function's constants, not the main chunk's: with
-- more than 256 main-chunk constants luac stops using SETTABUP for globals, which tools/luatest/check_globals.lua reads.)
---------------------------------------------------------------------------------------------
local function marston_points() return {
    spawn = { x = -790, y = 0, z = -1510 },                     -- missions.spawn (0x0A: F2 lobby, facing the atrium)
    zone = { x0 = -3122, x1 = 2606, z0 = -4640, z1 = 2610 },    -- bounding box of every floor outline (heights count here)
    y_f1 = -600,                                                -- floors[].z_game_m (F1 = the basement)
    y_f2 = 0,
    y_f3 = 600,
    y_f4 = 1200,
    y_f5 = 1800,
    rail = 100,                                                 -- atrium.game.railing_m (1 m balcony railings)
    clear = 540,                                                -- clear_height_game_m (5.4 m under every slab)

    -- act 1 (design 1): the climb
    climb_goal = { x = -240, y = 1800, z = -1890 },             -- F5 north reading room (an 8 m goal disc)
    climb_star = { x = -440, y = 1880, z = -1930 },             -- its middle aisle, 0.8 m up (the 4 m spawn hump
                                                                --   stays under the 5.4 m ceiling)
    stair_foot = { x = -365, y = 0, z = -440 },                 -- grand_stair.game.bottom_m (F2 -> F3)
    atrium = { x0 = -540, x1 = 777, z0 = -590, z1 = 890 },      -- vertical.atrium.poly_m (the void, F3-F5)
    lift_a = { x = 607, z = 150, bottom = 700, top = 1300, half = 110 },   -- book-cart lift A (east side of the
                                                                --   void, 0.6 m in): deck top F3 railing -> F4 railing
    lift_b = { x = -370, z = 150, bottom = 1300, top = 1900, half = 110 }, -- lift B (west side): F4 -> F5 railing
    board_a = { x = 897, y = 600, z = 150 },                    -- F3 balcony beside lift A (route marker)
    board_b = { x = -650, y = 1200, z = 150 },                  -- F4 walkway beside lift B (route marker)
    shaft_door = { x = -1565, y = 0, z = -730 },                -- 1 m in front of elevator 1's F2 door (the shaft)
    stair_doors = {                                             -- act 1 barriers: NE stair, SW stair, core stair and
                                                                --   elevator 2 doors of F1-F4 (vertical[].game.doors)
        { x0 = 730, z0 = -1990, x1 = 990, z1 = -1990, y = -600 },
        { x0 = -2060, z0 = 1150, x1 = -2060, z1 = 1390, y = -600 },
        { x0 = -1010, z0 = -1490, x1 = -1010, z1 = -1250, y = -600 },
        { x0 = -1330, z0 = -830, x1 = -1180, z1 = -830, y = -600 },
        { x0 = 730, z0 = -1990, x1 = 990, z1 = -1990, y = 0 },
        { x0 = -1986, z0 = 950, x1 = -1986, z1 = 1170, y = 0 },
        { x0 = -1010, z0 = -1490, x1 = -1010, z1 = -1250, y = 0 },
        { x0 = -1330, z0 = -830, x1 = -1180, z1 = -830, y = 0 },
        { x0 = 730, z0 = -1990, x1 = 990, z1 = -1990, y = 600 },
        { x0 = -1986, z0 = 1070, x1 = -1986, z1 = 1310, y = 600 },
        { x0 = -1010, z0 = -1490, x1 = -1010, z1 = -1250, y = 600 },
        { x0 = -1330, z0 = -830, x1 = -1180, z1 = -830, y = 600 },
        { x0 = 730, z0 = -1990, x1 = 990, z1 = -1990, y = 1200 },
        { x0 = -2240, z0 = 890, x1 = -2040, z1 = 890, y = 1200 },
        { x0 = -1010, z0 = -1490, x1 = -1010, z1 = -1250, y = 1200 },
        { x0 = -1330, z0 = -830, x1 = -1180, z1 = -830, y = 1200 },
    },

    -- act 2 (design 2 + 4): the silent 5th floor
    quiet_start = { x = 560, y = 1800, z = -2140 },             -- design_act2_quiet_floor.start (by the NE stair
                                                                --   hall's west door; also where a Shusher sends you)
    quiet_star = { x = -2750, y = 1880, z = 10 },               -- the west window desk's aisle, 0.8 m up
    books = {                                                   -- the 8 lost textbooks (y = the surface they lie on)
        { x = -640, y = 1875, z = -2880, name = "VIEW COUNTER" },     -- north window counter (0.75 m)
        { x = 260, y = 1875, z = -2590, name = "READING TABLE" },     -- north reading table 1 (0.75 m)
        { x = 460, y = 1800, z = -730, name = "ATRIUM RAIL" },        -- by the atrium railing, north room
        { x = 1260, y = 1800, z = 110, name = "EAST TERRACE" },       -- the upper east terrace (outdoors: NE stair hall)
        { x = -1415, y = 1800, z = -710, name = "ELEVATOR LOBBY" },   -- the corridor south of the core
        { x = -2475, y = 1875, z = -1055, name = "COMPUTER ROW" },    -- the west wing's computer row (0.75 m)
        { x = -1690, y = 1930, z = 210, name = "CARREL TOP" },        -- on top of carrel row 3 (1.3 m: a jump)
        { x = -1915, y = 1800, z = 560, name = "BACK AISLE" },        -- between carrel rows 2 and 3
    },
    patrol_n = {                                                -- Shusher 1: north reading room (back and forth)
        { x = 60, z = -2090 },
        { x = -900, z = -2090 },
        { x = -900, z = -900 },
        { x = 60, z = -900 },
    },
    patrol_w = {                                                -- Shusher 2: west reading room (a loop)
        { x = -2365, z = -490 },
        { x = -2365, z = 825 },
        { x = -1465, z = 825 },
        { x = -1465, z = -490 },
    },
    patrol_c = {                                                -- Shusher 3: the corridor past the core (back and forth)
        { x = -2690, z = -710 },
        { x = -690, z = -710 },
    },

    -- act 3 (design 3): the booking kiosks and glass room L129
    kiosks = {                                                  -- yaw: a player punching it faces this way (and stands
                                                                --   2.2 m back: D-pad Down lands there)
        { x = 1960, y = -600, z = 1530, yaw = 0, name = "1F BY ROOM L129" },      -- K1 (layout), outside the star room
        { x = 360, y = 0, z = -470, yaw = 32768, name = "2F ATRIUM" },            -- K2 (layout), south tip of the desk
        { x = 1410, y = 1200, z = 610, yaw = 16384, name = "4F QUIET STUDY" },    -- K3 moved from the layout's F3 fish
                                                                      --   tank (a 3.4 s run from K2 up the grand stair) to F4
        { x = -2540, y = 1800, z = -790, yaw = 49152, name = "5F WEST WING" },    -- K4 (layout), by the computers
    },
    room_door = { x0 = 2220, z0 = 2170, x1 = 2220, z1 = 1990, y = -600 },  -- L129's west face (its only free wall)
    room_star = { x = 2410, y = -520, z = 2300 },               -- missions act 3 star, inside L129, 0.8 m up
    room_center = { x = 2413, y = -600, z = 2300 },             -- L129's middle (a probe)
} end
MARSTON_POINTS = marston_points()

-- which act each mission is (star id = act - 1). Keep in step with the act names in course.lua
-- (tools/luatest/test_marston_missions.lua checks that every mission title equals its course.lua act name).
MARSTON_MISSION_ACTS = { climb = 1, quiet = 2, booking = 3 }

---------------------------------------------------------------------------------------------
if sgl_mission_register == nil then
    log_to_console("[SGL] uf_marston_missions.lua: sgl_mission.lua is not loaded", CONSOLE_MESSAGE_ERROR)
    return
end

local P = MARSTON_POINTS
local POINTS_FILE = "uf_marston_missions.lua (MARSTON_POINTS)"

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
    return ((a - b + 0x8000) & 0xFFFF) - 0x8000
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

-- a player who may be teleported (D-pad Down, a Shusher): alive, not in a cutscene, holding or riding nothing
local function can_teleport(m)
    return alive(m) and (m.action & ACT_GROUP_MASK) ~= ACT_GROUP_CUTSCENE and m.heldObj == nil and m.riddenObj == nil
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

-- vanilla animation of a visual stand-in (nil-safe: an object without the table keeps its model's pose)
local function animate(o, anims, index)
    if anims ~= nil then
        o.oAnimations = anims
        obj_init_animation(o, index or 0)
    end
end

-- a punch or a kick (the kiosks; whacking a flying book)
local PUNCHES = {}
for _, a in ipairs({ ACT_PUNCHING, ACT_MOVE_PUNCHING, ACT_JUMP_KICK }) do PUNCHES[a] = true end

local function punching(m)
    return alive(m) and PUNCHES[m.action] == true
end

---------------------------------------------------------------------------------------------
-- local objects. Lifts: Lua platforms with the vanilla checkerboard-platform collision (5.12 x 0.51 x 3.07 m at scale
-- 1), scaled to a 2.2 x 2.2 m deck, moved by Lua with oVel = the displacement so the engine carries the rider. Solids:
-- the same collision scaled into a box (the act 1 barriers, the kiosks' bodies, room L129's lock), switched off by
-- not loading it. Props: visuals only (outline / "!" boxes, Toads, books).
---------------------------------------------------------------------------------------------
local PHX, PTOP, PBOT, PHZ = 256, 26, 25, 153     -- checkerboard collision at scale 1: half x, deck top, underside, half z
local BOX_UNIT = 51           -- the "!" box models are 51 units at scale 1, origin at the bottom centre (as wf_reitz_missions.lua)
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

local function lift_init(o)
    o.oFlags = OBJ_FLAG_UPDATE_GFX_POS_AND_ANGLE | OBJ_FLAG_ACTIVE_FROM_AFAR
    o.collisionData = gGlobalObjectCollisionData.checkerboard_platform_seg8_collision_0800D710
    o.oCollisionDistance = 2000
    o.oDrawingDistance = 20000
    o.oIntangibleTimer = -1
end

local function lift_loop(o)
    local rec = rec_of(o)
    if rec == nil then
        obj_mark_for_deletion(o)
        return
    end
    if rec.drive ~= nil then rec.drive(rec) end
    local dx, dy = rec.x - o.oPosX, rec.y - o.oPosY
    if math.abs(dx) > PLAT_SNAP then dx = 0 end
    if math.abs(dy) > PLAT_SNAP then dy = 0 end
    o.oVelX, o.oVelY, o.oVelZ = dx, dy, 0          -- the engine carries the rider by the step (the book cart: along X)
    o.oPosX, o.oPosY = rec.x, rec.y
    load_object_collision_model()
end

id_bhvSglMarstonLift = hook_behavior(nil, OBJ_LIST_SURFACE, true, lift_init, lift_loop, "bhvSglMarstonLift")

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

id_bhvSglMarstonSolid = hook_behavior(nil, OBJ_LIST_SURFACE, true, solid_init, solid_loop, "bhvSglMarstonSolid")

local function prop_init(o)
    o.oFlags = OBJ_FLAG_UPDATE_GFX_POS_AND_ANGLE | OBJ_FLAG_ACTIVE_FROM_AFAR
    o.oDrawingDistance = 20000
    o.oIntangibleTimer = -1
end

local function prop_loop(o)
end

id_bhvSglMarstonProp = hook_behavior(nil, OBJ_LIST_DEFAULT, true, prop_init, prop_loop, "bhvSglMarstonProp")

local function spawn_prop(model, x, y, z, setup)
    return spawn_non_sync_object(id_bhvSglMarstonProp, model, x, y, z, setup)
end

-- a lift: a deck of half size `half` whose TOP follows rec.y + PTOP (rec.drive sets rec.y)
local function spawn_lift(x, top, z, half, drive)
    local rec = new_rec({ x = x, y = top - PTOP, z = z, half = half, drive = drive })
    rec.o = spawn_non_sync_object(id_bhvSglMarstonLift, E_MODEL_CHECKERBOARD_PLATFORM, x, rec.y, z, function(obj)
        obj.oBehParams = rec.idx
        obj_scale_xyz(obj, half / PHX, 1, half / PHZ)
    end)
    return rec
end

-- a solid box: bottom centre (x, y, z), length `len` along its local x, height h, thickness t, yaw; with a visual
-- box model of the same size (origin at its bottom centre) when model is given
local function spawn_box(x, y, z, len, h, t, yaw, model, animState)
    local rec = new_rec({ x = x, y = y, z = z, off = false })
    local sy = h / (PTOP + PBOT)
    rec.o = spawn_non_sync_object(id_bhvSglMarstonSolid, E_MODEL_NONE, x, y + PBOT * sy, z, function(obj)
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

-- switch a solid box (and its visual) on or off
local function box_on(rec, on)
    rec.off = not on
    if obj_ok(rec.vis, id_bhvSglMarstonProp) then set_hidden(rec.vis, not on) end
end

-- a door segment { x0, z0, x1, z1, y } -> centre x, z, length (+ 2 margin), yaw (axis-aligned doors)
local function door_box(d, margin)
    local cx, cz = (d.x0 + d.x1) / 2, (d.z0 + d.z1) / 2
    local dx, dz = math.abs(d.x1 - d.x0), math.abs(d.z1 - d.z0)
    if dx >= dz then return cx, cz, dx + 2 * margin, 0 end
    return cx, cz, dz + 2 * margin, 0x4000
end

---------------------------------------------------------------------------------------------
-- Lift numbers (act 1): deck top at network area time t, shuttling bottom <-> top: WAIT frames at each end, SPEED
-- units a frame between them; offset shifts one lift's cycle against the other's. The deck moves at most CATCH_UP
-- units a frame toward that height (the area timer jumps after a stall; a deck that jumped with it would drop its
-- rider through it: find_floor only looks 78 units up).
---------------------------------------------------------------------------------------------
SGL_MARSTON_LIFT = { WAIT = 60, SPEED = 6, CATCH_UP = 12 }
local LIFT = SGL_MARSTON_LIFT

function sgl_marston_lift_y(t, bottom, top, offset)
    local move = math.ceil((top - bottom) / LIFT.SPEED)
    local u = (math.floor(t) + (offset or 0)) % (2 * (LIFT.WAIT + move))
    if u < LIFT.WAIT then return bottom end
    u = u - LIFT.WAIT
    if u < move then return math.min(top, bottom + u * LIFT.SPEED) end
    u = u - move
    if u < LIFT.WAIT then return top end
    u = u - LIFT.WAIT
    return math.max(bottom, top - u * LIFT.SPEED)
end

function sgl_marston_lift_step(y, target)
    if y == nil then return target end
    return y + clamp(target - y, -LIFT.CATCH_UP, LIFT.CATCH_UP)
end

-- The book cart (fix round: one jumping beat, and no walk round the F4 balcony): a deck at the F4 railing tops that
-- shuttles across the atrium void between lift A and lift B, a 0.5 m hop from either (CART_GAP). Its cycle has the
-- lifts' period (WAIT frames at each end fill it up), phased so it leaves lift A's side when lift A leaves the top
-- and waits at lift B's side while lift B waits at the bottom. Deck X at network area time t (pure):
local CART_GAP = 50

function sgl_marston_cart_x(t, east, west, period, offset)
    local dist = math.abs(west - east)
    local move = math.ceil(dist / LIFT.SPEED)
    local wait = math.max(0, period // 2 - move)
    local dir = west < east and -1 or 1
    local u = (math.floor(t) + (offset or 0)) % (2 * (wait + move))
    if u < wait then return east end
    u = u - wait
    if u < move then return east + dir * math.min(dist, u * LIFT.SPEED) end
    u = u - move
    if u < wait then return west end
    u = u - wait
    return west - dir * math.min(dist, u * LIFT.SPEED)
end

-- the cart between two lifts { x, z, bottom, top, half, offset } (A: rises to the cart's level, B: starts there) ->
-- { east, west, z, top, half, period, offset }
function sgl_marston_cart_of(la, lb, half)
    local moveL = math.ceil((la.top - la.bottom) / LIFT.SPEED)
    local period = 2 * (LIFT.WAIT + moveL)
    local dir = lb.x < la.x and -1 or 1
    local east = la.x + dir * (la.half + CART_GAP + half)
    local west = lb.x - dir * (lb.half + CART_GAP + half)
    local wait = math.max(0, period // 2 - math.ceil(math.abs(west - east) / LIFT.SPEED))
    -- leave lift A's side when lift A leaves the top (at u = 2 WAIT + move of lift A's cycle)
    local offset = (wait - (2 * LIFT.WAIT + moveL) + (la.offset or 0)) % period
    return { east = east, west = west, z = la.z, top = la.top, half = half, period = period, offset = offset }
end

---------------------------------------------------------------------------------------------
-- CLIMB kind (act 1): the framework's reach kind (goal, milestones, route marker, team best) plus spec =
-- { reach = <sgl_mission_kind_reach spec>, lifts = { { x, z, bottom, top, half, offset }, ... }, cart = { half } (the
-- book cart between lifts[1] and lifts[2], sgl_marston_cart_of) or nil, barriers = { door
-- segments }, basement = { below (Y), to = {x,y,z}, yaw } (while the barriers stand, a player below `below` - down the
-- one-way book chute - is sent back to `to`), barrierMargin, barrierHeight, barrierThick, atrium = { x0, x1, z0, z1 }, shaft = {x,y,z},
-- books = { floors = { y, ... }, reach, first, every, telegraph, speed, life, hurt, scale, model } or nil }
-- Flying books: while the local player stands on the F3 / F4 floor within `reach` of the atrium void (not on a lift),
-- a book rises over the void on the far side every `every` frames, hovers `telegraph` frames, then flies straight at
-- where the player's chest was (1.25 m up; speed units a frame) for `life` frames. A hit is a knock-back and `hurt`
-- (4 = one wedge); crouching or crawling ducks under it; a punch or kick within 1.8 m knocks it away. The lifts are a
-- safe zone: boarding one sends every book back to its shelf.
---------------------------------------------------------------------------------------------
local BOOK_HIT_R = 90         -- a flying book hits within 0.9 m (xz) ...
local BOOK_HALF_H = 40        -- ... when its 0.8 m overlaps Mario's height
local MARIO_H, DUCK_H = 160, 70
local BOOK_AIM_Y = 125        -- a book flies at this height over the player's feet (at launch)
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

-- can a flying book hit the local player now (not mid-hit, not invincible, not in a cutscene or intangible)
local function hittable(m)
    return alive(m) and (m.invincTimer or 0) == 0 and not KNOCKBACK[m.action]
        and (m.action & ACT_GROUP_MASK) ~= ACT_GROUP_CUTSCENE and (m.action & ACT_FLAG_INTANGIBLE) == 0
end

-- does a book at (x, y, z) touch Mario (pos, action)? Pure (tools/luatest checks it): crouching / crawling ducks under
-- a book flying at chest height
function sgl_marston_book_hits(pos, action, x, y, z)
    local dx, dz = x - pos.x, z - pos.z
    if dx * dx + dz * dz > BOOK_HIT_R * BOOK_HIT_R then return false end
    local h = DUCKING[action] and DUCK_H or MARIO_H
    return y + BOOK_HALF_H > pos.y and y - BOOK_HALF_H < pos.y + h
end

local function kind_climb(spec)
    local R = sgl_mission_kind_reach(spec.reach)
    local K = {}
    for k, v in pairs(R) do K[k] = v end
    K.reachKind = R
    K.lifts = spec.lifts
    local B = spec.books

    local function on_lift(ctx, p)
        for _, rec in ipairs(ctx.objs.lifts or {}) do
            local top = rec.y + PTOP
            if math.abs(p.x - rec.x) <= rec.half + 40 and math.abs(p.z - rec.z) <= rec.half + 40
                and p.y >= top - 40 and p.y <= top + 400 then
                return true
            end
        end
        return false
    end
    K.onLift = on_lift

    -- standing on the F3 / F4 floor by the void, not on a lift: the flying books' target
    local function exposed(ctx, m)
        if B == nil or not alive(m) or (m.action & ACT_GROUP_MASK) == ACT_GROUP_CUTSCENE then return false end
        local a, r = spec.atrium, B.reach
        local p = m.pos
        if p.x < a.x0 - r or p.x > a.x1 + r or p.z < a.z0 - r or p.z > a.z1 + r then return false end
        local onFloor = false
        for _, fy in ipairs(B.floors) do
            if p.y >= fy - 50 and p.y <= fy + 400 then onFloor = true end
        end
        return onFloor and not on_lift(ctx, p)
    end
    K.exposed = exposed

    K.cart = spec.cart and sgl_marston_cart_of(spec.lifts[1], spec.lifts[2], spec.cart.half) or nil
    K.spawnLocal = function(ctx)
        ctx.objs.lifts = {}
        for i, lf in ipairs(spec.lifts) do
            local t0 = get_network_area_timer()
            ctx.objs.lifts[i] = spawn_lift(lf.x, sgl_marston_lift_y(t0, lf.bottom, lf.top, lf.offset), lf.z, lf.half,
                function(rec)
                    local want = sgl_marston_lift_y(get_network_area_timer(), lf.bottom, lf.top, lf.offset) - PTOP
                    rec.y = sgl_marston_lift_step(rec.started and rec.y or nil, want)
                    rec.started = true
                end)
        end
        local ct = K.cart
        if ct ~= nil then
            -- the book cart rides with the lifts (ctx.objs.lifts): carried like them, safe from the books like them
            local x0 = sgl_marston_cart_x(get_network_area_timer(), ct.east, ct.west, ct.period, ct.offset)
            local rec = spawn_lift(x0, ct.top, ct.z, ct.half, function(r)
                local want = sgl_marston_cart_x(get_network_area_timer(), ct.east, ct.west, ct.period, ct.offset)
                r.x = sgl_marston_lift_step(r.started and r.x or nil, want)
                r.started = true
            end)
            rec.cart = true
            table.insert(ctx.objs.lifts, rec)
            ctx.objs.cart = rec
        end
        ctx.objs.barriers = {}
        for i, d in ipairs(spec.barriers or {}) do
            local cx, cz, len, yaw = door_box(d, spec.barrierMargin or 30)
            local rec = spawn_box(cx, d.y, cz, len, spec.barrierHeight or 500, spec.barrierThick or 40, yaw,
                E_MODEL_EXCLAMATION_BOX_OUTLINE, 0)
            rec.door = d
            ctx.objs.barriers[i] = rec
        end
        ctx.objs.books = {}
    end

    local function poof(o)
        if obj_ok(o, id_bhvSglMarstonProp) then
            spawn_non_sync_object(id_bhvMistParticleSpawner, E_MODEL_MIST, o.oPosX, o.oPosY, o.oPosZ, nil)
            obj_mark_for_deletion(o)
        end
    end

    -- a book over the void on the far side from the player, at their chest height + 0.3 m
    local function launch_book(ctx, m)
        local a = spec.atrium
        local cx, cz = (a.x0 + a.x1) / 2, (a.z0 + a.z1) / 2
        local dx, dz = cx - m.pos.x, cz - m.pos.z
        local d = math.sqrt(dx * dx + dz * dz)
        if d < 1 then dx, dz, d = 1, 0, 1 end
        local x = clamp(cx + dx / d * 450, a.x0 + 100, a.x1 - 100)
        local z = clamp(cz + dz / d * 450, a.z0 + 100, a.z1 - 100)
        local y = m.pos.y + 130
        local o = spawn_prop(B.model or E_MODEL_BOOKEND, x, y, z, function(obj)
            obj_scale(obj, B.scale or 1)
            obj.oFaceAngleYaw = atan2s(m.pos.z - z, m.pos.x - x)
        end)
        animate(o, gObjectAnimations.bookend_seg5_anims_05002540, 0)
        table.insert(ctx.objs.books, { o = o, age = 0, x = x, y = y, z = z, vx = 0, vy = 0, vz = 0, flying = false })
        play_sound(SOUND_OBJ2_SWOOP, gGlobalSoundSource)
    end

    local function books_tick(ctx, m)
        local L = ctx.loc
        local list = ctx.objs.books
        -- the lifts are a safe zone (fix round): a knock-back on a deck would throw the rider into the 0.6 m gap
        -- between the deck and the balcony (a 6-12 m fall), so every book in the air goes back to its shelf
        local riding = alive(m) and on_lift(ctx, m.pos)
        for i = #list, 1, -1 do
            local b = list[i]
            b.age = b.age + 1
            local gone = not obj_ok(b.o, id_bhvSglMarstonProp)
            if not gone and riding then
                poof(b.o)
                gone = true
                L.liftSaves = (L.liftSaves or 0) + 1
            end
            if not gone then
                if not b.flying then
                    -- hover and shake: the telegraph
                    b.o.oFaceAngleRoll = math.floor(0x900 * math.sin(b.age * 0.9))
                    b.o.oFaceAngleYaw = atan2s(m.pos.z - b.z, m.pos.x - b.x)
                    if b.age >= B.telegraph then
                        -- at the player's chest (1.25 m up): over a crouching Mario's head (0.7 m)
                        local tx, ty, tz = m.pos.x - b.x, m.pos.y + BOOK_AIM_Y - b.y, m.pos.z - b.z
                        local d = math.max(1, math.sqrt(tx * tx + ty * ty + tz * tz))
                        b.vx, b.vy, b.vz = tx / d * B.speed, ty / d * B.speed, tz / d * B.speed
                        b.flying, b.age = true, 0
                        b.o.oFaceAngleRoll = 0
                    end
                else
                    b.x, b.y, b.z = b.x + b.vx, b.y + b.vy, b.z + b.vz
                end
                b.o.oPosX, b.o.oPosY, b.o.oPosZ = b.x, b.y, b.z
                local dx, dy, dz = b.x - m.pos.x, b.y - (m.pos.y + 80), b.z - m.pos.z
                if punching(m) and dx * dx + dy * dy + dz * dz <= 180 * 180 then
                    play_sound(SOUND_GENERAL_BREAK_BOX, gGlobalSoundSource)
                    sgl_hud_toast("Whack! Back to the shelf, book!", 2, SGL_HUD_GREEN)
                    L.whacked = (L.whacked or 0) + 1
                    poof(b.o)
                    gone = true
                elseif b.flying and hittable(m) and sgl_marston_book_hits(m.pos, m.action, b.x, b.y, b.z) then
                    m.faceAngle.y = atan2s(b.z - m.pos.z, b.x - m.pos.x)
                    local air = (m.action & ACT_GROUP_MASK) == ACT_GROUP_AIRBORNE
                    hurt_and_set_mario_action(m, air and ACT_BACKWARD_AIR_KB or ACT_BACKWARD_GROUND_KB, 0, B.hurt)
                    play_sound(SOUND_OBJ_DEFAULT_DEATH, gGlobalSoundSource)
                    sgl_hud_toast("THWACK! An overdue book! (duck: Z, or punch it)", 3, SGL_HUD_RED)
                    L.hits = (L.hits or 0) + 1
                    L.expandUntil = ctx.age + 150
                    poof(b.o)
                    gone = true
                elseif b.flying and b.age >= B.life then
                    poof(b.o)
                    gone = true
                end
            end
            if gone then table.remove(list, i) end
        end
        -- the next book: only while the act runs and the local player is out on a balcony
        if ctx.s == SGL_MS_ACTIVE and exposed(ctx, m) then
            L.bookIn = (L.bookIn or B.first) - 1
            if L.bookIn <= 0 then
                L.bookIn = B.every
                if #list == 0 then launch_book(ctx, m) end
            end
        else
            L.bookIn = nil
        end
    end

    -- the basement is closed too: the F2 book-return chute is a one-way slide down to F1, and every way back up (the
    -- stair halls, the core) is behind a barrier, so whoever slides down is sent back to the lobby (no damage)
    local function basement_tick(ctx, m)
        local bs = spec.basement
        if bs == nil or #(ctx.objs.barriers or {}) == 0 or m.pos.y >= bs.below or not can_teleport(m) then return end
        teleport(m, bs.to, bs.yaw or 0)
        play_sound(SOUND_MENU_CAMERA_BUZZ, gGlobalSoundSource)
        sgl_hud_toast("The basement is closed for the renovation too - back to the lobby", 3, SGL_HUD_ORANGE)
        ctx.loc.basement = (ctx.loc.basement or 0) + 1
    end
    K.basementTick = basement_tick

    K.localTick = function(ctx)
        R.localTick(ctx)
        local m = gMarioStates[0]
        if B ~= nil then books_tick(ctx, m) end
        basement_tick(ctx, m)
    end

    K.panel = function(ctx)
        local lines = R.panel(ctx)
        table.insert(lines, { "Stairs closed for renovation: ride the atrium book-cart lifts", SGL_HUD_GREY, 0.26 })
        if K.cart ~= nil then
            table.insert(lines, { "At the top of lift A, hop onto the book cart across to lift B", SGL_HUD_GREY, 0.26 })
        end
        table.insert(lines, { "...or wall-kick up the out-of-order elevator shaft", SGL_HUD_GREY, 0.26 })
        if B ~= nil then
            table.insert(lines, { "Flying books on the balconies: duck (Z) or punch (B)", SGL_HUD_ORANGE, 0.26 })
        end
        return lines
    end

    K.hud = function(ctx)
        R.hud(ctx)
        if ctx.s ~= SGL_MS_ACTIVE and ctx.s ~= SGL_MS_INTRO then return end
        local m = gMarioStates[0]
        -- the nearest closed door on my floor
        local best, bestD = nil, nil
        for _, rec in ipairs(ctx.objs.barriers or {}) do
            local d = dist2_xz(m.pos, rec)
            if math.abs(m.pos.y - rec.y) < 300 and d <= 700 * 700 and (bestD == nil or d < bestD) then best, bestD = rec, d end
        end
        if best ~= nil then sgl_hud_marker(up(best, 280), "CLOSED FOR RENOVATION", SGL_HUD_RED, nil, true) end
        local s = spec.shaft
        if s ~= nil and math.abs(m.pos.y - s.y) < 300 and dist2_xz(m.pos, s) <= 2000 * 2000 then
            sgl_hud_marker(up(s, 250), "OUT-OF-ORDER SHAFT (wall kick)", SGL_HUD_GREY, nil, true)
        end
        for _, b in ipairs(ctx.objs.books or {}) do
            if not b.flying then sgl_hud_marker({ x = b.x, y = b.y + 80, z = b.z }, "BOOK!", SGL_HUD_RED, nil, true) end
        end
    end
    return K
end

---------------------------------------------------------------------------------------------
-- Noise (act 2): what the local Mario's action sounds like to a Shusher -> hearing radius (units), label. Pure
-- (tools/luatest checks it). Silent: standing, tiptoeing (forward speed <= WALK_V, the stick tilted a little),
-- crouching and crawling (keyboard players: hold Z), hanging, falling. Steps: walking; running: over RUN_V; jumps
-- (Mario's yell), punches and kicks, landings, and loud crashes (ground pounds, dives, slides, hard knock-backs).
---------------------------------------------------------------------------------------------
SGL_MARSTON_NOISE = { WALK = 300, RUN = 600, JUMP = 650, HIT = 600, LAND = 750, HARD = 1100, WALK_V = 10, RUN_V = 20 }
local NOISE = SGL_MARSTON_NOISE
local NOISE_KIND = nil

-- How loud may I be this far from a Shusher (units)? -> label, colour of its marker (fix round: readability). Pure.
-- Over NOISE.LAND (7.5 m): run, jump and land; over NOISE.WALK (3 m): walk (running is heard within 6 m); closer:
-- only tiptoe / crawl. (Its sight, 2.2 m ahead, and bumping it count at any noise.)
function sgl_marston_noise_tier(d)
    if d > NOISE.LAND then return "RUN", SGL_HUD_GREEN end
    if d > NOISE.WALK then return "WALK", SGL_HUD_WHITE end
    return "TIPTOE", SGL_HUD_RED
end

-- Tiptoe for keyboard players (fix round): a keyboard's stick is all or nothing, and crawling (Z) is slower than a
-- Shusher. Holding L (keyboard default: Left Shift) caps the stick at SNEAK_STICK of 64 while the act-2 mission runs
-- and the player is on its quiet floor: intendedMag = (32 / 64)^2 * 64 / 2 = 8 <= NOISE.WALK_V, a silent tiptoe at
-- full keyboard tilt. Applied in HOOK_BEFORE_MARIO_UPDATE, before update_mario_inputs reads the stick (coopdx v1.5.1
-- object_list_processor.c: the hook, then execute_mario_action). Pure part: the scaled stick.
SGL_MARSTON_SNEAK_STICK = 32

function sgl_marston_sneak_stick(x, y, mag)
    local cap = SGL_MARSTON_SNEAK_STICK
    if mag == nil or mag <= cap then return x, y, mag end
    local f = cap / mag
    return x * f, y * f, cap
end

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

function sgl_marston_noise(action, forwardVel)
    NOISE_KIND = NOISE_KIND or noise_kinds()
    local kind = NOISE_KIND[action]
    if kind == "hard" then return NOISE.HARD, "CRASH!" end
    if kind == "land" then return NOISE.LAND, "landing" end
    if kind == "hit" then return NOISE.HIT, "punch" end
    if kind == "quiet" then return 0, "quiet" end
    local group = action & ACT_GROUP_MASK
    if group == ACT_GROUP_AIRBORNE then return NOISE.JUMP, "jump" end
    if group == ACT_GROUP_MOVING then
        local v = math.abs(forwardVel or 0)
        if v > NOISE.RUN_V then return NOISE.RUN, "running" end
        if v > NOISE.WALK_V then return NOISE.WALK, "steps" end
    end
    return 0, "quiet"
end

---------------------------------------------------------------------------------------------
-- Patrols (act 2): a Shusher walks a polyline of { x, z } points, closed (loop) or back and forth. Pure: position and
-- heading at arc length s (units) -> x, z, yaw.
---------------------------------------------------------------------------------------------
local sPatrolLen = setmetatable({}, { __mode = "k" })

local function patrol_len(pts, loop)
    local key = sPatrolLen[pts]
    if key ~= nil and key.loop == loop then return key.len end
    local n = #pts
    local len = 0
    for i = 1, (loop and n or n - 1) do
        local a, b = pts[i], pts[(i % n) + 1]
        len = len + math.sqrt((b.x - a.x) ^ 2 + (b.z - a.z) ^ 2)
    end
    sPatrolLen[pts] = { loop = loop, len = len }
    return len
end

function sgl_marston_patrol_pos(pts, loop, s)
    local n = #pts
    local total = patrol_len(pts, loop)
    if n < 2 or total <= 0 then return pts[1].x, pts[1].z, 0 end
    local back = false
    local u
    if loop then
        u = s % total
    else
        u = s % (2 * total)
        if u > total then
            u = 2 * total - u
            back = true
        end
    end
    for i = 1, (loop and n or n - 1) do
        local a, b = pts[i], pts[(i % n) + 1]
        local L = math.sqrt((b.x - a.x) ^ 2 + (b.z - a.z) ^ 2)
        if u <= L or i == (loop and n or n - 1) then
            local t = L > 0 and math.min(1, u / L) or 0
            local yaw = atan2s(b.z - a.z, b.x - a.x)
            if back then yaw = (yaw + 0x8000) & 0xFFFF end
            return a.x + (b.x - a.x) * t, a.z + (b.z - a.z) * t, yaw
        end
        u = u - L
    end
    return pts[1].x, pts[1].z, 0
end

---------------------------------------------------------------------------------------------
-- QUIET kind (act 2): spec = { books = { {x, y, z, name}, ... }, y (the floor), start = {x,y,z} (where a Shusher sends
-- you; D-pad Down), startYaw, patrols = { { pts, loop, s0 (start offset, units) }, ... }, speed (units a frame),
-- pause (frames per pause unit), hmUnits, shhUnits, sight, sightHalf (s16 half angle), bump, sameFloor, alert (x the
-- noise radius: heard at the edge -> it stops and looks), cool (frames of grace after being sent back), radius, below,
-- above (touching a book), model, modelScale, bookModel }
-- Fields: f = textbooks found (bits), p = how many, c = times the team got shushed, g = pause units per Shusher
-- (10 bits each). Shusher k at area time t: arc length s0 + (t - applied_k) * speed, where applied_k approaches
-- g's units_k * pause one frame per frame (a pause), so every client walks it the same once the pause is over.
---------------------------------------------------------------------------------------------
local UNIT_BITS = 10
local UNIT_MASK = (1 << UNIT_BITS) - 1

function sgl_marston_units_of(g, k)
    return (g >> (UNIT_BITS * (k - 1))) & UNIT_MASK
end

local function units_add(g, k, n)
    local u = (sgl_marston_units_of(g, k) + n) & UNIT_MASK
    local sh = UNIT_BITS * (k - 1)
    return (g & ~(UNIT_MASK << sh)) | (u << sh)
end

local function kind_quiet(spec)
    local K = {}
    local books = spec.books
    local nBooks = #books
    local ALL = (1 << nBooks) - 1
    local R, BELOW, ABOVE = spec.radius or 140, spec.below or 100, spec.above or 250
    local RESEND = 90

    local function touching(p, b)
        return dist2_xz(p, b) <= R * R and p.y >= b.y - BELOW and p.y <= b.y + ABOVE
    end
    K.touching = touching

    local function found(ctx)
        return (ctx.f | (ctx.loc.mine or 0) | (ctx.loc.seen or 0)) & ALL
    end
    K.found = found

    local function sound_for(n)
        return SOUND_MENU_COLLECT_RED_COIN + (clamp(n - 1, 0, 7) << 16)
    end

    local function nearest(ctx, pos)
        local got = found(ctx)
        local best, bestD = nil, nil
        for i, b in ipairs(books) do
            if (got & (1 << (i - 1))) == 0 then
                local d = math.sqrt((b.x - pos.x) ^ 2 + (b.y - pos.y) ^ 2 + (b.z - pos.z) ^ 2)
                if bestD == nil or d < bestD then best, bestD = i, d end
            end
        end
        return best, bestD and math.floor(bestD / 100 + 0.5) or nil
    end
    K.nearest = nearest

    -- this client's Shushers (ctx.objs.shushers[k] = { o, units, target, applied, x, z, yaw, lookX, lookZ, lookUntil })
    -- one Shusher's frame: spend its pause units, walk (or stand and look), place its Toad
    local function shusher_step(ctx, k, pt, sh, t)
        local u = sgl_marston_units_of(ctx.g, k)
        if sh.units == nil or u < sh.units then
            sh.target = u * spec.pause         -- arriving (or a new round): in step at once
            sh.applied = sh.target
        elseif u > sh.units then
            sh.target = sh.target + (u - sh.units) * spec.pause
        end
        sh.units = u
        sh.paused = sh.applied < sh.target
        if sh.paused then sh.applied = sh.applied + 1 end
        local x, z, yaw = sgl_marston_patrol_pos(pt.pts, pt.loop, (pt.s0 or 0) + (t - sh.applied) * spec.speed)
        local want = yaw
        if sh.lookUntil ~= nil and ctx.age < sh.lookUntil then
            want = atan2s(sh.lookZ - z, sh.lookX - x)
        end
        if sh.yaw == nil then sh.yaw = want end
        sh.yaw = (sh.yaw + clamp(angle_diff(want, sh.yaw), -0xA00, 0xA00)) & 0xFFFF
        sh.moving = not sh.paused and (sh.x ~= nil and (sh.x ~= x or sh.z ~= z))
        sh.x, sh.z = x, z
        local o = sh.o
        if obj_ok(o, id_bhvSglMarstonProp) then
            local bob = sh.moving and math.abs(math.sin(ctx.age * 0.3)) * 8 or 0
            o.oPosX, o.oPosY, o.oPosZ = x, spec.y + bob, z
            o.oFaceAngleYaw = sh.yaw
            o.oFaceAngleRoll = sh.moving and math.floor(0x280 * math.sin(ctx.age * 0.3)) or 0
        end
    end

    local function shusher_update(ctx, t)
        for k, pt in ipairs(spec.patrols) do
            local sh = ctx.objs.shushers[k]
            if sh ~= nil then shusher_step(ctx, k, pt, sh, t) end
        end
    end
    K.shusherUpdate = shusher_update

    -- who of my Shushers catches the local player now -> k, why ("heard", "saw", "bumped") or nil; and the one
    -- that only half-hears them (stops and looks)
    local function judge(ctx, m)
        if math.abs(m.pos.y - spec.y) > spec.sameFloor then return nil end
        local r, label = sgl_marston_noise(m.action, m.forwardVel)
        local half = nil
        for k, sh in ipairs(ctx.objs.shushers or {}) do
            if sh.x ~= nil then
                local dx, dz = m.pos.x - sh.x, m.pos.z - sh.z
                local d = math.sqrt(dx * dx + dz * dz)
                if d <= spec.bump then return k, "bumped", label end
                if r > 0 and d <= r then return k, "heard", label end
                if d <= spec.sight and math.abs(angle_diff(atan2s(dz, dx), sh.yaw)) <= spec.sightHalf then
                    return k, "saw", label
                end
                if r > 0 and d <= r * spec.alert and half == nil then half = k end
            end
        end
        return nil, nil, label, half
    end
    K.judge = judge

    K.onReset = function(ctx)
        ctx:set("f", 0)
        ctx:set("p", 0)
        ctx:set("c", 0)
        ctx:set("g", 0)
    end

    K.leaderTick = function(ctx)
        if (ctx.f & ALL) == ALL then ctx:succeed() end
    end

    local function live(ctx)
        return ctx.s == SGL_MS_ACTIVE or ctx.s == SGL_MS_SUCCESS
    end
    K.catching = live

    K.onEvent = function(ctx, ev, data)
        if data.r ~= ctx.r then return end
        local me = data.gi == gNetworkPlayers[0].globalIndex
        if ev == "book" then
            if math.type(data.i) ~= "integer" or data.i < 1 or data.i > nBooks then return end
            local bit = 1 << (data.i - 1)
            if ctx.isLeader and (ctx.s == SGL_MS_ACTIVE or ctx.s == SGL_MS_INTRO) and (ctx.f & bit) == 0 then
                local f = ctx.f | bit
                ctx:set("f", f)
                ctx:set("p", popcount(f & ALL))
                if (f & ALL) == ALL then ctx:succeed() end
            end
            local L = ctx.loc
            if not me and ((L.seen or 0) & bit) == 0 and ((L.mine or 0) & bit) == 0 then
                L.seen = (L.seen or 0) | bit
                local n = popcount(found(ctx))
                sgl_hud_toast(string.format("%s found the %s textbook! %d/%d", data.nm or "?", books[data.i].name, n, nBooks),
                    3, SGL_HUD_GREEN)
                play_sound(sound_for(n), gGlobalSoundSource)
                L.expandUntil = ctx.age + 150
            end
        elseif ev == "shh" or ev == "hm" then
            local k = data.k
            if math.type(k) ~= "integer" or k < 1 or k > #spec.patrols then return end
            local units = ev == "shh" and spec.shhUnits or spec.hmUnits
            if ctx.isLeader and live(ctx) then
                ctx.lead.hm = ctx.lead.hm or {}
                local last = ctx.lead.hm[k]
                if ev == "shh" or last == nil or ctx.age - last >= spec.pause + 15 then
                    ctx.lead.hm[k] = ctx.age
                    ctx:set("g", units_add(ctx.g, k, units))
                    if ev == "shh" then ctx:set("c", ctx.c + 1) end
                end
            end
            local sh = ctx.objs.shushers and ctx.objs.shushers[k]
            if sh ~= nil and type(data.x) == "number" and type(data.z) == "number" then
                sh.lookX, sh.lookZ = data.x, data.z
                sh.lookUntil = ctx.age + units * spec.pause
            end
            if ev == "shh" and not me then
                sgl_hud_toast((data.nm or "?") .. " got shushed! Back to the stairwell", 3, SGL_HUD_ORANGE)
                ctx.loc.expandUntil = ctx.age + 150
            end
        end
    end

    K.spawnLocal = function(ctx)
        ctx.objs.shushers = {}
        local anims = gObjectAnimations.toad_seg6_anims_0600FB58
        for k, pt in ipairs(spec.patrols) do
            local x, z, yaw = sgl_marston_patrol_pos(pt.pts, pt.loop, pt.s0 or 0)
            local o = spawn_prop(spec.model or E_MODEL_TOAD, x, spec.y, z, function(obj)
                obj_scale(obj, spec.modelScale or 1)
                obj.oFaceAngleYaw = yaw
            end)
            animate(o, anims, 6)          -- bhvToadMessage's standing animation
            ctx.objs.shushers[k] = { o = o, yaw = yaw }
        end
        ctx.objs.books = {}
        for i, b in ipairs(books) do
            ctx.objs.books[i] = spawn_prop(spec.bookModel or E_MODEL_BREAKABLE_BOX_SMALL, b.x, b.y + 40, b.z, function(obj)
                obj_scale_xyz(obj, 0.55, 0.22, 0.75)      -- a flat brown hardback
            end)
        end
    end

    local function caught(ctx, m, k, why)
        local L = ctx.loc
        L.cool = spec.cool
        L.shushed = (L.shushed or 0) + 1
        L.shAge = 0
        L.expandUntil = ctx.age + 150
        play_sound(SOUND_MENU_CAMERA_BUZZ, gGlobalSoundSource)
        local text = why == "saw" and "A librarian saw you! SHHH!" or (why == "bumped" and "You bumped a librarian! SHHH!"
            or "Too loud! SHHH!")
        sgl_hud_toast(text .. " Back to the stairwell", 3, SGL_HUD_RED)
        ctx:send("shh", { k = k, x = math.floor(m.pos.x), z = math.floor(m.pos.z), nm = gNetworkPlayers[0].name })
        teleport(m, spec.start, spec.startYaw)
    end

    K.localTick = function(ctx)
        local L = ctx.loc
        local m = gMarioStates[0]
        local t = get_network_area_timer()
        if ctx.objs.shushers ~= nil then shusher_update(ctx, t) end
        L.mine = L.mine or 0
        L.seen = L.seen or 0
        L.sentAt = L.sentAt or {}
        L.hmAt = L.hmAt or {}
        if L.shAge ~= nil then L.shAge = L.shAge + 1 end
        -- the Shushers
        if (L.cool or 0) > 0 then L.cool = L.cool - 1 end
        L.noise = nil
        if live(ctx) and can_teleport(m) then
            local k, why, label, half = judge(ctx, m)
            L.noise = label
            if k ~= nil and (L.cool or 0) == 0 then
                caught(ctx, m, k, why)
            elseif half ~= nil and (L.cool or 0) == 0 and ctx.age - (L.hmAt[half] or -9999) >= spec.pause + 15 then
                L.hmAt[half] = ctx.age
                ctx:send("hm", { k = half, x = math.floor(m.pos.x), z = math.floor(m.pos.z) })
            end
        end
        -- the textbooks
        if ctx.s == SGL_MS_ACTIVE and alive(m) then
            local got = found(ctx)
            for i, b in ipairs(books) do
                local bit = 1 << (i - 1)
                if (got & bit) == 0 and touching(m.pos, b) then
                    L.mine = L.mine | bit
                    got = got | bit
                    L.sentAt[i] = ctx.age
                    local n = popcount(got)
                    play_sound(sound_for(n), gGlobalSoundSource)
                    sgl_hud_toast(string.format("Textbook: %s! %d/%d", b.name, n, nBooks), 3, SGL_HUD_GOLD)
                    L.expandUntil = ctx.age + 150
                    ctx:send("book", { i = i, nm = gNetworkPlayers[0].name })
                end
            end
            -- not in the synced bits after 3 s (the leader left before applying it): send it again
            for i = 1, nBooks do
                local bit = 1 << (i - 1)
                if (L.mine & bit) ~= 0 and (ctx.f & bit) == 0 and L.sentAt[i] ~= nil and ctx.age - L.sentAt[i] >= RESEND then
                    L.sentAt[i] = ctx.age
                    ctx:send("book", { i = i, nm = gNetworkPlayers[0].name })
                end
            end
        end
        local got = found(ctx)
        for i, o in ipairs(ctx.objs.books or {}) do
            if obj_ok(o, id_bhvSglMarstonProp) then
                set_hidden(o, (got & (1 << (i - 1))) ~= 0)
                o.oFaceAngleYaw = (o.oFaceAngleYaw + 0x180) & 0xFFFF
            end
        end
    end

    local NOISE_COL = { quiet = SGL_HUD_GREEN, steps = SGL_HUD_WHITE, running = SGL_HUD_ORANGE, jump = SGL_HUD_ORANGE,
        punch = SGL_HUD_ORANGE, landing = SGL_HUD_RED }

    K.panel = function(ctx)
        local L = ctx.loc
        local got = found(ctx)
        local i, d = nearest(ctx, gMarioStates[0].pos)
        local head = string.format("Textbooks %d/%d", popcount(got), nBooks)
        if i ~= nil then head = head .. string.format("   next: %s %d m", books[i].name, d) end
        local lines = { { head, SGL_HUD_WHITE } }
        local noise = L.noise or "quiet"
        table.insert(lines, { "Noise: " .. noise:upper(), NOISE_COL[noise] or SGL_HUD_RED, 0.3 })
        table.insert(lines, { string.format("Shushed: you %d   team %d", L.shushed or 0, ctx.c), SGL_HUD_GREY, 0.28 })
        table.insert(lines, { "Tiptoe (tilt the stick a little, or hold L / Left Shift) or crawl (Z)", SGL_HUD_GREY, 0.24 })
        table.insert(lines, { "Librarian markers: green = run OK, white = walk, red = tiptoe", SGL_HUD_GREY, 0.24 })
        local m = gMarioStates[0]
        if m.pos.y < spec.y - 100 then
            table.insert(lines, { "D-pad Down: up to the quiet 5th floor", SGL_HUD_GREY, 0.26 })
        end
        return lines
    end

    K.hud = function(ctx)
        local L = ctx.loc
        local m = gMarioStates[0]
        if L.shAge ~= nil and L.shAge < 45 then sgl_hud_big("SHHH!", SGL_HUD_RED, 2.6) end
        if ctx.s ~= SGL_MS_ACTIVE and ctx.s ~= SGL_MS_INTRO and ctx.s ~= SGL_MS_SUCCESS then return end
        if m.pos.y < spec.y - 100 then
            sgl_hud_marker(up(spec.start, 150), "QUIET FLOOR (5F)", SGL_HUD_GOLD, m)
        elseif ctx.s ~= SGL_MS_SUCCESS then
            local got = found(ctx)
            local near = nearest(ctx, m.pos)
            for i, b in ipairs(books) do
                if (got & (1 << (i - 1))) == 0 and i ~= near then
                    sgl_hud_marker(up(b, 100), "", SGL_HUD_ORANGE, nil, true)
                end
            end
            if near ~= nil then sgl_hud_marker(up(books[near], 100), books[near].name, SGL_HUD_GOLD, m) end
        end
        if math.abs(m.pos.y - spec.y) <= spec.sameFloor then
            for _, sh in ipairs(ctx.objs.shushers or {}) do
                local d2 = (m.pos.x - (sh.x or 0)) ^ 2 + (m.pos.z - (sh.z or 0)) ^ 2
                if sh.x ~= nil and d2 <= 1800 * 1800 then
                    -- colour = how loud I may be at this distance (green run, white walk, red tiptoe / crawl)
                    local tier, col = sgl_marston_noise_tier(math.sqrt(d2))
                    sgl_hud_marker({ x = sh.x, y = spec.y + 200, z = sh.z }, (sh.paused and "? " or "SHH ") .. tier, col,
                        nil, true)
                end
            end
        end
    end

    -- D-pad Down / /mission start: to the stairwell door of the quiet floor
    K.toStart = function(ctx, m)
        if not can_teleport(m) or ctx.s == SGL_MS_WAITING then return false end
        if dist2_xz(m.pos, spec.start) <= 300 * 300 and math.abs(m.pos.y - spec.start.y) < 200 then return false end
        teleport(m, spec.start, spec.startYaw)
        play_sound(SOUND_MENU_EXIT_PIPE, gGlobalSoundSource)
        sgl_hud_toast("The quiet floor: shhh...", 2, SGL_HUD_WHITE)
        return true
    end
    return K
end

---------------------------------------------------------------------------------------------
-- BOOKING kind (act 3, co-op): spec = { kiosks = { {x, y, z, name}, ... }, sets = { [N] = { kiosk, ... } } (lit
-- kiosks for N players here, N clamped to 2..#kiosks), window (s), confirm (frames: a kiosk reads the punches this
-- long after the last one), radius (punch reach), readyRadius, door = { x0, z0, x1, z1, y } (room L129's doorway),
-- doorHeight, doorThick }
-- Fields: a = N, f = booked kiosks (bits), c = seconds left in the window (0 = closed), g = lit kiosks with somebody
-- at them, x = count-in (3, 2, 1; 9 = "PUNCH!"; 0 none), p = expired bookings, o = the booking codes (2 bits per
-- kiosk: 1-3 punches).
-- LibCal-style confirmation codes (fix round, so the co-op needs talking): a kiosk's screen (the panel of whoever
-- stands at it) shows the codes of the OTHER lit kiosks, never its own, so the players have to tell each other. Punch
-- your kiosk that many times; `confirm` frames after the last punch it reads the count and sends a "kiosk" event with
-- it: the right code books the kiosk (the LEADER timestamps it on receipt, design 7.3), a wrong one buzzes. A booked
-- kiosk punched again does not refresh its time. Every lit kiosk booked within `window` s -> SUCCESS: room L129's
-- lock opens on every client and the star appears inside. A window that runs out rolls new codes. When everybody
-- stands at a lit kiosk the leader counts in 3-2-1-PUNCH. D-pad Down: back to a lit kiosk YOU have already walked to
-- this visit (the first trip to a kiosk is on foot), refused for window + 2 s after your own booking attempt (so
-- nobody books two kiosks alone).
---------------------------------------------------------------------------------------------
function sgl_marston_code_of(o, k)
    return ((o or 0) >> (2 * (k - 1))) & 3
end

local function kind_booking(spec)
    local K = { minPlayers = 2 }
    local ks = spec.kiosks
    local nK = #ks
    local WINDOW = math.floor(spec.window * 30)
    local CONFIRM = spec.confirm or 30
    local R, READY = spec.radius or 170, spec.readyRadius or 250

    local function count_for(n)
        return clamp(n, K.minPlayers, nK)
    end
    K.countFor = count_for

    local function lit_mask(N)
        local mask = 0
        for _, i in ipairs(spec.sets[N] or {}) do mask = mask | (1 << (i - 1)) end
        return mask
    end
    K.litMask = lit_mask

    local function current_mask(ctx)
        return lit_mask(ctx.a > 0 and ctx.a or count_for(ctx.n))
    end
    K.currentMask = current_mask

    local function at_kiosk(p, k, r)
        return dist2_xz(p, k) <= r * r and p.y >= k.y - 100 and p.y <= k.y + 300
    end
    K.atKiosk = at_kiosk

    -- new codes for the lit kiosks of `mask` (leader): 1-3 punches each
    local function roll_codes(mask)
        local o = 0
        for i = 1, nK do
            if (mask & (1 << (i - 1))) ~= 0 then o = o | (math.random(1, 3) << (2 * (i - 1))) end
        end
        return o
    end
    K.rollCodes = roll_codes

    local function codes_ok(o, mask)
        for i = 1, nK do
            if (mask & (1 << (i - 1))) ~= 0 and sgl_marston_code_of(o, i) == 0 then return false end
        end
        return true
    end

    K.needPlayers = function(ctx) return K.minPlayers end

    K.onReset = function(ctx)
        local N = count_for(ctx.n)
        ctx:set("a", N)
        ctx:set("f", 0)
        ctx:set("c", 0)
        ctx:set("g", 0)
        ctx:set("x", 0)
        ctx:set("p", 0)
        ctx:set("o", roll_codes(lit_mask(N)))
    end
    K.onStart = function(ctx)
        K.onReset(ctx)
        if ctx.lead ~= nil then ctx.lead.ts = {} end
    end

    K.leaderTick = function(ctx)
        local lead = ctx.lead
        lead.ts = lead.ts or {}
        local now = ctx.age
        local N = count_for(ctx.n)
        if N ~= ctx.a then
            ctx:set("a", N)
            lead.ts = {}
            ctx:set("o", roll_codes(lit_mask(N)))
        end
        local mask = lit_mask(N)
        if not codes_ok(ctx.o, mask) then ctx:set("o", roll_codes(mask)) end
        local booked, oldest = 0, nil
        for i = 1, nK do
            local bit = 1 << (i - 1)
            local ts = lead.ts[i]
            if (mask & bit) ~= 0 and ts ~= nil and now - ts <= WINDOW then
                booked = booked | bit
                if oldest == nil or ts < oldest then oldest = ts end
            end
        end
        if booked ~= ctx.f then ctx:set("f", booked) end
        local left = oldest ~= nil and math.max(1, math.ceil((WINDOW - (now - oldest)) / 30)) or 0
        if left ~= ctx.c then ctx:set("c", left) end
        if booked == mask then
            ctx:set("c", 0)
            ctx:set("x", 0)
            ctx:succeed()
            return
        end
        if booked ~= 0 then
            lead.open = true
        elseif lead.open then
            -- the window ran out with some kiosks still free: new codes on every screen
            lead.open = false
            lead.ts = {}
            lead.cinDone = false
            ctx:set("p", ctx.p + 1)
            ctx:set("o", roll_codes(mask))
            ctx:send("miss", {})
        end
        -- who stands at a lit kiosk; the count-in once everybody does
        local ready = 0
        for i, k in ipairs(ks) do
            local bit = 1 << (i - 1)
            if (mask & bit) ~= 0 then
                for _, li in ipairs(ctx.players) do
                    local mm = gMarioStates[li]
                    if alive(mm) and at_kiosk(mm.pos, k, READY) then
                        ready = ready | bit
                        break
                    end
                end
            end
        end
        if ready ~= ctx.g then ctx:set("g", ready) end
        if ready ~= mask then
            lead.cinDone = false
            if lead.cin ~= nil and lead.cin < 90 then
                lead.cin = nil
                if ctx.x ~= 0 then ctx:set("x", 0) end
            end
        end
        if lead.cin == nil and not lead.cinDone and ready == mask and booked == 0 then lead.cin = 0 end
        if lead.cin ~= nil then
            lead.cin = lead.cin + 1
            local x
            if lead.cin < 90 then
                x = 3 - lead.cin // 30
            elseif lead.cin < 135 then
                x = 9
            else
                x = 0
                lead.cin = nil
                lead.cinDone = true
            end
            if x ~= ctx.x then ctx:set("x", x) end
        end
    end

    K.onEvent = function(ctx, ev, data)
        if data.r ~= ctx.r then return end
        local me = data.gi == gNetworkPlayers[0].globalIndex
        if ev == "kiosk" then
            local k, n = data.k, data.n
            if math.type(k) ~= "integer" or k < 1 or k > nK or math.type(n) ~= "integer" then return end
            local bit = 1 << (k - 1)
            local right = n == sgl_marston_code_of(ctx.o, k)
            if ctx.isLeader and ctx.s == SGL_MS_ACTIVE and (current_mask(ctx) & bit) ~= 0 and right then
                local lead = ctx.lead
                lead.ts = lead.ts or {}
                local ts = lead.ts[k]
                if ts == nil or ctx.age - ts > WINDOW then lead.ts[k] = ctx.age end
            end
            if not me then
                if right then
                    sgl_hud_toast(string.format("%s booked kiosk %s!", data.nm or "?", ks[k].name), 2, SGL_HUD_GOLD)
                    play_sound(SOUND_GENERAL2_SWITCH_TICK_FAST, gGlobalSoundSource)
                else
                    sgl_hud_toast(string.format("%s punched a wrong code at %s", data.nm or "?", ks[k].name), 2, SGL_HUD_ORANGE)
                end
                ctx.loc.expandUntil = ctx.age + 150
            end
        elseif ev == "miss" then
            play_sound(SOUND_MENU_CAMERA_BUZZ, gGlobalSoundSource)
            sgl_hud_toast("Booking expired! New codes on the kiosk screens - all within " .. spec.window .. " s", 3,
                SGL_HUD_RED)
            ctx.loc.expandUntil = ctx.age + 150
            ctx.loc.burst = nil
        end
    end

    K.spawnLocal = function(ctx)
        ctx.objs.kiosks = {}
        for i, k in ipairs(ks) do
            local body = spawn_box(k.x, k.y, k.z, 100, 100, 100, 0, E_MODEL_EXCLAMATION_BOX, 3)
            local fx = spawn_non_sync_object(id_bhvSglMissionFx, E_MODEL_RED_FLAME, k.x, k.y + 230, k.z,
                function(obj) obj_scale(obj, 3) end)
            ctx.objs.kiosks[i] = { body = body, fx = fx }
        end
        local d = spec.door
        local cx, cz, len, yaw = door_box(d, spec.doorMargin or 30)
        ctx.objs.door = spawn_box(cx, d.y, cz, len, spec.doorHeight or 520, spec.doorThick or 40, yaw,
            E_MODEL_EXCLAMATION_BOX_OUTLINE, 0)
        ctx.objs.doorPos = { x = cx, y = d.y, z = cz }
        ctx.objs.doorOpen = false
    end

    -- the nearest lit kiosk nobody else stands at, among `allowed` (bits; nil = any)
    local function free_kiosk(ctx, from, allowed)
        local mask = current_mask(ctx) & (allowed or 0xFF)
        local best, bestD = nil, nil
        for i, k in ipairs(ks) do
            if (mask & (1 << (i - 1))) ~= 0 then
                local taken = false
                for _, li in ipairs(ctx.players) do
                    if li ~= 0 and at_kiosk(gMarioStates[li].pos, k, 300) then taken = true end
                end
                local d = dist2_xz(from, k) + (from.y - k.y) ^ 2
                if not taken and (bestD == nil or d < bestD) then best, bestD = i, d end
            end
        end
        return best
    end
    K.freeKiosk = free_kiosk

    K.localTick = function(ctx)
        local L = ctx.loc
        local m = gMarioStates[0]
        local mask = current_mask(ctx)
        local live = ctx.s == SGL_MS_ACTIVE or ctx.s == SGL_MS_WAITING or ctx.s == SGL_MS_INTRO
        L.punchAt = L.punchAt or {}
        L.reached = L.reached or 0
        -- where I stand; my punches at a lit kiosk (a burst: its code is read CONFIRM frames after the last punch)
        L.at = nil
        for i, k in ipairs(ks) do
            local bit = 1 << (i - 1)
            if (mask & bit) ~= 0 and alive(m) then
                if at_kiosk(m.pos, k, READY) then L.reached = L.reached | bit end
                if at_kiosk(m.pos, k, R) then
                    L.at = i
                    if ctx.s == SGL_MS_ACTIVE and punching(m) and ctx.age - (L.punchAt[i] or -9999) >= 15 then
                        L.punchAt[i] = ctx.age
                        if (ctx.f & bit) ~= 0 then
                            sgl_hud_toast("Kiosk " .. k.name .. " is already booked", 1, SGL_HUD_GREEN)
                        else
                            if L.burst ~= nil and L.burst.k == i then
                                L.burst.n = L.burst.n + 1
                            else
                                L.burst = { k = i, n = 1 }
                            end
                            L.burst.last = ctx.age
                            play_sound(SOUND_GENERAL2_SWITCH_TICK_FAST, gGlobalSoundSource)
                        end
                    end
                end
            end
        end
        if ctx.s ~= SGL_MS_ACTIVE then L.burst = nil end
        local b = L.burst
        if b ~= nil and ctx.age - b.last >= CONFIRM then
            L.burst = nil
            L.lastPunch = ctx.age
            ctx:send("kiosk", { k = b.k, n = b.n, nm = gNetworkPlayers[0].name })
            if b.n == sgl_marston_code_of(ctx.o, b.k) then
                play_sound(SOUND_GENERAL2_RIGHT_ANSWER, gGlobalSoundSource)
                sgl_hud_toast("Kiosk " .. ks[b.k].name .. " booked! The others have " .. spec.window .. " s", 2, SGL_HUD_GOLD)
            else
                play_sound(SOUND_MENU_CAMERA_BUZZ, gGlobalSoundSource)
                sgl_hud_toast(string.format("Wrong code (%d punch%s)! Your code is on your friend's screen", b.n,
                    b.n == 1 and "" or "es"), 3, SGL_HUD_RED)
                L.wrong = (L.wrong or 0) + 1
            end
            L.expandUntil = ctx.age + 150
        end
        -- kiosks: lit = solid yellow "!" box + red flame; booked = green box + blue flame; unlit = gone
        for i, rec in ipairs(ctx.objs.kiosks or {}) do
            local bit = 1 << (i - 1)
            local on = (mask & bit) ~= 0 and ctx.s ~= SGL_MS_DONE
            box_on(rec.body, on)
            local booked = (ctx.f & bit) ~= 0
            if obj_ok(rec.body.vis, id_bhvSglMarstonProp) then rec.body.vis.oAnimState = booked and 1 or 3 end
            if obj_ok(rec.fx, id_bhvSglMissionFx) then
                local want = booked and E_MODEL_BLUE_FLAME or E_MODEL_RED_FLAME
                if rec.model ~= want then
                    obj_set_model_extended(rec.fx, want)
                    rec.model = want
                end
                set_hidden(rec.fx, not (on and live))
            end
        end
        -- room L129's lock: shut until the booking succeeds
        local open = ctx.s == SGL_MS_SUCCESS or ctx.s == SGL_MS_DONE
        if ctx.objs.door ~= nil then
            box_on(ctx.objs.door, not open)
            if open and not ctx.objs.doorOpen then
                play_sound(SOUND_GENERAL_OPEN_IRON_DOOR, gGlobalSoundSource)
                sgl_hud_toast("Room L129 is booked! The star is inside", 4, SGL_HUD_GOLD)
            end
            ctx.objs.doorOpen = open
        end
        -- count-in ticks
        if ctx.x ~= (L.x or 0) then
            if ctx.x >= 1 and ctx.x <= 3 then play_sound(SOUND_MENU_CHANGE_SELECT, gGlobalSoundSource) end
            if ctx.x == 9 then play_sound(SOUND_GENERAL2_RIGHT_ANSWER, gGlobalSoundSource) end
            L.x = ctx.x
        end
    end

    K.panel = function(ctx)
        local L = ctx.loc
        local mask = current_mask(ctx)
        local N = popcount(mask)
        local lines = {}
        if ctx.c > 0 then
            table.insert(lines, { string.format("BOOKING OPEN: %d s - book the other kiosks! (%d/%d)", ctx.c,
                popcount(ctx.f & mask), N), SGL_HUD_GOLD })
        else
            table.insert(lines, { string.format("Book room L129: all %d kiosks within %d s", N, spec.window), SGL_HUD_WHITE })
        end
        for i, k in ipairs(ks) do
            local bit = 1 << (i - 1)
            if (mask & bit) ~= 0 then
                local text, col
                if (ctx.f & bit) ~= 0 then
                    text, col = " - booked", SGL_HUD_GREEN
                elseif (ctx.g & bit) ~= 0 then
                    text, col = " - ready", SGL_HUD_WHITE
                else
                    text, col = " - nobody there", SGL_HUD_RED
                end
                table.insert(lines, { "  " .. k.name .. text .. (L.at == i and "  (you)" or ""), col, 0.28 })
            end
        end
        if L.at ~= nil then
            -- this kiosk's screen: the OTHER kiosks' codes
            table.insert(lines, { "This screen shows your friends' codes - tell them:", SGL_HUD_GOLD, 0.28 })
            for i, k in ipairs(ks) do
                local code = sgl_marston_code_of(ctx.o, i)
                if (mask & (1 << (i - 1))) ~= 0 and i ~= L.at and code > 0 then
                    table.insert(lines, { string.format("  %s: punch %d time%s", k.name, code, code == 1 and "" or "s"),
                        SGL_HUD_WHITE, 0.28 })
                end
            end
            table.insert(lines, { "Your own code is on a friend's screen. Punch it (B) - it reads 1 s later",
                SGL_HUD_GREY, 0.24 })
        elseif ((L.reached or 0) & mask) ~= 0 then
            table.insert(lines, { "D-pad Down: back to a kiosk you have reached", SGL_HUD_GREY, 0.26 })
        else
            table.insert(lines, { "Walk to a lit kiosk: its screen shows your friends' codes", SGL_HUD_GREY, 0.26 })
        end
        if ctx.p > 0 then table.insert(lines, { "Expired bookings: " .. ctx.p, SGL_HUD_GREY, 0.26 }) end
        table.insert(lines, { "(LibCal: a group study room is booked by 2 or more people)", SGL_HUD_GREY, 0.22 })
        return lines
    end

    K.hud = function(ctx)
        local m = gMarioStates[0]
        local L = ctx.loc
        if ctx.s == SGL_MS_ACTIVE then
            local mask = current_mask(ctx)
            for i, k in ipairs(ks) do
                local bit = 1 << (i - 1)
                if (mask & bit) ~= 0 and L.at ~= i then
                    local booked = (ctx.f & bit) ~= 0
                    sgl_hud_marker(up(k, 200), booked and "" or ("KIOSK " .. k.name), booked and SGL_HUD_GREEN or SGL_HUD_RED,
                        m, booked)
                end
            end
            if ctx.x >= 1 and ctx.x <= 3 then
                sgl_hud_big(tostring(ctx.x), SGL_HUD_GOLD, 3)
            elseif ctx.x == 9 then
                sgl_hud_big("PUNCH!", SGL_HUD_GOLD, 2.6)
            elseif L.burst ~= nil then
                sgl_hud_big("x" .. L.burst.n, SGL_HUD_WHITE, 2.2)
            elseif ctx.c > 0 then
                sgl_hud_big(tostring(ctx.c), SGL_HUD_ORANGE, 2.2)
            end
        end
        local d = ctx.objs.doorPos
        if d ~= nil and ctx.s ~= SGL_MS_SUCCESS and ctx.s ~= SGL_MS_DONE and math.abs(m.pos.y - d.y) < 300
            and dist2_xz(m.pos, d) <= 1500 * 1500 then
            sgl_hud_marker(up(d, 300), "ROOM L129 - LOCKED", SGL_HUD_GOLD, nil, true)
        end
    end

    -- D-pad Down / /mission start: back to the nearest free lit kiosk I have already walked to
    K.toStart = function(ctx, m)
        if not can_teleport(m) or ctx.s ~= SGL_MS_ACTIVE then return false end
        local L = ctx.loc
        if L.lastPunch ~= nil and ctx.age - L.lastPunch < WINDOW + 60 then
            sgl_hud_toast("You just used a kiosk - let your friends book theirs", 2, SGL_HUD_ORANGE)
            return false
        end
        if L.at ~= nil then
            sgl_hud_toast("You are at a kiosk: punch your code (B)", 2, SGL_HUD_WHITE)
            return false
        end
        local i = free_kiosk(ctx, m.pos, L.reached or 0)
        if i == nil then
            sgl_hud_toast("Walk to a lit kiosk first: D-pad Down only takes you back to one you have reached", 3,
                SGL_HUD_ORANGE)
            return false
        end
        local k = ks[i]
        local yaw = k.yaw or 0
        teleport(m, { x = k.x - sins(yaw) * 220, y = k.y, z = k.z - coss(yaw) * 220 }, yaw)   -- 2.2 m back, facing it
        play_sound(SOUND_MENU_EXIT_PIPE, gGlobalSoundSource)
        sgl_hud_toast("Kiosk " .. k.name, 2, SGL_HUD_WHITE)
        return true
    end
    return K
end

---------------------------------------------------------------------------------------------
-- act 1: OUT-OF-ORDER ELEVATOR
---------------------------------------------------------------------------------------------
sgl_mission_register({
    id = "marston_climb",
    pointsFile = POINTS_FILE,
    level = LEVEL_CCM,
    act = MARSTON_MISSION_ACTS.climb,
    title = "OUT-OF-ORDER ELEVATOR",
    objective = "The elevator's broken! Climb the atrium to the 5th floor!",
    star = P.climb_star,            -- spawned in the 5th-floor north reading room (no level-script star)
    starFrom = up(P.climb_star, -80),   -- rising out of the floor below it: the spawn's 4 m hump (bhvStarSpawnCoordinates)
                                    -- stays under the 5.4 m ceiling
    starCutsceneRange = 3000,
    probes = { probe(P.spawn, "the 2nd-floor lobby"), probe(P.board_a, "the 3rd-floor atrium balcony"),
        probe(P.climb_goal, "the 5th-floor reading room") },
    compactPanel = true,
    kind = kind_climb({
        reach = {
            goal = P.climb_goal,
            goalRadius = 800,       -- anywhere in the north reading room (17 x 24 m) ...
            goalBelow = 50,         -- ... with the feet on floor 5
            goalLabel = "5TH FLOOR READING ROOM",
            zone = P.zone,
            ground = P.y_f2,        -- 0 m = the entrance floor
            milestones = {
                { name = "3rd floor", y = P.y_f3 },
                { name = "4th floor", y = P.y_f4 },
            },
            route = {
                { pos = P.stair_foot, label = "GRAND STAIR", doneY = P.y_f3 - 50 },
                { pos = P.board_a, label = "BOOK-CART LIFT", doneY = P.y_f4 - 50 },
                { pos = P.board_b, label = "BOOK-CART LIFT", doneY = P.y_f5 - 50 },
            },
        },
        lifts = {
            { x = P.lift_a.x, z = P.lift_a.z, bottom = P.lift_a.bottom, top = P.lift_a.top, half = P.lift_a.half, offset = 0 },
            -- offset 20 (fix round; was 160): lift A tops out at F4 at t = 160 (cycle 320); the ~4.5 s run round the
            -- F4 balcony to board_b arrives at t ~ 295, and lift B (u = t + 20) reaches the bottom at t = 300 and waits
            -- 2 s there: the two lifts chain instead of a ~5 s wait
            { x = P.lift_b.x, z = P.lift_b.z, bottom = P.lift_b.bottom, top = P.lift_b.top, half = P.lift_b.half, offset = 20 },
        },
        cart = { half = 110 },      -- the book cart across the void at F4, lift A -> lift B (nil: no cart)
        barriers = P.stair_doors,   -- {} opens the stairs
        basement = { below = P.y_f1 + 150, to = P.spawn, yaw = 0x0000 },   -- down the chute to F1: back to the lobby
        barrierMargin = 30,         -- 0.3 m past both jambs
        barrierHeight = 500,
        barrierThick = 40,
        atrium = P.atrium,
        shaft = P.shaft_door,
        books = {                   -- nil removes the flying books
            floors = { P.y_f3, P.y_f4 },
            reach = 400,            -- on the balconies: within 4 m of the void
            first = 90,             -- 3 s after stepping out, then
            every = 210,            -- one every 7 s (one at a time)
            telegraph = 30,         -- it hovers and shakes for 1 s ...
            speed = 36,             -- ... then flies at 10.8 m/s ...
            life = 60,              -- ... for 2 s
            hurt = 4,               -- a hit: one wedge and a knock-back
            scale = 1.0,
            model = E_MODEL_BOOKEND,
        },
    }),
})

---------------------------------------------------------------------------------------------
-- act 2: SHHH! LOST TEXTBOOKS
---------------------------------------------------------------------------------------------
sgl_mission_register({
    id = "marston_quiet",
    pointsFile = POINTS_FILE,
    level = LEVEL_CCM,
    act = MARSTON_MISSION_ACTS.quiet,
    title = "SHHH! LOST TEXTBOOKS",
    objective = "Find 8 lost textbooks on the silent 5th floor. Shhh!",
    star = P.quiet_star,            -- by the west window desk (design 7.3 act 2's goal), on the quiet floor
    starFrom = up(P.quiet_star, -80),   -- out of the floor (the hump stays under the ceiling)
    starCutsceneRange = 3000,
    probes = { probe(P.quiet_start, "the 5th-floor north reading room"), probe(P.books[8], "the 5th-floor west reading room") },
    compactPanel = true,
    sneakY = P.y_f5,                -- hold L on this floor: tiptoe (quiet_sneak, end of file)
    kind = kind_quiet({
        books = P.books,
        y = P.y_f5,
        start = P.quiet_start,
        startYaw = 0xC000,          -- facing west, into the reading room
        patrols = {
            { pts = P.patrol_n, loop = false, s0 = 0 },
            { pts = P.patrol_w, loop = true, s0 = 1500 },
            { pts = P.patrol_c, loop = false, s0 = 600 },
        },
        speed = 4,                  -- 1.2 m/s
        pause = 60,                 -- a pause unit is 2 s ...
        hmUnits = 1,                -- ... a half-heard noise: it stops and looks for 2 s
        shhUnits = 2,               -- ... shushing someone: 4 s
        sight = 220,                -- it sees you 2.2 m ahead ...
        sightHalf = 0x2700,         -- ... within 55 degrees either side
        bump = 110,
        sameFloor = 350,
        alert = 1.6,                -- noise heard at the edge (up to 1.6 x its radius): stop and look
        cool = 75,                  -- 2.5 s of grace after being sent back
        radius = 140,               -- touch a textbook (1.4 m) ...
        below = 100,
        above = 250,
        model = E_MODEL_TOAD,       -- a Toad librarian (vanilla, no walk animation: it bobs)
        modelScale = 1.3,
    }),
})

---------------------------------------------------------------------------------------------
-- act 3 (co-op): STUDY ROOM BOOKING - 2P
---------------------------------------------------------------------------------------------
sgl_mission_register({
    id = "marston_booking",
    pointsFile = POINTS_FILE,
    level = LEVEL_CCM,
    act = MARSTON_MISSION_ACTS.booking,
    title = "STUDY ROOM BOOKING - 2P",
    objective = "Swap booking codes, then book every kiosk within 4 s!",
    star = P.room_star,             -- inside glass room L129 on floor 1
    starFrom = up(P.room_star, -80),    -- out of the room's floor (the hump stays under the ceiling)
    starCutsceneRange = 2500,
    probes = { probe(P.kiosks[1], "the 1st-floor commons by L129"), probe(P.kiosks[4], "the 5th-floor west wing") },
    kind = kind_booking({
        kiosks = P.kiosks,
        sets = { [2] = { 1, 4 }, [3] = { 1, 3, 4 }, [4] = { 1, 2, 3, 4 } },   -- 1F + 5F; + 4F; all four
        window = 4,                 -- design 7.3: within 4 s of each other
        confirm = 30,               -- a kiosk reads the punches 1 s after the last one
        radius = 170,               -- punch from 1.7 m (the box is 1 m)
        readyRadius = 250,
        door = P.room_door,
        doorMargin = 30,
        doorHeight = 520,
        doorThick = 40,
    }),
})

---------------------------------------------------------------------------------------------
-- act 2: hold L to tiptoe (keyboard players; see SGL_MARSTON_SNEAK_STICK)
---------------------------------------------------------------------------------------------
local function quiet_sneak(m)
    if m.playerIndex ~= 0 then return end
    local ctx = sgl_mission_ctx()
    if ctx == nil or ctx.def == nil or ctx.def.id ~= "marston_quiet" or ctx.def.sneakY == nil
        or gNetworkPlayers[0].currLevelNum ~= ctx.def.level then return end
    if ctx.s ~= SGL_MS_ACTIVE and ctx.s ~= SGL_MS_INTRO and ctx.s ~= SGL_MS_SUCCESS then return end
    local c = m.controller
    if c == nil or (c.buttonDown & L_TRIG) == 0 or math.abs(m.pos.y - ctx.def.sneakY) > 350 then return end
    c.stickX, c.stickY, c.stickMag = sgl_marston_sneak_stick(c.stickX, c.stickY, c.stickMag)
    ctx.loc.sneaking = ctx.age
end

hook_event(HOOK_BEFORE_MARIO_UPDATE, quiet_sneak)
