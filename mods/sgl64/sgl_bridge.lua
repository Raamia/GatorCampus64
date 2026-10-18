-- Super Gatorlator 64: bridge between the hosted game and server/bridge (docs/web_platform_spec.md 6.2-6.4).
--
-- Only does anything on a HEADLESS dedicated host (sm64coopdx --headless --server ...), and on the
-- clients connected to one (gServerSettings.headlessServer is sent to joiners in the join packet).
-- Offline, on a normal (non-headless) host or on its clients, nothing prints and the inbox is never read.
--
-- Game -> bridge (events): the host prints one line per event to stdout:
--     SGLEVT {"t":"join","gi":3,"name":"Alberta"}
--   "t" first, then the other keys sorted; strings escaped (\" \\ \n \r \t \uXXXX for other control
--   bytes; non-ASCII bytes pass through as-is). Events: hello {version, proto}; join / leave {gi, name};
--   char {gi, name, friend (friend id, e.g. "daniel" or "guest_3"; "" = none), index (0 = none)};
--   fin {gi, name, race (the race's pbKey), frames, level, act}; login_req {gi, name};
--   link_req {gi, name, code}; run {mission, round, frames, client_frames, retries, level, act, players,
--   gi1, name1, ...} (verified runs, timed by the host itself: see "verified runs" below). The bridge
--   itself adds "exit" when the game process ends. Clients relay their
--   events to the host with a packet (sgl = "be"); the host takes `name` from its own player list.
--   sglBridgeEmit(t, fields) is the call for other files (sgl_login.lua: "login_req", "link_req",
--   "login_cancel"), on the host or on any client.
--
-- Bridge -> game (inbox): server/bridge writes <savepath>/sav/sgl64.modfs (a zip, coopdx mod_fs
-- format) holding inbox.json: {"seq": N, "cmds": [{"seq": n, "t": "<command>", ...fields}, ...]}.
-- The host calls mod_fs_reload() every 30 frames and runs each command whose seq is higher than the
-- last one it ran (in seq order). If the file's top-level seq goes BELOW the last one handled (the
-- bridge restarted its counter), the counter resets. Routing (host):
--   * "verified" and "announce" (SGL_BRIDGE_BROADCAST), or any command without a numeric gi:
--     network_send(true, ...) to every client + run on the host too;
--   * otherwise (login_code, login_failed, a leaderboard re-sent to a joiner, ...): network_send_to the
--     player with global index gi only.
-- Clients run the command handlers registered with sglBridgeOnCommand(name, fn); fn(fields) gets the
-- command's fields (primitives only: packets cannot carry tables). "announce" {text, secs} is built in
-- (a popup + a chat line for everyone; secs is advisory: coopdx popups have a fixed duration).
--
-- Hooks from the mission code (sgl_mission.lua), on clients: _G.sglOnRaceFinish(pbKey, frames) on the
-- finishing client of a race, _G.sglOnRoundSuccess(def, round, frames, full) on every client that sees a
-- round succeed (its own count, reported to the host for the "run" event).

SGL_BRIDGE_VERSION = "sgl64-web-1"
SGL_BRIDGE_PROTO = 1
SGL_BRIDGE_POLL_FRAMES = 30          -- inbox: mod_fs_reload() every 30 frames (1 s)
SGL_BRIDGE_CHAR_FRAMES = 15          -- character pick watch on the host
SGL_BRIDGE_INBOX_FILE = "inbox.json"
SGL_BRIDGE_BROADCAST = { verified = true, announce = true }

local PKT_EVENT = "be"               -- client -> host: an event for the host to print
local PKT_CMD = "bc"                 -- host -> client(s): an inbox command
local CMD_KEY = "bc_t"               -- command name inside a PKT_CMD packet

---------------------------------------------------------------------------------------------
-- JSON (small: enough for events and the inbox)
---------------------------------------------------------------------------------------------
local ESCAPES = { ['"'] = '\\"', ['\\'] = '\\\\', ['\n'] = '\\n', ['\r'] = '\\r', ['\t'] = '\\t',
    ['\b'] = '\\b', ['\f'] = '\\f' }

local function encode_string(s)
    return '"' .. s:gsub('[%c"\\]', function(c)
        return ESCAPES[c] or string.format("\\u%04x", c:byte())
    end) .. '"'
end

local function is_array(t)
    local n = 0
    for k in pairs(t) do
        if math.type(k) ~= "integer" or k < 1 then return false end
        n = n + 1
    end
    if n == 0 then return false end
    for i = 1, n do
        if t[i] == nil then return false end
    end
    return true
end

local encode_value

local function encode_table(t, depth)
    if depth > 16 then error("json: nesting too deep") end
    local out = {}
    if is_array(t) then
        for i = 1, #t do out[i] = encode_value(t[i], depth + 1) end
        return "[" .. table.concat(out, ",") .. "]"
    end
    local keys = {}
    for k in pairs(t) do
        if type(k) == "string" then
            keys[#keys + 1] = k
        elseif type(k) == "number" then
            keys[#keys + 1] = k
        end
    end
    table.sort(keys, function(a, b)
        if a == "t" then return b ~= "t" end
        if b == "t" then return false end
        return tostring(a) < tostring(b)
    end)
    for _, k in ipairs(keys) do
        out[#out + 1] = encode_string(tostring(k)) .. ":" .. encode_value(t[k], depth + 1)
    end
    return "{" .. table.concat(out, ",") .. "}"
end

encode_value = function(v, depth)
    local ty = type(v)
    if ty == "string" then
        return encode_string(v)
    elseif ty == "number" then
        if math.type(v) == "integer" then return string.format("%d", v) end
        if v ~= v or v == math.huge or v == -math.huge then return "null" end
        if v == math.floor(v) and math.abs(v) < 2 ^ 53 then return string.format("%d", math.floor(v)) end
        return string.format("%.14g", v)
    elseif ty == "boolean" then
        return v and "true" or "false"
    elseif ty == "table" then
        return encode_table(v, depth)
    end
    return "null"
end

function sgl_json_encode(v)
    return encode_value(v, 0)
end

-- decoder: returns the value, or raises "json: ..." (callers pcall it)
local function utf8_char(cp)
    if cp < 0x80 then return string.char(cp) end
    if cp < 0x800 then return string.char(0xC0 | (cp >> 6), 0x80 | (cp & 0x3F)) end
    if cp < 0x10000 then
        return string.char(0xE0 | (cp >> 12), 0x80 | ((cp >> 6) & 0x3F), 0x80 | (cp & 0x3F))
    end
    return string.char(0xF0 | (cp >> 18), 0x80 | ((cp >> 12) & 0x3F), 0x80 | ((cp >> 6) & 0x3F), 0x80 | (cp & 0x3F))
end

local decode_value

local function skip_ws(s, i)
    return s:find("[^ \t\r\n]", i) or (#s + 1)
end

local function decode_string(s, i)
    -- s:sub(i, i) == '"'
    local out = {}
    local j = i + 1
    while true do
        local c = s:sub(j, j)
        if c == "" then error("json: unterminated string") end
        if c == '"' then return table.concat(out), j + 1 end
        if c == "\\" then
            local e = s:sub(j + 1, j + 1)
            local simple = ({ ['"'] = '"', ['\\'] = '\\', ['/'] = '/', b = '\b', f = '\f', n = '\n', r = '\r', t = '\t' })[e]
            if simple then
                out[#out + 1] = simple
                j = j + 2
            elseif e == "u" then
                local hex = s:sub(j + 2, j + 5)
                if not hex:match("^%x%x%x%x$") then error("json: bad \\u escape") end
                local cp = tonumber(hex, 16)
                j = j + 6
                if cp >= 0xD800 and cp <= 0xDBFF and s:sub(j, j + 1) == "\\u" then
                    local lo = tonumber(s:sub(j + 2, j + 5), 16)
                    if lo ~= nil and lo >= 0xDC00 and lo <= 0xDFFF then
                        cp = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00)
                        j = j + 6
                    end
                end
                out[#out + 1] = utf8_char(cp)
            else
                error("json: bad escape")
            end
        else
            local k = s:find('["\\]', j)
            if k == nil then error("json: unterminated string") end
            out[#out + 1] = s:sub(j, k - 1)
            j = k
        end
    end
end

local function decode_number(s, i)
    local num = s:match("^-?%d+%.?%d*[eE]?[-+]?%d*", i)
    if num == nil or num == "" or num == "-" then error("json: bad number") end
    local v = tonumber(num)
    if v == nil then error("json: bad number") end
    if math.type(v) == "float" and v == math.floor(v) and math.abs(v) < 2 ^ 53 then
        v = math.tointeger(v) or v
    end
    return v, i + #num
end

decode_value = function(s, i, depth)
    if depth > 32 then error("json: nesting too deep") end
    i = skip_ws(s, i)
    local c = s:sub(i, i)
    if c == "{" then
        local t = {}
        i = skip_ws(s, i + 1)
        if s:sub(i, i) == "}" then return t, i + 1 end
        while true do
            if s:sub(i, i) ~= '"' then error("json: object key expected") end
            local k
            k, i = decode_string(s, i)
            i = skip_ws(s, i)
            if s:sub(i, i) ~= ":" then error("json: ':' expected") end
            t[k], i = decode_value(s, i + 1, depth + 1)
            i = skip_ws(s, i)
            local d = s:sub(i, i)
            if d == "}" then return t, i + 1 end
            if d ~= "," then error("json: ',' or '}' expected") end
            i = skip_ws(s, i + 1)
        end
    elseif c == "[" then
        local t = {}
        i = skip_ws(s, i + 1)
        if s:sub(i, i) == "]" then return t, i + 1 end
        while true do
            t[#t + 1], i = decode_value(s, i, depth + 1)
            i = skip_ws(s, i)
            local d = s:sub(i, i)
            if d == "]" then return t, i + 1 end
            if d ~= "," then error("json: ',' or ']' expected") end
            i = i + 1
        end
    elseif c == '"' then
        return decode_string(s, i)
    elseif c == "-" or c:match("%d") then
        return decode_number(s, i)
    elseif s:sub(i, i + 3) == "true" then
        return true, i + 4
    elseif s:sub(i, i + 4) == "false" then
        return false, i + 5
    elseif s:sub(i, i + 3) == "null" then
        return nil, i + 4
    end
    error("json: unexpected '" .. c .. "' at " .. i)
end

function sgl_json_decode(s)
    if type(s) ~= "string" then error("json: not a string") end
    local v, i = decode_value(s, 1, 0)
    if skip_ws(s, i) <= #s then error("json: trailing data") end
    return v
end

---------------------------------------------------------------------------------------------
-- host detection
---------------------------------------------------------------------------------------------
local function headless_flag()
    local hs = gServerSettings.headlessServer
    return hs ~= nil and hs ~= 0 and hs ~= false
end

-- this process is the headless dedicated host (the one whose stdout the bridge reads)
function sgl_bridge_is_host()
    return network_is_server() and headless_flag()
end

-- local index of the host (global index 0) on a client connected to a headless host, else nil
local function host_local_index()
    if network_is_server() or not headless_flag() then return nil end
    local li = network_local_index_from_global(0)
    if li == nil or li <= 0 or li >= MAX_PLAYERS or not gNetworkPlayers[li].connected then return nil end
    return li
end

local function np_of_global(gi)
    if type(gi) ~= "number" then return nil end
    local li = network_local_index_from_global(gi)
    if li == nil or li < 0 or li >= MAX_PLAYERS then return nil end
    local np = gNetworkPlayers[li]
    if np == nil or not np.connected then return nil end
    return np, li
end

---------------------------------------------------------------------------------------------
-- events (game -> bridge)
---------------------------------------------------------------------------------------------
local function primitive(v)
    local ty = type(v)
    return ty == "string" or ty == "number" or ty == "boolean"
end

-- host only: print one SGLEVT line. Returns the line (nil when not the headless host).
local function print_event(t, fields)
    if not sgl_bridge_is_host() then return nil end
    local ev = {}
    for k, v in pairs(fields or {}) do ev[k] = v end
    ev.t = t
    local line = "SGLEVT " .. sgl_json_encode(ev)
    print(line)
    return line
end

-- any process: the host prints it, a client relays it to the headless host (gi + name filled in by
-- the host). Returns true when the event went somewhere, false offline / without a headless host.
function sglBridgeEmit(t, fields)
    if type(t) ~= "string" then return false end
    local ev = {}
    for k, v in pairs(fields or {}) do
        if primitive(v) and type(k) == "string" then ev[k] = v end
    end
    local me = gNetworkPlayers[0]
    if sgl_bridge_is_host() then
        if ev.gi == nil then ev.gi = me.globalIndex end
        if ev.name == nil then ev.name = me.name end
        return print_event(t, ev) ~= nil
    end
    local li = host_local_index()
    if li == nil then return false end
    ev.sgl = PKT_EVENT
    ev.t = t
    ev.gi = me.globalIndex
    network_send_to(li, true, ev)
    return true
end

local function on_event_packet(data)
    -- npc_ask must go through sgl_npc.lua's own validation (pending/truncation checks), not this generic relay.
    if data.t == "npc_ask" then return end
    if not sgl_bridge_is_host() or type(data.t) ~= "string" then return end
    local np = np_of_global(data.gi)
    if np == nil then return end
    local ev = {}
    for k, v in pairs(data) do ev[k] = v end
    ev.sgl, ev.t = nil, nil
    ev.name = np.name          -- the host's own view, not what the client claims
    print_event(data.t, ev)
end

-- join / leave (host hooks)
local sCharSeen = {}         -- [gi] = last friend index printed

local function on_player_connected(m)
    if not sgl_bridge_is_host() then return end
    local np = gNetworkPlayers[m.playerIndex]
    if np == nil or m.playerIndex == 0 then return end
    sCharSeen[np.globalIndex] = nil
    sglBridgeEmit("join", { gi = np.globalIndex, name = np.name })
end

local function on_player_disconnected(m)
    if not sgl_bridge_is_host() then return end
    local np = gNetworkPlayers[m.playerIndex]
    if np == nil or m.playerIndex == 0 then return end
    sCharSeen[np.globalIndex] = nil
    sglBridgeEmit("leave", { gi = np.globalIndex, name = np.name })
end

-- character picks: gPlayerSyncTable[i].friend (characters.lua), watched on the host
local function friend_id(index)
    local list = _G.sglFriends
    local f = (type(list) == "table" and index ~= 0) and list[index] or nil
    return (f ~= nil and f.id) or ""
end

local function watch_chars()
    for i = 1, MAX_PLAYERS - 1 do
        local np = gNetworkPlayers[i]
        if np.connected then
            local f = gPlayerSyncTable[i].friend
            if math.type(f) == "integer" and sCharSeen[np.globalIndex] ~= f then
                sCharSeen[np.globalIndex] = f
                sglBridgeEmit("char", { gi = np.globalIndex, name = np.name, friend = friend_id(f), index = f })
            end
        end
    end
end

-- race finishes (sgl_mission.lua race kind -> here, on the finishing client)
_G.sglOnRaceFinish = function(race, frames)
    local np = gNetworkPlayers[0]
    sglBridgeEmit("fin", { race = tostring(race), frames = frames, level = np.currLevelNum, act = np.currActNum })
end

---------------------------------------------------------------------------------------------
-- verified runs (spec 10.1): the host times every mission round itself and prints "run"
---------------------------------------------------------------------------------------------
-- The headless host is in no act, but it receives every mission's synced state: gGlobalSyncTable
-- writes and mod packets from a client go to the server first (packet.c processes them there, then
-- rebroadcasts; PLMT_NONE, no level match), so the host's own sync table holds "sglm_<level>_<area>_
-- <act>_s|r|a|f" for every instance and its HOOK_ON_PACKET_RECEIVE sees every mission event. Each
-- frame the host reads s (state) + r (round) of every registered mission and timestamps the changes
-- with its own monotonic clock (clock_elapsed_ticks(): 30 ticks per second of wall time):
--   * frames = the sum of the round's ACTIVE stretches (co-op pauses excluded) as the host saw them
--     arrive, from the round going active to ACTIVE -> SUCCESS (or ACTIVE -> DONE: a level star grabbed
--     before the leader saw the goal). Both edges come from the same leader, so its network delay
--     cancels out: the error is the delay JITTER of those two packets (plus a resend of a lost
--     reliable packet) and up to 1 host frame per edge.
--   * races (def.raceTiming, sgl_mission_kind_race): from the host seeing phase "a" go RACING (GO) to
--     the arrival of the winning "fin" event (the smallest time of that race); client_frames = that
--     fin's own frames. The finisher heard GO one downlink later and its fin took one uplink, so the
--     host time is the race time + about the finisher's round trip.
--   * client_frames (other kinds): every client in the act reports its own count of the round
--     (sgl_mission.lua round_clock, game frames) to the host with a reliable packet; the host waits
--     for every player in the act (at most SGL_RUN_REPORT_WAIT frames) and uses the longest count
--     among those who saw the whole round (in solo: the leader's own). Left out when nobody did.
--     Client counts are game frames: a client running below 30 fps counts fewer than the host.
--   * retries: rounds of that instance that FAILED since its last success (or since it was empty).
--   * players: the connected players in the instance (level + area + act) when the round succeeded,
--     with the host's view of their names. No "run" when the host did not see the round start (e.g.
--     it was already active when the mod loaded) or nobody is left in the act.
-- Exactly one "run" per mission + round. Fields (primitives only): mission, round, frames,
-- client_frames, retries, level, act, players, gi1, name1, gi2, name2, ...
SGL_RUN_REPORT_WAIT = 90             -- frames the host waits for the players' own counts (3 s)
SGL_RUN_MAX_PLAYERS = 16

local PKT_RUN = "br"                 -- client -> host: my own count of a round that succeeded
local MS_ACTIVE, MS_SUCCESS, MS_FAILED, MS_DONE = 3, 4, 5, 6   -- SGL_MS_* (sgl_mission.lua)
local RACE_RACING = 2                -- SGL_RACE_RACING (sgl_mission.lua)

local function host_ticks() return clock_elapsed_ticks() end

-- client (any act): sgl_mission.lua calls this when it sees a round succeed
_G.sglOnRoundSuccess = function(def, round, frames, full)
    if type(def) ~= "table" or type(def.id) ~= "string" or def.raceTiming then return end
    local li = host_local_index()
    if li == nil then return end
    network_send_to(li, true, { sgl = PKT_RUN, mi = def.id, r = math.floor(round), cf = math.floor(frames),
        full = full == true, gi = gNetworkPlayers[0].globalIndex })
end

local sRuns = {}             -- [mission id] = host watch state
local sPending = {}          -- runs waiting for the players' reports
local sHostFrame = 0

local function run_state(def)
    local st = sRuns[def.id]
    if st == nil then
        local function key(f)
            return "sglm_" .. def.level .. "_" .. def.area .. "_" .. def.act .. "_" .. f   -- sgl_mission_sync_key
        end
        st = { def = def, ks = key("s"), kr = key("r"), ka = key("a"), kf = key("f"),
            ik = def.level .. ":" .. def.area .. ":" .. def.act,                         -- sgl_instance_key
            s = nil, r = nil, valid = false, acc = 0, since = nil, retries = 0, done = {},
            goAt = nil, goRace = nil, lastA = nil, fins = {}, reports = {} }
        sRuns[def.id] = st
    end
    return st
end

local function sync_int(k)
    local v = gGlobalSyncTable[k]
    if type(v) ~= "number" then return 0 end
    return math.floor(v)
end

-- connected players in the mission's instance (host view), sorted by global index
local function instance_players(def)
    local out = {}
    for i = 1, MAX_PLAYERS - 1 do
        local np = gNetworkPlayers[i]
        if np ~= nil and np.connected and np.currLevelNum == def.level and np.currAreaIndex == def.area
            and np.currActNum == def.act then
            out[#out + 1] = { gi = np.globalIndex, name = np.name }
        end
    end
    table.sort(out, function(a, b) return a.gi < b.gi end)
    return out
end

local function emit_run(p)
    local ev = { mission = p.def.id, round = p.r, frames = p.frames, retries = p.retries,
        level = p.def.level, act = p.def.act, players = #p.players }
    local best = p.clientFrames
    if best == nil then
        for _, pl in ipairs(p.players) do
            local rep = p.reports[pl.gi]
            if rep ~= nil and rep.full and (best == nil or rep.cf > best) then best = rep.cf end
        end
    end
    ev.client_frames = best
    for i, pl in ipairs(p.players) do
        if i > SGL_RUN_MAX_PLAYERS then break end
        ev["gi" .. i] = pl.gi
        ev["name" .. i] = pl.name
    end
    print_event("run", ev)
end

local function round_succeeded(st)
    local def = st.def
    if not st.valid or st.done[st.r] then return end
    st.done[st.r] = true
    local players = instance_players(def)
    local retries = st.retries
    st.retries = 0
    if #players == 0 then return end
    local p = { def = def, r = st.r, retries = retries, players = players, at = sHostFrame }
    if def.raceTiming then
        local win = nil
        for _, f in ipairs(st.fins[st.goRace or -1] or {}) do
            if win == nil or f.fr < win.fr then win = f end
        end
        if win == nil or st.goAt == nil then
            log_to_console("[SGL] run " .. def.id .. " round " .. st.r .. ": no GO / finish seen on the host, not reported",
                CONSOLE_MESSAGE_WARNING)
            return
        end
        p.frames = math.max(1, win.at - st.goAt)
        p.clientFrames = win.fr
        emit_run(p)
        return
    end
    p.frames = math.max(1, st.acc)
    st.reports[st.r] = st.reports[st.r] or {}
    p.reports = st.reports[st.r]
    sPending[#sPending + 1] = p
end

local function watch_mission(def, now)
    local st = run_state(def)
    local s, r = sync_int(st.ks), sync_int(st.kr)
    if r ~= st.r then
        -- a new round (or the first look): timed only when it has not gone active yet
        st.r, st.s, st.acc, st.since = r, s, 0, nil
        st.valid = s ~= MS_ACTIVE and s ~= MS_SUCCESS and s ~= MS_DONE
        st.goAt, st.goRace, st.lastA, st.fins = nil, nil, nil, {}
        for k in pairs(st.reports) do
            if k < r - 1 then st.reports[k] = nil end
        end
        return
    end
    local old = st.s
    if s ~= old then
        st.s = s
        if old == MS_ACTIVE and st.since ~= nil then
            st.acc = st.acc + math.max(0, now - st.since)
            st.since = nil
        end
        if s == MS_ACTIVE then st.since = now end
        if old == MS_ACTIVE and s == MS_FAILED then st.retries = st.retries + 1 end
        if old == MS_ACTIVE and (s == MS_SUCCESS or s == MS_DONE) then round_succeeded(st) end
    end
    if def.raceTiming and s == MS_ACTIVE then
        local a, f = sync_int(st.ka), sync_int(st.kf)
        if a == RACE_RACING and (st.lastA ~= RACE_RACING or st.goRace ~= f) then
            st.goAt, st.goRace = now, f
        end
        st.lastA = a
    end
    -- the instance emptied (checked once a second): the next group starts from zero retries
    if st.retries > 0 and sHostFrame % 30 == 0 and #instance_players(def) == 0 then st.retries = 0 end
end

local function watch_runs()
    local list = rawget(_ENV, "SGL_MISSION_LIST")   -- sgl_mission.lua (this mod's _ENV, not _G)
    if type(list) ~= "table" then return end
    sHostFrame = sHostFrame + 1
    local now = host_ticks()
    for _, def in ipairs(list) do watch_mission(def, now) end
    local keep = {}
    for _, p in ipairs(sPending) do
        local all = true
        for _, pl in ipairs(p.players) do
            if p.reports[pl.gi] == nil then all = false end
        end
        if all or sHostFrame - p.at >= SGL_RUN_REPORT_WAIT then
            emit_run(p)
        else
            keep[#keep + 1] = p
        end
    end
    sPending = keep
end

-- host: a client's own count of a round (PKT_RUN)
local function on_run_packet(data)
    if not sgl_bridge_is_host() or type(data.mi) ~= "string" or math.type(data.r) ~= "integer"
        or math.type(data.cf) ~= "integer" then return end
    local st = sRuns[data.mi]
    if np_of_global(data.gi) == nil or st == nil then return end
    st.reports[data.r] = st.reports[data.r] or {}
    if st.reports[data.r][data.gi] == nil then
        st.reports[data.r][data.gi] = { cf = math.max(0, data.cf), full = data.full == true }
    end
end

-- host: race finishes ("fin" mission events, sgl_mission.lua race kind) as they arrive
local function on_mission_packet(data)
    if not sgl_bridge_is_host() or data.ev ~= "fin" or type(data.ik) ~= "string" then return end
    if math.type(data.race) ~= "integer" or type(data.fr) ~= "number" then return end
    for _, st in pairs(sRuns) do
        if st.ik == data.ik and st.def.raceTiming and data.r == st.r and np_of_global(data.gi) ~= nil then
            local list = st.fins[data.race] or {}
            st.fins[data.race] = list
            for _, f in ipairs(list) do
                if f.gi == data.gi then return end
            end
            list[#list + 1] = { gi = data.gi, fr = math.floor(data.fr), at = host_ticks() }
            return
        end
    end
end

---------------------------------------------------------------------------------------------
-- commands (bridge -> game)
---------------------------------------------------------------------------------------------
local sHandlers = {}         -- [name] = { fn, ... }
local sLastSeq = 0

-- register fn(fields) for an inbox command (runs on the client(s) the command is routed to)
function sglBridgeOnCommand(name, fn)
    if type(name) ~= "string" or type(fn) ~= "function" then return false end
    sHandlers[name] = sHandlers[name] or {}
    table.insert(sHandlers[name], fn)
    return true
end

local function run_handlers(name, fields)
    local list = sHandlers[name]
    if list == nil then return 0 end
    for _, fn in ipairs(list) do fn(fields) end
    return #list
end

local function flat_fields(cmd)
    local fields = {}
    for k, v in pairs(cmd) do
        if type(k) == "string" and primitive(v) and k ~= "t" and k ~= "seq" then fields[k] = v end
    end
    return fields
end

-- host: deliver one decoded inbox command to where it belongs
local function route_command(cmd)
    local name = cmd.t
    if type(name) ~= "string" then return end
    local fields = flat_fields(cmd)
    local pkt = { sgl = PKT_CMD, [CMD_KEY] = name }
    for k, v in pairs(fields) do
        -- Empty optional fields cannot be serialized by coopdx (for example a blank nickname).
        if k ~= "sgl" and k ~= CMD_KEY and v ~= "" then pkt[k] = v end
    end
    if SGL_BRIDGE_BROADCAST[name] or type(fields.gi) ~= "number" then
        network_send(true, pkt)
        run_handlers(name, fields)
        return
    end
    local np, li = np_of_global(fields.gi)
    if np == nil then return end
    if li == 0 then
        run_handlers(name, fields)
    else
        network_send_to(li, true, pkt)
    end
end

-- host: run the new commands of an inbox document (text). Returns how many ran.
function sgl_bridge_process_inbox(text)
    local ok, doc = pcall(sgl_json_decode, text)
    if not ok or type(doc) ~= "table" or type(doc.cmds) ~= "table" then return 0 end
    if math.type(doc.seq) == "integer" and doc.seq < sLastSeq then sLastSeq = 0 end
    local fresh = {}
    for _, cmd in ipairs(doc.cmds) do
        if type(cmd) == "table" and math.type(cmd.seq) == "integer" and cmd.seq > sLastSeq then
            fresh[#fresh + 1] = cmd
        end
    end
    table.sort(fresh, function(a, b) return a.seq < b.seq end)
    for _, cmd in ipairs(fresh) do
        sLastSeq = cmd.seq
        route_command(cmd)
    end
    return #fresh
end

function sgl_bridge_last_seq() return sLastSeq end

-- host: reload the modfs and read inbox.json (nil when missing / empty / unreadable; no console errors)
local function read_inbox()
    mod_fs_hide_errors(true)
    local text = nil
    local fs = mod_fs_reload()
    if fs ~= nil then
        local f = mod_fs_get_file(fs, SGL_BRIDGE_INBOX_FILE)
        if f ~= nil and f.size > 0 then
            mod_fs_file_rewind(f)
            text = mod_fs_file_read_string(f)
        end
    end
    mod_fs_hide_errors(false)
    return text
end

local function on_command_packet(data)
    local name = data[CMD_KEY]
    if type(name) ~= "string" then return end
    local fields = {}
    for k, v in pairs(data) do
        if k ~= "sgl" and k ~= CMD_KEY then fields[k] = v end
    end
    run_handlers(name, fields)
end

local function on_packet_receive(data)
    if data.sgl == PKT_EVENT then
        on_event_packet(data)
    elseif data.sgl == PKT_CMD then
        on_command_packet(data)
    elseif data.sgl == PKT_RUN then
        on_run_packet(data)
    elseif data.sgl == "m" then
        on_mission_packet(data)
    end
end

-- built-in: announce {text, secs}
sglBridgeOnCommand("announce", function(f)
    if type(f.text) ~= "string" or f.text == "" then return end
    local lines = math.max(1, math.min(4, (#f.text + 39) // 40))
    djui_popup_create("\\#ffd700\\" .. f.text, lines)
    djui_chat_message_create("\\#ffd700\\" .. f.text)
end)

---------------------------------------------------------------------------------------------
-- host loop
---------------------------------------------------------------------------------------------
local sFrame = 0
local sHelloSent = false

local function bridge_update()
    if not sgl_bridge_is_host() then return end
    sFrame = sFrame + 1
    if not sHelloSent then
        sHelloSent = true
        sglBridgeEmit("hello", { version = SGL_BRIDGE_VERSION, proto = SGL_BRIDGE_PROTO })
    end
    watch_runs()
    if sFrame % SGL_BRIDGE_CHAR_FRAMES == 0 then watch_chars() end
    if sFrame % SGL_BRIDGE_POLL_FRAMES == 0 then
        local text = read_inbox()
        if text ~= nil then sgl_bridge_process_inbox(text) end
    end
end

hook_event(HOOK_UPDATE, bridge_update)
hook_event(HOOK_ON_PLAYER_CONNECTED, on_player_connected)
hook_event(HOOK_ON_PLAYER_DISCONNECTED, on_player_disconnected)
hook_event(HOOK_ON_PACKET_RECEIVE, on_packet_receive)
