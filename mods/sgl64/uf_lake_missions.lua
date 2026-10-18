-- Super Gatorlator 64: Lake Alice (course 3, LEVEL_JRB, hub door 3 "Newell Hall") missions, on the
-- framework in sgl_mission.lua (docs/game_design.md 7.4, docs/flow.md 5).
--
--   act 1  BOARDWALK WELCOME         solo (design 7.4 act 1): from the bat-house field across Museum Road onto
--                                    the north boardwalk, wade onto the west bog, then hop the 15 lily pads of
--                                    the north_shallows route (level collision, lake_alice_water.py) out to the
--                                    observation deck at the lake centre (stage_lake.py), where the mission
--                                    spawns the star on the deck's far side. Five vanilla Skeeters skate beside
--                                    the pad line and two big gators lurk in the open water beside its middle
--                                    (local objects): the pads are the safe way, a swimmer gets bitten.
--   act 2  GATOR HOP                 solo-friendly (design 7.4 act 2): from the deck's big end pad, 17 basking
--                                    gators (Lua platforms) lead north over the deep hole to the gator nest on
--                                    the small bog. They sink in a wave (2.8 s up, 1.6 s under), timed by the
--                                    network area timer, so every client sees the same gators. Two players on
--                                    one gator make it sink at once (co-op: spread out). Three big gators
--                                    patrol beside the line (by gators 3-7, at the bend, south of the nest)
--                                    and snap at anyone in the water nearby (a wedge and a knock-back). The
--                                    gators must be hopped in order (one may be skipped): swimming straight to
--                                    the nest does not count.
--   act 3  BAT CENSUS AT DUSK - 2P   co-op, 2-4 players (design 7.4 act 4): the act plays at dusk (lighting
--                                    set from Lua, restored when you leave the act; night falls during the
--                                    count). Three census posts (by the bat barns, in the Bat House Gardens,
--                                    on the north boardwalk, 67-136 m apart) count bats only while someone
--                                    stands on them. Once two posts are staffed the bats stream out of the
--                                    two barns for 90 s: count 600 + 300 per extra player (at most 1500). One
--                                    post alone can never make it. Each player's bat swarm streams over their
--                                    own post. Swoopers dive at the counters (one at a time, every 11 s); a hit
--                                    is a knock-back (no damage) that stops your count until you are back on.
--   act 4  GATOR REGATTA             race, solo or with friends (design 7.4 act 3 "Shell Surf Regatta"): a ride gator
--                                    waits at the dock (the water off the Baughman lawn); ride it into the start box,
--                                    and after the countdown round the 8 buoys in order (tall, wide checkpoints,
--                                    flames over them, the next one blue). The timer stops at buoy 8; under par
--                                    (1'15) the star lands at the dock. Lost your gator? A spare waits on the east
--                                    shore, and the dock's comes back. Every player rides their own (local) gator;
--                                    friends see a stand-in gator under each other.
--   acts 5-6 "COMING SOON - ..." in course.lua (design 7.4 acts 5, 6): free roam, no star.
-- Act order (course.lua header): playable acts 1..4 with no gap, the solo ones first up to the co-op act 3 (the
-- regatta is act 4 like every stage's next act, so act select offers it after act 3's star). Every star is spawned
-- by its mission (spawn_default_star from the controller loop, star id = act - 1): the level script must NOT
-- place a bhvStar for acts 1-4. Each mission checks the stage geometry first (probes on LAKE_POINTS): if
-- levels/jrb is not the real Lake Alice they stay offline (/mission force overrides).
--
-- File name: coopdx loads a mod's files in strcmp order of their names. This file registers missions at load,
-- so it must sort AFTER sgl_mission.lua (docs/flow.md 7 step 9); it also sorts after swamp_missions.lua, which
-- keeps the order the other suites check ("lake_missions.lua" or "jrb_..." would load before the framework).
--
-- Networking: act 1, the act 2 nest and the act 4 race need nothing new (synced positions and actions; reliable
-- "hop" / "nest" / "fin" events, hop and nest re-sent after 3 s while unapplied). The basking gators are local
-- copies driven by get_network_area_timer() (identical on every client of the area); the "two on one gator" sink
-- is decided by each client from the synced player positions. The ride gators of act 4, big gators, Skeeters, the
-- bat swarm and the diving Swoopers are local objects:
-- each player is chased only by their own copies (design 7.4: "Swooper spawns are local and cosmetic"). The
-- census count is the leader's: it samples who stands on which post at 2 Hz (the design's rule) and writes
-- the count to the synced fields; a new leader carries on from the synced count.

