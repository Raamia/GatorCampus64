-- Super Gatorlator 64: the stage table, the hub <-> stage warp contract and the course / act names.
-- Full contract: docs/flow.md. Loaded before levels.lua (files load alphabetically into one shared
-- environment), which builds the hub doors, the warps and /campus on top of these globals.
--
-- Stages replace vanilla level slots (DynOS, the Star Road way): mods/sgl64/levels/<slot>/ holds the
-- Fast64 C export with a level_<slot>_entry script; coopdx compiles it into
-- levels/level_<slot>_entry.lvl at launch and that .lvl replaces the vanilla level.
--   hub    castle_grounds  LEVEL_CASTLE_GROUNDS  (tools/campus/build_stage.py hub)
--   door 1 bob             LEVEL_BOB / COURSE_BOB  The Swamp (Auditorium door)                 built
--   door 2 wf              LEVEL_WF  / COURSE_WF   Reitz Union + Engineering (The Hub door)    built (2 stars)
--   door 3 jrb             LEVEL_JRB / COURSE_JRB  Lake Alice (Newell Hall door)               built (5 stars)
--   door 4 ccm             LEVEL_CCM / COURSE_CCM  Marston Science Library (Marston door)      built (8 stars; an interior)
--   door 5 bbh             LEVEL_BBH / COURSE_BBH  Library West After Dark (Library West door) built (11 stars; an interior)
--   door 6 ttc             LEVEL_TTC / COURSE_TTC  Century Tower interior (tower base door)    reserved (14 stars)
--
-- Stars: act k (1..6) mission star = star id k - 1 of the stage's course. Star id 6 is the unused vanilla
-- 100-coin slot; ambient coins are disabled in the campus maps. Star collection is shared by coopdx.
--
-- Act order = what is actually playable. Vanilla act select only offers the acts you already have
-- stars for plus the NEXT one, so the built missions must be acts 1, 2, 3 (in that order, solo-able
-- ones first) or progression would stop at the first act without a star. Acts with no mission yet are
-- named "COMING SOON - ..." (sgl_act_is_soon): they load the stage as free roam (no star), the HUD says
-- so (sgl_mission.lua) and Pause > EXIT COURSE returns to the hub, so nothing can soft-lock.
-- The Swamp: 1 Kickoff (design 7.1 act 1), 2 Stair Sprint (design act 5), 3 Chomp Chorus (design act 3,
-- co-op); design acts 2 (Visiting Mascot), 4 (Tailgate Tokens) and 6 (Flyover!) come later as 4/5/6.
-- Reitz & Engineering: 1 Rooftop of the Reitz (design 7.2 act 1), 2 Meal Swipe Tokens (design act 5),
-- 3 Remote Robotics Lab (design act 2, co-op); design acts 3 (Weil Wind Tunnel), 4 (Rogue Robot Roundup)
-- and 6 (Data Packet Relay) come later as 4/5/6.
-- Lake Alice: 1 Boardwalk Welcome (design 7.4 act 1), 2 Gator Hop (design act 2), 3 Bat Census at Dusk (design
-- act 4, co-op); design acts 3 (Shell Surf Regatta), 5 (Lost Hatchling) and 6 (Lily Pad Red Coins) come later
-- as 4/5/6.
-- Marston Science Library: 1 Out-of-Order Elevator (design 7.3 act 1), 2 Shhh! Lost Textbooks (design acts 2 + 4: the
-- quiet floor's Shushers guarding 8 textbooks), 3 Study Room Booking (design act 3, co-op); design acts 4 (Lost Lab
-- Notebook Pages), 5 (Printer Jam) and 6 (Overdue Book Express) come later as 4/5/6. Built: levels/ccm (an interior,
-- tools/campus/build_interior.py marston).
-- Library West After Dark: 1 All-Nighter (design 7.5 act 1), 2 Coffee Run (design act 5, a race), 3 Quiet Hours Hide &
-- Seek (design act 2, co-op / competitive); design acts 3 (The Ghost of Finals Past), 4 (Lights Out) and 6 (Re-shelve the
-- Glowing Books) come later as 4/5/6. Missions: uf_west_library_missions.lua. Built: levels/bbh (an interior at night,
-- tools/campus/build_interior.py libwest).
-- Star curve: doors open at 0, 2, 5, 8, 11, 14. With ambient coins removed, the third act's shared co-op star is
-- required to keep advancing beyond the first two courses.

