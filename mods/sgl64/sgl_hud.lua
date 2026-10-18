-- Super Gatorlator 64: HUD kit for missions (banners, panels, timers, counters, prompts, world
-- markers, results boards, toasts). Used by sgl_mission.lua (framework) and the stage mission files.
--
-- Shared layout at RESOLUTION_N64 (240 units tall): counters in the top
-- corners, navigation at top centre, objective card at (10, 46), timer on the
-- right, prompts above the bottom edge, and one quiet notification below them.
-- Use FONT_NORMAL for interface text and keep the centre clear for gameplay.
-- All dimensions are logical units and text is measured before it is drawn.

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
function sgl_hud_blocked(allowLogin)
    if is_game_paused() then return true end
    local campusMenu = rawget(_ENV, "sgl_campus_menu_is_open")
    if campusMenu ~= nil and campusMenu() then return true end
    if not allowLogin and _G.sglLoginPanel ~= nil and _G.sglLoginPanel() ~= nil then return true end
    local open = _G.sglCharSelectIsOpen   -- nil when charselect.lua is not loaded
    return open ~= nil and open() == true
end

-- Shared reservation for the bottom-left map. Menus hide it automatically.
local function minimap_box()
    local getBox = rawget(_ENV, "sgl_minimap_rect")
    return getBox ~= nil and getBox() or nil
end

function sgl_hud_clear_of_minimap(x, y, w, h)
    local box = minimap_box()
    return box == nil or x + w < box.x - 4 or x > box.x + box.w + 4
        or y + h < box.y - 4 or y > box.y + box.h + 4
end

local function bottom_lane(W)
    local box = minimap_box()
    local left = box ~= nil and box.x + box.w + 10 or 8
    return left, W - 8, (left + W - 8) / 2
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
    djui_hud_print_text(text, x + 0.5, y + 0.5, scale)
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
    return math.max(0, room / w)
end

