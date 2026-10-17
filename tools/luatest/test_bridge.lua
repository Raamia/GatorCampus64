-- Tests for mods/sgl64/sgl_bridge.lua: the JSON encoder / decoder, SGLEVT events (host prints, client
-- relay), inbox sequencing + routing, and that everything is inert without a headless host.
-- Run: tools/luatest/run.sh   (or: lua tools/luatest/test_bridge.lua)
local HERE = debug.getinfo(1, "S").source:match("^@(.*/)") or "./"
local Sim = dofile(HERE .. "sim.lua")
local C = Sim.C

local passed, failed = 0, 0
local current = "?"

local function check(cond, what)
    if cond then
        passed = passed + 1
    else
        failed = failed + 1
        print("  FAIL [" .. current .. "] " .. what)
    end
    return cond
end

local function test(name, fn)
    current = name
    local before = failed
    local ok, err = xpcall(fn, debug.traceback)
    if not ok then
        failed = failed + 1
        print("  ERROR [" .. name .. "] " .. tostring(err))
    end
    print((failed == before and "PASS " or "FAIL ") .. name)
end

local FILES = { "characters.lua", "sgl_bridge.lua" }

-- a fake modfs for the host: c.inbox = text (nil = no modfs file at all)
local function install_modfs(c)
    c.prints, c.reloads = {}, 0
    c.stubs.print = function(s) table.insert(c.prints, s) end
    c.stubs.mod_fs_hide_errors = function(h) assert(type(h) == "boolean") end
    c.stubs.mod_fs_reload = function()
        c.reloads = c.reloads + 1
        if c.inbox == nil then return nil end
        return { files = { ["inbox.json"] = { size = #c.inbox, data = c.inbox } } }
    end
    c.stubs.mod_fs_get_file = function(fs, name) return fs.files[name] end
    c.stubs.mod_fs_file_rewind = function(f) return true end
    c.stubs.mod_fs_file_read_string = function(f)
        assert(f.size > 0, "read_string on an empty file raises a modfs error")
        return f.data
    end
end

-- host H (gi 0) + clients A (1), B (2); headless = the host runs with --headless
local function world(headless)
    local w = Sim.new({ files = FILES, levelScripts = false })
    local H, A, B = w:connect("Campus"), w:connect("A"), w:connect("B")
    for _, c in ipairs({ H, A, B }) do
        install_modfs(c)
        if headless then c.stubs.gServerSettings.headlessServer = 1 end
    end
    w:step(3)
    return w, H, A, B
end

local function events(c)
    local out = {}
    for _, line in ipairs(c.prints) do
        local json = line:match("^SGLEVT (.*)$")
        if json then table.insert(out, c.env.sgl_json_decode(json)) end
    end
    return out
end

local function find_event(c, t)
    for _, e in ipairs(events(c)) do
        if e.t == t then return e end
    end
    return nil
end

---------------------------------------------------------------------------------------------
-- JSON
---------------------------------------------------------------------------------------------
local _, H0 = world(false)
local enc, dec = H0.env.sgl_json_encode, H0.env.sgl_json_decode

test("json: encoder escapes, key order (t first), numbers, nesting", function()
    check(enc("a\"b\\c\nd\te\1") == '"a\\"b\\\\c\\nd\\te\\u0001"', "string escapes: " .. enc("a\"b\\c\nd\te\1"))
    check(enc({ t = "join", name = "x", gi = 3 }) == '{"t":"join","gi":3,"name":"x"}', "t first, rest sorted")
    check(enc({ 1, 2, "x" }) == '[1,2,"x"]', "array")
    check(enc({ a = { b = { true, false } } }) == '{"a":{"b":[true,false]}}', "nested")
    check(enc(1.5) == "1.5" and enc(42) == "42" and enc(3.0) == "3", "numbers")
    check(enc(0 / 0) == "null" and enc(math.huge) == "null", "nan / inf -> null")
    check(enc({}) == "{}", "empty table -> {}")
    check(enc("caf\xc3\xa9") == '"caf\xc3\xa9"', "utf-8 passes through")
end)

test("json: decoder round trip, escapes, unicode, integers stay integers", function()
    local doc = { seq = 7, cmds = { { seq = 7, t = "announce", text = "Hi \"there\"\n", secs = 5, ok = true } } }
    local back = dec(enc(doc))
    check(back.seq == 7 and math.type(back.seq) == "integer", "integer seq")
    check(back.cmds[1].text == "Hi \"there\"\n" and back.cmds[1].ok == true, "string + bool")
    check(dec('"\\u00e9\\u2713\\ud83d\\ude00"') == "\xc3\xa9\xe2\x9c\x93\xf0\x9f\x98\x80", "\\u escapes incl. surrogate pair")
    check(dec(' { "a" : [ 1 , -2.5e1 , null , "x" ] } ').a[2] == -25.0, "whitespace + exponent")
    check(math.type(dec("1e3")) == "integer" and dec("1e3") == 1000, "integral floats -> integers")
    check(dec("[]")[1] == nil and next(dec("{}")) == nil, "empty containers")
    for _, bad in ipairs({ "", "{", '{"a"}', "[1,]", '"abc', "tru", "{} x", '{"a":1,}', "\"\\x\"" }) do
        check(not pcall(dec, bad), "rejects " .. bad)
    end
end)

---------------------------------------------------------------------------------------------
-- inert without a headless host
---------------------------------------------------------------------------------------------
test("inert: no headless host -> no prints, no modfs reads, no packets", function()
    local w, H, A, B = world(false)
    H.inbox = enc({ seq = 1, cmds = { { seq = 1, t = "announce", text = "boo" } } })
    local handled = 0
    A.env.sglBridgeOnCommand("login_code", function() handled = handled + 1 end)
    w:step(120)
    check(#H.prints == 0 and #A.prints == 0, "nothing printed")
    check(H.reloads == 0 and A.reloads == 0, "mod_fs_reload never called")
    check(A.env.sglBridgeSend("login_req", {}) == false, "client send refused")
    check(H.env.sglBridgeSend("login_req", {}) == false, "non-headless host send refused")
    A.env._G.sglOnRaceFinish("sgl_pb_x", 100)
    w:step(2)
    check(#H.prints == 0 and #H.popups == 0 and #A.popups == 0, "still nothing")
    Sim.run_hooks(H, C.HOOK_ON_PLAYER_CONNECTED, H.ms[1])
    w:disconnect(B)
    check(#H.prints == 0, "join / leave silent")
end)

test("inert: offline single player (no server, no host) is silent", function()
    local w = Sim.new({ files = FILES, levelScripts = false })
    local S = w:connect("Solo", { gi = 5 })     -- not the server (gi ~= 0) and nobody else
    install_modfs(S)
    S.stubs.gServerSettings.headlessServer = 0
    w:step(60)
    check(S.env.sglBridgeSend("login_req", {}) == false and #S.prints == 0 and S.reloads == 0, "silent")
end)

---------------------------------------------------------------------------------------------
-- events
---------------------------------------------------------------------------------------------
test("events: hello once, join / leave from the host hooks", function()
    local w, H, A, B = world(true)
    local hellos = 0
    for _, e in ipairs(events(H)) do if e.t == "hello" then hellos = hellos + 1 end end
    check(hellos == 1, "one hello")
    local hello = find_event(H, "hello")
    check(hello and hello.v == "sgl64-web-1" and hello.proto == 1, "hello fields")
    check(H.prints[1]:match('^SGLEVT {"t":"hello",') ~= nil, "line format: " .. tostring(H.prints[1]))
    Sim.run_hooks(H, C.HOOK_ON_PLAYER_CONNECTED, H.ms[Sim.raw(H.nps[1]).localIndex])
    local j = find_event(H, "join")
    check(j and j.gi == 1 and j.name == "A", "join gi + name")
    w:disconnect(B)
    local l = find_event(H, "leave")
    check(l and l.gi == 2 and l.name == "B", "leave gi + name")
    check(#A.prints == 0 and #B.prints == 0, "clients never print")
end)

test("events: char changes watched on the host (friend index + id)", function()
    local w, H, A = world(true)
    local li = H.env.network_local_index_from_global(1)
    H.stubs.gPlayerSyncTable[li].friend = 0
    w:step(20)
    local e = find_event(H, "char")
    check(e and e.gi == 1 and e.friend == 0 and e.id == "", "initial pick printed")
    H.prints = {}
    w:step(20)
    check(find_event(H, "char") == nil, "no repeat without a change")
    H.stubs.gPlayerSyncTable[li].friend = 2
    w:step(20)
    e = find_event(H, "char")
    check(e and e.friend == 2 and e.id == "corina" and e.name == "A", "change printed with the friend id")
end)

test("events: client relay (login_req, link_req, fin) with the host's view of the name", function()
    local w, H, A = world(true)
    H.prints = {}
    check(A.env.sglBridgeSend("login_req", { name = "spoofed", gi = 9 }) == true, "client send accepted")
    A.env.sglBridgeSend("link_req", { code = "K7Q2XF", junk = { 1 } })
    A.env._G.sglOnRaceFinish("sgl_pb_swamp_race", 1234)
    check(#H.prints == 0, "printed only after the packet arrives")
    w:step(1)
    local lr = find_event(H, "login_req")
    check(lr and lr.gi == 1 and lr.name == "A", "login_req: gi + name from the host")
    local lk = find_event(H, "link_req")
    check(lk and lk.code == "K7Q2XF" and lk.junk == nil and lk.sgl == nil, "link_req: code, tables dropped, no packet tag")
    local fin = find_event(H, "fin")
    check(fin and fin.race == "sgl_pb_swamp_race" and fin.frames == 1234 and fin.gi == 1 and fin.level ~= nil, "fin")
    check(#A.prints == 0, "the client printed nothing")
end)

---------------------------------------------------------------------------------------------
-- inbox
---------------------------------------------------------------------------------------------
local function record(c, name)
    local got = {}
    c.env.sglBridgeOnCommand(name, function(f) table.insert(got, f) end)
    return got
end

test("inbox: sequencing (new seqs only, in order, counter reset when the bridge restarts)", function()
    local w, H = world(true)
    local got = record(H, "probe")
    local P = H.env.sgl_bridge_process_inbox
    local function doc(top, seqs)
        local cmds = {}
        for _, s in ipairs(seqs) do table.insert(cmds, { seq = s, t = "probe", n = s }) end
        return enc({ seq = top, cmds = cmds })
    end
    check(P(doc(2, { 2, 1 })) == 2 and got[1].n == 1 and got[2].n == 2, "both run, in seq order")
    check(P(doc(2, { 2, 1 })) == 0, "same inbox again: nothing")
    check(P(doc(3, { 1, 2, 3 })) == 1 and got[3].n == 3, "only the new one")
    check(H.env.sgl_bridge_last_seq() == 3, "last seq")
    check(P(doc(1, { 1 })) == 1 and got[4].n == 1, "lower top seq (bridge restarted): counter reset")
    check(P("not json") == 0 and P('{"cmds":"x"}') == 0 and P('{"seq":5}') == 0, "garbage ignored")
    check(P(enc({ seq = 9, cmds = { { t = "probe" }, { seq = "9", t = "probe" }, 5 } })) == 0, "commands without integer seq ignored")
    check(got[1].seq == nil and got[1].t == nil, "handlers get the fields only")
end)

test("inbox: polled through mod_fs_reload every 30 frames; missing / empty files are fine", function()
    local w, H = world(true)
    local got = record(H, "probe")
    local r0 = H.reloads
    w:step(30)
    check(H.reloads - r0 == 1, "one reload per 30 frames")
    H.inbox = ""
    w:step(30)
    H.inbox = enc({ seq = 1, cmds = { { seq = 1, t = "probe" } } })
    w:step(30)
    check(#got == 1, "picked up")
    w:step(90)
    check(#got == 1, "not re-run")
end)

test("inbox: routing (targeted to one client, verified / announce broadcast)", function()
    local w, H, A, B = world(true)
    local codeA, codeB, codeH = record(A, "login_code"), record(B, "login_code"), record(H, "login_code")
    local verA, verB, verH = record(A, "verified"), record(B, "verified"), record(H, "verified")
    local failB = record(B, "login_failed")
    H.inbox = enc({ seq = 3, cmds = {
        { seq = 1, t = "login_code", gi = 1, user_code = "ABCD-EFGH", uri = "https://login.x/activate?user_code=ABCD-EFGH", expires = 900 },
        { seq = 2, t = "verified", gi = 1, nickname = "Albert", guest_slot = 3 },
        { seq = 3, t = "login_failed", gi = 2, reason = "expired" },
    } })
    w:step(31)
    check(#codeA == 1 and #codeB == 0 and #codeH == 0, "login_code only to gi 1")
    check(codeA[1] and codeA[1].user_code == "ABCD-EFGH" and codeA[1].expires == 900 and codeA[1].gi == 1, "login_code fields")
    check(codeA[1] and codeA[1].sgl == nil and codeA[1].bc_t == nil, "no packet tags in the fields")
    check(#verA == 1 and #verB == 1 and #verH == 1, "verified broadcast (host too)")
    check(verB[1] and verB[1].nickname == "Albert" and verB[1].guest_slot == 3, "verified fields")
    check(#failB == 1 and failB[1].reason == "expired", "login_failed to gi 2")
    H.inbox = enc({ seq = 4, cmds = { { seq = 4, t = "announce", text = "New gator Albert arrives in 60 s", secs = 10 } } })
    w:step(31)
    check(Sim.find(A.popups, "New gator Albert") and Sim.find(B.popups, "New gator Albert") and Sim.find(H.popups, "New gator"), "announce popup everywhere")
    check(Sim.find(A.chat, "New gator Albert") ~= nil, "announce chat line")
    H.inbox = enc({ seq = 5, cmds = { { seq = 5, t = "login_code", gi = 7, user_code = "X" } } })
    w:step(31)
    check(#codeA == 1 and #codeB == 0, "unknown gi: dropped")
end)

print(string.format("\n%d checks passed, %d failed", passed, failed))
if failed > 0 then os.exit(1) end
