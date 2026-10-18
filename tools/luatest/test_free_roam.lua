-- Physical entrances must be usable with zero stars and never auto-start missions.
local HERE = debug.getinfo(1, 'S').source:match('^@(.*/)')
local Sim = dofile(HERE .. 'sim.lua')
local C = Sim.C
local script = assert(Sim.level_script('castle_grounds'))
local count = 0
for _, door in ipairs(script.objects) do
    if door.bhv == 'id_bhvSglDoor' then
        local w = Sim.new({ files = Sim.ALL_FILES, built = Sim.built_on_disk() })
        local c = w:connect('Host')
        c.cam = { zoomed_in_dist = 900, zoomed_out_dist = 1400, zoomed_in_height = 300, zoomed_out_height = 450, collisions = 0 }
        for f in pairs(c.cam) do
            c.stubs['camera_romhack_get_' .. f] = function() return c.cam[f] end
            c.stubs['camera_romhack_set_' .. f] = function(v) c.cam[f] = v end
        end
        w:warp(c, C.LEVEL_CASTLE_GROUNDS, 1, 0)
        w:step(30)
        c.pressed = C.A_BUTTON
        w:step(25)
        local stage = c.env.sgl_stage_by_door((door.bparams >> 24) & 0xff)
        assert(stage.stars == 0)
        assert(c.env.sgl_total_stars() == 0)
        if Sim.level_script(stage.slot) then
            local yaw = math.floor(door.ry * 65536 / 360)
            local a = yaw / 65536 * 2 * math.pi
            c.pos.x = door.x + math.sin(a) * 80
            c.pos.y = door.y
            c.pos.z = door.z + math.cos(a) * 80
            c.face.y = (yaw + 0x8000) & 0xffff
            w:step(4)
            assert(c.level == stage.level, stage.slot .. ': door did not enter')
            assert(c.act == 0, stage.slot .. ': door started mission act')
            w:step(90)
            assert(c.env.sgl_mission_get(c.level, c.act) == nil, stage.slot .. ': free roam mission')
            assert(#c.starSpawns == 0, stage.slot .. ': free roam spawned reward')
            assert(not Sim.hud_has(c, 'COMING SOON'))
            count = count + 1
        end
    end
end
assert(count == 5)
print('Free roam: all five built entrances accept zero stars; no automatic mission or reward')
