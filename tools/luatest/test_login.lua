-- Offline tests for the web platform's mod side (docs/web_platform_spec.md §5.2, §6, §7.1, §7.2), with
-- every mod file loaded in the coopdx simulation (sim.lua):
--   * guests.lua -> characters.lua: the 8 guest slots follow the 10 friends (ids, names, models),
--     name cleaning, bad entries skipped, /char guest_<n>; a guests.lua rendered by the bridge's own
--     generator (server/bridge/sglbridge/deploy.py render_guests_lua, run with python3) loads, and its
--     name cleaning matches characters.lua's;
--   * charselect.lua paging: page 1 = the team, page 2 = "GUEST GATORS"; L / R turn the page, D-pad
--     left / right run through the cards in reading order across pages, up / down stay on the page;
--   * sgl_login.lua against the REAL sgl_bridge.lua (server/bridge/README.md): a hosted world has a
--     headless host "Campus" (global index 0, as in test_bridge.lua) that prints the SGLEVT lines;
--     inbox commands go through the bridge's own routing (sgl_bridge_process_inbox on the host, then
--     the packets to the clients): /login, /login cancel, B, login_cancel, /link, login_code (QR +
--     code + countdown, page), login_failed reasons, expiry and no-answer timeouts, verified (own:
--     popup + guest gator selected; others: chat, name tag star, player list description, charselect
--     name tag), verified resend (marks only), disconnects, and the offline / no-headless-host answer.
-- Run: tools/luatest/run.sh   (or: lua tools/luatest/test_login.lua)
local HERE = debug.getinfo(1, "S").source:match("^@(.*/)") or "./"
local Sim = dofile(HERE .. "sim.lua")
local C = Sim.C
local raw = Sim.raw

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
local URL = "https://login.gatorcamp.us/activate?user_code=ABCD-EFGH"
local PAGE = "https://login.gatorcamp.us/activate"
local OFFLINE = "Login is only available on the hosted server"

-- a world with every mod file; each client has a saved pick (no first-spawn menu over the panel)
local function world(opts)
    opts = opts or {}
    opts.files = opts.files or Sim.ALL_FILES
    opts.built = opts.built or Sim.built_on_disk()
    return Sim.new(opts)
end

-- in a hosted world (w.headless) every process sees gServerSettings.headlessServer; the host's stdout
-- is captured (c.prints) and it has no modfs inbox file (commands go in through inbox() below)
local function join(w, name, pick)
    local c = w:connect(name)
    if w.headless then
        c.stubs.gServerSettings.headlessServer = 1
        c.prints = {}
        c.stubs.print = function(s) table.insert(c.prints, s) end
        c.stubs.mod_fs_hide_errors = function(h) assert(type(h) == "boolean") end
        c.stubs.mod_fs_reload = function() return nil end
        if c.gi == 0 then w.host = c end
    end
    c.strStorage.friend = pick or "daniel"
    w:step(3)
    w:warp(c, HUB, 1, 0)
    w:step(3)
    return c
end

-- the hosted server: "Campus" (global index 0) is the headless host the bridge reads
local function hosted()
    local w = world()
    w.headless, w.seq = true, 0
    local H = join(w, "Campus")
    assert(H.gi == 0 and H.env.sgl_bridge_is_host(), "Campus is the headless host")
    return w, H
end

-- the bridge writes an inbox command: the host routes it (sgl_bridge.lua), the packets arrive a frame later
local function inbox(w, t, fields)
    w.seq = w.seq + 1
    local cmd = { seq = w.seq, t = t }
    for k, v in pairs(fields) do cmd[k] = v end
    local H = w.host
    check(H.env.sgl_bridge_process_inbox(H.env.sgl_json_encode({ seq = w.seq, cmds = { cmd } })) == 1, t .. " taken from the inbox")
    w:step(1)
end

