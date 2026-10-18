import io
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

from sglbridge.api import ApiUnavailable
from sglbridge.deploy import (DEFAULT_RENAME_TOOL, DeployError, DeployLoop, clean_name, extract_zip,
                              render_guests_lua, snapshot_placeholders, stage_build)
from sglbridge.inbox import Inbox, read_modfs

# stand-in for server/worker/actor_rename.py (same CLI: <src actor dir> <dst actors dir> <new id>)
FAKE_RENAME = '''
import os, sys
src, dst, new = sys.argv[1:4]
old = os.path.basename(os.path.normpath(src))
if open(os.path.join(src, "geo.inc.c")).read().startswith("BROKEN"):
    sys.exit("geo.inc.c: 'sglguest' still present after rename")
os.makedirs(os.path.join(dst, new), exist_ok=True)
for n in os.listdir(src):
    text = open(os.path.join(src, n)).read().replace(old + "_", new + "_")
    open(os.path.join(dst, new, n), "w").write(text)
print(os.path.join(dst, new))
'''

BUILD = {
    "actors/sglguest/geo.inc.c": "const GeoLayout sglguest_geo[] = {};",
    "actors/sglguest/model.inc.c": "Gfx mat_sglguest_skin[] = {};",
    "actors/sglguest/geo_header.h": "extern const GeoLayout sglguest_geo[];",
    "portrait.png": b"\x89PNG portrait",
    "character.json": json.dumps({"id": "sglguest", "name": "Albert"}),
    "previews/front.png": b"\x89PNG front",
    "manifest.json": "{}",
}


@pytest.fixture
def rename_tool(tmp_path):
    p = tmp_path / "actor_rename.py"
    p.write_text(FAKE_RENAME)
    return p


def write_build(root, files=BUILD):
    for rel, data in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(data if isinstance(data, bytes) else data.encode())
    return root


def zip_of(files, wrapper=""):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for rel, data in files.items():
            zf.writestr(wrapper + rel, data)
    return buf.getvalue()


def test_stage_build_renames_actor_and_portrait(tmp_path, rename_tool):
    dl = write_build(tmp_path / "dl")
    info = stage_build(dl, 3, tmp_path / "st", rename_tool)
    assert info == {"actor_from": "sglguest", "portrait": True}
    geo = (tmp_path / "st/actors/guest_3/geo.inc.c").read_text()
    assert "guest_3_geo" in geo and "sglguest" not in geo
    assert (tmp_path / "st/textures/sgl_portrait_guest_3.png").read_bytes() == b"\x89PNG portrait"
    assert json.loads((tmp_path / "st/character.json").read_text())["id"] == "guest_3"


def test_stage_build_failures(tmp_path, rename_tool):
    with pytest.raises(DeployError, match="one actor"):
        stage_build(write_build(tmp_path / "a", {"portrait.png": b"x"}), 3, tmp_path / "sa", rename_tool)
    with pytest.raises(DeployError, match="actor_rename failed"):
        broken = dict(BUILD, **{"actors/sglguest/geo.inc.c": "BROKEN"})
        stage_build(write_build(tmp_path / "b", broken), 3, tmp_path / "sb", rename_tool)
    with pytest.raises(DeployError, match="bad slot"):
        stage_build(write_build(tmp_path / "c"), 9, tmp_path / "sc", rename_tool)
    with pytest.raises(DeployError, match="rename tool missing"):
        stage_build(write_build(tmp_path / "d"), 3, tmp_path / "sd", tmp_path / "nope.py")


@pytest.mark.skipif(not DEFAULT_RENAME_TOOL.exists(), reason="server/worker/actor_rename.py not merged here")
def test_stage_build_with_the_real_rename_tool(tmp_path):
    stage_build(write_build(tmp_path / "dl"), 2, tmp_path / "st")
    assert "guest_2_geo" in (tmp_path / "st/actors/guest_2/geo.inc.c").read_text()


