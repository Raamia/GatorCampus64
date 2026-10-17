-- Local-first score outbox for the DeepSpace bridge.
--
-- The game engine has no HTTP client in this mod API. Persist compact TSV-like rows in ModFS; a
-- separate local bridge can watch the saved .modfs archive and submit them with the player's
-- authenticated DeepSpace session. Gameplay never waits for that bridge or a network connection.

SGL_DS_GAME_VERSION = "0.1.0"
SGL_DS_OUTBOX_FILE = "pending_runs.txt"

local function safe_field(value)
    return type(value) == "string" and value:match("^[A-Za-z0-9_.+-]+$") ~= nil
end

function sgl_deepspace_new_run_id()
    local sequence = mod_storage_load_integer("sgl_ds_run_sequence", 0) + 1
    mod_storage_save_integer("sgl_ds_run_sequence", sequence)
    return string.format("sgl_%d_%d", get_global_timer(), sequence)
end

function sgl_deepspace_queue_run(run)
    if type(run) ~= "table" or not safe_field(run.runId) or not safe_field(run.missionId) then return false end
    if type(run.elapsedFrames) ~= "number" or run.elapsedFrames < 1 then return false end
    if type(run.retries) ~= "number" or run.retries < 0 then return false end

    local fs = mod_fs_get() or mod_fs_create()
    if fs == nil then
        log_to_console("[SGL] Could not open ModFS; this run stays local-only.", CONSOLE_MESSAGE_WARNING)
        return false
    end

    local file = fs:get_file(SGL_DS_OUTBOX_FILE) or fs:create_file(SGL_DS_OUTBOX_FILE, true)
    if file == nil then
        log_to_console("[SGL] Could not open the DeepSpace run outbox.", CONSOLE_MESSAGE_WARNING)
        return false
    end
    file:set_text_mode(true)
    if not file:seek(0, FILE_SEEK_END) then return false end
    local assisted = run.assisted and "1" or "0"
    local line = string.format("%s|%s|%d|%d|%s|%s", run.runId, run.missionId,
        math.floor(run.elapsedFrames), math.floor(run.retries), assisted, SGL_DS_GAME_VERSION)
    if not file:write_line(line) then return false end
    if not fs:save() then return false end
    return true
end

local BOARD_LIST = {
    { label = "Reitz rooftop", missionId = "reitz_rooftop" },
    { label = "Marston climb", missionId = "marston_climb" },
    { label = "Stadium Stair Sprint", missionId = "swamp_sprint" },
    { label = "Skybox Climb", missionId = "swamp_skybox" },
}

-- The menu opens from the engine Mods screen. Wait for that screen to close and
-- for the closing button to be released before taking controller input.
local sLeaderboardMenu = nil
local sLeaderboardCursor = 1
local sLeaderboardArmed = false
local sLeaderboardRepeat = 0
local sLeaderboardDirection = 0
local sLeaderboardBoard = nil

local function leaderboard_is_paused()
    return (djui_hud_is_pause_menu_created ~= nil and djui_hud_is_pause_menu_created())
        or (is_game_paused ~= nil and is_game_paused())
end

local function open_leaderboard_menu()
    sLeaderboardMenu = "list"
    sLeaderboardCursor = 1
    sLeaderboardArmed = false
    sLeaderboardRepeat = 0
    sLeaderboardDirection = 0
    sLeaderboardBoard = nil
end

local function load_cached_board(board)
    local prefix = "sgl_ds_lb_" .. board.missionId .. "_"
    local count = mod_storage_load_integer(prefix .. "count", 0)
    local entries = {}
    for rank = 1, math.min(count, 5) do
        local entry = mod_storage_load(prefix .. rank)
        local tag, frames, retries
        if type(entry) == "string" then
            tag, frames, retries = entry:match("^([^|]+)|(%d+)|(%d+)$")
        end
        if tag ~= nil then
            table.insert(entries, { tag = tag, frames = tonumber(frames), retries = tonumber(retries) })
        end
    end
    return { label = string.upper(board.label), entries = entries }