-- the SGLEVT events of type t the host printed (from global index gi when given)
local function events(w, t, gi)
    local out = {}
    for _, line in ipairs(w.host.prints) do
        local json = line:match("^SGLEVT (.*)$")
        local e = json and w.host.env.sgl_json_decode(json)
        if e and e.t == t and (gi == nil or e.gi == gi) then out[#out + 1] = e end
    end
    return out
end

local function li_of(c, gi)
    for i = 0, C.MAX_PLAYERS - 1 do
        if raw(c.nps[i]).connected and raw(c.nps[i]).globalIndex == gi then return i end
    end
end

local function panel(c) return c.env._G.sglLoginPanel() end
local function last(list) return list[#list] end
local function hud_text(c) return table.concat(c.hudText, " | ") end

-- the label under the charselect cursor: the footer name, the largest text the menu draws
local function cursor_label(c)
    local best, sc = nil, -1
    for _, d in ipairs(c.draw) do
        if d.k == "text" and d.sc > sc and d.s:match("^[A-Z0-9 ]+$") and #d.s > 1 then best, sc = d.s, d.sc end
    end
    return best
end

local function press(w, c, button, n)
    for _ = 1, (n or 1) do
        c.pressed = button
        w:step(1)
    end
    w:step(1)
end

local function menu_open(c) return c.env._G.sglCharSelectIsOpen() end

-- coopdx (smlua_hooks.c): HOOK_ON_NAMETAGS_RENDER hooks run in registration order, the first one that
-- returns a string or a table decides the tag
local function nametag(c, li)
    for _, fn in ipairs(c.hooks[C.HOOK_ON_NAMETAGS_RENDER] or {}) do
        local r = fn(li, { x = 0, y = 0, z = 0 })
        if type(r) == "string" or type(r) == "table" then return r end
    end
    return nil
end

---------------------------------------------------------------------------------------------
test("guests.lua: 8 guest slots after the 10 friends", function()
    local w = world()
    local H = join(w, "Host")
    local list = H.env._G.sglFriends
    check(#list == 18, "18 characters (" .. #list .. ")")
    check(list[10].id == "cher" and not list[10].guest, "the team first")
    for n = 1, 8 do
        local f = list[10 + n]
        check(f.id == "guest_" .. n and f.name == "Guest " .. n and f.guest == true and f.slot == n and f.owner == nil,
            "slot " .. n .. ": guest_" .. n .. " / Guest " .. n)
        check(math.type(f.model) == "integer" and f.model ~= C.E_MODEL_ERROR_MODEL, "slot " .. n .. ": model guest_" .. n .. "_geo loaded")
    end
    Sim.cmd(H, "char", "guest_3")
    check(H.env.gPlayerSyncTable[0].friend == 13 and H.strStorage.friend == "guest_3", "/char guest_3 picks slot 3 and remembers it")
    Sim.cmd(H, "char", "Guest 5")
    check(H.env.gPlayerSyncTable[0].friend == 15, "/char by display name")
    w:step(2)
    check(raw(H.ms[0].marioObj)._model == list[15].model, "the guest model is used")
end)

test("guests.lua format: names cleaned, bad entries skipped", function()
    local w = world()
    local H = join(w, "Host")
    local env = H.env
    local before = #env._G.sglFriends
    local added = env.sgl_guests_register({
        { slot = 0, name = "zero" }, { slot = 9, name = "nine" }, { slot = 2.5, name = "frac" }, "junk",
        { slot = 4, name = "\\#ff0000\\Evil\tName That Is Far Too Long", owner = "auth0|abc" },
        { slot = 4, name = "dupe" },
        { slot = 6, name = "   " },
    })
    check(added == 2, "only valid, distinct slots are added (" .. tostring(added) .. ")")
    local a, b = env._G.sglFriends[before + 1], env._G.sglFriends[before + 2]
    check(a.id == "guest_4" and a.name == "EvilName Tha" and a.owner == "auth0|abc", "colour code + tab stripped, 12 chars max: '" .. a.name .. "'")
    check(b.id == "guest_6" and b.name == "Guest 6", "blank name -> 'Guest 6'")
    check(#H.console >= 4, "warnings logged for the bad entries")
end)

test("charselect: two pages, L / R, D-pad across the page edge, pick a guest", function()
    local w = world()
    local H = join(w, "Host", "cher")
    Sim.cmd(H, "char", "")
    w:step(12)
    check(menu_open(H), "/char opens the menu")
    check(cursor_label(H) == "CHER", "cursor starts on the current pick (Cher, card 10): " .. tostring(cursor_label(H)))
    check(Sim.hud_has(H, "^DANIEL$") and not Sim.hud_has(H, "^GUEST 1$"), "page 1: the team's cards only")
    check(Sim.hud_has(H, "L / R: page"), "footer hint mentions L / R")
    press(w, H, C.R_JPAD)
    check(cursor_label(H) == "GUEST 1", "right from the last card of page 1 -> Guest 1 (" .. tostring(cursor_label(H)) .. ")")
    check(Sim.hud_has(H, "^GUEST 8$") and not Sim.hud_has(H, "^DANIEL$"), "page 2: guest cards only")
    -- the title of page 2 (drawn letter by letter)
    local letters = {}
    for _, d in ipairs(H.draw) do if d.k == "text" and #d.s == 1 then letters[#letters + 1] = d.s end end
    check(table.concat(letters):find("GGUUEESSTTGGAATTOORRSS", 1, true) ~= nil, "page 2 title GUEST GATORS (shadow + letter each)")
    press(w, H, C.L_JPAD)
    check(cursor_label(H) == "CHER", "left from Guest 1 -> back to Cher")
    press(w, H, C.R_TRIG)
    check(cursor_label(H) == "GUEST 8", "R: next page, same spot (row 2, last column -> clamped to Guest 8)")
    press(w, H, C.U_JPAD)
    check(cursor_label(H) == "GUEST 3", "up on page 2: Guest 8 -> Guest 3")
    press(w, H, C.U_JPAD)
    check(cursor_label(H) == "GUEST 8", "up wraps within the page: Guest 3 -> Guest 8 (clamped)")
    press(w, H, C.L_TRIG)
    check(cursor_label(H) == "ALFRED", "L: previous page, same spot (Guest 8 = card 8 of its page -> Alfred)")
    press(w, H, C.L_TRIG)
    check(cursor_label(H) == "GUEST 8", "L wraps to the last page")
    press(w, H, C.R_TRIG)
    press(w, H, C.U_JPAD)
    check(cursor_label(H) == "RAAMI", "back on page 1, up from Alfred -> Raami")
    press(w, H, C.R_TRIG)
    check(cursor_label(H) == "GUEST 3", "R from Raami -> Guest 3")
    press(w, H, C.R_JPAD)
    press(w, H, C.L_JPAD)
    check(cursor_label(H) == "GUEST 3", "right then left: Guest 4, back to Guest 3")
    press(w, H, C.A_BUTTON)
    w:step(25)
    check(not menu_open(H), "picked and closed")
    check(H.env.gPlayerSyncTable[0].friend == 13 and H.strStorage.friend == "guest_3", "Guest 3 picked and remembered")
    check(Sim.find(H.popups, "You are now .-Guest 3") ~= nil, "popup names the guest")
    -- L + START opens without turning the page
    H.pressed = C.L_TRIG | C.START_BUTTON
    w:step(3)
    check(menu_open(H) and cursor_label(H) == "GUEST 3", "L + START reopens on the pick's page (the L does not turn it)")
end)

test("charselect: a guest whose model failed shows the ? card and buzzes", function()
    local w = world({})
    w.brokenModels = { guest_2_geo = true }
    local H = join(w, "Host", "cher")
    Sim.cmd(H, "char", "guest_2")
    check(Sim.find(H.chat, "Guest 2's model failed to load") ~= nil, "/char guest_2 says it failed")
    Sim.cmd(H, "char", "")
    w:step(12)
    press(w, H, C.R_JPAD, 2)
    check(cursor_label(H) == "GUEST 2", "cursor on Guest 2")
    check(Sim.hud_has(H, "model failed to load"), "footer says the model failed")
    press(w, H, C.A_BUTTON)
    check(menu_open(H) and H.env.gPlayerSyncTable[0].friend == 10, "A does not pick it")
end)


-- characters.lua + charselect.lua without the checked-in guests.lua (the test loads its own)
local function files_without_guests()
    local out = {}
    for _, f in ipairs(Sim.ALL_FILES) do
        if f ~= "guests.lua" then out[#out + 1] = f end
    end
    return out
end

-- run a Python snippet with server/bridge on sys.path; returns its stdout (python3, or $PYTHON)
local function python(src)
    local path = os.tmpname()
    local f = assert(io.open(path, "w"))
    f:write("import sys\nsys.path.insert(0, " .. string.format("%q", Sim.ROOT .. "server/bridge") .. ")\n" .. src)
    f:close()
    local p = assert(io.popen((os.getenv("PYTHON") or "python3") .. " " .. path .. " 2>&1"))
    local out = p:read("a")
    local ok = p:close()
    os.remove(path)
    assert(ok, "python failed:\n" .. out)
    return out
end

test("guests.lua rendered by the bridge (deploy.py render_guests_lua) loads in characters.lua", function()
    local out = python([[
import json
from sglbridge.deploy import clean_name, render_guests_lua
raw = {1: 'Al "the" \\gator\\', 2: "\\#ff0000\\Evil\tName That Is Far Too Long", 3: "café über gator",
       4: "   ", 5: "Twelve chars x", 7: "abcdefghijk  z", 8: "x" * 40}
owners = {1: "auth0|1", 2: "google-oauth2|1234567890", 3: "github|42", 7: ""}
roster = {s: {"name": raw[s], "owner": owners.get(s)} for s in raw}
print(json.dumps({"lua": render_guests_lua(roster),
                  "raw": [raw.get(s, "") for s in range(1, 9)],
                  "names": [clean_name(raw.get(s), s) for s in range(1, 9)],
                  "owners": [owners.get(s) or "" for s in range(1, 9)]}))
]])
    local w = world({ files = files_without_guests() })
    local H = join(w, "Host")
    local doc = H.env.sgl_json_decode(out)
    local list = H.env._G.sglFriends
    check(#list == 10, "no guests before the generated file")
    local warnings = #H.console
    local chunk = assert(load(doc.lua, "=guests.lua", "t", H.env))
    H.loading = true
    chunk()
    H.loading = false
    check(#list == 18, "8 guest slots registered (" .. #list .. ")")
    check(#H.console == warnings, "no warnings: " .. tostring(H.console[warnings + 1]))
    for n = 1, 8 do
        local f = list[10 + n]
        check(f ~= nil and f.id == "guest_" .. n and f.slot == n and f.guest == true, "slot " .. n .. " in order")
        check(f ~= nil and f.name == doc.names[n], "slot " .. n .. " name: game '" .. tostring(f and f.name) .. "' = bridge '" .. doc.names[n] .. "'")
        check(f ~= nil and f.owner == (doc.owners[n] ~= "" and doc.owners[n] or nil), "slot " .. n .. " owner")
        check(f ~= nil and f.model ~= C.E_MODEL_ERROR_MODEL, "slot " .. n .. " model")
    end
    -- the two cleanings agree on the raw names too (the site shows the bridge's, the game its own)
    local w2 = world({ files = files_without_guests() })
    local H2 = join(w2, "Host")
    local entries = {}
    for n = 1, 8 do entries[n] = { slot = n, name = doc.raw[n] } end
    check(H2.env.sgl_guests_register(entries) == 8, "raw names registered")
    for n = 1, 8 do
        local f = H2.env._G.sglFriends[10 + n]
        check(f.name == doc.names[n], "raw slot " .. n .. ": characters.lua '" .. f.name .. "' = deploy.py clean_name '" .. doc.names[n] .. "'")
    end
end)

test("offline / no headless host: /login and /link only answer that login needs the hosted server", function()
    local w = world()
    local H = join(w, "Host")
    local F = join(w, "Friend")
    check(type(F.env.sglBridgeEmit) == "function", "the real sgl_bridge.lua is loaded")
    for _, c in ipairs({ H, F }) do
        Sim.cmd(c, "login", "")
        check(last(c.chat) == OFFLINE, c.name .. ": /login")
        Sim.cmd(c, "link", "K7Q2XF")
        check(last(c.chat) == OFFLINE, c.name .. ": /link")
        check(panel(c) == nil, c.name .. ": no panel")
    end
    w:step(30)
    check(not Sim.hud_has(H, "GATOR PASS") and not Sim.hud_has(F, "GATOR PASS"), "nothing drawn")
end)

test("/login: request, QR + code panel, countdown, B closes it and sends login_cancel", function()
    local w, H = hosted()
    local F = join(w, "Friend")
    local G = join(w, "Guest")
    Sim.cmd(F, "login", "")
    check(panel(F).state == "requesting", "panel: requesting")
    w:step(2)
    local req = events(w, "login_req")
    check(#req == 1 and req[1].gi == F.gi and req[1].name == "Friend", "login_req { gi, name } printed by the host")
    check(Sim.hud_has(F, "GATOR PASS") and Sim.hud_has(F, "Asking the login server"), "requesting panel drawn")
    Sim.cmd(F, "login", "")
    w:step(1)
    check(#events(w, "login_req") == 1 and Sim.find(F.chat, "already waiting") ~= nil, "a second /login does not ask again")

    -- a code for somebody else goes to them only (and a player who did not ask ignores it)
    inbox(w, "login_code", { gi = G.gi, user_code = "ZZZZ-ZZZZ", uri = URL, page = PAGE, expires = 900 })
    check(panel(F).state == "requesting", "login_code for another player: not here")
    check(panel(G) == nil, "login_code without a /login: ignored")
    inbox(w, "login_code", { gi = F.gi, user_code = "ABCD-EFGH", uri = URL, page = PAGE, expires = 900 })
    local p = panel(F)
    check(p.state == "code" and p.code == "ABCD-EFGH" and p.qr ~= nil and p.qr.version == 4, "panel: code + version 4 QR")
    w:step(1)
    check(Sim.hud_has(F, "^ABCD%-EFGH$"), "the code in big letters")
    check(Sim.hud_has(F, "^login%.gatorcamp%.us/activate$"), "the activate address (page)")
    check(Sim.hud_has(F, "Code expires in 15:00") or Sim.hud_has(F, "Code expires in 14:59"), "countdown from 15 minutes")
    check(Sim.hud_has(F, "Waiting for approval"), "waiting line")
    check(Sim.hud_has(F, "B or /login cancel: close"), "how to close")
    local rects, white, frame = 0, false, nil
    for _, d in ipairs(F.draw) do
        if d.k == "rect" then
            rects = rects + 1
            if d.col[1] == 255 and d.col[2] == 255 and d.col[3] == 255 and d.w == d.h and d.w >= 45 then white = true end
            if d.col[1] == 250 and d.col[2] == 70 and d.col[3] == 22 then frame = d end
        end
    end
    check(rects > 150 and white, "QR drawn: white square + many module runs (" .. rects .. " rects)")
    local screenW, screenH = F.env.djui_hud_get_screen_width(), F.env.djui_hud_get_screen_height()
    check(frame ~= nil and math.abs((frame.x + frame.w / 2) - screenW / 2) <= 1,
        "Gator Pass card is centered between the corner HUD controls")
    check(frame ~= nil and frame.y >= 21 and frame.x + frame.w < screenW - 54,
        "card clears the top-left Boards button and the right-edge HUD badges")
    w:seconds(2)
    check(Sim.hud_has(F, "Code expires in 14:5[78]"), "countdown runs: " .. tostring(hud_text(F):match("Code expires in [%d:]+")))
    check(not Sim.hud_has(H, "GATOR PASS") and not Sim.hud_has(G, "GATOR PASS"), "only the requesting player sees it")

    F.pressed = C.B_BUTTON
    w:step(1)
    check(panel(F) == nil, "B closes the panel")
    check((F.lastInput.pressed & C.B_BUTTON) == 0, "the B press does not reach Mario")
    w:step(1)
    local cancel = events(w, "login_cancel")
    check(#cancel == 1 and cancel[1].gi == F.gi and cancel[1].name == "Friend", "B on a waiting login: login_cancel { gi, name }")
    inbox(w, "login_code", { gi = F.gi, user_code = "LATE-CODE", uri = URL, page = PAGE, expires = 900 })
    check(panel(F) == nil, "a code arriving after the close is ignored")
    Sim.cmd(F, "login", "cancel")
    check(last(F.chat) == "No login in progress.", "/login cancel with nothing open")
    Sim.cmd(F, "login", "please")
    check(last(F.chat):find("Usage: /login") ~= nil, "unknown argument: usage")
    w:step(1)
    check(#events(w, "login_cancel") == 1, "nothing else cancelled")
end)

test("/login: cancel, failure reasons, expiry and no-answer timeouts", function()
    local w, H = hosted()
    local P = join(w, "Player")
    local function code(extra)
        local f = { gi = P.gi, user_code = "ABCD-EFGH", uri = URL, page = PAGE, expires = 900 }
        for k, v in pairs(extra or {}) do f[k] = v end
        return f
    end
    local function cancels() w:step(1); return #events(w, "login_cancel", P.gi) end

    Sim.cmd(P, "login", "")
    inbox(w, "login_code", code())
    Sim.cmd(P, "login", "cancel")
    check(panel(P) == nil and last(P.chat) == "Login panel closed.", "/login cancel closes it")
    check(cancels() == 1, "/login cancel while waiting: login_cancel")

    Sim.cmd(P, "login", "")
    inbox(w, "login_code", code({ page = "https://gp.example.org/activate/" }))
    w:step(1)
    check(Sim.hud_has(P, "^gp%.example%.org/activate$"), "the address to type comes from page")
    inbox(w, "login_failed", { gi = P.gi, reason = "denied" })
    check(panel(P).state == "failed" and Sim.find(P.popups, "denied") ~= nil, "denied: failed panel + popup")
    w:step(1)
    check(Sim.hud_has(P, "NOT LOGGED IN"), "failure drawn")
    P.pressed = C.B_BUTTON
    w:step(1)
    check(panel(P) == nil and cancels() == 1, "B on a failure panel closes it, nothing to cancel")

    Sim.cmd(P, "login", "")
    inbox(w, "login_code", code({ expires = 2 }))
    w:seconds(2.5)
    check(panel(P) ~= nil and panel(P).state == "failed" and panel(P).msg:find("expired") ~= nil, "code expires on the client too")
    check(cancels() == 2, "an expired code is cancelled with the bridge")
    w:seconds(6)
    check(panel(P) == nil, "the failure panel goes away by itself")

    -- a Unix-time `expires` works as well; without page the address comes from the uri
    Sim.cmd(P, "login", "")
    inbox(w, "login_code", { gi = P.gi, user_code = "ABCD-EFGH", uri = URL, expires = P.env.get_time() + 600 })
    check(panel(P).frames > 590 * 30 and panel(P).frames <= 600 * 30, "Unix-time expiry -> about 10 minutes")
    w:step(1)
    check(Sim.hud_has(P, "^login%.gatorcamp%.us/activate$"), "no page: the uri without its query")
    Sim.cmd(P, "login", "cancel")
    check(cancels() == 3, "cancelled")

    Sim.cmd(P, "login", "")
    w:seconds(21)
    check(panel(P) ~= nil and panel(P).state == "failed" and panel(P).msg:find("No answer") ~= nil, "no login_code within 20 s: no-answer message")
    check(cancels() == 4, "no answer: the request is cancelled")
    w:seconds(6)
    inbox(w, "login_failed", { gi = P.gi, reason = "expired" })
    check(Sim.find(P.popups, "expired") ~= nil, "login_failed without an open panel still tells the player")
    w:seconds(6)
    for reason, text in pairs({ invalid_token = "could not be checked", unavailable = "unavailable right now",
            error = "did not work", bad_code = "link code is not valid" }) do
        inbox(w, "login_failed", { gi = P.gi, reason = reason })
        check(panel(P) ~= nil and panel(P).msg:find(text, 1, true) ~= nil, reason .. ": " .. tostring(panel(P) and panel(P).msg))
    end
    check(#events(w, "login_req", P.gi) == 5, "one login_req per /login (" .. #events(w, "login_req", P.gi) .. ")")
end)

test("/link: code check, link_req, no-answer timeout", function()
    local w, H = hosted()
    local P = join(w, "Player")
    local function links() w:step(1); return events(w, "link_req", P.gi) end
    Sim.cmd(P, "link", "")
    check(last(P.chat):find("Usage: /link") ~= nil, "no code: usage")
    Sim.cmd(P, "link", "K7Q2X")
    check(last(P.chat):find("Usage: /link") ~= nil and #links() == 0, "5 characters: usage")
    Sim.cmd(P, "link", "K7Q2X!")
    check(#links() == 0, "punctuation: usage")
    Sim.cmd(P, "link", " k7q-2xf ")
    check(last(P.chat) == "Linking with code K7Q2XF...", "says it is linking")
    local l = links()
    check(#l == 1 and l[1].code == "K7Q2XF" and l[1].name == "Player", "link_req { gi, name, code } with the code normalised")
    w:seconds(21)
    check(Sim.find(P.chat, "No answer from the login server") ~= nil, "no answer: says so")
    Sim.cmd(P, "link", "K7Q2XF")
    inbox(w, "login_failed", { gi = P.gi, reason = "bad_code" })
    check(Sim.find(P.popups, "link code is not valid") ~= nil, "bad code: popup")
end)

test("verified: own popup + guest gator, star for everyone, cleared on leave", function()
    local w, H = hosted()
    local F = join(w, "Friend", "josh")
    local G = join(w, "Guest")
    Sim.cmd(F, "login", "")
    inbox(w, "login_code", { gi = F.gi, user_code = "ABCD-EFGH", uri = URL, page = PAGE, expires = 900 })
    -- the bridge's verified is a broadcast: every client runs the handler (the host too)
    inbox(w, "verified", { gi = F.gi, name = "Friend", nickname = "Alice", guest_slot = 3, uf = true })
    check(panel(F).state == "ok" and Sim.find(F.popups, "verified as Alice") ~= nil, "Friend: VERIFIED panel + popup")
    check(F.env.gPlayerSyncTable[0].friend == 13 and F.strStorage.friend == "guest_3", "Friend now plays their guest gator (slot 3), remembered")
    check(Sim.find(F.popups, "Your gator .-Guest 3.- is ready") ~= nil, "popup about the guest gator")
    w:step(1)
    check(Sim.hud_has(F, "VERIFIED!") and Sim.hud_has(F, "Welcome, Alice!") and Sim.hud_has(F, "Your gator Guest 3 is ready!"), "success panel drawn")
    check(H.env.gPlayerSyncTable[0].friend == 1 and G.env.gPlayerSyncTable[0].friend == 1, "the others keep their characters")
    check(Sim.find(G.chat, "Friend is verified with Gator Pass") ~= nil, "Guest: chat line")
    check(Sim.find(H.chat, "Friend is verified with Gator Pass") ~= nil, "Campus (host): chat line")
    w:seconds(6)
    check(panel(F) == nil, "success panel closes by itself")

    -- marks: own and seen from the others
    local gf = li_of(G, F.gi)
    check(G.env._G.sglIsVerified(gf) == true and G.env._G.sglIsVerified(0) == false, "Guest: Friend verified, Guest not")
    check(F.env._G.sglIsVerified(0) == true, "Friend: self verified")
    local tag = nametag(G, gf)
    check(tag == "\\#ffd700\\* \\#dcdcdc\\Friend", "Guest: Friend's name tag gets the gold star: " .. tostring(tag))
    check(nametag(G, 0) == nil, "unverified name tags untouched")
    -- Library West hide and seek hides tags: the star must not un-hide one
    local hide = G.env.sgl_libwest_hns_hide_tag
    G.env.sgl_libwest_hns_hide_tag = function() return true end
    G.stubs.gLakituState = {}                                   -- (the hide hook reads it)
    local hidden = nametag(G, gf)
    check(type(hidden) == "table" and hidden.name == "", "a hidden tag stays hidden for a verified player")
    G.env.sgl_libwest_hns_hide_tag = hide
    local np = raw(G.nps[gf])
    check(np.description == "GATOR PASS" and np.descriptionR == 255 and np.descriptionG == 215, "player list description in gold")
    -- charselect name tags: Guest opens the menu and turns to the guest page, Friend's tag has the star
    G.env.gPlayerSyncTable[gf].friend = F.env.gPlayerSyncTable[0].friend   -- (sim.lua does not sync player tables)
    Sim.cmd(G, "char", "")
    w:step(12)
    press(w, G, C.R_TRIG)
    check(Sim.hud_has(G, "^%*Friend$"), "charselect: '*Friend' tag on Guest 3's card")
    press(w, G, C.B_BUTTON)
    Sim.cmd(F, "char", "")
    w:step(12)
    check(Sim.hud_has(F, "^%*YOU$"), "charselect: own tag '*YOU'")
    press(w, F, C.B_BUTTON)

    -- already verified
    Sim.cmd(F, "login", "")
    check(last(F.chat) == "You are already verified as Alice.", "/login when verified")
    w:step(1)
    check(#events(w, "login_req", F.gi) == 1, "no second login_req")

    -- leaving clears it; a new player on the same index is not verified
    w:disconnect(F)
    w:step(2)
    check(G.env._G.sglIsVerified(gf) == false, "Guest: mark gone after Friend left")
    check(nametag(G, gf) == nil, "name tag plain again")
    check(#events(w, "login_req", G.gi) == 0 and #events(w, "login_req", H.gi) == 0, "the others sent nothing")
end)

test("verified resend (somebody joined): marks only, no popup / panel / gator change", function()
    local w, H = hosted()
    local F = join(w, "Friend", "josh")
    Sim.cmd(F, "login", "")
    inbox(w, "login_code", { gi = F.gi, user_code = "ABCD-EFGH", uri = URL, page = PAGE, expires = 900 })
    inbox(w, "verified", { gi = F.gi, name = "Friend", nickname = "Alice", guest_slot = 3 })
    w:seconds(6)
    check(F.env.gPlayerSyncTable[0].friend == 13 and panel(F) == nil, "verified once: guest gator, panel gone")
    Sim.cmd(F, "char", "cher")
    check(F.env.gPlayerSyncTable[0].friend == 10, "Friend switched to Cher afterwards")

    local J = join(w, "Joiner")
    local jf = li_of(J, F.gi)
    check(J.env._G.sglIsVerified(jf) == false, "the joiner does not know yet")
    local popupsF, chatF, chatH, soundsF = #F.popups, #F.chat, #H.chat, #F.sounds
    -- the bridge re-broadcasts every linked player with resend = true
    inbox(w, "verified", { gi = F.gi, name = "Friend", nickname = "Alice", guest_slot = 3, resend = true })
    w:step(1)
    check(J.env._G.sglIsVerified(jf) == true, "the joiner now sees Friend verified")
    check(nametag(J, jf) == "\\#ffd700\\* \\#dcdcdc\\Friend", "the joiner's name tag star")
    check(raw(J.nps[jf]).description == "GATOR PASS", "the joiner's player list description")
    check(Sim.find(J.chat, "is verified with Gator Pass") == nil and #H.chat == chatH, "no chat line for a re-broadcast")
    check(F.env._G.sglIsVerified(0) == true, "Friend still verified")
    check(#F.popups == popupsF and #F.chat == chatF and #F.sounds == soundsF, "Friend: no popup, chat line or sound again")
    check(panel(F) == nil and not Sim.hud_has(F, "VERIFIED!"), "Friend: no welcome panel again")
    check(F.env.gPlayerSyncTable[0].friend == 10 and F.strStorage.friend == "cher", "Friend keeps Cher (the guest gator is not re-selected)")
end)

test("verified: no guest slot, unknown slot, broken guest model", function()
    local w = world({})
    w.brokenModels = { guest_5_geo = true }
    w.headless, w.seq = true, 0
    join(w, "Campus")
    local P = join(w, "Player", "anh")
    inbox(w, "verified", { gi = P.gi, name = "Player", nickname = "Bob" })
    check(P.env.gPlayerSyncTable[0].friend == 4 and Sim.find(P.popups, "verified as Bob") ~= nil, "no slot: keeps Anh, popup")
    inbox(w, "verified", { gi = P.gi, name = "Player", nickname = "Bob", guest_slot = 5 })
    check(P.env.gPlayerSyncTable[0].friend == 4 and Sim.find(P.chat, "slot 5%) did not load") ~= nil, "broken guest model: says so, keeps Anh")
    inbox(w, "verified", { gi = P.gi, name = "Player", nickname = "Bob", guest_slot = 42 })
    check(P.env.gPlayerSyncTable[0].friend == 4 and Sim.find(P.chat, "slot 42%) did not load") ~= nil, "unknown slot: says so")
    inbox(w, "verified", { gi = P.gi, name = "Player", nickname = "", guest_slot = "2" })
    check(P.env.gPlayerSyncTable[0].friend == 12, "slot as a string (JSON) still works")
    check(Sim.find(P.popups, "verified as Player") ~= nil, "empty nickname: the coopdx name")
    inbox(w, "verified", { gi = 99, name = "Ghost", nickname = "Ghost" })
    check(true, "verified for an unknown player does not throw")
end)

print(string.format("\n%d checks passed, %d failed", passed, failed))
if failed > 0 then os.exit(1) end