def test_extract_zip_safety(tmp_path):
    extract_zip(zip_of(BUILD, wrapper="build-77/"), tmp_path / "ok")
    assert (tmp_path / "ok/actors/sglguest/geo.inc.c").exists()
    with pytest.raises(DeployError):
        extract_zip(zip_of({"../../etc/passwd": "x"}), tmp_path / "bad")
    with pytest.raises(DeployError):
        extract_zip(b"not a zip", tmp_path / "bad2")


def test_guests_lua(tmp_path):
    lua = render_guests_lua({2: {"name": 'Al "the" \\gator\\ with a long name', "owner": "auth0|1"}})
    assert lua.count("sgl_guests_register({") == 1 and lua.rstrip().endswith("})")
    assert '    { slot = 1, name = "Guest 1", owner = nil },' in lua
    assert '    { slot = 2, name = "Al \\"the\\" gat", owner = "auth0|1" },' in lua
    assert lua.count("slot =") == 8
    if shutil.which("lua"):
        prelude = "function sgl_guests_register(t) G = t end\n"
        (tmp_path / "guests.lua").write_text(prelude + lua + "io.write(G[2].name, '|', #G, '|', tostring(G[1].owner))\n")
        r = subprocess.run(["lua", str(tmp_path / "guests.lua")], capture_output=True)
        assert r.returncode == 0, r.stderr
        assert r.stdout.decode() == 'Al "the" gat|8|nil'


def test_clean_name_matches_characters_lua():
    # characters.lua guest_name: colour codes, non-printables and backslashes out, trim, 12 chars, rtrim
    assert clean_name("\\#ff0000\\Evil\tName That Is Far Too Long", 4) == "EvilName Tha"
    assert clean_name("  caf\u00e9 \\o/  ", 1) == "caf o/"
    assert clean_name("Twelve chars x", 2) == "Twelve chars"
    assert clean_name("abcdefghijk  z", 2) == "abcdefghijk"
    assert clean_name("   ", 6) == clean_name(None, 6) == "Guest 6"


def test_guests_lua_placeholders_match_the_checked_in_file():
    """The empty-roster render is the checked-in mods/sgl64/guests.lua's register call, line for line
    (the mod's format, spec 5.2). tools/luatest/test_login.lua loads a render in the Lua sim."""
    checked_in = (Path(__file__).resolve().parents[3] / "mods/sgl64/guests.lua").read_text()

    def call(text):
        return text[text.index("\nsgl_guests_register({") + 1:].rstrip()   # the call, not the comment

    assert call(render_guests_lua({})) == call(checked_in)


class FakeApi:
    def __init__(self, pending, blobs):
        self.pending = pending
        self.blobs = blobs
        self.reports = []
        self.downloads = []
        self.current = None

    def pending_deploys(self):
        out, self.pending = self.pending, []
        return out

    def reconcile_deploys(self, installed):
        pass

    def check_deploys(self, ids):
        return set(ids) if self.current is None else set(self.current)

    def download(self, url):
        self.downloads.append(url)
        b = self.blobs[url]
        if isinstance(b, Exception):
            raise b
        return b

    def report_deploy(self, deploy_id, status, detail=""):
        self.reports.append((deploy_id, status))


class FakeGame:
    def __init__(self, mod_dir):
        self.mod_dir = mod_dir
        self.restarts = 0
        self.stopped = False

    def stop(self):
        self.stopped = True

    def restart(self, during=None):
        self.restarts += 1
        during()


def file_deploy(did, slot, name, prefix="u", owner="auth0|9"):
    files = [{"path": rel, "url": f"{prefix}/{rel}"} for rel in BUILD]
    blobs = {f"{prefix}/{rel}": (d if isinstance(d, bytes) else d.encode()) for rel, d in BUILD.items()}
    return {"id": did, "slot": slot, "kind": "character", "name": name, "owner_sub": owner, "files": files}, blobs


