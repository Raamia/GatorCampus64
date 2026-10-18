-- Super Gatorlator 64: The Swamp (course 1, LEVEL_BOB) missions, on the framework in sgl_mission.lua.
--
--   act 1  KICKOFF - CLIMB THE SKYBOX   reach: climb the West Skybox Tower to the press box roof (66 m).
--                                       Its star is the LEVEL-SCRIPT star (bhvStar id 0, ACT_1, placed by
--                                       build_stage.py STAGE_STARS): the mission only tracks the climb.
--                                       The marker walks the route: CLIMB HERE (west rim) -> LEDGES ->
--                                       CAMERA DECKS / POLE -> PRESS BOX ROOF. Coins on every ledge and
--                                       deck, hearts at the rim, the Bull Gator Deck and deck 5, and a
--                                       22.5 m pole from the deck to the roof (stage_pickups.py).
--   act 2  STADIUM STAIR SPRINT         race: north end zone -> up the east stands -> around the rim
--                                       -> South Ramp terrace, 9 checkpoints, par 1'10, gold 0'45 (solo or
--                                       more); race music; D-pad Down = back to the start box
--   act 3  GATOR CHOMP CHORUS           buttons (co-op, POUND mode): 3 phrases; in each, hold the lit
--                                       end-zone corners while the crowd counts GA... TOR..., then
--                                       ground-pound on CHOMP!; the next phrase lights other corners.
--                                       Lit buttons = players here, 2..4. ALONE: the solo rhythm game of
--                                       swamp_chomp.lua (4 pads in the north end zone), same star.
--   acts 4-6 "COMING SOON - ..." in course.lua: free roam, no star (sgl_mission.lua shows a notice).
-- Act order: vanilla act select offers the acts you have stars for plus the next one, so the playable
-- missions are acts 1-3, the solo ones first (course.lua header). Stars of acts 2 and 3 are spawned by
-- the mission (spawn_default_star, star id = act - 1): do NOT place a bhvStar for them in the level
-- script (the framework warns in the console if one is there). Act 1 sets levelStar = true instead.
-- Each mission checks the stage geometry first (SWAMP_POINTS probes): if levels/bob is not the real
-- Swamp they stay offline (HUD note + console line); /mission force runs them anyway.

---------------------------------------------------------------------------------------------
-- ALL Swamp mission coordinates, in game units (area 1 of LEVEL_BOB). Swap values here only.
-- Source: data/uf/swamp_points.json (written by tools/campus/build_stage.py swamp from the BUILT
-- collision; "game" = [X, floor Y, Z]), names in the comments. The JSON follows the stadium landmark
-- module tools/campus/landmarks/swamp_stadium.py through the stages.json transform of the swamp window
-- (centre (-580, 160) m):  X = (x + 580) * 100,  Y = z * 100,  Z = -(y - 160) * 100.
-- Grade around the stadium is Y 0; the field is sunk to Y -1000; the bowl rim is Y 2000.
-- tools/luatest/check_swamp_points.py fails on drift > 0.5 m against the JSON; --print prints fresh values.
---------------------------------------------------------------------------------------------
SWAMP_POINTS = {
    field_center   = { x = 6572,  y = -1000, z = 3702 },   -- field.points field_center (midfield, turf)
    scoreboard_top = { x = 6510,  y = 5560,  z = 15477 },  -- secret_spots secret_south_board_top (stars drop from here)

    -- act 1: the West Skybox Tower (press box / skybox, roof 66 m)
    climb_goal     = { x = -3828, y = 6600,  z = 3648 },   -- press_box.points press_box_roof_star_spot (roof centre)
    climb_star     = { x = -3828, y = 6720,  z = 3648 },   -- stars[1]: the level-script act 1 star (id 0), 1.2 m up
    climb_zone     = { x0 = -6457, x1 = -1399, z0 = -1966, z1 = 9260 },  -- tower footprint (module local u -130..-80, v -56..56)
    climb_start    = { x = -2433, y = 2000,  z = 8505 },   -- press_box.kickoff_climb_route[1]: west rim, foot of the ledges
    climb_bgd      = { x = -2173, y = 4400,  z = 3656 },   -- press_box.points bull_gator_deck (44 m)
    climb_ledge_top = { x = -2572, y = 4200, z = 8294 },   -- press_box.kickoff_climb_route[12]: the last ledge (42 m)
    climb_decks    = { x = -1904, y = 4600,  z = 3778 },   -- press_box.kickoff_climb_route[14]: the first camera deck (46 m)
    climb_pole     = { x = -1825, y = 4400,  z = 3108 },   -- act_spots.poles pole_bgd_to_press_box_roof (22.5 m pole)

    -- act 3: the four end-zone corner buttons (field level, 1 m inside the end line and sideline)
    button_nw      = { x = 4262,  y = -1000, z = -1697 },  -- field.points endzone_corner_NW
    button_ne      = { x = 8939,  y = -1000, z = -1672 },  -- field.points endzone_corner_NE
    button_se      = { x = 8882,  y = -1000, z = 9101 },   -- field.points endzone_corner_SE
    button_sw      = { x = 4205,  y = -1000, z = 9076 },   -- field.points endzone_corner_SW

    -- act 2: races.stair_sprint.waypoints (start = [1], checkpoints = [2..10])
    sprint_start   = { x = 6598,  y = -1000, z = -1298 },  -- north end zone
    sprint_checkpoints = {
        { x = 9402,  y = -1000, z = -2083, name = "NE field corner" },
        { x = 10053, y = -826,  z = -280,  name = "east field wall" },
        { x = 11668, y = 0,     z = 729,   name = "east cross-aisle" },
        { x = 13540, y = 948,   z = 2238,  name = "east stands" },
        { x = 15552, y = 2000,  z = 3749,  name = "east rim" },
        { x = 15528, y = 2000,  z = 8249,  name = "east rim, south end" },
        { x = 13520, y = 2000,  z = 13589, name = "south-east rim" },
        { x = 8670,  y = 2000,  z = 15568, name = "south rim" },
        { x = 6508,  y = 2000,  z = 15832, name = "South Ramp terrace (finish)" },
    },
    sprint_star    = { x = 6508,  y = 2000,  z = 15942 },  -- act_spots.act4_red_coin_candidates rc_south_ramp_terrace
}

