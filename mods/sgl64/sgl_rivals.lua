-- GatorCampus 64: UF's rivals sneak around campus. USF Bulls and FSU Seminoles replace the Goombas, and UCF
-- Knight ghosts replace the Boos of Library West (SGL_KNIGHT_GHOST_MODEL, used by uf_west_library_missions.lua).
-- Every Goomba already looks like a USF Bull (actors/goomba replaces the vanilla goomba_geo); this file swaps
-- individual Goombas to the Seminole (actors/rival_fsu: a garnet rival with a gold spear-tip crest). Both are on the
-- vanilla Goomba skeleton (tools/actors/make_rivals.py), and only the model changes: they walk, charge, get
-- squashed flat when you stomp them (or knocked out by a punch or kick) and drop a coin exactly like Goombas.
--
-- Which rival a Goomba becomes comes from its home position (where it spawned), so every player sees the same
-- mascot on the same Goomba.

SGL_RIVALS = {
    usf = { school = "USF Bulls", mascot = "a bull" },                      -- the default Goomba model
    fsu = { school = "Florida State Seminoles", mascot = "a spear-crested Seminole", geo = "rival_fsu_geo" },
}

SGL_RIVAL_POOLS = {
    default = { "usf", "fsu" },
}

-- the Knight ghost (the Boos' stand-in), or nil when its model failed to load (the missions fall back to the Boo)
SGL_KNIGHT_GHOST_MODEL = smlua_model_util_get_id("knight_ghost_geo")
if SGL_KNIGHT_GHOST_MODEL == E_MODEL_ERROR_MODEL then SGL_KNIGHT_GHOST_MODEL = nil end

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
