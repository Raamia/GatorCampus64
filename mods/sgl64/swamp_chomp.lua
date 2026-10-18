-- GatorCampus 64: GATOR CHOMP CHORUS, the SOLO rhythm game (Swamp act 3, LEVEL_BOB).
-- With 2+ players in the act the co-op chorus of swamp_missions.lua runs unchanged (corner buttons,
-- GA... TOR... CHOMP!). ALONE (the mission waits for a study buddy) this Simon-style game runs instead:
-- 4 pads in the north end zone; the pads play a phrase (each lights up with its own sound on a steady
-- beat), then READY... GO! and the player repeats it: jump + Z (ground-pound) on each pad in order.
-- A wrong pad / a pound before GO! / no pound within NOTE_TIME: "WRONG PAD" / "TOO EARLY" / "TOO LATE",
-- the same phrase again (no lives). Practice (1 note), then phrases of 2, 3, 4 notes -> "GATOR GREAT!",
-- a grade by misses, and the act's star through the normal mission path (SUCCESS, star spawned once).
-- B plays again (for fun, no second star). Local scratch only (ctx.loc.solo): alone = the leader.
-- Loads after sgl_mission.lua and before swamp_missions.lua (file names sort alphabetically).
-- Docs: docs/gator_chomp_chorus.md. Tests: tools/luatest/test_missions.lua ("act 3 solo").

SGL_CHOMP = {
    beat = 24,          -- frames per played note (0.8 s)
    litFrames = 16,     -- a played pad stays lit this long
    countFrames = 20,   -- READY..., then GO! (frames each)
    noteTime = 75,      -- frames to land the next pound after GO! / the last hit (2.5 s: a jump + Z)
    feedbackFrames = 45,
    introFrames = 120,
    padRadius = 200,    -- xz hit radius of a pad (game units)
    padScale = 1.0,     -- purple switch scale (the corner buttons are 1.5)
    -- practice, then the rounds (pad numbers 1..4); B replays rotate the pads
    phrases = { { 2 }, { 1, 3 }, { 4, 2, 3 }, { 1, 4, 2, 3 } },
    sounds = { SOUND_OBJ_BUBBA_CHOMP, SOUND_GENERAL_BIG_POUND, SOUND_GENERAL_BREAK_BOX, SOUND_MENU_COLLECT_RED_COIN },
}

local CH = SGL_CHOMP
local PH_INTRO, PH_PLAY, PH_COUNT, PH_INPUT, PH_FEEDBACK, PH_WIN = 1, 2, 3, 4, 5, 6

local function alive(o, id)
    if o == nil or o.activeFlags == ACTIVE_FLAG_DEACTIVATED then return false end
    local r = obj_has_behavior_id(o, id)
    return r == true or r == 1
end

local function hide(o, hidden)
    local flags = o.header.gfx.node.flags
    if hidden then
        o.header.gfx.node.flags = flags | GRAPH_RENDER_INVISIBLE
    else
        o.header.gfx.node.flags = flags & ~GRAPH_RENDER_INVISIBLE
    end
end

-- the pad under p (1..4) or nil
local function pad_at(pads, p)
    for i, b in ipairs(pads) do
        local dx, dz = p.x - b.x, p.z - b.z
        if dx * dx + dz * dz <= CH.padRadius * CH.padRadius and p.y >= b.y - 100 and p.y <= b.y + 400 then return i end
    end
    return nil
end

local function grade(misses)
    if misses == 0 then return "A+" elseif misses == 1 then return "A" elseif misses <= 3 then return "B" end
    return "C"
end

-- solo runs while I am alone in the act and the co-op chorus waits (or after my solo win, for replays)
local function solo_on(ctx)
    if ctx.n ~= 1 or ctx.dormant then return false end
    if ctx.s == SGL_MS_WAITING then return true end
    local S = ctx.loc.solo
    return S ~= nil and S.won and (ctx.s == SGL_MS_SUCCESS or ctx.s == SGL_MS_DONE)
end

local function note(S, k)
    local p = CH.phrases[S.k][k]
    return ((p - 1 + S.rot) % 4) + 1
end

local function go(S, phase)
    S.ph, S.t = phase, 0
end

local function new_solo(rot, won)
    return { ph = PH_INTRO, t = 0, k = 1, i = 1, misses = 0, rot = rot or 0, won = won or false,
        lit = 0, flash = 0, flashPad = 0, msg = nil, ok = false, lastAct = 0 }
end

local function fail(S, msg)
    S.misses = S.misses + 1
    S.msg, S.ok = msg, false
    play_sound(SOUND_MENU_CAMERA_BUZZ, gGlobalSoundSource)
    go(S, PH_FEEDBACK)
