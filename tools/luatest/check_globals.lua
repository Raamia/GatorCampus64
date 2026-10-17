-- Cross-file global check for the mods/sgl64 Lua files, from the compiled bytecode (luac -l), so it
-- sees exactly what the Lua compiler sees: every global READ and WRITE (bare names = _ENV.name, and
-- _G.name), split into load-time code (a file's main chunk) and runtime code (functions).
--
-- coopdx loads a mod's top-level .lua files in strcmp order of their file names (mod.c
-- mod_set_loading_order) into ONE per-mod _ENV table whose __index is the real _G (smlua.c
-- smlua_load_script). So:
--   * a name read in a main chunk must be a coopdx global / Lua std name, or written by an EARLIER file
--     (or earlier in the same file);
--   * a name read at runtime must be written by SOME file (or be a coopdx / std name);
--   * a mod global must not shadow a coopdx function or constant;
--   * two files writing the same global is reported (allowed only for the names in SHARED below).
-- Usage: lua check_globals.lua <mod dir>   (exit 1 on findings). LUAC env var picks the luac binary.
-- Limitation: a main chunk that calls one of its own local functions at load time is only checked
-- for the main chunk's own reads; test_missions.lua's full-mod load (strict globals) covers that.
local HERE = debug.getinfo(1, "S").source:match("^@(.*/)") or "./"
local API = dofile(HERE .. "coopdx_api_v151.lua")
local LUAC = os.getenv("LUAC") or "luac"

local C = setmetatable({}, { __index = _G })
C.get_time = function() return 0 end
C.table_copy = function(t) return t end
C.table_deepcopy = function(t) return t end
C._set_sync_table_field = function() end
assert(loadfile(HERE .. "coopdx_constants_v151.lua", "t", C))()

-- engine globals exposed by smlua (docs/lua/globals.md, v1.5.1) + per-mod sync tables
local ENGINE = {
    gMarioStates = true, gNetworkPlayers = true, gActiveMods = true, gCharacters = true, gControllers = true,
    gMatStack = true, gMatStackPrev = true, gTextures = true, gObjectAnimations = true,
    gGlobalObjectCollisionData = true, gLakituState = true, gServerSettings = true, gNametagsSettings = true,
    gHudDisplay = true, gLevelValues = true, gBehaviorValues = true, gGlobalSyncTable = true,
    gPlayerSyncTable = true, gGlobalSoundSource = true, gFirstPersonCamera = true, gPaintingValues = true,
    gGlobalObjectAnimations = true, gDialogs = true, _G = true,
}
-- Lua 5.3-era standard names (coopdx embeds 5.3-style Lua; nothing 5.4+-only such as warn)
local STD = {}
for n in ([[assert error ipairs next pairs pcall print rawequal rawget rawlen rawset select setmetatable
    getmetatable tonumber tostring type xpcall string table math utf8 os coroutine debug require
    _VERSION]]):gmatch("%S+") do STD[n] = true end

-- names deliberately written by more than one file (none today)
local SHARED = {}

local function external(n)
    return STD[n] or ENGINE[n] or API[n] ~= nil or rawget(C, n) ~= nil
end

