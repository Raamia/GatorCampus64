-- name: Super Gatorlator 64
-- incompatible: romhack
-- description: Our school, in Super Mario 64: the real University of Florida campus at true scale, with online co-op and playable friends.\n\nThe hub replaces Castle Grounds; building doors lead into the stages.\nThe Swamp (University Auditorium door) is open from the start; Reitz & Engineering (The Hub door) opens at 2 stars.\n\nL + START or /char: choose your friend. D-pad Up or /join: join your friends' stage act.\nR + START, BOARDS button, or /leaderboard: campus leaderboards.\nAlbert and Alberta roam the game: walk up and type in chat, or /albert and /alberta from anywhere (the host runs tools/npc_bridge/bridge.py).\nChat: /albert, /alberta, /char, /join, /mission, /campus, /school
--
-- Map data (c) OpenStreetMap contributors, ODbL 1.0.
-- Level flow (hub, doors, stages, warp nodes, stars): docs/flow.md, course.lua, levels.lua.
-- (The old "Super Gatorlator 64 loaded" banner is gone: it read like a debug line on the vanilla HUD
-- row. /school still answers, and levels.lua shows where to go next in the hub.)

local sWelcomed = false

local function count_players()
    local count = 0
    for i = 0, MAX_PLAYERS - 1 do
        if gNetworkPlayers[i].connected then
            count = count + 1
        end
    end
    return count
end

local function on_level_init()
    if sWelcomed then return end
    sWelcomed = true
    djui_popup_create("\\#ffd700\\Welcome to Super Gatorlator 64, " .. gNetworkPlayers[0].name .. "!", 2)
end

local function on_school_command()
    djui_chat_message_create("\\#ffd700\\Super Gatorlator 64 is working!\\#dcdcdc\\ Players online: " .. count_players())
    return true
end

hook_event(HOOK_ON_LEVEL_INIT, on_level_init)
hook_chat_command("school", "Check that the Super Gatorlator 64 mod is running", on_school_command)
