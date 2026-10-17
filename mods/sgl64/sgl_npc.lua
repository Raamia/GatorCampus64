-- Super Gatorlator 64: talking NPCs on the hub (UF characters with vanilla models).
-- Walk up to one and type in chat: the host's tools/npc_bridge/bridge.py asks an AI (Gemini) for the
-- reply, which shows as a speech bubble over the NPC and a chat line for everyone.
--
-- NPCs are local props (spawn_non_sync_object on every client, like the Marston Shushers): they stand
-- still, play their idle animation and turn to face the nearest player within SGL_NPC_FACE_DIST.
-- Ids must match tools/npc_bridge/npcs.json (tools/luatest/check_npc_ids.py checks this).

SGL_NPC_TALK_DIST = 600      -- chat within 6 m of an NPC goes to it
SGL_NPC_FACE_DIST = 800      -- NPCs turn toward a player within 8 m

-- y is the hub ground (the generated plaza is flat at 0); yaw in degrees (0 = facing +Z, south)
SGL_NPCS = {
    { id = "guide", name = "Tour Guide Koopa", model = E_MODEL_KOOPA_WITH_SHELL, anims = "koopa_seg6_anims_06011364",
      anim = 9, scale = 1.5, x = 8800, y = 0, z = -3750, yaw = -120, col = { 120, 255, 140 } },
    { id = "albert", name = "Albert", model = E_MODEL_YOSHI, anims = "yoshi_seg5_anims_05024100",
      anim = 0, scale = 1.2, x = 8800, y = 0, z = 3050, yaw = 180, col = { 250, 140, 40 } },
    { id = "libby", name = "Libby", model = E_MODEL_TOAD, anims = "toad_seg6_anims_0600FB58",
      anim = 6, scale = 1.2, x = 8000, y = 0, z = -15550, yaw = 150, col = { 150, 200, 255 } },
    { id = "prof", name = "Professor Bob", model = E_MODEL_BOBOMB_BUDDY, anims = "bobomb_seg8_anims_0802396C",
      anim = 0, scale = 1.3, x = 4050, y = 0, z = 9000, yaw = 30, col = { 255, 160, 210 } },
}

local sNpcById = {}
for i, npc in ipairs(SGL_NPCS) do
    npc.index = i
    sNpcById[npc.id] = npc
end

function sgl_npc_by_id(id) return sNpcById[id] end

local function in_hub(np)
    return np.currLevelNum == SGL_HUB_LEVEL and np.currAreaIndex == 1
end

local function dist2d(ax, az, bx, bz)
    local dx, dz = ax - bx, az - bz
    return math.sqrt(dx * dx + dz * dz)
end

-- the NPC within SGL_NPC_TALK_DIST of a MarioState (nearest first), or nil
function sgl_npc_near(m)
    if m == nil or not in_hub(gNetworkPlayers[m.playerIndex]) then return nil end
    local best, bestD = nil, SGL_NPC_TALK_DIST
    for _, npc in ipairs(SGL_NPCS) do
        local d = dist2d(m.pos.x, m.pos.z, npc.x, npc.z)
        if d <= bestD and math.abs(m.pos.y - npc.y) < 400 then
            best, bestD = npc, d
        end
    end
    return best
end

---------------------------------------------------------------------------------------------
-- the NPC objects (oBehParams = index into SGL_NPCS)
---------------------------------------------------------------------------------------------
local function npc_init(o)
    o.oFlags = OBJ_FLAG_UPDATE_GFX_POS_AND_ANGLE | OBJ_FLAG_ACTIVE_FROM_AFAR
    o.oDrawingDistance = 8000
    o.oIntangibleTimer = -1
end

local function npc_loop(o)
    local npc = SGL_NPCS[o.oBehParams]
    if npc == nil then
        obj_mark_for_deletion(o)
        return
    end
    -- face the nearest player in range, else turn back to the resting yaw
    local target, bestD = nil, SGL_NPC_FACE_DIST
    for i = 0, MAX_PLAYERS - 1 do
        local m = gMarioStates[i]
        if gNetworkPlayers[i].connected and in_hub(gNetworkPlayers[i]) then
            local d = dist2d(m.pos.x, m.pos.z, o.oPosX, o.oPosZ)
            if d < bestD then target, bestD = m, d end
        end
    end
    local want = degrees_to_sm64(npc.yaw)
    if target ~= nil then want = atan2s(target.pos.z - o.oPosZ, target.pos.x - o.oPosX) end
    o.oFaceAngleYaw = approach_s16_symmetric(o.oFaceAngleYaw, want, 0x400)
    o.oMoveAngleYaw = o.oFaceAngleYaw
end

id_bhvSglNpc = hook_behavior(nil, OBJ_LIST_DEFAULT, true, npc_init, npc_loop, "bhvSglNpc")

local function spawn_npcs()
    for _, npc in ipairs(SGL_NPCS) do
        local o = spawn_non_sync_object(id_bhvSglNpc, npc.model, npc.x, npc.y, npc.z, function(obj)
            obj.oBehParams = npc.index
            obj_scale(obj, npc.scale)
            obj.oFaceAngleYaw = degrees_to_sm64(npc.yaw)
        end)
        local anims = gObjectAnimations[npc.anims]
        if o ~= nil and anims ~= nil then
            o.oAnimations = anims
            obj_init_animation(o, npc.anim)
        end
        npc.obj = o
    end
end

local function on_level_init()
    for _, npc in ipairs(SGL_NPCS) do npc.obj = nil end
    if in_hub(gNetworkPlayers[0]) then spawn_npcs() end
end

---------------------------------------------------------------------------------------------
-- HUD: name tags over the NPCs nearby, and the "talk" prompt
---------------------------------------------------------------------------------------------
local function on_hud_render()
    if sgl_hud_blocked() or not in_hub(gNetworkPlayers[0]) then return end
    local m = gMarioStates[0]
    local W, H = sgl_hud_setup(FONT_NORMAL)
    local out = { x = 0, y = 0, z = 0 }
    for _, npc in ipairs(SGL_NPCS) do
        if dist2d(m.pos.x, m.pos.z, npc.x, npc.z) < 2500 then
            local head = { x = npc.x, y = npc.y + 180 * npc.scale + 40, z = npc.z }
            if djui_hud_world_pos_to_screen_pos(head, out) and out.x > -50 and out.x < W + 50 and out.y > 0 and out.y < H then
                sgl_hud_text_center(npc.name, out.x, out.y - 10, 0.28, npc.col, 1)
            end
        end
    end
    local near = sgl_npc_near(m)
    if near ~= nil then
        sgl_hud_prompt("TALK TO " .. near.name:upper(), "Press Enter and type in chat", 1)
    end
end

hook_event(HOOK_ON_LEVEL_INIT, on_level_init)
hook_event(HOOK_ON_HUD_RENDER, on_hud_render)
