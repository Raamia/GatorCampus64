-- Offline test of mods/sgl64/sgl_npc.lua (the talking hub NPCs) in the multi-client simulator:
-- Albert spawns with his own model, a chat line near him becomes a request in the host's modfs outbox
-- (npc_out.txt, with the sender's live stats for the game guide), the bridge's reply file
-- (sgl64_npc.modfs replies.txt) is relayed to every client as a chat line + speech bubble, and with no
-- bridge the request times out. Run: lua tools/luatest/test_npc.lua (from tools/luatest/run.sh).
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
local ALBERT = { x = 8800, z = -3750 }

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

local function setup()
    local w = Sim.new({ files = Sim.ALL_FILES, built = Sim.built_on_disk() })
    local H = w:connect("Host")
    local F = w:connect("Friend")
    for _, c in ipairs({ H, F }) do
        c.stubs.save_file_get_course_star_count = function(file, course)
            assert(math.type(file) == "integer" and math.type(course) == "integer")
            return course == C.COURSE_BOB - 1 and 2 or 0
        end
    end
    local disk = fake_modfs(H)
    w:warp(H, HUB, 1, 0)
    w:warp(F, HUB, 1, 0)
    w:step(60)
    return w, H, F, disk
end

local function say(w, H, sender, msg)
    for _, fn in ipairs(H.hooks[C.HOOK_ON_CHAT_MESSAGE] or {}) do fn(sender, msg) end
    w:step(1)
end

local function npc_objects(c)
    return Sim.objects_with(c, c.env.id_bhvSglNpc)
end

test("Albert stands at the spawn with his own model; the Koopa is gone", function()
    local w, H = setup()
    local npcs = H.env.SGL_NPCS
    check(npcs[1].id == "albert" and npcs[1].jaw == true, "Albert is the first NPC and flaps his jaw")
    for _, n in ipairs(npcs) do check(n.id ~= "guide", "no Tour Guide Koopa") end
    check(math.abs(npcs[1].x - 8320) + math.abs(npcs[1].z + 4440) < 1500, "Albert is next to the Plaza spawn")
    local objs = npc_objects(H)
    check(#objs == #npcs, "one object per NPC in the hub (" .. #objs .. ")")
end)

test("a line near Albert -> outbox request with the sender's stats", function()
    local w, H, F, disk = setup()
    H.pos.x, H.pos.z = ALBERT.x + 200, ALBERT.z
    w:step(2)
    say(w, H, H.ms[0], "how many stars do i have")
    local text = outbox(disk)
    local session = text:match("^session\t([^\n]+)\n")
    check(session ~= nil, "outbox starts with the session line: " .. text)
    local seq, npc, player, msg, stats = text:match("\n(%d+)\t([^\t]+)\t([^\t]+)\t([^\t]+)\t([^\n]*)\n")
    check(seq == "1" and npc == "albert" and player == H.nps[0].name and msg == "how many stars do i have",
        "request line: " .. tostring(seq) .. " " .. tostring(npc) .. " " .. tostring(player) .. " " .. tostring(msg))
    stats = stats or ""
    for _, key in ipairs({ "stars=", "lives=", "coins=", "players=2", "here=central campus", "s_swamp=2", "s_reitz=0",
                           "go=THE SWAMP|UNIVERSITY AUDITORIUM", "lock=REITZ & ENGINEERING|THE HUB|2" }) do
        check(stats:find(key, 1, true) ~= nil, "stats has " .. key .. ": " .. stats)
    end
    check(disk.own.saves >= 1, "the outbox was saved to disk")
    check(Sim.find(H.chat, "Albert") == nil, "no reply yet (the bridge has not answered)")
end)

test("lines away from NPCs, commands and a second question while waiting are ignored", function()
    local w, H, F, disk = setup()
    H.pos.x, H.pos.z = ALBERT.x + 3000, ALBERT.z
    say(w, H, H.ms[0], "hello?")
    check(disk.own == nil or not outbox(disk):find("\n1\t"), "far away: no request")
    H.pos.x, H.pos.z = ALBERT.x + 100, ALBERT.z
    say(w, H, H.ms[0], "/campus where")
    check(disk.own == nil or not outbox(disk):find("\n1\t"), "a command: no request")
    say(w, H, H.ms[0], "first question")
    say(w, H, H.ms[0], "second question")
    check(outbox(disk):find("first question", 1, true) and not outbox(disk):find("second question", 1, true),
        "one pending question per player")
end)

test("the bridge's reply reaches everyone as chat + bubble; Albert flaps his jaw", function()
    local w, H, F, disk = setup()
    H.pos.x, H.pos.z = ALBERT.x + 150, ALBERT.z
    say(w, H, H.ms[0], "how many stars do i have")
    local session = outbox(disk):match("^session\t([^\n]+)\n")
    local long = "CHOMP! You have 2 stars, Host! Head to The Hub door for Reitz & Engineering! " ..
        string.rep("More detail for the chat line. ", 6)
    disk.inbox["sgl64_npc"] = "session\t" .. session .. "\n1\talbert\t" .. long .. "\n"
    w:step(20)
    check(Sim.find(H.chat, "Albert:.*You have 2 stars") ~= nil, "host chat shows the reply")
    check(Sim.find(F.chat, "Albert:.*You have 2 stars") ~= nil, "friend chat shows the reply (npc_say packet)")
    check(not outbox(disk):find("\n1\t"), "answered request leaves the outbox")
    local albert = npc_objects(H)[1]
    local opened = false
    for _ = 1, 10 do
        w:step(1)
        if albert.oAnimState == 1 then opened = true end
    end
    check(opened, "Albert's jaw opens while he talks")
end)

test("a stale session's replies are ignored; no bridge -> timeout line", function()
    local w, H, F, disk = setup()
    H.pos.x, H.pos.z = ALBERT.x + 150, ALBERT.z
    say(w, H, H.ms[0], "hello albert")
    disk.inbox["sgl64_npc"] = "session\told-session\n1\talbert\tstale reply\n"
    w:step(30)
    check(Sim.find(H.chat, "stale reply") == nil, "another session's reply is not shown")
    w:seconds(16)
    check(Sim.find(H.chat, "ask me again") ~= nil, "timeout line after 15 s")
    check(Sim.find(H.chat, "npc_bridge/bridge.py") ~= nil, "the host is told to start the bridge")
end)

print(string.format("%d checks passed, %d failed", passed, failed))
if failed > 0 then os.exit(1) end
