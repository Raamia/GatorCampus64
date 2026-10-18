-- Super Gatorlator 64: mission framework (docs/game_design.md section 6, docs/flow.md section 5).
--
-- One MISSION per stage act. A mission is a table registered with sgl_mission_register(def) (see
-- swamp_missions.lua for real ones). This file provides:
--   * instance + leader: players see each other only in the same level + area + act (an "instance").
--     The instance LEADER is the level- and area-synced player there with the smallest globalIndex
--     (the same rule as coopdx's own get_network_player_smallest_global()). The host may be elsewhere
--     (or gone): authority never assumes it. When the leader leaves, the next one takes over on the
--     next frame, because the state is synced, not held by the leader.
--   * synced state: gGlobalSyncTable keys namespaced per instance, "sglm_<level>_<area>_<act>_<f>".
--     Framework fields: s (state), r (round), t (seconds in state), w (fail reason).
--     Mission fields (free use): p, f, a, c, x, o, g. Only the leader writes, and only on change. Every
--     client can write the sync table in coopdx; concurrent writes converge to the writer with the
--     smaller globalIndex (smlua_sync_table seq rule), i.e. to the leader. Late joiners get the whole
--     table on join, so nobody needs the host to replay anything.
--   * the controller object (id_bhvSglMission): spawned by Lua on every client when the act starts
--     (or placed by a level script with OBJECT_WITH_ACTS(MODEL_NONE, ..., bparams, id_bhvSglMission,
--     ACT_k): it is then adopted). Its loop runs the leader tick, the local tick, and spawns the star
--     with spawn_default_star() FROM INSIDE THE OBJECT LOOP (the function reads the star id from the
--     calling object's oBehParams >> 24 = act - 1). Never call it from HOOK_UPDATE.
--     coopdx de-duplicates spawn_default_star per behParams and sends PACKET_SPAWN_STAR to the area,
--     so "every client spawns once" gives exactly one star everywhere. The de-dup list is only cleared
--     when a level loads, so the star's bparams carry the round number in their low 16 bits (the star
--     id stays in the top byte): a /mission reset round gets a new star in the same visit. coopdx keeps
--     at most 8 such stars per level visit; after that the panel asks to re-enter the act.
--   * def.starAt(ctx) -> star, starFrom (optional): a star position that depends on the round (e.g.
--     the last token found), read from synced fields; nil = not known yet (the spawn waits).
--   * events: ctx:send(ev, data) -> reliable network_send to all + local dispatch. Receivers drop
--     events of other instances; def.onEvent decides (leader-only effects check ctx.isLeader).
--   * states: WAITING (fewer than the needed players) -> INTRO (banner, 3 s) -> ACTIVE ->
--     SUCCESS (star spawned) -> DONE (star collected); FAILED (4 s) -> a new round -> INTRO.
--     A player who arrives ALONE resets the instance (stale state from an earlier visit).
--   * HUD (sgl_hud.lua): act banner, left panel, players-needed prompt, STAR!/TRY AGAIN, markers.
--   * Study Group: entering a stage act alone sends an invite; everyone elsewhere gets a popup and a
--     10 s prompt: D-pad Up (or /join, or the mod menu "Join my study group") warps them into the
--     same level + act (door star lock still applies). /join <name> follows a given player.
--   * reusable mission kinds: sgl_mission_kind_reach (climb to a goal), sgl_mission_kind_buttons
--     (co-op: N buttons held at once, N = players here, min 2), sgl_mission_kind_race (start box,
--     countdown, ordered checkpoints, par time, results board).
--   * a stage geometry probe: def.probes = { { x, y, z, name } } must find a floor at y (+-2.5 m).
--     Otherwise the mission sleeps on that client (e.g. a stage build that moved things): no state
--     writes, no star. /mission force overrides it for testing.
-- Chat: /mission [status|reset|start|list|force], /join [name].
-- Unit tests: tools/luatest/run.sh (multi-client simulation with stubbed coopdx APIs).
--
--   * acts without a mission whose course.lua name starts with "COMING SOON" (sgl_act_is_soon): a
--     notice on arrival (free roam, no star, Pause > EXIT COURSE goes back) and no Study Group invite.
--   * the HUD stays hidden while the character select menu (charselect.lua) covers the screen.
--   * the star: a "got" event (with the collector's name) ends the round (DONE) from any live state, and
--     a levelStar mission also ends when its level-script star vanishes (collected on another client).
--     Everyone else in the act gets 10 s to LEAVE TOGETHER: D-pad Up = Pause > EXIT COURSE
--     (level_trigger_warp(WARP_OP_EXIT): the stage's 0xF1 -> outside its hub door, no life lost).
--   * def.toStart(ctx, m) (race kind: back to the start box; Reitz act 3: into the robotics lab):
--     D-pad Down or /mission start. It decides itself in which states it works.
--   * def.compactPanel: the left panel shrinks to its first line once the act is under way, and opens
--     up again for a few seconds when something happens (ctx.loc.expandUntil).
--   * def.onLeave(ctx): called when the player leaves the act (the race stops its music).
--   * verified runs (hosted server, sgl_bridge.lua): every client keeps its own count of the round's
--     ACTIVE time (ctx.rc, round_clock) and calls _G.sglOnRoundSuccess(def, round, frames, full) when it
--     sees the round succeed; the headless host times the round itself from the synced state.
--
-- Adding a mission (another stage, or Swamp acts 4 / 5 / 6): in a <stage>_missions.lua that sorts
-- after this file, call sgl_mission_register({ id, level = LEVEL_X, act = k, title = <the act name
-- in course.lua, renamed from "COMING SOON - ...">, objective (<= ~60 chars), star = {x,y,z} (game
-- units of that stage), starFrom, probes = { {x,y,z,name} }, kind = sgl_mission_kind_reach/buttons/
-- race(spec) } (or your own callbacks). The mission spawns its star: do not also place a bhvStar for
-- that act in the level script. Exception: levelStar = true when the level script DOES place that
-- act's star (Swamp act 1): the mission then never spawns one (it falls back to spawning if the level
-- has none). Keep packets small and event-only; anything every client must agree on goes through
-- ctx:set (leader) / ctx:send (events).

---------------------------------------------------------------------------------------------
-- constants
---------------------------------------------------------------------------------------------
SGL_MS_IDLE = 0
SGL_MS_WAITING = 1
SGL_MS_INTRO = 2
SGL_MS_ACTIVE = 3
SGL_MS_SUCCESS = 4
SGL_MS_FAILED = 5
SGL_MS_DONE = 6
SGL_MS_NAMES = { [0] = "idle", "waiting", "intro", "active", "success", "failed", "done" }

SGL_MISSION_INTRO_SECONDS = 3
SGL_MISSION_FAIL_SECONDS = 4
SGL_MISSION_BANNER_FRAMES = 120          -- act banner on arrival / at INTRO (4 s)
SGL_MISSION_STAR_CUTSCENE_RANGE = 4000   -- star spawn cutscene only for players within 40 m
SGL_MISSION_PROBE_TOLERANCE = 250        -- 2.5 m
SGL_PARTY_PROMPT_FRAMES = 300            -- Study Group prompt: 10 s
SGL_PARTY_INVITE_COOLDOWN = 60 * 30      -- one invite per level + act per player per minute
SGL_PARTY_JOIN_WINDOW = 120 * 30         -- plain /join follows the last invite for 2 minutes

local MISSION_FIELDS = { "p", "f", "a", "c", "x", "o", "g" }
local ALL_FIELDS = { "s", "r", "t", "w", "p", "f", "a", "c", "x", "o", "g" }

local function has_bhv(o, id)
    if o == nil then return false end
    local r = obj_has_behavior_id(o, id)   -- an integer in v1.5.1 (0 is truthy in Lua)
    return r == true or r == 1
end

local function obj_alive(o, id)
    return o ~= nil and o.activeFlags ~= ACTIVE_FLAG_DEACTIVATED and has_bhv(o, id)
end

local function set_hidden(o, hidden)
    local flags = o.header.gfx.node.flags
    if hidden then
        o.header.gfx.node.flags = flags | GRAPH_RENDER_INVISIBLE
    else
        o.header.gfx.node.flags = flags & ~GRAPH_RENDER_INVISIBLE
    end
end

local function popcount(v)
    local n = 0
    while v > 0 do
        n = n + (v & 1)
        v = v >> 1
    end
    return n
end

local function chat(text) djui_chat_message_create(text) end

---------------------------------------------------------------------------------------------
-- registry
---------------------------------------------------------------------------------------------
SGL_MISSIONS = {}        -- [level][act] = def
SGL_MISSION_LIST = {}    -- registration order (the order is the same on every client)

-- def fields: id, level, act, title, objective, star {x,y,z}; optional: area (1), starFrom, minPlayers
-- (1), probes, starCutsceneRange (units; default 40 m: farther players get no star cutscene),
-- levelStar (the level script places this act's star: never spawn one), starAt(ctx) -> star, starFrom (a
-- per-round star position; nil while unknown), pointsFile (the file that holds the
-- mission's coordinates, named in the console when a probe fails; default swamp_missions.lua), kind (a
-- table of callbacks from sgl_mission_kind_*), and the callbacks themselves:
-- onReset(ctx), onStart(ctx), leaderTick(ctx), localTick(ctx), onEvent(ctx, ev, data),
-- needPlayers(ctx), spawnLocal(ctx), panel(ctx) -> lines, hud(ctx). Own callbacks override the kind's.
function sgl_mission_register(def)
    if type(def) ~= "table" or type(def.id) ~= "string" or type(def.level) ~= "number"
        or type(def.act) ~= "number" or def.act < 1 or def.act > 6 or type(def.star) ~= "table" then
        log_to_console("[SGL] sgl_mission_register: bad mission definition " .. tostring(def and def.id), CONSOLE_MESSAGE_ERROR)
        return nil
    end
    if def.kind ~= nil then
        for k, v in pairs(def.kind) do
            if def[k] == nil then def[k] = v end
        end
    end
    def.area = def.area or 1
    def.minPlayers = def.minPlayers or 1
    def.title = def.title or ("ACT " .. def.act)
    def.starFrom = def.starFrom or def.star
    if sgl_mission_star_id ~= nil then def.starId = sgl_mission_star_id(def.act) else def.starId = def.act - 1 end
    def.num = #SGL_MISSION_LIST + 1
    def.bparams = ((def.starId & 0xFF) << 24) | ((def.num & 0xFF) << 16)
    SGL_MISSIONS[def.level] = SGL_MISSIONS[def.level] or {}
    if SGL_MISSIONS[def.level][def.act] ~= nil then
        log_to_console("[SGL] two missions for level " .. def.level .. " act " .. def.act .. ": " .. def.id, CONSOLE_MESSAGE_WARNING)
    end
    SGL_MISSIONS[def.level][def.act] = def
    table.insert(SGL_MISSION_LIST, def)
    return def
end

function sgl_mission_get(level, act)
    local l = SGL_MISSIONS[level]
    return l and l[act] or nil
end

---------------------------------------------------------------------------------------------
-- instance + leader
---------------------------------------------------------------------------------------------
function sgl_instance_key(np)
    return np.currLevelNum .. ":" .. np.currAreaIndex .. ":" .. np.currActNum
end

-- pure: entries = { { li = localIndex, gi = globalIndex, synced = bool }, ... }
-- -> local index + global index of the leader (smallest globalIndex among synced entries), or nil
function sgl_elect_leader(entries)
    local li, gi = nil, nil
    for _, e in ipairs(entries) do
        if e.synced and (gi == nil or e.gi < gi) then li, gi = e.li, e.gi end
    end
    return li, gi
end

local function np_synced(np)
    return np.currAreaSyncValid and np.currLevelSyncValid
end

-- local indices of connected players in my level + area + act (syncedOnly: level + area synced ones)
function sgl_instance_players(syncedOnly)
    local me = gNetworkPlayers[0]
    local out = {}
    for i = 0, MAX_PLAYERS - 1 do
        local np = gNetworkPlayers[i]
        if np ~= nil and np.connected and np.currLevelNum == me.currLevelNum and np.currAreaIndex == me.currAreaIndex
            and np.currActNum == me.currActNum and (not syncedOnly or np_synced(np)) then
            table.insert(out, i)
        end
    end
    return out
end

function sgl_instance_leader()
    local entries = {}
    for _, i in ipairs(sgl_instance_players(false)) do
        local np = gNetworkPlayers[i]
        table.insert(entries, { li = i, gi = np.globalIndex, synced = np_synced(np) })
    end
    return sgl_elect_leader(entries)
end

function sgl_is_leader()
    return np_synced(gNetworkPlayers[0]) and sgl_instance_leader() == 0
end

-- nobody else (synced or still loading) in my level + area + act
function sgl_mission_alone()
    return #sgl_instance_players(false) <= 1
end

---------------------------------------------------------------------------------------------
-- mission context (one per instance visit, local) + synced fields
---------------------------------------------------------------------------------------------
local CTX = {}
CTX.__index = CTX

function sgl_mission_sync_key(level, area, act, field)
    return "sglm_" .. level .. "_" .. area .. "_" .. act .. "_" .. field
end

function CTX:get(field)
    local v = gGlobalSyncTable[self.keys[field]]
    if type(v) ~= "number" then return 0 end
    return v
end

-- leader only (or a lone arriving player). Integers only; writes only on change.
function CTX:set(field, v)
    v = math.floor(v)
    local k = self.keys[field]
    if gGlobalSyncTable[k] ~= v then gGlobalSyncTable[k] = v end
    self[field] = v
end

function CTX:setState(s)
    if self.s == s then return end
    self:set("t", 0)
    if self.lead ~= nil then self.lead.tick = 0 end
    self:set("s", s)
end

function CTX:succeed()
    if self.s == SGL_MS_ACTIVE then self:setState(SGL_MS_SUCCESS) end
end

function CTX:fail(code)
    if self.s == SGL_MS_ACTIVE then
        self:set("w", code or 0)
        self:setState(SGL_MS_FAILED)
    end
end

-- reliable event to everyone + local delivery (receivers drop other instances)
function CTX:send(ev, data)
    data = data or {}
    data.sgl = "m"
    data.ik = self.key
    data.ev = ev
    data.r = self.r
    data.gi = gNetworkPlayers[0].globalIndex
    network_send(true, data)
    sgl_mission_dispatch(self, data)
end

function CTX:name_of(li)
    local np = gNetworkPlayers[li]
    return np and np.name or "?"
end

local function new_ctx(def, np)
    local ctx = setmetatable({}, CTX)
    ctx.def = def
    ctx.level, ctx.area, ctx.act = np.currLevelNum, np.currAreaIndex, np.currActNum
    ctx.key = sgl_instance_key(np)
    ctx.keys = {}
    for _, f in ipairs(ALL_FIELDS) do
        ctx.keys[f] = sgl_mission_sync_key(ctx.level, ctx.area, ctx.act, f)
        ctx[f] = 0
    end
    ctx.loc = { round = -1 }     -- local scratch, reset every round
    ctx.run = {
        runId = sgl_deepspace_new_run_id(),
        activeStartedFrame = nil,
        elapsedFrames = 0,
        retries = 0,
        failedPending = false,
        submitted = false,
    }
    ctx.lead = nil               -- leader scratch, fresh whenever this client becomes leader
    ctx.objs = {}                -- local helper objects (live as long as the controller)
    ctx.players, ctx.n, ctx.need = {}, 0, def.minPlayers
    ctx.age, ctx.stateAge, ctx.bannerAge = 0, 0, 0
    ctx.lastState = -1
    ctx.isLeader = false
    ctx.freeze = false
    ctx.dormant = false
    return ctx
end

local function refresh(ctx)
    for _, f in ipairs(ALL_FIELDS) do ctx[f] = ctx:get(f) end
    ctx.players = sgl_instance_players(true)
    ctx.n = #ctx.players
    local li, gi = sgl_instance_leader()
    ctx.leaderLi, ctx.leaderGi = li, gi
    local leader = li == 0 and np_synced(gNetworkPlayers[0])
    if leader and not ctx.isLeader then ctx.lead = { tick = 0 } end
    if not leader then ctx.lead = nil end
    ctx.isLeader = leader
    if ctx.def.needPlayers ~= nil then ctx.need = ctx.def.needPlayers(ctx) else ctx.need = ctx.def.minPlayers end
end

-- new round: clear the mission fields, back to INTRO (or WAITING). Leader / lone arrival only.
function sgl_mission_reset(ctx)
    ctx:set("r", ctx:get("r") + 1)
    for _, f in ipairs(MISSION_FIELDS) do ctx:set(f, 0) end
    ctx:set("w", 0)
    ctx:set("t", 0)
    if ctx.def.onReset ~= nil then ctx.def.onReset(ctx) end
    ctx:set("s", ctx.n >= ctx.need and SGL_MS_INTRO or SGL_MS_WAITING)
    ctx.lead = ctx.isLeader and { tick = 0 } or nil
end

---------------------------------------------------------------------------------------------
-- event dispatch
---------------------------------------------------------------------------------------------
function sgl_mission_dispatch(ctx, data)
    local ev = data.ev
    if ev == "got" then
        if data.r ~= ctx.r then return end -- ignore a delayed reward from an older replay
        -- someone collected this act's star: DONE from any live state (a levelStar star can be grabbed
        -- before the leader has seen anyone reach the goal: the round must not stay ACTIVE / SUCCESS with
        -- a marker over a star that is gone), no respawn for late joiners, and everyone else may leave
        -- together (sgl_exit_offer)
        if ctx.loc.got == nil then ctx.loc.got = data.nm or "?" end
        if ctx.isLeader and ctx.s ~= SGL_MS_DONE and ctx.s ~= SGL_MS_IDLE then ctx:setState(SGL_MS_DONE) end
        if ctx.def.minPlayers > 1 and ctx.loc.participated then
            sgl_coop_complete(ctx, data.nm)
        elseif data.gi ~= gNetworkPlayers[0].globalIndex then
            sgl_exit_offer(data.nm)
        end
    elseif ev == "reset" then
        if ctx.run ~= nil and (ctx.run.activeStartedFrame ~= nil or ctx.run.elapsedFrames > 0) then
            ctx.run.failedPending = true
        end
        if ctx.isLeader and not ctx.dormant then sgl_mission_reset(ctx) end
        if data.gi ~= gNetworkPlayers[0].globalIndex then
            sgl_hud_toast("Mission restarted", 3, SGL_HUD_ORANGE)
        end
    elseif ctx.def.onEvent ~= nil then
        ctx.def.onEvent(ctx, ev, data)
    end
end

---------------------------------------------------------------------------------------------
-- leader tick / local tick / star
---------------------------------------------------------------------------------------------
local function leader_tick(ctx)
    local def = ctx.def
    local lead = ctx.lead
    lead.tick = (lead.tick or 0) + 1
    ctx.second = false
    if lead.tick >= 30 then
        lead.tick = 0
        ctx.second = true
    end
    local s = ctx.s
    if s == SGL_MS_IDLE then
        sgl_mission_reset(ctx)
    elseif s == SGL_MS_WAITING then
        if ctx.n >= ctx.need then ctx:setState(SGL_MS_INTRO) end
    elseif s == SGL_MS_INTRO then
        if ctx.n < ctx.need then
            ctx:setState(SGL_MS_WAITING)
        else
            if ctx.second then ctx:set("t", ctx.t + 1) end
            if ctx.t >= SGL_MISSION_INTRO_SECONDS then
                if def.onStart ~= nil then def.onStart(ctx) end
                ctx:setState(SGL_MS_ACTIVE)
            end
        end
    elseif s == SGL_MS_ACTIVE then
        if ctx.n < ctx.need then
            ctx:setState(SGL_MS_WAITING)   -- co-op: pause until enough players are back
        elseif def.leaderTick ~= nil then
            def.leaderTick(ctx)
        end
    elseif s == SGL_MS_SUCCESS or s == SGL_MS_DONE then
        if def.tickAfterSuccess and def.leaderTick ~= nil then def.leaderTick(ctx) end
    elseif s == SGL_MS_FAILED then
        if ctx.second then ctx:set("t", ctx.t + 1) end
        if ctx.t >= SGL_MISSION_FAIL_SECONDS then sgl_mission_reset(ctx) end
    end
end

local function on_state_change(ctx, old, new)
    ctx.stateAge = 0
    ctx.loc.expandUntil = ctx.age + 150    -- a compact panel opens up for 5 s
    if new == SGL_MS_INTRO and old ~= -1 then ctx.bannerAge = 0 end
    if old == -1 then return end   -- first look after arriving: no sounds
    if old == SGL_MS_ACTIVE and new ~= SGL_MS_ACTIVE and ctx.run ~= nil and ctx.run.activeStartedFrame ~= nil then
        ctx.run.elapsedFrames = ctx.run.elapsedFrames + math.max(0, get_global_timer() - ctx.run.activeStartedFrame)
        ctx.run.activeStartedFrame = nil
    end
    if new == SGL_MS_FAILED then
        if ctx.run ~= nil then ctx.run.failedPending = true end
        play_sound(SOUND_MENU_CAMERA_BUZZ, gGlobalSoundSource)
    elseif new == SGL_MS_WAITING and old == SGL_MS_ACTIVE then
        sgl_hud_toast("Paused: waiting for enough players", 3, SGL_HUD_ORANGE)
    elseif new == SGL_MS_ACTIVE then
        if ctx.run ~= nil and not ctx.run.submitted then
            if ctx.run.failedPending then
                ctx.run.retries = ctx.run.retries + 1
                ctx.run.failedPending = false
            end
            ctx.run.activeStartedFrame = get_global_timer()
        end
        play_sound(SOUND_GENERAL2_RIGHT_ANSWER, gGlobalSoundSource)
    elseif new == SGL_MS_DONE then
        sgl_hud_toast("Star collected!", 3, SGL_HUD_GOLD)
    end
end

local function queue_completed_run(ctx)
    local run = ctx.run
    if run == nil or run.submitted or (run.activeStartedFrame == nil and run.elapsedFrames == 0) then return end
    if ctx.def.minPlayers > 1 or ctx.n > 1 then return end
    local activeFrames = run.activeStartedFrame ~= nil and (get_global_timer() - run.activeStartedFrame) or 0
    local elapsed = math.max(1, run.elapsedFrames + activeFrames)
    if sgl_deepspace_queue_run({
        runId = run.runId,
        missionId = ctx.def.id,
        elapsedFrames = elapsed,
        retries = run.retries,
        assisted = false,
    }) then
        run.submitted = true
    else
        log_to_console("[SGL] Run finished, but the DeepSpace outbox could not save it.", CONSOLE_MESSAGE_WARNING)
    end
end

-- this round's ACTIVE time on my own clock (game frames, summed over co-op pauses), for the hosted
-- server's run check (sgl_bridge.lua: the headless host measures the same round itself and compares).
-- full = I saw the round before it went active (an arrival mid-round only has a partial count). Every
-- client in the act reports once per round, when it sees the round succeed (ACTIVE -> SUCCESS / DONE).
local function round_clock(ctx, old, new)
    local rc = ctx.rc
    if rc == nil or rc.r ~= ctx.r then
        rc = { r = ctx.r, frames = 0, since = nil, reported = false,
            full = new ~= SGL_MS_ACTIVE and new ~= SGL_MS_SUCCESS and new ~= SGL_MS_DONE }
        ctx.rc = rc
        if new == SGL_MS_ACTIVE then rc.since = get_global_timer() end
    end
    if old == new then return end
    local now = get_global_timer()
    if old == SGL_MS_ACTIVE and rc.since ~= nil then
        rc.frames = rc.frames + math.max(0, now - rc.since)
        rc.since = nil
    end
    if new == SGL_MS_ACTIVE then rc.since = now end
    if old == SGL_MS_ACTIVE and (new == SGL_MS_SUCCESS or new == SGL_MS_DONE) and not rc.reported then
        rc.reported = true
        if _G.sglOnRoundSuccess ~= nil then _G.sglOnRoundSuccess(ctx.def, rc.r, rc.frames, rc.full) end
    end
end

local function local_tick(ctx)
    local def = ctx.def
    if ctx.loc.round ~= ctx.r then
        ctx.loc = { round = ctx.r, star = false, starTries = 0, witnessed = false }
    end
    if ctx.rc == nil or ctx.rc.r ~= ctx.r or ctx.s ~= ctx.lastState then
        round_clock(ctx, ctx.rc ~= nil and ctx.rc.r == ctx.r and ctx.lastState or -1, ctx.s)
    end
    if ctx.s ~= ctx.lastState then
        on_state_change(ctx, ctx.lastState, ctx.s)
        ctx.lastState = ctx.s
    end
    if ctx.s == SGL_MS_ACTIVE then ctx.loc.participated = true end
    if ctx.s ~= SGL_MS_SUCCESS and ctx.s ~= SGL_MS_DONE and ctx.s ~= SGL_MS_IDLE then
        ctx.loc.witnessed = true   -- I saw this round before its star: I get the star cutscene
    end
    if not ctx.spawnedLocal then
        ctx.spawnedLocal = true
        if def.spawnLocal ~= nil then def.spawnLocal(ctx) end
    end
    -- a levelStar mission's star vanished (collected here, or on another client: packet_collect_star
    -- deletes the copies): the same as a "got" event, which may arrive later or not at all
    if def.levelStar and ctx.levelStarFound and ctx.loc.got == nil and ctx.s ~= SGL_MS_IDLE
        and ctx.age % 10 == 0 and not sgl_mission_star_exists(def) then
        ctx.loc.got = "?"
        queue_completed_run(ctx)
        if ctx.isLeader and ctx.s ~= SGL_MS_DONE then ctx:setState(SGL_MS_DONE) end
    end
    ctx.freeze = false
    if def.localTick ~= nil then def.localTick(ctx) end
end

-- a star of this act already in the level (spawned by a packet, or placed by the level script)?
local function mission_star_exists(def)
    for _, bhv in ipairs({ id_bhvStarSpawnCoordinates, id_bhvStar }) do
        local o = obj_get_first_with_behavior_id(bhv)
        local guard = 0
        while o ~= nil and guard < 64 do
            if ((o.oBehParams >> 24) & 0xFF) == def.starId then return true end
            o = obj_get_next_with_same_behavior_id(o)
            guard = guard + 1
        end
    end
    return false
end
sgl_mission_star_exists = mission_star_exists

-- where this round's star goes: def.starAt(ctx) (per round, from synced fields) or the fixed def.star.
-- -> star, starFrom, or nil while def.starAt does not know yet
function sgl_mission_star_pos(ctx)
    local def = ctx.def
    if def.starAt == nil then return def.star, def.starFrom end
    local star, from = def.starAt(ctx)
    if star == nil then return nil end
    return star, from or star
end

-- the bparams of this round's star: the act's star id (top byte) + mission number, and the round in the
-- low 16 bits, so coopdx's per-visit de-dup (spawn_star_deduplication, cleared only at level load) lets
-- a /mission reset round spawn its own star
function sgl_mission_star_bparams(def, round)
    return def.bparams | (math.floor(round or 0) & 0xFFFF)
end

-- every client, from the controller's loop (spawn_default_star needs the calling object)
local function star_tick(ctx, o)
    if ctx.loc.star or ctx.s ~= SGL_MS_SUCCESS then return end
    local def = ctx.def
    if ctx.levelStarFound or mission_star_exists(def) then
        ctx.loc.star = true
        return
    end
    local pos, starFrom = sgl_mission_star_pos(ctx)
    if pos == nil then return end            -- its synced position is still on its way
    -- late joiners (did not see the mission happen) get the star where it lands, without a cutscene
    local from = ctx.loc.witnessed and starFrom or pos
    o.oBehParams = sgl_mission_star_bparams(def, ctx.r)
    o.oPosX, o.oPosY, o.oPosZ = from.x, from.y, from.z
    local star = spawn_default_star(pos.x, pos.y, pos.z)
    if star ~= nil then
        ctx.loc.star = true
        local m = gMarioStates[0]
        local dx, dy, dz = m.pos.x - pos.x, m.pos.y - pos.y, m.pos.z - pos.z
        local range = def.starCutsceneRange or SGL_MISSION_STAR_CUTSCENE_RANGE
        if not ctx.loc.witnessed or dx * dx + dy * dy + dz * dz > range * range then
            star.oStarSpawnExtCutsceneFlags = 0
        end
    else
        -- not in normal play mode yet, or de-duplicated (coopdx keeps 8 stars per level visit): retry
        -- for 2 s, then give up and say so (the panel asks to re-enter the act)
        ctx.loc.starTries = ctx.loc.starTries + 1
        if ctx.loc.starTries > 60 then
            ctx.loc.star = true
            ctx.loc.starLost = true
            log_to_console("[SGL] mission " .. def.id .. ": no star could be spawned in round " .. ctx.r
                .. " (coopdx spawns at most 8 per level visit): re-enter the act", CONSOLE_MESSAGE_WARNING)
        end
    end
end

---------------------------------------------------------------------------------------------
-- controller object
---------------------------------------------------------------------------------------------
local sCtrl = nil     -- the controller object of my instance
local sCtx = nil      -- its context
local sForce = false  -- /mission force: ignore failed geometry probes

function sgl_mission_ctx() return sCtx end

local function ctrl_alive()
    return obj_alive(sCtrl, id_bhvSglMission)
end

local function probe(ctx)
    ctx.dormant = false
    if sForce then return end
    for _, p in ipairs(ctx.def.probes or {}) do
        local fy = find_floor_height(p.x, p.y + 200, p.z)
        if math.abs(fy - p.y) > SGL_MISSION_PROBE_TOLERANCE then
            ctx.dormant = true
            ctx.dormantWhy = string.format("no floor at %s (found y %d, expected %d)", p.name or "probe",
                math.floor(fy), math.floor(p.y))
            log_to_console("[SGL] mission " .. ctx.def.id .. " sleeps: " .. ctx.dormantWhy
                .. " - stage geometry does not match " .. (ctx.def.pointsFile or "swamp_missions.lua")
                .. " coordinates", CONSOLE_MESSAGE_WARNING)
            return
        end
    end
end

local function ctrl_init(o)
    o.oFlags = OBJ_FLAG_UPDATE_GFX_POS_AND_ANGLE | OBJ_FLAG_ACTIVE_FROM_AFAR
    -- keep ticking while the local player reads a sign or watches a star cutscene
    o.activeFlags = o.activeFlags | ACTIVE_FLAG_INITIATED_TIME_STOP
    o.oIntangibleTimer = -1
    local np = gNetworkPlayers[0]
    local def = sgl_mission_get(np.currLevelNum, np.currActNum)
    if def == nil or (ctrl_alive() and not (sCtrl == o)) then
        obj_mark_for_deletion(o)
        return
    end
    sCtrl = o
    o.oBehParams = def.bparams
    sCtx = new_ctx(def, np)
    probe(sCtx)
    refresh(sCtx)
    if sCtx.dormant then return end
    if sgl_mission_alone() then
        sgl_mission_reset(sCtx)   -- first one here: drop whatever an earlier visit left behind
    end
    local found = mission_star_exists(def)
    if def.levelStar then
        -- the level script's star is THE star of this act; never spawn a second one (even after it
        -- was collected and deleted). Without it, fall back to spawning one so the act stays winnable.
        sCtx.levelStarFound = found
        if not found then
            log_to_console("[SGL] mission " .. def.id .. ": the level script has no star for act " .. def.act
                .. " (id " .. def.starId .. "); the mission spawns one instead", CONSOLE_MESSAGE_WARNING)
        end
    elseif found then
        log_to_console("[SGL] level script already has a star for act " .. def.act .. " (id " .. def.starId
            .. "); mission " .. def.id .. " spawns its own: remove the static one", CONSOLE_MESSAGE_WARNING)
    end
