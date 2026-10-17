-- Static check of mod Lua files against sm64coopdx v1.5.1 without running the game:
--   * every global function a file CALLS is defined by one of the checked files, the Lua std lib,
--     the constants prelude, or a v1.5.1 binding (coopdx_api_v151.lua);
--   * calls to bindings pass an argument count the C binding accepts (e.g. spawn_non_sync_object
--     needs exactly 6, djui_hud_print_text 4 or 5);
--   * ALL_CAPS constants, id_bhv* / id_* ids and g* engine globals that are READ exist in coopdx
--     (or are defined by the checked files).
-- Usage: lua check_api.lua <file.lua> [more.lua ...]   (pass every file of the mod: they share globals)
-- Exit status 1 on any finding.
local HERE = debug.getinfo(1, "S").source:match("^@(.*/)") or "./"
local API = dofile(HERE .. "coopdx_api_v151.lua")

local C = setmetatable({}, { __index = _G })
C.get_time = function() return 0 end
C.table_copy = function(t) return t end
C.table_deepcopy = function(t) return t end
C._set_sync_table_field = function() end
assert(loadfile(HERE .. "coopdx_constants_v151.lua", "t", C))()

-- engine globals (docs/lua/globals.md, v1.5.1) + hook functions bound by smlua_hooks.c
local ENGINE_GLOBALS = {
    gMarioStates = true, gNetworkPlayers = true, gActiveMods = true, gCharacters = true, gControllers = true,
    gMatStack = true, gMatStackPrev = true, gTextures = true, gObjectAnimations = true,
    gGlobalObjectCollisionData = true, gLakituState = true, gServerSettings = true, gNametagsSettings = true,
    gHudDisplay = true, gLevelValues = true, gBehaviorValues = true, gGlobalSyncTable = true,
    gPlayerSyncTable = true, gGlobalSoundSource = true, gFirstPersonCamera = true, gPaintingValues = true,
    gGlobalObjectAnimations = true, gDialogs = true,
}

local LUA_STD = {}
for k in pairs(_G) do LUA_STD[k] = true end

