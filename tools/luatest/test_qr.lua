-- Offline tests for mods/sgl64/sgl_qr.lua (the vendored speedata/luaqrcode QR encoder + HUD draw helper).
-- Known vectors:
--   * "HELLO WORLD", version 1-M: the data + Reed-Solomon codewords published in the thonky.com QR
--     tutorial (an independent encoder), byte for byte;
--   * the Gator Pass activate URL, version 5-M: the full 37 x 37 module matrix, checked once with an
--     independent decoder (zbarimg 0.23: renders and decodes back to the URL) and pinned here;
--   * structure of every code: finder patterns, timing lines, a format word that is a valid BCH
--     codeword with the requested EC level, version = (size - 17) / 4.
-- Run: tools/luatest/run.sh   (or: lua tools/luatest/test_qr.lua)
local HERE = debug.getinfo(1, "S").source:match("^@(.*/)") or "./"
local MOD = os.getenv("SGL_MOD_DIR") or (HERE .. "../../mods/sgl64/")

local passed, failed = 0, 0
local function check(cond, what)
    if cond then passed = passed + 1 else failed = failed + 1; print("  FAIL " .. what) end
    return cond
end

-- load sgl_qr.lua the way coopdx does: its own _ENV, no io / os / require / load / dofile
local draws = {}
local env = setmetatable({
    djui_hud_set_color = function(r, g, b, a)
        for _, v in ipairs({ r, g, b, a }) do assert(math.type(v) == "integer" and v >= 0 and v <= 255, "colour ints") end
        draws.color = r
    end,
    djui_hud_render_rect = function(x, y, w, h)
        draws[#draws + 1] = { x = x, y = y, w = w, h = h, color = draws.color }
    end,
}, {
    __index = function(_, k)
        if k == "io" or k == "os" or k == "require" or k == "load" or k == "loadfile" or k == "dofile" then
            error("sgl_qr.lua uses '" .. k .. "' (not in coopdx's sandbox)", 2)
        end
        return _G[k]
    end,
})
assert(loadfile(MOD .. "sgl_qr.lua", "t", env))()

---------------------------------------------------------------------------------------------
-- 1. codewords of HELLO WORLD 1-M (thonky.com: data analysis, encoding, error correction pages)
local cw, version, ec = env.sgl_qr_codewords("HELLO WORLD", 2)
check(version == 1 and ec == 2, "HELLO WORLD at M is version 1")
check(table.concat(cw, " ") == "32 91 11 120 209 114 220 77 67 64 236 17 236 17 236 17 196 35 39 119 235 215 231 226 93 23",
    "HELLO WORLD 1-M data + EC codewords: " .. table.concat(cw, " "))

---------------------------------------------------------------------------------------------
-- 2. structure checks for any code
local FORMAT_MASK = 0x5412
local function bch_ok(word)
    -- format info: 15 bits, generator 0x537 (x^10 + x^8 + x^5 + x^4 + x^2 + x + 1)
    local v = word
    for i = 14, 10, -1 do
        if (v >> i) & 1 == 1 then v = v ~ (0x537 << (i - 10)) end
    end
    return v == 0
end

local function structure(qr, wantEc, label)
    local n, d = qr.size, qr.dark
    check(n == 17 + 4 * qr.version, label .. ": size matches the version")
    -- finder patterns (7x7 rings) in three corners
    local function finder(x0, y0)
        for y = 0, 6 do
            for x = 0, 6 do
                local ring = math.max(math.abs(x - 3), math.abs(y - 3))
                if d[y0 + y][x0 + x] ~= (ring ~= 2) then return false end
            end
        end
        return true
    end
    check(finder(1, 1) and finder(n - 6, 1) and finder(1, n - 6), label .. ": three finder patterns")
    -- timing lines on row / column 7 (0-based 6)
    local timing = true
    for i = 9, n - 8 do
        if d[7][i] ~= (i % 2 == 1) or d[i][7] ~= (i % 2 == 1) then timing = false end
    end
    check(timing, label .. ": timing patterns")
    check(d[n - 7][9] == true, label .. ": the dark module")
    -- format word, copy 1: (row 8, cols 0..5, 7, 8) then (rows 7, 5..0 of col 8), MSB first
    local bits = {}
    for x = 0, 5 do bits[#bits + 1] = d[9][x + 1] end
    bits[#bits + 1] = d[9][8]
    bits[#bits + 1] = d[9][9]
    bits[#bits + 1] = d[8][9]
    for y = 5, 0, -1 do bits[#bits + 1] = d[y + 1][9] end
    local word = 0
    for _, b in ipairs(bits) do word = (word << 1) | (b and 1 or 0) end
    check(bch_ok(word ~ FORMAT_MASK), label .. ": format word (unmasked) is a BCH codeword")
    local info = (word ~ FORMAT_MASK) >> 10
    local ecBits = { [1] = 1, [2] = 0, [3] = 3, [4] = 2 }   -- L 01, M 00, Q 11, H 10
    check(info >> 3 == ecBits[wantEc], label .. ": format word says EC level " .. wantEc)
    -- copy 2 (bottom-left column 8 + top-right row 8) agrees
    local bits2 = {}
    for y = n - 1, n - 7, -1 do bits2[#bits2 + 1] = d[y + 1][9] end
    for x = n - 8, n - 1 do bits2[#bits2 + 1] = d[9][x + 1] end
    local word2 = 0
    for _, b in ipairs(bits2) do word2 = (word2 << 1) | (b and 1 or 0) end
    check(word2 == word, label .. ": both format copies agree")
end

---------------------------------------------------------------------------------------------
-- 3. the activate URL at M: pinned matrix (decoded by zbarimg when it was pinned)
local URL = "https://login.chooseyourgator.select/activate?user_code=ABCD-EFGH"
local GOLDEN = {
    "1111111010010001001100101010101111111",
    "1000001000001100000011100110001000001",
    "1011101001000000011111010000101011101",
    "1011101010111101101100010111101011101",
    "1011101010101110001001010111101011101",
    "1000001011000001001111101010101000001",
    "1111111010101010101010101010101111111",
    "0000000010111000111010100010100000000",
    "1000101111001111001000101100011111001",
    "1011010010110110100110000010100011010",
    "0010101111100010100011100111001110100",
    "0110010101110010011001001011110111110",
    "1001001100110111110111110000011101111",
    "1010010010011101110000110111100011000",
    "0111111000111011001011111011110111100",
    "1011000011010111100011011000001110110",
    "1101001011111101100110001011011011111",
    "0110010001111010001100101010100011110",
    "1110001000010101011101010111001010000",
    "1100100101111101110111110011001000110",
    "0011001101000010011011110001011101100",
    "1110000101000001101001010001000110010",
    "0111001000110001110010011011101111100",
    "1001000111100011011100101010001110100",
    "0011011011010100001100111101111001101",
    "1110100011000010110111000111000011000",
    "0011101000100000101010011101000100100",
    "0010110101111010011001001011001100100",
    "1101111101110011110101101000111111101",
    "0000000011100011111000110110100010000",
    "1111111010011111001001111010101010000",
    "1000001001001100100111010010100011111",
    "1011101010000000100010011100111111111",
    "1011101000100100001100100111011100001",
    "1011101001100001010100110011011000000",
    "1000001001101011111111101011000010110",
    "1111111010100110010011000001001100111",
}
local qr = env.sgl_qr_encode(URL, 2)
check(qr ~= nil and qr.version == 5 and qr.size == 37, "activate URL (" .. #URL .. " chars) at M: version 5")
if qr ~= nil then
    local same = true
    for y = 1, qr.size do
        local row = {}
        for x = 1, qr.size do row[x] = qr.dark[y][x] and "1" or "0" end
        if table.concat(row) ~= GOLDEN[y] then
            same = false
            print("    row " .. y .. " got  " .. table.concat(row) .. "\n           want " .. GOLDEN[y])
        end
    end
    check(same, "activate URL matrix matches the pinned (zbarimg-decoded) one")
    structure(qr, 2, "activate URL 5-M")
end

---------------------------------------------------------------------------------------------
-- 4. a ~90-character verification_uri_complete fits version 5-6 at L and M
local LONG = "https://login.chooseyourgator.select/activate?user_code=WXYZ-QRST&from=sgl64&player=SomeName1234"
for ecl = 1, 2 do
    local q = env.sgl_qr_encode(LONG, ecl)
    check(q ~= nil and q.version >= 5 and q.version <= 6, #LONG .. "-char URL at EC " .. ecl .. ": version 5-6 (got " .. tostring(q and q.version) .. ")")
    if q then structure(q, ecl, #LONG .. "-char URL EC " .. ecl) end
end
local auto = env.sgl_qr_encode(LONG)
check(auto ~= nil and auto.version == 5, "no EC level given: smallest version")
local none, err = env.sgl_qr_encode("")
check(none == nil and type(err) == "string", "empty string: nil + error")
local huge, err2 = env.sgl_qr_encode(string.rep("x", 4000))
check(huge == nil and type(err2) == "string", "too long for any version: nil + error, no throw")

---------------------------------------------------------------------------------------------
-- 5. drawing: white square incl. the quiet zone first, then black runs covering exactly the dark modules
if qr ~= nil then
    local total = env.sgl_qr_draw(qr, 10, 20, 3, 4)
    check(total == (37 + 8) * 3, "draw returns the full width incl. quiet zone")
    local bg = draws[1]
    check(bg ~= nil and bg.color == 255 and bg.x == 10 and bg.y == 20 and bg.w == total and bg.h == total, "white backing + quiet zone first")
    local area, darkCount, inside = 0, 0, true
    for i = 2, #draws do
        local r = draws[i]
        area = area + r.w * r.h
        if r.color ~= 0 or r.h ~= 3 or r.x < 10 + 12 or r.y < 20 + 12 or r.x + r.w > 10 + 12 + 37 * 3 then inside = false end
    end
    for y = 1, 37 do for x = 1, 37 do if qr.dark[y][x] then darkCount = darkCount + 1 end end end
    check(inside, "black runs are one module tall and inside the code area")
    check(area == darkCount * 9, "black runs cover exactly the dark modules")
    check(#draws - 1 < darkCount / 2, "runs merged (" .. (#draws - 1) .. " rects for " .. darkCount .. " dark modules)")
end

print(string.format("\n%d checks passed, %d failed", passed, failed))
if failed > 0 then os.exit(1) end