end

local function leaderboard_time(frames)
    local tenths = math.floor(frames / 3)
    local seconds = tenths // 10
    local minutes = seconds // 60
    return string.format("%dM%02d.%dS", minutes, seconds % 60, tenths % 10)
end

local function move_leaderboard_cursor(direction)
    sLeaderboardCursor = sLeaderboardCursor + direction
    if sLeaderboardCursor < 1 then sLeaderboardCursor = #BOARD_LIST end
    if sLeaderboardCursor > #BOARD_LIST then sLeaderboardCursor = 1 end
end

local function eat_leaderboard_input(c)
    c.buttonPressed = 0
    c.buttonDown = 0
    c.stickX = 0
    c.stickY = 0
    c.stickMag = 0
    c.rawStickX = 0
    c.rawStickY = 0
    c.extStickX = 0
    c.extStickY = 0
end

local function leaderboard_controller_idle(c)
    return c.buttonDown == 0 and c.buttonPressed == 0
        and math.abs(c.stickX or 0) < 10 and math.abs(c.stickY or 0) < 10
end

local function leaderboard_input(c)
    if not sLeaderboardArmed then
        if leaderboard_controller_idle(c) then sLeaderboardArmed = true end
        return
    end

    local pressed = c.buttonPressed
    local held = c.buttonDown
    local vertical = 0
    if ((pressed | held) & U_JPAD) ~= 0 or (c.stickY or 0) > 60 then vertical = -1 end
    if ((pressed | held) & D_JPAD) ~= 0 or (c.stickY or 0) < -60 then vertical = 1 end
    if vertical ~= 0 then
        if vertical ~= sLeaderboardDirection or sLeaderboardRepeat <= 0 then
            move_leaderboard_cursor(vertical)
            sLeaderboardRepeat = 8
        else
            sLeaderboardRepeat = sLeaderboardRepeat - 1
        end
        sLeaderboardDirection = vertical
    else
        sLeaderboardDirection = 0
        sLeaderboardRepeat = sLeaderboardRepeat - 1
    end

    if (pressed & B_BUTTON) ~= 0 then
        if sLeaderboardMenu == "board" then
            sLeaderboardMenu = "list"
        else
            sLeaderboardMenu = nil
        end
    elseif (pressed & START_BUTTON) ~= 0 then
        sLeaderboardMenu = nil
    elseif (pressed & A_BUTTON) ~= 0 and sLeaderboardMenu == "list" then
        sLeaderboardMenu = "board"
        sLeaderboardBoard = load_cached_board(BOARD_LIST[sLeaderboardCursor])
    end
end

local function on_leaderboard_before_mario_update(m)
    if m.playerIndex ~= 0 or sLeaderboardMenu == nil then return end
    if not leaderboard_is_paused() then leaderboard_input(m.controller) end
    -- Keep movement and pause from leaking through while the custom menu is open.
    if not leaderboard_is_paused() then eat_leaderboard_input(m.controller) end
end

local function on_leaderboard_update()
    if sLeaderboardMenu == nil or leaderboard_is_paused() then return end
    local m = gMarioStates ~= nil and gMarioStates[0] or nil
    if m ~= nil and m.controller ~= nil and not sLeaderboardArmed then
        -- Catch the controller release even during frames where Mario isn't updated.
        if leaderboard_controller_idle(m.controller) then sLeaderboardArmed = true end
    end
end

