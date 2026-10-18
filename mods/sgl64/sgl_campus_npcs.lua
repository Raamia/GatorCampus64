-- Campus students are local scenery around each player on the hub's safe sidewalk graph.
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
local sNodes = SGL_CAMPUS_ROUTES.nodes
local sAdj = {}
for i = 1, #sNodes do sAdj[i] = {} end
for _, l in ipairs(SGL_CAMPUS_ROUTES.links) do
    table.insert(sAdj[l[1]], l[2])
    table.insert(sAdj[l[2]], l[1])
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
    s.side = (rnd(s) < 0.5 and -1 or 1) * (10 + rnd(s) * 25)
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

-- Start at a safe sidewalk node, not a random distance down a potentially long link.
-- Never fall back to an in-view node during recycling. No nearby safe node means no spawn.
local function place_ambient(s, minD, maxD, hidden)
    local candidates = {}
    for i, n in ipairs(sNodes) do
        if #sAdj[i] > 0 and math.abs(n[2] - sAround.y) <= 500 then
            local d = dist2d(n[1], n[3], sAround.x, sAround.z)
            if d >= minD and d <= maxD and (not hidden or not camera_sees(n[1], n[3])) then
                table.insert(candidates, i)
            end
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
        if distance > SGL_CROWD_AROUND.hard or math.abs(o.oPosY - sAround.y) > 800 then
            despawn(s)
            return
        end
        if distance > SGL_CROWD_AROUND.recycle and not camera_sees(o.oPosX, o.oPosZ) then
            local r = SGL_CROWD_AROUND.respawn
            if not place_ambient(s, r[1], r[2], true) then
                despawn(s)
                return
            end
        end
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
    cur_obj_push_mario_away_from_cylinder(SGL_CROWD_PUSH_RADIUS, 160)
end

id_bhvSglCrowd = hook_behavior(nil, OBJ_LIST_DEFAULT, true, crowd_init, crowd_loop, "bhvSglCrowd")

local sEnabled = true
local sFrame = 0
local sLastQuota = -1

local function despawn_all()
    for _, s in ipairs(SGL_CROWD) do despawn(s) end
end

local function eligible()
    local np = gNetworkPlayers[0]
    return sEnabled and np.connected and np.currLevelNum == SGL_HUB_LEVEL and np.currAreaIndex == 1
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
            local A = SGL_CROWD_AROUND
            if place_ambient(s, A.near, A.far, true) then
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
    update_around()
    local quota = eligible() and sgl_crowd_quota() or 0
    -- Reductions apply immediately; grow at most two students each half second.
    if quota ~= sLastQuota or sFrame % 15 == 1 then
        reconcile(quota, sFrame % 15 == 1)
        sLastQuota = quota
    end
end

local function on_level_init()
    for _, s in ipairs(SGL_CROWD) do s.obj, s.playing = nil, nil end
    sLastQuota = -1  -- the engine already removed objects in the previous level
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
