import threading
import time

from sglbridge.api import ApiError, ApiUnavailable, RetryQueue


class Sender:
    def __init__(self):
        self.up = True
        self.got = []
        self.reject = set()

    def __call__(self, item):
        if item in self.reject:
            raise ApiError(422, "bad")
        if not self.up:
            raise ApiUnavailable("down")
        self.got.append(item)


def test_delivers_in_order(clock):
    s = Sender()
    q = RetryQueue(s, clock=clock)
    for i in range(5):
        q.put(i)
    assert q.drain_once() == 5
    assert s.got == [0, 1, 2, 3, 4] and len(q) == 0


def test_outage_backs_off_and_keeps_order(clock):
    s = Sender()
    q = RetryQueue(s, base_delay=1, max_delay=8, clock=clock)
    s.up = False
    q.put("a")
    q.put("b")
    delays = []
    for _ in range(6):
        assert q.drain_once() == 0
        delays.append(q.next_attempt - clock.t)
        assert q.drain_once() == 0                   # still inside the backoff window: no attempt
        clock.t = q.next_attempt
    assert delays == [1, 2, 4, 8, 8, 8]
    s.up = True
    assert q.drain_once() == 2
    assert s.got == ["a", "b"] and q.failures == 0


def test_bounded_drops_oldest(clock):
    s = Sender()
    q = RetryQueue(s, maxlen=3, clock=clock)
    for i in range(10):
        q.put(i)                                     # never blocks
    assert len(q) == 3 and q.dropped == 7
    q.drain_once()
    assert s.got == [7, 8, 9]


def test_client_errors_are_dropped_not_retried(clock):
    s = Sender()
    s.reject = {"bad"}
    q = RetryQueue(s, clock=clock)
    for x in ("a", "bad", "c"):
        q.put(x)
    assert q.drain_once() == 2
    assert s.got == ["a", "c"] and len(q) == 0


def test_put_never_blocks_while_sender_hangs():
    release = threading.Event()

    def slow_send(item):
        release.wait(5)

    q = RetryQueue(slow_send, maxlen=100)
    stop = threading.Event()
    t = threading.Thread(target=q.run, args=(stop,), daemon=True)
    t.start()
    q.put("first")
    time.sleep(0.05)                                 # the sender is now stuck on "first"
    start = time.monotonic()
    for i in range(1000):
        q.put(i)
    assert time.monotonic() - start < 0.5
    assert len(q) == 100 and q.dropped > 0
    release.set()
    stop.set()
    t.join(2)
