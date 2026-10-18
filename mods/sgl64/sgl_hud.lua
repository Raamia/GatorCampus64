-- Super Gatorlator 64: HUD kit for missions (banners, panels, timers, counters, prompts, world
-- markers, results boards, toasts). Used by sgl_mission.lua (framework) and the stage mission files.
--
-- Everything is drawn from HOOK_ON_HUD_RENDER at RESOLUTION_N64: 240 units tall, the width grows with
-- the window's aspect ratio (djui_hud_get_screen_width()). The vanilla HUD sits along the top edge
-- (lives top-left, coins, stars top-right), so mission UI uses:
--   left panel      x 8, y 34 ..             (mission name, state, counters)
--   right column    x W-92, y 34 (race timer, Reitz crane side view x W-84, y 32 .. 192);
--                   results board x W-166, y 84 ..
--   toasts          y 34 / 49 / 64, centred in the space between the panel and the right column
--                   (shrunk to fit), at most 3
--   banner          centre, y 84 .. 136      (act start: the first seconds of an act / round)
--   big text        centre, y 88             (countdown digits, GO!, chant, STAR!, TRY AGAIN)
--   prompt          centre, bottom           (Study Group invite, players needed, leave together)
--   markers         over the target; off screen an arrow on the screen edge (y 40 .. H-36)
-- The banner and the big text never show together (sgl_mission.lua hides the banner once play
-- is under way).
-- Colours passed to djui_hud_set_color must be integers (the binding rejects 127.5), hence c8().
-- FONT_HUD only has 0-9, A-Z and ! # ? & % @ $ , * . ^ ' " / - ~ + (no colon), so times use the
-- vanilla race-timer style 1'05"32.

SGL_HUD_GOLD = { 255, 215, 0 }
SGL_HUD_ORANGE = { 250, 110, 30 }
SGL_HUD_BLUE = { 90, 150, 255 }
SGL_HUD_WHITE = { 255, 255, 255 }
SGL_HUD_GREY = { 190, 190, 200 }
SGL_HUD_GREEN = { 120, 255, 140 }
SGL_HUD_RED = { 255, 110, 110 }

local LINE = 32          -- FONT_NORMAL line height at scale 1 (N64 units)

-- what was drawn where in the last frames (toasts keep clear of the panel and the race timer)
local sZone = { panelRight = 0, panelFrame = -100, rightFrame = -100 }

local function c8(v)
    v = math.floor((v or 0) + 0.5)
    if v < 0 then return 0 end
    if v > 255 then return 255 end
    return v
end

local function clamp01(v)
    if v < 0 then return 0 end
    if v > 1 then return 1 end
    return v
end

---------------------------------------------------------------------------------------------
-- pure helpers (unit tested in tools/luatest)
---------------------------------------------------------------------------------------------

-- true while mission UI must not draw: the game is paused, or the character select menu
-- (charselect.lua, _G.sglCharSelectIsOpen) covers the screen. Every HOOK_ON_HUD_RENDER of the mod
-- checks it; hooks run in file load order, so charselect.lua's menu is drawn BEFORE everything else
-- and would otherwise be painted over.
function sgl_hud_blocked()
    if is_game_paused() then return true end
    local campusMenu = rawget(_ENV, "sgl_campus_menu_is_open")
    if campusMenu ~= nil and campusMenu() then return true end
    local open = _G.sglCharSelectIsOpen   -- nil when charselect.lua is not loaded
    return open ~= nil and open() == true
end