end

local function solo_tick(ctx, pads)
    local S = ctx.loc.solo
    if S == nil then S = new_solo(); ctx.loc.solo = S end
    S.t = S.t + 1
    if S.flash > 0 then S.flash = S.flash - 1 end
    local m = gMarioStates[0]
    local landed = m.action == ACT_GROUND_POUND_LAND and S.lastAct ~= ACT_GROUND_POUND_LAND
    S.lastAct = m.action
    local hit = landed and pad_at(pads, m.pos) or nil
    local phrase = CH.phrases[S.k]

    if S.ph == PH_INTRO then
        if S.t >= CH.introFrames then go(S, PH_PLAY) end
    elseif S.ph == PH_PLAY then
        local k = 1 + (S.t - 1) // CH.beat
        local inBeat = (S.t - 1) % CH.beat
        if k > #phrase then
            S.lit = 0
            go(S, PH_COUNT)
            play_sound(SOUND_GENERAL2_SWITCH_TICK_FAST, gGlobalSoundSource)
        else
            local pad = note(S, k)
            S.lit = inBeat < CH.litFrames and pad or 0
            if inBeat == 0 then play_sound(CH.sounds[pad], gGlobalSoundSource) end
        end
    elseif S.ph == PH_COUNT then
        if hit ~= nil then
            fail(S, "TOO EARLY")
        elseif S.t >= 2 * CH.countFrames then
            S.i = 1
            go(S, PH_INPUT)
            play_sound(SOUND_GENERAL_RACE_GUN_SHOT, gGlobalSoundSource)
        elseif S.t == CH.countFrames then
            play_sound(SOUND_GENERAL2_SWITCH_TICK_FAST, gGlobalSoundSource)
        end
    elseif S.ph == PH_INPUT then
        if hit ~= nil then
            if hit == note(S, S.i) then
                play_sound(CH.sounds[hit], gGlobalSoundSource)
                S.flash, S.flashPad = 12, hit
                S.i = S.i + 1
                S.t = 0
                if S.i > #phrase then
                    S.msg, S.ok = "NICE!", true
                    play_sound(SOUND_GENERAL2_RIGHT_ANSWER, gGlobalSoundSource)
                    go(S, PH_FEEDBACK)
                end
            else
                fail(S, "WRONG PAD")
            end
        elseif S.t >= CH.noteTime then
            fail(S, "TOO LATE")
        end
    elseif S.ph == PH_FEEDBACK then
        if S.t >= CH.feedbackFrames then
            if S.ok then
                if S.k >= #CH.phrases then
                    go(S, PH_WIN)
                    play_sound(SOUND_MENU_STAR_SOUND, gGlobalSoundSource)
                    play_sound(SOUND_MENU_COLLECT_SECRET, gGlobalSoundSource)
                    -- Albert (at the swamp_chorus post in act 3) does the Gator Chomp (sgl_npc.lua, local anim)
                    local byId = rawget(_ENV, "sgl_npc_by_id")
                    local albert = byId ~= nil and byId("albert") or nil
                    if albert ~= nil then albert.chomp = 96 end
                    if not S.won then
                        S.won = true
                        -- the act's star, through the normal mission path (spawned once by star_tick)
                        if ctx.isLeader and ctx.s == SGL_MS_WAITING then ctx:setState(SGL_MS_SUCCESS) end
                    end
                    return
                end
                S.k = S.k + 1
            end
            go(S, PH_PLAY)
        end
    elseif S.ph == PH_WIN then
        if (m.controller.buttonPressed & B_BUTTON) ~= 0 then
            ctx.loc.solo = new_solo(S.rot + 1, true)
        end
    end
end

