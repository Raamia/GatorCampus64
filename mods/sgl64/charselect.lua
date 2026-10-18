-- Character select menu: an SM64-style overlay with one portrait card per friend.
--
-- Opens by itself on your first spawn while you have never picked a friend, and any time with
-- /char (no name), L + START, or Pause > Mods > GatorCampus 64 > "Choose your friend".
--   move:  D-pad, stick, C-buttons (arrow keys on keyboard) or the mouse
--   page:  L / R, or D-pad / stick left-right past the first / last card of a page
--   pick:  A or left click        close: B or START
-- Pages hold 10 cards (5 x 2): page 1 is the team ("CHOOSE YOUR GATOR!"), page 2 the guest slots
-- from guests.lua ("GUEST GATORS", characters made on the website).
-- The pick goes through characters.lua (_G.sglSetFriend -> gPlayerSyncTable[0].friend, synced to
-- everyone) and is remembered in mod storage (key "friend" = friend id, or "off") for next time.
-- Cards show who else already plays as that friend (a name tag per player).
--
-- Portraits: textures/sgl_portrait_<id>.png (64x64). When the game starts, DynOS converts every
-- PNG in a mod's textures/ folder into textures/<name>.tex, which get_texture_info('<name>') finds.
-- A portrait that fails to load falls back to a coloured card with the friend's initial.

local SHOW_EVERY_SESSION = false -- true: also open on the first spawn of every session after a pick
local STORAGE_KEY = "friend"
local PORTRAIT_FILTER = FILTER_NEAREST -- FILTER_LINEAR for a softer N64 look

-- card colours = the portrait backgrounds (make_portraits.py COLORS)
local CARD_COLORS = {
    daniel = { 232, 88, 56 },
    corina = { 240, 112, 176 },
    raami = { 250, 140, 32 },
    anh = { 64, 172, 236 },
    josh = { 72, 196, 112 },
    donald = { 152, 100, 224 },
    jaime = { 240, 200, 40 },
    alfred = { 56, 96, 208 },
    vignesh = { 216, 40, 64 },
    cher = { 40, 188, 188 },
}
local DEFAULT_CARD_COLOR = { 128, 128, 150 }

-- only used if characters.lua did not export _G.sglFriends
local FALLBACK_FRIENDS = {
    { id = "daniel", name = "Daniel" }, { id = "corina", name = "Corina" },
    { id = "raami", name = "Raami" }, { id = "anh", name = "Anh" },
    { id = "josh", name = "Josh" }, { id = "donald", name = "Donald" },
    { id = "jaime", name = "Jaime" }, { id = "alfred", name = "Alfred" },
    { id = "vignesh", name = "Vignesh" }, { id = "cher", name = "Cher" },
}

local function friends()
    return _G.sglFriends or FALLBACK_FRIENDS
end

local function friend_ok(f)
    return f ~= nil and (f.model == nil or f.model ~= E_MODEL_ERROR_MODEL)
end

local function local_pick()
    local k = gPlayerSyncTable[0].friend
    if type(k) == "number" then return k end
    return 0
end

---------------------------------------------------------------------------------------------
-- layout (virtual 344 x 240 canvas, scaled to fit the screen and centred)
---------------------------------------------------------------------------------------------

local VW, VH = 344, 240
local COLS = 5
local CARD_W, CARD_H = 58, 74
local GAP_X, GAP_Y = 6, 8
local GRID_X = (VW - (COLS * CARD_W + (COLS - 1) * GAP_X)) / 2
local GRID_Y = 40
local PORTRAIT = 50

-- current screen mapping, set every render (ox/oy/u in DJUI units)
local V = { ox = 0, oy = 0, u = 1, fade = 1 }

local PER_PAGE = 10        -- COLS x 2 rows fit between the title and the footer

