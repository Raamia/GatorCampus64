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

local sLeaderboard = nil

local function show_cached_leaderboard(label, mission_id)
    local prefix = "sgl_ds_lb_" .. mission_id .. "_"
    local count = mod_storage_load_integer(prefix .. "count", 0)
    local entries = {}
    for rank = 1, math.min(count, 5) do
        local entry = mod_storage_load(prefix .. rank)
        local tag, frames, retries
        if type(entry) == "string" then
            tag, frames, retries = entry:match("^([^|]+)|(%d+)|(%d+)$")
        end
        if tag ~= nil then
            table.insert(entries, {
                tag = tag,
                frames = tonumber(frames),
                retries = tonumber(retries),
            })
        end
    end
    sLeaderboard = {
        label = string.upper(label),
        entries = entries,
        openedAt = get_global_timer(),
        duration = 360,
    }
end

local function leaderboard_time(frames)
    local tenths = math.floor(frames / 3)
    local seconds = tenths // 10
    local minutes = seconds // 60
    return string.format("%dM%02d.%dS", minutes, seconds % 60, tenths % 10)
end

local function render_cached_leaderboard()
    if sLeaderboard == nil then return end
    local age = get_global_timer() - sLeaderboard.openedAt
    if age >= sLeaderboard.duration then
        sLeaderboard = nil
        return
    end

    djui_hud_set_resolution(RESOLUTION_N64)
    djui_hud_set_font(FONT_NORMAL)
    local width = djui_hud_get_screen_width()
    -- The CoopDX Mods screen draws a wide dark sheet over the left ~3/4 of
    -- widescreen HUD space. Keep this card in the remaining right gutter so
    -- that screen can sit above it without hiding the heading or scores.
    local cardW = math.min(104, width - 16)
    local cardX = width - cardW - 4
    local cardY = 13
    local titleH = 34
    local rowH = 23
    local cardH = 8 + titleH + math.max(1, #sLeaderboard.entries) * rowH + 14

    -- Dark navy glass with a UF orange cap and a cool blue edge, instead of the
    -- engine's plain black popup. Keep the card compact so it reads beside the
    -- Mods menu on both 4:3 and widescreen layouts.
    sgl_hud_rect(cardX - 1, cardY - 1, cardW + 2, cardH + 2, 73, 154, 235, 230)
    sgl_hud_rect(cardX, cardY, cardW, cardH, 7, 17, 38, 238)
    sgl_hud_rect(cardX, cardY, cardW, 3, 250, 110, 30, 255)
    sgl_hud_rect(cardX + 7, cardY + 9, 2, 20, 90, 170, 255, 255)
    sgl_hud_text("GLOBAL BOARD", cardX + 13, cardY + 9, 0.20, { 142, 194, 255 }, 1)
    local labelScale = math.min(0.27, (cardW - 21) / djui_hud_measure_text(sLeaderboard.label))
    sgl_hud_text(sLeaderboard.label, cardX + 13, cardY + 19, labelScale, { 255, 255, 255 }, 1)
    sgl_hud_rect(cardX + 9, cardY + titleH, cardW - 18, 1, 76, 105, 143, 220)

    if #sLeaderboard.entries == 0 then
        sgl_hud_text("NO SCORES YET", cardX + 8, cardY + titleH + 8, 0.20, { 220, 228, 240 }, 1)
        sgl_hud_text("Finish + sync a run", cardX + 8, cardY + titleH + 19, 0.18, { 155, 174, 199 }, 1)
    else
        for rank, score in ipairs(sLeaderboard.entries) do
            local rowY = cardY + titleH + 3 + (rank - 1) * rowH
            local medal = rank == 1 and { 255, 205, 70 } or (rank == 2 and { 190, 210, 235 } or { 205, 145, 100 })
            local rowBg = rank == 1 and { 55, 48, 29 } or { 14, 29, 52 }
            sgl_hud_rect(cardX + 6, rowY, cardW - 12, 20, rowBg[1], rowBg[2], rowBg[3], 235)
            sgl_hud_rect(cardX + 6, rowY, 2, 20, medal[1], medal[2], medal[3], 255)
            local left = string.format("#%d %s", rank, score.tag)
            local timeLine = string.format("%s  RETRIES %d", leaderboard_time(score.frames), score.retries)
            local nameScale = math.min(0.19, (cardW - 21) / djui_hud_measure_text(left))
            local timeScale = math.min(0.19, (cardW - 21) / djui_hud_measure_text(timeLine))
            sgl_hud_text(left, cardX + 11, rowY + 2, nameScale, medal, 1)
            sgl_hud_text(timeLine, cardX + 11, rowY + 11, timeScale, { 238, 243, 250 }, 1)
        end
    end

    local footer = "DEEPSPACE SNAPSHOT"
    sgl_hud_text(footer, cardX + 7, cardY + cardH - 10, 0.17, { 137, 162, 194 }, 1)
end

if hook_event ~= nil and HOOK_ON_HUD_RENDER ~= nil then
    hook_event(HOOK_ON_HUD_RENDER, render_cached_leaderboard)
end

if hook_mod_menu_button ~= nil then
    hook_mod_menu_button("Reitz leaderboard", function()
        show_cached_leaderboard("Reitz", "reitz_rooftop")
    end)
    hook_mod_menu_button("Marston leaderboard", function()
        show_cached_leaderboard("Marston", "marston_climb")
    end)
    hook_mod_menu_button("Stadium leaderboard", function()
        show_cached_leaderboard("Stadium Stair Sprint", "swamp_sprint")
    end)
    hook_mod_menu_button("Skybox Climb leaderboard", function()
        show_cached_leaderboard("Skybox Climb", "swamp_skybox")
    end)
end