local dir = arg[1] or (HERE .. "../../mods/sgl64")
local files = {}
local p = io.popen('ls "' .. dir .. '"/*.lua')
for f in p:lines() do files[#files + 1] = f end
p:close()
table.sort(files, function(a, b) return a:match("[^/]+$") < b:match("[^/]+$") end)   -- strcmp order

-- per file: list of { name, write, main, line }
local function accesses(path)
    local h = io.popen(LUAC .. ' -l -o /dev/null "' .. path .. '" 2>&1')
    local out = h:read("a")
    h:close()
    -- ops whose A operand is NOT a destination register (stores, tests, jumps, returns)
    local KEEP_A = {}
    for o in ("SETFIELD SETTABLE SETI SETUPVAL SETTABUP SETLIST RETURN RETURN0 RETURN1 TEST JMP EQ LT LE EQK "
        .. "EQI LTI LEI GTI GEI MMBIN MMBINI MMBINK TFORCALL TFORLOOP FORLOOP FORPREP TFORPREP CLOSE TBC"):gmatch("%u+") do
        KEEP_A[o] = true
    end
    local list, main, gReg = {}, false, {}
    for line in out:gmatch("[^\n]+") do
        if line:match("^main <") then
            main, gReg = true, {}
        elseif line:match("^function <") then
            main, gReg = false, {}
        else
            local ln, op, rest = line:match("^%s*%d+%s+%[(%d+)%]%s+(%u+)%s+(.*)$")
            if op ~= nil then
                local a, b = rest:match("^(%-?%d+)%s+(%-?%d+)")
                a, b = tonumber(a), tonumber(b)
                local name = rest:match('; _ENV "([%w_]+)"')
                if op == "GETTABUP" and name ~= nil then
                    if name == "_G" then
                        gReg[a] = true
                    else
                        gReg[a] = nil
                        list[#list + 1] = { name = name, write = false, main = main, line = tonumber(ln) }
                    end
                elseif op == "SETTABUP" and name ~= nil then
                    list[#list + 1] = { name = name, write = true, main = main, line = tonumber(ln) }
                elseif op == "SETFIELD" and gReg[a] then          -- _G.name = v  /  function _G.name()
                    local f = rest:match('; "([%w_]+)"')
                    if f then list[#list + 1] = { name = f, write = true, main = main, line = tonumber(ln), viaG = true } end
                elseif op == "GETFIELD" and gReg[b] then          -- v = _G.name
                    local f = rest:match('; "([%w_]+)"')
                    if f then list[#list + 1] = { name = f, write = false, main = main, line = tonumber(ln), viaG = true } end
                    gReg[a] = nil
                elseif a ~= nil and not KEEP_A[op] then
                    gReg[a] = nil
                end
            end
        end
    end
    if out:match("^luac:") then error(out) end
    return list
end

local findings, notes = {}, {}
local writer = {}        -- name -> { file index, line } of the first write (load order)
local writers = {}       -- name -> set of file names
local perFile = {}
for i, path in ipairs(files) do
    perFile[i] = accesses(path)
    for _, a in ipairs(perFile[i]) do
        if a.write then
            local base = path:match("[^/]+$")
            writers[a.name] = writers[a.name] or {}
            writers[a.name][base] = true
            if writer[a.name] == nil then writer[a.name] = { i = i, line = a.line, main = a.main } end
        end
    end
end

for i, path in ipairs(files) do
    local base = path:match("[^/]+$")
    for _, a in ipairs(perFile[i]) do
        local n = a.name
        if not a.write and not external(n) then
            local w = writer[n]
            if w == nil then
                findings[#findings + 1] = string.format("%s:%d reads global '%s' that no mod file assigns and coopdx does not have", base, a.line, n)
            elseif a.main and (w.i > i or (w.i == i and w.line > a.line) or not w.main) then
                findings[#findings + 1] = string.format("%s:%d reads '%s' at LOAD time, but it is only assigned %s (%s:%d)",
                    base, a.line, n, w.main and "later in the load order" or "inside a function", files[w.i]:match("[^/]+$"), w.line)
            end
        end
    end
end

for n, set in pairs(writers) do
    if API[n] ~= nil or (rawget(C, n) ~= nil and type(rawget(C, n)) ~= "nil") then
        findings[#findings + 1] = string.format("mod global '%s' shadows a coopdx %s", n, API[n] ~= nil and "function" or "constant")
    end
    local names = {}
    for f in pairs(set) do names[#names + 1] = f end
    table.sort(names)
    if #names > 1 and not SHARED[n] then
        findings[#findings + 1] = string.format("global '%s' is assigned by several files: %s", n, table.concat(names, ", "))
    end
end

-- summary: which file provides which cross-file globals
local cross = 0
for i, path in ipairs(files) do
    local base = path:match("[^/]+$")
    local used = {}
    for _, a in ipairs(perFile[i]) do
        local w = writer[a.name]
        if not a.write and w ~= nil and w.i ~= i then used[files[w.i]:match("[^/]+$")] = (used[files[w.i]:match("[^/]+$")] or 0) + 1 end
    end
    local parts = {}
    for f, k in pairs(used) do parts[#parts + 1] = f .. " x" .. k end
    table.sort(parts)
    cross = cross + #parts
    notes[#notes + 1] = string.format("  %-20s uses %s", base, #parts > 0 and table.concat(parts, ", ") or "(no other mod file)")
end

table.sort(findings)
for _, f in ipairs(findings) do print("FAIL " .. f) end
print(string.format("check_globals: %d file(s) in coopdx load order: %s", #files,
    (function() local t = {} for _, f in ipairs(files) do t[#t + 1] = f:match("[^/]+$") end return table.concat(t, " < ") end)()))
for _, n in ipairs(notes) do print(n) end
if #findings > 0 then
    print(#findings .. " finding(s)")
    os.exit(1)
end
print("check_globals: OK (every global read resolves; load-time reads only use earlier files)")
