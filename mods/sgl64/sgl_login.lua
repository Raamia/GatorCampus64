-- Super Gatorlator 64: Gator Pass, the in-game login (docs/web_platform_spec.md §7.1, §7.2).
--
--   /login            ask the hosted server for a login code: a panel shows a QR code (scan it with a
--                     phone) plus "login.chooseyourgator.select/activate" and the code to type there,
--                     the time left and "Waiting for approval...". B or /login cancel closes it.
--   /link <code>      link with the 6-character code the website shows after you log in there
--                     (the fallback when the QR / device flow is a problem).
-- Once the account is linked the server broadcasts `verified`: every client marks that player
-- verified, which shows as
--   * a gold "*" in front of the name tag above the player's head (HOOK_ON_NAMETAGS_RENDER),
--   * "GATOR PASS" in gold as the player's description in the player list (TAB),
--   * a "*" on the player's name tag pill in the character select cards (charselect.lua),
-- and the player's own client selects their guest gator (guest_<slot>) when their account owns one.
--
-- Transport: sgl_bridge.lua (loads before this file) relays client -> host -> bridge process and back:
--   _G.sglBridgeEmit(t, fields)        client -> host: login_req { name }, link_req { name, code }
--   _G.sglBridgeOnCommand(name, fn)    fn(cmd) on the client a command targets:
--       login_code   { gi, user_code, uri, expires }   uri = verification_uri_complete (the QR content),
--                                                       expires = seconds left (or a Unix time)
--       verified     { gi, nickname, guest_slot }       broadcast; guest_slot may be nil
--       login_failed { gi, reason }                     "expired", "denied" / "access_denied", or text
-- Both are looked up when used, so this file also loads (and stays inert) without the bridge: offline
-- /login and /link only answer "Login is only available on the hosted server".
-- The verified marks are client-side decoration; the API is the source of truth (spec §14).