-- which act each mission is (star id = act - 1). Keep in step with the act names in course.lua
-- (tools/luatest/test_missions.lua checks that every mission title equals its course.lua act name).
SWAMP_MISSION_ACTS = { skybox = 1, sprint = 2, chorus = 3 }

---------------------------------------------------------------------------------------------
if sgl_mission_register == nil then
    log_to_console("[SGL] swamp_missions.lua: sgl_mission.lua is not loaded", CONSOLE_MESSAGE_ERROR)
    return
end

local P = SWAMP_POINTS

local function up(p, dy)
    return { x = p.x, y = p.y + dy, z = p.z }
end

local function probe(p, name)
    return { x = p.x, y = p.y, z = p.z, name = name }
end

-- act 1 ------------------------------------------------------------------------------------
sgl_mission_register({
    id = "swamp_skybox",
    level = LEVEL_BOB,
    act = SWAMP_MISSION_ACTS.skybox,
    title = "KICKOFF - CLIMB THE SKYBOX",
    objective = "Climb the West Skybox Tower to the press box roof, 66 m up!",   -- <= ~60 chars (banner)
    levelStar = true,               -- the star is the level script's bhvStar (id 0, ACT_1): never spawn one
    star = P.climb_star,            -- (HUD marker once the roof is reached)
    probes = { probe(P.climb_goal, "the press box roof"), probe(P.field_center, "the field") },
    compactPanel = true,            -- the left panel shrinks to the height line once the climb is on
    kind = sgl_mission_kind_reach({
        goal = P.climb_goal,
        goalRadius = 4000,          -- anywhere on the roof (it is ~36 x 90 m) counts
        goalBelow = 100,
        goalLabel = "PRESS BOX ROOF",
        zone = P.climb_zone,
        ground = 0,
        milestones = {
            { name = "West rim", y = P.climb_start.y },
            { name = "Bull Gator Deck", y = P.climb_bgd.y },
            { name = "Press box roof", y = P.climb_goal.y },
        },
        -- the marker walks the climb (a stage is done once you are above its doneY in the tower zone;
        -- from the first camera deck on it points at the roof)
        route = {
            { pos = P.climb_start, label = "CLIMB HERE", doneY = P.climb_start.y - 50 },
            { pos = P.climb_ledge_top, label = "LEDGES", doneY = P.climb_bgd.y - 50 },
            { pos = P.climb_decks, label = "CAMERA DECKS / POLE", doneY = P.climb_decks.y + 50 },
        },
    }),
})