def make_loop(tmp_path, clock, api, rename_tool, players=0):
    mod = tmp_path / "mod"
    (mod / "actors/guest_3").mkdir(parents=True)
    (mod / "actors/guest_3/geo.inc.c").write_text("// placeholder")
    (mod / "actors/guest_3/old_only.c").write_text("stale")
    (mod / "actors/guest_3_geo.bin").write_bytes(b"old")
    shipped = tmp_path / "shipped"
    (shipped / "actors/guest_5").mkdir(parents=True)
    (shipped / "actors/guest_5/geo.inc.c").write_text("// shipped placeholder 5")
    game = FakeGame(mod)
    inbox = Inbox(tmp_path / "sav/sgl64.modfs", clock=clock)
    online = {"n": players}

    def wait(s):
        clock.t += s
        if clock.t > 1030:
            online["n"] = 0                                  # everyone left after 30 s
        return False
    loop = DeployLoop(api, inbox, game, mod, tmp_path / "state/roster.json", lambda: online["n"],
                      placeholder_mod=shipped, rename_tool=rename_tool, clock=clock, wait=wait)
    return loop, game, inbox, mod


def test_deploy_batch_installs_and_reports(tmp_path, clock, rename_tool):
    d, blobs = file_deploy(11, 3, "Albert")
    bad = {"id": 12, "slot": 4, "kind": "character", "name": "Broken",
           "files": [{"path": "portrait.png", "url": "p"}]}
    api = FakeApi([d, bad, {"id": 13, "slot": 5, "kind": "placeholder"}], dict(blobs, p=b"x"))
    loop, game, inbox, mod = make_loop(tmp_path, clock, api, rename_tool)
    assert loop.tick() == [11, 13]
    assert api.reports == [(12, "failed"), (11, "deployed"), (13, "deployed")]
    assert not any("previews/" in u for u in api.downloads)        # previews are not fetched
    assert game.restarts == 1
    assert "guest_3_geo" in (mod / "actors/guest_3/geo.inc.c").read_text()
    assert not (mod / "actors/guest_3/old_only.c").exists()
    assert not (mod / "actors/guest_3_geo.bin").exists()           # DynOS recompiles it
    assert (mod / "textures/sgl_portrait_guest_3.png").read_bytes() == b"\x89PNG portrait"
    assert (mod / "actors/guest_5/geo.inc.c").read_text() == "// shipped placeholder 5"
    assert not (mod / "character.json").exists()
    guests = (mod / "guests.lua").read_text()
    assert '{ slot = 3, name = "Albert", owner = "auth0|9" },' in guests
    assert '{ slot = 5, name = "Guest 5", owner = nil },' in guests
    assert json.loads((tmp_path / "state/roster.json").read_text())["3"]["name"] == "Albert"
    assert inbox.document()["cmds"] == []                          # nobody online: no announcement


def test_announce_and_restart_gap(tmp_path, clock, rename_tool):
    d, blobs = file_deploy(1, 3, "Al")
    api = FakeApi([d], blobs)
    loop, game, inbox, mod = make_loop(tmp_path, clock, api, rename_tool, players=2)
    t0 = clock.t
    assert loop.tick() == [1]
    ann = json.loads(read_modfs(inbox.path.read_bytes())[0]["inbox.json"])["cmds"][0]
    assert ann["t"] == "announce" and ann["secs"] == 60 and "New gator Al arrives in 60 s" in ann["text"]
    assert 30 <= clock.t - t0 <= 32                                # waited until the server emptied
    d2, _ = file_deploy(2, 3, "Bo")
    api.pending = [d2]
    assert loop.tick() == [] and game.restarts == 1                # within 5 min of the last restart
    clock.t += 300
    api.pending = [d2]
    assert loop.tick() == [2] and game.restarts == 2


def test_zip_artifacts_url_still_supported(tmp_path, clock, rename_tool):
    api = FakeApi([{"id": 7, "slot": 3, "name": "Zed", "artifacts_url": "z"}], {"z": zip_of(BUILD)})
    loop, game, _, mod = make_loop(tmp_path, clock, api, rename_tool)
    assert loop.tick() == [7]
    assert "guest_3_geo" in (mod / "actors/guest_3/geo.inc.c").read_text()


