-- Offline test of mods/sgl64/sgl_npc.lua (Albert and Alberta, the roaming mascots) in the multi-client simulator:
-- they appear only in the level of their current spot, a line near one becomes a request in the host's modfs
-- outbox (npc_out.txt, with the asker's own live stats, sent by the asker's client), /albert and /alberta ask from
-- anywhere, the bridge's reply file (sgl64_npc.modfs replies.txt) reaches every client as a chat line + bubble,
-- the host moves them along their routes (synced step, poofs) but never mid-conversation, their animations follow
-- what they're doing, with no bridge a request times out, and on a headless host (play.gatorcamp.us) requests go
-- out as npc_ask events for server/bridge instead. Run: lua tools/luatest/test_npc.lua (run.sh).
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

local HUB = C.LEVEL_CASTLE_GROUNDS

-- an in-memory modfs: own = the mod's file system (sgl64.modfs), inbox[path] = text of a public file
local function fake_modfs(c)
    local disk = { own = nil, inbox = {} }
    local function new_file(text)
        local f = { data = text or "", offset = 0 }
        f.size = #f.data
        function f.rewind(self) self.offset = 0 return true end
        function f.erase(self, n)
            self.data = self.data:sub(1, self.offset) .. self.data:sub(self.offset + n + 1)
            self.size = #self.data
            return true
        end
        function f.write_string(self, s)
            self.data = self.data:sub(1, self.offset) .. s .. self.data:sub(self.offset + #s + 1)
            self.offset = self.offset + #s
            self.size = #self.data
            return true
        end
        function f.is_eof(self) return self.offset >= #self.data end
        function f.read_line(self)
            if self:is_eof() then return nil end
            local nl = self.data:find("\n", self.offset + 1, true) or (#self.data + 1)
            local line = self.data:sub(self.offset + 1, nl - 1)
            self.offset = nl
            return line
        end
        return f
    end
    local function new_fs(files)
        local fs = { files = files, saves = 0 }
        function fs.get_file(self, name) return self.files[name] end
        function fs.create_file(self, name, text)
            assert(text == true, "create_file(name, true): a text file")
            self.files[name] = new_file("")
            return self.files[name]
        end
        function fs.save(self) self.saves = self.saves + 1 return true end
        return fs
    end
    c.stubs.mod_fs_hide_errors = function(b) assert(type(b) == "boolean") end
    c.stubs.mod_fs_get = function(path)
        assert(path == nil, "mod_fs_get(): the mod's own modfs")
        return disk.own
    end
    c.stubs.mod_fs_create = function()
        assert(disk.own == nil, "mod_fs_create() only once")
        disk.own = new_fs({})
        return disk.own
    end
    c.stubs.mod_fs_reload = function(path)
        local text = disk.inbox[path]
        if text == nil then return nil end
        return new_fs({ ["replies.txt"] = new_file(text) })
    end
    return disk
end

local function outbox(disk)
    local f = disk.own and disk.own.files["npc_out.txt"]
    return f and f.data or ""
end

-- a world with a host and a friend on the hub; clock = { t = seconds } drives get_time() on both
local function setup()
    local w = Sim.new({ files = Sim.ALL_FILES, built = Sim.built_on_disk() })
    local H = w:connect("Host")
    local F = w:connect("Friend")
    local clock = { t = 1000 }
    for _, c in ipairs({ H, F }) do
        c.stubs.save_file_get_course_star_count = function(file, course)
            assert(math.type(file) == "integer" and math.type(course) == "integer")
            return course == C.COURSE_BOB - 1 and 2 or 0
        end
        c.stubs.get_time = function() return clock.t end
    end
    local disk = fake_modfs(H)
    w:warp(H, HUB, 1, 0)
    w:warp(F, HUB, 1, 0)
    w:step(60)
    return w, H, F, disk, clock
end

local function npc(c, id) return c.env.sgl_npc_by_id(id) end
local function spot_of(c, id) return c.env.sgl_npc_spot(npc(c, id)) end
local function objects(c) return Sim.objects_with(c, c.env.id_bhvSglNpc) end
local function anim_of(o) return o ~= nil and Sim.raw(o)._customAnim or nil end

-- stand a client next to a mascot's current spot (dx: how far east)
local function next_to(c, id, dx)
    local s = spot_of(c, id)
    c.pos.x, c.pos.y, c.pos.z = s.x + (dx or 150), s.y, s.z
end

-- a chat line typed by client `by` (the hook runs on every client; only the speaker's own client acts on it)
local function say(w, by, msg)
    for _, c in ipairs(w.clients) do
        local sender = (c == by) and c.ms[0] or c.ms[1]
        for _, fn in ipairs(c.hooks[C.HOOK_ON_CHAT_MESSAGE] or {}) do fn(sender, msg) end
    end
    w:step(2)
end

local function reply(w, disk, seq, id, text)
    local session = outbox(disk):match("^session\t([^\n]+)\n")
    disk.inbox["sgl64_npc"] = "session\t" .. session .. "\n" .. seq .. "\t" .. id .. "\t" .. text .. "\n"
    w:step(20)
end

test("two mascots with rigged models; at the start Albert is on the hub and Alberta in Marston", function()
    local w, H, F = setup()
    local ids = {}
    for _, n in ipairs(H.env.SGL_NPCS) do
        table.insert(ids, n.id)
        check(n.rig == true, n.id .. ": rigged model")
    end
    check(table.concat(ids, ",") == "albert,alberta", "the cast is Albert and Alberta: " .. table.concat(ids, ","))
    local count = 0
    for name, a in pairs(H.customAnims) do
        count = count + 1
        check(#a.index == 2 * (3 + 3 * #H.env.ALBERT_JOINTS), name .. ": one index entry per channel")
    end
    check(count == 6, "six shared animations registered: " .. count)
    check(spot_of(H, "albert").level == HUB and spot_of(H, "alberta").level == C.LEVEL_CCM, "step 0 spots")
    local objs = objects(H)
    check(#objs == 1 and Sim.raw(objs[1])._model == npc(H, "albert").model, "only Albert stands on the hub")
    check(H.commands.albert ~= nil and H.commands.alberta ~= nil, "/albert and /alberta registered")
end)

test("the host's own line near Albert -> outbox request with live stats and where both mascots are", function()
    local w, H, F, disk = setup()
    next_to(H, "albert")
    w:step(2)
    say(w, H, "how many stars do i have")
    local text = outbox(disk)
    check(text:match("^session\t[^\n]+\n") ~= nil, "outbox starts with the session line")
    local seq, id, player, msg, stats = text:match("\n(%d+)\t([^\t]+)\t([^\t]+)\t([^\t]+)\t([^\n]*)\n")
    check(seq == "1" and id == "albert" and player == H.nps[0].name and msg == "how many stars do i have",
        "request line: " .. tostring(seq) .. " " .. tostring(id) .. " " .. tostring(player) .. " " .. tostring(msg))
    stats = stats or ""
    for _, key in ipairs({ "stars=", "lives=", "coins=", "players=2", "here=central campus", "s_swamp=2",
                           "go=THE SWAMP|UNIVERSITY AUDITORIUM", "lock=REITZ & ENGINEERING|THE HUB|2",
                           "albert_at=on the Plaza", "alberta_at=in Marston" }) do
        check(stats:find(key, 1, true) ~= nil, "stats has " .. key .. ": " .. stats)
    end
end)

test("a friend's line near Albert reaches the host from the friend's own client", function()
    local w, H, F, disk = setup()
    H.pos.x = H.pos.x + 5000
    next_to(F, "albert")
    w:step(2)
    say(w, F, "where do i go next")
    local text = outbox(disk)
    check(text:find("\t" .. F.nps[0].name .. "\twhere do i go next\t", 1, true) ~= nil, "the friend's request: " .. text)
    check(not text:find("\t" .. H.nps[0].name .. "\t", 1, true), "nothing from the host, who is far away")
end)

test("lines away from the mascots, commands and a second question while waiting are ignored", function()
    local w, H, F, disk = setup()
    next_to(H, "albert", 3000)
    say(w, H, "hello?")
    check(not outbox(disk):find("\n1\t"), "far away: no request")
    next_to(H, "albert")
    say(w, H, "/campus where")
    check(not outbox(disk):find("\n1\t"), "a command: no request")
    say(w, H, "first question")
    say(w, H, "second question")
    check(outbox(disk):find("first question", 1, true) and not outbox(disk):find("second question", 1, true),
        "one pending question per player")
end)

test("the bridge's reply reaches everyone as chat + bubble; Albert thinks, talks, then stops", function()
    local w, H, F, disk = setup()
    next_to(H, "albert")
    say(w, H, "how many stars do i have")
    local albert = objects(H)[1]
    check(anim_of(albert) == "sgl_albert_think", "hand on chin while the bridge works: " .. tostring(anim_of(albert)))
    reply(w, disk, 1, "albert", "CHOMP! You have 2 stars, Host! " .. string.rep("More detail for the chat line. ", 6))
    check(Sim.find(H.chat, "Albert:.*You have 2 stars") ~= nil, "host chat shows the reply")
    check(Sim.find(F.chat, "Albert:.*You have 2 stars") ~= nil, "friend chat shows the reply (npc_say packet)")
    check(not outbox(disk):find("\n1\t"), "answered request leaves the outbox")
    check(anim_of(albert) == "sgl_albert_talk", "Albert talks (gestures, jaw): " .. tostring(anim_of(albert)))
    w:seconds(9)
    check(anim_of(albert) ~= "sgl_albert_talk", "and stops talking afterwards")
end)

test("/alberta asks from anywhere; /albert alone says where he is", function()
    local w, H, F, disk = setup()
    Sim.cmd(F, "alberta", "what is the coffee run")
    w:step(3)
    check(Sim.find(F.chat, "asks Alberta:.*what is the coffee run") ~= nil, "the asker sees the question")
    check(Sim.find(H.chat, "asks Alberta:.*what is the coffee run") ~= nil, "so does everyone else")
    check(outbox(disk):find("\talberta\t" .. F.nps[0].name .. "\twhat is the coffee run\t", 1, true) ~= nil,
        "the host queued it for Alberta: " .. outbox(disk))
    reply(w, disk, 1, "alberta", "Race from your 6th-floor desk to the coffee counter and back!")
    check(Sim.find(F.chat, "Alberta:.*coffee counter") ~= nil, "the answer reaches the asker without Alberta nearby")
    Sim.cmd(H, "albert", "")
    check(Sim.find(H.chat, "Albert.* is on the Plaza") ~= nil, "/albert: where Albert is")
end)

test("every 4 minutes the host moves them along their routes: synced, with a poof, one always on the hub", function()
    local w, H, F, disk, clock = setup()
    H.pos.x, F.pos.x = H.pos.x + 5000, F.pos.x + 5000   -- nobody near: free to move
    w:step(5)
    clock.t = clock.t + H.env.SGL_NPC_ROTATE + 1
    w:step(5)
    check(H.env.sgl_npc_step() == 1 and F.env.sgl_npc_step() == 1, "step 1 on both clients")
    check(spot_of(F, "albert").level == C.LEVEL_BOB and spot_of(F, "alberta").level == HUB,
        "Albert went to The Swamp, Alberta came to the hub")
    local objs = objects(F)
    check(#objs == 1 and Sim.raw(objs[1])._model == npc(F, "alberta").model, "the friend now sees Alberta on the hub")
    check(#Sim.objects_with(F, C.id_bhvMistParticleSpawner) >= 1, "with a puff of mist")
    w:warp(F, C.LEVEL_BOB, 1, 1)
    w:step(5)
    objs = objects(F)
    check(#objs == 1 and Sim.raw(objs[1])._model == npc(F, "albert").model, "and Albert is in The Swamp")
end)

test("they don't move while someone is near (a friend's report holds the host)", function()
    local w, H, F, disk, clock = setup()
    H.pos.x = H.pos.x + 5000
    next_to(F, "albert")
    clock.t = clock.t + H.env.SGL_NPC_ROTATE - 1
    w:step(70)      -- the friend's client reports "near a mascot" every 2 s
    clock.t = clock.t + 2
    w:step(30)
    check(H.env.sgl_npc_step() == 0, "held while the friend stands next to Albert")
    F.pos.x = F.pos.x + 5000
    clock.t = clock.t + H.env.SGL_NPC_BUSY_HOLD + 1
    w:step(70)
    check(H.env.sgl_npc_step() == 1, "moves once the friend walks away")
end)

test("waves at newcomers, then faces them", function()
    local w, H, F = setup()
    local albert = objects(H)[1]
    next_to(H, "albert", 2000)
    w:step(5)
    next_to(H, "albert", 300)
    w:step(3)
    check(anim_of(albert) == "sgl_albert_wave", "a player walks up: wave (" .. tostring(anim_of(albert)) .. ")")
    w:step(60)
    check(anim_of(albert) == "sgl_albert_idle", "then stands and attends")
    local want = H.env.atan2s(H.pos.z - albert.oPosZ, H.pos.x - albert.oPosX)
    check(math.abs((albert.oFaceAngleYaw - want + 32768) % 65536 - 32768) < 0x400, "facing the player")
end)

test("nobody around: Albert strolls to the same spots on every client and stays in his spot's radius", function()
    local w, H, F, disk, clock = setup()
    local spot = spot_of(H, "albert")
    local slot
    for s = 126, 150 do     -- slots within the 4 minutes before the next move (the clock starts at 1000 s)
        local tx, tz = H.env.sgl_albert_wander_target(spot, s, 1)
        if math.abs(tx - spot.x) + math.abs(tz - spot.z) > 150 then slot = s break end
    end
    H.pos.x, F.pos.x = H.pos.x + 5000, F.pos.x + 5000
    clock.t = slot * H.env.ALBERT_WANDER_SLOT
    local tx, tz = H.env.sgl_albert_wander_target(spot, slot, 1)
    local a, b = objects(H)[1], objects(F)[1]
    w:step(100)   -- (a Gator Chomp may finish first)
    w:seconds(5)
    check(H.env.sgl_npc_step() == 0, "(still step 0)")
    local d = math.sqrt((a.oPosX - tx) ^ 2 + (a.oPosZ - tz) ^ 2)
    check(d < 40, "he walked to the slot's spot (" .. math.floor(d) .. " away)")
    check(math.abs(a.oPosX - b.oPosX) + math.abs(a.oPosZ - b.oPosZ) < 1, "the same spot on both clients")
    for name, s in pairs(H.env.SGL_NPC_SPOTS) do
        for k = 1, 300 do
            local x, z = H.env.sgl_albert_wander_target(s, k, 2)
            if math.sqrt((x - s.x) ^ 2 + (z - s.z) ^ 2) > s.radius + 1 then
                check(false, name .. ": stroll targets stay within the spot's radius")
                break
            end
        end
    end
end)

test("a stale session's replies are ignored; no bridge -> timeout line", function()
    local w, H, F, disk = setup()
    next_to(H, "albert")
    say(w, H, "hello albert")
    disk.inbox["sgl64_npc"] = "session\told-session\n1\talbert\tstale reply\n"
    w:step(30)
    check(Sim.find(H.chat, "stale reply") == nil, "another session's reply is not shown")
    w:seconds(16)
    check(Sim.find(H.chat, "ask me again") ~= nil, "timeout line after 15 s")
    check(Sim.find(H.chat, "npc_bridge/bridge.py") ~= nil, "the host is told to start the bridge")
end)

test("hosted server (headless host): questions go out as npc_ask events, never into the bridge's inbox", function()
    local w, H, F, disk = setup()
    local prints = {}
    for _, c in ipairs({ H, F }) do c.stubs.gServerSettings.headlessServer = 1 end
    H.stubs.print = function(s) table.insert(prints, s) end
    H.pos.x = H.pos.x + 5000
    next_to(F, "albert")
    w:step(2)
    say(w, F, "how do i unlock lake alice")
    local ev
    for _, line in ipairs(prints) do
        local json = line:match("^SGLEVT (.*)$")
        local e = json and H.env.sgl_json_decode(json)
        if e and e.t == "npc_ask" then ev = e end
    end
    check(ev ~= nil, "the host printed an npc_ask event")
    ev = ev or {}
    check(ev.npc == "albert" and ev.player == F.nps[0].name and ev.text == "how do i unlock lake alice"
        and ev.seq == 1 and type(ev.session) == "string", "event fields: " .. tostring(ev.player) .. " " .. tostring(ev.text))
    check(type(ev.stats) == "string" and ev.stats:find("players=2", 1, true) ~= nil, "with the asker's stats")
    check(disk.own == nil, "no npc_out.txt in sgl64.modfs (server/bridge's inbox)")
    disk.inbox["sgl64_npc"] = "session\t" .. tostring(ev.session) .. "\n1\talbert\tFind four stars, " ..
        F.nps[0].name .. "!\n"
    w:step(20)
    check(Sim.find(F.chat, "Albert:.*Find four stars") ~= nil, "server/bridge's reply reaches the asker")
    say(w, F, "and then?")
    w:seconds(16)
    check(Sim.find(H.chat, "npc_bridge/bridge.py") == nil, "no 'run bridge.py' hint on the hosted server")
end)

print(string.format("%d checks passed, %d failed", passed, failed))
if failed > 0 then os.exit(1) end
