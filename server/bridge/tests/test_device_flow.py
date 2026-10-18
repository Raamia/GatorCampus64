import json
import threading
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from sglbridge.api import ApiClient, ApiError
from sglbridge.auth import (Auth0Config, Cancelled, DeviceCode, DeviceFlowClient, IdTokenValidator, LoginFailed,
                            M2MTokenProvider)
from sglbridge.httpclient import TransportError
from sglbridge.inbox import Inbox, read_modfs
from sglbridge.login import UF_CLAIM, LoginService

from conftest import resp

CFG = Auth0Config("login.example.test", "gatorpass-client", "https://api.example.test")
CODE_URL = "https://login.example.test/oauth/device/code"
TOKEN_URL = "https://login.example.test/oauth/token"
DEVICE_REPLY = {"device_code": "dev-123", "user_code": "ABCD-EFGH",
                "verification_uri": "https://login.example.test/activate",
                "verification_uri_complete": "https://login.example.test/activate?user_code=ABCD-EFGH",
                "expires_in": 900, "interval": 5}


def pending():
    return resp(403, {"error": "authorization_pending", "error_description": "User has yet to authorize device code."})


def dc(expires_in=900, interval=5):
    return DeviceCode("dev-123", "ABCD-EFGH", "https://x/activate", "https://x/activate?user_code=ABCD-EFGH",
                      expires_in, interval)


# --- device code request ---------------------------------------------------------------------------
def test_request_code(http, clock):
    http.add("POST", CODE_URL, resp(200, DEVICE_REPLY))
    got = DeviceFlowClient(CFG, http, clock).request_code()
    assert got.user_code == "ABCD-EFGH" and got.interval == 5 and got.expires_in == 900
    assert got.verification_uri_complete.endswith("user_code=ABCD-EFGH")
    assert http.calls[0]["form"] == {"client_id": "gatorpass-client", "scope": "openid profile email",
                                     "audience": "https://api.example.test"}


def test_request_code_errors(http, clock):
    http.add("POST", CODE_URL, resp(401, {"error": "unauthorized_client"}))
    with pytest.raises(LoginFailed) as e:
        DeviceFlowClient(CFG, http, clock).request_code()
    assert e.value.reason == "error"
    http.routes.clear()
    http.add("POST", CODE_URL, TransportError("down"))
    with pytest.raises(LoginFailed) as e:
        DeviceFlowClient(CFG, http, clock).request_code()
    assert e.value.reason == "unavailable"