def test_placeholder_snapshot_taken_once_and_restored(tmp_path, clock, rename_tool):
    d, blobs = file_deploy(1, 3, "Al")
    api = FakeApi([d], blobs)
    loop, game, _, mod = make_loop(tmp_path, clock, api, rename_tool)
    (mod / "textures").mkdir(exist_ok=True)
    (mod / "textures/sgl_portrait_guest_3.png").write_bytes(b"donald portrait")
    loop.prepare()                                                  # first start: pristine copy of guest_3
    snap = loop.snapshot_dir
    assert (snap / "actors/guest_3/geo.inc.c").read_text() == "// placeholder"
    assert loop.tick() == [1]                                       # a character replaces guest_3
    assert snapshot_placeholders(mod, snap, loop.load_roster()) == []   # never re-snapshotted
    clock.t += 301
    api.pending = [{"id": 2, "slot": 3, "kind": "placeholder"}]
    assert loop.tick() == [2]
    assert (mod / "actors/guest_3/geo.inc.c").read_text() == "// placeholder"
    assert (mod / "textures/sgl_portrait_guest_3.png").read_bytes() == b"donald portrait"
    assert '{ slot = 3, name = "Guest 3", owner = nil },' in (mod / "guests.lua").read_text()


def test_download_outage_keeps_deploy_pending(tmp_path, clock, rename_tool):
    d, blobs = file_deploy(1, 3, "Al")
    blobs["u/portrait.png"] = ApiUnavailable("503")
    api = FakeApi([d], blobs)
    loop, game, _, _ = make_loop(tmp_path, clock, api, rename_tool)
    assert loop.tick() == []
    assert api.reports == [] and game.restarts == 0


def test_deploy_invalidated_during_countdown_is_not_installed(tmp_path, clock, rename_tool):
    d, blobs = file_deploy(1, 3, 'Deleted')
    api = FakeApi([d], blobs)
    loop, game, _, mod = make_loop(tmp_path, clock, api, rename_tool, players=2)
    api.current = []
    assert loop.tick() == []
    assert 'sglguest_geo' not in (mod / 'actors/guest_3/geo.inc.c').read_text()
    assert (mod / 'actors/guest_3/geo.inc.c').read_text() == '// placeholder'
    assert not api.reports
    assert loop.load_roster()[3]['owner'] == ''


def test_ack_rejection_restores_placeholder_before_restart(tmp_path, clock, rename_tool):
    from sglbridge.api import ApiError
    d, blobs = file_deploy(1, 3, 'Deleted')
    api = FakeApi([d], blobs)
    loop, game, _, mod = make_loop(tmp_path, clock, api, rename_tool)
    def reject(*args):
        raise ApiError(409, 'superseded')
    api.report_deploy = reject
    assert loop.tick() == []
    assert (mod / 'actors/guest_3/geo.inc.c').read_text() == '// placeholder'
    assert not (mod / 'textures/sgl_portrait_guest_3.png').exists()
    assert loop.load_roster()[3]['deploy_id'] is None


def test_revalidation_outage_does_not_install_staged_build(tmp_path, clock, rename_tool):
    d, blobs = file_deploy(1, 3, 'Al')
    api = FakeApi([d], blobs)
    loop, game, _, mod = make_loop(tmp_path, clock, api, rename_tool)
    def unavailable(ids):
        raise ApiUnavailable('503')
    api.check_deploys = unavailable
    assert loop.tick() == []
    assert (mod / 'actors/guest_3/geo.inc.c').read_text() == '// placeholder'


def test_failed_rollback_stops_game(tmp_path, clock, rename_tool, monkeypatch):
    d, blobs = file_deploy(1, 3, 'Al')
    api = FakeApi([d], blobs)
    loop, game, _, _ = make_loop(tmp_path, clock, api, rename_tool)
    def fail(staged):
        raise OSError('disk failed')
    monkeypatch.setattr(loop, '_install', fail)
    assert loop.tick() == []
    assert game.stopped


def test_missing_fallback_prevents_swap(tmp_path, clock, rename_tool):
    d, blobs = file_deploy(1, 2, 'Al')
    api = FakeApi([d], blobs)
    loop, game, _, mod = make_loop(tmp_path, clock, api, rename_tool)
    with pytest.raises(DeployError, match='no pristine placeholder'):
        loop.tick()
    assert game.restarts == 0
    assert not (mod / 'actors/guest_2').exists()