end

local function ctrl_loop(o)
    if sCtrl == nil or not (sCtrl == o) or sCtx == nil then
        obj_mark_for_deletion(o)
        return
    end
    local ctx = sCtx
    refresh(ctx)
    ctx.age = ctx.age + 1
    ctx.stateAge = ctx.stateAge + 1
    ctx.bannerAge = ctx.bannerAge + 1
    if ctx.dormant then return end
    if ctx.isLeader then leader_tick(ctx) end
    local_tick(ctx)
    star_tick(ctx, o)
end

id_bhvSglMission = hook_behavior(nil, OBJ_LIST_DEFAULT, true, ctrl_init, ctrl_loop, "bhvSglMission")

-- one controller per instance visit: spawned when the act starts (once the area is synced)
local function drop_ctx()
    local ctx = sCtx
    sCtrl, sCtx = nil, nil
    if ctx ~= nil and ctx.def.onLeave ~= nil then ctx.def.onLeave(ctx) end
end

local function spawner_update()
    local np = gNetworkPlayers[0]
    local def = sgl_mission_get(np.currLevelNum, np.currActNum)
    if def == nil or np.currAreaIndex ~= def.area then
        drop_ctx()
        return
    end
    if sCtx ~= nil and sCtx.key ~= sgl_instance_key(np) then drop_ctx() end
    if not np.currAreaSyncValid or ctrl_alive() then return end
    if obj_get_first_with_behavior_id(id_bhvSglMission) ~= nil then return end   -- its init adopts it
    spawn_non_sync_object(id_bhvSglMission, E_MODEL_NONE, def.starFrom.x, def.starFrom.y, def.starFrom.z,
        function(obj) obj.oBehParams = def.bparams end)