# --- polling state machine -------------------------------------------------------------------------
def test_poll_pending_slow_down_then_tokens(http, clock):
    http.add("POST", TOKEN_URL, pending(), resp(429, {"error": "slow_down"}), pending(),
             resp(200, {"access_token": "at", "id_token": "it", "expires_in": 86400}))
    tokens = DeviceFlowClient(CFG, http, clock).poll(dc(), clock.wait)
    assert tokens["id_token"] == "it"
    assert clock.waits == [5, 5, 10, 10]                 # slow_down adds 5 s for every later poll
    assert http.calls[0]["form"] == {"grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                                     "device_code": "dev-123", "client_id": "gatorpass-client"}


@pytest.mark.parametrize("reply,reason", [
    (resp(403, {"error": "expired_token"}), "expired"),
    (resp(403, {"error": "access_denied", "error_description": "User refused"}), "denied"),
    (resp(400, {"error": "invalid_grant"}), "error"),
])
def test_poll_terminal_errors(http, clock, reply, reason):
    http.add("POST", TOKEN_URL, pending(), reply)
    with pytest.raises(LoginFailed) as e:
        DeviceFlowClient(CFG, http, clock).poll(dc(), clock.wait)
    assert e.value.reason == reason
    assert len(http.calls) == 2


def test_poll_local_deadline(http, clock):
    http.add("POST", TOKEN_URL, pending())
    with pytest.raises(LoginFailed) as e:
        DeviceFlowClient(CFG, http, clock).poll(dc(expires_in=20, interval=5), clock.wait)
    assert e.value.reason == "expired"
    assert len(http.calls) == 3                           # t = 5, 10, 15; at 20 the code is gone


def test_poll_survives_transport_errors_then_gives_up(http, clock):
    http.add("POST", TOKEN_URL, TransportError("blip"), pending(), resp(200, {"access_token": "a", "id_token": "i"}))
    assert DeviceFlowClient(CFG, http, clock).poll(dc(), clock.wait)["id_token"] == "i"
    http.routes.clear()
    http.add("POST", TOKEN_URL, TransportError("down"))
    with pytest.raises(LoginFailed) as e:
        DeviceFlowClient(CFG, http, clock).poll(dc(), clock.wait)
    assert e.value.reason == "unavailable"


def test_poll_cancel(http, clock):
    http.add("POST", TOKEN_URL, pending())
    n = {"waits": 0}

    def wait(s):
        n["waits"] += 1
        return n["waits"] >= 3
    with pytest.raises(Cancelled):
        DeviceFlowClient(CFG, http, clock).poll(dc(), wait)
    assert len(http.calls) == 2


# --- ID token validation ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def keys():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048), \
        rsa.generate_private_key(public_exponent=65537, key_size=2048)


def make_token(key, **over):
    now = int(time.time())
    claims = {"iss": "https://login.example.test/", "aud": "gatorpass-client", "sub": "google-oauth2|42",
              "iat": now, "exp": now + 3600, "nickname": "albert"}
    claims.update(over)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": "k1"})


def validator(pub):
    return IdTokenValidator("https://login.example.test/", "gatorpass-client", key_resolver=lambda t: pub)


def test_id_token_valid(keys):
    good, _ = keys
    claims = validator(good.public_key()).validate(make_token(good))
    assert claims["sub"] == "google-oauth2|42"


@pytest.mark.parametrize("over", [
    {"aud": "https://api.example.test"},             # an access token's audience, not the app's
    {"iss": "https://evil.example.test/"},
    {"exp": int(time.time()) - 3600},
    {"sub": None},
])
def test_id_token_rejected(keys, over):
    good, _ = keys
    with pytest.raises(LoginFailed) as e:
        validator(good.public_key()).validate(make_token(good, **over))
    assert e.value.reason == "invalid_token"


def test_id_token_bad_signature_and_alg(keys):
    good, other = keys
    with pytest.raises(LoginFailed):
        validator(good.public_key()).validate(make_token(other))
    hs = jwt.encode({"iss": "https://login.example.test/", "aud": "gatorpass-client", "sub": "x",
                     "iat": int(time.time()), "exp": int(time.time()) + 60}, "secret" * 8, algorithm="HS256")
    with pytest.raises(LoginFailed):
        validator(good.public_key()).validate(hs)


# --- the whole login: device flow -> /links -> inbox -------------------------------------------------
class FakeTokens:
    def __init__(self):
        self.n = 0
        self.invalidated = 0

    def get(self):
        self.n += 1
        return f"m2m-{self.n}"

    def invalidate(self):
        self.invalidated += 1


def inbox_cmds(path):
    return json.loads(read_modfs(path.read_bytes())[0]["inbox.json"])["cmds"]


def login_service(http, clock, tmp_path, keys):
    good, _ = keys
    flow = DeviceFlowClient(CFG, http, clock)
    api = ApiClient("https://api.example.test", FakeTokens(), http)
    inbox = Inbox(tmp_path / "sgl64.modfs")
    svc = LoginService(flow, validator(good.public_key()), api, inbox, spawn=lambda fn: fn(),
                       waiter=lambda ev, s: clock.wait(s) or ev.is_set())
    return svc, inbox


def test_login_end_to_end(http, clock, tmp_path, keys):
    good, _ = keys
    http.add("POST", CODE_URL, resp(200, DEVICE_REPLY))
    http.add("POST", TOKEN_URL, pending(), resp(200, {"access_token": "at", "id_token": make_token(good, **{UF_CLAIM: True})}))
    http.add("POST", "https://api.example.test/links", resp(200, {"nickname": "Albert", "guest_slot": 3}))
    svc, inbox = login_service(http, clock, tmp_path, keys)
    svc.on_login_req(4, "AlbertG")
    cmds = inbox_cmds(inbox.path)
    assert cmds[0] == {"seq": 1, "t": "login_code", "gi": 4, "user_code": "ABCD-EFGH",
                       "uri": "https://login.example.test/activate?user_code=ABCD-EFGH",
                       "page": "https://login.example.test/activate", "expires": 900}
    assert cmds[1] == {"seq": 2, "t": "verified", "gi": 4, "name": "AlbertG", "nickname": "Albert", "guest_slot": 3,
                       "uf": True}
    link_call = [c for c in http.calls if c["url"].endswith("/links")][0]
    assert link_call["json"] == {"sub": "google-oauth2|42", "coopdx_name": "AlbertG", "gi": 4,
                                 "nickname": "albert", "uf": True}
    assert link_call["headers"]["Authorization"].startswith("Bearer m2m-")


def test_login_denied_goes_to_inbox(http, clock, tmp_path, keys):
    http.add("POST", CODE_URL, resp(200, DEVICE_REPLY))
    http.add("POST", TOKEN_URL, resp(403, {"error": "access_denied"}))
    svc, inbox = login_service(http, clock, tmp_path, keys)
    svc.on_login_req(2, "B")
    assert inbox_cmds(inbox.path)[-1] == {"seq": 2, "t": "login_failed", "gi": 2, "reason": "denied"}


def test_login_without_auth0_config(tmp_path):
    inbox = Inbox(tmp_path / "sgl64.modfs")
    LoginService(None, None, None, inbox).on_login_req(1, "A")
    assert inbox_cmds(inbox.path) == [{"seq": 1, "t": "login_failed", "gi": 1, "reason": "unavailable"}]


def test_link_code(http, clock, tmp_path, keys):
    http.add("POST", "https://api.example.test/links", resp(200, {"nickname": "Bo", "guest_slot": None}),
             resp(404, {"detail": "unknown code"}))
    svc, inbox = login_service(http, clock, tmp_path, keys)
    svc.on_link_req(5, "Bo", "K7Q2XF")
    svc.on_link_req(5, "Bo", "ZZZZZZ")
    cmds = inbox_cmds(inbox.path)
    assert cmds[0] == {"seq": 1, "t": "verified", "gi": 5, "name": "Bo", "nickname": "Bo"}
    assert cmds[1] == {"seq": 2, "t": "login_failed", "gi": 5, "reason": "bad_code"}
    assert http.calls[0]["json"] == {"code": "K7Q2XF", "coopdx_name": "Bo", "gi": 5}


def test_link_code_expired_and_resend_verified(http, clock, tmp_path, keys):
    http.add("POST", "https://api.example.test/links",
             resp(410, {"detail": {"reason": "expired", "message": "link code expired"}}),
             resp(200, {"nickname": "Cy", "guest_slot": 2, "uf": True}))
    svc, inbox = login_service(http, clock, tmp_path, keys)
    svc.on_link_req(6, "Cy", "AAAAAA")
    svc.on_link_req(6, "Cy", "BBBBBB")
    assert svc.resend_verified() == 1
    cmds = inbox_cmds(inbox.path)
    svc.forget(6)
    assert svc.resend_verified() == 0
    assert inbox_cmds(inbox.path) == []
    assert cmds[0] == {"seq": 1, "t": "login_failed", "gi": 6, "reason": "expired"}
    assert cmds[1] == {"seq": 2, "t": "verified", "gi": 6, "name": "Cy", "nickname": "Cy", "guest_slot": 2, "uf": True}
    assert cmds[2] == dict(cmds[1], seq=3, resend=True)


def test_cancel_on_leave_is_silent(tmp_path):
    inbox = Inbox(tmp_path / "sgl64.modfs")
    started = threading.Event()

    class SlowFlow:
        def request_code(self):
            return dc()

        def poll(self, d, wait):
            started.set()
            while not wait(0.01):
                pass
            raise Cancelled()

    svc = LoginService(SlowFlow(), object(), object(), inbox)
    svc.on_login_req(1, "A")
    assert started.wait(2)
    svc.cancel(1)
    for _ in range(200):
        if not svc._sessions:
            break
        time.sleep(0.01)
    assert not svc._sessions
    assert [c["t"] for c in inbox_cmds(inbox.path)] == ["login_code"]      # no login_failed after a cancel


# --- M2M token + API auth --------------------------------------------------------------------------
@pytest.mark.parametrize("lifecycle", ["cancel", "forget", "reset", "replace"])
def test_late_link_response_cannot_publish(tmp_path, lifecycle):
    inbox = Inbox(tmp_path / "sgl64.modfs")
    pending = []

    class Api:
        def redeem_link_code(self, code, name, gi):
            if lifecycle == "replace":
                svc.on_link_req(gi, "New player", "NEW123")
            elif lifecycle == "reset":
                svc.reset()
            else:
                getattr(svc, lifecycle)(gi)
            return {"nickname": "Old player", "guest_slot": 3}

    svc = LoginService(None, None, Api(), inbox, spawn=pending.append)
    svc.on_link_req(1, "Old player", "OLD123")
    pending.pop(0)()
    assert not svc.linked()
    assert not inbox.document()["cmds"]


def test_forget_removes_queued_verification(tmp_path):
    inbox = Inbox(tmp_path / "sgl64.modfs")
    inbox.push("verified", gi=1, name="Old player")
    inbox.push("verified", gi=2, name="Still here")
    svc = LoginService(None, None, None, inbox)
    svc.forget(1)
    assert [c["gi"] for c in inbox.document()["cmds"]] == [2]


def test_device_flow_cancelled_during_link_write_cannot_publish(tmp_path):
    inbox = Inbox(tmp_path / 'sgl64.modfs')
    class Flow:
        def request_code(self): return dc()
        def poll(self, *_): return {'id_token': 'checked-by-test-validator'}
    class Validator:
        def validate(self, _): return {'sub': 'auth0|alice'}
    class Api:
        def post_link(self, *args, **kwargs):
            svc.forget(1)  # disconnect occurs while the HTTP response is in flight
            return {'link_id': 1, 'nickname': 'Alice'}
    svc = LoginService(Flow(), Validator(), Api(), inbox, spawn=lambda fn: fn())
    svc.on_login_req(1, 'Alice', {'session_id': 'session', 'connection_id': 'connection'})
    assert not svc.linked() and not svc.identities()
    assert not inbox.document()['cmds']


def test_m2m_token_cached_until_expiry(http, clock):
    url = "https://tenant.example.test/oauth/token"
    http.add("POST", url, resp(200, {"access_token": "t1", "expires_in": 3600}),
             resp(200, {"access_token": "t2", "expires_in": 3600}))
    p = M2MTokenProvider("tenant.example.test", "m2m-id", "m2m-secret", "https://api.example.test", http, clock)
    assert p.get() == "t1" and p.get() == "t1"
    assert http.calls[0]["json"]["grant_type"] == "client_credentials"
    clock.t += 3600 - 59
    assert p.get() == "t2"
    assert len(http.calls) == 2


def test_api_retries_once_on_401(http):
    tokens = FakeTokens()
    http.add("GET", "https://api.example.test/deploys/pending", resp(401, {}), resp(200, [{"id": 1}]))
    assert ApiClient("https://api.example.test/", tokens, http).pending_deploys() == [{"id": 1}]
    assert tokens.invalidated == 1
    http.routes.clear()
    http.add("POST", "https://api.example.test/events", resp(422, {"detail": "bad"}))
    with pytest.raises(ApiError):
        ApiClient("https://api.example.test", tokens, http).post_event("join", {}, "now")
