-- Small keyboard quality-of-life controls for Super Gatorlator 64.
-- Keyboard 0 is bound to Y_BUTTON in sm64config.txt and is consumed here so it
-- only switches mouse look; it must not also perform the normal Y action.

local sMouseLookEnabled = camera_config_is_mouse_look_enabled()
local sToggleHeld = false

local function set_mouse_look(enabled)
    sMouseLookEnabled = enabled
    camera_config_enable_mouse_look(sMouseLookEnabled)
    djui_popup_create(sMouseLookEnabled and "Mouse look ON - move mouse to look"
        or "Mouse look OFF - click menus with mouse", 2)
end

local function on_mouse_command(msg)
    msg = (msg or ""):lower():gsub("^%s+", ""):gsub("%s+$", "")

    if msg == "on" then
        set_mouse_look(true)
    elseif msg == "off" then
        set_mouse_look(false)
    elseif msg == "" then
        set_mouse_look(not camera_config_is_mouse_look_enabled())
    else
        djui_chat_message_create("Usage: /mouse [on|off]. With no option, toggle mouse look.")
    end
    return true
end

local function consume_toggle_key(m)
    if m.playerIndex ~= 0 or m.controller == nil then return end

    local c = m.controller
    local down = (c.buttonDown & Y_BUTTON) ~= 0
    local pressed = (c.buttonPressed & Y_BUTTON) ~= 0
    local released = (c.buttonReleased & Y_BUTTON) ~= 0

    -- Some keyboard backends repeat buttonPressed while a key is held. Treat 0
    -- as an edge-triggered toggle and keep consuming it until physical release.
    if pressed and not sToggleHeld then
        sToggleHeld = true
        set_mouse_look(not camera_config_is_mouse_look_enabled())
    elseif not down and sToggleHeld then
        sToggleHeld = false
    end

    if down or pressed or released then
        c.buttonDown = c.buttonDown & ~Y_BUTTON
        c.buttonPressed = c.buttonPressed & ~Y_BUTTON
        c.buttonReleased = c.buttonReleased & ~Y_BUTTON
    end
end

hook_chat_command("mouse", "[on|off] Toggle mouse look (also works from chat on remote servers)", on_mouse_command)
hook_event(HOOK_BEFORE_MARIO_UPDATE, consume_toggle_key)