-- act 2 (race) -----------------------------------------------------------------------------
sgl_mission_register({
    id = "swamp_sprint",
    level = LEVEL_BOB,
    act = SWAMP_MISSION_ACTS.sprint,
    title = "STADIUM STAIR SPRINT",
    objective = "Up the east stands, round the rim. Par 1'10!",        -- <= ~50 chars: 4:3 windows
    star = up(P.sprint_star, 150),
    starFrom = P.scoreboard_top,
    probes = { probe(P.sprint_start, "the north end zone"),
               probe(P.sprint_checkpoints[#P.sprint_checkpoints], "the South Ramp terrace") },
    kind = sgl_mission_kind_race({
        start = P.sprint_start,
        startRadius = 700,
        startLabel = "north end zone",
        checkpoints = P.sprint_checkpoints,
        cpRadius = 800,
        cpBelow = 400,
        cpAbove = 800,
        par = 70,
        timeout = 150,
        lobbyWait = 10,
        countdown = 3,
        resultsSeconds = 4,
        finishGrace = 45,           -- results 45 s after the first finish (a racer who gave up never stalls it)
        gold = 45,                  -- gold time on the board (the ideal line is ~31-38 s)
        music = SEQ_LEVEL_SLIDE,    -- Koopa-the-Quick race music while racing
        pbKey = "pb_swamp_stair_sprint",
        title = "STAIR SPRINT",
    }),
})

-- act 3 (co-op) ----------------------------------------------------------------------------
sgl_mission_register({
    id = "swamp_chorus",
    level = LEVEL_BOB,
    act = SWAMP_MISSION_ACTS.chorus,
    title = "GATOR CHOMP CHORUS",
    objective = "Hold the lit corners, then ground-pound on CHOMP!",
    star = up(P.field_center, 150),
    starFrom = P.scoreboard_top,
    starCutsceneRange = 8000,       -- the corner buttons are ~58 m from midfield: everyone sees it
    probes = { probe(P.field_center, "the field"), probe(P.button_nw, "the NW end-zone corner") },
    kind = sgl_swamp_chomp_kind(sgl_mission_kind_buttons({
        buttons = {
            { x = P.button_nw.x, y = P.button_nw.y, z = P.button_nw.z, name = "North-west corner" },
            { x = P.button_ne.x, y = P.button_ne.y, z = P.button_ne.z, name = "North-east corner" },
            { x = P.button_se.x, y = P.button_se.y, z = P.button_se.z, name = "South-east corner" },
            { x = P.button_sw.x, y = P.button_sw.y, z = P.button_sw.z, name = "South-west corner" },
        },
        -- POUND mode: 3 phrases; the lit corners move every phrase, so players run to new corners
        -- (2 players: NW + SE, then NE + SW (47 m runs), then NW + SE again)
        pound = true,
        phrases = {
            [2] = { { 1, 3 }, { 2, 4 }, { 1, 3 } },
            [3] = { { 1, 2, 3 }, { 2, 3, 4 }, { 3, 4, 1 } },
            [4] = { { 1, 2, 3, 4 }, { 1, 2, 3, 4 }, { 1, 2, 3, 4 } },
        },
        chant = { "GA...", "TOR...", "CHOMP!" },
        beat = 1.0,                 -- seconds per chant word
        window = 1.3,               -- seconds after CHOMP! to land the ground pound
        minPlayers = 2,
        radius = 300,               -- stand on the switch (vanilla purple switch at scale 1.5)
        height = 400,               -- ... or be in the air above it (the jump of a ground pound)
    }), {
        -- solo pads: a row of 4, 3.5 m apart, mid north end zone (well clear of the corner buttons)
        { x = (P.button_nw.x + P.button_ne.x) // 2 - 525, y = P.button_nw.y, z = (P.button_nw.z + P.button_ne.z) // 2 + 450 },
        { x = (P.button_nw.x + P.button_ne.x) // 2 - 175, y = P.button_nw.y, z = (P.button_nw.z + P.button_ne.z) // 2 + 450 },
        { x = (P.button_nw.x + P.button_ne.x) // 2 + 175, y = P.button_nw.y, z = (P.button_nw.z + P.button_ne.z) // 2 + 450 },
        { x = (P.button_nw.x + P.button_ne.x) // 2 + 525, y = P.button_nw.y, z = (P.button_nw.z + P.button_ne.z) // 2 + 450 },
    }),
})
