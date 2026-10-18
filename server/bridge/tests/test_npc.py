"""NPC chat on the hosted server (sglbridge/npc.py): npc_ask events -> tools/npc_bridge -> sgl64_npc.modfs."""
import threading
import time
import zipfile

import pytest

from bridge import Bridge
from sglbridge import config as config_mod
from sglbridge import npc as npc_mod
from sglbridge.inbox import Inbox

ASK = ('SGLEVT {"t":"npc_ask","gi":0,"name":"Campus","npc":"albert","player":"Alberta","seq":%d,'
       '"session":"%s","stats":"stars=3;lives=4;players=2","text":"%s"}')


class ListQueue(list):
    def put(self, item):
        self.append(item)


class NoLogin:
    def reset(self):
        pass


def replies(savepath):
    with zipfile.ZipFile(savepath / "sav" / "sgl64_npc.modfs") as z:
        return z.read("replies.txt").decode()


def service(tmp_path, **env):
    e = {"SGL_SAVEPATH": str(tmp_path), "GEMINI_API_KEY": ""}
    e.update(env)
    return npc_mod.build(config_mod.from_env(e))


def test_config_defaults():
    cfg = config_mod.from_env({"GEMINI_API_KEY": " key "})
    assert cfg.npc and not cfg.npc_fake and cfg.gemini_api_key == "key"
    assert cfg.npc_dir == str(npc_mod.REPO_NPC_DIR) and (npc_mod.REPO_NPC_DIR / "bridge.py").is_file()
    assert config_mod.from_env({"SGL_NPC": "0"}).npc is False


def test_parse_ask():
    ok = {"t": "npc_ask", "session": "s1", "seq": 2, "npc": "albert", "player": "A", "text": "hi", "stats": "stars=1"}
    assert npc_mod.parse_ask(ok) == ("s1", (2, "albert", "A", "hi", "stars=1"))
    assert npc_mod.parse_ask({**ok, "text": "x" * 999})[1][3] == "x" * npc_mod.MAX_TEXT
    for bad in ({"seq": "2"}, {"seq": True}, {"session": ""}, {"text": "  "}, {"npc": None}, {"stats": 3}):
        assert npc_mod.parse_ask({**ok, **bad}) is None


def test_ask_events_are_answered_and_never_forwarded(tmp_path):
    npc = service(tmp_path)
    q = ListQueue()
    b = Bridge(Inbox(tmp_path / "sav" / "sgl64.modfs"), q, NoLogin(), npc=npc)
    b.on_line(ASK % (1, "s-1", "how many stars do i have"))
    b.on_line('SGLEVT {"t":"npc_ask","seq":"bad"}')
    assert q == [] and npc.queue.qsize() == 1
    session, req = npc.queue.get_nowait()
    assert npc.answer_one(session, req) == 1
    text = replies(tmp_path)
    assert text.startswith("session\ts-1\n1\talbert\t")
    assert "3 stars" in text.splitlines()[1]               # the guide used the asker's live star count
    assert "inbox.json" not in str(list((tmp_path / "sav").iterdir()))   # the inbox file is untouched


def test_new_session_starts_over_and_game_start_drops_the_queue(tmp_path):
    npc = service(tmp_path, SGL_NPC_FAKE="1")
    npc.answer_one("s-1", (1, "albert", "A", "hello there", ""))
    npc.answer_one("s-1", (1, "albert", "A", "hello again", ""))    # a repeat seq is skipped
    assert len(replies(tmp_path).splitlines()) == 2
    npc.answer_one("s-2", (1, "alberta", "B", "hi alberta", ""))
    assert replies(tmp_path).startswith("session\ts-2\n1\talberta\t")
    b = Bridge(Inbox(tmp_path / "sav" / "sgl64.modfs"), None, NoLogin(), npc=npc)
    b.on_line(ASK % (2, "s-2", "anyone home"))
    b.on_game_start()
    assert npc.queue.empty()


def test_run_thread_and_failures(tmp_path):
    class Boom:
        def handle(self, session, reqs):
            raise RuntimeError("gemini down")

    npc = npc_mod.NpcService(Boom(), lambda s: {}, max_queue=1)
    ev = {"session": "s", "seq": 1, "npc": "albert", "player": "A", "text": "hi"}
    assert npc.ask(ev) and not npc.ask({**ev, "seq": 2})          # queue full: dropped
    stop = threading.Event()
    t = threading.Thread(target=npc.run, args=(stop,))
    t.start()
    for _ in range(200):
        if npc.queue.empty():
            break
        time.sleep(0.01)
    assert npc.queue.empty()                                       # the failure didn't stop the thread
    stop.set()
    t.join(2)
    assert not t.is_alive()


def test_build_off_or_missing(tmp_path):
    assert service(tmp_path, SGL_NPC="0") is None
    assert service(tmp_path, SGL_NPC_DIR=str(tmp_path / "nope")) is None


def test_gemini_when_keyed(tmp_path):
    npc = service(tmp_path, GEMINI_API_KEY="k", SGL_NPC_MODEL="gemini-x", SGL_NPC_THINKING="none")
    r = npc.answerer.replier
    assert type(r).__name__ == "GeminiReplier" and r.api_key == "k" and r.model == "gemini-x" and r.thinking is None
    assert npc.answerer.unanswered == str(tmp_path / "bridge" / "npc_unanswered.log")


@pytest.fixture(autouse=True)
def _quiet_logs(caplog):
    caplog.set_level("WARNING")
