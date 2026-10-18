import json
import threading

import pytest

from bridge import Bridge
from conftest import FakeClock, resp
from sglbridge.api import ApiUnavailable
from sglbridge.httpclient import TransportError
from sglbridge.inbox import Inbox, read_modfs
from sglbridge.leaderboard import LeaderboardPoller, board_rows, fetch_leaderboards, join_names

API = "https://api.example.test"


def boards(*missions):
    return resp(200, {"missions": list(missions)})


def mission(mid, *rows, title="T"):
    return {"mission": mid, "title": title,
            "rows": [{"rank": i + 1, "names": names, "frames": frames} for i, (names, frames) in enumerate(rows)]}


def cmds(inbox):
    return [c for c in inbox.document()["cmds"] if c["t"] == "leaderboard"]


@pytest.fixture
def inbox(tmp_path):
    return Inbox(tmp_path / "sav" / "sgl64.modfs", clock=lambda: 1000.0)


def make(http, inbox, clock=None):
    clock = clock or FakeClock(500.0)
    return LeaderboardPoller(lambda: fetch_leaderboards(http, API), inbox, clock=clock,
                             wall=lambda: 1_800_000_000.7), clock


def test_join_names_and_rows():
    assert join_names(["Alice", "Bob"]) == "Alice + Bob"
    assert join_names("Solo") == "Solo"
    assert join_names(["  Ann   Lee ", "", None, 7]) == "Ann Lee + 7"
    long = join_names(["Alexandria", "Bartholomew", "Constantine"])
    assert len(long) <= 28 and long.endswith("...") and long.startswith("Alexandria + Bartholomew")
    assert join_names([]) == "?" and join_names(None) == "?"
    rows = board_rows({"rows": [{"rank": 2, "names": ["B"], "frames": 900}, {"rank": 1, "names": ["A"], "frames": 800},
                                {"rank": 3, "names": ["x"], "frames": 0}, {"rank": 4, "names": ["y"], "frames": True},
                                "junk"] + [{"rank": 5 + i, "names": [f"p{i}"], "frames": 1000 + i} for i in range(6)]})
    assert rows[:2] == (("A", 800), ("B", 900)) and len(rows) == 5


def test_fetch_is_public_and_raises_unavailable(http):
    http.add("GET", API + "/leaderboards", boards(mission("swamp_sprint", (["A"], 1200))))
    assert fetch_leaderboards(http, API + "/")[0]["mission"] == "swamp_sprint"
    assert "Authorization" not in http.calls[0]["headers"]          # public: no token
    for r in (resp(503), resp(200, {"nope": 1}), TransportError("down")):
        http.routes.clear()
        http.add("GET", API + "/leaderboards", r)
        with pytest.raises(ApiUnavailable):
            fetch_leaderboards(http, API)


def test_poll_broadcasts_changed_boards_only(http, inbox):
    http.add("GET", API + "/leaderboards",
             boards(mission("swamp_sprint", (["Alice", "Bob"], 1200), (["Carl"], 1500)),
                    mission("reitz_rooftop"), mission("bad id!", (["X"], 5))),
             boards(mission("swamp_sprint", (["Alice", "Bob"], 1200), (["Carl"], 1500)), mission("reitz_rooftop")),
             boards(mission("swamp_sprint", (["Dana"], 1100), (["Alice", "Bob"], 1200)), mission("reitz_rooftop", (["E"], 700))),
             boards(mission("reitz_rooftop", (["E"], 700))))
    p, _ = make(http, inbox)
    assert p.poll_once() == 1                  # the empty board and the bad id are not sent
    assert cmds(inbox) == [{"seq": 1, "t": "leaderboard", "mission": "swamp_sprint", "n": 2, "name1": "Alice + Bob",
                            "frames1": 1200, "name2": "Carl", "frames2": 1500, "at": 1_800_000_000}]
    assert p.poll_once() == 0                  # unchanged: nothing
    assert p.poll_once() == 2                  # both changed
    c = cmds(inbox)
    assert [x["mission"] for x in c[1:]] == ["reitz_rooftop", "swamp_sprint"]
    assert c[2]["name1"] == "Dana" and c[2]["frames1"] == 1100 and c[2]["n"] == 2 and "gi" not in c[2]
    assert p.poll_once() == 1                  # the sprint vanished: sent once with n = 0
    assert cmds(inbox)[-1] == {"seq": 4, "t": "leaderboard", "mission": "swamp_sprint", "n": 0, "at": 1_800_000_000}
    assert p.poll_once() == 0
    # what the mod reads: primitives only, ASCII JSON in the modfs
    files, _ = read_modfs(inbox.path.read_bytes())
    doc = json.loads(files["inbox.json"])
    assert all(isinstance(v, (str, int)) for cmd in doc["cmds"] for v in cmd.values())