end

-- generic visual helper (flames, markers): billboard, animated, no interaction
local function fx_init(o)
    o.oFlags = OBJ_FLAG_UPDATE_GFX_POS_AND_ANGLE | OBJ_FLAG_ACTIVE_FROM_AFAR
    obj_set_billboard(o)
    o.oIntangibleTimer = -1
    o.oDrawingDistance = 20000
end

local function fx_loop(o)
    o.oAnimState = o.oAnimState + 1
end

id_bhvSglMissionFx = hook_behavior(nil, OBJ_LIST_DEFAULT, true, fx_init, fx_loop, "bhvSglMissionFx")

---------------------------------------------------------------------------------------------
-- hooks: star collected, packets, input freeze, HUD
---------------------------------------------------------------------------------------------
local function on_interact(m, o, interactType, interactValue)
    if m.playerIndex ~= 0 or interactType ~= INTERACT_STAR_OR_KEY or o == nil or interactValue ~= true then return end
    local ctx = sCtx
    if ctx == nil or ctx.dormant or not ctrl_alive() then return end
    if ((o.oBehParams >> 24) & 0xFF) ~= ctx.def.starId then return end
    queue_completed_run(ctx)
    ctx:send("got", { nm = gNetworkPlayers[0].name })
end

local function on_before_mario_update(m)
    if m.playerIndex ~= 0 or sCtx == nil or not sCtx.freeze then return end
    -- race countdown: players in the start box wait for GO
    local c = m.controller
    c.buttonPressed = 0
    c.buttonDown = 0
    c.stickX = 0
    c.stickY = 0
    c.stickMag = 0
    c.rawStickX = 0
    c.rawStickY = 0
end

local function got_text(ctx)
    local who = ctx.loc.got
    if who ~= nil and who ~= "?" then return "Star collected by " .. who end
    return "Star collected"
