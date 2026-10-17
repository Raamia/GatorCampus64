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
-- chat. The host owns the conversation: HOOK_ON_CHAT_MESSAGE runs on every client for every line,
-- so the host sees its friends' lines too. A line said within SGL_NPC_TALK_DIST of an NPC becomes a
-- request in the host's own modfs (sav/sgl64.modfs, npc_out.txt); tools/npc_bridge/bridge.py answers
-- in sav/sgl64_npc.modfs (replies.txt, public), which the host re-reads with mod_fs_reload() and
-- relays to everyone ("npc_say" packets). Format: see bridge.py.
---------------------------------------------------------------------------------------------
SGL_NPC_POLL = 15             -- frames between reads of the bridge's replies while a request is pending
SGL_NPC_TIMEOUT = 15 * 30     -- frames before a request gives up (no bridge running, API trouble)
SGL_NPC_BUBBLE = 9 * 30       -- frames a reply stays over the NPC's head
local OUT_FILE = "npc_out.txt"
local IN_MODPATH = "sgl64_npc"
local IN_FILE = "replies.txt"

local sSession = string.format("%d-%d", get_time(), math.random(1000, 9999))
local sSeq = 0
local sPending = {}           -- seq -> { npc, player, age } (host only)
local sPollTimer = 0
local sWarned = false
local sBubbles = {}           -- npc id -> { text, age, thinking } (every client)

local function escape(s)
    return (s:gsub("\\", "\\\\"):gsub("\t", "\\t"):gsub("\n", "\\n"):gsub("\r", ""))
end

local function unescape(s)
    return (s:gsub("\\(.)", function(c)
        if c == "t" then return "\t" elseif c == "n" then return " " else return c end
    end))
end

local function write_outbox()
    mod_fs_hide_errors(true)
    local fs = mod_fs_get() or mod_fs_create()
    if fs == nil then return false end
    local file = fs:get_file(OUT_FILE) or fs:create_file(OUT_FILE, true)
    if file == nil then return false end
    local lines = { "session\t" .. sSession }
    local seqs = {}
    for seq in pairs(sPending) do table.insert(seqs, seq) end
    table.sort(seqs)
    for _, seq in ipairs(seqs) do
        local p = sPending[seq]
        table.insert(lines, string.format("%d\t%s\t%s\t%s", seq, p.npc, escape(p.player), escape(p.text)))
    end
    file:rewind()
    file:erase(file.size)
    file:write_string(table.concat(lines, "\n") .. "\n")
    return fs:save()
end

-- the bridge's replies: { { seq, npc, text }, ... } for this session, or {} when there are none yet
local function read_replies()
    mod_fs_hide_errors(true)
    local fs = mod_fs_reload(IN_MODPATH)
    if fs == nil then return {} end
    local file = fs:get_file(IN_FILE)
    if file == nil then return {} end
    file:rewind()
    local out, session = {}, nil
    while not file:is_eof() do
        local line = file:read_line()
        if line == nil then break end
        local a, b, c = line:match("^([^\t]+)\t([^\t]+)\t?(.*)$")
        if a == "session" then
            session = b
        elseif a ~= nil and tonumber(a) ~= nil and session == sSession then
            table.insert(out, { seq = math.tointeger(tonumber(a)), npc = b, text = unescape(c) })
        end
    end
    return out
end

-- every client: show a reply (or the "..." while the host waits for one)
local function npc_show(id, text, thinking)
    local npc = sNpcById[id]
    if npc == nil then return end
    sBubbles[id] = { text = text, age = 0, thinking = thinking }
    if thinking then return end
    local c = npc.col
    djui_chat_message_create(string.format("\\#%02x%02x%02x\\%s:\\#dcdcdc\\ %s", c[1], c[2], c[3], npc.name, text))
    if in_hub(gNetworkPlayers[0]) and dist2d(gMarioStates[0].pos.x, gMarioStates[0].pos.z, npc.x, npc.z) < 2500 then
        play_sound(SOUND_MENU_MESSAGE_APPEAR, gGlobalSoundSource)
    end
end

local function npc_say(id, text, thinking)
    network_send(true, { sgl = "npc_say", npc = id, text = text, thinking = thinking == true })
    npc_show(id, text, thinking)
end

local function pending_for(player)
    for _, p in pairs(sPending) do
        if p.player == player then return true end
    end
    return false
end

