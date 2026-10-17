r"""Dump the level scripts inside a compiled DynOS .lvl (pure Python).

Usage: python3 tools/blender/dump_lvl.py <file.lvl> [script_name ...]
  e.g. python3 tools/blender/dump_lvl.py \
         ~/Library/Application\ Support/sm64coopdx/mods/sgl64/levels/level_sgl_test_entry.lvl
Reads both compressed ("DYNOSBIN" + zlib) and plain .lvl files, finds every LEVEL_SCRIPT node
and prints its commands (pointers as names, Lua variables as their token, built-in functions
as indices). Handy to confirm what DynOS actually compiled (warp nodes, spawn objects, Lua
names) or to study the bundled mods' levels (arena, star-road).
"""
import re, struct, sys, zlib

FUNC, PNTR, LUAV = 0x434E5546, 0x52544E50, 0x5641554C
NAMES = {0x00:'EXECUTE',0x02:'EXIT',0x03:'SLEEP',0x04:'SLEEP_BEFORE_EXIT',0x05:'JUMP',0x06:'JUMP_LINK',0x07:'RETURN',
 0x0A:'LOOP_BEGIN',0x0B:'LOOP_UNTIL',0x0C:'JUMP_IF',0x11:'CALL',0x12:'CALL_LOOP',0x1B:'INIT_LEVEL',0x1C:'CLEAR_LEVEL',
 0x1D:'ALLOC_LEVEL_POOL',0x1E:'FREE_LEVEL_POOL',0x1F:'AREA',0x20:'END_AREA',0x21:'LOAD_MODEL_FROM_DL',0x22:'LOAD_MODEL_FROM_GEO',
 0x24:'OBJECT',0x25:'MARIO',0x26:'WARP_NODE',0x27:'PAINTING_WARP_NODE',0x28:'INSTANT_WARP',0x2B:'MARIO_POS',0x2E:'TERRAIN',
 0x2F:'ROOMS',0x30:'SHOW_DIALOG',0x31:'TERRAIN_TYPE',0x36:'SET_BACKGROUND_MUSIC',0x37:'SET_MENU_MUSIC',0x38:'STOP_MUSIC',
 0x39:'MACRO_OBJECTS',0x3F:'OBJECT_EXT',0x40:'OBJECT_EXT2',0x41:'LOAD_MODEL_FROM_GEO_EXT',0x42:'JUMP_AREA_EXT',0x43:'OBJECT_EXT_LUA_PARAMS',0x44:'SHOW_DIALOG_EXT'}

def load(path):
    d = open(path, 'rb').read()
    if d[:8] == b'DYNOSBIN':
        d = zlib.decompress(d[16:])
    return d

def read_word(d, i):
    v = struct.unpack_from('<I', d, i)[0]; i += 4
    if v == PNTR:
        n = d[i]; name = d[i+1:i+1+n].decode(); i += 1 + n
        off = struct.unpack_from('<I', d, i)[0]; i += 4
        return ('PTR', name + (f'+{off}' if off else '')), i
    if v == LUAV:
        n = d[i]; name = d[i+1:i+1+n].decode(); i += 1 + n
        return ('LUA', name), i
    if v == FUNC:
        idx = struct.unpack_from('<i', d, i)[0]; i += 4
        return ('FUNC', idx), i
    return ('U32', v), i

def dump(d, name):
    key = bytes([12, len(name)]) + name.encode()
    pos = d.find(key)
    if pos < 0:
        return False
    i = pos + len(key)
    size = struct.unpack_from('<I', d, i)[0]; i += 4
    words = []
    for _ in range(size):
        w, i = read_word(d, i); words.append(w)
    print(f'== {name} ({size} words)')
    k = 0
    while k < len(words):
        w = words[k]
        if w[0] != 'U32':
            print('   ?', w); k += 1; continue
        t, sz = w[1] & 0xFF, (w[1] >> 8) & 0xFF
        n = max(1, sz // 4)
        args = [w[1] >> 16 & 0xFF, w[1] >> 24 & 0xFF]
        rest = []
        for x in words[k+1:k+n]:
            rest.append(x[1] if x[0] != 'U32' else hex(x[1]))
        print(f'   {NAMES.get(t, hex(t)):24s} b2={args[0]:#x} b3={args[1]:#x} {rest}')
        k += n
    return True

if __name__ == '__main__':
    d = load(sys.argv[1])
    names = sys.argv[2:] or sorted(set(m.decode() for m in re.findall(rb'\x0c.([a-z_][a-z0-9_]{3,60})', d)))
    for nm in names:
        dump(d, nm)
