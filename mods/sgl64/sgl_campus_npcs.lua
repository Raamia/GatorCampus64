-- Campus students are local scenery around each player on destination-specific safe walking graphs.
-- The host divides one server-wide budget equally among connected human players (including
-- players visiting stages). No fixed landmark crowd, no headless-host objects, no position packets.
-- Each client renders only its own share; unused shares are not redistributed. Albert/Alberta
-- and mission NPCs are separate. See docs/campus_crowd.md for budgets and rollout checks.

SGL_CROWD_BUDGET = 24         -- default total across players; host: /crowd budget 0..40
SGL_CROWD_PER_PLAYER = 12     -- avoid giving a solo player the entire server budget
SGL_CROWD_ANIM_Y = 189
SGL_CROWD_PUSH_RADIUS = 55
SGL_CROWD_DRAW_DIST = 4500
SGL_CROWD_AROUND = { near = 600, far = 3000, leash = 2200, recycle = 3800, hard = 5500,
                     respawn = { 1800, 3000 } }

local IDLE_ANIMS = { MARIO_ANIM_IDLE_HEAD_LEFT, MARIO_ANIM_IDLE_HEAD_RIGHT, MARIO_ANIM_IDLE_HEAD_CENTER }

---------------------------------------------------------------------------------------------
-- the sidewalk graph
---------------------------------------------------------------------------------------------
local sRoute = nil
local sPlayerComponent = nil
local sNodes, sAdj, sComponents, sBuckets = {}, {}, {}, {}
local sLimits = SGL_CROWD_AROUND
local INDOOR = { near = 200, far = 1200, leash = 900, recycle = 1600, hard = 2400,
                 respawn = { 400, 1200 } }
local sRouteCache = {}
local function bucket_key(x, z) return math.floor(x / 1000) .. ":" .. math.floor(z / 1000) end