---------------------------------------------------------------------------------------------
-- tokenizer (identifiers, strings, numbers, punctuation; comments dropped)
---------------------------------------------------------------------------------------------
local function tokenize(src)
    local toks = {}
    local i, n, line = 1, #src, 1
    local function push(t, v) toks[#toks + 1] = { t = t, v = v, line = line } end
    while i <= n do
        local c = src:sub(i, i)
        if c == "\n" then
            line = line + 1
            i = i + 1
        elseif c:match("%s") then
            i = i + 1
        elseif src:sub(i, i + 1) == "--" then
            local lvl = src:match("^%[(=*)%[", i + 2)
            if lvl then
                local close = "]" .. lvl .. "]"
                local e = src:find(close, i, true) or n
                for _ in src:sub(i, e):gmatch("\n") do line = line + 1 end
                i = e + #close
            else
                local e = src:find("\n", i, true) or (n + 1)
                i = e
            end
        elseif c == "[" and src:match("^%[=*%[", i) then
            local lvl = src:match("^%[(=*)%[", i)
            local close = "]" .. lvl .. "]"
            local e = src:find(close, i, true) or n
            for _ in src:sub(i, e):gmatch("\n") do line = line + 1 end
            push("str", "")
            i = e + #close
        elseif c == '"' or c == "'" then
            local j = i + 1
            while j <= n do
                local d = src:sub(j, j)
                if d == "\\" then
                    if src:sub(j + 1, j + 1) == "\n" then line = line + 1 end
                    j = j + 2
                elseif d == c then
                    break
                else
                    if d == "\n" then line = line + 1 end
                    j = j + 1
                end
            end
            push("str", src:sub(i + 1, j - 1))
            i = j + 1
        elseif c:match("[%a_]") then
            local w = src:match("^[%w_]+", i)
            push("id", w)
            i = i + #w
        elseif c:match("%d") or (c == "." and src:sub(i + 1, i + 1):match("%d")) then
            local num = src:match("^0[xX][%x%.]+", i) or src:match("^%d*%.?%d+[eE][%+%-]?%d+", i)
                or src:match("^%d*%.?%d*", i)
            push("num", num)
            i = i + math.max(#num, 1)
        else
            local three, two = src:sub(i, i + 2), src:sub(i, i + 1)
            if three == "..." then
                push("op", three); i = i + 3
            elseif two == "==" or two == "~=" or two == "<=" or two == ">=" or two == ".." or two == "::"
                or two == "//" or two == "<<" or two == ">>" then
                push("op", two); i = i + 2
            else
                push("op", c); i = i + 1
            end
        end
    end
    return toks
end

local KEYWORDS = {}
for w in ("and break do else elseif end false for function goto if in local nil not or repeat return then true until while"):gmatch("%a+") do
    KEYWORDS[w] = true
end

---------------------------------------------------------------------------------------------
-- pass 1: names the files define (globals, locals, params, loop vars, fields are ignored)
---------------------------------------------------------------------------------------------
local defined = {}
local files = {}
for _, path in ipairs(arg) do
    local f = assert(io.open(path, "r"))
    local src = f:read("a")
    f:close()
    local toks = tokenize(src)
    files[#files + 1] = { path = path, toks = toks }
    for k, t in ipairs(toks) do
        local prev, nxt = toks[k - 1], toks[k + 1]
        if t.t == "id" and not KEYWORDS[t.v] then
            local afterDot = prev and prev.t == "op" and (prev.v == "." or prev.v == ":")
            if not afterDot then
                -- function NAME / local function NAME / local NAME[, NAME] / NAME = (statement start)
                if prev and prev.t == "id" and (prev.v == "function" or prev.v == "local") then defined[t.v] = true end
                if nxt and nxt.t == "op" and nxt.v == "=" then defined[t.v] = true end
                if prev and prev.t == "op" and prev.v == "," then
                    -- a, b = ... / local a, b / function(a, b) / for k, v in
                    defined[t.v] = true
                end
                if prev and prev.t == "op" and prev.v == "(" then
                    -- parameter lists: function(NAME / function name(NAME
                    local p2 = toks[k - 2]
                    local p3 = toks[k - 3]
                    if (p2 and p2.t == "id" and p2.v == "function") or (p3 and p3.t == "id" and p3.v == "function") then
                        defined[t.v] = true
                    end
                end
                if prev and prev.t == "id" and prev.v == "for" then defined[t.v] = true end
            end
        end
    end
end

---------------------------------------------------------------------------------------------
-- pass 2: calls and constant reads
---------------------------------------------------------------------------------------------
local findings = 0
local function report(file, line, msg)
    findings = findings + 1
    print(string.format("%s:%d: %s", file, line, msg))
end

local function count_args(toks, k)
    -- toks[k] is "(" of the call; returns the number of top-level arguments
    local depth, block, args, any = 0, 0, 0, false
    local j = k
    while j <= #toks do
        local t = toks[j]
        if t.t == "op" and (t.v == "(" or t.v == "{" or t.v == "[") then
            depth = depth + 1
        elseif t.t == "op" and (t.v == ")" or t.v == "}" or t.v == "]") then
            depth = depth - 1
            if depth == 0 then return any and args + 1 or 0, j end
        elseif t.t == "id" and (t.v == "function" or t.v == "if" or t.v == "do" or t.v == "repeat") then
            block = block + 1
        elseif t.t == "id" and (t.v == "end" or t.v == "until") then
            block = block - 1
        elseif depth == 1 and block == 0 and t.t == "op" and t.v == "," then
            args = args + 1
        end
        if j > k and depth >= 1 then any = true end
        j = j + 1
    end
    return -1, j
end

for _, file in ipairs(files) do
    local toks = file.toks
    local short = file.path:match("[^/]+$")
    for k, t in ipairs(toks) do
        if t.t == "id" and not KEYWORDS[t.v] then
            local prev, nxt = toks[k - 1], toks[k + 1]
            local afterDot = prev and prev.t == "op" and (prev.v == "." or prev.v == ":")
            local isDef = prev and prev.t == "id" and (prev.v == "function" or prev.v == "local")
            if not afterDot and not isDef then
                local name = t.v
                if nxt and nxt.t == "op" and nxt.v == "(" then
                    if not defined[name] and not LUA_STD[name] and C[name] == nil then
                        if API[name] == nil then
                            report(short, t.line, "call to unknown function '" .. name .. "' (not a coopdx v1.5.1 API)")
                        else
                            local n = count_args(toks, k + 1)
                            local lo, hi = API[name][1], API[name][2]
                            if lo >= 0 and n >= 0 and (n < lo or n > hi) then
                                report(short, t.line, string.format("%s(...) with %d argument(s); the v1.5.1 binding takes %s",
                                    name, n, lo == hi and tostring(lo) or (lo .. "-" .. hi)))
                            end
                        end
                    end
                elseif not defined[name] and not (nxt and nxt.t == "op" and nxt.v == "=") then
                    local constLike = name:match("^[A-Z][A-Z0-9_]+$") or name:match("^id_") or name:match("^g[A-Z]")
                    if constLike and C[name] == nil and not ENGINE_GLOBALS[name] and API[name] == nil then
                        report(short, t.line, "unknown constant / global '" .. name .. "'")
                    end
                end
            end
        end
    end
end

if findings == 0 then
    print(string.format("check_api: %d file(s) OK against sm64coopdx v1.5.1", #files))
end
os.exit(findings == 0 and 0 or 1)
