-- Offline tests for the web platform's mod side (docs/web_platform_spec.md §5.2, §7.1, §7.2), with
-- every mod file loaded in the coopdx simulation (sim.lua):
--   * guests.lua -> characters.lua: the 8 guest slots follow the 10 friends (ids, names, models),
--     name cleaning, bad entries skipped, /char guest_<n>;
--   * charselect.lua paging: page 1 = the team, page 2 = "GUEST GATORS"; L / R turn the page, D-pad
--     left / right run through the cards in reading order across pages, up / down stay on the page;
--   * sgl_login.lua against a stub sgl_bridge.lua (_G.sglBridgeEmit / _G.sglBridgeOnCommand, the
--     bridge's host -> client forwarding modelled as a direct call on the target client):
--     /login, /login cancel, B, /link, login_code (QR + code + countdown), login_failed, expiry and
--     no-answer timeouts, verified (own: popup + guest gator selected; others: chat, name tag star,
--     player list description, charselect name tag), disconnects, and the offline answer.
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
local URL = "https://login.chooseyourgator.select/activate?user_code=ABCD-EFGH"

-- a world with every mod file; each client has a saved pick (no first-spawn menu over the panel)
local function world(opts)
    opts = opts or {}
    opts.files = Sim.ALL_FILES
    opts.built = opts.built or Sim.built_on_disk()
    return Sim.new(opts)
end

local function join(w, name, pick)
    local c = w:connect(name)
    c.strStorage.friend = pick or "daniel"
    w:step(3)
    w:warp(c, HUB, 1, 0)
    w:step(3)
    return c
end

-- stub sgl_bridge.lua on client c: records emits, keeps the command handlers
local function stub_bridge(c)
    local b = { emits = {}, handlers = {} }
    c.env._G.sglBridgeEmit = function(t, fields)
        assert(type(t) == "string" and type(fields) == "table", "sglBridgeEmit(t, fields)")
        table.insert(b.emits, { t = t, fields = fields })
    end
    c.env._G.sglBridgeOnCommand = function(name, fn)
        assert(type(name) == "string" and type(fn) == "function", "sglBridgeOnCommand(name, fn)")
        b.handlers[name] = fn
    end
    c.bridge = b
    return b
end

local function send(c, name, cmd)
    local fn = c.bridge.handlers[name]
    assert(fn ~= nil, c.name .. ": no handler for " .. name)
    fn(cmd)
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

test("offline: /login and /link only answer that login needs the hosted server", function()
    local w = world()
    local H = join(w, "Host")
    Sim.cmd(H, "login", "")
    check(last(H.chat) == "Login is only available on the hosted server", "/login offline")
    Sim.cmd(H, "link", "K7Q2XF")
    check(last(H.chat) == "Login is only available on the hosted server", "/link offline")
    check(panel(H) == nil, "no panel")
    w:step(30)
    check(not Sim.hud_has(H, "GATOR PASS"), "nothing drawn")
end)

test("/login: request, QR + code panel, countdown, B closes it", function()
    local w = world()
    local H = join(w, "Host")
    local F = join(w, "Friend")
    local b = stub_bridge(F)
    w:step(1)
    check(b.handlers.login_code and b.handlers.verified and b.handlers.login_failed, "handlers registered once the bridge exists")
    Sim.cmd(F, "login", "")
    check(#b.emits == 1 and b.emits[1].t == "login_req" and b.emits[1].fields.name == "Friend", "login_req { name } emitted")
    check(panel(F).state == "requesting", "panel: requesting")
    w:step(2)
    check(Sim.hud_has(F, "GATOR PASS") and Sim.hud_has(F, "Asking the login server"), "requesting panel drawn")
    Sim.cmd(F, "login", "")
    check(#b.emits == 1 and Sim.find(F.chat, "already waiting") ~= nil, "a second /login does not ask again")

    -- a code for somebody else is ignored
    send(F, "login_code", { gi = 0, user_code = "ZZZZ-ZZZZ", uri = URL, expires = 900 })
    check(panel(F).state == "requesting", "login_code for another player ignored")
    send(F, "login_code", { gi = F.gi, user_code = "ABCD-EFGH", uri = URL, expires = 900 })
    local p = panel(F)
    check(p.state == "code" and p.code == "ABCD-EFGH" and p.qr ~= nil and p.qr.version == 5, "panel: code + version 5 QR")
    w:step(1)
    check(Sim.hud_has(F, "^ABCD%-EFGH$"), "the code in big letters")
    check(Sim.hud_has(F, "^login%.chooseyourgator%.select/activate$"), "the activate address (from the uri)")
    check(Sim.hud_has(F, "Code expires in 15:00") or Sim.hud_has(F, "Code expires in 14:59"), "countdown from 15 minutes")
    check(Sim.hud_has(F, "Waiting for approval"), "waiting line")
    check(Sim.hud_has(F, "B or /login cancel: close"), "how to close")
    local rects, white = 0, false
    for _, d in ipairs(F.draw) do
        if d.k == "rect" then
            rects = rects + 1
            if d.col[1] == 255 and d.col[2] == 255 and d.col[3] == 255 and d.w == d.h and d.w >= 45 then white = true end
        end
    end
    check(rects > 150 and white, "QR drawn: white square + many module runs (" .. rects .. " rects)")
    w:seconds(2)
    check(Sim.hud_has(F, "Code expires in 14:5[78]"), "countdown runs: " .. hud_text(F):match("Code expires in [%d:]+"))
    check(not Sim.hud_has(H, "GATOR PASS"), "only the requesting player sees it")

    F.pressed = C.B_BUTTON
    w:step(1)
    check(panel(F) == nil, "B closes the panel")
    check((F.lastInput.pressed & C.B_BUTTON) == 0, "the B press does not reach Mario")
    Sim.cmd(F, "login", "cancel")
    check(last(F.chat) == "No login in progress.", "/login cancel with nothing open")
    Sim.cmd(F, "login", "please")
    check(last(F.chat):find("Usage: /login") ~= nil, "unknown argument: usage")
end)

test("/login: cancel, failure, expiry and no-answer timeouts", function()
    local w = world()
    local H = join(w, "Host")
    local b = stub_bridge(H)
    w:step(1)
    Sim.cmd(H, "login", "")
    send(H, "login_code", { gi = H.gi, user_code = "ABCD-EFGH", uri = URL, expires = 900 })
    Sim.cmd(H, "login", "cancel")
    check(panel(H) == nil and last(H.chat) == "Login panel closed.", "/login cancel closes it")

    Sim.cmd(H, "login", "")
    send(H, "login_code", { gi = H.gi, user_code = "ABCD-EFGH", uri = URL, expires = 900 })
    send(H, "login_failed", { gi = H.gi, reason = "access_denied" })
    check(panel(H).state == "failed" and Sim.find(H.popups, "denied") ~= nil, "denied: failed panel + popup")
    w:step(1)
    check(Sim.hud_has(H, "NOT LOGGED IN"), "failure drawn")
    w:seconds(6)
    check(panel(H) == nil, "the failure panel goes away by itself")

    Sim.cmd(H, "login", "")
    send(H, "login_code", { gi = H.gi, user_code = "ABCD-EFGH", uri = URL, expires = 2 })
    w:seconds(2.5)
    check(panel(H) ~= nil and panel(H).state == "failed" and panel(H).msg:find("expired") ~= nil, "code expires on the client too")
    w:seconds(6)

    -- a Unix-time `expires` works as well
    Sim.cmd(H, "login", "")
    send(H, "login_code", { gi = H.gi, user_code = "ABCD-EFGH", uri = URL, expires = H.env.get_time() + 600 })
    check(panel(H).frames > 590 * 30 and panel(H).frames <= 600 * 30, "Unix-time expiry -> about 10 minutes")
    Sim.cmd(H, "login", "cancel")

    Sim.cmd(H, "login", "")
    w:seconds(21)
    check(panel(H) ~= nil and panel(H).state == "failed" and panel(H).msg:find("No answer") ~= nil, "no login_code within 20 s: no-answer message")
    w:seconds(6)
    send(H, "login_failed", { gi = H.gi, reason = "expired" })
    check(Sim.find(H.popups, "expired") ~= nil, "login_failed without an open panel still tells the player")
    check(#b.emits == 5, "one login_req per /login (" .. #b.emits .. ")")
end)

test("/link: code check, link_req, no-answer timeout", function()
    local w = world()
    local H = join(w, "Host")
    local b = stub_bridge(H)
    w:step(1)
    Sim.cmd(H, "link", "")
    check(last(H.chat):find("Usage: /link") ~= nil, "no code: usage")
    Sim.cmd(H, "link", "K7Q2X")
    check(last(H.chat):find("Usage: /link") ~= nil and #b.emits == 0, "5 characters: usage")
    Sim.cmd(H, "link", "K7Q2X!")
    check(#b.emits == 0, "punctuation: usage")
    Sim.cmd(H, "link", " k7q-2xf ")
    check(#b.emits == 1 and b.emits[1].t == "link_req" and b.emits[1].fields.code == "K7Q2XF" and b.emits[1].fields.name == "Host",
        "link_req { name, code } with the code normalised")
    check(last(H.chat) == "Linking with code K7Q2XF...", "says it is linking")
    w:seconds(21)
    check(Sim.find(H.chat, "No answer from the login server") ~= nil, "no answer: says so")
    Sim.cmd(H, "link", "K7Q2XF")
    send(H, "login_failed", { gi = H.gi, reason = "bad_code" })
    check(Sim.find(H.popups, "link code is not valid") ~= nil, "bad code: popup")
end)

test("verified: own popup + guest gator, star for everyone, cleared on leave", function()
    local w = world()
    local H = join(w, "Host")
    local F = join(w, "Friend", "josh")
    local G = join(w, "Guest")
    local bh, bf, bg = stub_bridge(H), stub_bridge(F), stub_bridge(G)
    w:step(1)
    Sim.cmd(F, "login", "")
    send(F, "login_code", { gi = F.gi, user_code = "ABCD-EFGH", uri = URL, expires = 900 })
    -- the bridge broadcasts: every client runs the handler
    local cmd = { gi = F.gi, nickname = "Alice", guest_slot = 3 }
    for _, c in ipairs({ H, F, G }) do send(c, "verified", cmd) end
    check(panel(F).state == "ok" and Sim.find(F.popups, "verified as Alice") ~= nil, "Friend: VERIFIED panel + popup")
    check(F.env.gPlayerSyncTable[0].friend == 13 and F.strStorage.friend == "guest_3", "Friend now plays their guest gator (slot 3), remembered")
    check(Sim.find(F.popups, "Your gator .-Guest 3.- is ready") ~= nil, "popup about the guest gator")
    w:step(1)
    check(Sim.hud_has(F, "VERIFIED!") and Sim.hud_has(F, "Welcome, Alice!") and Sim.hud_has(F, "Your gator Guest 3 is ready!"), "success panel drawn")
    check(H.env.gPlayerSyncTable[0].friend == 1 and G.env.gPlayerSyncTable[0].friend == 1, "the others keep their characters")
    check(Sim.find(H.chat, "Friend is verified with Gator Pass") ~= nil, "Host: chat line")
    w:seconds(6)
    check(panel(F) == nil, "success panel closes by itself")

    -- marks: own and seen from the others
    local function li_of(c, gi)
        for i = 0, C.MAX_PLAYERS - 1 do
            if raw(c.nps[i]).connected and raw(c.nps[i]).globalIndex == gi then return i end
        end
    end
    local hf = li_of(H, F.gi)
    check(H.env._G.sglIsVerified(hf) == true and H.env._G.sglIsVerified(0) == false, "Host: Friend verified, Host not")
    check(F.env._G.sglIsVerified(0) == true, "Friend: self verified")
    local tag = nametag(H, hf)
    check(tag == "\\#ffd700\\* \\#dcdcdc\\Friend", "Host: Friend's name tag gets the gold star: " .. tostring(tag))
    check(nametag(H, 0) == nil, "unverified name tags untouched")
    -- Library West hide and seek hides tags: the star must not un-hide one
    local hide = H.env.sgl_libwest_hns_hide_tag
    H.env.sgl_libwest_hns_hide_tag = function() return true end
    H.stubs.gLakituState = {}                                   -- (the hide hook reads it)
    local hidden = nametag(H, hf)
    check(type(hidden) == "table" and hidden.name == "", "a hidden tag stays hidden for a verified player")
    H.env.sgl_libwest_hns_hide_tag = hide
    local np = raw(H.nps[hf])
    check(np.description == "GATOR PASS" and np.descriptionR == 255 and np.descriptionG == 215, "player list description in gold")
    -- charselect name tags: Host opens the menu and turns to the guest page, Friend's tag has the star
    H.env.gPlayerSyncTable[hf].friend = F.env.gPlayerSyncTable[0].friend   -- (sim.lua does not sync player tables)
    Sim.cmd(H, "char", "")
    w:step(12)
    press(w, H, C.R_TRIG)
    check(Sim.hud_has(H, "^%*Friend$"), "charselect: '*Friend' tag on Guest 3's card")
    press(w, H, C.B_BUTTON)
    Sim.cmd(F, "char", "")
    w:step(12)
    check(Sim.hud_has(F, "^%*YOU$"), "charselect: own tag '*YOU'")
    press(w, F, C.B_BUTTON)

    -- already verified
    Sim.cmd(F, "login", "")
    check(last(F.chat) == "You are already verified as Alice.", "/login when verified")
    check(#bf.emits == 1, "no second login_req")

    -- leaving clears it; a new player on the same index is not verified
    w:disconnect(F)
    w:step(2)
    check(H.env._G.sglIsVerified(hf) == false, "Host: mark gone after Friend left")
    check(nametag(H, hf) == nil, "name tag plain again")
    check(#bh.emits == 0 and #bg.emits == 0, "the others sent nothing")
end)

test("verified: no guest slot, unknown slot, broken guest model", function()
    local w = world({})
    w.brokenModels = { guest_5_geo = true }
    local H = join(w, "Host", "anh")
    stub_bridge(H)
    w:step(1)
    send(H, "verified", { gi = H.gi, nickname = "Bob" })
    check(H.env.gPlayerSyncTable[0].friend == 4 and Sim.find(H.popups, "verified as Bob") ~= nil, "no slot: keeps Anh, popup")
    send(H, "verified", { gi = H.gi, nickname = "Bob", guest_slot = 5 })
    check(H.env.gPlayerSyncTable[0].friend == 4 and Sim.find(H.chat, "slot 5%) did not load") ~= nil, "broken guest model: says so, keeps Anh")
    send(H, "verified", { gi = H.gi, nickname = "Bob", guest_slot = 42 })
    check(H.env.gPlayerSyncTable[0].friend == 4 and Sim.find(H.chat, "slot 42%) did not load") ~= nil, "unknown slot: says so")
    send(H, "verified", { gi = H.gi, nickname = "", guest_slot = "2" })
    check(H.env.gPlayerSyncTable[0].friend == 12, "slot as a string (JSON) still works")
    check(Sim.find(H.popups, "verified as Host") ~= nil, "empty nickname: the coopdx name")
    send(H, "verified", { gi = 99, nickname = "Ghost" })
    check(true, "verified for an unknown player does not throw")
end)

print(string.format("\n%d checks passed, %d failed", passed, failed))
if failed > 0 then os.exit(1) end
