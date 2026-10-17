-- Super Gatorlator 64: Albert and Alberta, the UF mascots, roam the game as talking NPCs.
-- Walk up to one and type in chat (or use /albert <question>, /alberta <question> from anywhere): the host's
-- tools/npc_bridge/bridge.py answers game questions from tools/npc_bridge/game_guide.md and everything else with
-- Gemini; the reply shows as a speech bubble over the mascot and a chat line for everyone.
--
-- Where they are: every SGL_NPC_ROTATE seconds the host moves both mascots one step along their routes
-- (SGL_NPCS[].route, spots in SGL_NPC_SPOTS) by bumping gGlobalSyncTable.sglNpcStep; every client follows the
-- synced step, so everyone sees them in the same place. Exactly one of them is on the hub at any time
-- (Albert's route covers the outdoor stages, Alberta's the libraries; both visit Lake Alice, never together).
-- A mascot never vanishes mid-conversation: the step waits while anyone is talking to or standing near one.
-- Moving = a puff of mist and a vanish sound where they were, and the same where they appear.
--
-- The mascots are local props (spawn_non_sync_object on every client in their level, like the Marston Shushers),
-- with their own skeleton models (actors/albert, actors/alberta, tools/actors/make_gators.py) animated by
-- sgl_albert.lua: they stroll around their spot, wave when someone walks up, turn to whoever they're talking to,
-- stroke their chin while thinking, gesture and flap their jaw while answering, and break into the Gator Chomp.
-- Ids must match tools/npc_bridge/npcs.json (tools/luatest/check_npc_ids.py checks this).

SGL_NPC_TALK_DIST = 600      -- chat within 6 m of a mascot goes to it
SGL_NPC_FACE_DIST = 800      -- the fallback (Yoshi) model turns toward a player within 8 m
SGL_NPC_ROTATE = 240         -- seconds between moves
SGL_NPC_BUSY_HOLD = 6        -- seconds a "someone is near" report holds the next move

-- Where the mascots can be: flat, clear ground near each stage's arrival point, off the mission routes
-- (radius = how far they stroll; floors and clearance checked offline by tools/luatest/check_npc_spots.py).
-- yaw: degrees, 0 = facing +Z; they face the arrival point. label: for "where is Albert?" answers.
SGL_NPC_SPOTS = {
    hub_albert = { level = SGL_HUB_LEVEL, area = 1, x = 8800, y = 0, z = -3750, yaw = -120, radius = 350,
                   label = "on the Plaza of the Americas, right by the spawn" },
    hub_alberta = { level = SGL_HUB_LEVEL, area = 1, x = 7896, y = 0, z = -4864, yaw = 45, radius = 450,
                    label = "on the Plaza of the Americas, right by the spawn" },
    swamp = { level = LEVEL_BOB, area = 1, x = 6261, y = 0, z = -11523, yaw = 60, radius = 300,
              label = "in The Swamp, near where you arrive" },
    reitz = { level = LEVEL_WF, area = 1, x = 6975, y = 0, z = -9690, yaw = 30, radius = 300,
              label = "at Reitz & Engineering, on the North Lawn near where you arrive" },
    alice = { level = LEVEL_JRB, area = 1, x = -13750, y = 0, z = -11900, yaw = 90, radius = 300,
              label = "at Lake Alice, on the bat-house field near where you arrive" },
    marston = { level = LEVEL_CCM, area = 1, x = -596, y = 0, z = -786, yaw = -165, radius = 150,
                label = "in Marston Science Library, in the lobby" },
    libwest = { level = LEVEL_BBH, area = 1, x = -325, y = 0, z = 2508, yaw = 120, radius = 0,
                label = "in Library West, by the entrance" },
}

SGL_NPCS = {
    { id = "albert", name = "Albert", geo = "albert_geo", col = { 250, 140, 40 },
      route = { "hub_albert", "swamp", "hub_albert", "reitz", "hub_albert", "alice" } },
    { id = "alberta", name = "Alberta", geo = "alberta_geo", col = { 110, 170, 255 },
      route = { "marston", "hub_alberta", "libwest", "hub_alberta", "alice", "hub_alberta" } },
}

