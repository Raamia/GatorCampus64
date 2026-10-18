-- Replace vanilla Mario-era counters with campus art. Stars still drive course
-- progression; only their on-screen icon is renamed to gator coins.

local HIDE_VANILLA = HUD_DISPLAY_FLAGS_LIVES | HUD_DISPLAY_FLAGS_COIN_COUNT
    | HUD_DISPLAY_FLAGS_STAR_COUNT | HUD_DISPLAY_FLAGS_CAMERA
    | HUD_DISPLAY_FLAGS_CAMERA_AND_POWER | HUD_DISPLAY_FLAGS_POWER
    | HUD_DISPLAY_FLAGS_EMPHASIZE_POWER
local sCoinTexture = nil
local sPortraits = {}

local function hide_vanilla_icons()
    -- The game rebuilds parts of its HUD state during level updates, which can
    -- re-enable the native coin counter after its display flags are cleared.
    -- Hide the vanilla HUD at its render gate as well; the custom campus HUD
    -- below is drawn by DJUI and remains visible.
    hud_hide()
    local flags = hud_get_value(HUD_DISPLAY_FLAGS)
    local filtered = flags & ~HIDE_VANILLA
    if filtered ~= flags then hud_set_value(HUD_DISPLAY_FLAGS, filtered) end
end

local function gator_coin_texture()
    if sCoinTexture == nil then sCoinTexture = get_texture_info("sgl_gator_coin") end
    return sCoinTexture
end

local function life_texture()
    local player = gPlayerSyncTable[0]
    local friend = player and _G.sglFriends and _G.sglFriends[player.friend]
    if friend == nil then return gator_coin_texture() end
    local id = friend.id
    if sPortraits[id] == nil then
        sPortraits[id] = get_texture_info("sgl_portrait_" .. id)
    end
    return sPortraits[id] or gator_coin_texture()
end

-- Replacing the normal HUD alone misses the course-complete/save menu, which
-- draws its own coin and star glyphs. Override those engine textures as well.
local sResultIconsReady = false
local sResultPortrait = nil
local function update_uf_icons()
    if not sResultIconsReady then
        local coin = get_texture_info("sgl_gator_coin")
        local crest = get_texture_info("sgl_gator_crest")
        if coin ~= nil and crest ~= nil then
            texture_override_set("texture_hud_char_coin", coin)
            texture_override_set("texture_hud_char_star", crest)
            for _, locale in ipairs({ "us", "eu", "jp" }) do
                texture_override_set("texture_font_char_" .. locale .. "_coin", coin)
                texture_override_set("texture_font_char_" .. locale .. "_star_filled", crest)
                texture_override_set("texture_font_char_" .. locale .. "_star_hollow", crest)
            end
            sResultIconsReady = true
        end
    end
    local portrait = life_texture()
    if portrait ~= nil and portrait ~= sResultPortrait then
        texture_override_set("texture_hud_char_mario_head", portrait)
        sResultPortrait = portrait
    end
end

local function draw_status_hud()
    if sgl_hud_blocked() then return end

    djui_hud_set_resolution(RESOLUTION_N64)
    djui_hud_set_filter(FILTER_NEAREST)
    djui_hud_set_font(FONT_NORMAL)
    djui_hud_set_color(255, 255, 255, 255)
    local sw = djui_hud_get_screen_width()
    local stars = math.max(0, hud_get_value(HUD_DISPLAY_STARS))

    -- Match the navy panels and orange accent used by the navigation dock.
    local countText = tostring(stars)
    local countWidth = math.max(6, math.min(30, sgl_hud_text_width(countText, 0.32)))
    local coinWidth = 32 + countWidth + 6
    local rightX = sw - 18 - coinWidth
    sgl_hud_rect(18, 8, 28, 28, 7, 17, 38, 210)
    sgl_hud_rect(18, 8, 28, 2, 250, 110, 30, 255)
    sgl_hud_rect(rightX, 8, coinWidth, 28, 7, 17, 38, 210)
    sgl_hud_rect(rightX, 8, coinWidth, 2, 250, 110, 30, 255)

    local portrait = life_texture()
    if portrait ~= nil then
        djui_hud_set_color(255, 255, 255, 255)
        djui_hud_render_texture(portrait, 24, 14, 16 / portrait.width, 16 / portrait.height)
    end

    local coin = gator_coin_texture()
    if coin ~= nil then
        djui_hud_set_color(255, 255, 255, 255)
        djui_hud_render_texture(coin, rightX + 6, 12, 20 / coin.width, 20 / coin.height)
    end
    sgl_hud_text_fit(countText, rightX + 32, 17, 0.32, countWidth, SGL_HUD_WHITE, 1)

end

hook_event(HOOK_UPDATE, hide_vanilla_icons)
hook_event(HOOK_UPDATE, update_uf_icons)
hook_event(HOOK_ON_HUD_RENDER, draw_status_hud)
