-- Local-first score outbox for the DeepSpace bridge, and the in-game leaderboard menu.
--
-- The game engine has no HTTP client in this mod API. Persist compact TSV-like rows in ModFS; a
-- separate local bridge can watch the saved .modfs archive and submit them with the player's
-- authenticated DeepSpace session. Gameplay never waits for that bridge or a network connection.
--
-- The outbox is written on players' machines only, never on a headless dedicated host: a mod has ONE
-- ModFS archive (<savepath>/sav/sgl64.modfs) and mod_fs_save() rewrites all of it, while on the host
-- server/bridge replaces that same archive with its inbox (inbox.json). Clients' archives are never
-- touched by server/bridge, so pending_runs.txt keeps its name (companion/native-bridge reads it).
--
-- Leaderboards (docs/web_platform_spec.md 10.3): on a hosted server the bridge sends a "leaderboard"
-- inbox command per mission {mission, n, name1, frames1, ... name5, frames5, at}; the menu shows those
-- rows (LIVE, with their age) for every mission that has them. Without them (offline, or a mission the
-- server has not sent yet) a board falls back to the .sav snapshot companion/native-bridge writes
-- (mod_storage keys sgl_ds_lb_<mission>_count / _<rank> = "tag|frames|retries").

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

-- this process is a headless dedicated host (server/bridge owns its ModFS archive)
local function headless_host()
    local hs = gServerSettings.headlessServer
    return network_is_server() and hs ~= nil and hs ~= 0 and hs ~= false
end

function sgl_deepspace_queue_run(run)
    if headless_host() then return false end
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

-- the offline boards (the .sav snapshot covers these); live boards for other missions are added after them
local BOARD_LIST = {
    { label = "Reitz rooftop", missionId = "reitz_rooftop" },
    { label = "Marston climb", missionId = "marston_climb" },
    { label = "Stadium Stair Sprint", missionId = "swamp_sprint" },
    { label = "Skybox Climb", missionId = "swamp_skybox" },
}
SGL_DS_BOARD_ROWS = 5
SGL_DS_LIST_ROWS = 4            -- rows visible in the board list (it scrolls when there are more)

---------------------------------------------------------------------------------------------
-- live boards from the hosted server (inbox command "leaderboard", routed by sgl_bridge.lua)
---------------------------------------------------------------------------------------------
local sLiveBoards = {}          -- [mission id] = { rows = { { name, frames } }, at = unix time or nil }

local function clean_name(s)
    s = s:gsub("\\#%x+\\", ""):gsub("[%c]", "")      -- coopdx colour codes, control bytes
    if #s > 40 then s = s:sub(1, 39) .. "." end
    return s
end