local ACTIVATE_TEXT = "login.chooseyourgator.select/activate"
local REQUEST_TIMEOUT = 20 * 30   -- frames to wait for login_code after /login (and for /link's answer)
local RESULT_FRAMES = 5 * 30      -- frames the success / failure panel stays up
local LINK_CODE_LEN = 6

local sPanel = nil       -- { state = "requesting" | "code" | "ok" | "failed", ... } while the panel is up
local sVerified = {}     -- [global index] = { name = coopdx name when verified, nickname = account nickname }
local sLinkTimer = 0     -- frames left waiting for a /link answer
local sRegistered = false
local sFrame = 0

---------------------------------------------------------------------------------------------
-- helpers
---------------------------------------------------------------------------------------------

-- sgl_bridge.lua's exports, looked up when needed (nil offline / before the bridge exists)
local function bridge(name)
    return _G[name]
end

local function trim(s)
    return ((s or ""):gsub("^%s+", ""):gsub("%s+$", ""))
end

-- printable ASCII only, no DJUI colour codes, at most n characters
local function clean(s, n)
    if type(s) ~= "string" then return "" end
    s = s:gsub("\\#%x+\\", ""):gsub("[^\32-\126]", ""):gsub("\\", "")
    if #s > n then s = s:sub(1, n) end
    return trim(s)
end

-- a whole number from a command field (JSON numbers may arrive as floats or strings), else nil
local function int(v)
    local n = tonumber(v)
    return n ~= nil and math.tointeger(n) or nil
end

local function my_gi()
    return gNetworkPlayers[0].globalIndex
end

-- local index of the connected player with global index gi, or nil
local function local_index_of(gi)
    for i = 0, MAX_PLAYERS - 1 do
        local np = gNetworkPlayers[i]
        if np.connected and np.globalIndex == gi then return i end
    end
    return nil
end

local function sfx(bits)
    if gGlobalSoundSource ~= nil then play_sound(bits, gGlobalSoundSource) end
end

local function open_panel(state, fields)
    sPanel = fields or {}
    sPanel.state = state
    sPanel.timer = 0
end

local function close_panel()
    sPanel = nil
end

-- verified marks: by global index, valid while the same player (same name) holds that index
local function is_verified_local(li)
    local np = gNetworkPlayers[li]
    if np == nil or not np.connected then return false end
    local v = sVerified[np.globalIndex]
    return v ~= nil and v.name == np.name
end

-- charselect.lua (card name tags) and other files
_G.sglIsVerified = function(localIndex)
    return type(localIndex) == "number" and is_verified_local(localIndex)
end

-- the guest friend index of slot n in characters.lua's list (nil when there is none)
local function guest_friend_index(slot)
    local list = _G.sglFriends
    if list == nil then return nil end
    for i, f in ipairs(list) do
        if f.id == "guest_" .. slot then return i end
    end
    return nil
end

local function failure_text(reason)
    reason = type(reason) == "string" and reason or ""
    local r = reason:lower()
    if r == "expired" or r == "expired_token" then
        return "The code expired. Type /login for a new one."
    elseif r == "denied" or r == "access_denied" then
        return "The login was denied on the website."
    elseif r == "bad_code" or r == "invalid_code" then
        return "That link code is not valid (or was already used)."
    elseif r == "" then
        return "The login did not work. Try /login again."
    end
    return clean(reason, 80)
end

---------------------------------------------------------------------------------------------
-- bridge commands
---------------------------------------------------------------------------------------------

local function for_me(cmd)
    local gi = int(cmd.gi)
    return gi == nil or gi == my_gi()
end

local function on_login_code(cmd)
    if type(cmd) ~= "table" or not for_me(cmd) then return end
    local code = clean(cmd.user_code, 16)
    local uri = type(cmd.uri) == "string" and cmd.uri or ""
    if code == "" and uri == "" then return end
    local secs = tonumber(cmd.expires) or 900
    if secs > 1000000000 then secs = secs - get_time() end   -- a Unix time, not seconds left
    secs = math.max(0, math.min(secs, 3600))
    local qr = nil
    if uri ~= "" then
        local err
        qr, err = sgl_qr_encode(uri, 2)          -- EC level M: version 5 for the usual ~66-char uri
        if qr == nil then qr, err = sgl_qr_encode(uri) end
        if qr == nil then log_to_console("[SGL] login QR failed: " .. tostring(err), CONSOLE_MESSAGE_WARNING) end
    end
    -- the address to type: the uri without scheme / query, else the default
    local shown = uri:gsub("^%a+://", ""):gsub("[?#].*$", "")
    if shown == "" or #shown > 48 then shown = ACTIVATE_TEXT end
    open_panel("code", { code = code, uri = uri, qr = qr, url = shown, frames = math.floor(secs * 30) })
    sfx(SOUND_MENU_MESSAGE_APPEAR)
end

local function on_verified(cmd)
    if type(cmd) ~= "table" then return end
    local gi = int(cmd.gi)
    if gi == nil then return end
    local li = local_index_of(gi)
    local nickname = clean(cmd.nickname, 32)
    local np = li ~= nil and gNetworkPlayers[li] or nil
    sVerified[gi] = { name = np and np.name or nil, nickname = nickname }
    if np ~= nil then network_player_set_description(np, "GATOR PASS", 255, 215, 0, 255) end
    if li ~= 0 then
        if np ~= nil then
            djui_chat_message_create("\\#ffd700\\*\\#dcdcdc\\ " .. np.name .. " is verified with Gator Pass.")
        end
        return
    end
    -- me
    sLinkTimer = 0
    local who = nickname ~= "" and nickname or gNetworkPlayers[0].name
    open_panel("ok", { msg = "Welcome, " .. who .. "!" })
    djui_popup_create("\\#ffd700\\Gator Pass:\\#dcdcdc\\ verified as " .. who .. "!", 2)
    sfx(SOUND_MENU_STAR_SOUND)
    local slot = int(cmd.guest_slot)
    if slot ~= nil then
        local index = guest_friend_index(slot)
        local friend = index and _G.sglFriends[index]
        if friend ~= nil and _G.sglSetFriend ~= nil and _G.sglSetFriend(index) then
            sPanel.msg2 = "Your gator " .. friend.name .. " is ready!"
            djui_popup_create("Your gator \\#ffd700\\" .. friend.name .. "\\#dcdcdc\\ is ready: you are playing as it now.", 2)
        else
            djui_chat_message_create("\\#ff8080\\Your guest gator (slot " .. slot .. ") did not load. /char to pick another.")
        end
    end
end

local function on_login_failed(cmd)
    if type(cmd) ~= "table" or not for_me(cmd) then return end
    local text = failure_text(cmd.reason)
    sLinkTimer = 0
    open_panel("failed", { msg = text })
    djui_popup_create("\\#ff8080\\Gator Pass:\\#dcdcdc\\ " .. text, 2)
    sfx(SOUND_MENU_CAMERA_BUZZ)
end

-- register with the bridge once it exists (it loads before this file; retried every frame otherwise)
local function register()
    if sRegistered then return true end
    local on = bridge("sglBridgeOnCommand")
    if on == nil then return false end
    on("login_code", on_login_code)
    on("verified", on_verified)
    on("login_failed", on_login_failed)
    sRegistered = true
    return true
end

---------------------------------------------------------------------------------------------
-- chat commands
---------------------------------------------------------------------------------------------

local OFFLINE_TEXT = "Login is only available on the hosted server"

local function on_login_command(msg)
    msg = trim(msg):lower()
    if msg == "cancel" or msg == "close" or msg == "off" then
        if sPanel ~= nil then
            close_panel()
            djui_chat_message_create("Login panel closed.")
        else
            djui_chat_message_create("No login in progress.")
        end
        return true
    end
    if msg ~= "" then
        djui_chat_message_create("Usage: /login (log in with a QR code), /login cancel, or /link <code>")
        return true
    end
    local emit = bridge("sglBridgeEmit")
    if emit == nil then
        djui_chat_message_create(OFFLINE_TEXT)
        return true
    end
    local me = sVerified[my_gi()]
    if is_verified_local(0) and me ~= nil then
        djui_chat_message_create("You are already verified" .. (me.nickname ~= "" and (" as " .. me.nickname) or "") .. ".")
        return true
    end
    if sPanel ~= nil and (sPanel.state == "requesting" or sPanel.state == "code") then
        djui_chat_message_create("A login is already waiting: scan the code, or /login cancel.")
        return true
    end
    register()
    emit("login_req", { name = gNetworkPlayers[0].name })
    open_panel("requesting", { frames = REQUEST_TIMEOUT })
    return true
end

local function on_link_command(msg)
    local code = trim(msg):upper():gsub("[%s%-]", "")
    if #code ~= LINK_CODE_LEN or code:match("^[A-Z0-9]+$") == nil then
        djui_chat_message_create("Usage: /link <code>, the " .. LINK_CODE_LEN ..
            "-character code chooseyourgator.select shows after you log in (e.g. /link K7Q2XF)")
        return true
    end
    local emit = bridge("sglBridgeEmit")
    if emit == nil then
        djui_chat_message_create(OFFLINE_TEXT)
        return true
    end
    register()
    emit("link_req", { name = gNetworkPlayers[0].name, code = code })
    sLinkTimer = REQUEST_TIMEOUT
    djui_chat_message_create("Linking with code " .. code .. "...")
    return true
end

---------------------------------------------------------------------------------------------
-- hooks
---------------------------------------------------------------------------------------------

local function on_update()
    sFrame = sFrame + 1
    if not sRegistered then register() end
    if sLinkTimer > 0 then
        sLinkTimer = sLinkTimer - 1
        if sLinkTimer == 0 then
            djui_chat_message_create("\\#ff8080\\No answer from the login server. Try /link again in a moment.")
        end
    end
    if sPanel == nil then return end
    sPanel.timer = sPanel.timer + 1
    local st = sPanel.state
    if st == "requesting" or st == "code" then
        sPanel.frames = sPanel.frames - 1
        if sPanel.frames <= 0 then
            if st == "requesting" then
                open_panel("failed", { msg = "No answer from the login server. Try /login again in a moment." })
            else
                open_panel("failed", { msg = failure_text("expired") })
            end
            sfx(SOUND_MENU_CAMERA_BUZZ)
        end
    elseif sPanel.timer >= RESULT_FRAMES then
        close_panel()
    end
end

local function panel_visible()
    return sPanel ~= nil and not sgl_hud_blocked()
end

-- B closes the panel (the press does not punch)
local function on_before_mario_update(m)
    if m.playerIndex ~= 0 or not panel_visible() then return end
    local c = m.controller
    if (c.buttonPressed & B_BUTTON) ~= 0 then
        c.buttonPressed = c.buttonPressed & ~B_BUTTON
        close_panel()
        sfx(SOUND_MENU_MESSAGE_DISAPPEAR)
    end
end

local function on_player_disconnected(m)
    local np = gNetworkPlayers[m.playerIndex]
    if np ~= nil then sVerified[np.globalIndex] = nil end
end

-- name tags: a gold star mark in front of a verified player's name
-- coopdx stops at the first HOOK_ON_NAMETAGS_RENDER that returns a name, and this file's hook runs
-- before uf_west_library_missions.lua's (load order), so a tag that the Library West hide-and-seek
-- round hides is left to that hook.
local function on_nametags_render(playerIndex)
    if not is_verified_local(playerIndex) then return nil end
    if sgl_libwest_hns_hide_tag ~= nil and sgl_libwest_hns_hide_tag(playerIndex) then return nil end
    local np = gNetworkPlayers[playerIndex]
    return "\\#ffd700\\* " .. network_get_player_text_color_string(playerIndex) .. np.name
end

---------------------------------------------------------------------------------------------
-- drawing (DJUI resolution: whole pixels per QR module keep the code sharp and scannable)
---------------------------------------------------------------------------------------------

local function c8(v)
    v = math.floor(v + 0.5)
    if v < 0 then return 0 end
    if v > 255 then return 255 end
    return v
end

local function color(r, g, b, a)
    djui_hud_set_color(c8(r), c8(g), c8(b), c8(a or 255))
end

-- text centred on cx with a drop shadow, shrunk to fit maxW
local function ctext(s, cx, y, scale, maxW, r, g, b, a)
    local w = djui_hud_measure_text(s) * scale
    if w > maxW then
        scale = scale * maxW / w
        w = maxW
    end
    color(0, 0, 0, (a or 255) * 0.75)
    djui_hud_print_text(s, cx - w / 2 + scale * 3, y + scale * 3, scale)
    color(r, g, b, a)
    djui_hud_print_text(s, cx - w / 2, y, scale)
    return scale
end

local function seconds_text(frames)
    local s = math.max(0, frames // 30)
    return string.format("%d:%02d", s // 60, s % 60)
end

local function on_hud_render()
    if not panel_visible() then return end
    djui_hud_set_resolution(RESOLUTION_DJUI)
    local sw, sh = djui_hud_get_screen_width(), djui_hud_get_screen_height()
    local u = sh / 240                          -- one N64 unit in DJUI units
    local st = sPanel.state
    local qr = st == "code" and sPanel.qr or nil

    -- size: the QR (whole DJUI units per module, 4-module quiet zone) or a fixed text box
    local module, qrW = 0, 0
    if qr ~= nil then
        module = math.max(1, math.floor(110 * u / (qr.size + 8)))
        qrW = module * (qr.size + 8)
    end
    local pad = 6 * u
    local W = math.max(qrW, 120 * u) + 2 * pad
    local textH = (st == "code") and 66 * u or 44 * u
    local H = 22 * u + qrW + textH
    local x = math.floor(sw - W - 10 * u)
    local y = math.floor((sh - H) / 2)
    local cx = x + W / 2
    local inner = W - 2 * pad

    -- frame: UF orange rim, navy body
    color(0, 0, 0, 120)
    djui_hud_render_rect(x + 2 * u, y + 2 * u, W, H)
    color(250, 70, 22, 255)
    djui_hud_render_rect(x, y, W, H)
    color(10, 22, 70, 240)
    djui_hud_render_rect(x + u, y + u, W - 2 * u, H - 2 * u)

    djui_hud_set_font(FONT_HUD)
    ctext("GATOR PASS", cx, y + 5 * u, 0.75 * u, inner, 255, 214, 40)
    local ty = y + 22 * u
    djui_hud_set_font(FONT_NORMAL)
    local small = 0.25 * u

    if st == "requesting" then
        local dots = string.rep(".", (sFrame // 15) % 4)
        ctext("Asking the login server" .. dots, cx, ty + 6 * u, small, inner, 235, 235, 245)
        ctext("B or /login cancel: close", cx, ty + 26 * u, 0.2 * u, inner, 160, 170, 200)
    elseif st == "code" then
        if qr ~= nil then
            sgl_qr_draw(qr, math.floor(cx - qrW / 2), math.floor(ty), module, 4)
            ty = ty + qrW + 3 * u
        end
        ctext("Scan it, or go to", cx, ty, small, inner, 200, 210, 235)
        ctext(sPanel.url, cx, ty + 9 * u, small, inner, 255, 255, 255)
        djui_hud_set_font(FONT_HUD)
        ctext(sPanel.code:upper(), cx, ty + 20 * u, 0.9 * u, inner, 255, 214, 40)
        djui_hud_set_font(FONT_NORMAL)
        ctext("Code expires in " .. seconds_text(sPanel.frames), cx, ty + 37 * u, 0.22 * u, inner, 200, 210, 235)
        local dots = string.rep(".", (sFrame // 15) % 4)
        ctext("Waiting for approval" .. dots, cx, ty + 46 * u, small, inner, 120, 255, 140)
        ctext("B or /login cancel: close", cx, ty + 56 * u, 0.2 * u, inner, 160, 170, 200)
    elseif st == "ok" then
        djui_hud_set_font(FONT_HUD)
        ctext("VERIFIED!", cx, ty + 2 * u, 0.8 * u, inner, 120, 255, 140)
        djui_hud_set_font(FONT_NORMAL)
        ctext(sPanel.msg or "", cx, ty + 18 * u, small, inner, 255, 255, 255)
        if sPanel.msg2 ~= nil then ctext(sPanel.msg2, cx, ty + 28 * u, small, inner, 255, 214, 40) end
    else
        djui_hud_set_font(FONT_HUD)
        ctext("NOT LOGGED IN", cx, ty + 2 * u, 0.6 * u, inner, 255, 110, 110)
        djui_hud_set_font(FONT_NORMAL)
        ctext(sPanel.msg or "", cx, ty + 18 * u, 0.22 * u, inner, 255, 255, 255)
    end
end

-- tests (tools/luatest/test_login.lua) read the panel state through this
_G.sglLoginPanel = function() return sPanel end

register()
hook_event(HOOK_UPDATE, on_update)
hook_event(HOOK_BEFORE_MARIO_UPDATE, on_before_mario_update)
hook_event(HOOK_ON_PLAYER_DISCONNECTED, on_player_disconnected)
hook_event(HOOK_ON_NAMETAGS_RENDER, on_nametags_render)
hook_event(HOOK_ON_HUD_RENDER, on_hud_render)
hook_chat_command("login", "[cancel] Log in with Gator Pass (QR code) to get verified and your own gator", on_login_command)
hook_chat_command("link", "<code> Link your chooseyourgator.select account with the code from the website", on_link_command)
