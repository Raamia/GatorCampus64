-- Live collision checks shared by generated mascot posts and student routes.
-- Each query has a fixed footprint/ray budget; no map scan or path search runs per frame.
SGL_NPC_GEOMETRY_STATS = { rejected = 0, reason = "none" }
local sDebug = false
local sFeet = { {0, 0}, {-1, 0}, {1, 0}, {0, -1}, {0, 1} }

local function reject(reason)
    SGL_NPC_GEOMETRY_STATS.rejected = SGL_NPC_GEOMETRY_STATS.rejected + 1
    SGL_NPC_GEOMETRY_STATS.reason = reason
    return nil, reason
end

local function hit(x, y, z, dx, dy, dz)
    local result = collision_find_surface_on_ray(x, y, z, dx, dy, dz)
    return result ~= nil and result.surface ~= nil
end

function sgl_npc_safe_position(x, referenceY, z, radius, height)
    local y = find_floor_height(x, referenceY + 200, z)
    -- Floor queries can return a roof/upper floor or the engine's no-floor sentinel.
    -- Accept only a small change from the intended surface, including at spawn.
    if y == nil or y ~= y or y <= -10000 or math.abs(y-referenceY) > 25 then return reject("floor") end
    local heights = {}
    for i, offset in ipairs(sFeet) do
        local px, pz = x+offset[1]*radius, z+offset[2]*radius
        local h = find_floor_height(px, y+200, pz)
        if h == nil or h ~= h or h <= -10000 or math.abs(h-y) > 25 then return reject("edge") end
        heights[i] = h
        if hit(px, h+30, pz, 0, height-30, 0) then return reject("ceiling") end
    end
    if math.abs(heights[2]-heights[3]) > radius*0.73
        or math.abs(heights[4]-heights[5]) > radius*0.73 then return reject("slope") end
    -- Two full body diameters at knee and shoulder height, not just a center ray.
    for _, up in ipairs({ 35, height-25 }) do
        if hit(x-radius, y+up, z, radius*2, 0, 0)
            or hit(x, y+up, z-radius, 0, 0, radius*2) then return reject("wall") end
    end
    local np = gNetworkPlayers[0]
    for _, box in ipairs(SGL_NPC_EXCLUSIONS) do
        local b = box.bounds
        if box.level == np.currLevelNum and box.area == np.currAreaIndex
            and x+radius > b[1] and x-radius < b[4] and y+height > b[2] and y < b[5]
            and z+radius > b[3] and z-radius < b[6] then return reject("exclusion") end
    end
    return y
end

function sgl_npc_safe_step(x, y, z, tx, tz, radius, height)
    local dx, dz = tx-x, tz-z
    local distance = math.sqrt(dx*dx+dz*dz)
    if distance > 80 then return reject("jump") end
    -- Short support samples prevent crossing a narrow gap between valid endpoints.
    local steps, floor = math.max(1, math.ceil(distance/10)), y
    for i = 1, steps do
        local px, pz = x+dx*i/steps, z+dz*i/steps
        floor = sgl_npc_safe_position(px, floor, pz, radius, height)
        if floor == nil then return nil end
    end
    if distance > 0 then
        local ox, oz = -dz/distance*radius, dx/distance*radius
        for _, side in ipairs({ -1, 0, 1 }) do
            for _, up in ipairs({ 35, height-25 }) do
                if hit(x+ox*side, y+up, z+oz*side, dx, floor-y, dz) then return reject("sweep") end
            end
        end
    end
    return floor
end

hook_chat_command("npcdebug", "Toggle NPC anchors and collision rejection diagnostics", function()
    sDebug = not sDebug
    djui_chat_message_create("NPC geometry diagnostics: " .. (sDebug and "on" or "off"))
    return true
end)

hook_event(HOOK_ON_HUD_RENDER, function()
    if not sDebug then return end
    djui_hud_set_resolution(RESOLUTION_N64)
    djui_hud_set_font(FONT_NORMAL)
    djui_hud_set_color(255, 200, 80, 255)
    djui_hud_print_text("NPC blocked: " .. SGL_NPC_GEOMETRY_STATS.rejected
        .. " (" .. SGL_NPC_GEOMETRY_STATS.reason .. ")", 8, 35, 0.35)
    local np = gNetworkPlayers[0]
    for name, spot in pairs(SGL_NPC_SPOTS) do
        if spot.level == np.currLevelNum and spot.area == np.currAreaIndex then
            local screen = { x = 0, y = 0, z = 0 }
            if djui_hud_world_pos_to_screen_pos({ x = spot.x, y = spot.y+20, z = spot.z }, screen) then
                djui_hud_render_rect(screen.x-2, screen.y-2, 4, 4)
                djui_hud_print_text(name .. " Y=" .. spot.y, screen.x+4, screen.y, 0.25)
            end
        end
    end
end)