-- pages: friend index i is on page (i - 1) // PER_PAGE + 1
local function page_count()
    return math.max(1, (#friends() + PER_PAGE - 1) // PER_PAGE)
end

local function page_of(i)
    return (i - 1) // PER_PAGE + 1
end

-- first friend index and number of cards on page p
local function page_range(p)
    local first = (p - 1) * PER_PAGE + 1
    return first, math.max(0, math.min(PER_PAGE, #friends() - first + 1))
end

local function card_pos(i)
    local k = (i - 1) % PER_PAGE
    return GRID_X + (k % COLS) * (CARD_W + GAP_X), GRID_Y + (k // COLS) * (CARD_H + GAP_Y)
end

-- card under a virtual-canvas point, on page p (0: none)
local function card_at(vx, vy, p)
    local first, n = page_range(p)
    for i = first, first + n - 1 do
        local x, y = card_pos(i)
        if vx >= x and vx < x + CARD_W and vy >= y and vy < y + CARD_H then return i end
    end
    return 0
end

---------------------------------------------------------------------------------------------
-- state
---------------------------------------------------------------------------------------------

local sOpen = false
local sCursor = 1
local sOpenTimer = 0       -- frames since the menu opened (open animation)
local sPageTimer = 0       -- frames since the page changed (cards drop in again)
local sTimer = 0           -- frames, for the idle animations
local sConfirmTimer = 0    -- > 0 while the "HERE WE GO" flash plays, closes at 0
local sConfirmIndex = 0
local sHasPick = false     -- a pick (or "off") is saved in mod storage
local sRestored = false    -- saved pick applied this session
local sAutoPending = false -- open as soon as the player is standing in a level
local sAutoReady = 0
local sAutoOpened = false
local sHidHud = false
local sMoveDir = 0         -- held stick direction (1 left, 2 right, 3 up, 4 down)
local sMoveRepeat = 0
local sFrame = 0
local sInputFrame = -1
local sMouseX, sMouseY = 0, 0
local sMouseShow = 0       -- frames the mouse cursor stays visible after it moved
local sMouseDown = 0
local sHover = 0           -- card under the mouse

local sPortraits = {}      -- id -> TextureInfo, or false when it failed to load

local function is_pot(n)
    if type(n) ~= "number" or n <= 0 then return false end
    n = math.floor(n)
    return (n & (n - 1)) == 0
end

local function portrait(id)
    local t = sPortraits[id]
    if t == nil then
        t = get_texture_info("sgl_portrait_" .. id)
        if t == nil or not is_pot(t.width) or not is_pot(t.height) then
            log_to_console("[SGL] portrait 'sgl_portrait_" .. id .. "' did not load, using a coloured card", CONSOLE_MESSAGE_WARNING)
            t = false
        end
        sPortraits[id] = t
    end
    return t or nil
end

local function sfx(bits)
    if gGlobalSoundSource ~= nil then
        play_sound(bits, gGlobalSoundSource)
    else
        play_sound(bits, gMarioStates[0].marioObj.header.gfx.cameraToObject)
    end
end

---------------------------------------------------------------------------------------------
-- picking and remembering
---------------------------------------------------------------------------------------------

local function remember(index)
    local f = friends()[index]
    mod_storage_save(STORAGE_KEY, (index ~= 0 and f ~= nil and f.id) or "off")
    sHasPick = true
end
-- characters.lua calls this after every pick (also /char <name|off>), so those are remembered too
_G.sglOnFriendSet = remember

local function set_friend(index)
    if _G.sglSetFriend ~= nil then
        return _G.sglSetFriend(index) -- calls sglOnFriendSet -> remember
    end
    gPlayerSyncTable[0].friend = index
    remember(index)
    return true
end

local function find_by_id(id)
    for i, f in ipairs(friends()) do
        if f.id == id then return i end
    end
    return nil
end

local function open_menu()
    if sOpen then return end
    sOpen = true
    sOpenTimer = 0
    sPageTimer = 0
    sConfirmTimer = 0
    sMoveDir = 0
    sMouseShow = 0
    sHover = 0
    sMouseX, sMouseY = djui_hud_get_mouse_x(), djui_hud_get_mouse_y()
    sMouseDown = djui_hud_get_mouse_buttons_down()
    local pick = local_pick()
    sCursor = (pick >= 1 and pick <= #friends()) and pick or 1
    sHidHud = not hud_is_hidden()
    if sHidHud then hud_hide() end
    sfx(SOUND_MENU_MESSAGE_APPEAR)
end

local function close_menu(silent)
    if not sOpen then return end
    sOpen = false
    sConfirmTimer = 0
    if sHidHud then hud_show() end
    sHidHud = false
    if not silent then sfx(SOUND_MENU_MESSAGE_DISAPPEAR) end
end

-- characters.lua: /char with no name
_G.sglOpenCharSelect = open_menu
-- sgl_hud.lua (sgl_hud_blocked): the other HUD hooks of the mod skip drawing while the menu is open.
-- This file's HUD hook is registered before theirs (files load alphabetically), so it draws first.
_G.sglCharSelectIsOpen = function() return sOpen end

local function confirm(index)
    local f = friends()[index]
    if not friend_ok(f) or not set_friend(index) then
        sfx(SOUND_MENU_CAMERA_BUZZ)
        return
    end
    sConfirmIndex = index
    sConfirmTimer = 20
    sfx(SOUND_MENU_CLICK_FILE_SELECT)
    play_character_sound(gMarioStates[0], CHAR_SOUND_HERE_WE_GO)
    djui_popup_create("You are now \\#ffd700\\" .. f.name .. "\\#dcdcdc\\!", 1)
end

---------------------------------------------------------------------------------------------
-- input
---------------------------------------------------------------------------------------------

local function set_cursor(i)
    if i ~= sCursor then
        if page_of(i) ~= page_of(sCursor) then sPageTimer = 0 end
        sCursor = i
        sfx(SOUND_MENU_CHANGE_SELECT)
    end
end

-- the card on page p at (row, col), clamped to the cards that page has
local function card_on_page(p, row, col)
    local first, n = page_range(p)
    local rows = (n + COLS - 1) // COLS
    row = math.min(row, rows - 1)
    return first + math.min(row * COLS + col, n - 1)
end

-- dir: 1 left, 2 right, 3 up, 4 down. Left / right step through the cards in reading order and wrap
-- (past the first / last card of a page they turn the page); up / down stay on the page and wrap.
local function move_cursor(dir)
    local n = #friends()
    if dir == 1 then set_cursor((sCursor - 2) % n + 1) return end
    if dir == 2 then set_cursor(sCursor % n + 1) return end
    local first, count = page_range(page_of(sCursor))
    local k = sCursor - first
    local rows = (count + COLS - 1) // COLS
    local row = (k // COLS + (dir == 3 and -1 or 1)) % rows
    set_cursor(first + math.min(row * COLS + k % COLS, count - 1))
end

-- L / R: previous / next page, same spot on the page
local function turn_page(delta)
    local pages = page_count()
    if pages == 1 then return end
    local p = page_of(sCursor)
    local k = sCursor - page_range(p)
    set_cursor(card_on_page((p - 1 + delta) % pages + 1, k // COLS, k % COLS))
end

-- Mouse: hover moves the cursor, left click picks. Returns true while a mouse button is in use
-- with the cursor showing, because coopdx binds left click to B and right click to A by default
-- and those presses must not also close the menu.
local function mouse_update()
    local mx, my = djui_hud_get_mouse_x(), djui_hud_get_mouse_y()
    local down = djui_hud_get_mouse_buttons_down()
    local clicked = (down & ~sMouseDown & L_MOUSE_BUTTON) ~= 0
    local busy = down ~= 0 or sMouseDown ~= 0
    sMouseDown = down
    if math.abs(mx - sMouseX) > 0.5 or math.abs(my - sMouseY) > 0.5 then
        sMouseShow = 90
    end
    sMouseX, sMouseY = mx, my
    if sMouseShow <= 0 then
        sHover = 0
        return false
    end
    sMouseShow = sMouseShow - 1
    local hover = card_at((mx - V.ox) / V.u, (my - V.oy) / V.u, page_of(sCursor))
    if sConfirmTimer == 0 then
        if hover ~= 0 and hover ~= sHover and hover ~= sCursor then
            set_cursor(hover)
        end
        if clicked and hover ~= 0 then
            sCursor = hover
            confirm(hover)
        end
    end
    sHover = hover
    return busy
end

local function menu_input(c)
    local mouseBusy = mouse_update()
    if sConfirmTimer > 0 or mouseBusy then return end
    local pressed = c.buttonPressed

    if (pressed & (B_BUTTON | START_BUTTON)) ~= 0 then
        close_menu(false)
        return
    end
    if (pressed & A_BUTTON) ~= 0 then
        confirm(sCursor)
        return
    end

    if (pressed & L_TRIG) ~= 0 then turn_page(-1) return end
    if (pressed & R_TRIG) ~= 0 then turn_page(1) return end
    if (pressed & (L_JPAD | L_CBUTTONS)) ~= 0 then move_cursor(1) return end
    if (pressed & (R_JPAD | R_CBUTTONS)) ~= 0 then move_cursor(2) return end
    if (pressed & (U_JPAD | U_CBUTTONS)) ~= 0 then move_cursor(3) return end
    if (pressed & (D_JPAD | D_CBUTTONS)) ~= 0 then move_cursor(4) return end

    -- stick, with hold-to-repeat
    local sx, sy = c.stickX, c.stickY
    local dir = 0
    if math.abs(sx) > 40 and math.abs(sx) >= math.abs(sy) then
        dir = sx < 0 and 1 or 2
    elseif math.abs(sy) > 40 then
        dir = sy > 0 and 3 or 4
    end
    if dir == 0 then
        sMoveDir = 0
    elseif dir ~= sMoveDir then
        sMoveDir = dir
        sMoveRepeat = 10
        move_cursor(dir)
    else
        sMoveRepeat = sMoveRepeat - 1
        if sMoveRepeat <= 0 then
            sMoveRepeat = 4
            move_cursor(dir)
        end
    end
end

local function eat_input(c)
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

local function menu_visible()
    return sOpen and not djui_hud_is_pause_menu_created() and not is_game_paused()
end

local function on_before_mario_update(m)
    if m.playerIndex ~= 0 then return end
    local c = m.controller
    if sOpen then
        if menu_visible() then
            menu_input(c)
            sInputFrame = sFrame
        end
        eat_input(c) -- Mario stands still and START does not pause while the menu is up
    elseif (c.buttonDown & L_TRIG) ~= 0 and (c.buttonPressed & START_BUTTON) ~= 0 then
        c.buttonPressed = c.buttonPressed & ~(START_BUTTON | L_TRIG) -- the L of L + START must not also turn the page
        open_menu()
    end
end

---------------------------------------------------------------------------------------------
-- auto open / restore
---------------------------------------------------------------------------------------------

local function can_auto_open()
    local m = gMarioStates[0]
    if m == nil or m.marioObj == nil then return false end
    if (m.action & ACT_GROUP_MASK) == ACT_GROUP_CUTSCENE then return false end
    if is_transition_playing() or is_game_paused() or djui_hud_is_pause_menu_created() then return false end
    if get_dialog_id() >= 0 then return false end
    if djui_is_chatbox_open ~= nil and djui_is_chatbox_open() then return false end
    return true
end

local function on_sync_valid()
    if sRestored then return end
    sRestored = true
    local saved = mod_storage_load(STORAGE_KEY)
    if saved ~= nil and saved ~= "" then
        sHasPick = true
        local index = find_by_id(saved)
        if index ~= nil and friend_ok(friends()[index]) then
            if local_pick() ~= index then set_friend(index) end
            djui_popup_create("Playing as \\#ffd700\\" .. friends()[index].name ..
                "\\#dcdcdc\\. L + START or /char to switch.", 2)
        end
    end
    sAutoPending = SHOW_EVERY_SESSION or not sHasPick
end

local function on_update()
    sTimer = sTimer + 1
    if sOpen then
        sOpenTimer = sOpenTimer + 1
        sPageTimer = sPageTimer + 1
        -- Mario was not updated this frame (cutscene, time stop...): read the pad here instead
        if sInputFrame ~= sFrame and menu_visible() then
            menu_input(gMarioStates[0].controller)
        end
        if sConfirmTimer > 0 then
            sConfirmTimer = sConfirmTimer - 1
            if sConfirmTimer == 0 then close_menu(true) end
        end
    elseif sAutoPending and not sAutoOpened then
        if can_auto_open() then
            sAutoReady = sAutoReady + 1
            if sAutoReady >= 20 then
                sAutoOpened = true
                sAutoPending = false
                open_menu()
            end
        else
            sAutoReady = 0
        end
    end
    sFrame = sFrame + 1
end

local function on_warp()
    if not sOpen then return end
    close_menu(true)
    -- an auto-opened menu that a warp interrupted comes back once the player has landed
    if sAutoOpened and not sHasPick then
        sAutoOpened = false
        sAutoPending = true
        sAutoReady = 0
    end
end

---------------------------------------------------------------------------------------------
-- drawing (DJUI resolution so text stays sharp; all coordinates in virtual units)
---------------------------------------------------------------------------------------------

local function clamp8(v)
    v = math.floor(v + 0.5)
    if v < 0 then return 0 end
    if v > 255 then return 255 end
    return v
end

local function col(r, g, b, a)
    djui_hud_set_color(clamp8(r), clamp8(g), clamp8(b), clamp8((a or 255) * V.fade))
end

local function rect(x, y, w, h)
    djui_hud_render_rect(V.ox + x * V.u, V.oy + y * V.u, w * V.u, h * V.u)
end

-- rectangle with notched (pixel-rounded) corners
local function rrect(x, y, w, h, r)
    rect(x + r, y, w - 2 * r, h)
    rect(x, y + r, r, h - 2 * r)
    rect(x + w - r, y + r, r, h - 2 * r)
end

local function text_w(s, scale)
    return djui_hud_measure_text(s) * scale
end

local function text(s, x, y, scale)
    djui_hud_print_text(s, V.ox + x * V.u, V.oy + y * V.u, scale * V.u)
end

local function shadow_text(s, x, y, scale, r, g, b, a, off)
    off = off or 1
    col(0, 0, 0, (a or 255) * 0.7)
    text(s, x + off, y + off, scale)
    col(r, g, b, a)
    text(s, x, y, scale)
end

local function ease_out(t)
    if t <= 0 then return 0 end
    if t >= 1 then return 1 end
    return 1 - (1 - t) * (1 - t) * (1 - t)
end

local function short_name(s)
    s = (s or ""):gsub("\\#%x+\\", "")
    local n = utf8 ~= nil and utf8.len(s) or nil
    if n ~= nil then
        if n > 8 then s = s:sub(1, utf8.offset(s, 8) - 1) .. "." end
    elseif #s > 8 then
        s = s:sub(1, 7) .. "."
    end
    return s
end

local function shirt_color(np)
    local ok, c = pcall(function() return np.palette.parts[SHIRT] end)
    if ok and c ~= nil and c.r ~= nil then return c.r, c.g, c.b end
    return 90, 90, 110
end

-- Gator Pass (sgl_login.lua): a verified player's name tag gets a star mark
local function verified(localIndex)
    local f = _G.sglIsVerified
    return f ~= nil and f(localIndex) == true
end

-- who else plays as which friend: index -> list of { name, r, g, b }
local function collect_tags()
    local tags = {}
    for i = 1, MAX_PLAYERS - 1 do
        local np = gNetworkPlayers[i]
        if np ~= nil and np.connected then
            local k = gPlayerSyncTable[i].friend
            if type(k) == "number" and k >= 1 then
                local r, g, b = shirt_color(np)
                tags[k] = tags[k] or {}
                table.insert(tags[k], { name = (verified(i) and "*" or "") .. short_name(np.name), r = r, g = g, b = b })
            end
        end
    end
    return tags
end

local function tag_pill(label, x, y, r, g, b)
    local scale = 0.2
    local w = text_w(label, scale) + 4
    col(0, 0, 0, 170)
    rrect(x - 0.5, y - 0.5, w + 1, 9, 1)
    col(r, g, b, 255)
    rrect(x, y, w, 8, 1)
    if 0.3 * r + 0.59 * g + 0.11 * b > 150 then col(20, 20, 30, 255) else col(255, 255, 255, 255) end
    text(label, x + 2, y + 0.6, scale)
end

local function draw_background(sw, sh)
    local t = ease_out(sOpenTimer / 8)
    djui_hud_set_color(4, 10, 36, clamp8(205 * t))
    djui_hud_render_rect(0, 0, sw, sh)

    -- scrolling checkerboard in UF blue
    local T = 20
    local off = (sTimer * 0.35) % (2 * T)
    local gx0 = math.floor((-V.ox / V.u) / T) - 2
    local gx1 = math.ceil(((sw - V.ox) / V.u) / T) + 1
    local gy0 = math.floor((-V.oy / V.u) / T) - 2
    local gy1 = math.ceil(((sh - V.oy) / V.u) / T) + 1
    col(0, 33, 165, 70 * t)
    for gy = gy0, gy1 do
        for gx = gx0, gx1 do
            if (gx + gy) % 2 == 0 then
                rect(gx * T + off, gy * T + off, T, T)
            end
        end
    end
end

local RAINBOW = { { 236, 52, 44 }, { 60, 200, 72 }, { 64, 120, 255 }, { 255, 204, 0 } }

local function draw_title(s)
    djui_hud_set_font(FONT_MENU)
    local scale = 0.33
    local w = text_w(s, scale)
    if w > 316 then
        scale = scale * 316 / w
        w = 316
    end
    local x = (VW - w) / 2
    local n = 0
    for ch in s:gmatch(".") do
        if ch ~= " " then
            n = n + 1
            local c = RAINBOW[(n - 1) % #RAINBOW + 1]
            local wave = math.sin(sTimer * 0.15 + n * 0.55) * 1.5
            shadow_text(ch, x, 11 + wave, scale, c[1], c[2], c[3], 255, 1.5)
        end
        x = x + text_w(ch, scale)
    end
end

local function draw_card(i, f, x, y, selected, tags)
    local c = CARD_COLORS[f.id] or DEFAULT_CARD_COLOR
    local lift = 0
    if selected then lift = -3 - math.abs(math.sin(sTimer * 0.12)) * 1.5 end

    -- drop shadow stays on the table, the card lifts
    col(0, 0, 0, 130)
    rrect(x + 2, y + 2, CARD_W, CARD_H, 3)
    y = y + lift
    if selected then
        local p = 0.5 + 0.5 * math.sin(sTimer * 0.25)
        col(255, 190 + 50 * p, 40 * p, 255)
        rrect(x - 2, y - 2, CARD_W + 4, CARD_H + 4, 4)
    end
    col(250, 70, 22, 255) -- UF orange rim
    rrect(x, y, CARD_W, CARD_H, 3)
    col(c[1] * 0.35, c[2] * 0.35, c[3] * 0.35, 255)
    rrect(x + 2, y + 2, CARD_W - 4, CARD_H - 4, 2)

    -- portrait, or the fallback card
    local px, py = x + (CARD_W - PORTRAIT) / 2, y + 4
    local tex = portrait(f.id)
    if tex ~= nil then
        col(255, 255, 255, 255)
        djui_hud_set_filter(PORTRAIT_FILTER)
        djui_hud_render_texture(tex, V.ox + px * V.u, V.oy + py * V.u,
            PORTRAIT * V.u / tex.width, PORTRAIT * V.u / tex.height)
        djui_hud_set_filter(FILTER_NEAREST)
    else
        col(c[1], c[2], c[3], 255)
        rect(px, py, PORTRAIT, PORTRAIT)
        col(c[1] + (255 - c[1]) * 0.35, c[2] + (255 - c[2]) * 0.35, c[3] + (255 - c[3]) * 0.35, 255)
        for k = 0, 4 do rect(px, py + k * 10 + 3, PORTRAIT, 3) end
        djui_hud_set_font(FONT_MENU)
        local initial = f.name:sub(1, 1):upper()
        local w = text_w(initial, 0.55)
        shadow_text(initial, px + (PORTRAIT - w) / 2, py + 9, 0.55, 255, 255, 255, 255, 2)
    end
    if not friend_ok(f) then
        col(20, 20, 20, 190)
        rect(px, py, PORTRAIT, PORTRAIT)
        djui_hud_set_font(FONT_HUD)
        shadow_text("?", px + PORTRAIT / 2 - 6, py + PORTRAIT / 2 - 8, 1, 255, 80, 80, 255)
    end
    if sConfirmTimer > 0 and sConfirmIndex == i then
        col(255, 255, 255, 200 * (sConfirmTimer % 6) / 6)
        rect(px, py, PORTRAIT, PORTRAIT)
    end

    -- name in the SM64 HUD font
    djui_hud_set_font(FONT_HUD)
    local label = f.name:upper()
    local s = 0.58
    local w = text_w(label, s)
    if w > CARD_W - 6 then
        s = s * (CARD_W - 6) / w
        w = CARD_W - 6
    end
    local ty = y + 4 + PORTRAIT + (CARD_H - 4 - PORTRAIT - 16 * s) / 2
    if selected then
        shadow_text(label, x + (CARD_W - w) / 2, ty, s, 255, 220, 60, 255)
    else
        shadow_text(label, x + (CARD_W - w) / 2, ty, s, 235, 235, 245, 255)
    end

    -- who plays as this friend
    djui_hud_set_font(FONT_NORMAL)
    local tagY = py + 1
    if local_pick() == i then
        tag_pill(verified(0) and "*YOU" or "YOU", px + 1, tagY, 60, 220, 90)
        tagY = tagY + 9
    end
    local list = tags[i]
    if list ~= nil then
        for k, t in ipairs(list) do
            if k == 3 and #list > 3 then
                tag_pill("+" .. (#list - 2), px + 1, tagY, 40, 40, 60)
                break
            end
            tag_pill(t.name, px + 1, tagY, t.r, t.g, t.b)
            tagY = tagY + 9
        end
    end
end

-- our own pointer: DJUI hides the system cursor during gameplay
local CURSOR_ROWS = {
    "B", "BB", "BWB", "BWWB", "BWWWB", "BWWWWB", "BWWWWWB", "BWWWWWWB",
    "BWWWWBBBB", "BWBWWB", "BB BWWB", "B  BWWB", "    BWWB", "    BB",
}

local function draw_mouse_cursor(vx, vy)
    local p = 0.8
    for row, s in ipairs(CURSOR_ROWS) do
        for k = 1, #s do
            local ch = s:sub(k, k)
            if ch ~= " " then
                if ch == "B" then col(0, 0, 0, 255) else col(255, 255, 255, 255) end
                rect(vx + (k - 1) * p, vy + (row - 1) * p, p, p)
            end
        end
    end
end

-- page tabs at the right end of the footer row (the name under the cursor is centred): "L 1 2 R" (FONT_HUD has no arrows)
local function draw_page_tabs(page, pages)
    djui_hud_set_font(FONT_HUD)
    local s = 0.5
    local step = 10
    local x = VW - 20 - (pages + 2) * step
    shadow_text("L", x, 208, s, 200, 210, 235, 255)
    for p = 1, pages do
        if p == page then
            shadow_text(tostring(p), x + p * step, 208, s, 255, 214, 40, 255)
        else
            shadow_text(tostring(p), x + p * step, 208, s, 120, 130, 170, 255)
        end
    end
    shadow_text("R", x + (pages + 1) * step, 208, s, 200, 210, 235, 255)
end

local function on_hud_render()
    if not menu_visible() then return end

    djui_hud_set_resolution(RESOLUTION_DJUI)
    djui_hud_set_font(FONT_NORMAL)
    local sw, sh = djui_hud_get_screen_width(), djui_hud_get_screen_height()
    V.u = math.min(sw / VW, sh / VH)
    V.ox = (sw - VW * V.u) / 2
    V.oy = (sh - VH * V.u) / 2
    V.fade = 1

    draw_background(sw, sh)

    -- panel fades in, cards drop in one after another
    local fade = ease_out(sOpenTimer / 8)
    V.fade = fade
    local list = friends()
    local tags = collect_tags()

    col(0, 0, 0, 120)
    rrect(10, 8, VW - 16, VH - 12, 6)
    col(250, 70, 22, 255)
    rrect(8, 6, VW - 16, VH - 12, 6)
    col(10, 22, 70, 245)
    rrect(11, 9, VW - 22, VH - 18, 5)
    col(0, 33, 165, 255)
    rect(14, 35, VW - 28, 1)
    rect(14, 202, VW - 28, 1)

    local page, pages = page_of(sCursor), page_count()
    local first, n = page_range(page)
    if sConfirmTimer > 0 and list[sConfirmIndex] ~= nil then
        draw_title("HERE WE GO, " .. list[sConfirmIndex].name:upper() .. "!")
    elseif list[first] ~= nil and list[first].guest then
        draw_title("GUEST GATORS")
    else
        draw_title("CHOOSE YOUR GATOR!")
    end

    for i = first, first + n - 1 do
        local x, y = card_pos(i)
        local t = (math.min(sOpenTimer, sPageTimer) - (i - first) * 1.2) / 8
        V.fade = fade * ease_out(t * 1.3)
        draw_card(i, list[i], x, y - (1 - ease_out(t)) * 24, i == sCursor, tags)
    end
    V.fade = fade
    if pages > 1 then draw_page_tabs(page, pages) end

    -- footer: name under the cursor + controls
    local f = list[sCursor]
    if f ~= nil then
        djui_hud_set_font(FONT_HUD)
        local label = f.name:upper()
        local w = text_w(label, 1)
        shadow_text(label, (VW - w) / 2, 205, 1, 255, 214, 40, 255, 1.5)
        djui_hud_set_font(FONT_NORMAL)
        local hint
        if friend_ok(f) then
            hint = "A / click: choose      B / START: close      L + START: reopen"
            if pages > 1 then hint = "A / click: choose      L / R: page      B / START: close" end
        else
            hint = "\\#ff8080\\" .. f.name .. "'s model failed to load"
        end
        local hw = text_w(hint, 0.22)
        shadow_text(hint, (VW - hw) / 2, 222, 0.22, 200, 210, 235, 255)
    end

    if sMouseShow > 0 then
        V.fade = 1
        draw_mouse_cursor((sMouseX - V.ox) / V.u, (sMouseY - V.oy) / V.u)
    end
    V.fade = 1
end

---------------------------------------------------------------------------------------------

hook_event(HOOK_BEFORE_MARIO_UPDATE, on_before_mario_update)
hook_event(HOOK_UPDATE, on_update)
hook_event(HOOK_ON_SYNC_VALID, on_sync_valid)
hook_event(HOOK_ON_WARP, on_warp)
hook_event(HOOK_ON_HUD_RENDER, on_hud_render)

if hook_mod_menu_button ~= nil then
    hook_mod_menu_button("Choose your friend", function() open_menu() end)
end