-- pads: { {x, y, z}, ... } (4). Wraps the co-op buttons kind K: same act, same star.
function sgl_swamp_chomp_kind(coop, pads)
    local K = {}
    for k, v in pairs(coop) do K[k] = v end
    K.chompPads = pads

    K.spawnLocal = function(ctx)
        if coop.spawnLocal ~= nil then coop.spawnLocal(ctx) end
        ctx.objs.pads = {}
        for i, b in ipairs(pads) do
            local o = spawn_non_sync_object(id_bhvSglButton, E_MODEL_PURPLE_SWITCH, b.x, b.y, b.z,
                function(obj) obj_scale(obj, CH.padScale) end)
            local fx = spawn_non_sync_object(id_bhvSglMissionFx, E_MODEL_RED_FLAME, b.x, b.y + 160, b.z,
                function(obj) obj_scale(obj, 3) end)
            ctx.objs.pads[i] = { o = o, fx = fx }
        end
    end

    K.localTick = function(ctx)
        if coop.localTick ~= nil then coop.localTick(ctx) end
        local on = solo_on(ctx)
        if on then
            solo_tick(ctx, pads)
        elseif ctx.loc.solo ~= nil and not ctx.loc.solo.won then
            ctx.loc.solo = nil      -- a study buddy arrived: the co-op chorus takes over
        end
        local S = on and ctx.loc.solo or nil
        for i, rec in ipairs(ctx.objs.pads or {}) do
            if alive(rec.o, id_bhvSglButton) then
                local squish = (S ~= nil and S.flash > 0 and S.flashPad == i) and SGL_BUTTON_PRESSED_Y or CH.padScale
                obj_scale_xyz(rec.o, CH.padScale, squish, CH.padScale)
                hide(rec.o, S == nil)
            end
            if alive(rec.fx, id_bhvSglMissionFx) then
                -- watch = orange flame on the playing pad; your turn = small blue flames; correct = big blue
                local model, scl = nil, 3
                if S ~= nil and S.ph == PH_PLAY and S.lit == i then
                    model = E_MODEL_RED_FLAME
                elseif S ~= nil and S.flash > 0 and S.flashPad == i then
                    model, scl = E_MODEL_BLUE_FLAME, 4
                elseif S ~= nil and S.ph == PH_INPUT then
                    model, scl = E_MODEL_BLUE_FLAME, 1.5
                end
                if model ~= nil then
                    if rec.model ~= model then obj_set_model_extended(rec.fx, model); rec.model = model end
                    obj_scale(rec.fx, scl)
                end
                hide(rec.fx, model == nil)
            end
        end
    end

    K.waitingText = function(ctx)
        if solo_on(ctx) then return "Solo Gator Chomp - a study buddy makes it the co-op chorus" end
        return nil
    end

    K.hud = function(ctx)
        if coop.hud ~= nil then coop.hud(ctx) end
        if not solo_on(ctx) or ctx.loc.solo == nil then return end
        local S = ctx.loc.solo
        local m = gMarioStates[0]
        local cx = djui_hud_get_screen_width() / 2
        local nPh = #CH.phrases
        local label = S.k == 1 and "PRACTICE" or string.format("ROUND %d/%d", S.k - 1, nPh - 1)
        sgl_hud_text_center("GATOR CHOMP CHORUS - SOLO   " .. label .. "   misses: " .. S.misses, cx, 40, 0.35, SGL_HUD_GOLD, 1)
        if S.ph == PH_INTRO then
            sgl_hud_text_center("Watch the pads, then repeat: jump + ground-pound (Z) on the lit pad", cx, 120, 0.4, SGL_HUD_WHITE, 1)
            sgl_hud_marker({ x = pads[2].x, y = pads[2].y + 300, z = pads[2].z }, "CHOMP PADS", SGL_HUD_ORANGE, m)
        elseif S.ph == PH_PLAY then
            sgl_hud_big("WATCH", SGL_HUD_ORANGE, 2)
            if S.lit ~= 0 then
                local b = pads[S.lit]
                sgl_hud_marker({ x = b.x, y = b.y + 250, z = b.z }, "PAD " .. S.lit, SGL_HUD_ORANGE, m)
            end
        elseif S.ph == PH_COUNT then
            sgl_hud_big(S.t < CH.countFrames and "READY..." or "SET...", SGL_HUD_BLUE, 2)
        elseif S.ph == PH_INPUT then
            sgl_hud_big(S.i == 1 and S.t < 20 and "GO!" or "YOUR TURN", SGL_HUD_BLUE, 2)
            sgl_hud_text_center(string.format("Pad %d of %d - jump + Z", S.i, #CH.phrases[S.k]), cx, 120, 0.4, SGL_HUD_WHITE, 1)
        elseif S.ph == PH_FEEDBACK then
            sgl_hud_big(S.msg or "", S.ok and SGL_HUD_GREEN or SGL_HUD_RED, 2.4)
            if not S.ok then sgl_hud_text_center("Same phrase again - watch!", cx, 120, 0.4, SGL_HUD_WHITE, 1) end
        elseif S.ph == PH_WIN then
            sgl_hud_big("GATOR GREAT!", SGL_HUD_GOLD, 2.6)
            sgl_hud_text_center("Grade " .. grade(S.misses) .. "   (misses: " .. S.misses .. ")   Press B to play again", cx, 120, 0.4, SGL_HUD_WHITE, 1)
        end
    end
    return K
end
