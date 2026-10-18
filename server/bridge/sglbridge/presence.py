"""Best-effort current presence, kept out of the durable historical event queue."""
import logging

log = logging.getLogger("sglbridge.presence")


class PresenceLoop:
    def __init__(self, send, snapshot, interval=20):
        self.send, self.snapshot, self.interval = send, snapshot, interval

    def tick(self, offline=False):
        try:
            body = self.snapshot()  # always resample, including after an outage
            if offline:
                body.update(online=False, players=[])
            self.send(body)
        except Exception as e:  # noqa: BLE001 - presence loss expires at the API
            log.warning("presence heartbeat failed: %s", e)

    def run(self, stop):
        while not stop.is_set():
            self.tick()
            stop.wait(self.interval)
        self.tick(offline=True)
