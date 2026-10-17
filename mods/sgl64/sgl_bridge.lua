-- Super Gatorlator 64: bridge between the hosted game and server/bridge (docs/web_platform_spec.md 6.2-6.4).
--
-- Only does anything on a HEADLESS dedicated host (sm64coopdx --headless --server ...), and on the
-- clients connected to one (gServerSettings.headlessServer is sent to joiners in the join packet).
-- Offline, on a normal (non-headless) host or on its clients, nothing prints and the inbox is never read.
--
-- Game -> bridge (events): the host prints one line per event to stdout:
--     SGLEVT {"t":"join","gi":3,"name":"Alberta"}
--   "t" first, then the other keys sorted; strings escaped (\" \\ \n \r \t \uXXXX for other control
--   bytes; non-ASCII bytes pass through as-is). Events: hello {v, proto}; join / leave {gi, name};
--   char {gi, name, friend (index, 0 = none), id (friend id or "")}; fin {gi, name, race (the race's
--   pbKey), frames, level, act}; login_req {gi, name}; link_req {gi, name, code}. Clients relay their
--   events to the host with a packet (sgl = "be"); the host takes `name` from its own player list.
--   sglBridgeSend(t, fields) is the call for other files (sgl_login.lua: "login_req", "link_req").
--
-- Bridge -> game (inbox): server/bridge writes <savepath>/sav/sgl64.modfs (a zip, coopdx mod_fs
-- format) holding inbox.json: {"seq": N, "cmds": [{"seq": n, "t": "<command>", ...fields}, ...]}.
-- The host calls mod_fs_reload() every 30 frames and runs each command whose seq is higher than the
-- last one it ran (in seq order). If the file's top-level seq goes BELOW the last one handled (the
-- bridge restarted its counter), the counter resets. Routing (host):
--   * "verified" and "announce" (SGL_BRIDGE_BROADCAST), or any command without a numeric gi:
--     network_send(true, ...) to every client + run on the host too;
--   * otherwise (login_code, login_failed, ...): network_send_to the player with global index gi only.
-- Clients run the command handlers registered with sglBridgeOnCommand(name, fn); fn(fields) gets the
-- command's fields (primitives only: packets cannot carry tables). "announce" {text, secs} is built in
-- (a popup + a chat line for everyone; secs is advisory: coopdx popups have a fixed duration).
--
-- Race finishes: sgl_mission.lua's race kind calls _G.sglOnRaceFinish(pbKey, frames) on the finishing
-- client (the only hook into the mission code).

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
function sglBridgeEmit(t, fields)
    if not sgl_bridge_is_host() then return nil end
    local ev = {}
    for k, v in pairs(fields or {}) do ev[k] = v end
    ev.t = t
    local line = "SGLEVT " .. sgl_json_encode(ev)
    print(line)
    return line
end

-- any process: the host prints it, a client relays it to the headless host (gi + name filled in)
function sglBridgeSend(t, fields)
    if type(t) ~= "string" then return false end
    local ev = {}
    for k, v in pairs(fields or {}) do
        if primitive(v) and type(k) == "string" then ev[k] = v end
    end
    local me = gNetworkPlayers[0]
    if sgl_bridge_is_host() then
        if ev.gi == nil then ev.gi = me.globalIndex end
        if ev.name == nil then ev.name = me.name end
        return sglBridgeEmit(t, ev) ~= nil
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
    if not sgl_bridge_is_host() or type(data.t) ~= "string" then return end
    local np = np_of_global(data.gi)
    if np == nil then return end
    local ev = {}
    for k, v in pairs(data) do ev[k] = v end
    ev.sgl, ev.t = nil, nil
    ev.name = np.name          -- the host's own view, not what the client claims
    sglBridgeEmit(data.t, ev)
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
                sglBridgeEmit("char", { gi = np.globalIndex, name = np.name, friend = f, id = friend_id(f) })
            end
        end
    end
end

-- race finishes (sgl_mission.lua race kind -> here, on the finishing client)
_G.sglOnRaceFinish = function(race, frames)
    local np = gNetworkPlayers[0]
    sglBridgeSend("fin", { race = tostring(race), frames = frames, level = np.currLevelNum, act = np.currActNum })
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
        if k ~= "sgl" and k ~= CMD_KEY then pkt[k] = v end
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
        sglBridgeEmit("hello", { v = SGL_BRIDGE_VERSION, proto = SGL_BRIDGE_PROTO })
    end
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
