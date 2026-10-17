"""The sm64coopdx child process: start, pipe stdout line by line, restart when it exits (spec §6.4)."""
from __future__ import annotations

import logging
import os
import signal
import subprocess
import threading
import time
from typing import Callable, Sequence

log = logging.getLogger("sglbridge.game")


class GameSupervisor:
    def __init__(self, cmd: Sequence[str], cwd: str | None, on_line: Callable[[str], None],
                 on_start: Callable[[], None] = lambda: None, *, on_exit: Callable[[int], None] = lambda rc: None,
                 stop_timeout: float = 20.0,
                 min_backoff: float = 5.0, max_backoff: float = 60.0, healthy_after: float = 60.0,
                 env: dict[str, str] | None = None):
        self.cmd = list(cmd)
        self.cwd = cwd
        self.on_line = on_line
        self.on_start = on_start
        self.on_exit = on_exit
        self.stop_timeout = stop_timeout
        self.min_backoff = min_backoff
        self.max_backoff = max_backoff
        self.healthy_after = healthy_after
        self.env = env
        self.starts = 0
        self._proc: subprocess.Popen[str] | None = None
        self._paused = threading.Event()          # set while restart() swaps files: do not start
        self._exited = threading.Event()          # the run loop saw the child exit
        self._restart_lock = threading.Lock()
        self._stop = threading.Event()

    @property
    def running(self) -> bool:
        p = self._proc
        return p is not None and p.poll() is None

    def run(self, stop: threading.Event) -> None:
        self._stop = stop
        backoff = self.min_backoff
        while not stop.is_set():
            while self._paused.is_set() and not stop.is_set():
                stop.wait(0.2)
            if stop.is_set():
                break
            started = time.monotonic()
            try:
                proc = subprocess.Popen(self.cmd, cwd=self.cwd, env=self.env, stdin=subprocess.DEVNULL,
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                        encoding="utf-8", errors="replace", bufsize=1)
            except OSError as e:
                log.error("cannot start the game (%s): %s", self.cmd[0], e)
                stop.wait(backoff)
                backoff = min(self.max_backoff, backoff * 2)
                continue
            self._exited.clear()
            self._proc = proc
            self.starts += 1
            log.info("game started (pid %d): %s", proc.pid, " ".join(self.cmd))
            try:
                self.on_start()
            except Exception:  # noqa: BLE001
                log.exception("on_start failed")
            assert proc.stdout is not None
            for line in proc.stdout:
                try:
                    self.on_line(line.rstrip("\n"))
                except Exception:  # noqa: BLE001 - one bad line must not stop the pipe
                    log.exception("line handler failed")
            rc = proc.wait()
            self._proc = None
            self._exited.set()
            try:
                self.on_exit(rc)
            except Exception:  # noqa: BLE001
                log.exception("on_exit failed")
            if stop.is_set():
                break
            if self._paused.is_set():
                log.info("game stopped for a restart (exit %s)", rc)
                backoff = self.min_backoff
                continue
            ran = time.monotonic() - started
            backoff = self.min_backoff if ran >= self.healthy_after else min(self.max_backoff, backoff * 2)
            log.warning("game exited with %s after %.0f s; restarting in %.0f s", rc, ran, backoff)
            stop.wait(backoff)

    def _terminate(self, proc: subprocess.Popen[str]) -> None:
        if proc.poll() is not None:
            return
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(self.stop_timeout)
        except subprocess.TimeoutExpired:
            log.warning("game ignored SIGTERM for %.0f s: killing it", self.stop_timeout)
            proc.kill()
            proc.wait()

    def restart(self, during: Callable[[], None] | None = None) -> None:
        """Stop the game, run `during` (e.g. swap mod files) while it is down, then let it start again."""
        with self._restart_lock:
            self._paused.set()
            try:
                proc = self._proc
                if proc is not None:
                    self._terminate(proc)
                    self._exited.wait(self.stop_timeout + 10)
                if during is not None:
                    during()
            finally:
                self._paused.clear()

    def stop(self) -> None:
        self._stop.set()
        proc = self._proc
        if proc is not None:
            self._terminate(proc)


def default_command(savepath: str, binary: str = "/opt/sm64coopdx/sm64coopdx") -> list[str]:
    """The same flags as server/deploy/sgl-game.service."""
    return [binary, "--headless", "--server", "7777", "--savepath", savepath, "--enable-mod", "sgl64",
            "--playername", "Campus", "--playercount", "16", "--no-discord", "--skip-update-check"]


def line_buffered(cmd: list[str]) -> list[str]:
    """Prefix stdbuf -oL when available so the engine's own printf lines arrive whole and in time."""
    for d in os.environ.get("PATH", "/usr/bin:/bin").split(os.pathsep):
        if os.access(os.path.join(d, "stdbuf"), os.X_OK):
            return ["stdbuf", "-oL", "-eL"] + cmd
    return cmd