end

-- connected players other than me (anywhere)
local function others_online()
    local n = 0
    for i = 1, MAX_PLAYERS - 1 do
        local np = gNetworkPlayers[i]
        if np ~= nil and np.connected then n = n + 1 end
    end
    return n
end

local function state_line(ctx)
    local s = ctx.s
    if s == SGL_MS_WAITING then
        return { string.format("Players here: %d - needs %d", ctx.n, ctx.need), SGL_HUD_ORANGE }
    elseif s == SGL_MS_INTRO then
        return { "Get ready...", SGL_HUD_WHITE }
    elseif s == SGL_MS_SUCCESS then
        if ctx.loc.got ~= nil then return { got_text(ctx), SGL_HUD_GREEN } end
        if ctx.loc.starLost and not mission_star_exists(ctx.def) then
            return { "Done! (no more stars this visit: re-enter the act)", SGL_HUD_GREEN }
        end
        return { "Done! Grab the star!", SGL_HUD_GREEN }
    elseif s == SGL_MS_DONE then
        if ctx.def.levelStar then
            return { got_text(ctx) .. " (replay: re-enter the act)", SGL_HUD_GREEN }
        end
        return { got_text(ctx) .. " (replay: /mission reset)", SGL_HUD_GREEN }
    elseif s == SGL_MS_FAILED then
        return { "Not this time - restarting...", SGL_HUD_RED }
    end
    return nil
end

local function mission_hud()
    local ctx = sCtx
    if ctx == nil or not ctrl_alive() or sgl_hud_blocked() then return end
    local def = ctx.def
    if ctx.dormant then
        if ctx.age < 300 then
            sgl_hud_panel({ { def.title, SGL_HUD_GOLD, 0.34 },
                { "Mission offline here: " .. (ctx.dormantWhy or "?"), SGL_HUD_GREY, 0.26 },
                { "(stage changed? /mission force to try anyway)", SGL_HUD_GREY, 0.26 } })
        end
        return
    end
    local stage = sgl_stage_by_level ~= nil and sgl_stage_by_level(ctx.level) or nil
    local kicker = (stage and stage.name or "MISSION") .. " - ACT " .. ctx.act
    -- the act banner belongs to the start of a round: gone once play is under way (big texts
    -- such as countdowns and STAR! use the same screen area)
    local s = ctx.s
    -- (on arrival in the middle of a round the banner gets its full time: ctx.age == ctx.bannerAge)
    if s == SGL_MS_WAITING or s == SGL_MS_INTRO
        or (s == SGL_MS_ACTIVE and (ctx.stateAge < 30 or ctx.age == ctx.bannerAge)) then
        sgl_hud_banner(kicker, def.title, def.objective, ctx.bannerAge, SGL_MISSION_BANNER_FRAMES)
    end

    local lines = { { def.title, SGL_HUD_GOLD, 0.34 } }
    local sl = state_line(ctx)
    if sl ~= nil then table.insert(lines, { sl[1], sl[2], 0.3 }) end
    if ctx.s == SGL_MS_ACTIVE or def.tickAfterSuccess then
        if def.panel ~= nil then
            -- compact: once under way, only the first line, unless something just happened
            local compact = def.compactPanel and ctx.s == SGL_MS_ACTIVE and ctx.stateAge > SGL_MISSION_BANNER_FRAMES
                and ctx.age > (ctx.loc.expandUntil or 0)
            for i, l in ipairs(def.panel(ctx) or {}) do
                if not compact or i == 1 then table.insert(lines, { l[1], l[2], l[3] or 0.3 }) end
            end
        end
    end
    sgl_hud_panel(lines)

    if ctx.s == SGL_MS_WAITING then
        -- def.waitingText(ctx): a solo mode while the co-op waits (Swamp act 3, swamp_chomp.lua)
        local solo = def.waitingText ~= nil and def.waitingText(ctx) or nil
        if others_online() == 0 then
            sgl_hud_prompt(solo or string.format("This act needs %d players - you are the only one online", ctx.need),
                solo and "Pause > EXIT COURSE to go back" or "Invite a friend to the game, or Pause > EXIT COURSE to go back")
        else
            sgl_hud_prompt(solo or string.format("Needs a study buddy: %d/%d here", ctx.n, ctx.need),
                "Friends got an invite: D-pad Up, /join or Pause > Mods > Join my study group")
        end
    elseif ctx.s == SGL_MS_SUCCESS and ctx.loc.got == nil then
        if ctx.stateAge < 90 then sgl_hud_big("STAR!", SGL_HUD_GOLD, 2.5) end
        local pos = sgl_mission_star_pos(ctx)
        if pos ~= nil and not (ctx.loc.starLost and not mission_star_exists(def)) then
            sgl_hud_marker(pos, "STAR", SGL_HUD_GOLD, gMarioStates[0])
        end
    elseif ctx.s == SGL_MS_FAILED and ctx.stateAge < 90 then
        sgl_hud_big("TRY AGAIN", SGL_HUD_RED, 1.6)
    end
    if def.hud ~= nil then def.hud(ctx) end
end

---------------------------------------------------------------------------------------------
-- "COMING SOON" acts (course.lua act names, sgl_act_is_soon): a built stage entered in an act that has
-- no mission yet is free roam without a star. Say so on arrival, so nobody waits for a mission that
-- is not there: Pause > EXIT COURSE (or /campus hub) goes back to the hub, no life lost.
---------------------------------------------------------------------------------------------
SGL_SOON_BANNER_FRAMES = 150     -- 5 s
SGL_SOON_PANEL_FRAMES = 600      -- 20 s
local sSoon = nil                 -- { key, age, stage, act } of the current coming-soon visit

function sgl_soon_act()
    local np = gNetworkPlayers[0]
    if np.currActNum < 1 or sgl_mission_get(np.currLevelNum, np.currActNum) ~= nil then return nil end
    local stage = sgl_stage_by_level(np.currLevelNum)
    if stage == nil or not sgl_stage_ready(stage) or not sgl_act_is_soon(stage, np.currActNum) then return nil end
    return stage, np.currActNum
end

local function soon_update()
    local np = gNetworkPlayers[0]
    local stage, act = sgl_soon_act()
    if stage == nil or not np.currAreaSyncValid then
        sSoon = nil   -- (re)starts once the area has synced, so a new act never shows the old notice
        return
    end
    local key = sgl_instance_key(np)
    if sSoon == nil or sSoon.key ~= key then
        sSoon = { key = key, age = 0, stage = stage, act = act }
        log_to_console("[SGL] " .. stage.name .. " act " .. act .. " has no mission yet (coming soon): free roam")
    end
    sSoon.age = sSoon.age + 1
end

local function soon_hud()
    local v = sSoon
    if v == nil or sgl_hud_blocked() then return end
    if v.age < SGL_SOON_BANNER_FRAMES then
        sgl_hud_banner(v.stage.name .. " - ACT " .. v.act, sgl_act_name(v.stage, v.act) or "COMING SOON",
            "No mission here yet - explore! Pause > EXIT COURSE goes back.", v.age, SGL_SOON_BANNER_FRAMES)
    end
    if v.age < SGL_SOON_PANEL_FRAMES then
        sgl_hud_panel({ { "ACT " .. v.act .. ": COMING SOON", SGL_HUD_GOLD, 0.34 },
            { "Free roam - no star in this act yet", SGL_HUD_GREY, 0.28 },
            { "Pause > EXIT COURSE: back to campus", SGL_HUD_GREY, 0.28 } })
    end
end