---------------------------------------------------------------------------------------------
-- warp nodes (area 1 everywhere)
---------------------------------------------------------------------------------------------
SGL_HUB_LEVEL = LEVEL_CASTLE_GROUNDS
SGL_NODE_SPAWN = 0x0A          -- hub: Plaza spawn (pause "Exit to castle", /campus hub); stages: entry spawn
SGL_NODE_HUB_DEATH = 0x0B      -- hub: Plaza respawn after dying in the hub (hub 0xF1 -> 0x0B)
SGL_NODE_DOOR = 0x10           -- hub: WARP_NODE(0x10 + door) -> stage level, area 1, node 0x0A
SGL_NODE_STAR_RETURN = 0x20    -- hub: spawn outside door after a star (stage WARP_NODE 0xF0 -> 0x20 + door)
SGL_NODE_DEATH_RETURN = 0x30   -- hub: spawn outside door after a death or pause "Exit course" (stage 0xF1)

SGL_STAR_ID_100_COINS = 6      -- vanilla 100-coin star id in every course

---------------------------------------------------------------------------------------------
-- stages. door = hub door index (its warp nodes are 0x10/0x20/0x30 + door); stars = total stars
-- (save file, all courses + castle secret stars) needed to open the door. acts = act select names
-- (menu font: A-Z 0-9 space ' . , - & ! ? only, no lower case / colon / parentheses / plus).
---------------------------------------------------------------------------------------------
SGL_STAGES = {
    { door = 1, key = "swamp", slot = "bob", level = LEVEL_BOB, course = COURSE_BOB, stars = 0,
      name = "THE SWAMP", building = "UNIVERSITY AUDITORIUM",
      acts = {
          "KICKOFF - CLIMB THE SKYBOX",   -- swamp_missions.lua swamp_skybox (+ level-script star id 0)
          "STADIUM STAIR SPRINT",         -- swamp_missions.lua swamp_sprint (race, par 1'10)
          "GATOR CHOMP CHORUS - 2P",      -- swamp_missions.lua swamp_chorus (co-op, 2-4 players)
          "COMING SOON - MASCOT",         -- design 7.1 "The Visiting Mascot" (no mission yet)
          "COMING SOON - TAILGATE",       -- design 7.1 "Tailgate Tokens" (no mission yet)
          "COMING SOON - FLYOVER!",       -- design 7.1 "Flyover!" (no mission yet)
      } },
    { door = 2, key = "reitz", slot = "wf", level = LEVEL_WF, course = COURSE_WF, stars = 2,
      name = "REITZ & ENGINEERING", building = "THE HUB",
      acts = {
          "ROOFTOP OF THE REITZ",         -- wf_reitz_missions.lua reitz_rooftop (spawns star id 0; no level-script star)
          "MEAL SWIPE TOKENS",            -- wf_reitz_missions.lua reitz_tokens (8 tokens, shared)
          "REMOTE ROBOTICS LAB - 2P",     -- wf_reitz_missions.lua reitz_robotics (co-op cranes, 2-4 players)
          "COMING SOON - WIND TUNNEL",    -- design 7.2 "Weil Wind Tunnel" (no mission yet)
          "COMING SOON - ROBOT ROUNDUP",  -- design 7.2 "Rogue Robot Roundup" (no mission yet)
          "COMING SOON - DATA RELAY",     -- design 7.2 "Data Packet Relay" (no mission yet)
      } },
    { door = 3, key = "alice", slot = "jrb", level = LEVEL_JRB, course = COURSE_JRB, stars = 5,
      name = "LAKE ALICE", building = "NEWELL HALL",
      acts = {
          "BOARDWALK WELCOME",            -- uf_lake_missions.lua lake_boardwalk (lily pads to the lake-centre deck; spawns star id 0)
          "GATOR HOP",                    -- uf_lake_missions.lua lake_gator_hop (sinking gators to the nest)
          "BAT CENSUS AT DUSK - 2P",      -- uf_lake_missions.lua lake_bat_census (co-op, 2-4 players, dusk lighting)
          "COMING SOON - REGATTA",        -- design 7.4 act 3 "Shell Surf Regatta" (no mission yet)
          "COMING SOON - HATCHLING",      -- design 7.4 act 5 "Lost Hatchling" (no mission yet)
          "COMING SOON - RED COINS",      -- design 7.4 act 6 "Lily Pad Red Coins" (no mission yet)
      } },
    { door = 4, key = "marston", slot = "ccm", level = LEVEL_CCM, course = COURSE_CCM, stars = 8,
      name = "MARSTON LIBRARY", building = "MARSTON SCIENCE LIBRARY",
      acts = {
          "OUT-OF-ORDER ELEVATOR",        -- uf_marston_missions.lua marston_climb (atrium lifts to the 5th floor; spawns star id 0)
          "SHHH! LOST TEXTBOOKS",         -- uf_marston_missions.lua marston_quiet (8 books on the silent floor, Shusher patrols)
          "STUDY ROOM BOOKING - 2P",      -- uf_marston_missions.lua marston_booking (co-op kiosks, 2-4 players)
          "COMING SOON - NOTEBOOK PAGES", -- design 7.3 act 4 "Lost Lab Notebook Pages" (no mission yet)
          "COMING SOON - PRINTER JAM",    -- design 7.3 act 5 "Printer Jam" (no mission yet)
          "COMING SOON - BOOK EXPRESS",   -- design 7.3 act 6 "Overdue Book Express" (no mission yet)
      } },
    { door = 5, key = "libwest", slot = "bbh", level = LEVEL_BBH, course = COURSE_BBH, stars = 11,
      name = "LIBRARY WEST AFTER DARK", building = "LIBRARY WEST",
      acts = {
          "ALL-NIGHTER",                  -- uf_west_library_missions.lua libwest_allnighter (lobby to the 6F big window; spawns star id 0)
          "COFFEE RUN",                   -- uf_west_library_missions.lua libwest_coffee (race: 6F desk -> lobby cup -> back, par 1'00)
          "QUIET HOURS HIDE & SEEK - 2P", -- uf_west_library_missions.lua libwest_hideseek (2+ players, night librarian vs hiders)
          "COMING SOON - GHOST HUNT",     -- design 7.5 act 3 "The Ghost of Finals Past" (no mission yet)
          "COMING SOON - LIGHTS OUT",     -- design 7.5 act 4 "Lights Out" (no mission yet)
          "COMING SOON - GLOWING BOOKS",  -- design 7.5 act 6 "Re-shelve the Glowing Books" (no mission yet)
      } },
    { door = 6, key = "tower", slot = "ttc", level = LEVEL_TTC, course = COURSE_TTC, stars = 14,
      name = "CENTURY TOWER", building = "CENTURY TOWER" },
}

local sByDoor, sByLevel, sByKey, sByCourse = {}, {}, {}, {}
for _, s in ipairs(SGL_STAGES) do
    sByDoor[s.door] = s
    sByLevel[s.level] = s
    sByKey[s.key] = s
    sByCourse[s.course] = s
end

function sgl_stage_by_door(door) return sByDoor[door] end
function sgl_stage_by_level(levelNum) return sByLevel[levelNum] end
function sgl_stage_by_key(key) return sByKey[key] end
function sgl_stage_by_course(courseNum) return sByCourse[courseNum] end

-- star id of act k's mission star (spawn it from an object whose bparam1 = this id, or place
-- OBJECT_WITH_ACTS(MODEL_STAR, ..., id << 24, bhvStar, ACT_k) in the stage's level script)
function sgl_mission_star_id(act) return act - 1 end

-- true once our mod replaces the stage's vanilla level (its levels/<slot>/ compiled and loaded);
-- a stage whose slot is still vanilla is "coming soon" (its door stays shut)
function sgl_stage_ready(stage)
    return stage ~= nil and not level_is_vanilla_level(stage.level)
end

function sgl_hub_ready()
    return not level_is_vanilla_level(SGL_HUB_LEVEL)
end

-- total stars of the current save file (what the door locks check; stars are shared in co-op)
function sgl_total_stars()
    local file = get_current_save_file_num() - 1
    if file < 0 then return gMarioStates[0].numStars end
    return save_file_get_total_star_count(file, COURSE_MIN - 1, COURSE_MAX - 1)
end

-- act select name of act k (nil for a stage without act names)
SGL_ACT_SOON_PREFIX = "COMING SOON"
function sgl_act_name(stage, act)
    if stage == nil or stage.acts == nil then return nil end
    return stage.acts[act]
end

-- true when act k of the stage has no mission yet (its name starts with "COMING SOON", or the stage
-- has no act names at all): free roam, no star, no Study Group invite
function sgl_act_is_soon(stage, act)
    local name = sgl_act_name(stage, act)
    return name == nil or name:sub(1, #SGL_ACT_SOON_PREFIX) == SGL_ACT_SOON_PREFIX
end

-- stars of one stage's course (bit k-1 = act k's mission star, bit 6 = 100 coins)
function sgl_stage_star_flags(stage)
    local file = get_current_save_file_num() - 1
    if stage == nil or file < 0 then return 0 end
    return save_file_get_star_flags(file, stage.course - 1)
end

---------------------------------------------------------------------------------------------
-- course + act names (act select, pause menu, course-complete screen)
---------------------------------------------------------------------------------------------
for _, s in ipairs(SGL_STAGES) do
    if s.acts ~= nil then
        -- the first 3 characters are the course number column (" 1 "), as in Star Road
        smlua_text_utils_course_acts_replace(s.course, string.format("%2d ", s.course) .. s.name,
            s.acts[1], s.acts[2], s.acts[3], s.acts[4], s.acts[5], s.acts[6])
    else
        smlua_text_utils_course_name_replace(s.course, s.name)
    end
end
smlua_text_utils_castle_secret_stars_replace("   CAMPUS SECRETS")
