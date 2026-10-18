-- Offline test of mods/sgl64/sgl_rivals.lua: UF's rivals replace the Goombas. Every Goomba gets a rival model
-- picked from its home position and its level's pool (the same on every client), keeps it while it walks around,
-- and stays a USF Bull (the default goomba_geo) when a rival's model failed to load. Run: lua tools/luatest/test_rivals.lua
local HERE = debug.getinfo(1, "S").source:match("^@(.*/)") or "./"
local Sim = dofile(HERE .. "sim.lua")
local C = Sim.C
local raw = Sim.raw

local passed, failed = 0, 0
local current = "?"
local function check(cond, what)
    if cond then passed = passed + 1 else failed = failed + 1 print("  FAIL [" .. current .. "] " .. what) end
    return cond
end
local function test(name, fn)
    current = name
    local before = failed
    local ok, err = xpcall(fn, debug.traceback)
    if not ok then failed = failed + 1 print("  ERROR [" .. name .. "] " .. tostring(err)) end
    print((failed == before and "PASS " or "FAIL ") .. name)
end

local function setup(opts)
    local w = Sim.new({ files = Sim.ALL_FILES, built = Sim.built_on_disk() })
    w.brokenModels = opts and opts.broken
    local H, F = w:connect("Host"), w:connect("Friend")
    w:warp(H, C.LEVEL_BOB, 1, 1)
    w:warp(F, C.LEVEL_BOB, 1, 1)
    w:step(5)
    return w, H, F
end

test("the Knight ghost replaces the Boo model", function()
    local w, H = setup()
    check(H.env.SGL_KNIGHT_GHOST_MODEL ~= nil and H.env.SGL_KNIGHT_GHOST_MODEL ~= C.E_MODEL_BOO, "a Knight ghost model")
    local w2, H2 = setup({ broken = { knight_ghost_geo = true } })
    check(rawget(H2.env, "SGL_KNIGHT_GHOST_MODEL") == nil, "no model: nil, so the missions keep the Boo")
end)

local function spawn_goombas(c, n)
    local out = {}
    for i = 1, n do
        local x, z = 1000 + 437 * i, -2000 + 911 * (i % 7)
        table.insert(out, c.env.spawn_non_sync_object(C.id_bhvGoomba, C.E_MODEL_GOOMBA, x, 0, z, nil))
    end
    return out
end

local function rival_of(c, o)
    for id, r in pairs(c.env.SGL_RIVALS) do
        if r.model == raw(o)._model then return id end
    end
    return nil
end

test("every Goomba becomes its home's rival, the same on both clients, from the level's pool", function()
    local w, H, F = setup()
    local hg, fg = spawn_goombas(H, 40), spawn_goombas(F, 40)
    w:step(H.env.SGL_RIVAL_SCAN + 1)
    local seen, same = {}, true
    local pool = {}
    for _, id in ipairs(H.env.SGL_RIVAL_POOLS[C.LEVEL_BOB] or H.env.SGL_RIVAL_POOLS.default) do pool[id] = true end
    for i = 1, #hg do
        local a, b = rival_of(H, hg[i]), rival_of(F, fg[i])
        local want = H.env.sgl_rival_for(C.LEVEL_BOB, raw(hg[i]).oHomeX, raw(hg[i]).oHomeZ)
        check(a == want, "goomba " .. i .. " is " .. tostring(want) .. " (got " .. tostring(a) .. ")")
        check(pool[a] == true, "goomba " .. i .. ": " .. tostring(a) .. " is in The Swamp's pool")
        if a ~= b then same = false end
        seen[a] = (seen[a] or 0) + 1
    end
    check(same, "both clients dress the same Goomba as the same rival")
    local kinds = 0
    for _ in pairs(seen) do kinds = kinds + 1 end
    check(kinds == 2, "Bulls and Seminoles both appear in The Swamp (" .. kinds .. " kinds)")
end)

test("a rival keeps its look while it wanders", function()
    local w, H = setup()
    local g = spawn_goombas(H, 12)
    w:step(H.env.SGL_RIVAL_SCAN + 1)
    local before = {}
    for i, o in ipairs(g) do before[i] = raw(o)._model end
    for _, o in ipairs(g) do raw(o).oPosX = raw(o).oPosX + 777 end
    w:step(3 * H.env.SGL_RIVAL_SCAN)
    for i, o in ipairs(g) do check(raw(o)._model == before[i], "goomba " .. i .. " kept its model") end
end)

test("every rival has a model and a school; a missing model leaves a USF Bull", function()
    local w, H = setup()
    for id, r in pairs(H.env.SGL_RIVALS) do
        check(type(r.school) == "string" and type(r.mascot) == "string", id .. ": school and mascot")
        check(r.model ~= nil and (id == "usf") == (r.model == C.E_MODEL_GOOMBA), id .. ": its own model (usf: the Goomba's)")
    end
    for lvl, pool in pairs(H.env.SGL_RIVAL_POOLS) do
        for _, id in ipairs(pool) do check(H.env.SGL_RIVALS[id] ~= nil, tostring(lvl) .. ": known rival " .. id) end
    end
    local w2, H2 = setup({ broken = { rival_fsu_geo = true } })
    local g = spawn_goombas(H2, 10)
    w2:step(H2.env.SGL_RIVAL_SCAN + 1)
    for i, o in ipairs(g) do check(raw(o)._model == C.E_MODEL_GOOMBA, "goomba " .. i .. " stays a bull") end
end)

print(string.format("%d checks passed, %d failed", passed, failed))
if failed > 0 then os.exit(1) end
