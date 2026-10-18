-- Exercise map selection, visibility, and marker lifetime through the real HUD hook.
local HERE = debug.getinfo(1, "S").source:match("^@(.*/)") or "./"
local hooks, command, stored = {}, nil, nil
local frame, now, blocked, chat, context = 0, 100, false, false, nil
local textureName, dots = nil, 0
local noop = function() end
local env = setmetatable({
    HOOK_UPDATE = 1, HOOK_ON_HUD_RENDER = 2, HOOK_ON_CHAT_MESSAGE = 3,
    RESOLUTION_N64 = 1, FONT_ALIASED = 1, FONT_NORMAL = 2, FILTER_LINEAR = 1,
    MAX_PLAYERS = 2, SGL_HUB_LEVEL = 1, SGL_MS_ACTIVE = 2,
    SGL_HUD_GOLD = {255, 215, 0}, SGL_HUD_GREY = {100, 100, 100},
    gNetworkPlayers = {[0] = {currLevelNum = 2, currAreaIndex = 1, currActNum = 1}},
    gMarioStates = {[0] = {area = {camera = {cutscene = 0}}, pos = {x = 0, y = 0, z = 0},
        floorHeight = 0, faceAngle = {y = 0}}},
    SGL_MINIMAP_MAPS = {
        {level = 2, area = 1, height = 0, texture = "lower", label = "Lower", minX = -6000, minZ = -6000, span = 12000},
        {level = 2, area = 1, height = 600, texture = "upper", label = "Upper", minX = -6000, minZ = -6000, span = 12000},
    },
    mod_storage_load = function() return stored end,
    mod_storage_save = function(_, value) stored = value end,
    hook_event = function(event, fn) hooks[event] = fn end,
    hook_chat_command = function(_, _, fn) command = fn end,
    get_global_timer = function() return frame end,
    get_time = function() return now end,
    sgl_hud_blocked = function() return blocked end,
    djui_is_chatbox_open = function() return chat end,
    sgl_mission_ctx = function() return context end,
    djui_hud_get_screen_height = function() return 240 end,
    get_texture_info = function(name) return {name = name, width = 256, height = 256} end,
    djui_hud_render_texture_tile = function(art, _, _, _, _, x, y, w, h)
        textureName = art.name
        assert(x >= 0 and y >= 0 and x + w <= art.width and y + h <= art.height, "crop stays inside artwork")
    end,
    sgl_hud_rect = function(_, _, w, h) if w == 2 and h == 2 then dots = dots + 1 end end,
}, {__index = _G})
for _, key in ipairs({"djui_hud_set_resolution", "djui_hud_set_font", "djui_hud_set_filter",
    "djui_hud_set_color", "djui_hud_set_rotation", "djui_hud_render_texture",
    "sgl_hud_text_fit", "sgl_hud_text_center", "sgl_hud_text", "sgl_hud_toast"}) do env[key] = noop end
assert(loadfile(HERE .. "../../mods/sgl64/sgl_minimap.lua", "t", env))()
local function render()
    textureName, dots = nil, 0
    hooks[2]()
    return textureName, dots
end
hooks[1]()
assert(render() == "lower", "ground floor map")
local mario = env.gMarioStates[0]
mario.pos.y = 900
assert(render() == "lower", "jumping does not select the next floor")
mario.floorHeight = 600
assert(render() == "upper", "landing upstairs changes the map")
mario.pos.x, mario.pos.z = 100000, -100000
assert(render() == "upper", "outlying player still produces a bounded crop")
mario.pos.x, mario.pos.z = 0, 0
env.sgl_minimap_track({x = 0, y = 600, z = 0}, "Objective")
local _, count = render()
assert(count == 1, "current-floor objective appears")
frame = frame + 5
hooks[1]()
_, count = render()
assert(count == 0, "stale objective expires")
env.sgl_minimap_track({x = 0, y = 0, z = 0}, "Downstairs")
_, count = render()
assert(count == 0, "other-floor objective stays hidden")
blocked = true
assert(render() == nil, "menus hide the map")
blocked, chat = false, true
assert(render() == nil, "chat hides the map")
chat = false
hooks[3]()
assert(render() == nil, "incoming chat temporarily hides the map")
now = now + 11
assert(render() == "upper", "map returns after chat timeout")
context = {def = {id = "libwest_hideseek"}, s = env.SGL_MS_ACTIVE}
assert(render() == nil, "hide-and-seek does not reveal positions")
context = nil
mario.area.camera.cutscene = 1
assert(render() == nil, "cutscenes hide the map")
mario.area.camera.cutscene = 0
command("off")
assert(render() == nil and stored == "0", "off preference persists")
command("on")
assert(render() == "upper" and stored == "1", "on preference persists")
env.gNetworkPlayers[0].currAreaIndex = 2
hooks[1]()
assert(render() == nil, "unmapped areas have no map")
print("Minimap floor selection, cropping, markers, privacy, and visibility checks passed")
