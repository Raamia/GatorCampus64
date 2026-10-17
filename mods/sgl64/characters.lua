-- Friend characters. Each player picks one with /char <name>; the pick is synced
-- through gPlayerSyncTable so every player sees everyone as the right friend.
-- Models come from actors/<id>/ (Fast64 C export), which DynOS compiles into
-- actors/<id>_geo.bin when the mod loads.

local FRIENDS = {
    { id = "daniel", name = "Daniel" },
    { id = "corina", name = "Corina" },
    { id = "raami", name = "Raami" },
    { id = "anh", name = "Anh" },
    { id = "josh", name = "Josh" },
    { id = "donald", name = "Donald" },
    { id = "jaime", name = "Jaime" },
    { id = "alfred", name = "Alfred" },
    { id = "vignesh", name = "Vignesh" },
    { id = "cher", name = "Cher" },
}

for _, friend in ipairs(FRIENDS) do
    friend.model = smlua_model_util_get_id(friend.id .. "_geo")
end

-- Shared with charselect.lua (the character select menu). sglSetFriend(index) picks a friend for
-- the local player (0 = normal character), returns false when that friend's model failed to load,
-- and calls sglOnFriendSet (charselect.lua) so the pick is remembered for the next session.
_G.sglFriends = FRIENDS
function _G.sglSetFriend(index)
    if index ~= 0 and (FRIENDS[index] == nil or FRIENDS[index].model == E_MODEL_ERROR_MODEL) then
        return false
    end
    gPlayerSyncTable[0].friend = index
    if _G.sglOnFriendSet ~= nil then _G.sglOnFriendSet(index) end
    return true
end

local function find_friend(query)
    query = query:lower()
    for i, friend in ipairs(FRIENDS) do
        if friend.id == query or friend.name:lower() == query then
            return i
        end
    end
    return nil
end

local function friend_list()
    local ids = {}
    for _, friend in ipairs(FRIENDS) do
        table.insert(ids, friend.id)
    end
    return table.concat(ids, ", ")
end

local function on_char_command(msg)
    msg = msg:gsub("^%s+", ""):gsub("%s+$", "")
    if msg == "" then
        if _G.sglOpenCharSelect ~= nil then
            _G.sglOpenCharSelect()
            return true
        end
        djui_chat_message_create("Usage: /char <name> or /char off. Characters: " .. friend_list())
        return true
    end
    if msg:lower() == "off" then
        _G.sglSetFriend(0)
        djui_chat_message_create("Back to your normal character.")
        return true
    end
    local index = find_friend(msg)
    if index == nil then
        djui_chat_message_create("No character named '" .. msg .. "'. Characters: " .. friend_list())
        return true
    end
    if FRIENDS[index].model == E_MODEL_ERROR_MODEL then
        djui_chat_message_create("\\#ff8080\\" .. FRIENDS[index].name .. "'s model failed to load.")
        return true
    end
    _G.sglSetFriend(index)
    djui_chat_message_create("You are now \\#ffd700\\" .. FRIENDS[index].name .. "\\#dcdcdc\\!")
    return true
end

-- coopdx only sets the player model when the base character changes, so switching
-- back from a friend has to restore the base character's model ourselves.
local BASE_MODELS = {
    [CT_MARIO] = E_MODEL_MARIO,
    [CT_LUIGI] = E_MODEL_LUIGI,
    [CT_TOAD] = E_MODEL_TOAD_PLAYER,
    [CT_WALUIGI] = E_MODEL_WALUIGI,
    [CT_WARIO] = E_MODEL_WARIO,
}
local sWasFriend = {}

local function apply_friend_model(m)
    if m.marioObj == nil then return end
    local index = gPlayerSyncTable[m.playerIndex].friend
    local friend = index and FRIENDS[index]
    if friend and friend.model ~= E_MODEL_ERROR_MODEL then
        -- CoopDX can restore the base character model between updates (for example
        -- when an action changes). Keep a render hook on this Mario object so a
        -- one-frame Mario model never reaches the screen.
        m.marioObj.hookRender = 1
        if obj_has_model_extended(m.marioObj, friend.model) == 0 then
            obj_set_model_extended(m.marioObj, friend.model)
        end
        sWasFriend[m.playerIndex] = true
    elseif sWasFriend[m.playerIndex] then
        obj_set_model_extended(m.marioObj, BASE_MODELS[m.character.type] or E_MODEL_MARIO)
        sWasFriend[m.playerIndex] = false
    end
end

local function on_object_render(obj)
    local m = get_mario_state_from_object(obj)
    if m ~= nil and m.marioObj == obj then apply_friend_model(m) end
end

local function on_sync_valid()
    if gPlayerSyncTable[0].friend == nil then
        gPlayerSyncTable[0].friend = 0
    end
end

hook_event(HOOK_MARIO_UPDATE, apply_friend_model)
hook_event(HOOK_ON_OBJECT_RENDER, on_object_render)
hook_event(HOOK_ON_SYNC_VALID, on_sync_valid)
hook_chat_command("char", "[name|off] Play as one of our friends (no name: open the menu)", on_char_command)
