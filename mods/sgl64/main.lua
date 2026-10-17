-- name: Super Gatorlator 64
-- description: Our school, in Super Mario 64.\n\nTest build: proves the mod pipeline works.\nType /school in chat.

local sWelcomed = false
local sBannerTimer = 0

local function count_players()
    local count = 0
    for i = 0, MAX_PLAYERS - 1 do
        if gNetworkPlayers[i].connected then
            count = count + 1
        end
    end
    return count
end

local function on_level_init()
    if sWelcomed then return end
    sWelcomed = true
    sBannerTimer = 30 * 8 -- 8 seconds (game runs at 30 ticks per second)
    djui_popup_create("\\#ffd700\\Welcome to Super Gatorlator 64, " .. gNetworkPlayers[0].name .. "!", 2)
end

local function on_hud_render()
    if sBannerTimer <= 0 then return end
    sBannerTimer = sBannerTimer - 1

    djui_hud_set_resolution(RESOLUTION_N64)
    djui_hud_set_font(FONT_NORMAL)

    local text = "Super Gatorlator 64 loaded"
    local scale = 0.5
    local width = djui_hud_measure_text(text) * scale
    local x = (djui_hud_get_screen_width() - width) * 0.5

    djui_hud_set_color(0, 0, 0, 160)
    djui_hud_render_rect(x - 6, 0, width + 12, 16)
    djui_hud_set_color(255, 215, 0, 255)
    djui_hud_print_text(text, x, 0, scale)
end

local function on_school_command()
    djui_chat_message_create("\\#ffd700\\Super Gatorlator 64 is working!\\#dcdcdc\\ Players online: " .. count_players())
    return true
end

hook_event(HOOK_ON_LEVEL_INIT, on_level_init)
hook_event(HOOK_ON_HUD_RENDER, on_hud_render)
hook_chat_command("school", "Check that the Super Gatorlator 64 mod is running", on_school_command)
