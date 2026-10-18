import threading

from bridge import Bridge
from sglbridge.inbox import Inbox
from sglbridge.presence import PresenceLoop
from test_events import FakeLogin, ListQueue


def test_presence_tracks_game_lifecycle_without_queueing(tmp_path):
    queue = ListQueue()
    b = Bridge(Inbox(tmp_path / 'sgl64.modfs'), queue, FakeLogin())
    assert not b.presence(True)['online']
    b.on_game_start()
    assert not b.presence(True)['online']  # wait for mod hello
    b.on_event({'t': 'hello', 'version': 'v1'})
    b.on_event({'t': 'join', 'gi': 2, 'name': 'Bo'})
    snap = b.presence(True)
    assert snap['online'] and snap['players'] == [{'gi': 2, 'name': 'Bo'}]
    assert snap['version'] == 'v1' and snap['since']
    count = len(queue)
    loop = PresenceLoop(lambda body: None, lambda: b.presence(True))
    loop.tick()
    assert len(queue) == count
    assert not b.presence(False)['online']  # detect process death even before exit callback
    b.on_game_exit(1)
    assert not b.presence(True)['online']
    b.on_game_start()
    assert b.presence(True)['session_id'] != snap['session_id']
    assert b.presence(True)['players'] == []


def test_outage_resamples_and_shutdown_publishes_offline():
    sent = []
    current = {'online': True, 'players': [{'gi': 1, 'name': 'Old'}]}
    def send(body):
        sent.append(body)
        if len(sent) == 1:
            raise OSError('offline')
    loop = PresenceLoop(send, lambda: dict(current))
    loop.tick()
    current.update(players=[])
    loop.tick()
    assert sent[1]['players'] == []
    stop = threading.Event()
    stop.set()
    loop.run(stop)
    assert sent[-1] == {'online': False, 'players': []}