---------------------------------------------------------------------------------------------
-- leave together: with the host's default "Leave level", only the player who grabs the star leaves.
-- Everyone else in the act gets 10 s to follow with D-pad Up, which takes the same exit as
-- Pause > EXIT COURSE (WARP_OP_EXIT -> the stage's 0xF1 -> outside its hub door, no life lost).
---------------------------------------------------------------------------------------------
SGL_EXIT_PROMPT_FRAMES = 300
local sExit = nil         -- { name, age, key } after someone else's star in my act

function sgl_exit_offer(name)
    local np = gNetworkPlayers[0]
    if np.currActNum < 1 or sgl_stage_by_level(np.currLevelNum) == nil then return end
    sExit = { name = name or "A friend", age = 0, key = sgl_instance_key(np) }
    play_sound(SOUND_MENU_STAR_SOUND, gGlobalSoundSource)
end

-- Save the same course bit once before a participant exits. CoopDX's native
-- collect-star packet also sets it; using a bit flag keeps either packet order idempotent.
function sgl_coop_complete(ctx, name)
    if ctx.loc.rewardedRound == ctx.r then return end
    ctx.loc.rewardedRound = ctx.r
    local stage = sgl_stage_by_level(ctx.level)
    if stage == nil then return end
    local file, course = get_current_save_file_num() - 1, stage.course - 1
    if file >= 0 then
        local flags = save_file_get_star_flags(file, course)
        local bit = 1 << ctx.def.starId
        if (flags & bit) == 0 then
            save_file_set_star_flags(file, course, flags | bit)
            save_file_do_save(file, 1)
        end
        gMarioStates[0].numStars = sgl_total_stars()
    end
    sgl_exit_offer(name)
    if sExit ~= nil then sExit.auto, sExit.round = true, ctx.r end
end

function sgl_exit_offer_active() return sExit ~= nil end

local function exit_update()
    local e = sExit
    if e == nil then return end
    e.age = e.age + 1
    if e.key ~= sgl_instance_key(gNetworkPlayers[0]) then sExit = nil; return end
    if e.auto then
        if sCtx == nil or sCtx.r ~= e.round then sExit = nil; return end
        -- Let finish reports arrive and let any active collection animation finish.
        if e.age >= 60 then sgl_exit_course(gMarioStates[0]) end
    elseif e.age >= SGL_EXIT_PROMPT_FRAMES then
        sExit = nil
    end
end

-- the pause menu's EXIT COURSE, from Lua. -> true when the exit started
function sgl_exit_course(m)
    if m.health <= 0xFF or (m.action & ACT_GROUP_MASK) == ACT_GROUP_CUTSCENE then return false end
    sExit = nil
    level_trigger_warp(m, WARP_OP_EXIT)
    return true
end

local function exit_hud()
    local e = sExit
    if e == nil or sgl_hud_blocked() then return end
    sgl_hud_prompt(e.auto and "Team Gator Crest earned!" or e.name .. " got the star!",
        e.auto and "Returning to campus together..." or "D-pad Up: back to campus together (or Pause > EXIT COURSE)",
        sgl_hud_fade(e.age, SGL_EXIT_PROMPT_FRAMES, 6, 30))
end

---------------------------------------------------------------------------------------------
-- Study Group: invites, /join, D-pad Up, mod menu button, player-list location
---------------------------------------------------------------------------------------------
local sInvite = nil       -- { lv, ac, gi, name, age, t }
local sInviteSent = {}    -- "level:act" -> global timer of my last invite

local function act_title(level, act)
    local def = sgl_mission_get(level, act)
    if def ~= nil then return def.title end
    local stage = sgl_stage_by_level ~= nil and sgl_stage_by_level(level) or nil
    if stage ~= nil and stage.acts ~= nil and stage.acts[act] ~= nil then return stage.acts[act] end
    return "ACT " .. act
end

function sgl_party_location_text(level, act)
    local stage = sgl_stage_by_level(level)
    if stage == nil then return nil end
    return stage.name .. " - Act " .. act .. ": " .. act_title(level, act)
end

local function others_in(level, act)
    local n = 0
    for i = 1, MAX_PLAYERS - 1 do
        local np = gNetworkPlayers[i]
        if np ~= nil and np.connected and np.currLevelNum == level and np.currActNum == act then n = n + 1 end
    end
    return n
end

-- -> true when the warp started
function sgl_party_join(level, act, who)
    local stage = sgl_stage_by_level(level)
    if stage == nil or act < 1 then
        chat("\\#ffa0a0\\[SGL] " .. (who or "They") .. " is not in a stage act right now.")
        return false
    end
    if not sgl_stage_ready(stage) then
        chat("\\#ffa0a0\\[SGL] " .. stage.name .. " is not built yet.")
        return false
    end
    local stars = sgl_total_stars()
    if stars < stage.stars then
        chat(string.format("\\#ffa0a0\\[SGL] %s is locked: it needs %d stars (you have %d).", stage.name, stage.stars, stars))
        play_sound(SOUND_MENU_CAMERA_BUZZ, gGlobalSoundSource)
        return false
    end
    local me = gNetworkPlayers[0]
    if me.currLevelNum == level and me.currActNum == act then
        chat("[SGL] You are already there.")
        return false
    end
    if warp_to_level(level, 1, act) then
        djui_popup_create(string.format("\\#ffd700\\Study group!\\#dcdcdc\\ Joining %s in %s act %d.",
            who or "your friends", stage.name, act), 2)
        sInvite = nil
        return true
    end
    return false
end

-- entering a stage act with nobody else there: invite everyone (once a minute per level + act)
local function party_sync_valid()
    local np = gNetworkPlayers[0]
    local stage = sgl_stage_by_level(np.currLevelNum)
    if stage == nil or np.currActNum < 1 then return end
    if sgl_mission_get(np.currLevelNum, np.currActNum) == nil and sgl_act_is_soon(stage, np.currActNum) then
        return   -- "COMING SOON" act: nothing to do together yet
    end
    local key = np.currLevelNum .. ":" .. np.currActNum
    local now = get_global_timer()
    local last = sInviteSent[key]
    if others_in(np.currLevelNum, np.currActNum) == 0 and (last == nil or now - last >= SGL_PARTY_INVITE_COOLDOWN) then
        sInviteSent[key] = now
        network_send(true, { sgl = "party", lv = np.currLevelNum, ac = np.currActNum, gi = np.globalIndex, nm = np.name })
    end
end

-- player list: "THE SWAMP - Act 3: GATOR CHOMP CHORUS" instead of the vanilla level name.
-- The override is local to each client, so every client labels every player (twice a second).
local function party_locations()
    if get_global_timer() % 15 ~= 0 then return end
    for i = 0, MAX_PLAYERS - 1 do
        local np = gNetworkPlayers[i]
        if np ~= nil and np.connected then
            local text = ""
            if np.currActNum >= 1 and sgl_stage_by_level(np.currLevelNum) ~= nil then
                text = sgl_party_location_text(np.currLevelNum, np.currActNum)
            elseif np.currLevelNum == SGL_HUB_LEVEL then
                text = "Central Campus"
            end
            if np.overrideLocation ~= text then network_player_set_override_location(np, text) end
        end
    end
end

local function party_receive(data)
    local me = gNetworkPlayers[0]
    if data.gi == me.globalIndex then return end
    if type(data.lv) ~= "number" or type(data.ac) ~= "number" then return end
    if me.currLevelNum == data.lv and me.currActNum == data.ac then return end
    local stage = sgl_stage_by_level(data.lv)
    if stage == nil then return end
    sInvite = { lv = data.lv, ac = data.ac, gi = data.gi, name = data.nm or "A friend", age = 0, t = get_global_timer() }
    djui_popup_create(string.format("\\#ffd700\\%s\\#dcdcdc\\ started %s act %d: %s.\nD-pad Up or /join to follow!",
        sInvite.name, stage.name, data.ac, act_title(data.lv, data.ac)), 3)
    play_sound(SOUND_MENU_MESSAGE_APPEAR, gGlobalSoundSource)
end

function sgl_party_invite() return sInvite end

local function party_update()
    local inv = sInvite
    if inv == nil then return end
    inv.age = inv.age + 1
    -- already there (came through the door, /campus, ...): nothing to join any more
    local me = gNetworkPlayers[0]
    if me.currLevelNum == inv.lv and me.currActNum == inv.ac then sInvite = nil end
end

-- D-pad Up: leave together (after someone else's star) or accept the Study Group invite;
-- D-pad Down: the mission's "back to the start" (race)
local function party_mario_update(m)
    if m.playerIndex ~= 0 or is_game_paused() then return end
    local pressed = m.controller.buttonPressed
    if (pressed & U_JPAD) ~= 0 then
        if sExit ~= nil then
            sgl_exit_course(m)
        elseif sInvite ~= nil and sInvite.age < SGL_PARTY_PROMPT_FRAMES then
            sgl_party_join(sInvite.lv, sInvite.ac, sInvite.name)
        end
    end
    if (pressed & D_JPAD) ~= 0 then
        local ctx = sCtx
        if ctx ~= nil and ctrl_alive() and not ctx.dormant and ctx.def.toStart ~= nil then ctx.def.toStart(ctx, m) end
    end
end

local function party_hud()
    local inv = sInvite
    if inv == nil or inv.age >= SGL_PARTY_PROMPT_FRAMES or sExit ~= nil or sgl_hud_blocked() then return end
    local stage = sgl_stage_by_level(inv.lv)
    if stage == nil then return end
    sgl_hud_prompt("D-pad Up: join " .. inv.name,
        stage.name .. " act " .. inv.ac .. ": " .. act_title(inv.lv, inv.ac) .. "  (or /join)",
        sgl_hud_fade(inv.age, SGL_PARTY_PROMPT_FRAMES, 6, 30))
end

-- the stage instance (level + act) with the most other players
function sgl_party_best_group()
    local counts, best, bestN = {}, nil, 0
    for i = 1, MAX_PLAYERS - 1 do
        local np = gNetworkPlayers[i]
        if np ~= nil and np.connected and np.currActNum >= 1 and sgl_stage_by_level(np.currLevelNum) ~= nil then
            local key = np.currLevelNum .. ":" .. np.currActNum
            counts[key] = (counts[key] or 0) + 1
            if counts[key] > bestN then
                bestN = counts[key]
                best = { lv = np.currLevelNum, ac = np.currActNum, name = np.name }
            end
        end
    end
    return best, bestN
end

local function join_best_group()
    local g = sgl_party_best_group()
    if g == nil then
        chat("[SGL] Nobody is in a stage right now. Walk into a door and your friends get an invite.")
        return
    end
    sgl_party_join(g.lv, g.ac, g.name)
end

local function on_join_command(msg)
    msg = (msg or ""):gsub("^%s+", ""):gsub("%s+$", "")
    if msg == "" then
        if sInvite ~= nil and get_global_timer() - sInvite.t <= SGL_PARTY_JOIN_WINDOW then
            sgl_party_join(sInvite.lv, sInvite.ac, sInvite.name)
        else
            local g = sgl_party_best_group()
            if g ~= nil then
                sgl_party_join(g.lv, g.ac, g.name)
            else
                chat("[SGL] No study group to join yet. /join <name> follows a friend into their stage act.")
            end
        end
        return true
    end
    local q = msg:lower()
    for i = 1, MAX_PLAYERS - 1 do
        local np = gNetworkPlayers[i]
        if np ~= nil and np.connected and np.name:lower():sub(1, #q) == q then
            sgl_party_join(np.currLevelNum, np.currActNum, np.name)
            return true
        end
    end
    chat("[SGL] No player named '" .. msg .. "' is online.")
    return true
end

---------------------------------------------------------------------------------------------
-- /mission
---------------------------------------------------------------------------------------------
local function on_mission_command(msg)
    local sub = ((msg or ""):match("^%s*(%S*)") or ""):lower()
    if sub == "list" then
        for _, d in ipairs(SGL_MISSION_LIST) do
            chat(string.format("[SGL] %s: level %d act %d (star %d) %s", d.id, d.level, d.act, d.starId, d.title))
        end
        return true
    elseif sub == "force" then
        sForce = not sForce
        chat("[SGL] missions ignore the stage geometry check: " .. (sForce and "ON" or "OFF")
            .. " (re-enter the act to apply)")
        return true
    end
    local ctx = sCtx
    if ctx == nil or not ctrl_alive() then
        chat("[SGL] No mission in this act. /mission list shows them all.")
        return true
    end
    if sub == "start" then
        if ctx.def.toStart == nil or ctx.dormant then
            chat("[SGL] This mission has no start to go back to.")
        else
            ctx.def.toStart(ctx, gMarioStates[0])
        end
        return true
    end
    if sub == "reset" then
        if ctx.dormant then
            chat("[SGL] This mission is offline here (" .. (ctx.dormantWhy or "?") .. ").")
        else
            ctx:send("reset", {})
            chat("[SGL] Mission restart requested.")
        end
        return true
    end
    local leader = ctx.leaderLi ~= nil and ctx:name_of(ctx.leaderLi) or "nobody"
    chat(string.format("[SGL] %s (%s act %d): %s, round %d, players %d/%d, leader %s%s",
        ctx.def.title, ctx.def.id, ctx.act, SGL_MS_NAMES[ctx.s] or tostring(ctx.s), ctx.r, ctx.n, ctx.need,
        leader, ctx.dormant and (", OFFLINE: " .. (ctx.dormantWhy or "?")) or ""))
    chat(string.format("[SGL] p %d  f %d  a %d  c %d  x %d  o %d  g %d  t %d", ctx.p, ctx.f, ctx.a, ctx.c, ctx.x,
        ctx.o, ctx.g, ctx.t))
    return true
end

---------------------------------------------------------------------------------------------
-- packets
---------------------------------------------------------------------------------------------
local function on_packet_receive(data)
    if data.sgl == "m" then
        local ctx = sCtx
        if ctx ~= nil and data.ik == ctx.key and ctrl_alive() and not ctx.dormant then
            sgl_mission_dispatch(ctx, data)
        end
    elseif data.sgl == "party" then
        party_receive(data)
    end
end

---------------------------------------------------------------------------------------------
-- mission kinds (reusable: a kind returns callbacks; the mission def adds its texts + coordinates)
---------------------------------------------------------------------------------------------

local function dist2_xz(p, q)
    local dx, dz = p.x - q.x, p.z - q.z
    return dx * dx + dz * dz
end

local function alive_player(m)
    return m ~= nil and m.health > 0xFF
end

-- REACH: climb to a goal. spec = {
--   goal = {x,y,z}, goalRadius, goalBelow (accept feet this far below goal.y), goalLabel,
--   zone = {x0,x1,z0,z1} (heights only count inside it), ground (y of 0 m on the meter),
--   milestones = { { name, y }, ... },
--   route = { { pos = {x,y,z}, label, doneY }, ... } (optional: the HUD marker walks the route: it shows
--   the first stage whose doneY is above the local player (outside the zone: the first stage), then the
--   goal) }
-- Leader: best height of anyone in the zone -> p (metres), milestones -> f bits; anyone at the goal
-- -> SUCCESS. Positions of everyone in the instance are synced by coopdx, so no packets are needed.
function sgl_mission_kind_reach(spec)
    local K = {}
    local top = math.floor((spec.goal.y - spec.ground) / 100)

    local function in_zone(p)
        local z = spec.zone
        return z == nil or (p.x >= z.x0 and p.x <= z.x1 and p.z >= z.z0 and p.z <= z.z1)
    end

    local function at_goal(p)
        return dist2_xz(p, spec.goal) <= spec.goalRadius * spec.goalRadius
            and p.y >= spec.goal.y - (spec.goalBelow or 100)
    end
    K.reachAtGoal = at_goal

    -- the route stage the local marker points at: index into spec.route, or nil for the goal
    local function route_stage(p)
        local route = spec.route
        if route == nil or #route == 0 then return nil end
        if not in_zone(p) then return 1 end
        for i, st in ipairs(route) do
            if p.y < st.doneY then return i end
        end
        return nil
    end
    K.routeStage = route_stage

    K.onReset = function(ctx)
        ctx:set("p", 0)
        ctx:set("f", 0)
    end

    K.leaderTick = function(ctx)
        local best, flags, reached = ctx.p, ctx.f, false
        for _, li in ipairs(ctx.players) do
            local m = gMarioStates[li]
            if alive_player(m) then
                if in_zone(m.pos) then
                    local h = math.floor((m.pos.y - spec.ground) / 100)
                    if h > best then best = h end
                    for i, ms in ipairs(spec.milestones or {}) do
                        if m.pos.y >= ms.y - 50 then flags = flags | (1 << (i - 1)) end
                    end
                end
                if at_goal(m.pos) then reached = true end
            end
        end
        if best ~= ctx.p then ctx:set("p", best) end
        if flags ~= ctx.f then ctx:set("f", flags) end
        if reached then ctx:succeed() end
    end

    K.localTick = function(ctx)
        local L = ctx.loc
        if L.flags == nil then L.flags = ctx.f end
        if ctx.f ~= L.flags then
            for i, ms in ipairs(spec.milestones or {}) do
                local bit = 1 << (i - 1)
                if (ctx.f & bit) ~= 0 and (L.flags & bit) == 0 then
                    sgl_hud_toast(ms.name .. " reached! (" .. math.floor((ms.y - spec.ground) / 100) .. " m)", 3, SGL_HUD_GREEN)
                    play_sound(SOUND_MENU_COLLECT_SECRET, gGlobalSoundSource)
                    L.expandUntil = ctx.age + 150
                end
            end
            L.flags = ctx.f
        end
    end

    K.panel = function(ctx)
        local m = gMarioStates[0]
        local here = in_zone(m.pos) and math.max(0, math.floor((m.pos.y - spec.ground) / 100)) or 0
        local lines = { { string.format("You %d m   team best %d m   goal %d m", here, ctx.p, top), SGL_HUD_WHITE } }
        for i, ms in ipairs(spec.milestones or {}) do
            local got = (ctx.f & (1 << (i - 1))) ~= 0
            table.insert(lines, { (got and "+ " or "- ") .. ms.name .. " " .. math.floor((ms.y - spec.ground) / 100) .. " m",
                got and SGL_HUD_GREEN or SGL_HUD_GREY, 0.28 })
        end
        return lines
    end

    K.hud = function(ctx)
        if ctx.s == SGL_MS_ACTIVE or ctx.s == SGL_MS_INTRO then
            local m = gMarioStates[0]
            local i = route_stage(m.pos)
            if i ~= nil then
                local st = spec.route[i]
                sgl_hud_marker({ x = st.pos.x, y = st.pos.y + 120, z = st.pos.z }, st.label, SGL_HUD_ORANGE, m)
            else
                sgl_hud_marker(spec.goal, spec.goalLabel or "GOAL", SGL_HUD_GOLD, m)
            end
        end
    end
    return K
end

-- BUTTONS (co-op): spec = {
--   buttons = { { x, y, z, name }, ... }, minPlayers (2), radius, height, scale, flameUp,
--   HOLD mode (spec.pound nil): sets = { [2] = { i, j }, [3] = {...}, [4] = {...} }, hold (seconds),
--     chant = { "GA...", ... } (one word per second held)
--   POUND mode (spec.pound = true): phrases = { [2] = { {i, j}, {k, l}, ... }, [3] = {...}, [4] = {...} },
--     chant = { "GA...", "TOR...", "CHOMP!" }, beat (seconds per word, 1), window (seconds, 1.3) }
-- N = players here clamped to [minPlayers, #buttons]: that many buttons light up and all of them must be
-- stood on at once. One player can only stand on one button, so N players are needed.
-- HOLD: hold them for `hold` seconds. Leader: f (held bits), a (N), c (seconds held).
-- POUND: a song of #phrases phrases. In each phrase its lit set (phrases[N][k]) must be held while the
-- crowd counts in (one chant word per beat); on the LAST word every lit button's player must ground-pound
-- on it within `window` seconds (jump, then Z). All pounded: next phrase (a new set lights up, so players
-- run to other corners); the last phrase -> SUCCESS. Too late, or someone steps off during the count:
-- "Off the beat!" and the phrase starts over. Leader: f (held bits), a (N), c (chant word 0..#chant,
-- #chant = the pound window), x (phrases done), p (pounded bits); the leader judges the ground pounds
-- from the synced player actions (ACT_GROUND_POUND / _LAND), so remote players get the window plus
-- their latency.
SGL_BUTTON_SCALE = 1.5          -- the vanilla purple switch scale (bhv_purple_switch_loop)
SGL_BUTTON_PRESSED_Y = 0.2      -- ... and its pressed height scale

local function button_init(o)
    o.oFlags = OBJ_FLAG_UPDATE_GFX_POS_AND_ANGLE | OBJ_FLAG_ACTIVE_FROM_AFAR
    o.collisionData = gGlobalObjectCollisionData.purple_switch_seg8_collision_0800C7A8
    o.oCollisionDistance = 1500
    o.oDrawingDistance = 20000
    o.oIntangibleTimer = -1
    obj_scale(o, SGL_BUTTON_SCALE)
end

local function button_loop(o)
    load_object_collision_model()
end

id_bhvSglButton = hook_behavior(nil, OBJ_LIST_SURFACE, true, button_init, button_loop, "bhvSglButton")

-- a ground pound in progress or just landed (what the pound window accepts)
function sgl_is_pound_action(action)
    return action == ACT_GROUND_POUND or action == ACT_GROUND_POUND_LAND
end

function sgl_mission_kind_buttons(spec)
    local K = { minPlayers = spec.minPlayers or 2 }
    local maxN = #spec.buttons
    local scale = spec.scale or SGL_BUTTON_SCALE
    local pound = spec.pound == true
    local chant = spec.chant or (pound and { "GA...", "TOR...", "CHOMP!" } or nil)
    local nWords = chant and #chant or 0
    local BEAT = math.floor((spec.beat or 1.0) * 30)
    local WINDOW = math.floor((spec.window or 1.3) * 30)
    local nPhrases = 1
    if pound and spec.phrases ~= nil then
        for _, list in pairs(spec.phrases) do nPhrases = math.max(nPhrases, #list) end
    end
    K.phraseCount = nPhrases

    local function count_for(n)
        return math.max(K.minPlayers, math.min(n, maxN))
    end
    K.buttonCount = count_for

    -- lit buttons for N players in phrase ph (0-based; HOLD mode ignores it)
    local function mask_for(N, ph)
        local set
        if pound and spec.phrases ~= nil and spec.phrases[N] ~= nil then
            local list = spec.phrases[N]
            set = list[((ph or 0) % #list) + 1]
        elseif spec.sets ~= nil then
            set = spec.sets[N]
        end
        local mask = 0
        if set == nil then
            for i = 1, N do mask = mask | (1 << (i - 1)) end
        else
            for _, i in ipairs(set) do mask = mask | (1 << (i - 1)) end
        end
        return mask
    end
    K.buttonMask = mask_for

    local function on_button(p, b)
        return dist2_xz(p, b) <= spec.radius * spec.radius and p.y >= b.y - 100 and p.y <= b.y + spec.height
    end
    K.onButton = on_button

    local function current_mask(ctx)
        return mask_for(ctx.a > 0 and ctx.a or count_for(ctx.n), ctx.x)
    end
    K.currentMask = current_mask

    K.needPlayers = function(ctx) return K.minPlayers end

    K.onReset = function(ctx)
        ctx:set("a", count_for(ctx.n))
        ctx:set("f", 0)
        ctx:set("c", 0)
        ctx:set("x", 0)
        ctx:set("p", 0)
    end
    K.onStart = K.onReset

    local function held_mask(ctx, mask)
        local held = 0
        for i, b in ipairs(spec.buttons) do
            local bit = 1 << (i - 1)
            if (mask & bit) ~= 0 then
                for _, li in ipairs(ctx.players) do
                    local m = gMarioStates[li]
                    if alive_player(m) and on_button(m.pos, b) then
                        held = held | bit
                        break
                    end
                end
            end
        end
        return held
    end

    local function hold_tick(ctx, mask, held)
        if held == mask then
            ctx.lead.hold = (ctx.lead.hold or ctx.c * 30) + 1   -- a new leader resumes from the synced seconds
            local secs = ctx.lead.hold // 30
            if secs ~= ctx.c then ctx:set("c", secs) end
            if ctx.lead.hold >= spec.hold * 30 then ctx:succeed() end
        else
            ctx.lead.hold = 0
            if ctx.c ~= 0 then ctx:set("c", 0) end
        end
    end

    local function phrase_restart(ctx)
        local lead = ctx.lead
        lead.beat, lead.win = nil, nil
        if ctx.p ~= 0 then ctx:set("p", 0) end
        if ctx.c ~= 0 then ctx:set("c", 0) end
    end

    local function pound_tick(ctx, mask, held)
        local lead = ctx.lead
        if ctx.c < nWords then
            -- counting in: every lit button held, one chant word per beat
            if held == mask then
                lead.beat = (lead.beat or math.max(ctx.c - 1, 0) * BEAT) + 1   -- a new leader resumes the count
                local step = 1 + (lead.beat - 1) // BEAT
                if step >= nWords then
                    step = nWords
                    lead.win = 0
                    if ctx.p ~= 0 then ctx:set("p", 0) end
                end
                if step ~= ctx.c then ctx:set("c", step) end
            elseif ctx.c ~= 0 then
                phrase_restart(ctx)
                ctx:send("miss", { why = 1 })
            else
                lead.beat = nil
            end
            return
        end
        -- the pound window (the last chant word)
        lead.win = (lead.win or 0) + 1
        local got = ctx.p
        for i, b in ipairs(spec.buttons) do
            local bit = 1 << (i - 1)
            if (mask & bit) ~= 0 and (got & bit) == 0 then
                for _, li in ipairs(ctx.players) do
                    local m = gMarioStates[li]
                    if alive_player(m) and on_button(m.pos, b) and sgl_is_pound_action(m.action) then
                        got = got | bit
                        break
                    end
                end
            end
        end
        if got ~= ctx.p then ctx:set("p", got) end
        if got == mask then
            lead.beat, lead.win = nil, nil
            ctx:set("p", 0)
            ctx:set("c", 0)
            ctx:set("x", ctx.x + 1)
            if ctx.x >= nPhrases then ctx:succeed() end
        elseif lead.win >= WINDOW then
            phrase_restart(ctx)
            ctx:send("miss", { why = 2 })
        end
    end

    K.leaderTick = function(ctx)
        local N = count_for(ctx.n)
        if N ~= ctx.a then
            ctx:set("a", N)
            ctx.lead.hold = 0
            if pound then phrase_restart(ctx) end
        end
        local mask = mask_for(N, ctx.x)
        local held = held_mask(ctx, mask)
        if held ~= ctx.f then ctx:set("f", held) end
        if pound then pound_tick(ctx, mask, held) else hold_tick(ctx, mask, held) end
    end

    K.onEvent = function(ctx, ev, data)
        if ev ~= "miss" or data.r ~= ctx.r then return end
        play_sound(SOUND_MENU_CAMERA_BUZZ, gGlobalSoundSource)
        sgl_hud_toast(data.why == 1 and "Off the beat! Someone left a button - again" or
            "Off the beat! Pound on CHOMP! - again", 3, SGL_HUD_RED)
        ctx.loc.expandUntil = ctx.age + 150
    end

    K.spawnLocal = function(ctx)
        ctx.objs.buttons = {}
        for i, b in ipairs(spec.buttons) do
            local o = spawn_non_sync_object(id_bhvSglButton, E_MODEL_PURPLE_SWITCH, b.x, b.y, b.z, nil)
            local fx = spawn_non_sync_object(id_bhvSglMissionFx, E_MODEL_RED_FLAME, b.x, b.y + (spec.flameUp or 250), b.z,
                function(obj) obj_scale(obj, 4) end)
            ctx.objs.buttons[i] = { o = o, fx = fx, squish = scale }
        end
    end

    -- who stands on button i (local view, for the HUD only)
    local function occupant(ctx, b)
        for _, li in ipairs(ctx.players) do
            local m = gMarioStates[li]
            if alive_player(m) and on_button(m.pos, b) then return li end
        end
        return nil
    end

    K.localTick = function(ctx)
        local mask = current_mask(ctx)
        local live = ctx.s == SGL_MS_ACTIVE or ctx.s == SGL_MS_WAITING or ctx.s == SGL_MS_INTRO
        for i, rec in ipairs(ctx.objs.buttons or {}) do
            local bit = 1 << (i - 1)
            local active = live and (mask & bit) ~= 0
            local held = active and (ctx.f & bit) ~= 0
            if obj_alive(rec.o, id_bhvSglButton) then
                local target = held and SGL_BUTTON_PRESSED_Y or scale
                rec.squish = rec.squish + (target - rec.squish) * 0.35
                obj_scale_xyz(rec.o, scale, rec.squish, scale)
            end
            if obj_alive(rec.fx, id_bhvSglMissionFx) then
                if active then
                    local want = (held or (ctx.p & bit) ~= 0) and E_MODEL_BLUE_FLAME or E_MODEL_RED_FLAME
                    if rec.model ~= want then
                        obj_set_model_extended(rec.fx, want)
                        rec.model = want
                    end
                    set_hidden(rec.fx, false)
                else
                    set_hidden(rec.fx, true)
                end
            end
        end
        -- local feedback: click when I step on a lit button; a tick per chant word / held second
        local m = gMarioStates[0]
        local L = ctx.loc
        local on = nil
        for i, b in ipairs(spec.buttons) do
            if (mask & (1 << (i - 1))) ~= 0 and on_button(m.pos, b) then on = i end
        end
        if on ~= L.on then
            if on ~= nil and live then play_sound(SOUND_GENERAL2_PURPLE_SWITCH, gGlobalSoundSource) end
            L.on = on
        end
        if ctx.c ~= (L.c or 0) then
            if ctx.c > 0 and ctx.s == SGL_MS_ACTIVE then
                if pound and ctx.c >= nWords then
                    play_sound(SOUND_GENERAL_BIG_POUND, gGlobalSoundSource)
                else
                    play_sound(SOUND_GENERAL2_SWITCH_TICK_FAST, gGlobalSoundSource)
                end
                L.wordAge = 0
            end
            L.c = ctx.c
        end
        if L.wordAge ~= nil then L.wordAge = L.wordAge + 1 end
        if pound then
            if L.x == nil then L.x = ctx.x end
            if ctx.x > L.x and ctx.s ~= SGL_MS_IDLE then
                if ctx.x < nPhrases then
                    sgl_hud_toast(string.format("CHOMP! Phrase %d/%d - new corners are lit!", ctx.x, nPhrases), 3, SGL_HUD_GOLD)
                    play_sound(SOUND_GENERAL2_RIGHT_ANSWER, gGlobalSoundSource)
                end
                L.expandUntil = ctx.age + 150
            end
            L.x = ctx.x
        end
    end

    K.panel = function(ctx)
        local mask = current_mask(ctx)
        local N = popcount(mask)
        local lines = {}
        if pound then
            table.insert(lines, { string.format("Phrase %d/%d - lit buttons held: %d/%d", math.min(ctx.x + 1, nPhrases), nPhrases,
                popcount(ctx.f & mask), N), SGL_HUD_WHITE })
        else
            table.insert(lines, { string.format("Buttons held: %d/%d   (players here: %d)", popcount(ctx.f & mask), N, ctx.n), SGL_HUD_WHITE })
        end
        for i, b in ipairs(spec.buttons) do
            local bit = 1 << (i - 1)
            if (mask & bit) ~= 0 then
                local held = (ctx.f & bit) ~= 0
                local who = occupant(ctx, b)
                local text = "  " .. b.name .. (held and (" - held" .. (who and (" by " .. ctx:name_of(who)) or "")) or " - empty")
                if pound and (ctx.p & bit) ~= 0 then text = text .. " - CHOMP!" end
                table.insert(lines, { text, held and SGL_HUD_GREEN or SGL_HUD_RED, 0.28 })
            end
        end
        if pound then
            table.insert(lines, { "On CHOMP!: jump + Z (ground-pound) on your button", SGL_HUD_GOLD, 0.28 })
        elseif mask ~= 0 and (ctx.f & mask) == mask then
            table.insert(lines, { string.format("Hold it! %d/%d s", ctx.c, spec.hold), SGL_HUD_GOLD })
        end
        return lines
    end

    K.hud = function(ctx)
        if ctx.s ~= SGL_MS_ACTIVE then return end
        local mask = current_mask(ctx)
        for i, b in ipairs(spec.buttons) do
            local bit = 1 << (i - 1)
            if (mask & bit) ~= 0 and (ctx.f & bit) == 0 then
                sgl_hud_marker({ x = b.x, y = b.y + 200, z = b.z }, b.name, SGL_HUD_RED, gMarioStates[0])
            end
        end
        if chant == nil then return end
        if pound then
            -- the count-in, then the pound beat
            if ctx.c >= 1 then
                local word = chant[math.min(ctx.c, nWords)]
                local last = ctx.c >= nWords
                sgl_hud_big(word, last and SGL_HUD_GOLD or SGL_HUD_ORANGE, last and 2.6 or 2)
                if last then
                    sgl_hud_text_center("POUND IT! (jump + Z)", djui_hud_get_screen_width() / 2, 120, 0.4, SGL_HUD_WHITE, 1)
                end
            end
        elseif mask ~= 0 and (ctx.f & mask) == mask then
            -- every lit button held: the crowd chants one word per second held
            local word = chant[math.min(ctx.c + 1, nWords)]
            if word ~= nil then sgl_hud_big(word, SGL_HUD_ORANGE, 2) end
        end
    end
    return K
end

-- RACE: spec = {
--   start = { x, y, z }, startRadius, checkpoints = { { x, y, z, name, r }, ... } (the last = finish),
--   cpRadius, cpBelow, cpAbove, par (s), timeout (s), lobbyWait (s), countdown (s), resultsSeconds,
--   pbKey (mod_storage key), title (results board), gold (s, optional: a "gold time" on the board),
--   finishGrace (s after the first finish before the results, default 45), music (SEQ_* while racing,
--   optional) }
-- Phases (a): 0 lobby (start box), 1 countdown (players in the box are frozen), 2 racing,
-- 3 results. f = race number, c = phase seconds, p = finishers, x = racers at the gun.
-- The race ends when min(racers at the gun, players still here) have finished (a racer who leaves does
-- not stall it), finishGrace seconds after the first finish, or at the timeout.
-- Times are judged LOCALLY (each client's frames from its GO) and reported with a reliable "fin"
-- event; every client keeps the results, so a new leader still knows who beat par.
-- Star: the first finish under par. After the star, races go on for fun (tickAfterSuccess).
-- Back to the start: D-pad Down or /mission start teleports a player who is not racing into the start
-- box (no walk back after a try).
SGL_RACE_LOBBY, SGL_RACE_COUNTDOWN, SGL_RACE_RACING, SGL_RACE_RESULTS = 0, 1, 2, 3
SGL_RACE_FAIL_PAR = 1
SGL_RACE_MUSIC_PRIORITY = 4     -- SEQUENCE_ARGS(4, seq): above the level music, like Koopa the Quick's race

function sgl_mission_kind_race(spec)
    -- raceTiming: the hosted server's host times a race from GO (phase RACING) to the winning "fin"
    -- event, not from the round going active (the lobby wait is not part of a race time)
    local K = { tickAfterSuccess = true, raceTiming = true }
    local cps = spec.checkpoints
    local nCp = #cps
    local grace = spec.finishGrace or 45
    local raceSeq = spec.music and ((SGL_RACE_MUSIC_PRIORITY << 8) | spec.music) or nil
    local musicOn = false

    -- race music while the local player races (the background music queue: the level music comes back
    -- when it stops)
    local function set_music(on)
        if raceSeq == nil or on == musicOn then return end
        musicOn = on
        if on then
            play_music(SEQ_PLAYER_LEVEL, raceSeq, 0)
        else
            stop_background_music(raceSeq)
        end
    end

    local function in_box(p)
        local s = spec.start
        return dist2_xz(p, s) <= spec.startRadius * spec.startRadius and p.y >= s.y - 200 and p.y <= s.y + 500
    end
    K.inStartBox = in_box

    local function at_cp(p, cp)
        local r = cp.r or spec.cpRadius
        return dist2_xz(p, cp) <= r * r and p.y >= cp.y - spec.cpBelow and p.y <= cp.y + spec.cpAbove
    end
    K.atCheckpoint = at_cp

    local function results_for(ctx, race)
        ctx.loc.results = ctx.loc.results or {}
        local list = ctx.loc.results[race]
        if list == nil then
            list = {}
            ctx.loc.results[race] = list
        end
        return list
    end

    local function best_frames(list)
        local best = nil
        for _, r in ipairs(list) do
            if best == nil or r.fr < best then best = r.fr end
        end
        return best
    end

    local function count_in_box(ctx)
        local n = 0
        for _, li in ipairs(ctx.players) do
            if in_box(gMarioStates[li].pos) then n = n + 1 end
        end
        return n
    end

    local function to_lobby(ctx)
        ctx:set("a", SGL_RACE_LOBBY)
        ctx:set("c", 0)
        ctx.lead.wait, ctx.lead.count, ctx.lead.firstFin = nil, nil, nil
    end

    K.onReset = function(ctx)
        ctx:set("a", SGL_RACE_LOBBY)
        ctx:set("c", 0)
        ctx:set("p", 0)
        ctx:set("x", 0)
    end
    K.onStart = K.onReset

    K.leaderTick = function(ctx)
        local lead = ctx.lead
        local phase = ctx.a
        if phase == SGL_RACE_LOBBY then
            local inBox = count_in_box(ctx)
            local go = false
            if inBox == 0 then
                lead.wait = nil
                if ctx.c ~= 0 then ctx:set("c", 0) end
            elseif inBox >= ctx.n then
                go = true   -- everybody here is in the box
            else
                lead.wait = (lead.wait or (ctx.c > 0 and (spec.lobbyWait - ctx.c) * 30 or 0)) + 1
                local left = spec.lobbyWait - lead.wait // 30
                if left <= 0 then
                    go = true
                elseif left ~= ctx.c then
                    ctx:set("c", left)
                end
            end
            if go then
                lead.wait, lead.count = nil, 0
                ctx:set("c", spec.countdown)
                ctx:set("a", SGL_RACE_COUNTDOWN)
            end
        elseif phase == SGL_RACE_COUNTDOWN then
            lead.count = (lead.count or (spec.countdown - math.max(ctx.c, 1)) * 30) + 1
            local left = spec.countdown - lead.count // 30
            if left <= 0 then
                lead.firstFin = nil
                ctx:set("x", count_in_box(ctx))
                ctx:set("f", ctx.f + 1)
                ctx:set("p", 0)
                ctx:set("c", 0)
                ctx:set("a", SGL_RACE_RACING)
                lead.count = nil
            elseif left ~= ctx.c then
                ctx:set("c", left)
            end
        elseif phase == SGL_RACE_RACING then
            if ctx.second then ctx:set("c", ctx.c + 1) end
            local list = results_for(ctx, ctx.f)
            if #list ~= ctx.p then ctx:set("p", #list) end
            if #list > 0 and lead.firstFin == nil then lead.firstFin = ctx.c end
            local best = best_frames(list)
            if best ~= nil and best <= spec.par * 30 then ctx:succeed() end
            local need = math.min(ctx.x, math.max(ctx.n, 1))      -- racers who are still here
            if (ctx.x > 0 and #list >= need) or (lead.firstFin ~= nil and ctx.c >= lead.firstFin + grace)
                or ctx.c >= spec.timeout then
                lead.firstFin = nil
                ctx:set("c", 0)
                ctx:set("a", SGL_RACE_RESULTS)
            end
        elseif phase == SGL_RACE_RESULTS then
            if ctx.second then ctx:set("c", ctx.c + 1) end
            if ctx.c >= spec.resultsSeconds then
                if ctx.s == SGL_MS_ACTIVE then
                    ctx:fail(SGL_RACE_FAIL_PAR)   -- nobody beat par: FAILED -> new round -> lobby
                else
                    to_lobby(ctx)                 -- star already out: free races
                end
            end
        end
    end

    -- personal best (mod_storage, per client), read once
    local pbCache = nil
    local function get_pb()
        if pbCache == nil then pbCache = mod_storage_load_number(spec.pbKey, 0) or 0 end
        return pbCache
    end

    local function finish(ctx, L)
        L.racing = false
        L.finished = L.frames
        L.finishAge = 0
        local underPar = L.frames <= spec.par * 30
        play_sound(underPar and SOUND_GENERAL2_RIGHT_ANSWER or SOUND_MENU_CAMERA_BUZZ, gGlobalSoundSource)
        local pb = get_pb()
        if pb <= 0 or L.frames < pb then
            mod_storage_save_number(spec.pbKey, L.frames)
            pbCache = L.frames
            L.newPb = true
        end
        sgl_hud_toast("Finish! " .. sgl_hud_format_time(L.frames) .. (underPar and " - under par!" or
            (" - par is " .. sgl_hud_format_time(spec.par * 30))), 5, underPar and SGL_HUD_GREEN or SGL_HUD_WHITE)
        if spec.gold ~= nil and L.frames <= spec.gold * 30 then
            sgl_hud_toast("GOLD TIME! (under " .. sgl_hud_format_time(spec.gold * 30) .. ")", 5, SGL_HUD_GOLD)
        end
        if L.newPb then sgl_hud_toast("New personal best!", 5, SGL_HUD_GOLD) end
        ctx:send("fin", { race = ctx.f, fr = L.frames, nm = gNetworkPlayers[0].name })
        -- sgl_bridge.lua: report the finish to a hosted server's bridge (inert offline)
        if _G.sglOnRaceFinish ~= nil then _G.sglOnRaceFinish(spec.pbKey, L.frames) end
    end

    K.localTick = function(ctx)
        local m = gMarioStates[0]
        local L = ctx.loc
        local phase = ctx.a
        local inBox = in_box(m.pos)
        if phase == SGL_RACE_COUNTDOWN then
            L.ready = inBox
            ctx.freeze = inBox and alive_player(m)
            if ctx.c ~= L.lastC then
                if ctx.c > 0 then play_sound(SOUND_MENU_CHANGE_SELECT, gGlobalSoundSource) end
                L.lastC = ctx.c
            end
        else
            L.lastC = nil
        end
        if phase == SGL_RACE_RACING and L.race ~= ctx.f then
            L.race = ctx.f
            L.racing = (L.ready or inBox) and alive_player(m)
            L.ready = false
            L.cp, L.frames, L.goAge, L.finished, L.newPb = 1, 0, 0, nil, false
            if L.racing then
                play_sound(SOUND_GENERAL_RACE_GUN_SHOT, gGlobalSoundSource)
                play_race_fanfare()
            end
        end
        if L.goAge ~= nil then L.goAge = L.goAge + 1 end
        if L.finishAge ~= nil then L.finishAge = L.finishAge + 1 end
        set_music(L.racing == true and ctx.s ~= SGL_MS_IDLE)
        if L.racing then
            if phase ~= SGL_RACE_RACING then
                L.racing = false
                set_music(false)
                sgl_hud_toast("Race over - no finish this time", 3, SGL_HUD_GREY)
            else
                L.frames = L.frames + 1
                if at_cp(m.pos, cps[L.cp]) then
                    if L.cp >= nCp then
                        finish(ctx, L)
                        set_music(false)
                    else
                        play_sound(SOUND_MENU_COLLECT_SECRET, gGlobalSoundSource)
                        L.cp = L.cp + 1
                    end
                end
            end
        end
    end

    K.onEvent = function(ctx, ev, data)
        if ev ~= "fin" or data.r ~= ctx.r or type(data.race) ~= "number" or type(data.fr) ~= "number" then return end
        local list = results_for(ctx, data.race)
        for _, r in ipairs(list) do
            if r.gi == data.gi then return end
        end
        table.insert(list, { gi = data.gi, name = data.nm or "?", fr = data.fr })
        table.sort(list, function(a, b) return a.fr < b.fr end)
        if data.gi ~= gNetworkPlayers[0].globalIndex then
            sgl_hud_toast((data.nm or "?") .. " finished: " .. sgl_hud_format_time(data.fr), 3, SGL_HUD_WHITE)
        end
    end

    K.panel = function(ctx)
        local L = ctx.loc
        local phase = ctx.a
        local lines = {}
        if phase == SGL_RACE_LOBBY then
            table.insert(lines, { "Stand in the start box: " .. (spec.startLabel or "START"), SGL_HUD_WHITE })
            if ctx.c > 0 then table.insert(lines, { "Starting in " .. ctx.c .. " s - step in to race!", SGL_HUD_ORANGE }) end
            if not in_box(gMarioStates[0].pos) then
                table.insert(lines, { "D-pad Down or /mission start: teleport there", SGL_HUD_GREY, 0.26 })
            end
        elseif phase == SGL_RACE_COUNTDOWN then
            table.insert(lines, { L.ready and "Get set..." or "Starting! Get in the box!", SGL_HUD_ORANGE })
        elseif phase == SGL_RACE_RACING then
            if L.racing then
                local cp = cps[L.cp]
                table.insert(lines, { string.format("Checkpoint %d/%d: %s", L.cp, nCp, cp.name or ""), SGL_HUD_WHITE })
                table.insert(lines, { "Time " .. sgl_hud_format_time(L.frames) .. "   par " .. sgl_hud_format_time(spec.par * 30),
                    L.frames <= spec.par * 30 and SGL_HUD_GREEN or SGL_HUD_RED })
            elseif L.finished ~= nil then
                table.insert(lines, { "Your time " .. sgl_hud_format_time(L.finished), SGL_HUD_GREEN })
                table.insert(lines, { "D-pad Down: back to the start box", SGL_HUD_GREY, 0.26 })
            else
                table.insert(lines, { "Race on - wait for the next start", SGL_HUD_GREY })
            end
        else
            table.insert(lines, { "Race over - D-pad Down: back to the start box", SGL_HUD_GREY })
        end
        local pb = get_pb()
        if pb > 0 then
            local gold = spec.gold ~= nil and pb <= spec.gold * 30
            table.insert(lines, { "Personal best " .. sgl_hud_format_time(pb) .. (gold and "  GOLD" or ""),
                gold and SGL_HUD_GOLD or SGL_HUD_GREY, 0.26 })
        end
        return lines
    end

    K.hud = function(ctx)
        local L = ctx.loc
        local phase = ctx.a
        local me = gMarioStates[0]
        local live = ctx.s == SGL_MS_ACTIVE or ctx.s == SGL_MS_SUCCESS or ctx.s == SGL_MS_DONE
        if not live then return end
        if phase == SGL_RACE_LOBBY or phase == SGL_RACE_COUNTDOWN then
            if not in_box(me.pos) then sgl_hud_marker(spec.start, "START", SGL_HUD_GOLD, me) end
        end
        if phase == SGL_RACE_COUNTDOWN and ctx.c > 0 then
            sgl_hud_big(tostring(ctx.c), SGL_HUD_GOLD, 3)
        end
        if L.racing then
            local cp = cps[L.cp]
            sgl_hud_marker({ x = cp.x, y = cp.y + 250, z = cp.z }, L.cp >= nCp and "FINISH" or ("CP " .. L.cp), SGL_HUD_BLUE, me)
            if L.goAge ~= nil and L.goAge < 30 then sgl_hud_big("GO!", SGL_HUD_GREEN, 3) end
            local W = djui_hud_get_screen_width()
            sgl_hud_timer(L.frames, W - 92, 34, "TIME")
        end
        local showBoard = phase == SGL_RACE_RESULTS or (L.finishAge ~= nil and L.finishAge < 240)
        if showBoard and L.race ~= nil then
            local list = results_for(ctx, L.race)
            if #list > 0 then
                local rows = {}
                for _, r in ipairs(list) do table.insert(rows, { r.name, r.fr, r.fr <= spec.par * 30 }) end
                local W = sgl_hud_setup(FONT_NORMAL)
                sgl_hud_board((spec.title or "RACE") .. " - RACE " .. L.race, rows, W - 166, 84,
                    "Par " .. sgl_hud_format_time(spec.par * 30)
                    .. (spec.gold and ("   Gold " .. sgl_hud_format_time(spec.gold * 30)) or ""))
            end
        end
    end

    -- D-pad Down / /mission start: into the start box (not while racing, not mid-cutscene)
    K.toStart = function(ctx, m)
        local L = ctx.loc
        if L.racing then
            sgl_hud_toast("You are racing - finish first!", 2, SGL_HUD_ORANGE)
            return false
        end
        if ctx.s == SGL_MS_WAITING or m.health <= 0xFF or (m.action & ACT_GROUP_MASK) == ACT_GROUP_CUTSCENE
            or m.heldObj ~= nil or m.riddenObj ~= nil then
            return false
        end
        if in_box(m.pos) then return false end
        local s = spec.start
        local a = (gNetworkPlayers[0].globalIndex % 8) * math.pi / 4      -- players land side by side
        local r = math.min(250, (spec.startRadius or 300) * 0.5)
        m.pos.x, m.pos.y, m.pos.z = s.x + math.sin(a) * r, s.y + 20, s.z + math.cos(a) * r
        m.vel.x, m.vel.y, m.vel.z = 0, 0, 0
        m.forwardVel = 0
        m.faceAngle.y = atan2s(cps[1].z - s.z, cps[1].x - s.x)
        set_mario_action(m, ACT_IDLE, 0)
        if m.area ~= nil and m.area.camera ~= nil then soft_reset_camera(m.area.camera) end
        play_sound(SOUND_MENU_EXIT_PIPE, gGlobalSoundSource)
        sgl_hud_toast("Back in the start box", 2, SGL_HUD_WHITE)
        return true
    end

    K.spawnLocal = function(ctx)
        musicOn = false          -- a fresh act visit: the level music is playing
    end

    K.onLeave = function(ctx)
        set_music(false)
    end
    return K
end

---------------------------------------------------------------------------------------------
hook_event(HOOK_UPDATE, spawner_update)
hook_event(HOOK_UPDATE, soon_update)
hook_event(HOOK_UPDATE, party_update)
hook_event(HOOK_UPDATE, exit_update)
hook_event(HOOK_UPDATE, party_locations)
hook_event(HOOK_ON_INTERACT, on_interact)
hook_event(HOOK_BEFORE_MARIO_UPDATE, on_before_mario_update)
hook_event(HOOK_MARIO_UPDATE, party_mario_update)
hook_event(HOOK_ON_SYNC_VALID, party_sync_valid)
hook_event(HOOK_ON_PACKET_RECEIVE, on_packet_receive)
hook_event(HOOK_ON_HUD_RENDER, mission_hud)
hook_event(HOOK_ON_HUD_RENDER, soon_hud)
hook_event(HOOK_ON_HUD_RENDER, party_hud)
hook_event(HOOK_ON_HUD_RENDER, exit_hud)
hook_chat_command("mission", "[status|reset|start|list|force] Super Gatorlator 64 mission of this act", on_mission_command)
hook_chat_command("join", "[name] Join your friends' stage act (Study Group)", on_join_command)
if hook_mod_menu_button ~= nil then
    hook_mod_menu_button("Join my study group", function() join_best_group() end)
end