def test_outage_keeps_the_boards(http, inbox):
    http.add("GET", API + "/leaderboards", boards(mission("swamp_sprint", (["A"], 1200))), resp(502),
             boards(mission("swamp_sprint", (["A"], 1200))))
    p, _ = make(http, inbox)
    assert p.poll_once() == 1
    assert p.poll_once() == 0                  # 502: logged, nothing pushed
    assert p.on_join(4) == 1                   # the last boards still go to joiners
    assert p.poll_once() == 0                  # back: unchanged


def test_join_resends_every_board_to_that_player(http, inbox):
    http.add("GET", API + "/leaderboards",
             boards(mission("swamp_sprint", (["A"], 1200)), mission("reitz_rooftop", (["B", "C"], 900)), mission("x_empty")))
    p, _ = make(http, inbox)
    assert p.on_join(3) == 0                   # nothing fetched yet
    p.poll_once()
    assert p.on_join(3) == 2
    sent = [c for c in cmds(inbox) if c.get("gi") == 3]
    assert [c["mission"] for c in sent] == ["reitz_rooftop", "swamp_sprint"]
    assert sent[0]["name1"] == "B + C" and sent[0]["at"] == 1_800_000_000


def test_game_restart_rebroadcasts(http, inbox):
    http.add("GET", API + "/leaderboards", boards(mission("swamp_sprint", (["A"], 1200))))
    p, clock = make(http, inbox)
    p.next_at = clock() + 60
    assert p.poll_once() == 1 and p.poll_once() == 0
    p.reset()
    assert p.next_at == clock() + 2.0          # soon after the restart
    assert p.poll_once() == 1


def test_schedule_start_interval_and_kick(http, inbox):
    http.add("GET", API + "/leaderboards", boards(mission("swamp_sprint", (["A"], 1200))))
    clock = FakeClock(500.0)
    p, _ = make(http, inbox, clock)
    stop = threading.Event()
    polls = []
    orig = p.poll_once
    p.poll_once = lambda: polls.append(clock()) or orig()

    class Cv:                                  # a condition whose wait advances the fake clock
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def wait(self, timeout):
            clock.t += timeout
            if clock.t >= 500.0 + 130:
                stop.set()

        def notify(self):
            pass

    p._wake = Cv()
    p.run(stop)
    assert polls[:3] == [500.0, 560.0, 620.0]  # at start, then every 60 s
    p.next_at = clock() + 60
    p.kick()
    assert p.next_at == clock() + 2.0          # ~2 s after a run
    p.kick(30)
    assert p.next_at == clock() + 2.0          # never later than an earlier kick


def test_bridge_wires_join_run_and_restart(http, inbox):
    from test_events import FakeLogin, ListQueue

    http.add("GET", API + "/leaderboards", boards(mission("swamp_sprint", (["A"], 1200))))
    p, clock = make(http, inbox)
    q = ListQueue()
    b = Bridge(inbox, q, FakeLogin(), p)
    p.poll_once()
    p.next_at = clock() + 60
    b.on_line('SGLEVT {"t":"join","gi":2,"name":"B"}')
    assert [c for c in cmds(inbox) if c.get("gi") == 2][0]["mission"] == "swamp_sprint"
    run = ('SGLEVT {"t":"run","act":2,"client_frames":1106,"frames":1104,"gi1":2,"level":9,'
           '"mission":"swamp_sprint","name1":"B","players":1,"retries":1,"round":2}')
    b.on_line(run)
    assert p.next_at == clock() + 2.0          # a poll ~2 s after the run
    assert q[-1]["t"] == "run" and q[-1]["payload"]["frames"] == 1104 and q[-1]["payload"]["name1"] == "B"
    b.on_game_start()
    assert p._sent == {}
