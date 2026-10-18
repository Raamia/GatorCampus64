-- Super Gatorlator 64: UF's rivals sneak around campus in place of the Goombas.
-- Every Goomba already looks like a USF Bull (actors/goomba replaces the vanilla goomba_geo); this file swaps
-- individual Goombas to the other rivals' models (actors/rival_<id>, all on the vanilla Goomba skeleton, generated
-- by tools/actors/make_rivals.py). Only the model changes: they walk, charge, get squashed flat when you stomp
-- them (or knocked out by a punch or kick) and drop a coin exactly like Goombas.
--
-- Which rival a Goomba becomes comes from its home position (where it spawned), so every player sees the same
-- mascot on the same Goomba. Each level draws from its own pool (SGL_RIVAL_POOLS): the football rivals at The
-- Swamp, the Miami ibis by Lake Alice, Knights guarding the libraries, a bit of everyone on campus.

SGL_RIVALS = {
    usf = { school = "USF Bulls", mascot = "a bull" },                      -- the default Goomba model
    ucf = { school = "UCF Knights", mascot = "a knight", geo = "rival_ucf_geo" },
    uga = { school = "Georgia Bulldogs", mascot = "a bulldog", geo = "rival_uga_geo" },
    tenn = { school = "Tennessee Volunteers", mascot = "Smokey the hound", geo = "rival_tenn_geo" },
    miami = { school = "Miami Hurricanes", mascot = "Sebastian the ibis", geo = "rival_miami_geo" },
    lsu = { school = "LSU Tigers", mascot = "a tiger", geo = "rival_lsu_geo" },
    fsu = { school = "Florida State Seminoles", mascot = "Renegade the horse", geo = "rival_fsu_geo" },
}

SGL_RIVAL_POOLS = {
    default = { "usf", "ucf", "uga", "tenn", "miami", "lsu", "fsu" },
    [LEVEL_BOB] = { "uga", "fsu", "tenn", "lsu", "usf" },        -- The Swamp: gameday rivals
    [LEVEL_WF] = { "ucf", "usf", "miami", "fsu" },               -- Reitz & Engineering: the in-state schools
    [LEVEL_JRB] = { "miami", "lsu", "usf" },                     -- Lake Alice: the ibis loves a lake
    [LEVEL_CCM] = { "ucf", "usf", "uga" },                       -- Marston: knights in the library
    [LEVEL_BBH] = { "ucf", "lsu", "tenn" },                      -- Library West after dark
}

SGL_RIVAL_SCAN = 5        -- frames between looks for new Goombas

for _, r in pairs(SGL_RIVALS) do
    r.model = E_MODEL_GOOMBA
    if r.geo ~= nil then
        local m = smlua_model_util_get_id(r.geo)
        if m ~= E_MODEL_ERROR_MODEL then r.model = m else r.missing = true end
    end
end

-- the rival for a Goomba that spawned at (x, z) in a level: the same answer on every client
function sgl_rival_for(level, x, z)
    local pool = SGL_RIVAL_POOLS[level] or SGL_RIVAL_POOLS.default
    local h = (math.floor(x) * 73856093 ~ math.floor(z) * 19349663 ~ level * 83492791) & 0x7FFFFFFF
    h = (h * 2654435761) % 4294967296
    return pool[(h >> 7) % #pool + 1]
end

local sScanTimer = 0

local function dress_goombas()
    local level = gNetworkPlayers[0].currLevelNum
    local o = obj_get_first_with_behavior_id(id_bhvGoomba)
    while o ~= nil do
        if obj_has_model_extended(o, E_MODEL_GOOMBA) ~= 0 and (o.oHomeX ~= 0 or o.oHomeZ ~= 0) then
            local r = SGL_RIVALS[sgl_rival_for(level, o.oHomeX, o.oHomeZ)]
            if r ~= nil and r.model ~= E_MODEL_GOOMBA then obj_set_model_extended(o, r.model) end
        end
        o = obj_get_next_with_same_behavior_id(o)
    end
end

local function on_update()
    sScanTimer = sScanTimer - 1
    if sScanTimer > 0 then return end
    sScanTimer = SGL_RIVAL_SCAN
    dress_goombas()
end

local function on_level_init()
    sScanTimer = 0
end

hook_event(HOOK_UPDATE, on_update)
hook_event(HOOK_ON_LEVEL_INIT, on_level_init)
