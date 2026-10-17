-- Super Gatorlator 64: custom levels.
--
-- How custom levels work in sm64coopdx v1.5.1:
--   levels/<name>/            C sources from Fast64 (tools/blender/export_level.py), with a script.c
--   levels/level_<name>_entry.lvl  compiled by DynOS when the game starts (only C changes recompile)
--   level_register("level_<name>_entry", course, ...) below turns it into a level number (50+).
-- Custom levels are entered with warp_to_level / warp_to_warpnode (DynOS warps). Their level
-- scripts can only name VANILLA levels in WARP_NODEs, so their death/exit warp nodes point at the
-- castle and this file sends the player back into SGL levels instead (see on_before_warp).
--
-- Levels:
--   sgl_hub   UF campus hub (Plaza of the Americas + Century Tower), tools/campus/build_stage.py
--   sgl_test  pipeline test field, tools/blender/build_test_level.py
--
-- Players start on campus: whenever the local player is in a vanilla level (joining, the castle
-- after the intro, a game over, a vanilla death warp) they are warped to the hub, Arena-style.
-- /campus off turns that off for this session (e.g. to visit vanilla courses), /campus on back on.
--
-- Test: /campus hub   /campus test   (everyone; add "me" for just you)   /campus where
--       /campus list   /campus off | on   /campus back (= off + vanilla start level)

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
local function sign_bparam(text)
    local id = make_dialog(text)
    if id == nil or id < 0 or id > 0xFF then
        log_to_console("[SGL] dialog id " .. tostring(id) .. " does not fit a sign's behavior param", CONSOLE_MESSAGE_WARNING)
        id = DIALOG_000
    end
    return (id & 0xFF) << 16
end

-- signpost in sgl_test
SGL_TEST_SIGN_BPARAM = sign_bparam("SGL TEST FIELD\
Welcome, Gators! Everything\
here is built at true scale:\
1 metre = 100 game units.\
The field is 200 m wide,\
the tower is 10 m tall\
and the pool is 4 m deep.")

-- sgl_hub: welcome sign on the Plaza of the Americas (in front of the spawn point, which faces
-- south toward the University Auditorium and Century Tower)
SGL_HUB_SIGN_WELCOME = sign_bparam("PLAZA OF THE AMERICAS\
Welcome to the University\
of Florida, Gators!\
Every building is real\
and full size. Century\
Tower is straight ahead\
(south), behind the\
University Auditorium.\
Library West is behind\
you. Signposts like this\
one mark the doors that\
will lead to the stages.\
Climb the plaza oaks,\
the lamp posts and the\
building ledges.\
Go Gators!")

-- sgl_hub: one signpost next to every future stage door (tools/campus/stage_landmarks.py
-- DOOR_DEFAULTS; the generator names the bparam SGL_HUB_SIGN_<DOOR SLUG>)
local function door_sign(building, stage, stars)
    return sign_bparam(building .. "\
Stage door: " .. stage .. "\
Opens at " .. stars .. " star" .. (stars == 1 and "" or "s") .. ".\
Coming soon!")
end
SGL_HUB_SIGN_UNIVERSITY_AUDITORIUM = door_sign("UNIVERSITY AUDITORIUM", "THE SWAMP", 0)
SGL_HUB_SIGN_THE_HUB = door_sign("THE HUB", "REITZ UNION AND\
ENGINEERING", 2)
SGL_HUB_SIGN_MARSTON = door_sign("MARSTON SCIENCE LIBRARY", "MARSTON", 5)
SGL_HUB_SIGN_NEWELL_HALL = door_sign("NEWELL HALL", "LAKE ALICE", 8)
SGL_HUB_SIGN_LIBRARY_WEST = door_sign("LIBRARY WEST", "LIBRARY WEST\
AFTER DARK", 14)
SGL_HUB_SIGN_CENTURY_TOWER = door_sign("CENTURY TOWER", "CENTURY TOWER\
(INSIDE)", 20)
SGL_HUB_SIGN_SMATHERS = door_sign("SMATHERS LIBRARY", "SMATHERS STACKS\
SLIDE", 3)
-- second door at the Century Tower base (west face): the star door to the finale
SGL_HUB_SIGN_FINAL_EXAM = door_sign("FINAL EXAM DOOR", "FINALS WEEK\
ASCENT", 30)

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
-- level registry
---------------------------------------------------------------------------------------------

