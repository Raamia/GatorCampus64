-- Offline multi-client simulation of sm64coopdx v1.5.1 for the mods/sgl64 Lua files.
--
-- Every simulated client gets its own Lua environment and loads the real mod files into it
-- (course.lua, sgl_hud.lua, sgl_mission.lua, swamp_missions.lua by default, in coopdx's alphabetical
-- order), on top of coopdx's real constants prelude (coopdx_constants_v151.lua). Engine functions
-- are stubs that model what the missions depend on:
--   * per-client gNetworkPlayers / gMarioStates with coopdx's local-index ordering (index 0 = me,
--     others in the order this client saw them connect), positions synced between clients;
--   * gGlobalSyncTable with coopdx's seq rule (seq += 16 + (16 - globalIndex), receivers keep the
--     higher seq), delivered one frame later;
--   * network_send / network_send_to (reliable, one frame later, to every other connected client);
--   * spawn_default_star: only legal inside an object's loop (it reads the calling object), de-dup
--     per behParams per level visit (at most 8 distinct behParams, like coopdx's spawn_star_deduplication),
--     PACKET_SPAWN_STAR to the same level/area/act (no cutscene there);
--   * objects as strict proxies (fields checked against coopdx_structs_v151.lua), behaviours run as
--     init once + loop every frame, warps unload them;
--   * HUD calls recorded per frame (text), colours must be integers like the real binding wants;
--   * level scripts: on every warp the REAL mods/sgl64/levels/<slot>/script.c of the destination is
--     parsed and its stars (bhvStar, with OBJECT_WITH_ACTS act masks), warp spawn objects and objects
--     with the mod's own Lua behaviours (id_bhvSglDoor, ...) are spawned (opts.levelScripts = false
--     turns it off); Sim.level_script(slot) gives the parsed WARP_NODEs + objects (per AREA block: only the
--     destination area's objects spawn; .warps = area 1's nodes, .areaWarps[n] = area n's);
--   * the save file: w.starFlags[course] (bit k-1 = act k) + w.stars extra stars;
--   * level_trigger_warp(m, WARP_OP_EXIT) leaves through the real level script's WARP_NODE 0xF1
--     (c.warpOps, c.arrivalNode); play_music / stop_background_music keep a per-client queue (c.music);
--     c.project(pos) -> front, x, y overrides the HUD projection (off-screen / behind-camera markers);
--     NetworkPlayer.type is NPT_LOCAL / NPT_SERVER (global index 0) / NPT_CLIENT like coopdx.
-- Any read of an undefined global fails the test (typos / APIs coopdx does not have).
-- Sim.ALL_FILES = every top-level mods/sgl64/*.lua in coopdx's load order (strcmp of the names).
-- Built stages: opts.built (default: the hub + BOB); Sim.built_on_disk() = every slot whose levels/<slot> exists.
local Sim = {}

local HERE = debug.getinfo(1, "S").source:match("^@(.*/)") or "./"
Sim.ROOT = HERE .. "../../"
Sim.MOD = os.getenv("SGL_MOD_DIR") or (Sim.ROOT .. "mods/sgl64/")   -- SGL_MOD_DIR: test a copy (mutation runs)
Sim.FILES = { "course.lua", "sgl_hud.lua", "sgl_mission.lua", "swamp_missions.lua" }
Sim.ALL_FILES = {}
do
    local p = io.popen('ls "' .. Sim.MOD .. '"')
    for f in p:lines() do
        if f:match("%.lua$") then Sim.ALL_FILES[#Sim.ALL_FILES + 1] = f end
    end
    p:close()
    table.sort(Sim.ALL_FILES)   -- byte order = strcmp (mod.c mod_set_loading_order)
end

local STRUCTS = dofile(HERE .. "coopdx_structs_v151.lua")
local API = dofile(HERE .. "coopdx_api_v151.lua")

local function deepcopy(v)
    if type(v) ~= "table" then return v end
    local r = {}
    for k, x in pairs(v) do r[k] = deepcopy(x) end
    return r
end
Sim.deepcopy = deepcopy

---------------------------------------------------------------------------------------------
-- level scripts (mods/sgl64/levels/<slot>/script.c): WARP_NODEs and OBJECT / OBJECT_WITH_ACTS
---------------------------------------------------------------------------------------------
Sim.SLOT_OF_LEVEL = {}       -- filled after the constants prelude loads (below)
local sScripts = {}

local function parse_int(v)
    v = v:gsub("%s", "")
    if v:match("^%-?0[xX]%x+$") then
        local neg = v:sub(1, 1) == "-"
        local n = tonumber(v:gsub("^%-", ""):sub(3), 16)
        return neg and -n or n
    end
    return tonumber(v)
end

function Sim.level_script(slot)
    if sScripts[slot] ~= nil then return sScripts[slot] or nil end
    local f = io.open(Sim.MOD .. "levels/" .. slot .. "/script.c", "r")
    if f == nil then sScripts[slot] = false return nil end
    local src = f:read("a")
    f:close()
    -- AREA(n, geo) ... END_AREA() blocks: a level can hold several areas (course 2: area 2 = the Reitz Union
    -- interior); every WARP_NODE / OBJECT belongs to the area block around it (o.area, out.areaWarps[n]).
    -- out.warps keeps the FIRST area's node for an id (area 1: the entry / exit contract), as before for
    -- one-area levels.
    local spans = {}
    for pos, name, n in src:gmatch("()([%w_]*AREA)%(%s*([%w]*)") do
        if name == "AREA" then
            spans[#spans + 1] = { from = pos, to = #src + 1, area = parse_int(n) }
        elseif name == "END_AREA" and #spans > 0 and spans[#spans].to == #src + 1 then
            spans[#spans].to = pos
        end
    end
    local function area_at(pos)
        for _, s in ipairs(spans) do
            if pos > s.from and pos < s.to then return s.area end
        end
        return nil
    end
    local out = { slot = slot, warps = {}, objects = {}, areaWarps = {} }
    for pos, id, lvl, area, node in src:gmatch("()WARP_NODE%(%s*([%wx]+)%s*,%s*([%w_]+)%s*,%s*([%wx]+)%s*,%s*([%wx]+)") do
        local a = area_at(pos)
        local wn = { level = lvl, area = parse_int(area), node = parse_int(node), inArea = a }
        local nid = parse_int(id)
        local old = out.warps[nid]
        if old == nil or old.inArea == a then out.warps[nid] = wn end
        if a ~= nil then
            out.areaWarps[a] = out.areaWarps[a] or {}
            out.areaWarps[a][nid] = wn
        end
    end
    for pos, kind, args in src:gmatch("()(OBJECT_WITH_ACTS)%(([^\n]-)%),?%s*\n") do
        out.objects[#out.objects + 1] = { kind = kind, args = args, area = area_at(pos) }
    end
    for pos, kind, args in src:gmatch("()(OBJECT)%(([^\n]-)%),?%s*\n") do
        out.objects[#out.objects + 1] = { kind = kind, args = args, area = area_at(pos) }
    end
    for _, o in ipairs(out.objects) do
        local a = {}
        for v in (o.args .. ","):gmatch("%s*([^,]-)%s*,") do a[#a + 1] = v end
        o.model, o.x, o.y, o.z = a[1], parse_int(a[2]), parse_int(a[3]), parse_int(a[4])
        o.rx, o.ry, o.rz = parse_int(a[5]), parse_int(a[6]), parse_int(a[7])
        o.bparamText = a[8]
        o.bparams = parse_int(a[8])
        o.bhv = a[9]
        o.acts = 0x3F
        if o.kind == "OBJECT_WITH_ACTS" then
            o.acts = 0
            for k in a[10]:gmatch("ACT_(%d)") do o.acts = o.acts | (1 << (tonumber(k) - 1)) end
        end
    end
    sScripts[slot] = out
    return out
end

-- vanilla act select (star_select.c bhv_act_selector_init / _loop): the acts you can pick with this
-- course's star flags = every collected act + the first uncollected one ("next act")
function Sim.selectable_acts(flags)
    flags = flags & 0x7F
    local obtained = 0
    for k = 0, 5 do if (flags >> k) & 1 == 1 then obtained = obtained + 1 end end
    local visible, i, init = 0, 0, 0
    while i ~= obtained do
        if (flags >> visible) & 1 == 1 then
            i = i + 1
        elseif init == 0 then
            init = visible + 1
        end
        visible = visible + 1
    end
    if visible == obtained and visible ~= 6 then
        init = visible + 1
        visible = visible + 1
    end
    local acts = {}
    for k = 1, visible do
        if (flags >> (k - 1)) & 1 == 1 or k == init or obtained == 6 then acts[#acts + 1] = k end
    end
    return acts
end

-- coopdx constants prelude, loaded once and shared read-only by every client
local C = setmetatable({}, { __index = _G })
C.get_time = function() return 0 end
C.table_copy = function(t) local r = {} for k, v in pairs(t) do r[k] = v end return r end
C.table_deepcopy = deepcopy
C._set_sync_table_field = function() end
assert(loadfile(HERE .. "coopdx_constants_v151.lua", "t", C))()
Sim.C = C
for slot, name in pairs({ castle_grounds = "LEVEL_CASTLE_GROUNDS", bob = "LEVEL_BOB", wf = "LEVEL_WF", jrb = "LEVEL_JRB",
    ccm = "LEVEL_CCM", bbh = "LEVEL_BBH", ttc = "LEVEL_TTC" }) do
    Sim.SLOT_OF_LEVEL[C[name]] = slot
end
local COURSE_OF_LEVEL = { [C.LEVEL_BOB] = C.COURSE_BOB, [C.LEVEL_WF] = C.COURSE_WF, [C.LEVEL_JRB] = C.COURSE_JRB,
    [C.LEVEL_CCM] = C.COURSE_CCM, [C.LEVEL_BBH] = C.COURSE_BBH, [C.LEVEL_TTC] = C.COURSE_TTC }

-- the levels our mod replaces right now, as the game would see them: every slot whose
-- mods/sgl64/levels/<slot>/script.c exists (DynOS compiles those at launch) -> { [LEVEL_X] = true }
function Sim.built_on_disk()
    local out = {}
    for level, slot in pairs(Sim.SLOT_OF_LEVEL) do
        if Sim.level_script(slot) ~= nil then out[level] = true end
    end
    return out
end

---------------------------------------------------------------------------------------------
-- strict struct proxies
---------------------------------------------------------------------------------------------
local function strict(kind, store)
    local fields = STRUCTS[kind]
    return setmetatable({}, {
        __index = function(_, k)
            if fields[k] == nil and not (type(k) == "string" and k:sub(1, 1) == "_") then
                error(kind .. " has no field '" .. tostring(k) .. "'", 2)
            end
            return store[k]
        end,
        __newindex = function(_, k, v)
            if type(k) == "string" and k:sub(1, 1) == "_" then store[k] = v return end
            if fields[k] == nil then error(kind .. " has no field '" .. tostring(k) .. "'", 2) end
            if fields[k] == false and store.__built then error(kind .. "." .. k .. " is read-only", 2) end
            store[k] = v
        end,
        __store = store,
    })
end

local function raw(proxy) return getmetatable(proxy).__store end
Sim.raw = raw

---------------------------------------------------------------------------------------------
-- world
---------------------------------------------------------------------------------------------
local World = {}
World.__index = World

-- opts.floor(x, y, z) -> find_floor_height result. The default puts a floor 2 m under every query, so
-- every mission probe (which asks 2 m above its anchor) passes, as on the real stadium build.
-- Sim.NO_FLOOR models a stage without the stadium (e.g. the old BOB placeholder): nothing at the coordinates.
function Sim.NO_FLOOR() return -11000 end

function Sim.new(opts)
    opts = opts or {}
    local w = setmetatable({
        clients = {}, frame = 0, queue = {}, nextGi = 0,
        floor = opts.floor or function(x, y, z) return y - 200 end,   -- "there is a floor under every probe"
        built = opts.built or { [C.LEVEL_CASTLE_GROUNDS] = true, [C.LEVEL_BOB] = true },
        stars = opts.stars or 0,
        starFlags = opts.starFlags or {},      -- [course] = flags (bit k-1 = act k, bit 6 = 100 coins)
        levelScripts = opts.levelScripts ~= false,
        files = opts.files or Sim.FILES,
    }, World)
    return w
end

function World:client(name)
    for _, c in ipairs(self.clients) do
        if c.name == name then return c end
    end
    error("no client " .. name)
end

local function new_np(li)
    local np = { connected = false, localIndex = li, globalIndex = 255, currLevelNum = 0, currAreaIndex = 0,
        currActNum = 0, currCourseNum = 0, currAreaSyncValid = false, currLevelSyncValid = false,
        name = "", overrideLocation = "", type = 0 }
    return np
end

local function strict_np(li)
    local s = new_np(li)
    local p = strict("NetworkPlayer", s)
    s.__built = true
    return p, s
end

-- the local-index slot this client uses for player gi (assigned on first sight, like coopdx)
local function local_index(c, gi)
    if gi == c.gi then return 0 end
    local li = c.liOf[gi]
    if li == nil then
        for i = 1, C.MAX_PLAYERS - 1 do
            if c.giAt[i] == nil then
                li = i
                break
            end
        end
        c.liOf[gi] = li
        c.giAt[li] = gi
    end
    return li
end

function World:connect(name, opts)
    opts = opts or {}
    local c = {
        world = self, name = name, gi = opts.gi or self.nextGi, connected = true,
        level = C.LEVEL_CASTLE_GROUNDS, area = 1, act = 0, synced = false, syncIn = 1,
        pos = { x = 0, y = 0, z = 0 }, face = { x = 0, y = 0, z = 0 }, health = 0x880, action = C.ACT_IDLE,
        hooks = {}, behaviors = {}, commands = {}, menu = {}, objects = {}, cur = nil, dedup = {},
        sync = {}, seq = {}, liOf = {}, giAt = {},
        popups = {}, chat = {}, console = {}, sounds = {}, warps = {}, starSpawns = {}, storage = {},
        hudText = {}, hudLog = {}, syncWrites = 0, fanfares = 0, nextObj = 1, pressed = 0,
        warpOps = {}, music = {}, musicLog = {}, project = nil, moderator = false,
    }
    self.nextGi = math.max(self.nextGi, c.gi) + 1
    table.insert(self.clients, c)
    self:build_env(c)
    -- the server sends the whole sync table to joiners
    for _, other in ipairs(self.clients) do
        if other ~= c and other.connected then
            for k, v in pairs(other.sync) do
                if (c.seq[k] or -1) < (other.seq[k] or 0) then
                    c.sync[k] = v
                    c.seq[k] = other.seq[k] or 0
                end
            end
        end
    end
    for _, f in ipairs(self.files) do
        local chunk = assert(loadfile(Sim.MOD .. f, "t", c.env))
        c.loading = true
        chunk()
        c.loading = false
    end
    self:refresh_views()
    c.syncIn = 1
    return c
end

function World:disconnect(c)
    c.connected = false
    for _, other in ipairs(self.clients) do
        if other ~= c and other.connected then
            for _, fn in ipairs(other.hooks[C.HOOK_ON_PLAYER_DISCONNECTED] or {}) do fn(other.ms[local_index(other, c.gi)]) end
        end
    end
    self:refresh_views()
end

-- every client's view of every player (location, sync flag, position)
function World:refresh_views()
    for _, c in ipairs(self.clients) do
        if c.connected then
            for _, o in ipairs(self.clients) do
                local li = local_index(c, o.gi)
                local s = raw(c.nps[li])
                s.connected = o.connected
                s.globalIndex = o.gi
                -- coopdx: my own entry is NPT_LOCAL, the server's (global index 0) NPT_SERVER, others NPT_CLIENT
                s.type = (li == 0) and C.NPT_LOCAL or ((o.gi == 0) and C.NPT_SERVER or C.NPT_CLIENT)
                s.name = o.name
                s.currLevelNum, s.currAreaIndex, s.currActNum = o.level, o.area, o.act
                s.currCourseNum = o.course or 0
                s.currAreaSyncValid = o.synced
                s.currLevelSyncValid = o.synced
                local m = raw(c.ms[li])
                if li ~= 0 then
                    m.pos.x, m.pos.y, m.pos.z = o.pos.x, o.pos.y, o.pos.z
                end
                m.health = o.health
                m.action = o.action
            end
        end
    end
end

function World:warp(c, level, area, act)
    table.insert(c.warps, { level, area, act })
    for _, o in ipairs(c.objects) do raw(o).activeFlags = C.ACTIVE_FLAG_DEACTIVATED end
    c.objects = {}
    c.dedup = {}
    c.dedupN = 0
    c.level, c.area, c.act = level, area, act
    c.course = COURSE_OF_LEVEL[level] or 0
    c.synced = false
    c.syncIn = 2
    if self.levelScripts then self:spawn_level_objects(c) end
    self:refresh_views()
    for _, fn in ipairs(c.hooks[C.HOOK_ON_WARP] or {}) do fn(0, level, area, 0, 0) end
    for _, fn in ipairs(c.hooks[C.HOOK_ON_LEVEL_INIT] or {}) do fn(0, level, area, 0, 0) end
    return true
end

-- the destination level's script objects the tests care about: stars, warp spawns and objects with
-- the mod's Lua behaviours (resolved by name in the client's env, like DynOS does at level load)
local SPAWN_BHVS = { bhvSpinAirborneWarp = true, bhvDeathWarp = true, bhvPaintingStarCollectWarp = true,
    bhvPaintingDeathWarp = true, bhvStar = true }
function World:spawn_level_objects(c)
    local slot = Sim.SLOT_OF_LEVEL[c.level]
    local ls = slot and Sim.level_script(slot)
    c.levelSpawns = {}
    if ls == nil or (c.level ~= C.LEVEL_CASTLE_GROUNDS and not self.built[c.level]) then return end
    local actBit = (c.act >= 1 and c.act <= 6) and (1 << (c.act - 1)) or 0x3F
    for _, o in ipairs(ls.objects) do
        if (o.acts & actBit) ~= 0 and (o.area == nil or o.area == c.area) then
            local bhv
            if SPAWN_BHVS[o.bhv] then
                bhv = C["id_" .. o.bhv]
            elseif o.bhv:match("^id_") then
                bhv = rawget(c.env, o.bhv)   -- nil when the file that hooks it is not loaded
            end
            if bhv ~= nil then
                local obj = c.spawn_object(bhv, C[o.model] or 0, o.x, o.y, o.z)
                local st = raw(obj)
                st.oBehParams = o.bparams or 0
                st.oMoveAngleYaw = math.floor((o.ry or 0) * 0x10000 / 360) & 0xFFFF
                st.oFaceAngleYaw = st.oMoveAngleYaw
                if o.bhv ~= "bhvStar" and not o.bhv:match("^id_") then
                    c.levelSpawns[((o.bparams or 0) >> 16) & 0xFF] = { x = o.x, y = o.y, z = o.z, yaw = st.oMoveAngleYaw, bhv = o.bhv }
                end
            end
        end
    end
end

-- inject a sync-table value on every client (as if written long ago by someone who left)
function World:set_sync_all(key, value)
    for _, c in ipairs(self.clients) do
        c.sync[key] = value
        c.seq[key] = (c.seq[key] or 0) + 1000
    end
end

local function run_hooks(c, ev, ...)
    local r
    for _, fn in ipairs(c.hooks[ev] or {}) do r = fn(...) end
    return r
end
Sim.run_hooks = run_hooks

function World:step_client(c)
    if not c.connected then return end
    if not c.synced then
        c.syncIn = c.syncIn - 1
        if c.syncIn <= 0 then
            c.synced = true
            self:refresh_views()
            run_hooks(c, C.HOOK_ON_SYNC_VALID)
        end
    end
    run_hooks(c, C.HOOK_UPDATE)
    -- objects: init once, then loop (objects spawned now run from the next frame, like SM64 lists)
    local list = {}
    for _, o in ipairs(c.objects) do table.insert(list, o) end
    for _, o in ipairs(list) do
        local s = raw(o)
        if s.activeFlags ~= C.ACTIVE_FLAG_DEACTIVATED then
            local b = c.behaviors[s.behavior]
            c.cur = o
            if not s._inited then
                s._inited = true
                if b and b.init then b.init(o) end
            end
            if s.activeFlags ~= C.ACTIVE_FLAG_DEACTIVATED and b and b.loop then b.loop(o) end
            c.cur = nil
            s.oTimer = s.oTimer + 1
        end
    end
    local keep = {}
    for _, o in ipairs(c.objects) do
        if raw(o).activeFlags ~= C.ACTIVE_FLAG_DEACTIVATED then table.insert(keep, o) end
    end
    c.objects = keep
    -- mario
    local m = c.ms[0]
    local ctl = raw(raw(m).controller)
    ctl.buttonPressed = c.pressed
    ctl.buttonDown = c.pressed
    ctl.stickX, ctl.stickY, ctl.stickMag = c.stickMag or 0, 0, c.stickMag or 0
    c.pressed = 0
    run_hooks(c, C.HOOK_BEFORE_MARIO_UPDATE, m)
    c.lastInput = { buttons = ctl.buttonDown, pressed = ctl.buttonPressed, stickMag = ctl.stickMag }
    run_hooks(c, C.HOOK_MARIO_UPDATE, m)
    for i = 1, C.MAX_PLAYERS - 1 do
        if c.giAt[i] ~= nil and c.nps[i].connected then run_hooks(c, C.HOOK_MARIO_UPDATE, c.ms[i]) end
    end
    -- hud
    c.hudText = {}
    c.draw = {}
    run_hooks(c, C.HOOK_ON_HUD_RENDER)
    c.hudLog[#c.hudLog + 1] = table.concat(c.hudText, " | ")
    if #c.hudLog > 3 then table.remove(c.hudLog, 1) end
end

function World:deliver()
    local q = self.queue
    self.queue = {}
    for _, msg in ipairs(q) do
        for _, r in ipairs(self.clients) do
            if r ~= msg.from and r.connected then
                if msg.kind == "sync" then
                    if msg.seq > (r.seq[msg.key] or 0) then
                        r.sync[msg.key] = msg.value
                        r.seq[msg.key] = msg.seq
                    end
                elseif msg.kind == "packet" and (msg.to == nil or msg.to == r.gi) then
                    run_hooks(r, C.HOOK_ON_PACKET_RECEIVE, deepcopy(msg.data))
                elseif msg.kind == "star" and r.level == msg.level and r.area == msg.area and r.act == msg.act then
                    if not r.dedup[msg.bparams] and (r.dedupN or 0) < 8 then
                        r.dedup[msg.bparams] = true
                        r.dedupN = (r.dedupN or 0) + 1
                        local st = r.spawn_object(C.id_bhvStarSpawnCoordinates, C.E_MODEL_STAR, msg.x, msg.y, msg.z)
                        raw(st).oBehParams = msg.bparams
                        raw(st).oStarSpawnExtCutsceneFlags = 0
                        table.insert(r.starSpawns, { x = msg.x, y = msg.y, z = msg.z, bparams = msg.bparams, network = true })
                    end
                end
            end
        end
    end
end

function World:step(n)
    for _ = 1, (n or 1) do
        self.frame = self.frame + 1
        self:refresh_views()
        for _, c in ipairs(self.clients) do self:step_client(c) end
        self:deliver()
    end
end

function World:seconds(s) self:step(math.floor(s * 30)) end

---------------------------------------------------------------------------------------------
-- per-client environment (stubbed engine)
---------------------------------------------------------------------------------------------
function World:build_env(c)
    local w = self
    local S = {}            -- stubs, then mod globals land in env itself
    c.stubs = S

    -- players
    c.nps, c.ms = {}, {}
    for i = 0, C.MAX_PLAYERS - 1 do
        c.nps[i] = strict_np(i)
        local ctl = strict("Controller", { buttonPressed = 0, buttonDown = 0, stickX = 0, stickY = 0, stickMag = 0,
            rawStickX = 0, rawStickY = 0, extStickX = 0, extStickY = 0, buttonReleased = 0, port = i })
        local mo = { behavior = 0, oPosX = 0, oPosY = 0, oPosZ = 0, activeFlags = C.ACTIVE_FLAG_ACTIVE, oBehParams = 0,
            header = { gfx = { node = { flags = 0 }, scale = { x = 1, y = 1, z = 1 }, cameraToObject = { x = 0, y = 0, z = 0 } } },
            _model = 0 }
        local marioObj = strict("Object", mo)
        mo.__built = true
        local ms = { playerIndex = i, pos = (i == 0) and c.pos or { x = 0, y = 0, z = 0 },
            faceAngle = (i == 0) and c.face or { x = 0, y = 0, z = 0 }, health = 0x880, action = C.ACT_IDLE, numLives = 4,
            numStars = 0, controller = ctl, marioObj = marioObj, character = { type = C.CT_MARIO },
            skipWarpInteractionsTimer = 0, interactObj = nil, usedObj = nil, riddenObj = nil,
            vel = { x = 0, y = 0, z = 0 }, forwardVel = 0, heldObj = nil, area = nil }
        c.ms[i] = strict("MarioState", ms)
    end
    S.gNetworkPlayers = c.nps
    S.gMarioStates = c.ms
    S.gPlayerSyncTable = {}
    for i = 0, C.MAX_PLAYERS - 1 do S.gPlayerSyncTable[i] = {} end
    S.gLevelValues, S.gServerSettings, S.gBehaviorValues = {}, {}, {}
    S.gGlobalSoundSource = { x = 0, y = 0, z = 0 }
    -- vanilla collision pointers the mod's objects use (sgl_mission.lua buttons; wf_reitz_missions.lua lift + cranes)
    S.gGlobalObjectCollisionData = { purple_switch_seg8_collision_0800C7A8 = "COL:purple_switch",
        checkerboard_platform_seg8_collision_0800D710 = "COL:checkerboard_platform" }
    S.gGlobalSyncTable = setmetatable({}, {
        __index = function(_, k) return c.sync[k] end,
        __newindex = function(_, k, v)
            assert(type(k) == "string" or type(k) == "number", "sync key type")
            assert(type(v) == "number" or type(v) == "string" or type(v) == "boolean", "sync value type " .. type(v))
            if c.sync[k] == v then return end
            c.sync[k] = v
            local seq = (c.seq[k] or 0) + C.MAX_PLAYERS + (C.MAX_PLAYERS - c.gi)
            c.seq[k] = seq
            c.syncWrites = c.syncWrites + 1
            if not c.loading then
                table.insert(w.queue, { kind = "sync", from = c, key = k, value = v, seq = seq })
            end
        end,
    })

    -- hooks
    S.hook_event = function(ev, fn)
        assert(type(ev) == "number" and type(fn) == "function", "hook_event args")
        c.hooks[ev] = c.hooks[ev] or {}
        table.insert(c.hooks[ev], fn)
    end
    local nextBhv = 0x1000
    S.hook_behavior = function(base, list, replace, init, loop, name)
        assert(c.loading, "hook_behavior() can only be called on load")
        nextBhv = nextBhv + 1
        for _, b in pairs(c.behaviors) do
            assert(name == nil or b.name ~= name, "hook_behavior: two behaviours named " .. tostring(name))
        end
        c.behaviors[nextBhv] = { init = init, loop = loop, name = name, list = list }
        if name ~= nil then c.env[name] = nextBhv end
        return nextBhv
    end
    S.hook_chat_command = function(name, desc, fn)
        assert(c.loading)
        assert(c.commands[name] == nil, "two files register the chat command /" .. name)
        c.commands[name] = fn
    end
    S.hook_mod_menu_button = function(name, fn)
        assert(c.loading)
        assert(c.menu[name] == nil, "two mod menu buttons named " .. name)
        c.menu[name] = fn
        return 0
    end
    S.define_custom_obj_fields = function() assert(c.loading) end

    -- text / ui / logging
    S.log_to_console = function(s, level) table.insert(c.console, s) end
    S.djui_popup_create = function(s, lines)
        assert(type(s) == "string" and math.type(lines) == "integer", "djui_popup_create(string, int)")
        table.insert(c.popups, s)
    end
    S.djui_chat_message_create = function(s) table.insert(c.chat, s) end
    S.smlua_text_utils_course_acts_replace = function() end
    S.smlua_text_utils_course_name_replace = function() end
    S.smlua_text_utils_castle_secret_stars_replace = function() end
    S.play_sound = function(bits, pos)
        assert(math.type(bits) == "integer" and type(pos) == "table", "play_sound(int, Vec3f)")
        table.insert(c.sounds, bits)
    end
    S.play_race_fanfare = function() c.fanfares = c.fanfares + 1 end
    S.is_game_paused = function() return false end
    S.get_global_timer = function() return w.frame end
    -- coopdx's per-area network timer (the same on every client of the area; c.areaTimerOffset skews one)
    S.get_network_area_timer = function() return w.frame + (c.areaTimerOffset or 0) end

    -- hud
    local function int8(v, what) assert(math.type(v) == "integer" and v >= 0 and v <= 255, what .. " must be an integer 0..255, got " .. tostring(v)) end
    S.djui_hud_set_resolution = function(r) assert(r == C.RESOLUTION_N64 or r == C.RESOLUTION_DJUI) end
    S.djui_hud_set_font = function(f) assert(math.type(f) == "integer"); c.font = f end
    S.djui_hud_get_screen_width = function() return 427 end
    S.djui_hud_get_screen_height = function() return 240 end
    S.djui_hud_measure_text = function(s) assert(type(s) == "string"); return #s * 16 end
    S.djui_hud_set_color = function(r, g, b, a)
        int8(r, "r"); int8(g, "g"); int8(b, "b"); int8(a, "a")
        c.color = { r, g, b, a }
    end
    S.djui_hud_print_text = function(s, x, y, sc)
        assert(type(s) == "string" and type(x) == "number" and type(y) == "number" and type(sc) == "number", "print_text args")
        assert(x == x and y == y, "NaN position")
        table.insert(c.hudText, s)
        table.insert(c.draw, { k = "text", s = s, x = x, y = y, sc = sc, font = c.font, col = c.color })
    end
    S.djui_hud_render_rect = function(x, y, wd, h)
        assert(type(wd) == "number" and type(h) == "number")
        table.insert(c.draw, { k = "rect", x = x, y = y, w = wd, h = h, col = c.color })
    end
    -- c.project(pos) -> front, x, y (default: everything on screen at (200, 120))
    S.djui_hud_world_pos_to_screen_pos = function(pos, out)
        assert(type(pos.x) == "number" and type(out) == "table")
        if c.project ~= nil then
            local front, x, y = c.project(pos)
            out.x, out.y, out.z = x, y, front and -1000 or 500
            return front
        end
        out.x, out.y, out.z = 200, 120, -1000
        return true
    end

    -- network
    S.network_send = function(reliable, t)
        assert(type(reliable) == "boolean" and type(t) == "table", "network_send(bool, table)")
        local n = 0
        for k, v in pairs(t) do
            n = n + 1
            assert(type(k) == "string" or type(k) == "number", "packet key")
            assert(type(v) ~= "table" and type(v) ~= "function", "packet values must be primitives (" .. tostring(k) .. ")")
        end
        assert(n < 256, "too many packet keys")
        table.insert(w.queue, { kind = "packet", from = c, data = deepcopy(t) })
    end
    S.network_send_to = function(li, reliable, t)
        assert(math.type(li) == "integer" and li > 0 and li < C.MAX_PLAYERS, "network_send_to local index")
        table.insert(w.queue, { kind = "packet", from = c, to = c.giAt[li], data = deepcopy(t) })
    end
    S.network_player_set_override_location = function(np, text)
        assert(type(text) == "string", "location must be a string")
        raw(np).overrideLocation = text
    end
    S.network_is_server = function() return c.gi == 0 end
    S.network_is_moderator = function() return c.moderator == true end

    -- levels / save
    S.level_is_vanilla_level = function(l) return not w.built[l] end
    S.save_file_get_total_star_count = function()
        local n = w.stars
        for _, flags in pairs(w.starFlags) do
            for k = 0, 6 do n = n + ((flags >> k) & 1) end
        end
        return n
    end
    S.save_file_get_star_flags = function(file, courseIndex)
        assert(math.type(file) == "integer" and math.type(courseIndex) == "integer", "save_file_get_star_flags ints")
        return w.starFlags[courseIndex + 1] or 0
    end
    S.get_current_save_file_num = function() return 1 end
    S.warp_to_level = function(level, area, act)
        assert(math.type(level) == "integer" and math.type(area) == "integer" and math.type(act) == "integer", "warp_to_level ints")
        return w:warp(c, level, area, act)
    end
    S.find_floor_height = function(x, y, z) return w.floor(x, y, z) end
    S.mod_storage_load_number = function(k, d) return c.storage[k] or d or 0 end
    S.mod_storage_save_number = function(k, v) c.storage[k] = v; return true end

    -- used by levels.lua / main.lua (integration test)
    S.camera_set_romhack_override = function() end
    S.camera_set_use_course_specific_settings = function() end
    local dialogN = 0
    S.smlua_text_utils_allocate_dialog = function() dialogN = dialogN + 1; return 0x100 + dialogN end
    S.smlua_text_utils_dialog_replace = function() end
    S.level_register = function() return 50 end
    S.set_override_far = function(v) c.far = v end
    S.sins = function(a) return math.sin((a % 65536) / 65536 * 2 * math.pi) end
    S.coss = function(a) return math.cos((a % 65536) / 65536 * 2 * math.pi) end
    S.mario_stop_riding_object = function() end
    -- the vanilla pause-menu exit (WARP_OP_EXIT): through the stage's WARP_NODE 0xF1 (level script)
    S.level_trigger_warp = function(m, op)
        assert(raw(m).playerIndex == 0 and math.type(op) == "integer", "level_trigger_warp(local m, op)")
        table.insert(c.warpOps, op)
        if op == C.WARP_OP_EXIT then
            local ls = Sim.level_script(Sim.SLOT_OF_LEVEL[c.level] or "")
            local wn = ls and ((ls.areaWarps[c.area] or {})[0xF1] or ls.warps[0xF1])
            if wn ~= nil then
                w:warp(c, C[wn.level], wn.area, 0)
                c.arrivalNode = wn.node
            end
        end
        return 1
    end
    -- background music queue (play_music / stop_background_music with SEQUENCE_ARGS(priority, seq))
    S.play_music = function(player, seqArgs, fade)
        assert(math.type(player) == "integer" and math.type(seqArgs) == "integer" and math.type(fade) == "integer", "play_music ints")
        table.insert(c.music, seqArgs)
        table.insert(c.musicLog, "play " .. seqArgs)
    end
    S.stop_background_music = function(seqArgs)
        assert(math.type(seqArgs) == "integer", "stop_background_music int")
        for i = #c.music, 1, -1 do
            if (c.music[i] & 0xFF) == (seqArgs & 0xFF) then table.remove(c.music, i) end
        end
        table.insert(c.musicLog, "stop " .. seqArgs)
    end
    S.atan2s = function(y, x)
        assert(type(y) == "number" and type(x) == "number")
        local a = math.floor(math.atan(x, y) / (2 * math.pi) * 65536 + 0.5)
        if a > 32767 then a = a - 65536 end
        return a
    end
    S.soft_reset_camera = function(cam) assert(cam ~= nil) end
    S.set_mario_action = function(m, a, arg)
        raw(m).action = a
        raw(m).actionArg = arg
        if raw(m).playerIndex == 0 then c.action = a end
        return 1
    end

    -- characters.lua / charselect.lua (full-mod tests)
    local modelN = 0x300
    S.smlua_model_util_get_id = function(name)
        assert(type(name) == "string")
        if w.brokenModels and w.brokenModels[name] then return C.E_MODEL_ERROR_MODEL end
        modelN = modelN + 1
        return modelN
    end
    S.get_texture_info = function(name)
        assert(type(name) == "string")
        if w.missingTextures and w.missingTextures[name] then return nil end
        return { width = 64, height = 64, name = name }
    end
    c.strStorage = {}
    S.mod_storage_load = function(k) assert(type(k) == "string"); return c.strStorage[k] end
    S.mod_storage_save = function(k, v)
        assert(type(k) == "string" and type(v) == "string", "mod_storage_save(string, string)")
        c.strStorage[k] = v
        return true
    end
    c.hudHidden = false
    S.hud_hide = function() c.hudHidden = true end
    S.hud_show = function() c.hudHidden = false end
    S.hud_is_hidden = function() return c.hudHidden end
    S.djui_hud_get_mouse_x = function() return 0 end
    S.djui_hud_get_mouse_y = function() return 0 end
    S.djui_hud_get_mouse_buttons_down = function() return 0 end
    S.djui_hud_is_pause_menu_created = function() return false end
    S.is_transition_playing = function() return false end
    S.get_dialog_id = function() return -1 end
    S.djui_is_chatbox_open = function() return false end
    S.play_character_sound = function(m, snd) assert(math.type(snd) == "integer"); table.insert(c.sounds, snd) end
    S.djui_hud_set_filter = function(f) assert(math.type(f) == "integer") end
    S.djui_hud_render_texture = function(tex, x, y, sx, sy)
        assert(type(tex) == "table" and type(x) == "number" and type(sy) == "number", "render_texture args")
        table.insert(c.draw, { k = "tex", name = tex.name, x = x, y = y })
    end

    -- sgl_login.lua (Gator Pass): player list description, name tag colour, Unix time
    S.network_player_set_description = function(np, desc, r, g, b, a)
        assert(type(desc) == "string", "description must be a string")
        for _, v in ipairs({ r, g, b, a }) do assert(math.type(v) == "integer" and v >= 0 and v <= 255, "description colour") end
        local s = raw(np)
        s.description, s.descriptionR, s.descriptionG, s.descriptionB, s.descriptionA = desc, r, g, b, a
    end
    S.network_get_player_text_color_string = function(li)
        assert(math.type(li) == "integer", "network_get_player_text_color_string(int)")
        return "\\#dcdcdc\\"
    end
    S.get_time = function() return 1800000000 + w.frame // 30 end

    -- objects
    local function new_object(bhv, model, x, y, z)
        local s = { behavior = bhv, _model = model, oPosX = x, oPosY = y, oPosZ = z, oBehParams = 0, oFlags = 0,
            activeFlags = C.ACTIVE_FLAG_ACTIVE, oAnimState = 0, oTimer = 0, oFaceAngleYaw = 0, oMoveAngleYaw = 0,
            oIntangibleTimer = 0,
            oDrawingDistance = 4000, oCollisionDistance = 1000, oStarSpawnExtCutsceneFlags = 0, oHealth = 0,
            header = { gfx = { node = { flags = 0 }, scale = { x = 1, y = 1, z = 1 } } },
            _inited = false, _id = c.nextObj }
        c.nextObj = c.nextObj + 1
        local o = strict("Object", s)
        s.__built = true
        table.insert(c.objects, o)
        return o
    end
    c.spawn_object = new_object
    S.spawn_non_sync_object = function(...)
        assert(select("#", ...) == 6, "spawn_non_sync_object takes 6 arguments")
        local bhv, model, x, y, z, setup = ...
        local o = new_object(bhv, model, x, y, z)
        if setup ~= nil then setup(o) end
        return o
    end
    local function list_of(bhv) local b = c.behaviors[bhv]; return b and b.list end
    local function first_from(i, bhv)
        for j = i, #c.objects do
            local s = raw(c.objects[j])
            if s.behavior == bhv and s.activeFlags ~= C.ACTIVE_FLAG_DEACTIVATED then return c.objects[j] end
        end
        return nil
    end
    S.obj_get_first_with_behavior_id = function(bhv) return first_from(1, bhv) end
    S.obj_get_next_with_same_behavior_id = function(o)
        for j, x in ipairs(c.objects) do
            if x == o then return first_from(j + 1, raw(o).behavior) end
        end
        return nil
    end
    S.obj_has_behavior_id = function(o, bhv) return (o ~= nil and raw(o).behavior == bhv) and 1 or 0 end
    S.obj_mark_for_deletion = function(o) raw(o).activeFlags = C.ACTIVE_FLAG_DEACTIVATED end
    S.obj_set_model_extended = function(o, m) raw(o)._model = m end
    S.obj_set_billboard = function(o) raw(o)._billboard = true end
    S.obj_scale = function(o, s) local g = raw(o).header.gfx.scale; g.x, g.y, g.z = s, s, s end
    S.obj_scale_xyz = function(o, x, y, z) local g = raw(o).header.gfx.scale; g.x, g.y, g.z = x, y, z end
    S.load_object_collision_model = function()
        assert(c.cur ~= nil, "load_object_collision_model outside an object behaviour")
        assert(raw(c.cur).collisionData ~= nil, "load_object_collision_model without collisionData")
    end
    S.spawn_default_star = function(x, y, z)
        assert(select("#", x, y, z) == 3 and type(x) == "number")
        assert(c.cur ~= nil, "spawn_default_star called outside an object's behaviour loop")
        local bp = raw(c.cur).oBehParams
        if c.dedup[bp] or (c.dedupN or 0) >= 8 then return nil end    -- coopdx: 8 per level visit
        c.dedup[bp] = true
        c.dedupN = (c.dedupN or 0) + 1
        local st = new_object(C.id_bhvStarSpawnCoordinates, C.E_MODEL_STAR, raw(c.cur).oPosX, raw(c.cur).oPosY, raw(c.cur).oPosZ)
        raw(st).oBehParams = bp
        raw(st).oStarSpawnExtCutsceneFlags = 1
        raw(st)._home = { x = x, y = y, z = z }
        table.insert(c.starSpawns, { x = x, y = y, z = z, bparams = bp, from = { x = raw(c.cur).oPosX, y = raw(c.cur).oPosY, z = raw(c.cur).oPosZ }, star = st })
        table.insert(w.queue, { kind = "star", from = c, level = c.level, area = c.area, act = c.act, bparams = bp, x = x, y = y, z = z })
        return st
    end

    -- coopdx's real _G is shared by every mod: `_G.name = v` (characters.lua / charselect.lua exports)
    -- lands there and bare reads fall through to it; `_G.missing` is nil there, not an error. One per
    -- simulated client (each client is its own game process).
    S._G = setmetatable({}, {
        __index = function(_, k)
            local v = rawget(c.env, k)
            if v ~= nil then return v end
            v = S[k]
            if v ~= nil then return v end
            return C[k]
        end,
        __newindex = function(_, k, v) rawset(c.env, k, v) end,
    })

    -- environment: stubs, then the constants prelude (+ Lua std lib); anything else is an error
    c.env = setmetatable({}, {
        __index = function(_, k)
            local v = S[k]
            if v ~= nil then return v end
            v = C[k]
            if v ~= nil then return v end
            error("undefined global: " .. tostring(k), 2)
        end,
    })
    -- every stub must be a real v1.5.1 API (or a global the engine exposes)
    for k, v in pairs(S) do
        if type(v) == "function" and API[k] == nil then error("stub " .. k .. " is not a coopdx v1.5.1 function") end
    end
end

-- helpers for tests ----------------------------------------------------------------------------
function Sim.ctx(c) return c.env.sgl_mission_ctx() end

function Sim.objects_with(c, bhv)
    local out = {}
    for _, o in ipairs(c.objects) do
        if raw(o).behavior == bhv and raw(o).activeFlags ~= C.ACTIVE_FLAG_DEACTIVATED then table.insert(out, o) end
    end
    return out
end

function Sim.stars_of(c, starId)
    local n = 0
    for _, o in ipairs(c.objects) do
        local s = raw(o)
        if (s.behavior == C.id_bhvStarSpawnCoordinates or s.behavior == C.id_bhvStar) and ((s.oBehParams >> 24) & 0xFF) == starId
            and s.activeFlags ~= C.ACTIVE_FLAG_DEACTIVATED then n = n + 1 end
    end
    return n
end

function Sim.cmd(c, name, args)
    local fn = c.commands[name]
    assert(fn, "no command /" .. name)
    return fn(args or "")
end

function Sim.find(list, pattern)
    for _, s in ipairs(list) do
        if s:find(pattern) then return s end
    end
    return nil
end

function Sim.hud_has(c, pattern)
    for _, s in ipairs(c.hudText) do
        if s:find(pattern) then return true end
    end
    return false
end

return Sim