function sgl_deepspace_on_leaderboard(f)
    if type(f) ~= "table" or type(f.mission) ~= "string" or #f.mission > 64
        or not f.mission:match("^[%w_.+-]+$") then return false end
    local n = type(f.n) == "number" and math.floor(f.n) or 0
    local rows = {}
    for i = 1, math.max(0, math.min(SGL_DS_BOARD_ROWS, n)) do
        local name, frames = f["name" .. i], f["frames" .. i]
        if type(name) == "string" and type(frames) == "number" and frames >= 1 then
            rows[#rows + 1] = { name = clean_name(name), frames = math.floor(frames) }
        end
    end
    sLiveBoards[f.mission] = { rows = rows, at = type(f.at) == "number" and math.floor(f.at) or nil }
    return true
end

function sgl_deepspace_live_board(missionId) return sLiveBoards[missionId] end

-- sgl_bridge.lua loads first (strcmp order); its globals live in this mod's _ENV, not in _G
local onCommand = rawget(_ENV, "sglBridgeOnCommand")
if onCommand ~= nil then onCommand("leaderboard", sgl_deepspace_on_leaderboard) end

local function mission_title(missionId)
    local list = rawget(_ENV, "SGL_MISSION_LIST")
    for _, def in ipairs(type(list) == "table" and list or {}) do
        if def.id == missionId and type(def.title) == "string" then
            local t = def.title:lower():gsub("(%a)([%w']*)", function(a, b) return a:upper() .. b end)
            return t
        end
    end
    return missionId
end

-- the boards the menu lists: the offline four, then every other mission with live rows (in mission
-- registration order, unknown ids last by name)
function sgl_deepspace_board_list()
    local out, seen = {}, {}
    for _, b in ipairs(BOARD_LIST) do
        out[#out + 1] = b
        seen[b.missionId] = true
    end
    local extra = {}
    for id, board in pairs(sLiveBoards) do
        if not seen[id] and #board.rows > 0 then extra[#extra + 1] = id end
    end
    local order = {}
    local list = rawget(_ENV, "SGL_MISSION_LIST")
    for i, def in ipairs(type(list) == "table" and list or {}) do order[def.id] = i end
    table.sort(extra, function(a, b)
        local oa, ob = order[a] or math.huge, order[b] or math.huge
        if oa ~= ob then return oa < ob end
        return a < b
    end)
    for _, id in ipairs(extra) do out[#out + 1] = { label = mission_title(id), missionId = id } end
    return out
end

-- "LIVE  UPDATED 3M AGO" (the bridge's fetch time; clocks off by more than a day: just LIVE)
local function live_age_text(board)
    if board.at == nil then return "LIVE" end
    local age = get_time() - board.at
    if age < -300 or age > 86400 then return "LIVE" end
    age = math.max(0, age)
    if age < 60 then return "LIVE  UPDATED JUST NOW" end
    if age < 3600 then return string.format("LIVE  UPDATED %dM AGO", age // 60) end
    return string.format("LIVE  UPDATED %dH AGO", age // 3600)
end

-- The menu opens from the engine Mods screen. Wait for that screen to close and
-- for the closing button to be released before taking controller input.
local sLeaderboardMenu = nil
local sLeaderboardCursor = 1
local sLeaderboardArmed = false
local sLeaderboardRepeat = 0
local sLeaderboardDirection = 0
local sLeaderboardBoard = nil
local sLeaderboardList = BOARD_LIST
local sLeaderboardScroll = 0
local sLeaderboardMouseDown = 0
local sLeaderboardMouseX = 0
local sLeaderboardMouseY = 0
local sLeaderboardMouseShow = 0
local sLeaderboardMouseHover = 0
local sTravelDestinations = {}
local sTravelCursor = 1
local sTravelStage = nil
local sTravelActions = {}
local sTravelActCursor = 1

-- Other HUD hooks run after this file; leave this modal unobstructed.
function sgl_campus_menu_is_open()
    return sLeaderboardMenu ~= nil
end

-- Menu text is drawn once. The world HUD helper adds a one-unit black shadow,
-- which becomes wider than a small glyph stroke on the light menu panels.
local function menu_text(text, x, y, scale, col, alpha)
    djui_hud_set_color(col[1], col[2], col[3], math.floor(255 * (alpha or 1)))
    djui_hud_print_text(text, x, y, scale)
end

local function menu_text_center(text, cx, y, scale, col, alpha)
    menu_text(text, cx - djui_hud_measure_text(text) * scale / 2, y, scale, col, alpha)
end

-- Mouse coordinates are always in DJUI units, even when the menu is drawn at N64 resolution.
local function leaderboard_mouse_point()
    local resolution = djui_hud_get_resolution()
    djui_hud_set_resolution(RESOLUTION_DJUI)
    local djuiH = djui_hud_get_screen_height()
    local mx, my = djui_hud_get_mouse_x(), djui_hud_get_mouse_y()
    djui_hud_set_resolution(RESOLUTION_N64)
    local sw, sh = djui_hud_get_screen_width(), djui_hud_get_screen_height()
    djui_hud_set_resolution(resolution)
    return mx * sh / djuiH, my * sh / djuiH, sw, sh
end

local function leaderboard_button_rect(sw)
    local w = 46
    -- Keep the button clear of the centered mission banner while leaving a
    -- deliberate gap after the player/lives HUD on the left.
    return math.floor(sw * 0.32 - w / 2), 5, w, 16
end

local function travel_button_rect(sw)
    local w = 46
    local bx, y, bw, h = leaderboard_button_rect(sw)
    return sw - bx - bw, y, w, h
end

local function leaderboard_panel_rect(sw, sh)
    local w = math.min(292, sw - 16)
    local h = sLeaderboardMenu == "list" and 194 or 190
    return (sw - w) / 2, (sh - h) / 2, w, h
end

local function leaderboard_tile_rect(index, x, y, panelW)
    local tileW = math.floor((panelW - 28) / 2)
    local column = (index - 1) % 2
    local row = (index - 1) // 2
    return x + 10 + column * (tileW + 8), y + 43 + row * 52, tileW, 46
end

local function travel_panel_rect(sw, sh)
    local w = math.min(292, sw - 16)
    local h = math.min(216, sh - 12)
    return (sw - w) / 2, (sh - h) / 2, w, h
end

local function travel_tile_rect(index, x, y, panelW)
    local tileW = math.floor((panelW - 28) / 2)
    local column = (index - 1) % 2
    local row = (index - 1) // 2
    return x + 10 + column * (tileW + 8), y + 43 + row * 43, tileW, 39
end

local function leaderboard_hit(mx, my, x, y, w, h)
    return mx >= x and mx < x + w and my >= y and my < y + h
end

local function leaderboard_is_paused()
    return (djui_hud_is_pause_menu_created ~= nil and djui_hud_is_pause_menu_created())
        or (is_game_paused ~= nil and is_game_paused())
end

local function close_leaderboard_menu()
    sLeaderboardMenu = nil
end

local function open_travel_menu()
    sTravelDestinations = sgl_campus_travel_destinations()
    if #sTravelDestinations == 0 then
        djui_popup_create("Campus destinations are not installed on this game.", 3)
        return
    end
    sLeaderboardMenu = "travel"
    sTravelCursor = 1
    sTravelStage = nil
    sTravelActions = {}
    sTravelActCursor = 1
    sLeaderboardArmed = false
    sLeaderboardRepeat = 0
    sLeaderboardDirection = 0
    sLeaderboardMouseDown = djui_hud_get_mouse_buttons_down()
    sLeaderboardMouseX, sLeaderboardMouseY = leaderboard_mouse_point()
    sLeaderboardMouseShow = 0
    sLeaderboardMouseHover = 0
end

local function open_travel_destination(destination)
    if destination == nil then return end
    if destination.key == "hub" then
        sLeaderboardMenu = nil
        sgl_campus_warp("hub", nil, false)
        return
    end
    sTravelStage = sgl_stage_by_key(destination.key)
    if sTravelStage == nil then return end
    sTravelActions = {}
    local freeRoamAct = nil
    for act = 1, 6 do
        local name = sgl_act_name(sTravelStage, act)
        if name ~= nil and not sgl_act_is_soon(sTravelStage, act) then
            sTravelActions[#sTravelActions + 1] = { act = act, label = name, detail = "MISSION " .. act }
        elseif freeRoamAct == nil then
            freeRoamAct = act
        end
    end
    if freeRoamAct ~= nil then
        table.insert(sTravelActions, 1, { act = freeRoamAct, label = "EXPLORE AREA", detail = "FREE ROAM" })
    end
    sTravelActCursor = 1
    sLeaderboardMenu = "travel_stage"
    sLeaderboardMouseHover = 0
end

local function choose_travel_action(index)
    local action = sTravelActions[index]
    if action == nil or sTravelStage == nil then return end
    local key, act = sTravelStage.key, action.act
    sLeaderboardMenu = nil
    sgl_campus_warp(key, act, false)
end

local function open_leaderboard_menu()
    if sLeaderboardMenu ~= nil then return end -- mouse clicks can fire more than once
    sLeaderboardMenu = "list"
    sLeaderboardCursor = 1
    sLeaderboardScroll = 0
    sLeaderboardList = sgl_deepspace_board_list()
    sLeaderboardArmed = false
    sLeaderboardRepeat = 0
    sLeaderboardDirection = 0
    sLeaderboardBoard = nil
    sLeaderboardMouseDown = djui_hud_get_mouse_buttons_down()
    sLeaderboardMouseX, sLeaderboardMouseY = leaderboard_mouse_point()
    sLeaderboardMouseShow = 0
    sLeaderboardMouseHover = 0
    if leaderboard_is_paused() then
        djui_popup_create("Ready. Close all pause menus to view, or use /leaderboard in-game.", 3)
    end
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

-- The list grows when live boards arrive; keep the cursor on screen and align scroll to a grid row.
local function refresh_leaderboard_list()
    sLeaderboardList = sgl_deepspace_board_list()
    local n = #sLeaderboardList
    sLeaderboardCursor = math.max(1, math.min(sLeaderboardCursor, n))
    if sLeaderboardCursor <= sLeaderboardScroll or sLeaderboardCursor > sLeaderboardScroll + SGL_DS_LIST_ROWS then
        sLeaderboardScroll = math.max(0, ((sLeaderboardCursor - 1) // 2) * 2 - 2)
    end
    local maxScroll = math.max(0, ((n - 1) // 2) * 2 - 2)
    sLeaderboardScroll = math.max(0, math.min(sLeaderboardScroll, maxScroll))
end

local function move_leaderboard_cursor(dx, dy)
    local n = #sLeaderboardList
    local localIndex = sLeaderboardCursor - sLeaderboardScroll
    if dx < 0 and localIndex % 2 == 0 then
        sLeaderboardCursor = sLeaderboardCursor - 1
    elseif dx > 0 and localIndex % 2 == 1 and sLeaderboardCursor < n then
        sLeaderboardCursor = sLeaderboardCursor + 1
    elseif dy < 0 and sLeaderboardCursor > 2 then
        sLeaderboardCursor = sLeaderboardCursor - 2
    elseif dy > 0 and sLeaderboardCursor + 2 <= n then
        sLeaderboardCursor = sLeaderboardCursor + 2
    end
    refresh_leaderboard_list()
end

-- live rows when the hosted server sent this mission's board, else the .sav snapshot
function sgl_deepspace_board_view(board)
    local live = sLiveBoards[board.missionId]
    if live ~= nil then
        local entries = {}
        for _, row in ipairs(live.rows) do entries[#entries + 1] = { tag = row.name, frames = row.frames } end
        return { label = string.upper(board.label), entries = entries, live = true, status = live_age_text(live) }
    end
    local view = load_cached_board(board)
    view.status = "OFFLINE SNAPSHOT"
    return view
end

local function open_selected_board()
    local board = sLeaderboardList[sLeaderboardCursor]
    if board == nil then return end
    sLeaderboardMenu = "board"
    sLeaderboardBoard = board
    sLeaderboardMouseHover = 0
end

-- CoopDX also maps left click to B. Consume its controller press while using the mouse.
local function leaderboard_mouse_input()
    local mx, my, sw, sh = leaderboard_mouse_point()
    local down = djui_hud_get_mouse_buttons_down()
    local clicked = (down & ~sLeaderboardMouseDown & L_MOUSE_BUTTON) ~= 0
    local busy = down ~= 0 or sLeaderboardMouseDown ~= 0
    sLeaderboardMouseDown = down
    if math.abs(mx - sLeaderboardMouseX) > 0.5 or math.abs(my - sLeaderboardMouseY) > 0.5 or clicked then
        sLeaderboardMouseShow = 90
    end
    sLeaderboardMouseX, sLeaderboardMouseY = mx, my
    if sLeaderboardMouseShow <= 0 then
        sLeaderboardMouseHover = 0
        return busy
    end
    sLeaderboardMouseShow = sLeaderboardMouseShow - 1

    local travel = sLeaderboardMenu == "travel" or sLeaderboardMenu == "travel_stage"
    local x, y, w, h
    if travel then x, y, w, h = travel_panel_rect(sw, sh)
    else x, y, w, h = leaderboard_panel_rect(sw, sh) end
    local hover = 0
    if sLeaderboardMenu == "list" then
        for i = 1, math.min(SGL_DS_LIST_ROWS, #sLeaderboardList - sLeaderboardScroll) do
            local tileX, tileY, tileW, tileH = leaderboard_tile_rect(i, x, y, w)
            if leaderboard_hit(mx, my, tileX, tileY, tileW, tileH) then
                hover = sLeaderboardScroll + i
                break
            end
        end
    elseif sLeaderboardMenu == "travel" then
        for i = 1, #sTravelDestinations do
            local tileX, tileY, tileW, tileH = travel_tile_rect(i, x, y, w)
            if leaderboard_hit(mx, my, tileX, tileY, tileW, tileH) then hover = i break end
        end
    elseif sLeaderboardMenu == "travel_stage" then
        for i = 1, #sTravelActions do
            local tileX, tileY, tileW, tileH = travel_tile_rect(i, x, y, w)
            if leaderboard_hit(mx, my, tileX, tileY, tileW, tileH) then hover = i break end
        end
    end
    if hover > 0 and (hover ~= sLeaderboardMouseHover or clicked) then
        if sLeaderboardMenu == "travel" then sTravelCursor = hover
        elseif sLeaderboardMenu == "travel_stage" then sTravelActCursor = hover
        else sLeaderboardCursor = hover end
    end
    if leaderboard_hit(mx, my, x + 10, y + h - 25, w - 20, 21) then hover = -1 end
    sLeaderboardMouseHover = hover
    if clicked then
        if hover == -1 then
            if sLeaderboardMenu == "board" then sLeaderboardMenu = "list"
            elseif sLeaderboardMenu == "travel_stage" then sLeaderboardMenu = "travel"
            else close_leaderboard_menu() end
        elseif hover > 0 and sLeaderboardMenu == "list" then
            open_selected_board()
        elseif hover > 0 and sLeaderboardMenu == "travel" then
            open_travel_destination(sTravelDestinations[hover])
        elseif hover > 0 and sLeaderboardMenu == "travel_stage" then
            choose_travel_action(hover)
        end
    end
    return busy
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
    refresh_leaderboard_list()
    local mouseBusy = leaderboard_mouse_input()
    if not sLeaderboardArmed then
        if leaderboard_controller_idle(c) then sLeaderboardArmed = true end
        return
    end
    if mouseBusy then return end

    if sLeaderboardMenu == "travel" or sLeaderboardMenu == "travel_stage" then
        local pressed, held = c.buttonPressed, c.buttonDown
        local dx, dy = 0, 0
        if ((pressed | held) & (L_JPAD | L_CBUTTONS)) ~= 0 or (c.stickX or 0) < -60 then dx = -1 end
        if ((pressed | held) & (R_JPAD | R_CBUTTONS)) ~= 0 or (c.stickX or 0) > 60 then dx = 1 end
        if ((pressed | held) & (U_JPAD | U_CBUTTONS)) ~= 0 or (c.stickY or 0) > 60 then dy = -1 end
        if ((pressed | held) & (D_JPAD | D_CBUTTONS)) ~= 0 or (c.stickY or 0) < -60 then dy = 1 end
        local cursor, n = sLeaderboardMenu == "travel" and sTravelCursor or sTravelActCursor,
            sLeaderboardMenu == "travel" and #sTravelDestinations or #sTravelActions
        local localIndex = cursor
        if dx < 0 and localIndex % 2 == 0 then cursor = cursor - 1
        elseif dx > 0 and localIndex % 2 == 1 and cursor < n then cursor = cursor + 1
        elseif dy < 0 and cursor > 2 then cursor = cursor - 2
        elseif dy > 0 and cursor + 2 <= n then cursor = cursor + 2 end
        if sLeaderboardMenu == "travel" then sTravelCursor = cursor else sTravelActCursor = cursor end
        if (pressed & B_BUTTON) ~= 0 then
            if sLeaderboardMenu == "travel_stage" then sLeaderboardMenu = "travel"
            else close_leaderboard_menu() end
        elseif (pressed & START_BUTTON) ~= 0 then
            close_leaderboard_menu()
        elseif (pressed & A_BUTTON) ~= 0 then
            if sLeaderboardMenu == "travel" then open_travel_destination(sTravelDestinations[sTravelCursor])
            else choose_travel_action(sTravelActCursor) end
        end
        return
    end

    local pressed = c.buttonPressed
    local held = c.buttonDown
    local dx, dy = 0, 0
    if ((pressed | held) & (L_JPAD | L_CBUTTONS)) ~= 0 or (c.stickX or 0) < -60 then dx = -1 end
    if ((pressed | held) & (R_JPAD | R_CBUTTONS)) ~= 0 or (c.stickX or 0) > 60 then dx = 1 end
    if ((pressed | held) & (U_JPAD | U_CBUTTONS)) ~= 0 or (c.stickY or 0) > 60 then dy = -1 end
    if ((pressed | held) & (D_JPAD | D_CBUTTONS)) ~= 0 or (c.stickY or 0) < -60 then dy = 1 end
    local direction = dx + dy * 2
    if direction ~= 0 then
        if direction ~= sLeaderboardDirection or sLeaderboardRepeat <= 0 then
            move_leaderboard_cursor(dx, dy)
            sLeaderboardRepeat = 8
        else
            sLeaderboardRepeat = sLeaderboardRepeat - 1
        end
        sLeaderboardDirection = direction
    else
        sLeaderboardDirection = 0
        sLeaderboardRepeat = sLeaderboardRepeat - 1
    end

    if (pressed & B_BUTTON) ~= 0 then
        if sLeaderboardMenu == "board" then
            sLeaderboardMenu = "list"
        else
            close_leaderboard_menu()
        end
    elseif (pressed & START_BUTTON) ~= 0 then
        close_leaderboard_menu()
    elseif (pressed & A_BUTTON) ~= 0 and sLeaderboardMenu == "list" then
        open_selected_board()
    end
end

local function on_leaderboard_before_mario_update(m)
    if m.playerIndex ~= 0 then return end
    if sLeaderboardMenu == nil then
        local mx, my, sw = leaderboard_mouse_point()
        local down = djui_hud_get_mouse_buttons_down()
        local clicked = (down & ~sLeaderboardMouseDown & L_MOUSE_BUTTON) ~= 0
        sLeaderboardMouseDown = down
        local bx, by, bw, bh = leaderboard_button_rect(sw)
        local tx, ty, tw, th = travel_button_rect(sw)
        local charMenu = _G.sglCharSelectIsOpen
        if not leaderboard_is_paused() and not (charMenu ~= nil and charMenu())
            and not (djui_is_chatbox_open ~= nil and djui_is_chatbox_open())
            and ((clicked and (leaderboard_hit(mx, my, bx, by, bw, bh)
                or leaderboard_hit(mx, my, tx, ty, tw, th)))
                or ((m.controller.buttonDown & R_TRIG) ~= 0
                    and (m.controller.buttonPressed & START_BUTTON) ~= 0)) then
            if clicked and leaderboard_hit(mx, my, tx, ty, tw, th) then open_travel_menu()
            else open_leaderboard_menu() end
            eat_leaderboard_input(m.controller)
        end
        return
    end
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
    if sLeaderboardMenu == nil then
        if leaderboard_is_paused() then return end
        local charMenu = _G.sglCharSelectIsOpen
        if charMenu ~= nil and charMenu() then return end
        if djui_is_chatbox_open ~= nil and djui_is_chatbox_open() then return end
        djui_hud_set_resolution(RESOLUTION_N64)
        djui_hud_set_font(FONT_NORMAL)
        local sw = djui_hud_get_screen_width()
        local x, y, w, h = leaderboard_button_rect(sw)
        local tx, ty, tw, th = travel_button_rect(sw)
        sgl_hud_rect(x, y, w, h, 7, 17, 38, 210)
        sgl_hud_rect(x, y, w, 2, 250, 110, 30, 255)
        menu_text_center("BOARDS", x + w / 2, y + 4, 0.25, { 255, 224, 160 }, 1)
        sgl_hud_rect(tx, ty, tw, th, 7, 17, 38, 210)
        sgl_hud_rect(tx, ty, tw, 2, 250, 110, 30, 255)
        menu_text_center("MAP", tx + tw / 2, ty + 4, 0.25, { 255, 224, 160 }, 1)
        return
    end
    if leaderboard_is_paused() then return end
    djui_hud_set_resolution(RESOLUTION_N64)
    djui_hud_set_font(FONT_NORMAL)
    djui_hud_set_font(FONT_MENU)
    djui_hud_set_filter(FILTER_LINEAR)
    local sw, sh = djui_hud_get_screen_width(), djui_hud_get_screen_height()
    local x, y, panelW, panelH = leaderboard_panel_rect(sw, sh)

    -- Campus board picker: a warm N64-style course select with focused tiles.
    local travel = sLeaderboardMenu == "travel" or sLeaderboardMenu == "travel_stage"
    if travel then x, y, panelW, panelH = travel_panel_rect(sw, sh) end
    sgl_hud_rect(0, 0, sw, sh, 0, 0, 0, 112)
    sgl_hud_rect(x - 3, y - 3, panelW + 6, panelH + 6, 105, 156, 205, 255)
    sgl_hud_rect(x, y, panelW, panelH, 250, 244, 224, 255)
    sgl_hud_rect(x, y, panelW, 34, 21, 43, 79, 255)
    sgl_hud_rect(x, y, panelW, 4, 238, 123, 43, 255)
    local heading = "CAMPUS BOARDS"
    if sLeaderboardMenu == "travel" then heading = "CAMPUS MAP"
    elseif sLeaderboardMenu == "travel_stage" then heading = sTravelStage.name end
    local headingScale = math.min(0.31, (panelW - 24) / djui_hud_measure_text(heading))
    menu_text_center(heading, sw / 2, y + 12, headingScale, { 255, 221, 113 }, 1)
    sgl_hud_rect(x + 12, y + 37, panelW - 24, 1, 183, 190, 192, 230)

    if sLeaderboardMenu == "list" then
        refresh_leaderboard_list()
        for i = 1, math.min(SGL_DS_LIST_ROWS, #sLeaderboardList - sLeaderboardScroll) do
            local index = sLeaderboardScroll + i
            local board = sLeaderboardList[index]
            local tileX, tileY, tileW, tileH = leaderboard_tile_rect(i, x, y, panelW)
            local selected = index == sLeaderboardCursor
            local cached = load_cached_board(board)
            local live = sLiveBoards[board.missionId] ~= nil
            local tileFill = selected and { 255, 217, 111 } or { 250, 244, 224 }
            local tileInk = { 23, 39, 69 }
            sgl_hud_rect(tileX + 2, tileY + 2, tileW, tileH, 3, 12, 29, 150)
            sgl_hud_rect(tileX, tileY, tileW, tileH, tileFill[1], tileFill[2], tileFill[3], 255)
            sgl_hud_rect(tileX, tileY, tileW, 2, selected and 238 or 112, selected and 123 or 155,
                selected and 43 or 194, 255)
            sgl_hud_rect(tileX, tileY, 3, tileH, selected and 238 or 112, selected and 123 or 155,
                selected and 43 or 194, 255)
            local badge = string.format("%02d", index)
            sgl_hud_rect(tileX + 6, tileY + 6, 20, 20, 21, 43, 79, 255)
            menu_text_center(badge, tileX + 16, tileY + 10, 0.17, { 255, 221, 113 }, 1)
            local titleScale = math.min(0.23, (tileW - 34) / djui_hud_measure_text(board.label))
            menu_text(board.label, tileX + 30, tileY + 8, titleScale, tileInk, 1)
            local status = live and "LIVE BOARD"
                or (#cached.entries > 0 and "SAVED TIMES" or "NO TIMES YET")
            local statusColor = live and { 58, 139, 78 }
                or (#cached.entries > 0 and { 71, 103, 150 } or { 116, 124, 132 })
            menu_text(status, tileX + 7, tileY + 31, 0.14, statusColor, 1)
        end
        if #sLeaderboardList > SGL_DS_LIST_ROWS then
            menu_text(string.format("%d/%d", sLeaderboardCursor, #sLeaderboardList), x + panelW - 30, y + 16,
                0.14, { 255, 221, 113 }, 1)
        end
        sgl_hud_rect(x + 12, y + panelH - 29, panelW - 24, 1, 129, 151, 181, 220)
        if sLeaderboardMouseHover == -1 then
            sgl_hud_rect(x + 10, y + panelH - 25, panelW - 20, 21, 221, 231, 242, 255)
        end
        menu_text_center("A / CLICK: VIEW    B: BACK    START: CLOSE", sw / 2, y + panelH - 20,
            0.17, { 23, 39, 69 }, 1)
    elseif sLeaderboardMenu == "travel" or sLeaderboardMenu == "travel_stage" then
        local inStage = sLeaderboardMenu == "travel_stage"
        local entries = inStage and sTravelActions or sTravelDestinations
        for i = 1, math.min(6, #entries) do
            local tileX, tileY, tileW, tileH = travel_tile_rect(i, x, y, panelW)
            local selected = i == (inStage and sTravelActCursor or sTravelCursor)
            local entry = entries[i]
            local tileFill = selected and { 255, 217, 111 } or { 250, 244, 224 }
            sgl_hud_rect(tileX + 2, tileY + 2, tileW, tileH, 3, 12, 29, 150)
            sgl_hud_rect(tileX, tileY, tileW, tileH, tileFill[1], tileFill[2], tileFill[3], 255)
            sgl_hud_rect(tileX, tileY, tileW, 2, selected and 238 or 112, selected and 123 or 155,
                selected and 43 or 194, 255)
            sgl_hud_rect(tileX, tileY, 3, tileH, selected and 238 or 112, selected and 123 or 155,
                selected and 43 or 194, 255)
            sgl_hud_rect(tileX + 6, tileY + 6, 18, 18, 21, 43, 79, 255)
            menu_text_center(string.format("%02d", i), tileX + 15, tileY + 9, 0.16, { 255, 221, 113 }, 1)
            local titleScale = math.min(0.21, (tileW - 32) / djui_hud_measure_text(entry.name or entry.label))
            menu_text(entry.name or entry.label, tileX + 29, tileY + 7, titleScale, { 23, 39, 69 }, 1)
            local detailScale = math.min(0.17, (tileW - 14) / djui_hud_measure_text(entry.detail))
            menu_text(entry.detail, tileX + 7, tileY + 26, detailScale, { 64, 83, 110 }, 1)
        end
        sgl_hud_rect(x + 12, y + panelH - 29, panelW - 24, 1, 183, 190, 192, 230)
        if sLeaderboardMouseHover == -1 then
            sgl_hud_rect(x + 10, y + panelH - 25, panelW - 20, 21, 221, 231, 242, 255)
        end
        local footer = inStage and "A / CLICK: GO    B: MAP    START: CLOSE"
            or "A / CLICK: SELECT    B: CLOSE    START: CLOSE"
        menu_text_center(footer, sw / 2, y + panelH - 20, 0.17, { 23, 39, 69 }, 1)
    else
        local board = sLeaderboardBoard and sgl_deepspace_board_view(sLeaderboardBoard)
            or { label = "GLOBAL BOARD", entries = {}, status = "" }
        menu_text_center(board.label, sw / 2, y + 36, 0.28, { 23, 39, 69 }, 1)
        menu_text_center(board.status, sw / 2, y + 46, 0.15,
            board.live and { 58, 139, 78 } or { 86, 105, 128 }, 1)
        sgl_hud_rect(x + 12, y + 54, panelW - 24, 1, 183, 190, 192, 230)
        if #board.entries == 0 and board.live then
            menu_text_center("NO VERIFIED RUNS YET", sw / 2, y + 79, 0.25, { 23, 39, 69 }, 1)
            menu_text_center("Finish this mission on the server to rank.", sw / 2, y + 98, 0.19,
                { 86, 105, 128 }, 1)
        elseif #board.entries == 0 then
            menu_text_center("NO SCORES CACHED YET", sw / 2, y + 79, 0.25, { 23, 39, 69 }, 1)
            menu_text_center("Complete a run, then sync scores.", sw / 2, y + 98, 0.19,
                { 86, 105, 128 }, 1)
        else
            for rank, score in ipairs(board.entries) do
                local rowY = y + 61 + (rank - 1) * 19
                local medal = rank == 1 and { 255, 205, 70 }
                    or (rank == 2 and { 190, 210, 235 } or { 205, 145, 100 })
                sgl_hud_rect(x + 10, rowY, panelW - 20, 17,
                    rank == 1 and 255 or 255, rank == 1 and 220 or 249, rank == 1 and 119 or 237, 255)
                sgl_hud_rect(x + 10, rowY, 3, 17, medal[1], medal[2], medal[3], 255)
                local line = score.retries ~= nil
                    and string.format("#%d  %s    %s   R%d", rank, score.tag, leaderboard_time(score.frames), score.retries)
                    or string.format("#%d  %s    %s", rank, score.tag, leaderboard_time(score.frames))
                local scale = math.min(0.22, (panelW - 38) / djui_hud_measure_text(line))
                menu_text(line, x + 18, rowY + 3, scale, { 23, 39, 69 }, 1)
            end
        end
        sgl_hud_rect(x + 12, y + panelH - 29, panelW - 24, 1, 183, 190, 192, 230)
        if sLeaderboardMouseHover == -1 then
            sgl_hud_rect(x + 10, y + panelH - 25, panelW - 20, 21, 221, 231, 242, 255)
        end
        menu_text_center("[BACK TO BOARDS]    START: CLOSE", sw / 2, y + panelH - 20,
            0.19, { 23, 39, 69 }, 1)
    end

    if sLeaderboardMouseShow > 0 then
        sgl_hud_rect(sLeaderboardMouseX + 1, sLeaderboardMouseY + 1, 5, 8, 0, 0, 0, 255)
        sgl_hud_rect(sLeaderboardMouseX, sLeaderboardMouseY, 4, 7, 255, 255, 255, 255)
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

if hook_mod_menu_text ~= nil then
    hook_mod_menu_text("In-game: click MAP for campus travel or BOARDS for records. This Mods button needs Pause closed.")
end

if hook_chat_command ~= nil then
    hook_chat_command("leaderboard", "Open the campus leaderboard menu", function()
        open_leaderboard_menu()
        return true
    end)
end