-- Word-wrap at a readable size, with a bounded line count. Long single words
-- are fitted when drawn, so player names and mission titles cannot spill out.
function sgl_hud_wrap(text, scale, width, limit)
    local lines, line = {}, ""
    for word in tostring(text or ""):gmatch("%S+") do
        local candidate = line == "" and word or line .. " " .. word
        if line ~= "" and sgl_hud_text_width(candidate, scale) > width then
            lines[#lines + 1] = line
            line = word
        else
            line = candidate
        end
    end
    if line ~= "" then lines[#lines + 1] = line end
    if limit ~= nil and #lines > limit then
        while #lines > limit do table.remove(lines) end
        lines[limit] = lines[limit] .. "..."
    end
    return lines
end

function sgl_hud_text_fit(text, x, y, scale, width, col, alpha)
    local measured = sgl_hud_text_width(text, scale)
    if measured > width then scale = scale * width / measured end
    sgl_hud_text(text, x, y, scale, col, alpha)
end

-- Area/mission introductions share the objective-card position and typography.
function sgl_hud_banner(kicker, title, sub, age, duration)
    local alpha = sgl_hud_fade(age, duration)
    if alpha <= 0 then return end
    local W = sgl_hud_setup(FONT_NORMAL)
    local x, y, width = 10, 46, math.min(142, W - 112)
    local lines = {}
    if kicker then lines[#lines + 1] = { kicker, SGL_HUD_GREY, 0.20 } end
    for _, line in ipairs(sgl_hud_wrap(title, 0.24, width - 16, 2)) do
        lines[#lines + 1] = { line, SGL_HUD_GOLD, 0.24 }
    end
    for _, line in ipairs(sgl_hud_wrap(sub, 0.21, width - 16, 3)) do
        lines[#lines + 1] = { line, SGL_HUD_WHITE, 0.21 }
    end
    local height = 12
    for _, line in ipairs(lines) do height = height + LINE * line[3] + 2 end
    sZone.panelRight, sZone.panelFrame, sZone.panelBottom = x + width - 4, get_global_timer(), y - 4 + height
    sgl_hud_rect(x - 4, y - 4, width, height, 10, 18, 30, 185 * alpha)
    sgl_hud_rect(x - 4, y - 4, 2, height, 238, 145, 65, 210 * alpha)
    for _, line in ipairs(lines) do
        sgl_hud_text_fit(line[1], x + 3, y + 2, line[3], width - 16, line[2], alpha)
        y = y + LINE * line[3] + 2
    end
end

-- Objective/progress card: a fixed reading column, never a full-width overlay.
function sgl_hud_panel(lines, x, y)
    if lines == nil or #lines == 0 then return y end
    local W, H = sgl_hud_setup(FONT_NORMAL)
    x, y = x or 10, y or 46
    local width = math.min(156, (W - 32) / 2, W - x - 108)
    local rows, height = {}, 7
    local maxHeight = math.min(106, H - y - 66)
    local mapBox = minimap_box()
    if mapBox ~= nil then maxHeight = math.min(maxHeight, mapBox.y - y - 8) end
    for index, line in ipairs(lines) do
        local scale = math.min(line[3] or 0.21, index == 1 and 0.24 or 0.21)
        -- Mission and navigation lines carry actionable details. Keep each one
        -- intact and fit it to the reading column rather than silently dropping
        -- later rows when a long hint wraps.
        local measured = sgl_hud_text_width(line[1], scale)
        if measured > width - 14 then scale = scale * (width - 14) / measured end
        rows[#rows + 1] = { line[1], line[2] or SGL_HUD_WHITE, scale }
        height = height + LINE * scale + 1
    end
    if height > maxHeight and height > 7 then
        local factor = math.max(0.5, (maxHeight - 7) / (height - 7))
        height = 7
        for _, row in ipairs(rows) do
            row[3] = row[3] * factor
            height = height + LINE * row[3] + 1
        end
    end
    local contentWidth = 0
    for _, row in ipairs(rows) do contentWidth = math.max(contentWidth, sgl_hud_text_width(row[1], row[3])) end
    width = math.min(width, contentWidth + 14)
    sZone.panelBottom = y - 4 + height
    sgl_hud_rect(x - 4, y - 4, width, height, 10, 18, 30, 170)
    sgl_hud_rect(x - 4, y - 4, 2, height, 238, 145, 65, 200)
    sZone.panelRight, sZone.panelFrame = x + width - 4, get_global_timer()
    for _, line in ipairs(rows) do
        sgl_hud_text_fit(line[1], x + 3, y + 1, line[3], width - 14, line[2], 1)
        y = y + LINE * line[3] + 1
    end
    return y + 4
end

-- Short game cues retain emphasis without giant arcade lettering.
function sgl_hud_big(text, col, scale, alpha, y)
    local W, H = sgl_hud_setup(FONT_NORMAL)
    scale = math.min((scale or 2) * 0.24, #text <= 3 and 0.65 or 0.40)
    scale = scale * sgl_hud_fit(sgl_hud_text_width(text, scale), W, 40)
    local cx, cy = W / 2, y or (H / 2 + 10)
    local width = sgl_hud_text_width(text, scale)
    if not sgl_hud_clear_of_minimap(cx - width / 2, cy, width, LINE * scale) then
        local left, right
        left, right, cx = bottom_lane(W)
        scale = scale * sgl_hud_fit(width, right - left, 4)
    end
    sgl_hud_text_center(text, cx, cy, scale, col or SGL_HUD_GOLD, alpha or 1)
end

-- Compact right-column timer, using the same interface font.
function sgl_hud_timer(frames, x, y, label, col)
    sgl_hud_setup(FONT_NORMAL)
    sZone.rightFrame = get_global_timer()
    if label then sgl_hud_text(label, x, y, 0.21, SGL_HUD_GREY, 1) end
    sgl_hud_text(sgl_hud_format_time(frames), x, y + (label and 9 or 0), 0.34, col or SGL_HUD_WHITE, 1)
    djui_hud_set_font(FONT_NORMAL)
end

-- something is drawn in the right column this frame (race timer, the Reitz crane side view): toasts keep
-- clear of it
function sgl_hud_reserve_right()
    sZone.rightFrame = get_global_timer()
end

-- Collect prompts so a nearby NPC cannot paint over a mission or team action.
-- Rendering reads the previous HUD pass (at most one frame old) because callers
-- are loaded after this shared HUD module.
local sPrompt = nil
function sgl_hud_prompt(text, sub, alpha, priority)
    local now = get_global_timer()
    priority = priority or 10
    if sPrompt ~= nil and sPrompt.frame == now and sPrompt.priority > priority then return end
    sPrompt = { text = text, sub = sub, alpha = alpha or 1, priority = priority, frame = now }
end

local function render_prompt()
    local prompt = sPrompt
    local blocked = sgl_hud_blocked()
    if prompt == nil or get_global_timer() - prompt.frame > 1 or blocked then return end
    local alpha = prompt.alpha
    if alpha <= 0 then return end
    local W, H = sgl_hud_setup(FONT_NORMAL)
    local laneLeft, laneRight = bottom_lane(W)
    local cx = W / 2
    -- Keep prompts centered on the screen, with symmetric clearance from the minimap.
    local centeredWidth = 2 * math.min(cx - laneLeft, laneRight - cx)
    local titleSize, bodySize = 0.23, 0.20
    local maxWidth = math.min(prompt.priority <= 1 and 140 or 210, centeredWidth)
    local width = math.max(sgl_hud_text_width(prompt.text, titleSize), sgl_hud_text_width(prompt.sub or "", bodySize)) + 16
    width = math.min(maxWidth, width)
    local lines = sgl_hud_wrap(prompt.sub, bodySize, width - 16, 2)
    local height = 15 + #lines * 8
    local y = H - 28 - height
    sgl_hud_rect(cx - width / 2, y, width, height, 10, 18, 30, 190 * alpha)
    local titleScale = titleSize * sgl_hud_fit(sgl_hud_text_width(prompt.text, titleSize), width, 8)
    sgl_hud_text_center(prompt.text, cx, y + 4, titleScale, SGL_HUD_GOLD, alpha)
    for i, line in ipairs(lines) do
        local scale = bodySize * sgl_hud_fit(sgl_hud_text_width(line, bodySize), width, 8)
        sgl_hud_text_center(line, cx, y + 12 + (i - 1) * 8, scale, SGL_HUD_GREY, alpha)
    end
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
    local track = rawget(_ENV, "sgl_minimap_track")
    if track ~= nil then track(pos, label, col) end
    local W, H = sgl_hud_setup(FONT_NORMAL)
    local out = { x = 0, y = 0, z = 0 }
    local front = djui_hud_world_pos_to_screen_pos(pos, out)
    col = col or SGL_HUD_GOLD
    local text = marker_text(pos, label, me)
    if front and out.x >= -20 and out.x <= W + 20 and out.y >= -20 and out.y <= H + 20 then
        local x, y = out.x, out.y
        local labelWidth = sgl_hud_text_width(text, 0.23)
        if not sgl_hud_clear_of_minimap(x - math.max(4, labelWidth / 2), y - 14, math.max(8, labelWidth), 20) then return true end
        if get_global_timer() - sZone.panelFrame <= 1 and x < sZone.panelRight + 12
            and y > 28 and y < (sZone.panelBottom or 38) + 16 then return true end
        sgl_hud_rect(x - 3, y - 3, 6, 6, 0, 0, 0, 160)
        sgl_hud_rect(x - 2, y - 2, 4, 4, col[1], col[2], col[3], 255)
        if text ~= "" then sgl_hud_text_center(text, x, y - 12, 0.23, col, 1) end
        return true
    end
    if noEdge then return false end
    -- edge arrow: inside the screen, below the vanilla HUD row, above the bottom prompt
    local x, y, ux, uy = sgl_hud_edge_point(out.x, out.y, front, W, H, 12, 40, W - 12, H - 36)
    local cardVisible = get_global_timer() - sZone.panelFrame <= 1
    if cardVisible and x < sZone.panelRight + 12 and y < (sZone.panelBottom or 38) + 20 then
        y = (sZone.panelBottom or 38) + 24
    end
    local mapBox = minimap_box()
    if mapBox ~= nil and not sgl_hud_clear_of_minimap(x - 14, y - 14, 28, 28) then
        x = mapBox.x + mapBox.w + 18
    end
    for k = 0, 2 do   -- arrow head of three squares, the smallest at the tip
        local s = 3 + 2 * k
        local px, py = x - ux * k * 4, y - uy * k * 4
        sgl_hud_rect(px - s / 2 - 1, py - s / 2 - 1, s + 2, s + 2, 0, 0, 0, 140)
        sgl_hud_rect(px - s / 2, py - s / 2, s, s, col[1], col[2], col[3], 230)
    end
    if text ~= "" then
        local sc = 0.22
        local w = sgl_hud_text_width(text, sc)
        local tx = math.max(4 + w / 2, math.min(W - 4 - w / 2, x - ux * 22))
        local ty = math.max(36, math.min(H - 44, y - uy * 22 - 5))
        -- clamping to the screen edge can slide a long label back over its own arrow (a left/right edge
        -- arrow at mid height): move the label just below the arrow, or above it near the bottom
        if math.abs(tx - x) < w / 2 + 8 and math.abs(ty + 4 - y) < 12 then
            ty = (y + 10 <= H - 44) and (y + 10) or (y - 20)
        end
        if cardVisible and tx - w / 2 < sZone.panelRight + 4 and ty < (sZone.panelBottom or 38) + 6 then
            ty = (sZone.panelBottom or 38) + 8
        end
        if mapBox ~= nil and not sgl_hud_clear_of_minimap(tx - w / 2, ty, w, 10) then
            local available = W - mapBox.x - mapBox.w - 16
            if w > available then sc, w = sc * available / w, available end
            tx = math.min(W - 4 - w / 2, mapBox.x + mapBox.w + 8 + w / 2)
        end
        sgl_hud_text_center(text, tx, ty, sc, col, 1)
    end
    return "edge"
end

-- results board (race finishes): rows = { { name, frames, highlight }, ... }
function sgl_hud_board(title, rows, x, y, footer)
    sgl_hud_setup(FONT_NORMAL)
    local n = math.min(#rows, 8)
    local w = 150
    local footerLines = sgl_hud_wrap(footer, 0.22, w, 2)
    local h = 20 + n * 11 + #footerLines * 9
    sgl_hud_rect(x - 4, y - 4, w + 8, h, 10, 22, 70, 200)
    sgl_hud_rect(x - 4, y - 4, w + 8, 2, 250, 110, 30, 255)
    sgl_hud_text_fit(title, x, y, 0.28, w, SGL_HUD_GOLD, 1)
    y = y + 15
    for i = 1, n do
        local r = rows[i]
        local col = r[3] and SGL_HUD_GREEN or SGL_HUD_WHITE
        sgl_hud_text_fit(i .. ". " .. r[1], x, y, 0.25, w - 65, col, 1)
        local t = sgl_hud_format_time(r[2])
        sgl_hud_text(t, x + w - sgl_hud_text_width(t, 0.25), y, 0.25, col, 1)
        y = y + 11
    end
    for _, line in ipairs(footerLines) do
        sgl_hud_text_fit(line, x, y + 1, 0.22, w, SGL_HUD_GREY, 1)
        y = y + 9
    end
end

---------------------------------------------------------------------------------------------
-- Notifications: one quiet line at the bottom; the newest notice takes priority.
---------------------------------------------------------------------------------------------
local sToasts = {}

function sgl_hud_toast(text, seconds, col)
    table.insert(sToasts, { text = text, col = col or SGL_HUD_WHITE, age = 0,
        dur = math.floor((seconds or 3) * 30) })
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
    local W, H = sgl_hud_setup(FONT_NORMAL)
    local laneLeft, laneRight, cx = bottom_lane(W)
    local available = laneRight - laneLeft - 12
    local count = math.min(#sToasts, 3)
    local first = #sToasts - count + 1
    for i = first, #sToasts do
        local t = sToasts[i]
        local alpha = sgl_hud_fade(t.age, t.dur, 4, 10)
        if alpha > 0 then
            local scale = 0.22
            local width = sgl_hud_text_width(t.text, scale)
            if width > available then scale = scale * available / width end
            width = sgl_hud_text_width(t.text, scale)
            local y = H - 18 - (#sToasts - i) * 14
            sgl_hud_rect(cx - width / 2 - 6, y - 3, width + 12, 13, 10, 18, 30, 170 * alpha)
            sgl_hud_text_center(t.text, cx, y, scale, t.col, alpha)
        end
    end
end

hook_event(HOOK_ON_HUD_RENDER, render_prompt)

hook_event(HOOK_UPDATE, update_toasts)
hook_event(HOOK_ON_HUD_RENDER, render_toasts)