local function on_chat_message(m, msg)
    if not network_is_server() or m == nil or msg == nil then return end
    msg = msg:gsub("^%s+", ""):gsub("%s+$", "")
    if msg == "" or msg:sub(1, 1) == "/" then return end
    local npc = sgl_npc_near(m)
    if npc == nil then return end
    local player = gNetworkPlayers[m.playerIndex].name
    if pending_for(player) then return end   -- one question at a time per player
    sSeq = sSeq + 1
    sPending[sSeq] = { npc = npc.id, player = player, text = msg:sub(1, 300), age = 0 }
    sPollTimer = SGL_NPC_POLL
    write_outbox()
    npc_say(npc.id, "...", true)
end

local function host_update()
    if not network_is_server() or next(sPending) == nil then return end
    local changed = false
    for seq, p in pairs(sPending) do
        p.age = p.age + 1
        if p.age > SGL_NPC_TIMEOUT then
            sPending[seq] = nil
            changed = true
            npc_say(p.npc, "Hmm... ask me again in a bit, " .. p.player .. ".")
            if not sWarned then
                sWarned = true
                djui_chat_message_create("\\#ffa0a0\\NPC chat: no reply from the bridge. On the host, run: python3 tools/npc_bridge/bridge.py")
            end
        end
    end
    sPollTimer = sPollTimer - 1
    if sPollTimer <= 0 then
        sPollTimer = SGL_NPC_POLL
        for _, r in ipairs(read_replies()) do
            local p = sPending[r.seq]
            if p ~= nil and p.npc == r.npc and r.text ~= "" then
                sPending[r.seq] = nil
                changed = true
                npc_say(r.npc, r.text)
            end
        end
    end
    if changed then write_outbox() end
end

local function on_update()
    host_update()
    for id, b in pairs(sBubbles) do
        b.age = b.age + 1
        if b.age > (b.thinking and SGL_NPC_TIMEOUT or SGL_NPC_BUBBLE) then sBubbles[id] = nil end
    end
end

local function on_packet_receive(data)
    if data.sgl ~= "npc_say" or type(data.npc) ~= "string" or type(data.text) ~= "string" then return end
    npc_show(data.npc, data.text, data.thinking == true)
end

---------------------------------------------------------------------------------------------
-- HUD: name tags and speech bubbles over the NPCs nearby, and the "talk" prompt
---------------------------------------------------------------------------------------------
local BUBBLE_SCALE = 0.26
local BUBBLE_W = 150          -- wrap width (N64 units)

local function wrap(text, scale, width)
    local lines, cur = {}, ""
    for word in text:gmatch("%S+") do
        local try = cur == "" and word or (cur .. " " .. word)
        if cur ~= "" and sgl_hud_text_width(try, scale) > width then
            table.insert(lines, cur)
            cur = word
        else
            cur = try
        end
    end
    if cur ~= "" then table.insert(lines, cur) end
    return lines
end

local function draw_bubble(b, x, y, col)
    local text = b.thinking and string.rep(".", 1 + (b.age // 8) % 3) or b.text
    local lines = wrap(text, BUBBLE_SCALE, BUBBLE_W)
    local w = 0
    for _, l in ipairs(lines) do w = math.max(w, sgl_hud_text_width(l, BUBBLE_SCALE)) end
    w = math.max(w, 14) + 10
    local lh = 10
    local h = #lines * lh + 6
    local alpha = sgl_hud_fade(b.age, b.thinking and SGL_NPC_TIMEOUT or SGL_NPC_BUBBLE, 4, 20)
    local top = y - h
    sgl_hud_rect(x - w / 2 - 1, top - 1, w + 2, h + 2, col[1], col[2], col[3], 220 * alpha)
    sgl_hud_rect(x - w / 2, top, w, h, 255, 255, 255, 235 * alpha)
    sgl_hud_rect(x - 2, y, 4, 4, 255, 255, 255, 235 * alpha)   -- the tail
    djui_hud_set_color(30, 30, 40, math.floor(255 * alpha))   -- dark text, no drop shadow on the white
    for i, l in ipairs(lines) do
        djui_hud_print_text(l, x - sgl_hud_text_width(l, BUBBLE_SCALE) / 2, top + 3 + (i - 1) * lh, BUBBLE_SCALE)
    end
end

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
                local b = sBubbles[npc.id]
                if b ~= nil then draw_bubble(b, out.x, out.y - 14, npc.col) end
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
hook_event(HOOK_ON_CHAT_MESSAGE, on_chat_message)
hook_event(HOOK_UPDATE, on_update)
hook_event(HOOK_ON_PACKET_RECEIVE, on_packet_receive)