-- key -> level_register arguments. course: COURSE_NONE for hubs/tests; COURSE_BOB..COURSE_RR
-- for stages whose stars should save (stars land in that course's save slot).
-- reach: acoustic reach (sound falloff distance); the hub is 580 m across.
SGL_LEVEL_DEFS = {
    { key = "hub", entry = "level_sgl_hub_entry", name = "UF Campus", short = "sglhub",
      course = COURSE_NONE, reach = 32000, echo = 0x08 },
    { key = "test", entry = "level_sgl_test_entry", name = "SGL Test Field", short = "sgltest",
      course = COURSE_NONE, reach = 28000, echo = 0x08 },
}

SGL_LEVELS = {}         -- key -> level number (0 when the .lvl was not compiled/found)
local sSglLevelNums = {} -- level number -> def

for _, def in ipairs(SGL_LEVEL_DEFS) do
    local num = level_register(def.entry, def.course, def.name, def.short, def.reach, def.echo, def.echo, def.echo)
    SGL_LEVELS[def.key] = num
    if num ~= nil and num ~= 0 then
        sSglLevelNums[num] = def
    else
        log_to_console("[SGL] level_register failed for " .. def.entry .. " (is levels/" .. def.entry .. ".lvl compiled?)", CONSOLE_MESSAGE_ERROR)
    end
end
LEVEL_SGL_HUB = SGL_LEVELS.hub
LEVEL_SGL_TEST = SGL_LEVELS.test

function sgl_is_sgl_level(levelNum)
    return sSglLevelNums[levelNum] ~= nil
end

local function level_ok(num)
    return num ~= nil and num ~= 0
end

-- where a death / star exit / pause exit from an SGL level sends the player
local function sgl_return_level()
    if level_ok(SGL_LEVELS.hub) then return SGL_LEVELS.hub end
    return SGL_LEVELS.test
end

---------------------------------------------------------------------------------------------
-- warps
---------------------------------------------------------------------------------------------

local sReturnPending = nil -- level number we are sending the player back to

-- act 1, not 0: OBJECT_WITH_ACTS filters on 1 << (act - 1), and arena warps with act 1 too

local function warp_local(levelNum, area, act)
    if not level_ok(levelNum) then
        djui_chat_message_create("\\#ffa0a0\\[SGL] That level is not loaded (check the console for DynOS errors).")
        return false
    end
    if not warp_to_level(levelNum, area or 1, act or 1) then
        djui_chat_message_create("\\#ffa0a0\\[SGL] warp_to_level failed: the level has no 0x0A spawn in area " .. (area or 1))
        return false
    end
    return true
end

-- Death and star exits of SGL levels name vanilla castle warp nodes; turn them into a DynOS warp
-- back into an SGL level. DynOS cancels the pending vanilla warp when its own warp starts.
local function on_before_warp(destLevel, destArea, destWarpNode, arg)
    local np = gNetworkPlayers[0]
    if not sgl_is_sgl_level(np.currLevelNum) or sgl_is_sgl_level(destLevel) then return end
    local target = sgl_return_level()
    if not level_ok(target) then return end
    sReturnPending = target
    -- the spin-airborne spawn does not refill health like SM64's death-exit spawn does
    local m = gMarioStates[0]
    m.health, m.hurtCounter, m.healCounter = 0x880, 0, 0
    warp_to_level(target, 1, 1)
end

-- Fallback: if the vanilla exit still happened, bounce straight back.
local function on_warp_or_init()
    if sReturnPending == nil then return end
    local cur = gNetworkPlayers[0].currLevelNum
    local target = sReturnPending
    sReturnPending = nil
    gMarioStates[0].health = 0x880
    if cur ~= target and not sgl_is_sgl_level(cur) then
        warp_to_level(target, 1, 1)
    end
end

---------------------------------------------------------------------------------------------
-- start on campus (Arena-style): pull the local player into the hub from any vanilla level
---------------------------------------------------------------------------------------------

local AUTO_DELAY = 15        -- frames the vanilla level must be valid before we warp (0.5 s)
local AUTO_RETRY = 60        -- frames between attempts
local AUTO_MAX_TRIES = 5     -- attempts without arriving in an SGL level, then give up (and say so)

local sAutoCampus = true     -- /campus off|back disables it, /campus on|hub enables it
local sAutoTimer = 0
local sAutoFails = 0

local function auto_campus_update()
    if not sAutoCampus or not level_ok(SGL_LEVELS.hub) then return end
    local np = gNetworkPlayers[0]
    if sgl_is_sgl_level(np.currLevelNum) then
        sAutoTimer, sAutoFails = 0, 0
        return
    end
    -- wait for the level to be in sync, for our own return warp, and never during a warp fade
    if not np.currAreaSyncValid or sReturnPending ~= nil or gMarioStates[0].action == ACT_DISAPPEARED then
        sAutoTimer = 0
        return
    end
    sAutoTimer = sAutoTimer + 1
    if sAutoTimer < AUTO_DELAY then return end
    sAutoTimer = AUTO_DELAY - AUTO_RETRY
    -- every attempt counts (a warp that starts but never arrives must not loop); arriving in an
    -- SGL level resets the counter above
    sAutoFails = sAutoFails + 1
    if sAutoFails > AUTO_MAX_TRIES then
        sAutoCampus = false
        djui_chat_message_create("\\#ffa0a0\\[SGL] Could not warp to the campus hub; staying here. /campus hub to retry.")
        return
    end
    warp_to_level(SGL_LEVELS.hub, 1, 1)
end

-- SGL levels use SM64's collision bug fixes (arena and star-road enable them globally);
-- vanilla levels keep the default so the rest of the game is unchanged.
local sDefaultFixCollisionBugs = gLevelValues.fixCollisionBugs
local sHubWelcomed = false

---------------------------------------------------------------------------------------------
-- hub draw distance: the level's GEO far clip is the s16 maximum (327 m), so Century Tower would
-- be cut off from the north end of the Plaza. While in the hub the projection far plane is
-- SGL_HUB_FAR_UNITS (tools/campus/build_stage.py fits the fog to exactly this value: fog starts at
-- 200 m and is full at 1000 m). Restored (0 = the level's own far clip) when leaving.
---------------------------------------------------------------------------------------------

SGL_HUB_FAR_UNITS = 100000
local sFarOverridden = false

local function hub_far_update()
    if gNetworkPlayers[0].currLevelNum == LEVEL_SGL_HUB and level_ok(LEVEL_SGL_HUB) then
        set_override_far(SGL_HUB_FAR_UNITS)   -- every frame: cheap, and survives anything resetting it
        sFarOverridden = true
    elseif sFarOverridden then
        set_override_far(0)
        sFarOverridden = false
    end
end

local function on_level_init()
    on_warp_or_init()
    hub_far_update()
    local cur = gNetworkPlayers[0].currLevelNum
    gLevelValues.fixCollisionBugs = sgl_is_sgl_level(cur) and 1 or sDefaultFixCollisionBugs
    if cur == LEVEL_SGL_TEST then
        djui_popup_create("\\#ffd700\\SGL Test Field\\#dcdcdc\\ - true scale, 1 m = 100 units", 2)
    elseif cur == LEVEL_SGL_HUB and level_ok(LEVEL_SGL_HUB) then
        if not sHubWelcomed then
            sHubWelcomed = true
            djui_popup_create("\\#ffd700\\University of Florida\\#dcdcdc\\\nPlaza of the Americas - read the sign!", 2)
        end
    end
end

local function on_packet_receive(data)
    if data.sgl ~= "warp" then return end
    local num = SGL_LEVELS[data.key]
    if level_ok(num) and gNetworkPlayers[0].currLevelNum ~= num then
        if data.key == "hub" then sAutoCampus = true end
        warp_local(num, 1, 1)
    end
end

---------------------------------------------------------------------------------------------
-- /campus command
---------------------------------------------------------------------------------------------

local function list_levels()
    local parts = {}
    for _, def in ipairs(SGL_LEVEL_DEFS) do
        local num = SGL_LEVELS[def.key]
        table.insert(parts, def.key .. "=" .. (level_ok(num) and tostring(num) or "MISSING"))
    end
    return table.concat(parts, ", ") .. "  (auto-campus " .. (sAutoCampus and "on" or "off") .. ")"
end

local function on_campus_command(msg)
    local args = {}
    for w in string.gmatch(msg or "", "%S+") do table.insert(args, w:lower()) end
    local sub = args[1] or ""

    if sub == "where" then
        local m = gMarioStates[0]
        local np = gNetworkPlayers[0]
        -- game units; for sgl_hub the map position is east = x/100 - 45, north = -z/100 + 98 (m)
        djui_chat_message_create(string.format("[SGL] level %d area %d  x %.1f m  z %.1f m  up %.1f m",
            np.currLevelNum, np.currAreaIndex, m.pos.x / 100, m.pos.z / 100, m.pos.y / 100))
        if np.currLevelNum == LEVEL_SGL_HUB then
            djui_chat_message_create(string.format("[SGL] campus map: %.1f m east, %.1f m north of Century Tower",
                m.pos.x / 100 - 45, -m.pos.z / 100 + 98))
        end
        return true
    elseif sub == "list" then
        djui_chat_message_create("[SGL] levels: " .. list_levels())
        return true
    elseif sub == "off" or sub == "back" then
        sAutoCampus = false
        djui_chat_message_create("[SGL] auto-warp to campus off for this session (/campus on to undo)")
        if sub == "back" then warp_to_start_level() end
        return true
    elseif sub == "on" then
        sAutoCampus = true
        sAutoTimer, sAutoFails = 0, 0
        djui_chat_message_create("[SGL] auto-warp to campus on")
        return true
    elseif SGL_LEVELS[sub] ~= nil then
        local num = SGL_LEVELS[sub]
        if sub == "hub" then
            sAutoCampus = true
            sAutoFails = 0
        end
        if args[2] ~= "me" then
            network_send(true, { sgl = "warp", key = sub })
        end
        if warp_local(num, 1, 1) then
            djui_chat_message_create("[SGL] warping " .. (args[2] == "me" and "you" or "everyone") .. " to " .. sub)
        end
        return true
    end
    djui_chat_message_create("/campus \\#00ffff\\[" .. table.concat((function()
        local keys = {}
        for _, def in ipairs(SGL_LEVEL_DEFS) do table.insert(keys, def.key) end
        return keys
    end)(), "|") .. "] [me]\\#dcdcdc\\ | where | list | on | off | back")
    return true
end

hook_event(HOOK_BEFORE_WARP, on_before_warp)
hook_event(HOOK_ON_WARP, on_warp_or_init)
hook_event(HOOK_ON_LEVEL_INIT, on_level_init)
hook_event(HOOK_ON_PACKET_RECEIVE, on_packet_receive)
hook_event(HOOK_UPDATE, auto_campus_update)
hook_event(HOOK_UPDATE, hub_far_update)
hook_chat_command("campus", "[hub|test] [me] | where | list | on | off | back - Super Gatorlator 64 levels", on_campus_command)
