import json
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

from sglbridge.inbox import Inbox, build_modfs, check_filepath, is_text, modfs_path, read_modfs

MOD_LUA = Path(__file__).resolve().parents[3] / "mods" / "sgl64" / "sgl_bridge.lua"


def test_modfs_path():
    assert modfs_path("/srv/sgl") == Path("/srv/sgl/sav/sgl64.modfs")


def test_round_trip_and_properties():
    data = build_modfs({"inbox.json": b'{"seq":0,"cmds":[]}'})
    files, props = read_modfs(data)
    assert files == {"inbox.json": b'{"seq":0,"cmds":[]}'}
    # the same shape mod_fs_write produces (mod_fs_get_properties_json)
    assert props == {"isPublic": False,
                     "files": {"inbox.json": {"isText": True, "isPublic": False, "compressionLevel": 1}}}
    with zipfile.ZipFile(__import__("io").BytesIO(data)) as zf:
        names = [i.filename for i in zf.infolist()]
        assert names == ["inbox.json", "properties.json"]          # no directory entries
        assert zf.testzip() is None
        assert all(i.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED) for i in zf.infolist())


def test_filepath_rules_match_mod_fs():
    for ok in ("inbox.json", "a/b.txt", "noext"):
        check_filepath(ok)
    for bad in ("", "properties.json", "/a.json", "a/", "a//b.json", "a\\b.json", "a*.json", "x.lua", "café.json"):
        with pytest.raises(ValueError):
            check_filepath(bad)


def test_text_detection():
    assert is_text(b'{"a": "b"}\n\t')
    assert not is_text(b"\x00abc")


def test_inbox_push_sequence_and_atomic_write(tmp_path):
    p = tmp_path / "sav" / "sgl64.modfs"
    inbox = Inbox(p)
    assert inbox.push("login_code", gi=1, user_code="ABCD-EFGH", uri="https://x/activate?user_code=ABCD-EFGH",
                      expires=900) == 1
    assert inbox.push("verified", gi=1, nickname="Al", guest_slot=None) == 2
    files, _ = read_modfs(p.read_bytes())
    raw = files["inbox.json"]
    raw.decode("ascii")                                              # ASCII only (text mode detection)
    doc = json.loads(raw)
    assert doc["seq"] == 2
    assert doc["cmds"][0] == {"seq": 1, "t": "login_code", "gi": 1, "user_code": "ABCD-EFGH",
                              "uri": "https://x/activate?user_code=ABCD-EFGH", "expires": 900}
    assert doc["cmds"][1] == {"seq": 2, "t": "verified", "gi": 1, "nickname": "Al"}     # None -> absent
    assert sorted(x.name for x in p.parent.iterdir()) == ["sgl64.modfs"]                 # no temp files left


def test_inbox_rejects_tables(tmp_path):
    with pytest.raises(TypeError):
        Inbox(tmp_path / "x.modfs").push("announce", text=["no"])


def test_inbox_reset_keeps_seq_and_prunes(tmp_path, clock):
    inbox = Inbox(tmp_path / "x.modfs", max_cmds=3, max_age=60, clock=clock)
    for i in range(5):
        inbox.push("announce", text=str(i))
    doc = inbox.document()
    assert [c["seq"] for c in doc["cmds"]] == [3, 4, 5] and doc["seq"] == 5
    clock.t += 61
    assert inbox.document()["cmds"] == []
    inbox.push("announce", text="x")
    inbox.reset()
    assert inbox.document() == {"seq": 6, "cmds": []}
    assert inbox.push("announce", text="y") == 7


def test_non_ascii_text_is_escaped(tmp_path):
    p = tmp_path / "x.modfs"
    Inbox(p).push("announce", text="Gator café ✓")
    raw = read_modfs(p.read_bytes())[0]["inbox.json"]
    assert b"\\u00e9" in raw and json.loads(raw)["cmds"][0]["text"] == "Gator café ✓"


@pytest.mark.skipif(shutil.which("lua") is None, reason="lua not installed")
def test_lua_decoder_reads_the_inbox(tmp_path):
    """Cross-check: the mod's own decoder (sgl_bridge.lua) parses what the bridge writes."""
    p = tmp_path / "x.modfs"
    inbox = Inbox(p)
    inbox.push("login_code", gi=3, user_code="ABCD-EFGH", uri="https://login.x/activate?user_code=ABCD-EFGH",
               page="https://login.x/activate", expires=900)
    inbox.push("announce", text='New gator "Al\\" café', secs=60)
    raw = read_modfs(p.read_bytes())[0]["inbox.json"]
    (tmp_path / "inbox.json").write_bytes(raw)
    script = f"""
local env = setmetatable({{ hook_event = function() end, gServerSettings = {{}} }}, {{ __index = _G }})
assert(loadfile({json.dumps(str(MOD_LUA))}, "t", env))()
local f = io.open({json.dumps(str(tmp_path / "inbox.json"))}, "rb"); local s = f:read("a"); f:close()
local doc = env.sgl_json_decode(s)
io.write(doc.seq, "|", #doc.cmds, "|", doc.cmds[1].t, "|", doc.cmds[1].user_code, "|", math.type(doc.cmds[1].gi),
    "|", doc.cmds[2].text)
"""
    out = subprocess.run(["lua", "-e", script], capture_output=True, check=True).stdout
    assert out.decode("utf-8") == '2|2|login_code|ABCD-EFGH|integer|New gator "Al\\" café'