local sNpcById = {}
for i, npc in ipairs(SGL_NPCS) do
    npc.index = i
    npc.model = smlua_model_util_get_id(npc.geo)
    npc.rig, npc.scale = true, 1.0
    if npc.model == E_MODEL_ERROR_MODEL then
        -- the model failed to load: a Yoshi stand-in that only turns to face you
        npc.model, npc.rig, npc.anims, npc.anim, npc.scale = E_MODEL_YOSHI, false, "yoshi_seg5_anims_05024100", 0, 1.2
    end
    sNpcById[npc.id] = npc
end

function sgl_npc_by_id(id) return sNpcById[id] end

-- the synced rotation step and where each mascot is at it
function sgl_npc_step()
    local s = gGlobalSyncTable.sglNpcStep
    return math.type(s) == "integer" and s or 0
end

function sgl_npc_spot(npc, step)
    step = step or sgl_npc_step()
    return SGL_NPC_SPOTS[npc.route[step % #npc.route + 1]]
end

local function same_place(np, spot)
    return np.currLevelNum == spot.level and np.currAreaIndex == spot.area
end

local function dist2d(ax, az, bx, bz)
    local dx, dz = ax - bx, az - bz
    return math.sqrt(dx * dx + dz * dz)
end

-- the mascot within SGL_NPC_TALK_DIST of the LOCAL player (their own client knows where they are), or nil
function sgl_npc_near(m)
    if m == nil then return nil end
    local best, bestD = nil, SGL_NPC_TALK_DIST
    for _, npc in ipairs(SGL_NPCS) do
        if npc.obj ~= nil then
            local d = dist2d(m.pos.x, m.pos.z, npc.x, npc.z)
            if d <= bestD and math.abs(m.pos.y - npc.y) < 400 then
                best, bestD = npc, d
            end
        end
    end
    return best
end

---------------------------------------------------------------------------------------------
-- the mascot objects (oBehParams = index into SGL_NPCS), only in the level of their current spot
---------------------------------------------------------------------------------------------
local sBubbles = {}           -- npc id -> { text, age, thinking } (every client; chat section below)
local HOP_FRAMES = 12         -- the little hop when a reply arrives

local function npc_init(o)
    o.oFlags = OBJ_FLAG_UPDATE_GFX_POS_AND_ANGLE | OBJ_FLAG_ACTIVE_FROM_AFAR
    o.oDrawingDistance = 8000
    o.oIntangibleTimer = -1
end

---------------------------------------------------------------------------------------------
-- The mascots' brain. What they do, most important first:
--   talk    a reply is up (their bubble, not "..."): gesture + jaw, facing whoever they're talking to
--   think   the host is waiting for the bridge ("..." bubble): hand on chin
--   wave    a player just walked up (within ALBERT_GREET_DIST)
--   chomp   the Gator Chomp: sometimes after an answer, and now and then on their strolls
--   idle    a player is around (within ALBERT_ATTEND_DIST): stand and face them
--   walk    nobody around: stroll to the wander target of the current time slot, then idle there
-- Every client runs this locally. The wander targets come from get_time() // ALBERT_WANDER_SLOT, so every
-- client walks them to the same spots; what they do around players depends on positions every client in the
-- level knows, so they look (nearly) the same everywhere.
---------------------------------------------------------------------------------------------
ALBERT_GREET_DIST = 750
ALBERT_ATTEND_DIST = 900
ALBERT_WANDER_SLOT = 8          -- seconds per stroll target
ALBERT_WALK_SPEED = 6           -- units per frame (about 1.8 m/s)

-- the stroll target of a time slot around a spot: the same point on every client
function sgl_albert_wander_target(spot, slot, salt)
    local h = ((slot + (salt or 0) * 7919) * 2654435761) % 4294967296
    if spot.radius < 100 or (h >> 3) % 4 == 0 then return spot.x, spot.z end
    local a = (h % 3600) / 3600 * 2 * math.pi
    local r = 80 + (h >> 12) % (spot.radius - 79)
    return spot.x + math.sin(a) * r, spot.z + math.cos(a) * r
end

local function talk_frames(text) return math.min(240, 45 + #text * 2) end

local function mascot_loop(o, npc, target, targetD)
    local b = sBubbles[npc.id]
    local anim, faceYaw, moving = "idle", nil, false
    local near = target ~= nil and targetD < ALBERT_GREET_DIST
    if near and not npc.wasNear then npc.greet, npc.chomp = 50, 0 end   -- a newcomer comes first
    npc.wasNear = near
    if b ~= nil and not b.thinking and b.age < talk_frames(b.text) then
        anim = "talk"
        npc.talked = true
    elseif b ~= nil and b.thinking then
        anim = "think"
    else
        if npc.talked then             -- just finished an answer: sometimes a Gator Chomp to celebrate
            npc.talked = false
            if math.random() < 0.4 then npc.chomp = 96 end
        end
        if (npc.greet or 0) > 0 then
            npc.greet = npc.greet - 1
            anim = "wave"
        elseif (npc.chomp or 0) > 0 then
            npc.chomp = npc.chomp - 1
            anim = "chomp"
        elseif target == nil or targetD >= ALBERT_ATTEND_DIST then
            local slot = get_time() // ALBERT_WANDER_SLOT
            local tx, tz = sgl_albert_wander_target(npc.spot, slot, npc.index)
            if dist2d(o.oPosX, o.oPosZ, tx, tz) > 30 then
                moving, anim = true, "walk"
                faceYaw = atan2s(tz - o.oPosZ, tx - o.oPosX)
            elseif npc.arrivedSlot ~= slot then
                npc.arrivedSlot = slot
                if (slot + npc.index) % 3 == 0 then npc.chomp = 96 end
            end
        end
    end
    if not moving and target ~= nil and targetD < ALBERT_ATTEND_DIST then
        faceYaw = atan2s(target.pos.z - o.oPosZ, target.pos.x - o.oPosX)
    end
    if faceYaw ~= nil then o.oFaceAngleYaw = approach_s16_symmetric(o.oFaceAngleYaw, faceYaw, 0x500) end
    o.oMoveAngleYaw = o.oFaceAngleYaw
    if moving then
        -- step once they're roughly facing the way (no moonwalking)
        local diff = math.abs((faceYaw - o.oFaceAngleYaw + 32768) % 65536 - 32768)
        if diff < 0x2000 then
            o.oPosX = o.oPosX + sins(o.oFaceAngleYaw) * ALBERT_WALK_SPEED
            o.oPosZ = o.oPosZ + coss(o.oFaceAngleYaw) * ALBERT_WALK_SPEED
        end
    end
    if npc.playing ~= anim then
        npc.playing = anim
        sgl_albert_play(o, anim)
    end
end

local function npc_loop(o)
    local npc = SGL_NPCS[o.oBehParams]
    if npc == nil or npc.obj ~= o then
        obj_mark_for_deletion(o)
        return
    end
    -- the nearest player in this level and area
    local me = gNetworkPlayers[0]
    local target, bestD = nil, math.huge
    for i = 0, MAX_PLAYERS - 1 do
        local np, m = gNetworkPlayers[i], gMarioStates[i]
        if np.connected and np.currLevelNum == me.currLevelNum and np.currAreaIndex == me.currAreaIndex then
            local d = dist2d(m.pos.x, m.pos.z, o.oPosX, o.oPosZ)
            if d < bestD then target, bestD = m, d end
        end
    end
    if npc.rig then
        mascot_loop(o, npc, target, bestD)
    else
        -- face the nearest player in range, else turn back to the spot's resting yaw
        local want = degrees_to_sm64(npc.spot.yaw)
        if target ~= nil and bestD < SGL_NPC_FACE_DIST then
            want = atan2s(target.pos.z - o.oPosZ, target.pos.x - o.oPosX)
        end
        o.oFaceAngleYaw = approach_s16_symmetric(o.oFaceAngleYaw, want, 0x400)
        o.oMoveAngleYaw = o.oFaceAngleYaw
    end
    -- a little hop when a reply arrives
    local y = npc.spot.y
    if npc.hop ~= nil and npc.hop < HOP_FRAMES then
        npc.hop = npc.hop + 1
        local t = npc.hop / HOP_FRAMES
        y = y + 40 * 4 * t * (1 - t)
    end
    o.oPosY = y
    npc.x, npc.y, npc.z = o.oPosX, o.oPosY, o.oPosZ
end

id_bhvSglNpc = hook_behavior(nil, OBJ_LIST_DEFAULT, true, npc_init, npc_loop, "bhvSglNpc")

local function poof(x, y, z)
    spawn_non_sync_object(id_bhvMistParticleSpawner, E_MODEL_MIST, x, y + 60, z, nil)
    play_sound(SOUND_GENERAL_VANISH_SFX, gGlobalSoundSource)
end

local function despawn(npc, withPoof)
    if npc.obj ~= nil then
        if withPoof then poof(npc.x, npc.y, npc.z) end
        obj_mark_for_deletion(npc.obj)
    end
    npc.obj, npc.playing, npc.wasNear, npc.greet, npc.chomp = nil, nil, false, 0, 0
end

-- (re)place a mascot for the current step: spawn it when its spot is in my level and area
local function place(npc, withPoof)
    local spot = sgl_npc_spot(npc)
    npc.spot = spot
    npc.x, npc.y, npc.z = spot.x, spot.y, spot.z
    if not same_place(gNetworkPlayers[0], spot) then return end
    local o = spawn_non_sync_object(id_bhvSglNpc, npc.model, spot.x, spot.y, spot.z, function(obj)
        obj.oBehParams = npc.index
        obj_scale(obj, npc.scale)
        obj.oFaceAngleYaw = degrees_to_sm64(spot.yaw)
    end)
    local anims = npc.anims ~= nil and gObjectAnimations[npc.anims] or nil
    if o ~= nil and anims ~= nil then
        o.oAnimations = anims
        obj_init_animation(o, npc.anim)
    end
    npc.obj = o
    if withPoof and o ~= nil then poof(spot.x, spot.y, spot.z) end
end

local sShownStep = nil

local function on_level_init()
    for _, npc in ipairs(SGL_NPCS) do
        npc.obj = nil      -- the level change removed the old objects
        despawn(npc, false)
        place(npc, false)
    end
    sShownStep = sgl_npc_step()
end

-- every client: follow the synced step (the host moved them)
local function follow_step()
    local step = sgl_npc_step()
    if sShownStep == nil or step == sShownStep then return end
    for _, npc in ipairs(SGL_NPCS) do
        if sgl_npc_spot(npc, step) ~= sgl_npc_spot(npc, sShownStep) then
            despawn(npc, true)
            place(npc, true)
        end
    end
    sShownStep = step
end

---------------------------------------------------------------------------------------------
-- chat. The host owns the conversation. The speaker's own client decides whether a line is said to a mascot
-- (it alone knows exactly where its player is) and sends it to the host ("npc_ask"; the host itself asks
-- directly); /albert and /alberta ask from anywhere. The host queues the request in its own modfs
-- (sav/sgl64.modfs, npc_out.txt); tools/npc_bridge/bridge.py answers in sav/sgl64_npc.modfs (replies.txt,
-- public), which the host re-reads with mod_fs_reload() and relays to everyone ("npc_say"). Format: bridge.py.
---------------------------------------------------------------------------------------------
SGL_NPC_POLL = 15             -- frames between reads of the bridge's replies while a request is pending
SGL_NPC_TIMEOUT = 15 * 30     -- frames before a request gives up (no bridge running, API trouble)
SGL_NPC_BUBBLE = 9 * 30       -- frames a reply stays over the mascot's head
local OUT_FILE = "npc_out.txt"
local IN_MODPATH = "sgl64_npc"
local IN_FILE = "replies.txt"

local sSession = string.format("%d-%d", get_time(), math.random(1000, 9999))
local sSeq = 0
local sPending = {}           -- seq -> { npc, player, text, stats, age } (host only)
local sPollTimer = 0
local sWarned = false
local sMovedAt = nil          -- host: get_time() of the last move
local sBusyUntil = 0          -- host: a client reported a player near a mascot until then
local sBusyTimer = 0          -- clients: frames to the next "near a mascot" report

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
        table.insert(lines, string.format("%d\t%s\t%s\t%s\t%s", seq, p.npc, escape(p.player), escape(p.text),
            escape(p.stats or "")))
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

local function chat_color(npc)
    local c = npc.col
    return string.format("\\#%02x%02x%02x\\", c[1], c[2], c[3])
end

-- every client: show a reply (or the "..." while the host waits for one)
local function npc_show(id, text, thinking)
    local npc = sNpcById[id]
    if npc == nil then return end
    sBubbles[id] = { text = text, age = 0, thinking = thinking }
    if thinking then return end
    npc.hop = 0
    djui_chat_message_create(chat_color(npc) .. npc.name .. ":\\#dcdcdc\\ " .. text)
    if npc.obj ~= nil and dist2d(gMarioStates[0].pos.x, gMarioStates[0].pos.z, npc.x, npc.z) < 2500 then
        play_sound(SOUND_MENU_MESSAGE_APPEAR, gGlobalSoundSource)
    end
end

local function npc_say(id, text, thinking)
    network_send(true, { sgl = "npc_say", npc = id, text = text, thinking = thinking == true })
    npc_show(id, text, thinking)
end

-- what the guide's live answers need ("how many stars do I have", "where is Albert"): "key=value;key=value"
-- (bridge.py parse_stats), computed by the asker's own client
local function clean(v)
    return (tostring(v):gsub("[;=\t\n\r\\]", " "))
end

local function my_stats()
    local m, np = gMarioStates[0], gNetworkPlayers[0]
    local stars = sgl_total_stars()
    local kv = { stars = stars, lives = m.numLives, coins = m.numCoins, players = 0 }
    for i = 0, MAX_PLAYERS - 1 do
        if gNetworkPlayers[i].connected then kv.players = kv.players + 1 end
    end
    local stage = sgl_stage_by_level(np.currLevelNum)
    if np.currLevelNum == SGL_HUB_LEVEL then
        kv.here = "central campus"
    elseif stage ~= nil then
        kv.here = stage.name .. " act " .. np.currActNum
    end
    local friends = _G.sglFriends
    local pick = gPlayerSyncTable[0].friend
    if friends ~= nil and type(pick) == "number" and friends[pick] ~= nil then kv.char = friends[pick].name end
    local go = sgl_next_stage()
    if go ~= nil then kv.go = go.name .. "|" .. go.building end
    local file = get_current_save_file_num() - 1
    for _, s in ipairs(SGL_STAGES) do
        if kv.lock == nil and s.stars > stars then kv.lock = s.name .. "|" .. s.building .. "|" .. s.stars end
        if s.acts ~= nil and file >= 0 then kv["s_" .. s.key] = save_file_get_course_star_count(file, s.course - 1) end
    end
    for _, npc in ipairs(SGL_NPCS) do kv[npc.id .. "_at"] = sgl_npc_spot(npc).label end
    local parts = {}
    for k, v in pairs(kv) do table.insert(parts, k .. "=" .. clean(v)) end
    table.sort(parts)
    return table.concat(parts, ";")
end

local function pending_for(player)
    for _, p in pairs(sPending) do
        if p.player == player then return true end
    end
    return false
end

-- host: queue a question for the bridge
local function host_enqueue(npcId, player, text, stats)
    if sNpcById[npcId] == nil or pending_for(player) then return end   -- one question at a time per player
    sSeq = sSeq + 1
    sPending[sSeq] = { npc = npcId, player = player, text = text:sub(1, 300), stats = stats or "", age = 0 }
    sPollTimer = SGL_NPC_POLL
    write_outbox()
    npc_say(npcId, "...", true)
end

-- any client: ask a mascot something (the host queues it)
local function ask(npc, text)
    local name = gNetworkPlayers[0].name
    if network_is_server() then
        host_enqueue(npc.id, name, text, my_stats())
    else
        network_send(true, { sgl = "npc_ask", npc = npc.id, player = name, text = text, stats = my_stats() })
    end
end

local function on_chat_message(m, msg)
    if m == nil or msg == nil or m.playerIndex ~= 0 then return end   -- my own lines only
    msg = msg:gsub("^%s+", ""):gsub("%s+$", "")
    if msg == "" or msg:sub(1, 1) == "/" then return end
    local npc = sgl_npc_near(m)
    if npc ~= nil then ask(npc, msg) end
end

-- /albert <question>, /alberta <question>: ask from anywhere; no question = where are they?
local function ask_command(npc)
    return function(msg)
        msg = (msg or ""):gsub("^%s+", ""):gsub("%s+$", "")
        if msg == "" then
            djui_chat_message_create(chat_color(npc) .. npc.name .. "\\#dcdcdc\\ is " .. sgl_npc_spot(npc).label ..
                ". Ask from anywhere with /" .. npc.id .. " <question>.")
            return true
        end
        local line = chat_color(npc) .. gNetworkPlayers[0].name .. " asks " .. npc.name .. ":\\#dcdcdc\\ " .. msg
        djui_chat_message_create(line)
        network_send(true, { sgl = "npc_q", line = line })
        ask(npc, msg)
        return true
    end
end

for _, npc in ipairs(SGL_NPCS) do
    hook_chat_command(npc.id, "<question> - ask " .. npc.name .. " anything, from anywhere (no question: where is " ..
        npc.name .. "?)", ask_command(npc))
end

-- host: is anyone talking to, waiting on, or standing near a mascot? (then they don't move yet)
local function busy()
    if next(sPending) ~= nil or get_time() < sBusyUntil then return true end
    for _, b in pairs(sBubbles) do
        if b.thinking or b.age < SGL_NPC_BUBBLE then return true end
    end
    local m = gMarioStates[0]
    for _, npc in ipairs(SGL_NPCS) do
        if npc.obj ~= nil and dist2d(m.pos.x, m.pos.z, npc.x, npc.z) < ALBERT_ATTEND_DIST then return true end
    end
    return false
end

local function host_update()
    if not network_is_server() then return end
    -- rotation
    local now = get_time()
    if sMovedAt == nil then sMovedAt = now end
    if now - sMovedAt >= SGL_NPC_ROTATE and not busy() then
        gGlobalSyncTable.sglNpcStep = sgl_npc_step() + 1
        sMovedAt = now
    end
    -- requests
    if next(sPending) == nil then return end
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

-- clients: tell the host while my player is near a mascot (it holds the next move)
local function report_busy()
    if network_is_server() then return end
    sBusyTimer = sBusyTimer - 1
    if sBusyTimer > 0 then return end
    sBusyTimer = 60
    local m = gMarioStates[0]
    for _, npc in ipairs(SGL_NPCS) do
        if npc.obj ~= nil and dist2d(m.pos.x, m.pos.z, npc.x, npc.z) < ALBERT_ATTEND_DIST then
            network_send(true, { sgl = "npc_busy" })
            return
        end
    end
end

local function on_update()
    follow_step()
    host_update()
    report_busy()
    for id, b in pairs(sBubbles) do
        b.age = b.age + 1
        if b.age > (b.thinking and SGL_NPC_TIMEOUT or SGL_NPC_BUBBLE) then sBubbles[id] = nil end
    end
end

local function on_packet_receive(data)
    if data.sgl == "npc_say" and type(data.npc) == "string" and type(data.text) == "string" then
        npc_show(data.npc, data.text, data.thinking == true)
    elseif data.sgl == "npc_ask" and network_is_server() and type(data.npc) == "string" and type(data.text) == "string"
        and type(data.player) == "string" then
        host_enqueue(data.npc, data.player, data.text, type(data.stats) == "string" and data.stats or "")
    elseif data.sgl == "npc_busy" and network_is_server() then
        sBusyUntil = get_time() + SGL_NPC_BUSY_HOLD
    elseif data.sgl == "npc_q" and type(data.line) == "string" then
        djui_chat_message_create(data.line)
    end
end

---------------------------------------------------------------------------------------------
-- HUD: name tags and speech bubbles over the mascots nearby, and the "talk" prompt
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

-- long guide answers: the bubble shows the first sentences (up to BUBBLE_CHARS), chat shows everything
local BUBBLE_CHARS = 200

local function bubble_text(text)
    if #text <= BUBBLE_CHARS then return text end
    local cut = text:sub(1, BUBBLE_CHARS)
    local last = nil
    for i = 1, #cut - 1 do
        local c = cut:sub(i, i)
        if (c == "." or c == "!" or c == "?") and cut:sub(i + 1, i + 1) == " " then last = i end
    end
    if last ~= nil and last > 40 then return cut:sub(1, last) .. " (more in chat)" end
    return cut:gsub("%s+%S*$", "") .. "... (more in chat)"
end

local function draw_bubble(b, x, y, col)
    local text = b.thinking and string.rep(".", 1 + (b.age // 8) % 3) or bubble_text(b.text)
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
    if sgl_hud_blocked() then return end
    local m = gMarioStates[0]
    local W, H = sgl_hud_setup(FONT_NORMAL)
    local out = { x = 0, y = 0, z = 0 }
    for _, npc in ipairs(SGL_NPCS) do
        if npc.obj ~= nil and dist2d(m.pos.x, m.pos.z, npc.x, npc.z) < 2500 then
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
