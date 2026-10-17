-- Super Gatorlator 64: levels and the hub <-> stage flow. Contract: docs/flow.md; the stage table and
-- the warp node numbers live in course.lua (loaded first).
--
-- The mod is a romhack-style total conversion (main.lua: "-- incompatible: romhack"). Its levels
-- REPLACE vanilla level slots through DynOS, the way Star Road does:
--   levels/castle_grounds/  the hub (UF central campus), tools/campus/build_stage.py hub
--   levels/bob/             course 1, The Swamp (Ben Hill Griffin Stadium + O'Connell Center + Gym),
--                           tools/campus/build_stage.py swamp (missions: swamp_missions.lua)
-- coopdx compiles each folder into levels/level_<slot>_entry.lvl at launch and the .lvl replaces the
-- vanilla level. sgl_test stays a custom (non-vanilla) test level, registered below.
--
-- Flow (all vanilla machinery, nothing warps "around" the engine):
--   start / game over      gLevelValues.entryLevel = the hub: MARIO_POS on the Plaza of the Americas
--   hub stage door i       id_bhvSglDoor (below, placed by the generator): walk into the doorway ->
--                          star lock check -> Mario "enters" it like a vanilla warp object, and
--                          level_trigger_warp(WARP_OP_WARP_OBJECT) uses the hub's WARP_NODE(0x10 + i)
--                          -> stage level, node 0x0A. The level change shows the vanilla ACT SELECT.
--   star in a stage        star dance -> stage WARP_NODE 0xF0 -> hub 0x20 + i (outside door i,
--                          course-complete screen)
--   death / "Exit course"  stage WARP_NODE 0xF1 -> hub 0x30 + i (outside door i)
--   "Exit to castle"       gLevelValues.exitCastle* -> hub Plaza spawn 0x0A
--
-- Test: /campus where | list | hub [me] | back [me] | test [me] | <stage> [act] [me]
--       (/campus swamp 1 = straight into The Swamp act 1, skipping the door and act select). Only the
--       host (or a moderator) moves everyone; anyone else's /campus moves only themselves.
-- Hub hint: once the character menu is out of the way, a "NEXT" panel + marker points at the door of
--       the next stage with an unstarred playable act (and the first visit's welcome popup).

---------------------------------------------------------------------------------------------
-- global level settings (same on every client, set at mod load like Star Road / sm74)
---------------------------------------------------------------------------------------------
gLevelValues.entryLevel = SGL_HUB_LEVEL           -- new game, game over, warp_to_start_level
gLevelValues.exitCastleLevel = SGL_HUB_LEVEL      -- pause > "Exit to castle"
gLevelValues.exitCastleArea = 1
gLevelValues.exitCastleWarpNode = SGL_NODE_SPAWN  -- ... lands on the Plaza (spin-in spawn)
gLevelValues.fixCollisionBugs = 1                 -- every level of the mod is ours (arena / star-road do this)
gServerSettings.skipIntro = 1                     -- the vanilla intro cutscene assumes Peach's castle grounds

-- camera: the romhack camera in our (non-vanilla) levels, no vanilla per-course camera triggers
camera_set_romhack_override(RCO_ALL_EXCEPT_BOWSER)
camera_set_use_course_specific_settings(false)

---------------------------------------------------------------------------------------------
-- Lua globals the level scripts reference (DynOS resolves these NAMES when a level loads,
-- so they must be globals of this mod and exist before anyone enters the level)
---------------------------------------------------------------------------------------------

local function make_dialog(text, linesPerBox)
    local id = smlua_text_utils_allocate_dialog()
    smlua_text_utils_dialog_replace(id, 1, linesPerBox or 4, 95, 200, text)
    return id
end

-- bhvMessagePanel (wooden signpost) reads its dialog id from behavior param byte 2
local function dialog_bparam(id)
    if id == nil or id < 0 or id > 0xFF then
        log_to_console("[SGL] dialog id " .. tostring(id) .. " does not fit a sign's behavior param", CONSOLE_MESSAGE_WARNING)
        id = DIALOG_000
    end
    return (id & 0xFF) << 16
end

local function sign_bparam(text)
    return dialog_bparam(make_dialog(text))
end

-- signpost in sgl_test
SGL_TEST_SIGN_BPARAM = sign_bparam("SGL TEST FIELD\
Welcome, Gators! Everything\
here is built at true scale:\
1 metre = 100 game units.\
The field is 200 m wide,\
the tower is 10 m tall\
and the pool is 4 m deep.")

-- hub: welcome sign on the Plaza of the Americas (in front of the spawn point, which faces south
-- toward the University Auditorium and Century Tower)
SGL_HUB_SIGN_WELCOME = sign_bparam("PLAZA OF THE AMERICAS\
Welcome to the University\
of Florida, Gators!\
Every building is real\
and full size. The\
University Auditorium is\
straight ahead (south):\
walk into its door to\
enter THE SWAMP.\
The other stage doors\
open as you collect\
stars; their signposts\
say how many you need.\
Century Tower is behind\
the Auditorium.\
Go Gators!")

-- one signpost next to every door (the generator names the bparam SGL_HUB_SIGN_<DOOR SLUG>); the
-- text is rewritten on every hub visit, so it says whether the stage behind the door is built yet
local sDoorSigns = {}

local function door_sign(building, stageName, stars, door)
    local sign = { id = make_dialog(building), building = building, stage = stageName, stars = stars, door = door }
    table.insert(sDoorSigns, sign)
    return dialog_bparam(sign.id)
end

local function door_sign_text(sign)
    local stars = sign.stars == 0 and "Open to everyone!" or
        ("Opens at " .. sign.stars .. " star" .. (sign.stars == 1 and "" or "s") .. ".")
    local stage = sign.door and sgl_stage_by_door(sign.door)
    local status
    if stage ~= nil and sgl_stage_ready(stage) then
        status = "Walk into the door\
to enter."
    else
        status = "Coming soon!"
    end
    return sign.building .. "\
Stage door: " .. sign.stage .. "\
" .. stars .. "\
" .. status
end

local function refresh_door_signs()
    for _, sign in ipairs(sDoorSigns) do
        smlua_text_utils_dialog_replace(sign.id, 1, 4, 95, 200, door_sign_text(sign))
    end
end

SGL_HUB_SIGN_UNIVERSITY_AUDITORIUM = door_sign("UNIVERSITY AUDITORIUM", "THE SWAMP", 0, 1)
SGL_HUB_SIGN_THE_HUB = door_sign("THE HUB", "REITZ UNION AND\
ENGINEERING", 2, 2)
SGL_HUB_SIGN_NEWELL_HALL = door_sign("NEWELL HALL", "LAKE ALICE", 8, 3)
SGL_HUB_SIGN_MARSTON = door_sign("MARSTON SCIENCE LIBRARY", "MARSTON", 5, 4)
SGL_HUB_SIGN_LIBRARY_WEST = door_sign("LIBRARY WEST", "LIBRARY WEST\
AFTER DARK", 14, 5)
SGL_HUB_SIGN_CENTURY_TOWER = door_sign("CENTURY TOWER", "CENTURY TOWER\
(INSIDE)", 20, 6)
-- no stage slot yet (bonus slide, finale): always "coming soon"
SGL_HUB_SIGN_SMATHERS = door_sign("SMATHERS LIBRARY", "SMATHERS STACKS\
SLIDE", 3, nil)
SGL_HUB_SIGN_FINAL_EXAM = door_sign("FINAL EXAM DOOR", "FINALS WEEK\
ASCENT", 30, nil)
refresh_door_signs()

-- goal marker on top of the sgl_test tower (OBJECT(MODEL_NONE, ..., id_bhvSglTestGoal))
local function bhv_sgl_test_goal_init(o)
    o.oFlags = OBJ_FLAG_UPDATE_GFX_POS_AND_ANGLE
    obj_set_model_extended(o, E_MODEL_TRANSPARENT_STAR)
    o.oAction = 0
end

local function bhv_sgl_test_goal_loop(o)
    o.oFaceAngleYaw = o.oFaceAngleYaw + 0x300
    local m = gMarioStates[0]
    local dx, dy, dz = m.pos.x - o.oPosX, m.pos.y - o.oPosY, m.pos.z - o.oPosZ
    local near = dx * dx + dy * dy + dz * dz < 300 * 300
    if near and o.oAction == 0 then
        o.oAction = 1
        play_sound(SOUND_MENU_STAR_SOUND, gGlobalSoundSource)
        djui_popup_create(string.format("\\#ffd700\\You climbed the tower!\\#dcdcdc\\ %.1f m up", m.pos.y / 100), 2)
    elseif not near and o.oAction == 1 and dx * dx + dz * dz > 800 * 800 then
        o.oAction = 0
    end
end

id_bhvSglTestGoal = hook_behavior(nil, OBJ_LIST_LEVEL, true, bhv_sgl_test_goal_init, bhv_sgl_test_goal_loop,
    "bhvSglTestGoal")

---------------------------------------------------------------------------------------------
-- hub stage doors: id_bhvSglDoor
--   placed by tools/campus/build_stage.py at each stage door, on the facade plane, facing out:
--   OBJECT(MODEL_NONE, x, y, z, 0, yaw, 0, (door << 24) | ((0x10 + door) << 16) | (halfWidth_dm << 8) | emblem_dm,
--          id_bhvSglDoor)
--   bparam1 = door index (course.lua SGL_STAGES[].door), bparam2 = the hub warp node it uses (the
--   vanilla warp reads it from m.usedObj), bparam3 = trigger half width in 10 cm units, bparam4 =
--   emblem height above the sill in 10 cm units (the generator lowers it under porch roofs); 0 = default.
-- Every client runs its own copy (no sync): only the local player is checked.
-- Looks: a spinning star above the doorway (gold = open, see-through = locked / coming soon), two
-- red flames beside a door that will not open, and a floating label within DOOR_LABEL_RANGE.
---------------------------------------------------------------------------------------------

local DOOR_REACH_OUT = 150      -- trigger reaches this far in front of the door plane (Mario stops ~50 out)
local DOOR_REACH_IN = -300      -- ... and this far behind it (recessed bays, porches)
local DOOR_HALF_WIDTH = 160     -- default trigger half width
local DOOR_DY_MIN, DOOR_DY_MAX = -150, 350
local DOOR_REARM = 450          -- step this far away to see the "locked" message again
local DOOR_FACING = 0x3800      -- Mario must face into the door (within ~79 degrees)
local DOOR_EMBLEM_OUT, DOOR_EMBLEM_UP = 120, 420   -- build_stage.py DOOR_EMBLEM_OUT_M / DOOR_EMBLEM_UP_M
local DOOR_FLAME_OUT, DOOR_FLAME_UP, DOOR_FLAME_SIDE, DOOR_FLAME_SCALE = 90, 40, 40, 5.0
local DOOR_LABEL_RANGE = 2500   -- 25 m
local DOOR_LABEL_UP = 330
local DOOR_DRAW_DISTANCE = 12000 -- emblem + flames stay visible from 120 m (the object default is 40 m)

local DOOR_OPEN, DOOR_LOCKED, DOOR_SOON = 0, 1, 2

-- door index -> { x, y, z (door sill on the facade plane), yaw (facing out), halfWidth, state,
--                 inside, told, fx = {flame objects}, seen = global timer of the last update }
local sDoors = {}

local function door_state(stage)
    if stage == nil or not sgl_stage_ready(stage) then return DOOR_SOON end
    if sgl_total_stars() < stage.stars then return DOOR_LOCKED end
    return DOOR_OPEN
end

local function angle_diff(a, b)
    local d = (a - b) & 0xFFFF
    if d > 0x8000 then d = 0x10000 - d end
    return d
end

local function door_can_trigger(m)
    if m.health <= 0xFF or is_game_paused() then return false end
    if not gNetworkPlayers[0].currAreaSyncValid then return false end
    if m.skipWarpInteractionsTimer > 0 then return false end
    local a = m.action
    if (a & ACT_FLAG_INTANGIBLE) ~= 0 then return false end
    local g = a & ACT_GROUP_MASK
    return g ~= ACT_GROUP_CUTSCENE and g ~= ACT_GROUP_AUTOMATIC
end

local function door_message(d, stage, state)
    local stars = sgl_total_stars()
    if state == DOOR_LOCKED then
        djui_popup_create(string.format("\\#ff8080\\Locked!\\#dcdcdc\\ %s needs %d star%s (you have %d).",
            stage.name, stage.stars, stage.stars == 1 and "" or "s", stars), 2)
    else
        local name = stage and stage.name or "This stage"
        local need = stage and stage.stars or 0
        djui_popup_create(string.format("\\#ffd700\\%s\\#dcdcdc\\ is coming soon%s.", name,
            need > 0 and string.format(" (opens at %d stars)", need) or ""), 2)
    end
    play_sound(SOUND_MENU_CAMERA_BUZZ, gGlobalSoundSource)
end

-- the vanilla warp-object entry (interact_warp): Mario vanishes into the door and, 2 frames later,
-- level_trigger_warp(m, WARP_OP_WARP_OBJECT) reads warp node bparam2 = 0x10 + door from m.usedObj
local function door_enter(m, o)
    m.interactObj = o
    m.usedObj = o
    play_sound(SOUND_MENU_ENTER_HOLE, m.marioObj.header.gfx.cameraToObject)
    mario_stop_riding_object(m)
    set_mario_action(m, ACT_DISAPPEARED, (WARP_OP_WARP_OBJECT << 16) + 2)
end

local function door_fx_init(o)
    o.oFlags = OBJ_FLAG_UPDATE_GFX_POS_AND_ANGLE
    obj_set_billboard(o)
    obj_scale(o, DOOR_FLAME_SCALE)
    o.oIntangibleTimer = -1
    o.oDrawingDistance = DOOR_DRAW_DISTANCE
end

local function door_fx_loop(o)
    o.oAnimState = o.oAnimState + 1
end

id_bhvSglDoorFx = hook_behavior(nil, OBJ_LIST_DEFAULT, true, door_fx_init, door_fx_loop, "bhvSglDoorFx")

local function door_spawn_fx(d)
    local s, c = sins(d.yaw), coss(d.yaw)
    local fx = {}
    for _, side in ipairs({ -1, 1 }) do
        local off = d.halfWidth + DOOR_FLAME_SIDE
        local x = d.x + s * DOOR_FLAME_OUT + c * off * side
        local z = d.z + c * DOOR_FLAME_OUT - s * off * side
        local f = spawn_non_sync_object(id_bhvSglDoorFx, E_MODEL_RED_FLAME, x, d.y + DOOR_FLAME_UP, z, nil)
        if f ~= nil then table.insert(fx, f) end
    end
    return fx
end

local function door_init(o)
    o.oFlags = OBJ_FLAG_UPDATE_GFX_POS_AND_ANGLE
    o.oIntangibleTimer = -1
    o.oDrawingDistance = DOOR_DRAW_DISTANCE
    local i = (o.oBehParams >> 24) & 0xFF
    local hw = ((o.oBehParams >> 8) & 0xFF) * 10
    if hw <= 0 then hw = DOOR_HALF_WIDTH end
    local up = (o.oBehParams & 0xFF) * 10
    if up <= 0 then up = DOOR_EMBLEM_UP end
    local d = { x = o.oPosX, y = o.oPosY, z = o.oPosZ, yaw = o.oMoveAngleYaw, halfWidth = hw,
                state = nil, inside = false, told = false, fx = nil, seen = 0 }
    sDoors[i] = d
    -- the object itself is the emblem: lift it above the doorway, a little in front of the wall
    o.oPosX = d.x + sins(d.yaw) * DOOR_EMBLEM_OUT
    o.oPosY = d.y + up
    o.oPosZ = d.z + coss(d.yaw) * DOOR_EMBLEM_OUT
    obj_set_model_extended(o, E_MODEL_TRANSPARENT_STAR)
end

local function door_loop(o)
    local i = (o.oBehParams >> 24) & 0xFF
    local d = sDoors[i]
    if d == nil then return end
    local stage = sgl_stage_by_door(i)
    d.seen = get_global_timer()
    if d.fx == nil then d.fx = door_spawn_fx(d) end

    -- looks (lock state is re-evaluated every frame: stars can arrive while you stand there)
    local state = door_state(stage)
    if state ~= d.state then
        d.state = state
        obj_set_model_extended(o, state == DOOR_OPEN and E_MODEL_STAR or E_MODEL_TRANSPARENT_STAR)
    end
    for _, f in ipairs(d.fx) do
        -- (object slots are reused: only touch it while it is still one of our flames)
        local ours = obj_has_behavior_id(f, id_bhvSglDoorFx)   -- integer in v1.5.1 (accept a boolean too)
        if f.activeFlags ~= ACTIVE_FLAG_DEACTIVATED and (ours == true or ours == 1) then
            local flags = f.header.gfx.node.flags
            if state == DOOR_OPEN then
                f.header.gfx.node.flags = flags | GRAPH_RENDER_INVISIBLE
            else
                f.header.gfx.node.flags = flags & ~GRAPH_RENDER_INVISIBLE
            end
        end
    end
    o.oFaceAngleYaw = o.oFaceAngleYaw + 0x200

    -- local player in the doorway?
    local m = gMarioStates[0]
    local dx, dy, dz = m.pos.x - d.x, m.pos.y - d.y, m.pos.z - d.z
    local s, c = sins(d.yaw), coss(d.yaw)
    local fwd = dx * s + dz * c          -- > 0: outside, in front of the door
    local side = dx * c - dz * s
    local inside = fwd < DOOR_REACH_OUT and fwd > DOOR_REACH_IN and math.abs(side) < d.halfWidth
        and dy > DOOR_DY_MIN and dy < DOOR_DY_MAX
    if not inside then
        if fwd > DOOR_REARM or math.abs(side) > d.halfWidth + DOOR_REARM or math.abs(dy) > DOOR_REARM then
            d.told = false
        end
        d.inside = false
        return
    end
    d.inside = true
    if not door_can_trigger(m) or angle_diff(m.faceAngle.y, d.yaw + 0x8000) > DOOR_FACING then return end
    if state == DOOR_OPEN then
        door_enter(m, o)
    elseif not d.told then
        d.told = true
        door_message(d, stage, state)
    end
end

id_bhvSglDoor = hook_behavior(nil, OBJ_LIST_LEVEL, true, door_init, door_loop, "bhvSglDoor")

-- floating label over each door (within 25 m): stage name + open / locked / coming soon
local function door_hud()
    if gNetworkPlayers[0].currLevelNum ~= SGL_HUB_LEVEL or sgl_hud_blocked() then return end
    local now = get_global_timer()
    local m = gMarioStates[0]
    djui_hud_set_resolution(RESOLUTION_N64)
    djui_hud_set_font(FONT_NORMAL)
    local stars = sgl_total_stars()
    for i, d in pairs(sDoors) do
        if d.state ~= nil and now - d.seen <= 2 then
            local dx, dy, dz = m.pos.x - d.x, m.pos.y - d.y, m.pos.z - d.z
            local dist = math.sqrt(dx * dx + dy * dy + dz * dz)
            if dist < DOOR_LABEL_RANGE then
                local pos = { x = d.x + sins(d.yaw) * 60, y = d.y + DOOR_LABEL_UP, z = d.z + coss(d.yaw) * 60 }
                local out = { x = 0, y = 0, z = 0 }
                djui_hud_world_pos_to_screen_pos(pos, out)
                if out.z <= -260 then   -- in front of the camera (arena-hud convention)
                    local stage = sgl_stage_by_door(i)
                    local title = stage and stage.name or "?"
                    local line, r, g, b
                    if d.state == DOOR_OPEN then
                        line, r, g, b = "Walk in!", 140, 255, 140
                    elseif d.state == DOOR_LOCKED then
                        line, r, g, b = string.format("LOCKED - %d stars (you have %d)", stage.stars, stars), 255, 120, 120
                    else
                        line, r, g, b = "Coming soon", 200, 200, 200
                    end
                    local alpha = math.floor(255 * math.min(1, (DOOR_LABEL_RANGE - dist) / 600))
                    local scale = math.max(0.25, math.min(0.6, 900 / math.max(dist, 1)))
                    for k, text in ipairs({ title, line }) do
                        local sc = k == 1 and scale or scale * 0.8
                        local w = djui_hud_measure_text(text) * sc
                        local x, y = out.x - w / 2, out.y + (k - 1) * 34 * scale
                        djui_hud_set_color(0, 0, 0, math.floor(alpha * 0.7))
                        djui_hud_print_text(text, x + 1, y + 1, sc)
                        if k == 1 then
                            djui_hud_set_color(255, 215, 0, alpha)
                        else
                            djui_hud_set_color(r, g, b, alpha)
                        end
                        djui_hud_print_text(text, x, y, sc)
                    end
                end
            end
        end
    end
end

---------------------------------------------------------------------------------------------
-- custom (non-vanilla) test level
---------------------------------------------------------------------------------------------

-- key -> level_register arguments. reach: acoustic reach (sound falloff distance).
SGL_LEVEL_DEFS = {
    { key = "test", entry = "level_sgl_test_entry", name = "SGL Test Field", short = "sgltest",
      course = COURSE_NONE, reach = 28000, echo = 0x08 },
}

SGL_LEVELS = {}          -- key -> level number (0 when the .lvl was not compiled/found)
for _, def in ipairs(SGL_LEVEL_DEFS) do
    local num = level_register(def.entry, def.course, def.name, def.short, def.reach, def.echo, def.echo, def.echo)
    SGL_LEVELS[def.key] = num
    if num == nil or num == 0 then
        log_to_console("[SGL] level_register failed for " .. def.entry .. " (is levels/" .. def.entry .. ".lvl compiled?)", CONSOLE_MESSAGE_ERROR)
    end
end
LEVEL_SGL_TEST = SGL_LEVELS.test

local function level_ok(num)
    return num ~= nil and num ~= 0
end

-- sgl_test's level script can only name vanilla levels in its WARP_NODEs (custom level numbers exist
-- at runtime only), so its exits point at Castle Inside: send them to the hub Plaza instead
local function on_before_warp(destLevel, destArea, destWarpNode, arg)
    if level_ok(LEVEL_SGL_TEST) and gNetworkPlayers[0].currLevelNum == LEVEL_SGL_TEST and destLevel == LEVEL_CASTLE then
        return { destLevel = SGL_HUB_LEVEL, destArea = 1, destWarpNode = SGL_NODE_SPAWN }
    end
end

---------------------------------------------------------------------------------------------
-- lives (the Star Road idea: no harsh game overs): every session starts with SGL_LIVES, and the hub
-- tops them back up (once a death exit has landed and taken its life). A game over therefore only
-- happens after losing them all inside one stage visit, and it just returns you to the Plaza.
---------------------------------------------------------------------------------------------
SGL_LIVES = 4
local sLivesInit = false

local function lives_mario_update(m)
    if m.playerIndex ~= 0 then return end
    if not sLivesInit then
        sLivesInit = true
        if m.numLives < SGL_LIVES then m.numLives = SGL_LIVES end
    end
    if m.numLives < SGL_LIVES and gNetworkPlayers[0].currLevelNum == SGL_HUB_LEVEL
        and (m.action & ACT_GROUP_MASK) ~= ACT_GROUP_CUTSCENE then
        m.numLives = SGL_LIVES
    end
end

---------------------------------------------------------------------------------------------
-- draw distance: the GEO far clip is the s16 maximum (327 m), so Century Tower would be cut off
-- from the north end of the Plaza. In the hub and in our stages the projection far plane is
-- SGL_FAR_UNITS (build_stage.py fits the fog to exactly this value: fog starts at 200 m and is full
-- at 1000 m). Restored (0 = the level's own far clip) everywhere else.
---------------------------------------------------------------------------------------------
SGL_FAR_UNITS = 100000
local sFarOverridden = false

local function sgl_far_level(levelNum)
    if levelNum == SGL_HUB_LEVEL then return sgl_hub_ready() end
    local stage = sgl_stage_by_level(levelNum)
    return stage ~= nil and sgl_stage_ready(stage)
end

local function far_update()
    if sgl_far_level(gNetworkPlayers[0].currLevelNum) then
        set_override_far(SGL_FAR_UNITS)   -- every frame: cheap, and survives anything resetting it
        sFarOverridden = true
    elseif sFarOverridden then
        set_override_far(0)
        sFarOverridden = false
    end
end

---------------------------------------------------------------------------------------------
-- level init
---------------------------------------------------------------------------------------------
local sHubWelcomed = false
local sHubWarned = false

---------------------------------------------------------------------------------------------
-- hub hint: where to go next. Waits until nothing covers the screen for SGL_HUB_HINT_CALM frames (the
-- first-spawn character menu opens ~1 s after landing and would hide it), then shows the welcome popup
-- (first hub visit of the session) and, for SGL_HUB_HINT_FRAMES, a "NEXT" panel + marker on the door of
-- the next stage: the first built, open stage (door order) whose course still has a playable act
-- without its star.
---------------------------------------------------------------------------------------------
SGL_HUB_HINT_CALM = 45
SGL_HUB_HINT_FRAMES = 600
local sHubHint = nil     -- { calm, age (nil until shown) } for the current hub visit

-- "UNIVERSITY AUDITORIUM" -> "University Auditorium"
local function title_case(text)
    return ((text or ""):lower():gsub("(%a)([%w']*)", function(a, b) return a:upper() .. b end))
end

function sgl_next_stage()
    local stars = sgl_total_stars()
    for _, stage in ipairs(SGL_STAGES) do
        if sgl_stage_ready(stage) and stars >= stage.stars and stage.acts ~= nil then
            local flags = sgl_stage_star_flags(stage)
            for k = 1, 6 do
                if not sgl_act_is_soon(stage, k) and (flags & (1 << (k - 1))) == 0 then return stage end
            end
        end
    end
    return nil
end

local function hub_hint_update()
    local h = sHubHint
    if h == nil then return end
    if gNetworkPlayers[0].currLevelNum ~= SGL_HUB_LEVEL then
        sHubHint = nil
        return
    end
    if h.age ~= nil then
        h.age = h.age + 1
        if h.age >= SGL_HUB_HINT_FRAMES then sHubHint = nil end
        return
    end
    local m = gMarioStates[0]
    if sgl_hud_blocked() or (m.action & ACT_GROUP_MASK) == ACT_GROUP_CUTSCENE then
        h.calm = 0
        return
    end
    h.calm = h.calm + 1
    if h.calm < SGL_HUB_HINT_CALM then return end
    h.age = 0
    if not sHubWelcomed then
        sHubWelcomed = true
        local nxt = sgl_next_stage()
        if nxt ~= nil then
            djui_popup_create("\\#ffd700\\University of Florida\\#dcdcdc\\\nWalk into the " .. title_case(nxt.building)
                .. " door to enter " .. nxt.name .. "!", 2)
        else
            djui_popup_create("\\#ffd700\\University of Florida\\#dcdcdc\\\nWelcome back to campus!", 2)
        end
    end
end

local function hub_hint_hud()
    local h = sHubHint
    if h == nil or h.age == nil or sgl_hud_blocked() then return end
    local stage = sgl_next_stage()
    if stage == nil then return end
    local d = sDoors[stage.door]
    local alpha = sgl_hud_fade(h.age, SGL_HUB_HINT_FRAMES, 10, 40)
    if alpha <= 0 then return end
    sgl_hud_panel({ { "NEXT: " .. stage.name, SGL_HUD_GOLD, 0.34 },
        { (stage.building or "its") .. " door - walk in!", SGL_HUD_WHITE, 0.28 } })
    if d ~= nil then
        local m = gMarioStates[0]
        local dx, dz = m.pos.x - d.x, m.pos.z - d.z
        if dx * dx + dz * dz > DOOR_LABEL_RANGE * DOOR_LABEL_RANGE then   -- near the door its own label takes over
            sgl_hud_marker({ x = d.x, y = d.y + DOOR_LABEL_UP, z = d.z }, stage.name, SGL_HUD_GOLD, m)
        end
    end
end

local function on_level_init()
    far_update()
    local cur = gNetworkPlayers[0].currLevelNum
    if cur == SGL_HUB_LEVEL then
        refresh_door_signs()
        if not sgl_hub_ready() and not sHubWarned then
            sHubWarned = true
            djui_chat_message_create("\\#ffa0a0\\[SGL] The campus hub did not load: levels/castle_grounds was not "
                .. "compiled (check the console for DynOS errors). This is vanilla Castle Grounds.")
        elseif sgl_hub_ready() then
            sHubHint = { calm = 0, age = nil }
        end
    elseif level_ok(LEVEL_SGL_TEST) and cur == LEVEL_SGL_TEST then
        djui_popup_create("\\#ffd700\\SGL Test Field\\#dcdcdc\\ - true scale, 1 m = 100 units", 2)
    end
end

---------------------------------------------------------------------------------------------
-- /campus command
---------------------------------------------------------------------------------------------

-- map metres of a level's origin (stages.json centre: map x = game X / 100 + cx, y = -Z / 100 + cy)
SGL_MAP_CENTERS = {
    [LEVEL_CASTLE_GROUNDS] = { -45, 98 },
    [LEVEL_BOB] = { -580, 160 },      -- The Swamp (stages.json swamp window centre; data/uf/swamp_points.json map_m)
}

local function warp_hub()
    -- act 0, like every normal arrival in the hub (coopdx puts players of different acts in
    -- different instances of a level)
    return warp_to_level(SGL_HUB_LEVEL, 1, 0)
end

local function warp_key(key, act)
    if key == "hub" then return warp_hub() end
    if key == "test" then
        if not level_ok(LEVEL_SGL_TEST) then
            djui_chat_message_create("\\#ffa0a0\\[SGL] sgl_test is not loaded (check the console for DynOS errors).")
            return false
        end
        return warp_to_level(LEVEL_SGL_TEST, 1, 1)
    end
    local stage = sgl_stage_by_key(key)
    if stage == nil then return false end
    if not sgl_stage_ready(stage) then
        djui_chat_message_create("\\#ffa0a0\\[SGL] " .. stage.name .. " is not built yet (levels/" .. stage.slot .. ").")
        return false
    end
    return warp_to_level(stage.level, 1, act or 1)
end

-- moving EVERYONE is for the host (or a moderator): a friend's stray "/campus swamp 3" would otherwise
-- drag the whole group into another act, past the door locks and the act select
local function can_move_everyone()
    return network_is_server() or network_is_moderator()
end

local function sender_is_host(gi)
    for i = 1, MAX_PLAYERS - 1 do
        local np = gNetworkPlayers[i]
        if np ~= nil and np.connected and np.globalIndex == gi then return np.type == NPT_SERVER end
    end
    return false
end

local function on_packet_receive(data)
    if data.sgl ~= "warp" then return end
    if not (sender_is_host(data.gi) or data.mod == true) then return end
    warp_key(data.key, data.act)
end

local function list_levels()
    local parts = { "hub(castle_grounds)=" .. (sgl_hub_ready() and "ours" or "VANILLA") }
    for _, s in ipairs(SGL_STAGES) do
        table.insert(parts, string.format("%s(%s, door %d, %d*)=%s", s.key, s.slot, s.door, s.stars,
            sgl_stage_ready(s) and "ours" or "vanilla"))
    end
    table.insert(parts, "test=" .. (level_ok(LEVEL_SGL_TEST) and tostring(LEVEL_SGL_TEST) or "MISSING"))
    return table.concat(parts, ", ")
end

local function campus_usage()
    local keys = { "hub", "back", "test" }
    for _, s in ipairs(SGL_STAGES) do table.insert(keys, s.key) end
    djui_chat_message_create("/campus \\#00ffff\\where | list | " .. table.concat(keys, " | ")
        .. "\\#dcdcdc\\  (stages take an act: /campus swamp 2; add \"me\" to warp only yourself; only the host moves everyone)")
end

local function on_campus_command(msg)
    local args = {}
    for w in string.gmatch(msg or "", "%S+") do table.insert(args, w:lower()) end
    local sub = args[1] or ""

    if sub == "where" then
        local m = gMarioStates[0]
        local np = gNetworkPlayers[0]
        djui_chat_message_create(string.format("[SGL] level %d area %d act %d  x %d  y %d  z %d  (%.1f m east, %.1f m up, %.1f m south)",
            np.currLevelNum, np.currAreaIndex, np.currActNum, math.floor(m.pos.x), math.floor(m.pos.y), math.floor(m.pos.z),
            m.pos.x / 100, m.pos.y / 100, m.pos.z / 100))
        local c = SGL_MAP_CENTERS[np.currLevelNum]
        if c ~= nil then
            djui_chat_message_create(string.format("[SGL] campus map: %.1f m east, %.1f m north of Century Tower",
                m.pos.x / 100 + c[1], -m.pos.z / 100 + c[2]))
        end
        return true
    elseif sub == "list" then
        djui_chat_message_create("[SGL] levels: " .. list_levels())
        djui_chat_message_create(string.format("[SGL] stars %d, lives %d", sgl_total_stars(), gMarioStates[0].numLives))
        return true
    end

    local key = sub == "back" and "hub" or sub
    if key == "hub" or key == "test" or sgl_stage_by_key(key) ~= nil then
        local act, onlyMe = nil, false
        for k = 2, #args do
            if args[k] == "me" then
                onlyMe = true
            elseif tonumber(args[k]) ~= nil then
                act = math.max(1, math.min(6, math.floor(tonumber(args[k]))))
            end
        end
        local stage = sgl_stage_by_key(key)
        if stage ~= nil and not sgl_stage_ready(stage) then
            djui_chat_message_create("\\#ffa0a0\\[SGL] " .. stage.name .. " is not built yet (levels/" .. stage.slot .. ").")
            return true
        end
        if not onlyMe and not can_move_everyone() then
            onlyMe = true
            djui_chat_message_create("[SGL] Only the host moves everyone; warping just you.")
        end
        if not onlyMe then
            network_send(true, { sgl = "warp", key = key, act = act, gi = gNetworkPlayers[0].globalIndex,
                                 mod = network_is_moderator() and not network_is_server() })
        end
        if warp_key(key, act) then
            djui_chat_message_create("[SGL] warping " .. (onlyMe and "you" or "everyone") .. " to " .. key
                .. (act and (" act " .. act) or ""))
        end
        return true
    end
    campus_usage()
    return true
end

hook_event(HOOK_BEFORE_WARP, on_before_warp)
hook_event(HOOK_ON_LEVEL_INIT, on_level_init)
hook_event(HOOK_ON_PACKET_RECEIVE, on_packet_receive)
hook_event(HOOK_UPDATE, far_update)
hook_event(HOOK_MARIO_UPDATE, lives_mario_update)
hook_event(HOOK_ON_HUD_RENDER, door_hud)
hook_event(HOOK_UPDATE, hub_hint_update)
hook_event(HOOK_ON_HUD_RENDER, hub_hint_hud)
hook_chat_command("campus", "where | list | hub | back | test | swamp [act] [me] - Super Gatorlator 64 levels", on_campus_command)