---------------------------------------------------------------------------------------------
-- ALL Lake Alice mission coordinates, in game units (area 1 of LEVEL_JRB). Swap values here only.
-- Source: data/uf/lake_points.json (written by tools/campus/build_stage.py lake_alice from the BUILT collision;
-- "game" = [X, floor Y, Z]; its actN_ keys use the DESIGN act numbers: design 4 = course act 3), point names in
-- the comments; without a JSON point, the landmark modules tools/campus/landmarks/lake_alice_water.py (basin,
-- lily pads, bog islands) and lake_alice_shore.py (bat barns, boardwalks, bat-house field), map metres, through
-- the stages.json transform of the lake_alice window (centre (-1760, -660) m):
--   X = (x + 1760) * 100,  Y = z * 100,  Z = -(y + 660) * 100.
-- Y is the floor (Mario's feet) at a standing point; the ground is Y 0, the lake surface Y -50 (water boxes),
-- its bed about Y -300 (deep holes to -500). tools/luatest/check_lake_points.py recomputes every value (derived
-- ones too) and fails on drift > 0.5 m; --print prints fresh values and where each one comes from.
-- Derived values (rules in check_lake_points.py): gators = 4.4 x 1.6 m backs every 6.71 m along end pad ->
-- GATOR_BEND map (-1716, -600) -> the small bog's south shore (2 m from the end pad's edge, 1.2 m from the
-- bog), yaw along the line, bed = the HIGHEST lake bed under the back; nest_star / census_star = 1.2 / 1.5 m over
-- their spot, regatta_star 1.2 m over the dock's water. deck_star / deck_star_from, lurk_gators and big_gators: stage_lake.py's rules (STAR_*, act1_lurk_spots,
-- BIG_GATOR_SPOTS), measured into the JSON by the build.
-- (The table is built by a local function so its ~250 numbers are that function's constants, not the main
-- chunk's: with more than 256 main-chunk constants luac stops using SETTABUP for globals, which
-- tools/luatest/check_globals.lua reads.)
---------------------------------------------------------------------------------------------
local function lake_points() return {
    water_y = -50,                                              -- water.surface_game_y (COL_WATER_BOX surface)
    spawn_field = { x = -13300, y = 0, z = -11900 },            -- spawn_0x0A (the bat-house field)

    -- act 1 (design 1): north boardwalk -> west bog -> north_shallows lily pads -> the observation deck
    boardwalk = { x = -8330, y = 50, z = -5121 },               -- act1_boardwalk_mid (deck 0.5 m)
    bog = { x = -3950, y = -12, z = -5750 },                    -- act1_west_bog_top (west bog hummock)
    deck = { x = 2590, y = 20, z = -470 },                      -- act1_deck_center (octagon, top 0.2 m, pavilion)
    deck_r = 450,                                               -- act1 deck geometry.inradius_m
    deck_star = { x = 2783, y = 140, z = -202 },                -- act1_star_target (1.2 m over the deck's far side,
                                                                --   1 m clear of the pavilion roof's eave)
    deck_star_from = { x = 3145, y = 300, z = 301 },            -- act1_star_from (3 m over the water beyond it)
    pads = {                                                    -- act1_pad_00..14, y = pad top, r = radius_m
        { x = -2420, y = -40, z = -5660, r = 170 },
        { x = -1979, y = -40, z = -5569, r = 150 },
        { x = -1658, y = -40, z = -5268, r = 150 },
        { x = -1209, y = -40, z = -5260, r = 140 },
        { x = -899, y = -40, z = -4933, r = 140 },
        { x = -434, y = -40, z = -4680, r = 230 },
        { x = -199, y = -40, z = -4204, r = 130 },
        { x = 208, y = -40, z = -4012, r = 130 },
        { x = 350, y = -40, z = -3574, r = 130 },
        { x = 718, y = -40, z = -3298, r = 120 },
        { x = 816, y = -40, z = -2849, r = 120 },
        { x = 1196, y = -40, z = -2555, r = 130 },
        { x = 1330, y = -40, z = -2083, r = 130 },
        { x = 1730, y = -40, z = -1801, r = 120 },
        { x = 2048, y = -40, z = -1223, r = 300 },              -- the big end pad, 1.8 m from the deck: act 2's first hop
    },
    skeeters = {                                                -- act1_skeeter_0..4 (water surface, 7 m beside the pads)
        { x = -2137, y = -50, z = -4757 },
        { x = -99, y = -50, z = -5295 },
        { x = -316, y = -50, z = -3358 },
        { x = 1624, y = -50, z = -3109 },
        { x = 1327, y = -50, z = -1229 },
    },
    lurk_gators = {                                             -- act1_lurk_gator_0..1: lurking big gators' homes
        { x = -300, z = -5734, bed = -277 },                    -- 10 m left of pad 5 (bed = floor_below)
        { x = -25, z = -2308, bed = -301 },                     -- 10 m right of pad 11
    },

    -- act 2 (design 2): the gator line and the nest on the small bog
    nest = { x = 3950, y = -11, z = -13150 },                   -- act2_nest_island_top (the bog's middle; the mound is 2.6 m west)
    nest_star = { x = 3950, y = 109, z = -13150 },              -- act 2 star, 1.2 m over the nest spot
    gators = {                                                  -- basking gators in hop order, derived
        { x = 2366, z = -1869, yaw = 27996, bed = -309 },
        { x = 2662, z = -2471, yaw = 27996, bed = -308 },
        { x = 2959, z = -3072, yaw = 27996, bed = -307 },
        { x = 3255, z = -3674, yaw = 27996, bed = -308 },
        { x = 3551, z = -4276, yaw = 27996, bed = -316 },
        { x = 3847, z = -4878, yaw = 27996, bed = -332 },
        { x = 4144, z = -5480, yaw = 27996, bed = -356 },
        { x = 4394, z = -6090, yaw = 33424, bed = -366 },
        { x = 4352, z = -6760, yaw = 33424, bed = -339 },
        { x = 4310, z = -7429, yaw = 33424, bed = -316 },
        { x = 4268, z = -8099, yaw = 33424, bed = -303 },
        { x = 4226, z = -8768, yaw = 33424, bed = -298 },
        { x = 4184, z = -9438, yaw = 33424, bed = -298 },
        { x = 4142, z = -10107, yaw = 33424, bed = -298 },
        { x = 4099, z = -10776, yaw = 33424, bed = -299 },
        { x = 4057, z = -11446, yaw = 33424, bed = -243 },
        { x = 4015, z = -12115, yaw = 33424, bed = -98 },       -- by the bog's skirt: it barely sinks
    },
    gator_bend = { x = 4400, y = -50, z = -6000 },              -- GATOR_BEND (west rim of the deep hole deep_1)
    big_gators = {                                              -- act2_big_gator_0..2: patrol homes (bed = floor_below)
        { x = 4600, z = -10400, bed = -283 },                   -- open water south of the small bog (gators 12-16)
        { x = 2790, z = -4310, bed = -308 },                    -- 7 m west of the line's first leg (gators 3-7)
        { x = 5600, z = -7000, bed = -396 },                    -- east of the bend, rim of deep_1 (gators 8-11)
    },

    -- act 3 (design 4): the census posts and the bat barns
    census_houses = { x = -13000, y = 0, z = -13200 },          -- act4_station_houses (field by the barn fences)
    census_gardens = { x = -8996, y = 0, z = -18553 },          -- act4_station_gardens (Bat House Gardens)
    census_boardwalk = { x = -8243, y = 50, z = -4975 },        -- act4_station_boardwalk (viewing bay, 0.5 m)
    bat_exit_2010 = { x = -12257, y = 420, z = -14944 },        -- act4_bat_exit_0 (the 2010 barn's open bottom)
    bat_exit_2017 = { x = -14890, y = 420, z = -15729 },        -- act4_bat_exit_1 (the 2017 barn)
    census_star = { x = -13000, y = 150, z = -13200 },          -- act 3 star, 1.5 m over the barns' post

    -- act 4 (design 3, Shell Surf Regatta): the dock, the 8 buoys, the spare gator on the safe shoreline
    regatta_dock = { x = -18100, y = -50, z = 4050 },           -- act3_start_water_baughman (the water off the Baughman
                                                                --   lawn, 0.4 m deep: the start box and the dock gator)
    regatta_star = { x = -18100, y = 70, z = 4050 },            -- act 4 star, 1.2 m over the dock's water
    regatta_spare = { x = 11746, y = 0, z = 5118 },             -- shoreline shore_cp_08 (east bank, 42 m off the
                                                                --   buoy 4 -> 5 leg): the spare gator
    buoys = {                                                   -- act3_buoy_1..8 (water surface; >= 27 m from every
        { x = -14500, y = -50, z = 1200 },                      --   shore and bog, open water between them)
        { x = -7600, y = -50, z = 9200 },
        { x = -3000, y = -50, z = 4600 },
        { x = 6000, y = -50, z = 1200 },
        { x = 17200, y = -50, z = 600 },
        { x = 12000, y = -50, z = -7500 },
        { x = 4400, y = -50, z = -8500 },
        { x = -6000, y = -50, z = -1000 },
    },
} end
LAKE_POINTS = lake_points()

-- which act each mission is (star id = act - 1). Keep in step with the act names in course.lua
-- (tools/luatest/test_lake_missions.lua checks that every mission title equals its course.lua act name).
LAKE_MISSION_ACTS = { boardwalk = 1, gators = 2, bats = 3, regatta = 4 }

---------------------------------------------------------------------------------------------
if sgl_mission_register == nil then
    log_to_console("[SGL] uf_lake_missions.lua: sgl_mission.lua is not loaded", CONSOLE_MESSAGE_ERROR)
    return
end

local P = LAKE_POINTS
local WATER_Y = P.water_y
local IN_WATER_Y = WATER_Y - 20          -- feet below this: in the lake (wading or swimming)
local POINTS_FILE = "uf_lake_missions.lua (LAKE_POINTS)"

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

local function lerp(a, b, t)
    return a + (b - a) * t
end

local function popcount(v)
    local n = 0
    while v > 0 do
        n = n + (v & 1)
        v = v >> 1
    end
    return n
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

-- a player who may be teleported (D-pad Down): alive, not in a cutscene, holding or riding nothing
local function can_teleport(m)
    return alive(m) and (m.action & ACT_GROUP_MASK) ~= ACT_GROUP_CUTSCENE and m.heldObj == nil and m.riddenObj == nil
end

local function teleport(m, p, faceYaw, text)
    local a = (gNetworkPlayers[0].globalIndex % 8) * math.pi / 4      -- players land side by side
    m.pos.x, m.pos.y, m.pos.z = p.x + math.sin(a) * 90, p.y + 20, p.z + math.cos(a) * 90
    m.vel.x, m.vel.y, m.vel.z = 0, 0, 0
    m.forwardVel = 0
    m.faceAngle.y = faceYaw
    set_mario_action(m, ACT_IDLE, 0)
    if m.area ~= nil and m.area.camera ~= nil then soft_reset_camera(m.area.camera) end
    play_sound(SOUND_MENU_EXIT_PIPE, gGlobalSoundSource)
    sgl_hud_toast(text, 2, SGL_HUD_WHITE)
end

-- vanilla animation of a visual stand-in (nil-safe: an object without the table keeps its model's pose)
local function animate(o, anims, index)
    if anims ~= nil then
        o.oAnimations = anims
        obj_init_animation(o, index or 0)
    end
end

-- the knock-back actions (a hit: a Swooper dive, a gator snap)
local KNOCKBACK = {}
for _, a in ipairs({ ACT_BACKWARD_GROUND_KB, ACT_FORWARD_GROUND_KB, ACT_HARD_BACKWARD_GROUND_KB, ACT_HARD_FORWARD_GROUND_KB,
    ACT_SOFT_BACKWARD_GROUND_KB, ACT_SOFT_FORWARD_GROUND_KB, ACT_BACKWARD_AIR_KB, ACT_FORWARD_AIR_KB,
    ACT_HARD_BACKWARD_AIR_KB, ACT_HARD_FORWARD_AIR_KB, ACT_BACKWARD_WATER_KB, ACT_FORWARD_WATER_KB }) do
    KNOCKBACK[a] = true
end

function sgl_lake_knocked_back(action)
    return KNOCKBACK[action] == true
end

---------------------------------------------------------------------------------------------
-- local objects: Lua platforms (basking gators: vanilla checkerboard-platform collision, scaled to a gator's
-- back, rotated by yaw, moved by Lua with oVel = the displacement, so the engine carries the rider), visual
-- props (the gators' bodies, station flames) and the cosmetic bats of the census.
---------------------------------------------------------------------------------------------
local PHX, PTOP, PBOT, PHZ = 256, 26, 25, 153     -- checkerboard collision at scale 1: half x, deck top, underside, half z
-- The platform object follows its record (rec.x/y/z, moved by the mission's local tick) by at most PLAT_STEP
-- units per frame on each axis, with oVel = that step, so the engine carries the rider. The controller keeps
-- ticking through a time stop (a star cutscene, a sign) while the platform itself is frozen: when time
-- resumes, the platform catches up at PLAT_STEP instead of jumping (a jump would drop its rider). Only a
-- record farther than PLAT_SNAP away (a broken record) is snapped to, carrying nobody.
local PLAT_STEP = 30
local PLAT_SNAP = 1500
local sPlat = {}
local sPlatNext = 0

-- one frame of an object at `cur` following `target`: at most PLAT_STEP per axis, a snap past PLAT_SNAP
-- -> the new position and the step (0 for a snap). Pure (tools/luatest checks it).
function sgl_lake_plat_follow(cur, target)
    local d = target - cur
    if math.abs(d) > PLAT_SNAP then return target, 0 end
    if d > PLAT_STEP then d = PLAT_STEP elseif d < -PLAT_STEP then d = -PLAT_STEP end
    return cur + d, d
end

local function plat_init(o)
    o.oFlags = OBJ_FLAG_UPDATE_GFX_POS_AND_ANGLE | OBJ_FLAG_ACTIVE_FROM_AFAR
    o.collisionData = gGlobalObjectCollisionData.checkerboard_platform_seg8_collision_0800D710
    o.oCollisionDistance = 1500
    o.oDrawingDistance = 20000
    o.oIntangibleTimer = -1
end

local function plat_loop(o)
    local rec = sPlat[o.oBehParams & 0xFF]
    if rec == nil or rec.o ~= o then
        obj_mark_for_deletion(o)
        return
    end
    if rec.drive ~= nil then rec.drive(rec) end
    local x, dx = sgl_lake_plat_follow(o.oPosX, rec.x)
    local y, dy = sgl_lake_plat_follow(o.oPosY, rec.y)
    local z, dz = sgl_lake_plat_follow(o.oPosZ, rec.z)
    o.oVelX, o.oVelY, o.oVelZ = dx, dy, dz
    o.oPosX, o.oPosY, o.oPosZ = x, y, z
    o.oFaceAngleYaw, o.oMoveAngleYaw = rec.yaw, rec.yaw
    load_object_collision_model()
    local v = rec.vis
    if v ~= nil and obj_ok(v, id_bhvSglLakeProp) then
        v.oPosX, v.oPosY, v.oPosZ = x, y + PTOP - (rec.visDrop or 0), z     -- the body sits on the collision
        v.oFaceAngleYaw = rec.yaw
        v.oFaceAngleRoll = rec.roll or 0
    end
end

id_bhvSglLakePlatform = hook_behavior(nil, OBJ_LIST_SURFACE, true, plat_init, plat_loop, "bhvSglLakePlatform")

-- visual-only stand-ins (gator bodies, big gators): no collision, no interaction, placed from Lua
local function prop_init(o)
    o.oFlags = OBJ_FLAG_UPDATE_GFX_POS_AND_ANGLE | OBJ_FLAG_ACTIVE_FROM_AFAR
    o.oDrawingDistance = 20000
    o.oIntangibleTimer = -1
end

local function prop_loop(o)
end

id_bhvSglLakeProp = hook_behavior(nil, OBJ_LIST_DEFAULT, true, prop_init, prop_loop, "bhvSglLakeProp")

-- a platform of half width hw (local x) and half length hl (local z, along yaw) whose deck top is `top`
-- -> the record (rec.o = the platform object, rec.vis = its visual stand-in)
local function spawn_platform(x, top, z, yaw, hw, hl, drive, model, modelScale, visDrop)
    sPlatNext = (sPlatNext % 250) + 1
    local idx = sPlatNext
    local rec = { x = x, y = top - PTOP, z = z, yaw = yaw, drive = drive, idx = idx, visDrop = visDrop }
    sPlat[idx] = rec
    rec.o = spawn_non_sync_object(id_bhvSglLakePlatform, E_MODEL_NONE, x, rec.y, z, function(obj)
        obj.oBehParams = idx
        obj.oFaceAngleYaw, obj.oMoveAngleYaw = yaw, yaw
        obj_scale_xyz(obj, hw / PHX, 1, hl / PHZ)
    end)
    if model ~= nil then
        rec.vis = spawn_non_sync_object(id_bhvSglLakeProp, model, x, top - (visDrop or 0), z, function(obj)
            obj.oFaceAngleYaw = yaw
            obj_scale(obj, modelScale or 1)
        end)
    end
    return rec
end

-- cosmetic bats (act 3): the swoop model on a fixed flight from a barn's open bottom toward a census post,
-- computed from the object's own timer and its home / heading / speed (oForwardVel) / climb (oVelY) / life
-- (oHealth, frames) (no sync, no interaction)
local BAT_LIFE = 210          -- frames (7 s): a bat spawned without a life of its own
local BAT_SPEED = 18          -- units per frame (5.4 m/s): the slowest bat
local BAT_CLIMB = 3           -- units per frame after the first half second

local function bat_init(o)
    o.oFlags = OBJ_FLAG_UPDATE_GFX_POS_AND_ANGLE | OBJ_FLAG_ACTIVE_FROM_AFAR
    o.oDrawingDistance = 20000
    o.oIntangibleTimer = -1
    animate(o, gObjectAnimations.swoop_seg6_anims_060070D0, 0)     -- 0 = flying
end

-- position of a bat t frames after leaving its barn (pure: tools/luatest checks the flight); speed and climb
-- in units per frame (default BAT_SPEED / BAT_CLIMB)
function sgl_lake_bat_pos(hx, hy, hz, yaw, seed, t, speed, climb)
    local s, c = sins(yaw), coss(yaw)
    local fwd = (speed or BAT_SPEED) * t
    local side = 160 * math.sin(t * 0.21 + seed)
    local y = hy - 90 * math.min(1, t / 15) + (climb or BAT_CLIMB) * math.max(0, t - 15) + 60 * math.sin(t * 0.33 + seed * 2)
    return hx + s * fwd + c * side, y, hz + c * fwd - s * side
end

-- the flight of a bat from a barn exit `e` over the census post `p` (both {x, y, z}): it passes 5 m over the
-- post, at a speed that gets it there in 4 s (BAT_SPEED to 60 units a frame, 5.4 to 18 m/s: the Boardwalk post,
-- ~100 m from the barns, takes 6-7 s) and flies on for 2 s
-- -> yaw (straight at the post), speed, climb, life (frames). Pure (tools/luatest checks it).
function sgl_lake_bat_flight(e, p)
    local dx, dz = p.x - e.x, p.z - e.z
    local d = math.sqrt(dx * dx + dz * dz)
    local speed = clamp(d / 120, BAT_SPEED, 60)
    local tPost = d / speed
    local climb = (p.y + 500 - e.y + 90) / math.max(15, tPost - 15)
    return atan2s(dz, dx), speed, climb, math.min(330, math.floor(tPost) + 60)
end

local function bat_loop(o)
    local t = o.oTimer
    local life = (o.oHealth or 0) > 0 and o.oHealth or BAT_LIFE
    if t >= life then
        obj_mark_for_deletion(o)
        return
    end
    local seed = o.oBehParams2ndByte / 40
    local speed = (o.oForwardVel or 0) > 0 and o.oForwardVel or BAT_SPEED
    o.oPosX, o.oPosY, o.oPosZ = sgl_lake_bat_pos(o.oHomeX, o.oHomeY, o.oHomeZ, o.oMoveAngleYaw, seed, t, speed,
        o.oVelY or BAT_CLIMB)
    o.oFaceAngleYaw = (o.oMoveAngleYaw + math.floor(0x1800 * math.cos(t * 0.21 + seed))) & 0xFFFF
    o.oFaceAnglePitch = 0
end

id_bhvSglLakeBat = hook_behavior(nil, OBJ_LIST_DEFAULT, true, bat_init, bat_loop, "bhvSglLakeBat")

---------------------------------------------------------------------------------------------
-- Gator numbers (acts 1 and 2). Basking gator k (1-based, act 2) at network area time t: phase u = (t - k * WAVE)
-- mod CYCLE: up (UP frames, the last WOBBLE of them shaking), sinking (SINK), under (UNDER: its back SINK_DEPTH
-- under the surface, or BED_CLEAR over the highest bed under it in shallow water), rising (RISE).
-- Big gators (acts 1 and 2; local hazards, one copy per client chasing only its own player): patrol a circle
-- (PATROL) round their home on the area timer; a player in the water within LUNGE of the home is chased
-- (CHASE: faster than Mario swims) and snapped at: a wedge of damage (BITE_HURT) and a knock-back away from
-- the gator, then COOL frames of rest. Act 1 overrides LUNGE / PATROL (its spec.lurk).
---------------------------------------------------------------------------------------------
SGL_LAKE_GATOR = {
    CYCLE = 150, UP = 84, SINK = 18, UNDER = 30, RISE = 18, WAVE = 27, WOBBLE = 20,
    SURF_LIFT = 12,           -- an up gator's back is 0.12 m over the water
    SINK_DEPTH = 160,         -- an under gator's back is 1.6 m under it (Mario swims below 1 m)
    BED_CLEAR = 70,           -- ... or 0.7 m over the highest lake bed under it (its underside stays clear)
    STEP = 20,                -- at most this many units per frame toward the timer's height (timer jumps)
    HW = 80, HL = 220,        -- half width / half length of a gator's back (1.6 x 4.4 m)
    LUNGE = 1800, CHASE = 22, RETURN = 14, PATROL = 500, BITE_R = 180, COOL = 60, BITE_HURT = 4,
}
local G = SGL_LAKE_GATOR
local BIG_Y = WATER_Y - 40    -- a patrolling big gator's origin: its back just breaks the surface

-- not mid-hit, not invincible, not in a cutscene (a star dance in the water) or intangible
local function biteable(m)
    return alive(m) and m.invincTimer == 0 and not sgl_lake_knocked_back(m.action)
        and (m.action & ACT_GROUP_MASK) ~= ACT_GROUP_CUTSCENE and (m.action & ACT_FLAG_INTANGIBLE) == 0
end

-- the big gators of one act: opts = { homes = { {x, z, bed}, ... }, model, scale, lunge, patrol, toast }
-- -> { spawn(ctx) (into ctx.objs.big), tick(ctx, m, t), biteable(m), lunge, patrol }
local function big_gators(opts)
    local B = { lunge = opts.lunge or G.LUNGE, patrol = opts.patrol or G.PATROL, biteable = biteable }
    local LUNGE, PATROL = B.lunge, B.patrol

    B.spawn = function(ctx)
        ctx.objs.big = {}
        local anims = gObjectAnimations.sushi_seg5_anims_0500AE54
        for i, b in ipairs(opts.homes or {}) do
            local o = spawn_non_sync_object(id_bhvSglLakeProp, opts.model or E_MODEL_SUSHI, b.x, BIG_Y, b.z, function(obj)
                obj_scale(obj, opts.scale or 1)
            end)
            animate(o, anims, 0)
            ctx.objs.big[i] = { o = o, home = b, x = b.x, y = BIG_Y, z = b.z, yaw = 0, cool = 0, chase = false }
        end
    end

    -- a big gator snaps at the local player (in the water): a wedge, knocked back away from it
    local function bite(ctx, m, bg)
        local swim = (m.action & ACT_FLAG_SWIMMING) ~= 0
        m.faceAngle.y = atan2s(bg.z - m.pos.z, bg.x - m.pos.x)
        hurt_and_set_mario_action(m, swim and ACT_BACKWARD_WATER_KB or ACT_BACKWARD_AIR_KB, 1, G.BITE_HURT)
        m.forwardVel = swim and -24 or -16
        bg.cool = G.COOL
        play_sound(SOUND_OBJ_BUBBA_CHOMP, gGlobalSoundSource)
        sgl_hud_toast(opts.toast or "CHOMP! A big gator!", 3, SGL_HUD_RED)
        ctx.loc.bites = (ctx.loc.bites or 0) + 1
        ctx.loc.expandUntil = ctx.age + 150
    end

    B.tick = function(ctx, m, t)
        local inWater = alive(m) and m.pos.y < IN_WATER_Y
        for i, bg in ipairs(ctx.objs.big or {}) do
            local h = bg.home
            local ang = t * 0.012 + i * 2.1
            local px, pz = h.x + math.sin(ang) * PATROL, h.z + math.cos(ang) * PATROL
            local near = inWater and dist2_xz(m.pos, h) <= LUNGE * LUNGE
            bg.chase = near and bg.cool == 0
            if bg.cool > 0 then bg.cool = bg.cool - 1 end
            local tx, tz, speed = px, pz, G.RETURN
            if bg.chase then tx, tz, speed = m.pos.x, m.pos.z, G.CHASE end
            local dx, dz = tx - bg.x, tz - bg.z
            local d = math.sqrt(dx * dx + dz * dz)
            if d > 1 then
                local step = math.min(d, speed)
                bg.x, bg.z = bg.x + dx / d * step, bg.z + dz / d * step
                bg.yaw = atan2s(dz, dx)
            end
            local ty = BIG_Y
            if bg.chase then ty = clamp(m.pos.y + 40, h.bed + 60, BIG_Y) end
            bg.y = bg.y + clamp(ty - bg.y, -10, 10)
            if bg.chase and biteable(m) and dist2_xz(m.pos, bg) <= G.BITE_R * G.BITE_R
                and math.abs(bg.y - (m.pos.y + 60)) <= 200 then
                bite(ctx, m, bg)
            end
            if obj_ok(bg.o, id_bhvSglLakeProp) then
                bg.o.oPosX, bg.o.oPosY, bg.o.oPosZ = bg.x, bg.y, bg.z
                bg.o.oFaceAngleYaw = bg.yaw
            end
        end
    end
    return B
end

---------------------------------------------------------------------------------------------
-- HOP kind (act 1): spec = { boardwalk = {x,y,z}, bog = {x,y,z}, pads = { {x,y,z,r}, ... } (route order, y = top),
-- goal = {x,y,z} (the deck floor), goalRadius, boardwalkRadius, bogRadius, skeeters = { {x,y,z}, ... },
-- lurk = big_gators options (gators lurking in the open water beside the middle of the pad line: the lily
-- pads are the safe way across, a swimmer gets bitten) }
-- Progress index: 1 = the boardwalk, 2 = the west bog, 2 + k = lily pad k, 3 + #pads = the deck (the goal).
-- Leader (synced positions, like the reach kind): p = the team's best index, f = milestone bits (1 boardwalk,
-- 2 bog, 4 halfway pad, 8 deck); anyone standing on the deck -> SUCCESS. Standing = feet on it (a swimmer
-- next to a pad or the deck is 0.8 m lower and does not count).
---------------------------------------------------------------------------------------------
local function kind_hop(spec)
    local K = {}
    local pads = spec.pads
    local nPads = #pads
    local LAST = 3 + nPads
    local HALF = 2 + (nPads + 1) // 2
    local BR, GR, DR = spec.boardwalkRadius or 600, spec.bogRadius or 1400, spec.goalRadius or 430
    local MILESTONES = { { bit = 1, at = 1, name = "North boardwalk" }, { bit = 2, at = 2, name = "West bog" },
        { bit = 4, at = HALF, name = "Halfway pad" }, { bit = 8, at = LAST, name = "Observation deck" } }
    K.lastIndex = LAST

    local function on_pad(p, pad)
        local r = pad.r + 30
        return dist2_xz(p, pad) <= r * r and p.y >= pad.y - 40 and p.y <= pad.y + 300
    end
    K.onPad = on_pad

    local function on_goal(p)
        local g = spec.goal
        return dist2_xz(p, g) <= DR * DR and p.y >= g.y - 40 and p.y <= g.y + 420
    end
    K.onGoal = on_goal

    -- the furthest route index at position p (0 = none)
    local function index_at(p)
        if on_goal(p) then return LAST end
        for k = nPads, 1, -1 do
            if on_pad(p, pads[k]) then return 2 + k end
        end
        if dist2_xz(p, spec.bog) <= GR * GR and p.y >= WATER_Y - 30 and p.y <= spec.bog.y + 400 then return 2 end
        local b = spec.boardwalk
        if dist2_xz(p, b) <= BR * BR and p.y >= b.y - 40 and p.y <= b.y + 300 then return 1 end
        return 0
    end
    K.indexAt = index_at

    local function flags_for(i)
        local f = 0
        for _, ms in ipairs(MILESTONES) do
            if i >= ms.at then f = f | ms.bit end
        end
        return f
    end

    K.onReset = function(ctx)
        ctx:set("p", 0)
        ctx:set("f", 0)
    end

    K.leaderTick = function(ctx)
        local best, flags = ctx.p, ctx.f
        for _, li in ipairs(ctx.players) do
            local m = gMarioStates[li]
            if alive(m) then
                local i = index_at(m.pos)
                if i > best then best = i end
                flags = flags | flags_for(i)
            end
        end
        if best ~= ctx.p then ctx:set("p", best) end
        if flags ~= ctx.f then ctx:set("f", flags) end
        if best >= LAST then ctx:succeed() end
    end

    local lurk = spec.lurk and big_gators(spec.lurk) or nil
    K.lurk = lurk

    K.spawnLocal = function(ctx)
        ctx.objs.skeeters = {}
        for _, s in ipairs(spec.skeeters or {}) do
            table.insert(ctx.objs.skeeters, spawn_non_sync_object(id_bhvSkeeter, E_MODEL_SKEETER, s.x, s.y, s.z, nil))
        end
        if lurk ~= nil then lurk.spawn(ctx) end
    end

    K.localTick = function(ctx)
        local L = ctx.loc
        local m = gMarioStates[0]
        if alive(m) then
            local i = index_at(m.pos)
            if i > (L.mine or 0) then L.mine = i end
        end
        if lurk ~= nil and ctx.s ~= SGL_MS_IDLE then lurk.tick(ctx, m, get_network_area_timer()) end
        if L.flags == nil then L.flags = ctx.f end
        if ctx.f ~= L.flags then
            for _, ms in ipairs(MILESTONES) do
                if (ctx.f & ms.bit) ~= 0 and (L.flags & ms.bit) == 0 and ms.at < LAST then
                    sgl_hud_toast(ms.name .. " reached!", 3, SGL_HUD_GREEN)
                    play_sound(SOUND_MENU_COLLECT_SECRET, gGlobalSoundSource)
                    L.expandUntil = ctx.age + 150
                end
            end
            L.flags = ctx.f
        end
    end

    local function pads_of(i) return clamp(i - 2, 0, nPads) end

    K.panel = function(ctx)
        local L = ctx.loc
        local lines = { { string.format("Lily pads: you %d/%d   team best %d/%d", pads_of(L.mine or 0), nPads,
            pads_of(ctx.p), nPads), SGL_HUD_WHITE } }
        for _, ms in ipairs(MILESTONES) do
            local got = (ctx.f & ms.bit) ~= 0
            table.insert(lines, { (got and "+ " or "- ") .. ms.name, got and SGL_HUD_GREEN or SGL_HUD_GREY, 0.28 })
        end
        local m = gMarioStates[0]
        if lurk ~= nil and alive(m) and m.pos.y < IN_WATER_Y then
            table.insert(lines, { "In the water: gators lurk here - get on a pad!", SGL_HUD_RED, 0.28 })
        else
            table.insert(lines, { "Fell in? Swim to a pad and climb on", SGL_HUD_GREY, 0.26 })
        end
        return lines
    end

    -- the marker walks the route: the boardwalk, the bog, then the next lily pad (the following one as a dot)
    K.hud = function(ctx)
        if ctx.s ~= SGL_MS_ACTIVE and ctx.s ~= SGL_MS_INTRO then return end
        local m = gMarioStates[0]
        local mine = ctx.loc.mine or 0
        if mine < 1 then
            sgl_hud_marker(up(spec.boardwalk, 150), "BOARDWALK", SGL_HUD_ORANGE, m)
        elseif mine < 2 then
            sgl_hud_marker(up(spec.bog, 150), "WEST BOG", SGL_HUD_ORANGE, m)
        elseif mine < 2 + nPads then
            local k = mine - 2 + 1
            sgl_hud_marker(up(pads[k], 100), "PAD " .. k, SGL_HUD_ORANGE, m)
            if k < nPads then sgl_hud_marker(up(pads[k + 1], 80), "", SGL_HUD_ORANGE, nil, true) end
        else
            sgl_hud_marker(up(spec.goal, 150), "OBSERVATION DECK", SGL_HUD_GOLD, m)
        end
    end
    return K
end

---------------------------------------------------------------------------------------------
-- GATORS kind (act 2): spec = { gators = { {x, z, yaw, bed}, ... } (hop order), start = {x,y,z} (the deck: D-pad
-- Down), startRadius, firstPad = {x,y,z,r} (the big lily pad between the deck and gator 1), nest = {x,y,z},
-- nestRadius, big = { {x, z, bed}, ... }, model, modelScale, bigScale, visDrop, bigToast }
-- The basking gators follow sgl_lake_gator_top (the wave, SGL_LAKE_GATOR above). Two or more riders on an up
-- gator: it wobbles and sinks at once, and stays down until its own cycle catches up (each client decides from
-- synced positions).
-- Progress (local, per player): standing on gator k counts when k <= progress + 2 (one may be skipped); the
-- leader keeps the team best in p ("hop" events). Standing on the nest island with progress >= N - 1 sends
-- "nest": the leader sets x = 1 and the mission succeeds. Swimming to the nest from the shore does nothing.
-- Big gators (big_gators above): a 5 m patrol, an 18 m lunge round three homes spread along the line.
---------------------------------------------------------------------------------------------

-- a gator's back when it is under: SINK_DEPTH under the water, or BED_CLEAR over the highest bed under it
-- (never above its surfaced height: a gator lying on the bog's skirt stays up)
local function sunk_top(bed)
    return math.min(WATER_Y + G.SURF_LIFT, math.max(WATER_Y - G.SINK_DEPTH, bed + G.BED_CLEAR))
end

-- the deck top of gator k (1-based) over a bed at `bed` at area time t -> top, state ("up", "sinking", "under",
-- "rising"), wobble (true in the last WOBBLE frames before it sinks). Pure: the same on every client.
function sgl_lake_gator_top(bed, k, t)
    local surf = WATER_Y + G.SURF_LIFT
    local sunk = sunk_top(bed)
    local u = (math.floor(t) - k * G.WAVE) % G.CYCLE
    if u < G.UP then return surf, "up", u >= G.UP - G.WOBBLE end
    u = u - G.UP
    if u < G.SINK then return lerp(surf, sunk, u / G.SINK), "sinking", false end
    u = u - G.SINK
    if u < G.UNDER then return sunk, "under", false end
    u = u - G.UNDER
    return lerp(sunk, surf, math.min(1, u / G.RISE)), "rising", false
end

local function kind_gators(spec)
    local K = {}
    local gators = spec.gators
    local N = #gators
    local RESEND = 90

    local function on_gator(p, g, top)
        local dx, dz = p.x - g.x, p.z - g.z
        local s, c = sins(g.yaw), coss(g.yaw)
        local along, across = dx * s + dz * c, dx * c - dz * s
        return math.abs(across) <= G.HW + 40 and math.abs(along) <= G.HL + 40 and p.y >= top - 40 and p.y <= top + 300
    end
    K.onGator = on_gator

    local function on_nest(p)
        local r = spec.nestRadius or 700
        return dist2_xz(p, spec.nest) <= r * r and p.y >= IN_WATER_Y and p.y <= spec.nest.y + 400
    end
    K.onNest = on_nest

    local function on_start(p)
        local r = spec.startRadius or 450
        return dist2_xz(p, spec.start) <= r * r and p.y >= spec.start.y - 40 and p.y <= spec.start.y + 420
    end

    -- on the big lily pad between the deck and gator 1
    local function on_pad(p)
        local pad = spec.firstPad
        if pad == nil then return false end
        local r = pad.r + 30
        return dist2_xz(p, pad) <= r * r and p.y >= pad.y - 40 and p.y <= pad.y + 300
    end

    -- this client's gator records (L.gators[k] = { top, state, wobble, force, riders })
    local function gator_state(ctx)
        local L = ctx.loc
        L.gators = L.gators or {}
        return L.gators
    end

    -- top of gator k now, with the co-op sink (rec.force: frames since two riders stepped on)
    local function gator_now(rec, g, k, t)
        local top, st, wob = sgl_lake_gator_top(g.bed, k, t)
        if rec.force ~= nil then
            if st == "rising" then
                rec.force = nil
            else
                local surf = WATER_Y + G.SURF_LIFT
                local sunk = sunk_top(g.bed)
                local f = rec.force
                local forced = surf
                if f >= G.WOBBLE then forced = lerp(surf, sunk, math.min(1, (f - G.WOBBLE) / G.SINK)) end
                wob = wob or f < G.WOBBLE
                if forced < top then
                    top = forced
                    st = f >= G.WOBBLE + G.SINK and "under" or (f >= G.WOBBLE and "sinking" or "up")
                end
            end
        end
        return top, st, wob
    end
    K.gatorNow = gator_now

    K.onReset = function(ctx)
        ctx:set("p", 0)
        ctx:set("x", 0)
    end

    K.leaderTick = function(ctx)
        if ctx.x > 0 then ctx:succeed() end
    end

    K.onEvent = function(ctx, ev, data)
        if data.r ~= ctx.r or math.type(data.k) ~= "integer" then return end
        if ev == "hop" then
            if data.k >= 1 and data.k <= N and ctx.isLeader and ctx.s == SGL_MS_ACTIVE and data.k > ctx.p then
                ctx:set("p", data.k)
            end
        elseif ev == "nest" then
            if ctx.isLeader and ctx.s == SGL_MS_ACTIVE and ctx.x == 0 then
                ctx:set("p", N)
                ctx:set("x", 1)
                ctx:succeed()
            end
            if data.gi ~= gNetworkPlayers[0].globalIndex and not ctx.loc.nestHeard then
                ctx.loc.nestHeard = true
                sgl_hud_toast((data.nm or "?") .. " reached the gator nest!", 3, SGL_HUD_GREEN)
                play_sound(SOUND_GENERAL2_RIGHT_ANSWER, gGlobalSoundSource)
            end
        end
    end

    local big = big_gators({ homes = spec.big, model = spec.model, scale = spec.bigScale,
        toast = spec.bigToast or "CHOMP! A big gator - get back on the gators!" })
    K.biteable = biteable

    K.spawnLocal = function(ctx)
        ctx.objs.gators = {}
        local anims = gObjectAnimations.sushi_seg5_anims_0500AE54
        local t = get_network_area_timer()
        for k, g in ipairs(gators) do
            local top = sgl_lake_gator_top(g.bed, k, t)
            local rec = spawn_platform(g.x, top, g.z, g.yaw, G.HW, G.HL, nil, spec.model, spec.modelScale, spec.visDrop)
            if rec.vis ~= nil then animate(rec.vis, anims, 0) end
            ctx.objs.gators[k] = rec
        end
        big.spawn(ctx)
    end

    K.localTick = function(ctx)
        local L = ctx.loc
        local m = gMarioStates[0]
        local t = get_network_area_timer()
        local recs = gator_state(ctx)
        L.prog = L.prog or 0
        L.sentAt = L.sentAt or {}
        L.onK = nil
        for k, g in ipairs(gators) do
            local rec = recs[k] or {}
            recs[k] = rec
            -- riders (local view of synced positions) on this gator's current deck
            local riders = 0
            local top0 = rec.top or sgl_lake_gator_top(g.bed, k, t)
            for _, li in ipairs(ctx.players) do
                local mm = gMarioStates[li]
                if alive(mm) and on_gator(mm.pos, g, top0) then riders = riders + 1 end
            end
            rec.riders = riders
            local _, natural = sgl_lake_gator_top(g.bed, k, t)
            if riders >= 2 and rec.force == nil and natural == "up" then
                rec.force = 0
                if alive(m) and on_gator(m.pos, g, top0) then
                    sgl_hud_toast("Too heavy! Two on one gator - it is going under!", 3, SGL_HUD_ORANGE)
                end
            elseif rec.force ~= nil then
                rec.force = rec.force + 1
            end
            local top, st, wob = gator_now(rec, g, k, t)
            rec.top = rec.top == nil and top or rec.top + clamp(top - rec.top, -G.STEP, G.STEP)
            rec.state, rec.wobble = st, wob
            local pr = ctx.objs.gators and ctx.objs.gators[k]
            if pr ~= nil then
                pr.y = rec.top - PTOP
                pr.roll = wob and math.floor(0x500 * math.sin(ctx.age * 1.3)) or 0
            end
            if alive(m) and on_gator(m.pos, g, rec.top) then L.onK = k end
        end
        -- my progress along the line
        local k = L.onK
        if k ~= nil and k > L.prog and k <= L.prog + 2 and ctx.s == SGL_MS_ACTIVE then
            L.prog = k
            L.sentAt[k] = ctx.age
            play_sound(SOUND_MENU_COLLECT_SECRET, gGlobalSoundSource)
            if k == N then sgl_hud_toast("Last gator! Jump onto the nest!", 3, SGL_HUD_GOLD) end
            ctx:send("hop", { k = k })
        end
        if L.prog > ctx.p and L.sentAt[L.prog] ~= nil and ctx.age - L.sentAt[L.prog] >= RESEND and ctx.s == SGL_MS_ACTIVE then
            L.sentAt[L.prog] = ctx.age
            ctx:send("hop", { k = L.prog })
        end
        -- the nest
        if alive(m) and on_nest(m.pos) and ctx.s == SGL_MS_ACTIVE then
            if L.prog >= N - 1 then
                if L.nestAt == nil or (ctx.x == 0 and ctx.age - L.nestAt >= RESEND) then
                    L.nestAt = ctx.age
                    ctx:send("nest", { k = N, nm = gNetworkPlayers[0].name })
                end
            elseif not L.nestHint then
                L.nestHint = true
                sgl_hud_toast("The gators get angry: hop ALL the gators from the lake deck!", 4, SGL_HUD_ORANGE)
            end
        end
        if L.onK ~= nil and (recs[L.onK].wobble or recs[L.onK].state == "sinking") then
            if not L.warned then
                L.warned = true
                play_sound(SOUND_GENERAL_QUIET_BUBBLE, gGlobalSoundSource)
            end
        else
            L.warned = false
        end
        if ctx.s ~= SGL_MS_IDLE then big.tick(ctx, m, t) end
    end

    K.panel = function(ctx)
        local L = ctx.loc
        local lines = { { string.format("Gators: you %d/%d   team best %d/%d", L.prog or 0, N, ctx.p, N), SGL_HUD_WHITE } }
        local m = gMarioStates[0]
        if L.onK ~= nil then
            local rec = (L.gators or {})[L.onK]
            if rec ~= nil and (rec.wobble or rec.state == "sinking") then
                table.insert(lines, { "Your gator is going under - hop!", SGL_HUD_ORANGE, 0.3 })
            elseif rec ~= nil and rec.riders >= 2 then
                table.insert(lines, { "Two on one gator: it sinks - spread out!", SGL_HUD_ORANGE, 0.28 })
            else
                table.insert(lines, { string.format("On gator %d", L.onK), SGL_HUD_GREEN, 0.28 })
            end
        elseif alive(m) and m.pos.y < IN_WATER_Y then
            table.insert(lines, { "In the water: big gators bite!", SGL_HUD_RED, 0.3 })
        end
        if (L.prog or 0) == 0 and not on_start(m.pos) then
            table.insert(lines, { "D-pad Down: to the lake deck (the start)", SGL_HUD_GREY, 0.26 })
        else
            table.insert(lines, { "Hop them in order; they sink in a wave", SGL_HUD_GREY, 0.26 })
        end
        return lines
    end

    K.hud = function(ctx)
        if ctx.s ~= SGL_MS_ACTIVE and ctx.s ~= SGL_MS_INTRO then return end
        local L = ctx.loc
        local m = gMarioStates[0]
        local prog = L.prog or 0
        local recs = L.gators or {}
        if prog == 0 and L.onK == nil and not on_start(m.pos) and not on_pad(m.pos) then
            sgl_hud_marker(up(spec.start, 150), "START: LAKE DECK", SGL_HUD_ORANGE, m)
            return
        end
        if prog >= N - 1 then
            sgl_hud_marker(up(spec.nest, 150), "NEST", SGL_HUD_GOLD, m)
        end
        local k = math.min(N, prog + 1)
        if prog < N then
            local g = gators[k]
            local rec = recs[k]
            local top = rec and rec.top or WATER_Y
            local col = (rec and (rec.state == "up" and not rec.wobble)) and SGL_HUD_GREEN or SGL_HUD_ORANGE
            sgl_hud_marker({ x = g.x, y = top + 80, z = g.z }, "GATOR " .. k, col, m)
        end
    end

    -- D-pad Down / /mission start: onto the observation deck (the end pad next to it is the first hop)
    K.toStart = function(ctx, m)
        if not can_teleport(m) or ctx.s == SGL_MS_WAITING then return false end
        if on_start(m.pos) then return false end
        local g1 = gators[1]
        teleport(m, spec.start, atan2s(g1.z - spec.start.z, g1.x - spec.start.x), "Start: the lake-centre deck")
        return true
    end
    return K
end

---------------------------------------------------------------------------------------------
-- CENSUS kind (act 3, co-op): spec = { stations = { {x, y, z, name}, ... }, radius, height, duration (s),
-- countdown (s), gatherMax (s), base, extra, maxExtra (bats per second), target0, targetPer, maxPlayers,
-- exits = { {x,y,z}, ... } (the barns' open bottoms), batEvery (frames), batMax, spread (bats' yaw spread round
-- the line to the post, +-), attackers (true: vanilla Swoopers dive at the local counter), swoopFirst, swoopEvery,
-- swoopLife (frames), swoopLeash (units from its post), music (SEQ_*) }
-- Fields: a = bats to count (600 + 300 per player past the first, players clamped to 2..maxPlayers; it only
-- drops once the count runs), x = phase (0 take your posts, 1 countdown, 2 counting, 3 complete),
-- c = seconds in the phase, g = countdown seconds left, p = bats counted, f = posts: bit i-1 = post i staffed,
-- bits 3 + 2(i-1) = its counters (0..3). The leader samples the posts at 2 Hz: a post with one counter adds
-- base bats per second, each extra counter `extra` more (up to maxExtra extra counters). A counter must stand on
-- the post and not be in a knock-back. Two posts staffed (or one after gatherMax s) start the countdown.
-- Count >= a -> SUCCESS; duration s without it -> FAILED (a new round after 4 s).
---------------------------------------------------------------------------------------------
SGL_LAKE_CENSUS_GATHER, SGL_LAKE_CENSUS_COUNTDOWN, SGL_LAKE_CENSUS_COUNTING, SGL_LAKE_CENSUS_COMPLETE = 0, 1, 2, 3
SGL_LAKE_CENSUS_FAIL_SHORT = 1

local function kind_census(spec)
    local K = { minPlayers = 2, spec = spec }
    local st = spec.stations
    local nSt = #st
    local R, H = spec.radius or 260, spec.height or 400
    local DUR = spec.duration or 90

    local function target_for(n)
        return spec.target0 + spec.targetPer * (clamp(n, K.minPlayers, spec.maxPlayers) - 1)
    end
    K.targetFor = target_for

    -- bats per second for counters = { n1, n2, n3 } (players on each post)
    local function rate_for(counts)
        local r = 0
        for i = 1, nSt do
            local n = counts[i] or 0
            if n >= 1 then r = r + spec.base + spec.extra * math.min(n - 1, spec.maxExtra) end
        end
        return r
    end
    K.rateFor = rate_for

    local function on_station(p, s)
        return dist2_xz(p, s) <= R * R and p.y >= s.y - 60 and p.y <= s.y + H
    end
    K.onStation = on_station

    local function counting(m, s)
        return alive(m) and on_station(m.pos, s) and not sgl_lake_knocked_back(m.action)
    end

    local function pack(counts)
        local f = 0
        for i = 1, nSt do
            local n = math.min(counts[i] or 0, 3)
            if n > 0 then f = f | (1 << (i - 1)) end
            f = f | (n << (3 + 2 * (i - 1)))
        end
        return f
    end
    local function counters_of(f, i) return (f >> (3 + 2 * (i - 1))) & 3 end
    K.countersOf = counters_of

    local function station_counts(ctx)
        local counts = {}
        for i, s in ipairs(st) do
            local n = 0
            for _, li in ipairs(ctx.players) do
                if counting(gMarioStates[li], s) then n = n + 1 end
            end
            counts[i] = n
        end
        return counts
    end

    K.needPlayers = function(ctx) return K.minPlayers end

    K.onReset = function(ctx)
        ctx:set("a", target_for(ctx.n))
        ctx:set("x", SGL_LAKE_CENSUS_GATHER)
        ctx:set("c", 0)
        ctx:set("g", 0)
        ctx:set("p", 0)
        ctx:set("f", 0)
    end

    K.leaderTick = function(ctx)
        local lead = ctx.lead
        local want = target_for(ctx.n)
        if ctx.x <= SGL_LAKE_CENSUS_COUNTDOWN then
            if want ~= ctx.a then ctx:set("a", want) end
        elseif want < ctx.a and ctx.x == SGL_LAKE_CENSUS_COUNTING then
            ctx:set("a", want)       -- someone left during the count: the target drops with them
        end
        local counts = station_counts(ctx)
        local f = pack(counts)
        if f ~= ctx.f then ctx:set("f", f) end
        local staffed = popcount(f & 7)
        if ctx.x == SGL_LAKE_CENSUS_GATHER then
            if ctx.second then ctx:set("c", ctx.c + 1) end
            if staffed >= 2 or (staffed >= 1 and ctx.c >= spec.gatherMax) then
                lead.cd = 0
                ctx:set("g", spec.countdown)
                ctx:set("c", 0)
                ctx:set("x", SGL_LAKE_CENSUS_COUNTDOWN)
            end
        elseif ctx.x == SGL_LAKE_CENSUS_COUNTDOWN then
            lead.cd = (lead.cd or (spec.countdown - math.max(ctx.g, 1)) * 30) + 1
            local left = spec.countdown - lead.cd // 30
            if left <= 0 then
                lead.cd, lead.acc, lead.samp = nil, 0, 0
                ctx:set("p", 0)
                ctx:set("c", 0)
                ctx:set("g", 0)
                ctx:set("x", SGL_LAKE_CENSUS_COUNTING)
            elseif left ~= ctx.g then
                ctx:set("g", left)
            end
        elseif ctx.x == SGL_LAKE_CENSUS_COUNTING then
            lead.samp = (lead.samp or 0) + 1
            if lead.acc == nil then lead.acc = ctx.p end   -- a new leader carries on from the synced count
            if lead.samp >= 15 then                        -- 2 Hz
                lead.samp = 0
                lead.acc = lead.acc + rate_for(counts) / 2
                local v = math.floor(lead.acc)
                if v ~= ctx.p then ctx:set("p", v) end
            end
            if ctx.second then ctx:set("c", ctx.c + 1) end
            if ctx.p >= ctx.a then
                ctx:set("x", SGL_LAKE_CENSUS_COMPLETE)
                ctx:succeed()
            elseif ctx.c >= DUR then
                ctx:fail(SGL_LAKE_CENSUS_FAIL_SHORT)
            end
        end
    end

    -- local visuals: a purple-switch post + flame per station (red: empty, blue: counting), the bat swarm,
    -- the diving Swoopers, the emergence music
    K.spawnLocal = function(ctx)
        ctx.objs.posts, ctx.objs.bats, ctx.objs.swoops = {}, {}, {}
        for i, s in ipairs(st) do
            local o = spawn_non_sync_object(id_bhvSglButton, E_MODEL_PURPLE_SWITCH, s.x, s.y, s.z, nil)
            local fx = spawn_non_sync_object(id_bhvSglMissionFx, E_MODEL_RED_FLAME, s.x, s.y + 250, s.z,
                function(obj) obj_scale(obj, 4) end)
            ctx.objs.posts[i] = { o = o, fx = fx, squish = SGL_BUTTON_SCALE }
        end
        ctx.objs.musicOn = false      -- per visit, not per round: a /mission reset mid-count still stops it
    end

    local function set_music(ctx, on)
        local V = ctx.objs
        if spec.music == nil or (V.musicOn == true) == on then return end
        V.musicOn = on
        local seq = (SGL_RACE_MUSIC_PRIORITY << 8) | spec.music
        if on then play_music(SEQ_PLAYER_LEVEL, seq, 0) else stop_background_music(seq) end
    end

    local function prune(list, id)
        for i = #list, 1, -1 do
            if not obj_ok(list[i], id) then table.remove(list, i) end
        end
    end

    -- the post my bats fly over: mine while I count, else the one nearest to me (each client's swarm is its
    -- own, so every counter sees the bats pass over their post)
    local function aim_post(ctx)
        local L = ctx.loc
        if L.station ~= nil then return L.station end
        local m = gMarioStates[0]
        local best, bestD = 1, nil
        for i, s in ipairs(st) do
            local d = dist2_xz(m.pos, s)
            if bestD == nil or d < bestD then best, bestD = i, d end
        end
        return best
    end
    K.aimPost = aim_post

    local function spawn_bat(ctx)
        local L = ctx.loc
        L.batN = (L.batN or 0) + 1
        local e = spec.exits[(L.batN % #spec.exits) + 1]
        local seedByte = (L.batN * 37) % 250
        local yaw, speed, climb, life = sgl_lake_bat_flight(e, st[aim_post(ctx)])
        yaw = (yaw + ((L.batN * 2654) % (2 * spec.spread)) - spec.spread) & 0xFFFF
        local o = spawn_non_sync_object(id_bhvSglLakeBat, E_MODEL_SWOOP, e.x, e.y, e.z, function(obj)
            obj.oHomeX, obj.oHomeY, obj.oHomeZ = e.x, e.y, e.z
            obj.oMoveAngleYaw = yaw
            obj.oBehParams2ndByte = seedByte
            obj.oForwardVel, obj.oVelY, obj.oHealth = speed, climb, life
            obj_scale(obj, spec.batScale or 0.5)
        end)
        table.insert(ctx.objs.bats, o)
    end

    -- a Swooper diving at me (vanilla bhvSwoop, local): spawned 7 m from my post and 6.5 m up. A Swooper only
    -- re-aims while it drops, then flies on level for good and never resets while I stay near (swoop.inc.c,
    -- cur_obj_mario_far_away), so each one is taken away (a puff of mist) swoopLife frames after it came or once
    -- it is swoopLeash from its post: the next one can come. Its hit is a knock-back only (damage 0, design 7.4:
    -- "a hit knocks you off your station"): a long count never costs a life.
    local function spawn_swoop(ctx, i)
        local s = st[i]
        local gi = gNetworkPlayers[0].globalIndex
        local a = ((ctx.age // 30) * 97 + gi * 53) % 360 * math.pi / 180
        local o = spawn_non_sync_object(id_bhvSwoop, E_MODEL_SWOOP, s.x + math.sin(a) * 700, s.y + 650,
            s.z + math.cos(a) * 700, nil)
        table.insert(ctx.objs.swoops, { o = o, born = ctx.age, post = i })
    end

    local function clear_swoops(ctx)
        for i = #ctx.objs.swoops, 1, -1 do
            local o = ctx.objs.swoops[i].o
            if o ~= nil and o.activeFlags ~= ACTIVE_FLAG_DEACTIVATED then obj_mark_for_deletion(o) end
            table.remove(ctx.objs.swoops, i)
        end
    end

    -- every frame, after the Swoopers' own update (OBJ_LIST_GENACTOR runs before this controller's
    -- OBJ_LIST_DEFAULT): no damage, and gone after their pass
    local function tend_swoops(ctx)
        local list = ctx.objs.swoops
        local leash = spec.swoopLeash or 1500
        for i = #list, 1, -1 do
            local r = list[i]
            local o = r.o
            if not obj_ok(o, id_bhvSwoop) then
                table.remove(list, i)
            else
                o.oDamageOrCoinValue = 0
                local age = ctx.age - r.born
                local s = st[r.post]
                local dx, dz = o.oPosX - s.x, o.oPosZ - s.z
                if age >= (spec.swoopLife or 240) or (age > 60 and dx * dx + dz * dz > leash * leash) then
                    spawn_non_sync_object(id_bhvMistParticleSpawner, E_MODEL_MIST, o.oPosX, o.oPosY, o.oPosZ, nil)
                    obj_mark_for_deletion(o)
                    table.remove(list, i)
                end
            end
        end
    end

    K.localTick = function(ctx)
        local L = ctx.loc
        local m = gMarioStates[0]
        local live = ctx.s == SGL_MS_ACTIVE or ctx.s == SGL_MS_SUCCESS or ctx.s == SGL_MS_DONE
        local x = live and ctx.x or -1
        -- my post
        local mine = nil
        for i, s in ipairs(st) do
            if counting(m, s) then mine = i end
        end
        if L.station ~= nil and mine == nil and x == SGL_LAKE_CENSUS_COUNTING and alive(m) and sgl_lake_knocked_back(m.action) then
            sgl_hud_toast("Knocked off your post! Get back on to count", 3, SGL_HUD_RED)
            play_sound(SOUND_MENU_CAMERA_BUZZ, gGlobalSoundSource)
            L.expandUntil = ctx.age + 150
        end
        if mine ~= nil and mine ~= L.station then play_sound(SOUND_GENERAL2_PURPLE_SWITCH, gGlobalSoundSource) end
        L.station = mine
        -- countdown ticks, the start, milestones
        if x == SGL_LAKE_CENSUS_COUNTDOWN and ctx.g ~= L.lastG then
            if ctx.g > 0 then play_sound(SOUND_MENU_CHANGE_SELECT, gGlobalSoundSource) end
        end
        L.lastG = ctx.g
        if x == SGL_LAKE_CENSUS_COUNTING and L.lastX ~= SGL_LAKE_CENSUS_COUNTING then
            L.goAge = 0
            L.quarter = 0
            L.tally = {}
            for i = 1, nSt do L.tally[i] = 0 end
            play_sound(SOUND_OBJ2_SWOOP, gGlobalSoundSource)
        end
        L.lastX = x
        if L.goAge ~= nil then L.goAge = L.goAge + 1 end
        -- each post's share of the count (local estimate from the synced counters, at the leader's 2 Hz)
        if x == SGL_LAKE_CENSUS_COUNTING and L.tally ~= nil and L.goAge % 15 == 0 then
            for i = 1, nSt do
                local n = counters_of(ctx.f, i)
                if n >= 1 then L.tally[i] = L.tally[i] + (spec.base + spec.extra * math.min(n - 1, spec.maxExtra)) / 2 end
            end
        end
        if x == SGL_LAKE_CENSUS_COUNTING and ctx.a > 0 then
            local q = math.min(3, (ctx.p * 4) // ctx.a)
            if q > (L.quarter or 0) then
                L.quarter = q
                sgl_hud_toast(string.format("Census: %d / %d bats", ctx.p, ctx.a), 3, SGL_HUD_GOLD)
                L.expandUntil = ctx.age + 150
            end
        end
        -- posts
        for i, rec in ipairs(ctx.objs.posts or {}) do
            local held = counters_of(ctx.f, i) > 0
            local inUse = live and x ~= SGL_LAKE_CENSUS_COMPLETE
            if obj_ok(rec.o, id_bhvSglButton) then
                local target = (held and inUse) and SGL_BUTTON_PRESSED_Y or SGL_BUTTON_SCALE
                rec.squish = rec.squish + (target - rec.squish) * 0.35
                obj_scale_xyz(rec.o, SGL_BUTTON_SCALE, rec.squish, SGL_BUTTON_SCALE)
            end
            if obj_ok(rec.fx, id_bhvSglMissionFx) then
                local want = held and E_MODEL_BLUE_FLAME or E_MODEL_RED_FLAME
                if rec.model ~= want then
                    obj_set_model_extended(rec.fx, want)
                    rec.model = want
                end
                set_hidden(rec.fx, not inUse)
            end
        end
        -- the swarm (cosmetic), and the Swoopers diving at me while I count
        prune(ctx.objs.bats, id_bhvSglLakeBat)
        tend_swoops(ctx)
        local swarm = x == SGL_LAKE_CENSUS_COUNTING or (x == SGL_LAKE_CENSUS_COMPLETE and ctx.stateAge < 300)
        if swarm and ctx.age % spec.batEvery == 0 and #ctx.objs.bats < spec.batMax then spawn_bat(ctx) end
        if x == SGL_LAKE_CENSUS_COUNTING and spec.attackers and mine ~= nil then
            L.swoopIn = (L.swoopIn or spec.swoopFirst) - 1
            if L.swoopIn <= 0 then
                L.swoopIn = spec.swoopEvery
                if #ctx.objs.swoops < 2 then spawn_swoop(ctx, mine) end
            end
        elseif x ~= SGL_LAKE_CENSUS_COUNTING and #ctx.objs.swoops > 0 then
            clear_swoops(ctx)
            L.swoopIn = nil
        end
        set_music(ctx, x == SGL_LAKE_CENSUS_COUNTING)
    end

    local function free_station(ctx, from)
        local best, bestD = nil, nil
        for i, s in ipairs(st) do
            if counters_of(ctx.f, i) == 0 then
                local d = dist2_xz(from, s)
                if bestD == nil or d < bestD then best, bestD = i, d end
            end
        end
        return best
    end
    K.freeStation = free_station

    K.panel = function(ctx)
        local L = ctx.loc
        local lines = {}
        local x = ctx.x
        if x == SGL_LAKE_CENSUS_GATHER then
            table.insert(lines, { string.format("Bats to count: %d - staff 2+ census posts!", ctx.a), SGL_HUD_WHITE })
        elseif x == SGL_LAKE_CENSUS_COUNTDOWN then
            table.insert(lines, { "The bats come out in " .. ctx.g .. "...", SGL_HUD_ORANGE })
        elseif x == SGL_LAKE_CENSUS_COUNTING then
            table.insert(lines, { string.format("Bats counted: %d / %d   %d s left", ctx.p, ctx.a, math.max(0, DUR - ctx.c)),
                ctx.p >= ctx.a and SGL_HUD_GREEN or SGL_HUD_WHITE })
        else
            table.insert(lines, { string.format("Census complete: %d bats!", ctx.p), SGL_HUD_GREEN })
        end
        for i, s in ipairs(st) do
            local n = counters_of(ctx.f, i)
            local text = "  " .. s.name .. (n > 0 and (" - counting" .. (n > 1 and (" x" .. n) or "")) or " - empty")
            local share = L.tally ~= nil and x >= SGL_LAKE_CENSUS_COUNTING and math.floor(L.tally[i] or 0) or 0
            if share > 0 then text = text .. string.format("   +%d", share) end
            table.insert(lines, { text, n > 0 and SGL_HUD_GREEN or SGL_HUD_RED, 0.28 })
        end
        if L.station ~= nil then
            table.insert(lines, { "You count at the " .. st[L.station].name .. " post", SGL_HUD_GOLD, 0.28 })
        else
            table.insert(lines, { "Stand on a census post (D-pad Down: a free one)", SGL_HUD_GREY, 0.26 })
        end
        return lines
    end

    K.hud = function(ctx)
        if ctx.s ~= SGL_MS_ACTIVE then return end
        local L = ctx.loc
        local m = gMarioStates[0]
        if ctx.x == SGL_LAKE_CENSUS_COUNTDOWN and ctx.g > 0 then
            sgl_hud_big(tostring(ctx.g), SGL_HUD_GOLD, 3)
        elseif ctx.x == SGL_LAKE_CENSUS_COUNTING and L.goAge ~= nil and L.goAge < 45 then
            sgl_hud_big("BATS OUT!", SGL_HUD_ORANGE, 2.2)
        end
        if ctx.x <= SGL_LAKE_CENSUS_COUNTING then
            for i, s in ipairs(st) do
                if counters_of(ctx.f, i) == 0 and L.station ~= i then
                    sgl_hud_marker(up(s, 220), "POST: " .. s.name:upper(), SGL_HUD_RED, m)
                end
            end
        end
    end

    -- D-pad Down / /mission start: onto the nearest census post nobody is counting at
    K.toStart = function(ctx, m)
        if not can_teleport(m) or sgl_lake_knocked_back(m.action) or ctx.x == SGL_LAKE_CENSUS_COMPLETE then return false end
        if ctx.loc.station ~= nil then
            sgl_hud_toast("You are on a census post", 2, SGL_HUD_WHITE)
            return false
        end
        local i = free_station(ctx, m.pos)
        if i == nil then
            local bestD = nil
            for j, s in ipairs(st) do
                local d = dist2_xz(m.pos, s)
                if bestD == nil or d < bestD then i, bestD = j, d end
            end
        end
        local s = st[i]
        teleport(m, s, atan2s(spec.lake.z - s.z, spec.lake.x - s.x), "Census post: " .. s.name)
        return true
    end

    K.onLeave = function(ctx)
        set_music(ctx, false)
    end
    return K
end

---------------------------------------------------------------------------------------------
-- REGATTA kind (act 4, design 7.4 act 3 "Shell Surf Regatta"): the framework's race (sgl_mission_kind_race: start
-- box, lobby wait, countdown, ordered checkpoints, par, results board, personal best) ridden on the ride gators
-- (bhvKoopaShell, drawn as a saddled gator: sgl_ride_gator.lua). spec = the race spec (start = the dock,
-- checkpoints = the buoys) plus gators = { { x, y, z, face = {x, z}, name }, ... } (where a ride gator waits: the dock
-- first, then the spare on the safe shoreline), buoyModel, buoyScale, flameUp, flameScale.
-- * Racers: only a player who RIDES a gator in the start box counts for the start (spec.mounted), is held during
--   the countdown and races. The buoys are tall, wide checkpoints in order (cpRadius, cpBelow, cpAbove); the timer
--   stops at the 8th; the star waits at the dock (the race kind: the first finish under par).
-- * Gators are local objects (spawn_non_sync_object of bhvKoopaShell: coopdx's shell skips sync_object_init on a
--   non-sync object, and only the local player interacts with a shell), one waiting at every gator spot on every
--   client, so each friend rides their own. Ridden away (GATOR_TAKEN from its spot) or gone (a ride ends with the
--   vanilla shell vanishing in a puff), a fresh one waits there again GATOR_RESPAWN frames later.
-- * A friend's gator is their own local object: each client draws a stand-in gator under every other player in
--   the act who rides one (ACT_FLAG_RIDING_SHELL with no riddenObj on this client).
-- * Buoys: a local prop on the water at every checkpoint with a flame over it: red, my next one blue, the ones I
--   passed this race put out.
-- * D-pad Down / /mission start (not while racing): off the gator (mario_stop_riding_object) and into the start
--   box beside the dock gator.
---------------------------------------------------------------------------------------------
SGL_LAKE_REGATTA = {
    GATOR_TAKEN = 600,        -- a gator ridden this far from its spot is taken: a fresh one waits there
    GATOR_RESPAWN = 30,       -- frames before a gone gator's spot gets a fresh one
}
local R = SGL_LAKE_REGATTA

function sgl_lake_riding_gator(m)
    return m ~= nil and alive(m) and (m.action & ACT_FLAG_RIDING_SHELL) ~= 0
end

-- a gator spot needs a fresh gator: never spawned (o nil), gone, or taken (moved GATOR_TAKEN away: ridden off, or
-- drifted) -> true. Pure apart from obj_ok (tools/luatest checks it)
local function spot_needs_gator(o, spot)
    if not obj_ok(o, id_bhvKoopaShell) then return true end
    local dx, dz = o.oPosX - spot.x, o.oPosZ - spot.z
    return dx * dx + dz * dz > R.GATOR_TAKEN * R.GATOR_TAKEN
end

local function kind_regatta(spec)
    spec.mounted = sgl_lake_riding_gator
    local K = sgl_mission_kind_race(spec)
    local race = { localTick = K.localTick, panel = K.panel, hud = K.hud, toStart = K.toStart, spawnLocal = K.spawnLocal }
    local cps = spec.checkpoints
    local spots = spec.gators

    local function spawn_gator(spot)
        local yaw = atan2s(spot.face.z - spot.z, spot.face.x - spot.x)
        return spawn_non_sync_object(id_bhvKoopaShell, E_MODEL_KOOPA_SHELL, spot.x, spot.y, spot.z, function(obj)
            obj.oFaceAngleYaw, obj.oMoveAngleYaw = yaw, yaw
        end)
    end

    K.spawnLocal = function(ctx)
        race.spawnLocal(ctx)
        local V = ctx.objs
        V.gators, V.wait, V.buoys, V.ghosts = {}, {}, {}, {}
        for i, b in ipairs(cps) do
            local o = spawn_non_sync_object(id_bhvSglLakeProp, spec.buoyModel or E_MODEL_KOOPA_FLAG, b.x, b.y, b.z, function(obj)
                obj_scale(obj, spec.buoyScale or 1)
            end)
            local fx = spawn_non_sync_object(id_bhvSglMissionFx, E_MODEL_RED_FLAME, b.x, b.y + (spec.flameUp or 500), b.z,
                function(obj) obj_scale(obj, spec.flameScale or 4) end)
            V.buoys[i] = { o = o, fx = fx, model = E_MODEL_RED_FLAME }
        end
    end

    -- every gator spot keeps one waiting gator (on this client)
    local function tend_gators(ctx)
        local V = ctx.objs
        for i, spot in ipairs(spots) do
            local o = V.gators[i]
            if spot_needs_gator(o, spot) then
                if obj_ok(o, id_bhvKoopaShell) and o.oAction == 0 then obj_mark_for_deletion(o) end   -- a drifted one
                V.wait[i] = (V.wait[i] or R.GATOR_RESPAWN) - 1
                if V.wait[i] <= 0 or o == nil then
                    V.gators[i] = spawn_gator(spot)
                    V.wait[i] = nil
                end
            end
        end
    end

    -- stand-in gators under the other riders of this act
    local function tend_ghosts(ctx)
        local V = ctx.objs
        local here = {}
        for _, li in ipairs(ctx.players) do here[li] = true end
        for li = 1, MAX_PLAYERS - 1 do
            local m = gMarioStates[li]
            local show = here[li] == true and sgl_lake_riding_gator(m) and m.riddenObj == nil
            local g = V.ghosts[li]
            if show and not obj_ok(g, id_bhvSglLakeProp) then
                g = spawn_non_sync_object(id_bhvSglLakeProp, E_MODEL_KOOPA_SHELL, m.pos.x, m.pos.y, m.pos.z, function(obj)
                    obj.oGraphYOffset = 10      -- as bhvKoopaShell's
                end)
                V.ghosts[li] = g
            end
            if obj_ok(g, id_bhvSglLakeProp) then
                if show then
                    g.oPosX, g.oPosY, g.oPosZ = m.pos.x, m.pos.y, m.pos.z
                    g.oFaceAngleYaw = m.faceAngle.y
                end
                set_hidden(g, not show)
            end
        end
    end

    -- buoy flames: red; while I race, my next buoy blue and the ones behind me out
    local function tend_buoys(ctx)
        local L = ctx.loc
        for i, rec in ipairs(ctx.objs.buoys or {}) do
            if obj_ok(rec.fx, id_bhvSglMissionFx) then
                local want = (L.racing and i == L.cp) and E_MODEL_BLUE_FLAME or E_MODEL_RED_FLAME
                if rec.model ~= want then
                    obj_set_model_extended(rec.fx, want)
                    rec.model = want
                end
                set_hidden(rec.fx, L.racing == true and i < L.cp)
            end
        end
    end

    K.localTick = function(ctx)
        race.localTick(ctx)
        tend_gators(ctx)
        tend_ghosts(ctx)
        tend_buoys(ctx)
    end

    -- the nearest spot with a waiting gator (for the "lost your gator" marker)
    local function nearest_gator(ctx, p)
        local best, bd = nil, nil
        for i, spot in ipairs(spots) do
            if not spot_needs_gator(ctx.objs.gators and ctx.objs.gators[i], spot) then
                local d = dist2_xz(p, spot)
                if bd == nil or d < bd then best, bd = spot, d end
            end
        end
        return best
    end

    K.panel = function(ctx)
        local lines = race.panel(ctx)
        local m = gMarioStates[0]
        local L = ctx.loc
        if sgl_lake_riding_gator(m) or not alive(m) then return lines end
        if ctx.a == SGL_RACE_LOBBY or ctx.a == SGL_RACE_COUNTDOWN then
            table.insert(lines, 1, { "Jump on a gator at the dock to race!", SGL_HUD_ORANGE })
        elseif L.racing then
            local g = nearest_gator(ctx, m.pos)
            table.insert(lines, 1, { "Lost your gator? " .. (g and ("Get one at " .. g.name) or "Swim back to the dock"), SGL_HUD_RED })
        end
        return lines
    end

    K.hud = function(ctx)
        race.hud(ctx)
        local live = ctx.s == SGL_MS_ACTIVE or ctx.s == SGL_MS_SUCCESS or ctx.s == SGL_MS_DONE
        local m = gMarioStates[0]
        if not live or sgl_lake_riding_gator(m) or not alive(m) then return end
        local L = ctx.loc
        if L.racing or ((ctx.a == SGL_RACE_LOBBY or ctx.a == SGL_RACE_COUNTDOWN) and K.inStartBox(m.pos)) then
            local g = nearest_gator(ctx, m.pos)
            if g ~= nil then sgl_hud_marker(up(g, 200), "GATOR", SGL_HUD_GREEN, m) end
        end
    end

    -- D-pad Down: a rider waiting outside the box gets off the gator first (the race kind teleports nobody riding)
    K.toStart = function(ctx, m)
        if not ctx.loc.racing and m.riddenObj ~= nil and alive(m) and not K.inStartBox(m.pos) then
            mario_stop_riding_object(m)
        end
        return race.toStart(ctx, m)
    end
    K.spotNeedsGator = spot_needs_gator
    return K
end

---------------------------------------------------------------------------------------------
-- dusk (act 3): while the local player is in the bat census act of the BUILT Lake Alice, the lighting is
-- blended from the values it had on arrival (a snapshot: vanilla defaults, or another mod's) to DUSK, then
-- toward NIGHT as the count runs (night once it is complete); leaving the act (warp, exit, another act)
-- restores the snapshot at once. coopdx v1.5.1 globals (gfx_pc.c): set_lighting_color (shaded geometry,
-- also resets the ambient), set_lighting_color_ambient, set_lighting_dir (added to the light direction),
-- set_vertex_color (unlit vertex-coloured geometry), set_fog_color, set_fog_intensity, set_skybox_color.
-- Palette after the bundled Day Night Cycle DX mod's sunset / night constants. With that mod on, its hooks
-- (_G.dayNightCycleApi.dnc_hook_event) are fed the same values, so both mods paint the same dusk.
---------------------------------------------------------------------------------------------
SGL_LAKE_DUSK = {
    dusk = { light = { 255, 150, 100 }, ambient = { 205, 130, 170 }, vertex = { 230, 145, 140 }, fog = { 205, 120, 135 },
        sky = { 255, 150, 140 }, dir = { 0, -0.15, -0.15 }, fogIntensity = 1.0 },
    night = { light = { 95, 105, 160 }, ambient = { 75, 90, 150 }, vertex = { 88, 100, 158 }, fog = { 40, 45, 80 },
        sky = { 70, 80, 140 }, dir = { 0, -0.4, -0.4 }, fogIntensity = 1.02 },
    FADE_IN = 60,              -- frames to blend in on arrival
}
local DUSK_COLORS = { "light", "ambient", "vertex", "fog", "sky" }

-- the lighting to show: snapshot (the values on arrival) blended toward dusk -> night. s = 0..1 (fade in),
-- b = 0..1 (dusk -> night). Pure (tools/luatest checks it). Colour channels are integers 0..255.
function sgl_lake_dusk_mix(snap, s, b)
    local D, Nt = SGL_LAKE_DUSK.dusk, SGL_LAKE_DUSK.night
    local out = {}
    for _, k in ipairs(DUSK_COLORS) do
        local c = {}
        for i = 1, 3 do
            local want = lerp(D[k][i], Nt[k][i], b)
            c[i] = clamp(math.floor(lerp(snap[k][i], want, s) + 0.5), 0, 255)
        end
        out[k] = c
    end
    out.dir = {}
    for i = 1, 3 do out.dir[i] = lerp(snap.dir[i], lerp(D.dir[i], Nt.dir[i], b), s) end
    out.fogIntensity = lerp(snap.fogIntensity, lerp(D.fogIntensity, Nt.fogIntensity, b), s)
    return out
end

local sDusk = { applied = false, s = 0, b = 0, snap = nil, cur = nil, dncHooked = false }

local function dusk_snapshot()
    local snap = { light = {}, ambient = {}, vertex = {}, fog = {}, sky = {}, dir = {} }
    for i = 0, 2 do
        snap.light[i + 1] = get_lighting_color(i)
        snap.ambient[i + 1] = get_lighting_color_ambient(i)
        snap.vertex[i + 1] = get_vertex_color(i)
        snap.fog[i + 1] = get_fog_color(i)
        snap.sky[i + 1] = get_skybox_color(i)
        snap.dir[i + 1] = get_lighting_dir(i)
    end
    snap.fogIntensity = get_fog_intensity()
    return snap
end

local function dusk_set(v)
    for i = 0, 2 do
        set_lighting_dir(i, v.dir[i + 1])
        set_lighting_color(i, v.light[i + 1])
    end
    for i = 0, 2 do
        set_lighting_color_ambient(i, v.ambient[i + 1])   -- after set_lighting_color, which resets the ambient
        set_vertex_color(i, v.vertex[i + 1])
        set_fog_color(i, v.fog[i + 1])
        set_skybox_color(i, v.sky[i + 1])
    end
    set_fog_intensity(v.fogIntensity)
end

local function dusk_restore()
    if sDusk.applied and sDusk.snap ~= nil then dusk_set(sDusk.snap) end
    sDusk.applied, sDusk.snap, sDusk.cur, sDusk.s, sDusk.b = false, nil, nil, 0, 0
end

-- true when the local player is in the bat census act of the built stage
function sgl_lake_in_dusk_act()
    local np = gNetworkPlayers[0]
    if np.currLevelNum ~= LEVEL_JRB or np.currActNum ~= LAKE_MISSION_ACTS.bats then return false end
    local stage = sgl_stage_by_level(LEVEL_JRB)
    return stage ~= nil and sgl_stage_ready(stage)
end

function sgl_lake_dusk_state() return sDusk end

-- Day Night Cycle DX: feed its lighting hooks our dusk while it is shown (it repaints the lighting every
-- frame); registered once, the first time the API is seen
local function dnc_color(k)
    return function()
        local v = sDusk.cur
        if not sDusk.applied or v == nil then return nil end
        return { r = v[k][1], g = v[k][2], b = v[k][3] }
    end
end

-- Day Night Cycle DX publishes its API as _G.dayNightCycleApi in coopdx's real global table. This file's _G is
-- that table too (the per-mod environment only falls back to it), but read it through the normal (metatable)
-- lookup as well, inside a pcall: if _G ever were the mod's own environment, its __index still reaches the
-- real globals, and a strict environment cannot raise.
local DNC_API = "dayNightCycleApi"      -- another mod's global: no file of this mod assigns it
local function dnc_read() return _G[DNC_API] end

local function dnc_api()
    local api = rawget(_G, DNC_API)
    if api == nil then
        local ok, v = pcall(dnc_read)
        if ok then api = v end
    end
    return api
end

local function dnc_hook()
    if sDusk.dncHooked then return end
    local api = dnc_api()
    if type(api) ~= "table" or type(api.dnc_hook_event) ~= "function" or type(api.constants) ~= "table" then return end
    sDusk.dncHooked = true
    local C = api.constants
    pcall(function()
        api.dnc_hook_event(C.DNC_HOOK_SET_LIGHTING_COLOR, dnc_color("light"))
        api.dnc_hook_event(C.DNC_HOOK_SET_AMBIENT_LIGHTING_COLOR, dnc_color("ambient"))
        api.dnc_hook_event(C.DNC_HOOK_SET_FOG_COLOR, dnc_color("fog"))
        api.dnc_hook_event(C.DNC_HOOK_SET_FOG_INTENSITY, function()
            if not sDusk.applied or sDusk.cur == nil then return nil end
            return sDusk.cur.fogIntensity
        end)
        api.dnc_hook_event(C.DNC_HOOK_SET_LIGHTING_DIR, function()
            local v = sDusk.cur
            if not sDusk.applied or v == nil then return nil end
            return { x = v.dir[1], y = v.dir[2], z = v.dir[3] }
        end)
    end)
end

local sBatsDef = nil

local function dusk_update()
    dnc_hook()
    if not sgl_lake_in_dusk_act() then
        if sDusk.applied then dusk_restore() end
        return
    end
    local b = 0
    local ctx = sgl_mission_ctx()
    if ctx ~= nil and ctx.def == sBatsDef and not ctx.dormant then
        if ctx.x == SGL_LAKE_CENSUS_COUNTING then
            b = clamp(ctx.c / (sBatsDef.spec.duration or 90), 0, 1)
        elseif ctx.x == SGL_LAKE_CENSUS_COMPLETE then
            b = 1
        end
    end
    if not sDusk.applied then
        sDusk.snap = dusk_snapshot()
        sDusk.applied = true
        sDusk.s, sDusk.b = 0, b
    end
    sDusk.s = math.min(1, sDusk.s + 1 / SGL_LAKE_DUSK.FADE_IN)
    sDusk.b = sDusk.b + clamp(b - sDusk.b, -0.01, 0.01)
    sDusk.cur = sgl_lake_dusk_mix(sDusk.snap, sDusk.s, sDusk.b)
    dusk_set(sDusk.cur)
end

---------------------------------------------------------------------------------------------
-- act 1: BOARDWALK WELCOME
---------------------------------------------------------------------------------------------
local END_PAD = P.pads[#P.pads]

sgl_mission_register({
    id = "lake_boardwalk",
    pointsFile = POINTS_FILE,
    level = LEVEL_JRB,
    act = LAKE_MISSION_ACTS.boardwalk,
    title = "BOARDWALK WELCOME",
    objective = "Boardwalk, bog, then lily pads out to the lake deck!",
    star = P.deck_star,             -- spawned on the deck's far side, 1 m clear of the pavilion roof's eave
    starFrom = P.deck_star_from,    -- it arcs in from over the open water beyond that side: neither its arc nor
                                    -- its final 2.1 m rise (bhvStarSpawnCoordinates) passes through the roof
    probes = { probe(P.boardwalk, "the north boardwalk"), probe(P.deck, "the observation deck") },
    compactPanel = true,
    kind = kind_hop({
        boardwalk = P.boardwalk,
        boardwalkRadius = 600,      -- the 10 m deck and its viewing bay
        bog = P.bog,
        bogRadius = 1400,           -- anywhere on the west bog (about 37 x 34 m)
        pads = P.pads,
        goal = P.deck,
        goalRadius = P.deck_r - 20, -- on the octagon (inradius 4.5 m)
        skeeters = P.skeeters,      -- {} removes the Skeeters
        lurk = {                    -- two big gators lurk beside the middle of the pad line (nil removes them)
            homes = P.lurk_gators,
            lunge = 1500,           -- they go for a swimmer within 15 m of their home (the pads are 6+ m off it)
            patrol = 300,           -- and cruise a 3 m circle (never under a pad)
            model = E_MODEL_SUSHI,
            scale = 0.8,
            toast = "CHOMP! A gator - back onto the lily pads!",
        },
    }),
})

---------------------------------------------------------------------------------------------
-- act 2: GATOR HOP
---------------------------------------------------------------------------------------------
sgl_mission_register({
    id = "lake_gator_hop",
    pointsFile = POINTS_FILE,
    level = LEVEL_JRB,
    act = LAKE_MISSION_ACTS.gators,
    title = "GATOR HOP",
    objective = "Hop the basking gators to their nest - don't fall in!",
    star = P.nest_star,
    starFrom = up(P.nest_star, 800),
    starCutsceneRange = 6000,       -- the last gators are ~50 m from the nest
    probes = { probe(P.deck, "the observation deck"), probe(P.nest, "the small bog (gator nest)") },
    compactPanel = true,
    kind = kind_gators({
        gators = P.gators,
        start = P.deck,             -- D-pad Down lands here; the end pad (1.8 m off it) is the first hop
        startRadius = P.deck_r,
        firstPad = END_PAD,
        nest = P.nest,
        nestRadius = 700,           -- on the small bog (about 18 x 16 m)
        big = P.big_gators,         -- {} removes the big gators
        model = E_MODEL_SUSHI,      -- stand-in for an alligator (vanilla shark): tune modelScale / visDrop in game
        modelScale = 0.64,          -- ~4.4 m long (sushi vertex bounds x the geo's 0.25), the length of the back
        bigScale = 0.8,
        visDrop = 37,               -- the body's top (0.37 m over its origin at 0.64) meets the collision deck
        bigToast = "CHOMP! A big gator - get back on the gators!",
    }),
})

---------------------------------------------------------------------------------------------
-- act 3 (co-op): BAT CENSUS AT DUSK - 2P
---------------------------------------------------------------------------------------------
sBatsDef = sgl_mission_register({
    id = "lake_bat_census",
    pointsFile = POINTS_FILE,
    level = LEVEL_JRB,
    act = LAKE_MISSION_ACTS.bats,
    title = "BAT CENSUS AT DUSK - 2P",
    objective = "Hold the census posts and count the bats at dusk!",
    star = P.census_star,
    starFrom = P.bat_exit_2010,     -- the star flies out of the 2010 bat barn
    starCutsceneRange = 6000,
    probes = { probe(P.census_houses, "the bat barns' census post"), probe(P.census_boardwalk, "the boardwalk census post") },
    kind = kind_census({
        stations = {
            { x = P.census_houses.x, y = P.census_houses.y, z = P.census_houses.z, name = "Bat barns" },
            { x = P.census_gardens.x, y = P.census_gardens.y, z = P.census_gardens.z, name = "Gardens" },
            { x = P.census_boardwalk.x, y = P.census_boardwalk.y, z = P.census_boardwalk.z, name = "Boardwalk" },
        },
        radius = 260,               -- stand on the post's switch (vanilla purple switch at scale 1.5)
        height = 400,
        duration = 90,              -- design: the bats stream out for 90 s
        countdown = 3,
        gatherMax = 60,             -- one post staffed for 60 s starts the count anyway (and it will fall short)
        base = 6.5,                 -- bats per second at a post: one post alone makes 585 in 90 s (< 600)
        extra = 3,                  -- + per extra counter at the same post (up to maxExtra)
        maxExtra = 2,
        target0 = 600,              -- design: 600 + 300 per extra player (2 players 900, 3 1200, 4+ 1500)
        targetPer = 300,
        maxPlayers = 4,
        exits = { P.bat_exit_2010, P.bat_exit_2017 },
        spread = 0x0A00,            -- each client's swarm streams from both barns over that player's post (+-14 deg)
        batEvery = 6,               -- one cosmetic bat every 0.2 s ...
        batMax = 40,                -- ... at most 40 at once (5-9 s each: 2 s past the post)
        batScale = 0.5,
        attackers = true,           -- false: no diving Swoopers
        swoopFirst = 120,           -- frames on a post before the first Swooper
        swoopEvery = 330,           -- then one every 11 s (at most 2 alive)
        swoopLife = 240,            -- a Swooper is taken away 8 s after it came ...
        swoopLeash = 1500,          -- ... or once it is 15 m from its post (after its pass), so the next one comes
        lake = P.deck,              -- D-pad Down: posts face the lake centre
        music = SEQ_LEVEL_SPOOKY,   -- while counting (Big Boo's Haunt)
    }),
})

---------------------------------------------------------------------------------------------
-- act 4: GATOR REGATTA (design 7.4 act 3 "Shell Surf Regatta")
---------------------------------------------------------------------------------------------
local BUOY_NAMES = { "west bay", "south-west bay", "south shore", "south of the deck", "east end", "north-east",
    "north shore", "home stretch" }
local REGATTA_BUOYS = {}
for i, b in ipairs(P.buoys) do
    REGATTA_BUOYS[i] = { x = b.x, y = b.y, z = b.z, name = "Buoy " .. i .. ", " .. BUOY_NAMES[i] }
end

sgl_mission_register({
    id = "lake_regatta",
    pointsFile = POINTS_FILE,
    level = LEVEL_JRB,
    act = LAKE_MISSION_ACTS.regatta,
    title = "GATOR REGATTA",
    objective = "Ride a gator round the 8 buoys. Par 1'15!",       -- <= ~50 chars: 4:3 windows
    star = P.regatta_star,          -- the star waits at the dock (design)
    starFrom = up(P.buoys[#P.buoys], 600),                           -- it flies in from the last buoy
    starCutsceneRange = 14000,      -- the last buoy is ~130 m from the dock: a racer coming home sees it land
    probes = { probe(P.regatta_dock, "the regatta dock (water off the Baughman lawn)"),
               probe(P.regatta_spare, "the spare gator's shore (east bank)") },
    kind = kind_regatta({
        start = P.regatta_dock,
        startRadius = 800,          -- the cove off the Baughman lawn
        startLabel = "the dock",
        checkpoints = REGATTA_BUOYS,
        cpRadius = 900,             -- tall and forgiving (design): 9 m round each buoy (all >= 27 m from shore) ...
        cpBelow = 500,              -- ... from 5 m under the surface (a swimmer counts too) ...
        cpAbove = 1500,             -- ... to 15 m over it (a gator hop)
        par = 75,                   -- design par; a ridden gator tops out near 19 m/s (~40 s flat out)
        gold = 45,
        timeout = 150,
        lobbyWait = 10,
        countdown = 3,
        resultsSeconds = 4,
        finishGrace = 45,
        pbKey = "pb_lake_gator_regatta",
        title = "GATOR REGATTA",
        cpMarker = "BUOY ",
        gators = {                  -- where a ride gator waits (one per client): the dock, the spare on the safe shoreline
            { x = P.regatta_dock.x, y = P.regatta_dock.y, z = P.regatta_dock.z, face = P.buoys[1], name = "the dock" },
            { x = P.regatta_spare.x, y = P.regatta_spare.y, z = P.regatta_spare.z, face = P.buoys[5], name = "the east shore" },
        },
        buoyModel = E_MODEL_KOOPA_FLAG,  -- Koopa the Quick's finish flag on the water
        buoyScale = 2,
        flameUp = 600,
        flameScale = 4,
    }),
})

hook_event(HOOK_UPDATE, dusk_update)
hook_event(HOOK_ON_WARP, function() dusk_update() end)
