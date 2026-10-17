-- Local-first score outbox for the DeepSpace bridge.
--
-- The game engine has no HTTP client in this mod API. Persist compact TSV-like rows in ModFS; a
-- separate local bridge can watch the saved .modfs archive and submit them with the player's
-- authenticated DeepSpace session. Gameplay never waits for that bridge or a network connection.

SGL_DS_GAME_VERSION = "0.1.0"
SGL_DS_OUTBOX_FILE = "pending_runs.txt"

local function safe_field(value)
    return type(value) == "string" and value:match("^[A-Za-z0-9_.+-]+$") ~= nil
end

function sgl_deepspace_new_run_id()
    local sequence = mod_storage_load_integer("sgl_ds_run_sequence", 0) + 1
    mod_storage_save_integer("sgl_ds_run_sequence", sequence)
    return string.format("sgl_%d_%d", get_global_timer(), sequence)
end

function sgl_deepspace_queue_run(run)
    if type(run) ~= "table" or not safe_field(run.runId) or not safe_field(run.missionId) then return false end
    if type(run.elapsedFrames) ~= "number" or run.elapsedFrames < 1 then return false end
    if type(run.retries) ~= "number" or run.retries < 0 then return false end

    local fs = mod_fs_get() or mod_fs_create()
    if fs == nil then
        log_to_console("[SGL] Could not open ModFS; this run stays local-only.", CONSOLE_MESSAGE_WARNING)
        return false
    end

    local file = fs:get_file(SGL_DS_OUTBOX_FILE) or fs:create_file(SGL_DS_OUTBOX_FILE, true)
    if file == nil then
        log_to_console("[SGL] Could not open the DeepSpace run outbox.", CONSOLE_MESSAGE_WARNING)
        return false
    end
    file:set_text_mode(true)
    if not file:seek(0, FILE_SEEK_END) then return false end
    local assisted = run.assisted and "1" or "0"
    local line = string.format("%s|%s|%d|%d|%s|%s", run.runId, run.missionId,
        math.floor(run.elapsedFrames), math.floor(run.retries), assisted, SGL_DS_GAME_VERSION)
    if not file:write_line(line) then return false end
    if not fs:save() then return false end
    return true
end
