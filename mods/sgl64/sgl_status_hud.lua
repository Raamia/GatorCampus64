-- Replace vanilla Mario-era counters with campus art. Stars still drive course
-- progression; only their on-screen icon is renamed to gator coins.

local HIDE_VANILLA = HUD_DISPLAY_FLAGS_LIVES | HUD_DISPLAY_FLAGS_COIN_COUNT
    | HUD_DISPLAY_FLAGS_STAR_COUNT | HUD_DISPLAY_FLAGS_CAMERA
local sCoinTexture = nil
local sPortraits = {}

local function hide_vanilla_icons()
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
    if hud_is_hidden() or sgl_hud_blocked() then return end

    djui_hud_set_resolution(RESOLUTION_N64)
    djui_hud_set_filter(FILTER_NEAREST)
    djui_hud_set_font(FONT_HUD)
    djui_hud_set_color(255, 255, 255, 255)
    local sw = djui_hud_get_screen_width()
    local lives = math.max(0, hud_get_value(HUD_DISPLAY_LIVES))
    local stars = math.max(0, hud_get_value(HUD_DISPLAY_STARS))

    local portrait = life_texture()
    if portrait ~= nil then
        djui_hud_render_texture(portrait, 22, 15, 16 / portrait.width, 16 / portrait.height)
    end
    sgl_hud_text("X" .. lives, 42, 15, 0.55, { 255, 255, 255 }, 1)

    local coin = gator_coin_texture()
    if coin ~= nil then
        -- Center the coin around the counter's text line and give the small badge
        -- a little more weight without moving the existing counter alignment.
        djui_hud_render_texture(coin, sw - 81, 9, 20 / coin.width, 20 / coin.height)
    end
    sgl_hud_text("X" .. stars, sw - 56, 15, 0.55, { 255, 255, 255 }, 1)

    -- Replace CoopDX's camera/Lakitu glyphs with a compact UF badge in the same corner.
    sgl_hud_rect(sw - 54, 203, 32, 18, 250, 110, 30, 255)
    sgl_hud_rect(sw - 52, 205, 28, 14, 20, 45, 95, 255)
    sgl_hud_text_center("UF", sw - 38, 207, 0.34, { 255, 140, 35 }, 1)
end

hook_event(HOOK_UPDATE, hide_vanilla_icons)
hook_event(HOOK_UPDATE, update_uf_icons)
hook_event(HOOK_ON_HUD_RENDER, draw_status_hud)