-- frames (30 per second) -> 1'05"32 (minutes ' seconds " hundredths), like the vanilla timer
function sgl_hud_format_time(frames)
    if frames == nil or frames < 0 then frames = 0 end
    local cs = math.floor(frames * 100 / 30)
    local m = cs // 6000
    local s = (cs // 100) % 60
    local c = cs % 100
    return string.format("%d'%02d\"%02d", m, s, c)
end

-- whole seconds -> 1'05
function sgl_hud_format_seconds(sec)
    if sec == nil or sec < 0 then sec = 0 end
    sec = math.floor(sec)
    return string.format("%d'%02d", sec // 60, sec % 60)
end

-- fade-in / hold / fade-out alpha (0..1) for something shown `age` frames ago for `duration` frames
function sgl_hud_fade(age, duration, fadeIn, fadeOut)
    fadeIn = fadeIn or 8
    fadeOut = fadeOut or 12
    if age < 0 or age >= duration then return 0 end
    local a = 1
    if age < fadeIn then a = age / fadeIn end
    if duration - age < fadeOut then a = math.min(a, (duration - age) / fadeOut) end
    return clamp01(a)
end

---------------------------------------------------------------------------------------------
-- drawing primitives
---------------------------------------------------------------------------------------------

-- N64 resolution + font; returns screen width, height
function sgl_hud_setup(font)
    djui_hud_set_resolution(RESOLUTION_N64)
    djui_hud_set_font(font or FONT_NORMAL)
    return djui_hud_get_screen_width(), djui_hud_get_screen_height()
end

function sgl_hud_rect(x, y, w, h, r, g, b, a)
    djui_hud_set_color(c8(r), c8(g), c8(b), c8(a))
    djui_hud_render_rect(x, y, w, h)
end

function sgl_hud_text_width(text, scale)
    return djui_hud_measure_text(text) * scale
end

-- text with a 1-unit drop shadow; col = { r, g, b }, alpha 0..1
function sgl_hud_text(text, x, y, scale, col, alpha)
    col = col or SGL_HUD_WHITE
    alpha = alpha or 1
    djui_hud_set_color(0, 0, 0, c8(200 * alpha))
    djui_hud_print_text(text, x + 1, y + 1, scale)
    djui_hud_set_color(c8(col[1]), c8(col[2]), c8(col[3]), c8(255 * alpha))
    djui_hud_print_text(text, x, y, scale)
end

function sgl_hud_text_center(text, cx, y, scale, col, alpha)
    local w = sgl_hud_text_width(text, scale)
    sgl_hud_text(text, cx - w / 2, y, scale, col, alpha)
    return w
end

---------------------------------------------------------------------------------------------
-- widgets
---------------------------------------------------------------------------------------------

-- scale factor (<= 1) that fits a text block of width w (at scale 1 factor) into the screen width W
-- with `pad` on both sides (a 4:3 window is only 320 units wide)
function sgl_hud_fit(w, W, pad)
    local room = W - 2 * (pad or 8)
    if w <= room or w <= 0 then return 1 end
    return math.max(0.5, room / w)
end

-- act-start banner: kicker (small, orange), title (gold), sub (white). age/duration in frames.
-- Shrinks to fit narrow windows.
function sgl_hud_banner(kicker, title, sub, age, duration)
    local alpha = sgl_hud_fade(age, duration)
    if alpha <= 0 then return end
    local W = sgl_hud_setup(FONT_NORMAL)
    local cx, y = W / 2, 84
    local wk = kicker and sgl_hud_text_width(kicker, 0.32) or 0
    local wt = sgl_hud_text_width(title, 0.55)
    local ws = sub and sgl_hud_text_width(sub, 0.34) or 0
    local k = sgl_hud_fit(math.max(wk, wt, ws) + 24, W, 4)
    local w = (math.max(wk, wt, ws) + 24) * k
    local h = 8 + (kicker and 12 or 0) + 19 + (sub and 13 or 0) + 6
    sgl_hud_rect(cx - w / 2, y - 6, w, h, 10, 22, 70, 190 * alpha)
    sgl_hud_rect(cx - w / 2, y - 6, w, 2, 250, 110, 30, 255 * alpha)
    sgl_hud_rect(cx - w / 2, y - 6 + h - 2, w, 2, 250, 110, 30, 255 * alpha)
    if kicker then
        sgl_hud_text_center(kicker, cx, y, 0.32 * k, SGL_HUD_ORANGE, alpha)
        y = y + 12
    end
    sgl_hud_text_center(title, cx, y, 0.55 * k, SGL_HUD_GOLD, alpha)
    y = y + 19
    if sub then sgl_hud_text_center(sub, cx, y, 0.34 * k, SGL_HUD_WHITE, alpha) end
end

-- left panel: lines = { { text, col, scale }, ... } (col / scale optional). Returns the bottom y.
function sgl_hud_panel(lines, x, y)
    if lines == nil or #lines == 0 then return y end
    sgl_hud_setup(FONT_NORMAL)
    x, y = x or 8, y or 34
    local w, h = 0, 6
    for _, l in ipairs(lines) do
        local sc = l[3] or 0.34
        w = math.max(w, sgl_hud_text_width(l[1], sc))
        h = h + LINE * sc + 1
    end
    sgl_hud_rect(x - 4, y - 3, w + 8, h, 0, 0, 0, 120)
    sgl_hud_rect(x - 4, y - 3, 2, h, 250, 110, 30, 220)
    sZone.panelRight = x + w + 4
    sZone.panelFrame = get_global_timer()
    for _, l in ipairs(lines) do
        local sc = l[3] or 0.34
        sgl_hud_text(l[1], x, y, sc, l[2] or SGL_HUD_WHITE, 1)
        y = y + LINE * sc + 1
    end
    return y + 3
end

-- big centred FONT_HUD text (countdown digits, STAR!, GO!). FONT_HUD glyphs only (see header).
function sgl_hud_big(text, col, scale, alpha, y)
    local W, H = sgl_hud_setup(FONT_HUD)
    scale = scale or 2
    sgl_hud_text_center(text, W / 2, y or 88, scale, col or SGL_HUD_GOLD, alpha or 1)
    djui_hud_set_font(FONT_NORMAL)
end

-- timer in FONT_HUD at (x, y), label in FONT_NORMAL above it
function sgl_hud_timer(frames, x, y, label, col)
    sgl_hud_setup(FONT_NORMAL)
    sZone.rightFrame = get_global_timer()
    if label then sgl_hud_text(label, x, y, 0.3, SGL_HUD_GREY, 1) end
    djui_hud_set_font(FONT_HUD)
    sgl_hud_text(sgl_hud_format_time(frames), x, y + (label and 10 or 0), 0.75, col or SGL_HUD_WHITE, 1)
    djui_hud_set_font(FONT_NORMAL)
end

-- something is drawn in the right column this frame (race timer, the Reitz crane side view): toasts keep
-- clear of it
function sgl_hud_reserve_right()
    sZone.rightFrame = get_global_timer()
end

-- bottom-centre prompt (Study Group invites, "stand in the start box", ...); shrinks to fit
function sgl_hud_prompt(text, sub, alpha)
    alpha = alpha or 1
    if alpha <= 0 then return end
    local W, H = sgl_hud_setup(FONT_NORMAL)
    local wt = sgl_hud_text_width(text, 0.36)
    local ws = sub and sgl_hud_text_width(sub, 0.3) or 0
    local k = sgl_hud_fit(math.max(wt, ws) + 16, W, 4)
    local w = (math.max(wt, ws) + 16) * k
    local h = sub and 28 or 17
    local y = H - 48 - h
    sgl_hud_rect(W / 2 - w / 2, y, w, h, 0, 0, 0, 150 * alpha)
    sgl_hud_text_center(text, W / 2, y + 3, 0.36 * k, SGL_HUD_GOLD, alpha)
    if sub then sgl_hud_text_center(sub, W / 2, y + 15, 0.3 * k, SGL_HUD_WHITE, alpha) end
end

-- pure: where an off-screen marker sticks to the screen edge. sx, sy = projected screen position
-- (front = true) or camera-space x (right) / y (up) of a point behind the camera (front = false).
-- -> x, y on the inset edge rectangle [l, r] x [t, b], and the unit direction (ux, uy) from the centre
function sgl_hud_edge_point(sx, sy, front, W, H, l, t, r, b)
    local cx, cy = W / 2, H / 2
    local dx, dy
    if front then
        dx, dy = sx - cx, sy - cy
    else
        -- behind the camera: turn toward its side, the arrow sits low on that edge
        dx = (sx >= 0) and 1 or -1
        dy = 0.3
    end
    local len = math.sqrt(dx * dx + dy * dy)
    if len < 1e-6 then dx, dy, len = 0, 1, 1 end
    local ux, uy = dx / len, dy / len
    local kx = (ux > 0) and (r - cx) / ux or ((ux < 0) and (l - cx) / ux or math.huge)
    local ky = (uy > 0) and (b - cy) / uy or ((uy < 0) and (t - cy) / uy or math.huge)
    local k = math.min(kx, ky)
    return cx + ux * k, cy + uy * k, ux, uy
end

local function marker_text(pos, label, me)
    local text = label or ""
    if me ~= nil then
        local dx, dy, dz = pos.x - me.pos.x, pos.y - me.pos.y, pos.z - me.pos.z
        local d = math.floor(math.sqrt(dx * dx + dy * dy + dz * dz) / 100 + 0.5)
        text = text .. (text ~= "" and "  " or "") .. d .. " m"
    end
    return text
end

-- line of sight from the camera to a world position, for labels drawn on the HUD over the world (door
-- labels, NPC name tags): HUD text is drawn on top of everything, so without this check it shows through
-- walls. A collision ray (walls, floors, ceilings; static and object collision) from the camera
-- (gLakituState.curPos) to pos; a hit before 95% of the way hides the label. The answer is cached per
-- key for SIGHT_FRAMES frames, so a label costs one ray every few frames. Mission markers stay visible
-- through walls on purpose (they are waypoints).
local SIGHT_FRAMES = 4
local sSight = {}
function sgl_hud_in_sight(key, pos)
    if collision_find_surface_on_ray == nil then return true end
    local ls = gLakituState
    if ls == nil or ls.curPos == nil then return true end
    local now = get_global_timer()
    local c = sSight[key]
    if c ~= nil and now >= c.t and now - c.t < SIGHT_FRAMES then return c.v end
    local cp = ls.curPos
    local dx, dy, dz = pos.x - cp.x, pos.y - cp.y, pos.z - cp.z
    local v = true
    local hit = collision_find_surface_on_ray(cp.x, cp.y, cp.z, dx, dy, dz)
    if hit ~= nil and hit.surface ~= nil then
        local hp = hit.hitPos
        if hp == nil then
            v = false
        else
            local f = ((hp.x - cp.x) ^ 2 + (hp.y - cp.y) ^ 2 + (hp.z - cp.z) ^ 2) / math.max(1, dx * dx + dy * dy + dz * dz)
            v = f >= 0.95 * 0.95
        end
    end
    sSight[key] = { t = now, v = v }
    return v
end

-- world marker: a small diamond + label + distance over a world position. me = the local MarioState
-- (for the distance). Off screen or behind the camera it sticks to the screen edge as an arrow pointing
-- the way to turn, with the label beside it (noEdge = true: draw nothing then).
-- -> true when the target is on screen, "edge" when the edge arrow was drawn, false otherwise.
function sgl_hud_marker(pos, label, col, me, noEdge)
    local W, H = sgl_hud_setup(FONT_NORMAL)
    local out = { x = 0, y = 0, z = 0 }
    local front = djui_hud_world_pos_to_screen_pos(pos, out)
    col = col or SGL_HUD_GOLD
    local text = marker_text(pos, label, me)
    if front and out.x >= -20 and out.x <= W + 20 and out.y >= -20 and out.y <= H + 20 then
        local x, y = out.x, out.y
        sgl_hud_rect(x - 3, y - 3, 6, 6, 0, 0, 0, 160)
        sgl_hud_rect(x - 2, y - 2, 4, 4, col[1], col[2], col[3], 255)
        if text ~= "" then sgl_hud_text_center(text, x, y - 14, 0.28, col, 1) end
        return true
    end
    if noEdge then return false end
    -- edge arrow: inside the screen, below the vanilla HUD row, above the bottom prompt
    local x, y, ux, uy = sgl_hud_edge_point(out.x, out.y, front, W, H, 12, 40, W - 12, H - 36)
    for k = 0, 2 do   -- arrow head of three squares, the smallest at the tip
        local s = 3 + 2 * k
        local px, py = x - ux * k * 4, y - uy * k * 4
        sgl_hud_rect(px - s / 2 - 1, py - s / 2 - 1, s + 2, s + 2, 0, 0, 0, 140)
        sgl_hud_rect(px - s / 2, py - s / 2, s, s, col[1], col[2], col[3], 230)
    end
    if text ~= "" then
        local sc = 0.26
        local w = sgl_hud_text_width(text, sc)
        local tx = math.max(4 + w / 2, math.min(W - 4 - w / 2, x - ux * 22))
        local ty = math.max(36, math.min(H - 44, y - uy * 22 - 5))
        sgl_hud_text_center(text, tx, ty, sc, col, 1)
    end
    return "edge"
end

-- results board (race finishes): rows = { { name, frames, highlight }, ... }
function sgl_hud_board(title, rows, x, y, footer)
    sgl_hud_setup(FONT_NORMAL)
    local n = math.min(#rows, 8)
    local w = 150
    local h = 20 + n * 11 + (footer and 12 or 0)
    sgl_hud_rect(x - 4, y - 4, w + 8, h, 10, 22, 70, 200)
    sgl_hud_rect(x - 4, y - 4, w + 8, 2, 250, 110, 30, 255)
    sgl_hud_text(title, x, y, 0.36, SGL_HUD_GOLD, 1)
    y = y + 15
    for i = 1, n do
        local r = rows[i]
        local col = r[3] and SGL_HUD_GREEN or SGL_HUD_WHITE
        sgl_hud_text(i .. ". " .. r[1], x, y, 0.3, col, 1)
        local t = sgl_hud_format_time(r[2])
        sgl_hud_text(t, x + w - sgl_hud_text_width(t, 0.3), y, 0.3, col, 1)
        y = y + 11
    end
    if footer then sgl_hud_text(footer, x, y + 1, 0.28, SGL_HUD_GREY, 1) end
end

---------------------------------------------------------------------------------------------
-- toasts: short one-line notices stacked under the top HUD (newest at the bottom)
---------------------------------------------------------------------------------------------
local sToasts = {}

function sgl_hud_toast(text, seconds, col)
    table.insert(sToasts, { text = text, col = col or SGL_HUD_WHITE, age = 0, dur = math.floor((seconds or 3) * 30) })
    while #sToasts > 3 do table.remove(sToasts, 1) end
end

function sgl_hud_toast_count() return #sToasts end

-- ages advance per game tick (HOOK_UPDATE, 30 Hz); the HUD may render more often than that
local function update_toasts()
    if #sToasts == 0 then return end
    local keep = {}
    for _, t in ipairs(sToasts) do
        t.age = t.age + 1
        if t.age < t.dur then table.insert(keep, t) end
    end
    sToasts = keep
end

local function render_toasts()
    if #sToasts == 0 or sgl_hud_blocked() then return end
    local W = sgl_hud_setup(FONT_NORMAL)
    local now = get_global_timer()
    local left = (now - sZone.panelFrame <= 2) and (sZone.panelRight + 6) or 8
    local right = W - 8 - ((now - sZone.rightFrame <= 2) and 96 or 0)
    if right - left < 120 then left, right = 8, W - 8 end
    local cx = (left + right) / 2
    local y = 34
    for _, t in ipairs(sToasts) do
        local a = sgl_hud_fade(t.age, t.dur, 4, 10)
        if a > 0 then
            local sc = 0.32
            local w = sgl_hud_text_width(t.text, sc)
            if w > right - left - 10 then
                sc = sc * (right - left - 10) / w
                w = sgl_hud_text_width(t.text, sc)
            end
            sgl_hud_rect(cx - w / 2 - 5, y - 2, w + 10, 14, 0, 0, 0, 130 * a)
            sgl_hud_text_center(t.text, cx, y, sc, t.col, a)
            y = y + 15
        end
    end
end

hook_event(HOOK_UPDATE, update_toasts)
hook_event(HOOK_ON_HUD_RENDER, render_toasts)
