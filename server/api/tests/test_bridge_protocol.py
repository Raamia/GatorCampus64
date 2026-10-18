"""Real bridge/login/outbox -> API -> PostgreSQL, without a game or Auth0 service."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'bridge'))
from bridge import Bridge
from sglbridge.api import ApiClient
from sglbridge.httpclient import HttpResponse
from sglbridge.inbox import Inbox
from sglbridge.login import LoginService
from sglbridge.outbox import DurableRetryQueue
from .test_runs import run_ev


def test_buffered_runs_keep_accounts_after_reconnect_and_restart(client, auth, bridge, conn, tmp_path):
    class Tokens:
        def get(self):
            return bridge['Authorization'].removeprefix('Bearer ')
        def invalidate(self):
            pass

    class Http:
        def request(self, method, url, *, json_body=None, headers=None, **_):
            result = client.request(method, url, json=json_body, headers=headers)
            return HttpResponse(result.status_code, result.content)

    api = ApiClient('http://testserver', Tokens(), Http())
    inbox = Inbox(tmp_path / 'inbox.modfs')
    login = LoginService(None, None, api, inbox, spawn=lambda fn: fn())
    path = tmp_path / 'events.sqlite3'
    send = lambda e: api.post_event(e['t'], e['payload'], e['at'])
    queue = DurableRetryQueue(send, path)
    game = Bridge(inbox, queue, login)
    game.on_event({'t': 'hello'})

    for sub in ('auth0|alice', 'auth0|bob'):
        game.on_event({'t': 'join', 'gi': 1, 'name': 'Ali'})
        code = client.post('/link-codes', headers=auth(sub=sub)).json()['code']
        game.on_event({'t': 'link_req', 'gi': 1, 'name': 'Ali', 'code': code})
        assert login.linked()[1]['name'] == 'Ali'
        event = run_ev()
        game.on_event({'t': 'run', **event['payload']})
        game.on_event({'t': 'leave', 'gi': 1, 'name': 'Ali'})
        assert not login.identities()
    game.on_game_exit(0)
    game.on_event({'t': 'hello'})
    # /links already succeeded, but no lifecycle/run event has reached the API.
    assert conn.execute('SELECT count(*) AS n FROM events').fetchone()['n'] == 0
    queue.close()
    replay = DurableRetryQueue(send, path)
    assert replay.drain_once() > 0
    replay.close()
    rows = conn.execute('SELECT subs, ranked FROM runs ORDER BY id').fetchall()
    assert rows == [{'subs': ['auth0|alice'], 'ranked': True}, {'subs': ['auth0|bob'], 'ranked': True}]
