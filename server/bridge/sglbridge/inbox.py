"""Bridge -> game inbox (spec §6.3): <savepath>/sav/sgl64.modfs, read by mods/sgl64/sgl_bridge.lua.

The file is a coopdx v1.5.1 ModFS: a ZIP archive (src/pc/mods/mod_fs.cpp, mod_fs_read / mod_fs_write):
  * path: fs_get_write_path("sav") + "/" + <mod relativePath without ".lua"> + ".modfs"; the write path
    is --savepath, the mod's relativePath is its directory name -> <savepath>/sav/sgl64.modfs;
  * every non-directory zip entry except properties.json is a file; names are checked like
    mod_fs_check_filepath (ASCII, no "\\" or "*", no leading/trailing/double "/", allowed extensions);
  * properties.json (optional) is what mod_fs_write produces: {"isPublic": bool, "files": {path:
    {"isText": bool, "isPublic": bool, "compressionLevel": int}}}; isText defaults to auto-detection
    (no control characters other than whitespace), so the JSON is written ASCII-only;
  * mod_fs_reload() re-reads the whole archive with miniz (stored or deflated entries both work).
The archive is written to a temp file in the same directory and renamed over the old one, so the game
never sees a half-written zip.

inbox.json: {"seq": <last seq>, "cmds": [{"seq": n, "t": "<command>", ...fields}, ...]}
  * seq increases by one per command for the life of the bridge process; the mod runs commands with a
    seq above the last one it ran, and resets its counter when the top-level seq goes below it;
  * reset() (called whenever the game is (re)started) drops every pending command but keeps seq, so a
    fresh game never replays old commands;
  * commands are kept for `max_age` seconds (the mod polls every second) and at most `max_cmds`.
"""
from __future__ import annotations

import io
import json
import os
import tempfile
import threading
import time
import zipfile
from pathlib import Path
from typing import Any, Callable

INBOX_NAME = "inbox.json"
PROPERTIES_NAME = "properties.json"
MOD_FS_MAX_PATH = 0x100
MOD_FS_MAX_SIZE = 0x2000000
MOD_FS_MAX_FILES = 0x200
ALLOWED_EXTENSIONS = (".txt", ".json", ".ini", ".sav", ".bin", ".col", ".bhv", ".tex", ".png", ".lvl",
                      ".m64", ".aiff", ".mp3", ".ogg")


def modfs_path(savepath: str | os.PathLike[str], mod_name: str = "sgl64") -> Path:
    return Path(savepath) / "sav" / f"{mod_name}.modfs"


def check_filepath(path: str) -> None:
    """Raise ValueError when coopdx's mod_fs_check_filepath would reject `path`."""
    if not path or len(path) > MOD_FS_MAX_PATH - 1:
        raise ValueError(f"bad modfs path length: {path!r}")
    if path == PROPERTIES_NAME:
        raise ValueError("properties.json is reserved")
    for c in path:
        if ord(c) > 127 or ord(c) < 32 or ord(c) == 127 or c in "*\\":
            raise ValueError(f"bad character in modfs path: {path!r}")
    if path.startswith("/") or path.endswith("/") or "//" in path:
        raise ValueError(f"bad slashes in modfs path: {path!r}")
    slash, dot = path.rfind("/"), path.rfind(".")
    if dot > slash and path[dot:].lower() not in ALLOWED_EXTENSIONS:
        raise ValueError(f"extension not allowed in modfs: {path!r}")


def is_text(data: bytes) -> bool:
    """mod_fs_file_detect_text_mode: no control characters except whitespace."""
    return all(not (b < 32 or b == 127) or b in b" \t\n\v\f\r" for b in data)


def build_modfs(files: dict[str, bytes], compression_level: int = 1) -> bytes:
    """A ModFS archive holding `files` + a properties.json like mod_fs_write's."""
    if len(files) > MOD_FS_MAX_FILES:
        raise ValueError("too many modfs files")
    if sum(len(d) for d in files.values()) > MOD_FS_MAX_SIZE:
        raise ValueError("modfs too large")
    props: dict[str, Any] = {"isPublic": False, "files": {}}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=compression_level) as zf:
        for name in sorted(files):
            check_filepath(name)
            data = files[name]
            zf.writestr(zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0)), data,
                        compress_type=zipfile.ZIP_DEFLATED)
            props["files"][name] = {"isText": is_text(data), "isPublic": False, "compressionLevel": compression_level}
        zf.writestr(zipfile.ZipInfo(PROPERTIES_NAME, date_time=(2026, 1, 1, 0, 0, 0)),
                    json.dumps(props, indent=4, sort_keys=True).encode("ascii"), compress_type=zipfile.ZIP_DEFLATED)
    return buf.getvalue()


def read_modfs(data: bytes) -> tuple[dict[str, bytes], dict[str, Any]]:
    """(files, properties) of a ModFS archive, read the way mod_fs_read does."""
    files: dict[str, bytes] = {}
    props: dict[str, Any] = {}
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            if info.filename == PROPERTIES_NAME:
                props = json.loads(zf.read(info).decode("utf-8"))
                continue
            check_filepath(info.filename)
            files[info.filename] = zf.read(info)
    return files, props


def write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="." + path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


class Inbox:
    def __init__(self, path: str | os.PathLike[str], *, max_cmds: int = 64, max_age: float = 180.0,
                 clock: Callable[[], float] = time.time):
        self.path = Path(path)
        self.max_cmds = max_cmds
        self.max_age = max_age
        self.clock = clock
        self.seq = 0
        self._cmds: list[tuple[float, dict[str, Any]]] = []
        self._lock = threading.Lock()

    def push(self, t: str, **fields: Any) -> int:
        """Queue command `t` (fields must be JSON primitives: the mod forwards them in a packet)."""
        cmd: dict[str, Any] = {}
        for k, v in fields.items():
            if v is None:
                continue                      # Lua has no null: absent = nil
            if not isinstance(v, (str, int, float, bool)):
                raise TypeError(f"inbox field {k} must be a primitive, got {type(v).__name__}")
            cmd[k] = v
        with self._lock:
            self.seq += 1
            cmd["seq"] = self.seq
            cmd["t"] = t
            self._cmds.append((self.clock(), cmd))
            self._write_locked()
            return self.seq

    def discard_player(self, gi: int) -> None:
        """Do not replay a previous connection's auth commands to a reused slot."""
        with self._lock:
            self._cmds = [(at, c) for at, c in self._cmds
                          if c.get("gi") != gi or c.get("t") not in ("verified", "login_code", "login_failed")]
            self._write_locked()

    def reset(self) -> None:
        """Drop pending commands (the game just (re)started); seq keeps counting."""
        with self._lock:
            self._cmds.clear()
            self._write_locked()

    def document(self) -> dict[str, Any]:
        with self._lock:
            self._prune_locked()
            return {"seq": self.seq, "cmds": [c for _, c in self._cmds]}

    def _prune_locked(self) -> None:
        now = self.clock()
        self._cmds = [(at, c) for at, c in self._cmds if now - at <= self.max_age][-self.max_cmds:]

    def _write_locked(self) -> None:
        self._prune_locked()
        doc = {"seq": self.seq, "cmds": [c for _, c in self._cmds]}
        text = json.dumps(doc, ensure_ascii=True, separators=(",", ":")).encode("ascii")
        write_atomic(self.path, build_modfs({INBOX_NAME: text}))