local function draw_leaderboard_menu()
    if sLeaderboardMenu == nil or leaderboard_is_paused() then return end
    djui_hud_set_resolution(RESOLUTION_N64)
    djui_hud_set_font(FONT_NORMAL)
    local sw, sh = djui_hud_get_screen_width(), djui_hud_get_screen_height()
    local panelW = math.min(244, sw - 24)
    local panelH = sLeaderboardMenu == "list" and 174 or 190
    local x, y = (sw - panelW) / 2, (sh - panelH) / 2

    -- Centered, full menu sheet using the same focus and button rhythm as CoopDX's menus.
    sgl_hud_rect(0, 0, sw, sh, 0, 0, 0, 112)
    sgl_hud_rect(x - 2, y - 2, panelW + 4, panelH + 4, 73, 154, 235, 255)
    sgl_hud_rect(x, y, panelW, panelH, 7, 17, 38, 248)
    sgl_hud_rect(x, y, panelW, 4, 250, 110, 30, 255)
    sgl_hud_text_center("CAMPUS LEADERBOARDS", sw / 2, y + 12, 0.31, { 255, 255, 255 }, 1)
    sgl_hud_rect(x + 12, y + 30, panelW - 24, 1, 76, 105, 143, 230)

    if sLeaderboardMenu == "list" then
        for i, board in ipairs(BOARD_LIST) do
            local rowY = y + 39 + (i - 1) * 24
            local selected = i == sLeaderboardCursor
            if selected then
                sgl_hud_rect(x + 10, rowY, panelW - 20, 21, 35, 73, 116, 255)
                sgl_hud_rect(x + 10, rowY, 3, 21, 250, 110, 30, 255)
            end
            sgl_hud_text_center(board.label, sw / 2, rowY + 4, 0.27,
                selected and { 255, 224, 160 } or { 220, 230, 244 }, 1)
        end
        sgl_hud_rect(x + 12, y + panelH - 29, panelW - 24, 1, 76, 105, 143, 230)
        sgl_hud_text_center("D-PAD: MOVE     A: OPEN     B: CLOSE", sw / 2, y + panelH - 20,
            0.19, { 155, 183, 216 }, 1)
    else
        local board = sLeaderboardBoard or { label = "GLOBAL BOARD", entries = {} }
        sgl_hud_text_center(board.label, sw / 2, y + 38, 0.28, { 255, 205, 70 }, 1)
        sgl_hud_rect(x + 12, y + 54, panelW - 24, 1, 76, 105, 143, 230)
        if #board.entries == 0 then
            sgl_hud_text_center("NO SCORES CACHED YET", sw / 2, y + 79, 0.25, { 220, 228, 240 }, 1)
            sgl_hud_text_center("Complete a run, then sync scores.", sw / 2, y + 98, 0.19,
                { 155, 174, 199 }, 1)
        else
            for rank, score in ipairs(board.entries) do
                local rowY = y + 61 + (rank - 1) * 19
                local medal = rank == 1 and { 255, 205, 70 }
                    or (rank == 2 and { 190, 210, 235 } or { 205, 145, 100 })
                sgl_hud_rect(x + 10, rowY, panelW - 20, 17,
                    rank == 1 and 55 or 14, rank == 1 and 48 or 29, rank == 1 and 29 or 52, 245)
                sgl_hud_rect(x + 10, rowY, 3, 17, medal[1], medal[2], medal[3], 255)
                local line = string.format("#%d  %s    %s   R%d", rank, score.tag,
                    leaderboard_time(score.frames), score.retries)
                local scale = math.min(0.22, (panelW - 38) / djui_hud_measure_text(line))
                sgl_hud_text(line, x + 18, rowY + 3, scale, medal, 1)
            end
        end
        sgl_hud_rect(x + 12, y + panelH - 29, panelW - 24, 1, 76, 105, 143, 230)
        sgl_hud_text_center("B: BOARDS     START: CLOSE", sw / 2, y + panelH - 20,
            0.20, { 155, 183, 216 }, 1)
    end
end

if hook_event ~= nil then
    if HOOK_ON_HUD_RENDER ~= nil then hook_event(HOOK_ON_HUD_RENDER, draw_leaderboard_menu) end
    if HOOK_BEFORE_MARIO_UPDATE ~= nil then hook_event(HOOK_BEFORE_MARIO_UPDATE, on_leaderboard_before_mario_update) end
    if HOOK_UPDATE ~= nil then hook_event(HOOK_UPDATE, on_leaderboard_update) end
end

if hook_mod_menu_button ~= nil then
    hook_mod_menu_button("Campus leaderboards", open_leaderboard_menu)
end