local function select_routes(level, area)
    local route = nil
    if level == SGL_HUB_LEVEL and area == 1 then route = SGL_CAMPUS_ROUTES end
    for _, candidate in ipairs(SGL_CROWD_AREAS) do
        if candidate.level == level and candidate.area == area then route = candidate break end
    end
    sRoute = route
    sLimits = route ~= nil and route.indoor and INDOOR or SGL_CROWD_AROUND
    sNodes, sAdj, sComponents, sBuckets = {}, {}, {}, {}
    if route == nil then return end
    local cached = sRouteCache[route]
    if cached == nil then
        local adj, components, buckets = {}, {}, {}
        for i, n in ipairs(route.nodes) do
            adj[i] = {}
            local key = bucket_key(n[1], n[3])
            if buckets[key] == nil then buckets[key] = {} end
            table.insert(buckets[key], i)
        end
        for _, link in ipairs(route.links) do
            table.insert(adj[link[1]], link[2])
            table.insert(adj[link[2]], link[1])
        end
        for i = 1, #route.nodes do
            if components[i] == nil then
                local queue, cursor = { i }, 1
                components[i] = i
                while cursor <= #queue do
                    for _, n in ipairs(adj[queue[cursor]]) do
                        if components[n] == nil then components[n] = i; queue[#queue + 1] = n end
                    end
                    cursor = cursor + 1
                end
            end
        end
        cached = { adj = adj, components = components, buckets = buckets }
        sRouteCache[route] = cached
    end
    sNodes, sAdj, sComponents, sBuckets = route.nodes, cached.adj, cached.components, cached.buckets
end

local function dist2d(ax, az, bx, bz)
    local dx, dz = ax - bx, az - bz
    return math.sqrt(dx * dx + dz * dz)
end

-- One moving anchor per client, updated once per frame, not once per object.
local sAround = { x = 0, y = 0, z = 0, leash = SGL_CROWD_AROUND.leash }
SGL_CROWD = {}
for i = 1, 40 do
    local id = string.format("npc_%02d", i)
    local model = smlua_model_util_get_id(id .. "_geo")
    if model ~= E_MODEL_ERROR_MODEL then
        table.insert(SGL_CROWD, { index = i, id = id, model = model, anchor = sAround })
    end
end

-- An independent random walk per student; positions are local scenery.
local function rnd(s)
    s.seed = (s.seed * 1103515245 + 12345) % 2147483648
    return s.seed / 2147483648
end

local function pick(s, list) return list[math.floor(rnd(s) * #list) + 1] end

local function set_link(s, a, b)
    s.a, s.b, s.pos = a, b, 0
    local na, nb = sNodes[a], sNodes[b]
    s.len = math.max(1, dist2d(na[1], na[3], nb[1], nb[3]))
end

-- reached node s.b: maybe stop a moment, then choose the next link (no U-turn unless it's a dead end)
local function arrive(s)
    local from, at = s.a, s.b
    local options = {}
    for _, n in ipairs(sAdj[at]) do
        if n ~= from then table.insert(options, n) end
    end
    if #options == 0 then options = { from } end
    local nxt
    local an = s.anchor
    local here = sNodes[at]
    if #options > 1 and dist2d(here[1], here[3], an.x, an.z) > an.leash and rnd(s) < 0.85 then
        local bestD = math.huge
        for _, n in ipairs(options) do
            local d = dist2d(sNodes[n][1], sNodes[n][3], an.x, an.z)
            if d < bestD then nxt, bestD = n, d end
        end
    else
        nxt = pick(s, options)
    end
    set_link(s, at, nxt)
    if rnd(s) < 0.12 then
        s.pause = 60 + math.floor(rnd(s) * 150)
        s.idle = pick(s, IDLE_ANIMS)
    end
end

-- Walk `frames` frames along the graph, handling short links and idle pauses.
local function advance(s, frames)
    while frames > 0 do
        if s.pause > 0 then
            local take = math.min(s.pause, frames)
            s.pause, frames = s.pause - take, frames - take
        else
            local need = (s.len - s.pos) / s.speed
            if need > frames then
                s.pos, frames = s.pos + s.speed * frames, 0
            else
                frames = frames - need
                arrive(s)
            end
        end
    end
end

-- A fresh walk from node a: speed, side of the path, first link.
local function start_walk(s, a)
    s.speed = 3.2 + rnd(s) * 1.2                 -- units per frame (about 1-1.3 m/s)
    s.side = sRoute ~= SGL_CAMPUS_ROUTES and 0 or (rnd(s) < 0.5 and -1 or 1) * (10 + rnd(s) * 25)
    s.pause, s.idle = 0, IDLE_ANIMS[1]
    set_link(s, a, pick(s, sAdj[a]))
end

-- position on the current link (+ its side offset) and the walking direction
local function place_of(s)
    local na, nb = sNodes[s.a], sNodes[s.b]
    local t = s.pos / s.len
    local dx, dz = nb[1] - na[1], nb[3] - na[3]
    local ox, oz = dz / s.len * s.side, -dx / s.len * s.side
    return na[1] + dx * t + ox, na[2] + (nb[2] - na[2]) * t, na[3] + dz * t + oz, atan2s(dz, dx)
end

-- roughly in front of the camera (within ~70 degrees of where it looks); false when the camera is unknown
local function camera_sees(x, z)
    local l = gLakituState
    if l == nil or l.curPos == nil or l.curFocus == nil then return false end
    local cx, cz = l.curPos.x, l.curPos.z
    local fx, fz = l.curFocus.x - cx, l.curFocus.z - cz
    local px, pz = x - cx, z - cz
    local fl, pl = math.sqrt(fx * fx + fz * fz), math.sqrt(px * px + pz * pz)
    if fl < 1 then return false end
    if pl < 1 then return true end
    return (fx * px + fz * pz) / (fl * pl) > 0.35
end

-- Collision rays choose a reachable room/component, not merely the nearest
-- node through a wall. Probe at most eight candidates per half second, shared by the crowd.
local function reachable_node(n)
    local hit = collision_find_surface_on_ray(sAround.x, sAround.y + 100, sAround.z,
        n[1] - sAround.x, n[2] - sAround.y, n[3] - sAround.z)
    return hit == nil or hit.surface == nil
end

local function nearby_nodes(maxD)
    local nearby = {}
    for bx = math.floor((sAround.x - maxD) / 1000), math.floor((sAround.x + maxD) / 1000) do
        for bz = math.floor((sAround.z - maxD) / 1000), math.floor((sAround.z + maxD) / 1000) do
            for _, i in ipairs(sBuckets[bx .. ":" .. bz] or {}) do
                local n = sNodes[i]
                local d = dist2d(n[1], n[3], sAround.x, sAround.z)
                if #sAdj[i] > 0 and math.abs(n[2] - sAround.y) <= 120 and d <= maxD then
                    nearby[#nearby + 1] = { i = i, d = d }
                end
            end
        end
    end
    return nearby
end

local function player_component()
    local nearby = nearby_nodes(sLimits.far)
    table.sort(nearby, function(a, b) return a.d < b.d end)
    for k = 1, math.min(8, #nearby) do
        local i = nearby[k].i
        if reachable_node(sNodes[i]) then return sComponents[i] end
    end
    return nil
end

local function place_ambient(s, minD, maxD, hidden)
    local nearby, candidates = nearby_nodes(maxD), {}
    local component = sRoute.indoor and sPlayerComponent or nil
    if sRoute.indoor and component == nil then return false end
    for _, entry in ipairs(nearby) do
        local i, d = entry.i, entry.d
        local n = sNodes[i]
        if d >= minD and (component == nil or sComponents[i] == component)
                and (not hidden or not camera_sees(n[1], n[3])) then
            local clear = true
            for _, other in ipairs(SGL_CROWD) do
                local o = other.obj
                if o ~= nil and other ~= s and math.abs(o.oPosY - n[2]) < 200
                        and dist2d(o.oPosX, o.oPosZ, n[1], n[3]) < 150 then clear = false; break end
            end
            if clear then candidates[#candidates + 1] = i end
        end
    end
    if #candidates == 0 then return false end
    s.seed = math.random(1, 2147483646)
    start_walk(s, candidates[math.random(#candidates)])
    return true
end

local function update_around()
    local m = gMarioStates[0]
    sAround.x, sAround.y, sAround.z = m.pos.x, m.pos.y, m.pos.z
end

local function headless()
    local flag = gServerSettings.headlessServer
    return flag ~= nil and flag ~= false and flag ~= 0
end

local function players()
    local ids = {}
    for i = 0, MAX_PLAYERS - 1 do
        local np = gNetworkPlayers[i]
        if np.connected and not (headless() and np.globalIndex == 0) then
            ids[#ids + 1] = np.globalIndex
        end
    end
    table.sort(ids)
    return ids
end

local sBudget = SGL_CROWD_BUDGET
local function publish_budget()
    if not network_is_server() then return end
    -- One atomic value avoids mixing a new budget with an old player count.
    -- Global IDs are stable across clients; local player indices are not.
    local allocation = tostring(sBudget) .. ":" .. table.concat(players(), ",")
    if gGlobalSyncTable.sglCrowdAllocation ~= allocation then
        gGlobalSyncTable.sglCrowdAllocation = allocation
    end
end

-- A new arrival waits for the host's roster. A newer local view may reduce the
-- share sooner, but cannot increase it ahead of the host's published allocation.
function sgl_crowd_quota()
    local allocation = gGlobalSyncTable.sglCrowdAllocation
    if type(allocation) ~= "string" then return 0 end
    local budget, roster = allocation:match("^(%d+):(.*)$")
    if budget == nil then return 0 end
    local count, member = 0, false
    for id in roster:gmatch("%d+") do
        count = count + 1
        if tonumber(id) == gNetworkPlayers[0].globalIndex then member = true end
    end
    if not member then return 0 end
    count = math.max(count, #players())
    return math.min(SGL_CROWD_PER_PLAYER, math.min(40, tonumber(budget)) // count)
end

local function despawn(s)
    if s.obj ~= nil then obj_mark_for_deletion(s.obj) end
    s.obj, s.playing = nil, nil
end

---------------------------------------------------------------------------------------------
-- objects (oBehParams = index into SGL_CROWD)
---------------------------------------------------------------------------------------------
-- play one of Mario's animations on a student (set_mario_anim_with_accel for an object); accel 0x10000 = 1x
local function play(o, s, animId, accel)
    local info = o.header.gfx.animInfo
    if s.playing ~= animId then
        local anim = get_mario_vanilla_animation(animId)
        if anim == nil then return end
        s.playing = animId
        info.animID = animId
        info.curAnim = anim
        info.animYTrans = SGL_CROWD_ANIM_Y
        info.animFrameAccelAssist = (anim.startFrame << 16) + accel
        info.animFrame = anim.startFrame
    end
    info.animAccel = accel
end

local function crowd_init(o)
    o.oFlags = OBJ_FLAG_UPDATE_GFX_POS_AND_ANGLE | OBJ_FLAG_ACTIVE_FROM_AFAR
    o.oDrawingDistance = SGL_CROWD_DRAW_DIST
    o.oIntangibleTimer = -1
end

local function nearest_player(o, range)
    local me = gNetworkPlayers[0]
    local best, bestD = nil, range
    for i = 0, MAX_PLAYERS - 1 do
        local np, m = gNetworkPlayers[i], gMarioStates[i]
        if np.connected and np.currLevelNum == me.currLevelNum and np.currAreaIndex == me.currAreaIndex then
            local d = dist2d(m.pos.x, m.pos.z, o.oPosX, o.oPosZ)
            if d < bestD then best, bestD = m, d end
        end
    end
    return best
end

local function crowd_loop(o)
    local s = SGL_CROWD[o.oBehParams]
    if s == nil or s.obj ~= o then
        obj_mark_for_deletion(o)
        return
    end
    -- Stagger recycling checks. The hard leash also removes an in-view student
    -- after a teleport; camera direction must never keep a distant crowd alive.
    if (o.oTimer + s.index) % 15 == 0 then
        local distance = dist2d(o.oPosX, o.oPosZ, sAround.x, sAround.z)
        if distance > sLimits.hard or math.abs(o.oPosY - sAround.y) > (sRoute.indoor and 160 or 800) then
            despawn(s)
            return
        end
        if distance > sLimits.recycle and not camera_sees(o.oPosX, o.oPosZ) then
            local r = sLimits.respawn
            if not place_ambient(s, r[1], r[2], true) then
                despawn(s)
                return
            end
        end
    end
    -- Static paths are validated offline. Recheck a short look-ahead indoors so
    -- a moving mission prop or closed door can stop a walker between updates.
    if sRoute.indoor and (o.oTimer + s.index) % 6 == 0 then
        local a, b = sNodes[s.a], sNodes[s.b]
        local t = math.min(s.len, s.pos + 80) / s.len
        local tx, tz = a[1] + (b[1] - a[1]) * t, a[3] + (b[3] - a[3]) * t
        local hit = collision_find_surface_on_ray(o.oPosX, o.oPosY + 100, o.oPosZ,
            tx - o.oPosX, 0, tz - o.oPosZ)
        if hit ~= nil and hit.surface ~= nil then s.pause = math.max(s.pause, 15) end
    end
    advance(s, 1)
    local x, y, z, yaw = place_of(s)
    o.oPosX, o.oPosY, o.oPosZ = x, y, z
    if s.pause > 0 then
        -- stopped: look at a player close by, else keep facing the way
        local m = nearest_player(o, 450)
        if m ~= nil then yaw = atan2s(m.pos.z - o.oPosZ, m.pos.x - o.oPosX) end
        play(o, s, s.idle, 0x10000)
    else
        play(o, s, MARIO_ANIM_WALKING, math.floor(s.speed / 4 * 0x10000))
    end
    o.oFaceAngleYaw = approach_s16_symmetric(o.oFaceAngleYaw, yaw, 0x800)
    o.oMoveAngleYaw = o.oFaceAngleYaw
    -- Interior crowds are scenery and must not shove players in tight halls or missions.
    if not sRoute.indoor then cur_obj_push_mario_away_from_cylinder(SGL_CROWD_PUSH_RADIUS, 160) end
end

id_bhvSglCrowd = hook_behavior(nil, OBJ_LIST_DEFAULT, true, crowd_init, crowd_loop, "bhvSglCrowd")

local sEnabled = true
local sFrame = 0
local sLastQuota = -1
local sPlace = nil
local sLastPos = nil
local sArrivalFrames = 0

local function despawn_all()
    for _, s in ipairs(SGL_CROWD) do despawn(s) end
end

local function eligible()
    local np = gNetworkPlayers[0]
    return sEnabled and np.connected and sRoute ~= nil
        and not (network_is_server() and headless())
end

local function reconcile(quota, spawn)
    -- Rotate through the model library by global player ID for visual variety.
    -- Existing students keep their walk when the quota stays the same.
    local size = #SGL_CROWD
    if size == 0 then return end
    local offset = (gNetworkPlayers[0].globalIndex * 13) % size
    local attempts = 0
    for rank = 1, size do
        local k = (rank - 1 + offset) % size + 1
        local s = SGL_CROWD[k]
        if rank > quota then
            despawn(s)
        elseif s.obj == nil and spawn and attempts < 2 then
            attempts = attempts + 1  -- bound graph scans even when there is no nearby sidewalk
            local A = sLimits
            local placed = place_ambient(s, A.near, A.far, true)
            -- During arrival only, a forward-facing camera must not suppress the
            -- entire destination crowd. Still require safe floor and separation.
            if not placed and sArrivalFrames > 0 then placed = place_ambient(s, A.near, A.far, false) end
            if placed then
                local x, y, z, yaw = place_of(s)
                s.obj = spawn_non_sync_object(id_bhvSglCrowd, s.model, x, y, z, function(obj)
                    obj.oBehParams = k
                    obj.oFaceAngleYaw = yaw
                    obj.oMoveAngleYaw = yaw
                end)
            end
        end
    end
end

local function update()
    sFrame = sFrame + 1
    if sFrame % 30 == 1 then publish_budget() end
    local np, m = gNetworkPlayers[0], gMarioStates[0]
    local place = np.currLevelNum .. ":" .. np.currAreaIndex .. ":" .. np.currActNum
    local jumped = sLastPos ~= nil and (dist2d(m.pos.x, m.pos.z, sLastPos.x, sLastPos.z) > 1500
        or math.abs(m.pos.y - sLastPos.y) > 400)
    local changed = place ~= sPlace
    if changed or jumped then
        despawn_all()
        if place ~= sPlace then select_routes(np.currLevelNum, np.currAreaIndex) end
        sPlace, sArrivalFrames, sLastQuota = place, 100, -1
    end
    sLastPos = { x = m.pos.x, y = m.pos.y, z = m.pos.z }
    update_around()
    sAround.leash = sLimits.leash
    if eligible() and sRoute.indoor and (changed or jumped or sFrame % 15 == 1) then
        local component = player_component()
        if component ~= nil and component ~= sPlayerComponent then sArrivalFrames = 100 end
        sPlayerComponent = component
        for _, s in ipairs(SGL_CROWD) do
            if s.obj ~= nil and sComponents[s.a] ~= sPlayerComponent then despawn(s) end
        end
    end
    if sArrivalFrames > 0 then sArrivalFrames = sArrivalFrames - 1 end
    local quota = eligible() and sgl_crowd_quota() or 0
    -- Let the destination/camera settle for ten frames, then fill gradually.
    local spawn = sFrame % 15 == 1 and sArrivalFrames < 90
    if quota ~= sLastQuota or sFrame % 15 == 1 then
        reconcile(quota, spawn)
        sLastQuota = quota
    end
end

local function on_level_init()
    for _, s in ipairs(SGL_CROWD) do s.obj, s.playing = nil, nil end
    sPlace, sLastPos, sLastQuota = nil, nil, -1
end

function sgl_crowd_pos(k)
    local s = SGL_CROWD[k]
    if s == nil or s.obj == nil then return nil end
    return place_of(s)
end

hook_chat_command("crowd", "[on|off|budget 0..40] - local crowd toggle; host sets total budget", function(msg)
    local arg = (msg or ""):lower():match("^%s*(.-)%s*$")
    local value = arg:match("^budget%s+(%d+)$")
    if value ~= nil then
        if not network_is_server() then
            djui_chat_message_create("Only the server host can change the campus crowd budget.")
            return true
        end
        local budget = tonumber(value)
        if budget > 40 then return false end
        sBudget = budget
        publish_budget()
    elseif arg == "off" then
        sEnabled = false
        despawn_all()
    elseif arg == "on" then
        sEnabled = true
    elseif arg ~= "" then
        return false
    end
    local count = 0
    for _, s in ipairs(SGL_CROWD) do if s.obj ~= nil then count = count + 1 end end
    djui_chat_message_create(string.format("Campus crowd: %s (%d active; share %d, cap %d per player)",
        sEnabled and "on" or "off", count, sgl_crowd_quota(), SGL_CROWD_PER_PLAYER))
    return true
end)

hook_event(HOOK_UPDATE, update)
hook_event(HOOK_ON_LEVEL_INIT, on_level_init)
