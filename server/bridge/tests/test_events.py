import json

from bridge import Bridge
from sglbridge.events import event_payload, parse_line
from sglbridge.inbox import Inbox, read_modfs


def test_plain_event():
    ev, other = parse_line('SGLEVT {"t":"join","gi":3,"name":"Alberta"}\n')
    assert ev == {"t": "join", "gi": 3, "name": "Alberta"}
    assert other is None
    assert event_payload(ev) == {"gi": 3, "name": "Alberta"}


def test_non_event_lines_are_logged_text():
    assert parse_line("FS: writepath set to `/srv/sgl`") == (None, "FS: writepath set to `/srv/sgl`")
    assert parse_line("   \n") == (None, None)
    assert parse_line("SGLEVT not json") == (None, "SGLEVT not json")


def test_marker_after_buffered_engine_output():
    ev, other = parse_line('[lua] loading...SGLEVT {"t":"hello","version":"sgl64-web-1","proto":1}')
    assert ev["t"] == "hello" and ev["proto"] == 1
    assert other == "[lua] loading..."


def test_rejects_bad_events():
    for line in ('SGLEVT {"t":1}', 'SGLEVT {"gi":1}', 'SGLEVT {"t":"join"', 'SGLEVT ["t"]', 'SGLEVT {"t":"x"} trailing'):
        ev, other = parse_line(line)
        assert ev is None and other == line


def test_escapes_and_utf8_from_lua_encoder():
    # what sgl_json_encode produces for a name with a quote, a backslash, a control byte and UTF-8
    ev, _ = parse_line('SGLEVT {"t":"join","gi":1,"name":"a\\"b\\\\c\\u0001caf\xc3\xa9"}'.encode("latin-1").decode("utf-8"))
    assert ev["name"] == 'a"b\\c\x01café'


class FakeLogin:
    def __init__(self):
        self.calls = []

    def on_login_req(self, gi, name, context=None):
        assert context and context["session_id"] and context["connection_id"]
        self.calls.append(("login", gi, name))

    def on_link_req(self, gi, name, code, context=None):
        assert context and context["session_id"] and context["connection_id"]
        self.calls.append(("link", gi, name, code))

    def cancel(self, gi):
        self.calls.append(("cancel", gi))

    def reset(self):
        self.calls.append(("reset",))

    def forget(self, gi):
        self.calls.append(("forget", gi))

    def resend_verified(self):
        self.calls.append(("resend",))

    def identities(self):
        return {}


class ListQueue(list):
    def put(self, item):
        self.append(item)


def test_bridge_routes_events(tmp_path):
    inbox = Inbox(tmp_path / "sav" / "sgl64.modfs")
    q = ListQueue()
    login = FakeLogin()
    b = Bridge(inbox, q, login)
    b.on_line('SGLEVT {"t":"hello","version":"sgl64-web-1","proto":1}')
    b.on_line('SGLEVT {"t":"join","gi":1,"name":"A"}')
    b.on_line('SGLEVT {"t":"join","gi":2,"name":"B"}')
    assert b.players_online() == 2
    b.on_line('SGLEVT {"t":"login_req","gi":1,"name":"A"}')
    b.on_line('SGLEVT {"t":"link_req","gi":2,"name":"B","code":"k7q-2xf"}')
    b.on_line('SGLEVT {"t":"link_req","gi":2,"name":"B","code":"!!"}')
    b.on_line('SGLEVT {"t":"login_cancel","gi":2,"name":"B"}')
    b.on_line('SGLEVT {"t":"leave","gi":1,"name":"A"}')
    b.on_line("some engine log line")
    assert b.players_online() == 1
    assert login.calls == [("reset",), ("forget", 1), ("resend",), ("forget", 2), ("resend",), ("login", 1, "A"),
                           ("link", 2, "B", "K7Q2XF"), ("cancel", 2), ("cancel", 1), ("forget", 1)]
    b.on_game_exit(-9)
    assert q[-1]["t"] == "exit" and q[-1]["payload"]["code"] == -9 and b.players_online() == 0
    files, _ = read_modfs((tmp_path / "sav" / "sgl64.modfs").read_bytes())
    doc = json.loads(files["inbox.json"])
    assert doc["cmds"] == []  # game exit clears commands for the old session
    assert [e["t"] for e in q][:8] == ["hello", "join", "join", "login_req", "link_req", "link_req", "login_cancel", "leave"]
    assert q[1]["payload"]["gi"] == 1 and q[1]["at"].endswith("Z")
    assert len({e["payload"]["event_id"] for e in q}) == len(q)
    assert [e["payload"]["sequence"] for e in q] == list(range(1, len(q) + 1))
    assert all('code' not in e['payload'] for e in q if e['t'] == 'link_req')


def test_game_start_resets_players_and_inbox(tmp_path):
    inbox = Inbox(tmp_path / "sgl64.modfs")
    inbox.push("announce", text="old")
    b = Bridge(inbox, None, FakeLogin())
    b.on_line('SGLEVT {"t":"join","gi":1,"name":"A"}')
    b.on_game_start()
    assert b.players_online() == 0
    assert inbox.document() == {"seq": 1, "cmds": []}
