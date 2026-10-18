"""Deploy loop (spec §5.2, §5.3): guest characters from the API into the installed mod.

Per batch (at most one game restart every `min_restart_gap` seconds):
  1. GET /deploys/pending; for each deploy, download its build and STAGE it in a temp dir (validated,
     actor renamed to guest_<slot>) while the game keeps running;
  2. if players are online: inbox `announce` and wait up to `announce_wait` s (or until the server is empty);
  3. stop the game, swap the staged slots into the mod, regenerate guests.lua, start the game
     (files only change while the game is down, so joiners never download a half-written mod);
  4. POST /deploys/{id} deployed, or failed with the reason for a build that could not be staged.

Deploy items (server/api GET /deploys/pending -> {"deploys": [...], "roster": [...]}, a bare list also works):
  {id, slot, kind: "character"|"placeholder", name, owner_sub, owner, files: [{path, url}], ...}
  files are presigned URLs of builds/<job>/<path>. A single zip `artifacts_url` is accepted too.
Build layout (server/worker): actors/sglguest/{geo_header.h, geo.inc.c, model.inc.c} (neutral actor id),
portrait.png (64x64 card portrait), character.json ("id": "sglguest"), previews/, manifest.json, ...
  * the actor is renamed with server/worker/actor_rename.py <dl>/actors/<id> <staging>/actors guest_<n>
    (an export already named guest_<n> is copied as is);
  * portrait.png (or sgl_portrait_guest_<n>.png, at the top or under textures/) -> textures/sgl_portrait_guest_<n>.png;
  * character.json is not installed into the mod (nothing in the game reads it); its id is rewritten to
    guest_<n> in the staging copy only.
kind "placeholder" restores actors/guest_<n>/ and its portrait from the pristine snapshot the bridge takes of
the installed mod's placeholders at first start (<state>/placeholders/), else from SGL_PLACEHOLDER_MOD.
Portraits: only the .png is written; the stale .tex is deleted so the host regenerates it on load.
"""
from __future__ import annotations

import io
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from .api import ApiError, ApiUnavailable

log = logging.getLogger("sglbridge.deploy")

GUEST_SLOTS = 8
MAX_ARTIFACT_BYTES = 64 * 1024 * 1024
MAX_NAME = 12
DEFAULT_RENAME_TOOL = Path(__file__).resolve().parents[2] / "worker" / "actor_rename.py"


class DeployError(Exception):
    pass


def clean_name(name: Any, slot: int) -> str:
    """The same cleaning as characters.lua guest_name (so the site and the game show the same name):
    DJUI colour codes, non-printable / non-ASCII characters and backslashes removed, trimmed, at most
    12 characters."""
    s = re.sub(r"\\#[0-9A-Fa-f]+\\", "", str(name or ""))
    s = "".join(c for c in s if 32 <= ord(c) < 127 and c != "\\").strip()
    s = s[:MAX_NAME].rstrip()
    return s or f"Guest {slot}"


def lua_string(s: str) -> str:
    out = ['"']
    for c in s:
        if c in '"\\':
            out.append("\\" + c)
        elif 32 <= ord(c) < 127:
            out.append(c)
        else:
            out.append("\\%03d" % (ord(c) & 0xFF))
    out.append('"')
    return "".join(out)


def render_guests_lua(roster: dict[int, dict[str, Any]]) -> str:
    """mods/sgl64/guests.lua (the format characters.lua reads, spec §5.2: ONE sgl_guests_register call,
    one line per slot, slots 1..8 in order, owner = Auth0 sub or nil). The only place that knows it."""
    lines = [
        "-- GENERATED FILE: the hosted server's bridge rewrites it on every character deploy",
        "-- (docs/web_platform_spec.md §5.2; server/bridge/sglbridge/deploy.py render_guests_lua).",
        "",
        "sgl_guests_register({",
    ]
    for slot in range(1, GUEST_SLOTS + 1):
        g = roster.get(slot, {})
        owner = str(g.get("owner") or "")
        lines.append("    { slot = %d, name = %s, owner = %s }," % (
            slot, lua_string(clean_name(g.get("name"), slot)), lua_string(owner) if owner else "nil"))
    lines.append("})")
    return "\n".join(lines) + "\n"


def snapshot_placeholders(mod_dir: Path, snap: Path, roster: dict[int, dict[str, Any]]) -> list[int]:
    """Keep a pristine copy of the shipped guest placeholders (actors/guest_<n>/ + portrait) for
    kind="placeholder" deploys. Only slots never deployed by this bridge are copied, once."""
    copied = []
    for slot in range(1, GUEST_SLOTS + 1):
        actor = f"guest_{slot}"
        if (snap / "actors" / actor).exists() or roster.get(slot, {}).get("character_id"):
            continue
        src = mod_dir / "actors" / actor
        if not (src / "geo.inc.c").exists():
            continue
        (snap / "actors").mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, snap / "actors" / actor)
        portrait = mod_dir / "textures" / f"sgl_portrait_{actor}.png"
        if portrait.is_file():
            (snap / "textures").mkdir(parents=True, exist_ok=True)
            shutil.copyfile(portrait, snap / "textures" / portrait.name)
        copied.append(slot)
    return copied


def safe_relpath(path: str) -> PurePosixPath:
    p = PurePosixPath(path)
    if not path or "\\" in path or p.is_absolute() or ".." in p.parts or "" in p.parts:
        raise DeployError(f"unsafe path in artifacts: {path!r}")
    return p


def extract_zip(data: bytes, dest: Path) -> None:
    """A whole-build zip into dest (safe paths only; an optional single wrapper directory is stripped)."""
    if len(data) > MAX_ARTIFACT_BYTES:
        raise DeployError("artifacts too large")
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as e:
        raise DeployError(f"artifacts are not a zip: {e}") from e
    with zf:
        infos = [i for i in zf.infolist() if not i.is_dir()]
        paths = [safe_relpath(i.filename) for i in infos]
        tops = {p.parts[0] for p in paths}
        if len(tops) == 1 and all(len(p.parts) > 1 for p in paths) and "actors" not in tops:
            paths = [PurePosixPath(*p.parts[1:]) for p in paths]
        total = 0
        for info, p in zip(infos, paths):
            total += info.file_size
            if total > MAX_ARTIFACT_BYTES:
                raise DeployError("artifacts too large uncompressed")
            target = dest / p
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)


def run_actor_rename(tool: Path, src: Path, dst_actors: Path, new_id: str) -> None:
    if not tool.exists():
        raise DeployError(f"actor rename tool missing: {tool}")
    r = subprocess.run([sys.executable, str(tool), str(src), str(dst_actors), new_id],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise DeployError(f"actor_rename failed: {(r.stderr or r.stdout).strip()[-500:]}")


def stage_build(dl: Path, slot: int, dest: Path, rename_tool: Path = DEFAULT_RENAME_TOOL) -> dict[str, Any]:
    """Turn a downloaded build (dl) into the files of slot `slot` under dest/{actors,textures}/."""
    if not isinstance(slot, int) or isinstance(slot, bool) or not 1 <= slot <= GUEST_SLOTS:
        raise DeployError(f"bad slot {slot!r}")
    actor = f"guest_{slot}"
    actors = dl / "actors"
    srcs = sorted(p for p in actors.iterdir() if p.is_dir()) if actors.is_dir() else []
    if len(srcs) != 1:
        raise DeployError(f"expected one actor export under actors/, found {[p.name for p in srcs]}")
    src = srcs[0]
    if not (src / "geo.inc.c").exists():
        raise DeployError(f"actors/{src.name}/geo.inc.c missing")
    (dest / "actors").mkdir(parents=True, exist_ok=True)
    if src.name == actor:
        shutil.copytree(src, dest / "actors" / actor)
    else:
        run_actor_rename(rename_tool, src, dest / "actors", actor)
    if not (dest / "actors" / actor / "geo.inc.c").exists():
        raise DeployError(f"staged actors/{actor}/geo.inc.c missing")
    portrait_name = f"sgl_portrait_{actor}.png"
    portrait = next((p for p in (dl / "portrait.png", dl / portrait_name, dl / "textures" / portrait_name)
                     if p.is_file()), None)
    if portrait is not None:
        (dest / "textures").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(portrait, dest / "textures" / portrait_name)
    cj = dl / "character.json"
    if cj.is_file():
        try:
            spec = json.loads(cj.read_text())
            spec["id"] = actor
            (dest / "character.json").write_text(json.dumps(spec, indent=2))
        except (ValueError, TypeError):
            log.warning("character.json of %s is not valid JSON (ignored)", actor)
    return {"actor_from": src.name, "portrait": portrait is not None}


def stage_placeholder(sources: list[Path], slot: int, dest: Path) -> dict[str, Any]:
    """Restore the shipped placeholder of `slot` from the first source holding it (the bridge's
    snapshot, then the repo copy of the mod)."""
    actor = f"guest_{slot}"
    src = next((s for s in sources if (s / "actors" / actor / "geo.inc.c").exists()), None)
    if src is None:
        raise DeployError(f"no pristine placeholder for {actor} (snapshot / SGL_PLACEHOLDER_MOD)")
    shutil.copytree(src / "actors" / actor, dest / "actors" / actor)
    portrait = src / "textures" / f"sgl_portrait_{actor}.png"
    if portrait.is_file():
        (dest / "textures").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(portrait, dest / "textures" / portrait.name)
    return {"actor_from": "placeholder", "portrait": portrait.is_file()}


def install_staged(staged: Path, mod_dir: Path, slot: int) -> None:
    """Swap a staged slot into the installed mod (the game must be stopped)."""
    actor = f"guest_{slot}"
    dst = mod_dir / "actors" / actor
    dst.parent.mkdir(parents=True, exist_ok=True)
    old = dst.with_name(f".{actor}.old")
    if old.exists():
        shutil.rmtree(old)
    if dst.exists():
        os.replace(dst, old)
    shutil.copytree(staged / "actors" / actor, dst)
    if old.exists():
        shutil.rmtree(old)
    # stale DynOS-compiled outputs: the game rebuilds them from the sources on load
    for stale in (mod_dir / "actors" / f"{actor}_geo.bin", mod_dir / "textures" / f"sgl_portrait_{actor}.tex"):
        if stale.exists():
            stale.unlink()
    portrait = staged / "textures" / f"sgl_portrait_{actor}.png"
    if portrait.exists():
        (mod_dir / "textures").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(portrait, mod_dir / "textures" / portrait.name)
    else:
        (mod_dir / "textures" / f"sgl_portrait_{actor}.png").unlink(missing_ok=True)


@dataclass
class Staged:
    deploy: dict[str, Any]
    slot: int
    name: str
    owner: str
    path: Path
    info: dict[str, Any] = field(default_factory=dict)


class DeployLoop:
    def __init__(self, api: Any, inbox: Any, game: Any, mod_dir: str | os.PathLike[str],
                 roster_path: str | os.PathLike[str], players_online: Callable[[], int], *,
                 placeholder_mod: str | os.PathLike[str] | None = None,
                 rename_tool: str | os.PathLike[str] = DEFAULT_RENAME_TOOL,
                 poll_interval: float = 30.0, min_restart_gap: float = 300.0, announce_wait: float = 60.0,
                 clock: Callable[[], float] = time.monotonic, wait: Callable[[float], bool] | None = None):
        self.api = api
        self.inbox = inbox
        self.game = game
        self.mod_dir = Path(mod_dir)
        self.roster_path = Path(roster_path)
        self.players_online = players_online
        self.snapshot_dir = self.roster_path.parent / "placeholders"
        self.placeholder_sources = [self.snapshot_dir] + ([Path(placeholder_mod)] if placeholder_mod else [])
        self.rename_tool = Path(rename_tool)
        self.poll_interval = poll_interval
        self.min_restart_gap = min_restart_gap
        self.announce_wait = announce_wait
        self.clock = clock
        self._stop = threading.Event()
        self._wait_fn = wait
        self.last_restart: float | None = None

    # roster ------------------------------------------------------------------------------------
    def load_roster(self) -> dict[int, dict[str, Any]]:
        try:
            raw = json.loads(self.roster_path.read_text())
            return {int(k): v for k, v in raw.items() if isinstance(v, dict)}
        except (OSError, ValueError):
            return {}

    def save_roster(self, roster: dict[int, dict[str, Any]]) -> None:
        self.roster_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.roster_path.with_suffix(".tmp")
        tmp.write_text(json.dumps({str(k): v for k, v in sorted(roster.items())}, indent=2))
        os.replace(tmp, self.roster_path)

    # loop --------------------------------------------------------------------------------------
    def prepare(self) -> None:
        """First start: snapshot the shipped placeholders before any deploy overwrites them."""
        try:
            copied = snapshot_placeholders(self.mod_dir, self.snapshot_dir, self.load_roster())
            if copied:
                log.info("snapshotted placeholder slots %s into %s", copied, self.snapshot_dir)
        except OSError as e:
            log.warning("placeholder snapshot failed: %s", e)

    def run(self, stop: threading.Event) -> None:
        self._stop = stop
        self.prepare()
        while not stop.is_set():
            try:
                self.tick()
            except Exception:  # noqa: BLE001 - keep polling
                log.exception("deploy tick failed")
            if stop.wait(self.poll_interval):
                break

    def tick(self) -> list[Any]:
        """One poll. Returns the ids reported deployed (empty when nothing ran)."""
        if self.last_restart is not None and self.clock() - self.last_restart < self.min_restart_gap:
            return []
        try:
            self.api.reconcile_deploys({slot: item.get("deploy_id") for slot, item in self.load_roster().items()})
            pending = self.api.pending_deploys()
        except (ApiUnavailable, ApiError) as e:
            log.warning("GET /deploys/pending: %s", e)
            return []
        if not pending:
            return []
        with tempfile.TemporaryDirectory(prefix="sgl-deploy-") as tmp:
            staged = self._stage_all(pending, Path(tmp))
            if not staged:
                return []
            self.prepare()  # pristine placeholders are required before a reversible install
            fallbacks = []
            for item in staged:
                path = Path(tmp) / f"fallback-{item.slot}"
                info = stage_placeholder(self.placeholder_sources, item.slot, path)
                fallbacks.append(Staged({}, item.slot, f"Guest {item.slot}", "", path, info))
            self._announce_and_wait([s.name for s in staged if s.deploy.get("kind") != "placeholder"])
            done = []
            def install_current():
                current = self.api.check_deploys([item.deploy["id"] for item in staged])
                selected = [item for item in staged if item.deploy["id"] in current]
                if self._stop.is_set():
                    return
                try:
                    stale_slots = {item.slot for item in staged if item.deploy["id"] not in current}
                    stale = [f for f in fallbacks if f.slot in stale_slots]
                    if stale:
                        self._install(stale)
                    if not selected:
                        return
                    self._install(selected)
                    for item in selected:
                        # A second authoritative check occurs in the acknowledgement transaction.
                        self.api.report_deploy(item.deploy["id"], "deployed", f"slot {item.slot}")
                        done.append(item.deploy["id"])
                except Exception:
                    # Includes a lost acknowledgement: reconcile will queue the intended state again.
                    try:
                        self._install(fallbacks)
                    except Exception:
                        self.game.stop()  # never start with an install we could not undo
                        raise
                    done.clear()
                    raise
            try:
                self.game.restart(during=install_current)
            except Exception as e:  # noqa: BLE001 - the supervisor still restarts the game
                log.exception("installing deploys failed")
                for s in staged:
                    self._report(s.deploy.get("id"), "failed", f"install: {e}")
                return []
            finally:
                self.last_restart = self.clock()
        return done

    def _fetch(self, d: dict[str, Any], dl: Path) -> None:
        files = d.get("files")
        if isinstance(files, list) and files:
            total = 0
            for f in files:
                if not isinstance(f, dict) or not f.get("path") or not f.get("url"):
                    raise DeployError(f"bad file entry {f!r}")
                rel = safe_relpath(str(f["path"]))
                if rel.parts[0] == "previews":
                    continue                            # not needed on the game server
                data = self.api.download(f["url"])
                total += len(data)
                if total > MAX_ARTIFACT_BYTES:
                    raise DeployError("artifacts too large")
                (dl / rel).parent.mkdir(parents=True, exist_ok=True)
                (dl / rel).write_bytes(data)
        elif d.get("artifacts_url"):
            extract_zip(self.api.download(d["artifacts_url"]), dl)
        else:
            raise DeployError("deploy has no files")

    def _stage_all(self, pending: list[dict[str, Any]], tmp: Path) -> list[Staged]:
        staged: list[Staged] = []
        seen_slots: set[int] = set()
        for i, d in enumerate(pending):
            slot = d.get("slot")
            if isinstance(slot, int) and slot in seen_slots:
                continue                                # one per slot per batch; the rest next round
            placeholder = d.get("kind") == "placeholder"
            dest = tmp / f"stage-{i}"
            try:
                if not isinstance(slot, int) or not 1 <= slot <= GUEST_SLOTS:
                    raise DeployError(f"bad slot {slot!r}")
                if placeholder:
                    info = stage_placeholder(self.placeholder_sources, slot, dest)
                else:
                    dl = tmp / f"download-{i}"
                    dl.mkdir()
                    self._fetch(d, dl)
                    info = stage_build(dl, slot, dest, self.rename_tool)
            except ApiUnavailable as e:
                log.warning("deploy %s: download failed, retrying later: %s", d.get("id"), e)
                continue
            except (DeployError, OSError, subprocess.SubprocessError) as e:
                log.error("deploy %s failed: %s", d.get("id"), e)
                self._report(d.get("id"), "failed", str(e))
                continue
            seen_slots.add(slot)
            name = f"Guest {slot}" if placeholder else clean_name(d.get("name"), slot)
            owner = "" if placeholder else str(d.get("owner_sub") or d.get("owner") or "")
            staged.append(Staged(d, slot, name, owner, dest, info))
        return staged

    def _announce_and_wait(self, names: list[str]) -> None:
        if self.players_online() <= 0:
            return
        if not names:
            text = f"The server restarts in {int(self.announce_wait)} s"
        else:
            who = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
            text = f"New gator {who} arrives in {int(self.announce_wait)} s: the server will restart"
        self.inbox.push("announce", text=text, secs=int(self.announce_wait))
        end = self.clock() + self.announce_wait
        while self.clock() < end and self.players_online() > 0:
            if self._wait(min(1.0, max(0.0, end - self.clock()))):
                break

    def _wait(self, seconds: float) -> bool:
        return (self._wait_fn or self._stop.wait)(seconds)

    def _install(self, staged: list[Staged]) -> None:
        roster = self.load_roster()
        for s in staged:
            install_staged(s.path, self.mod_dir, s.slot)
            roster[s.slot] = {"name": s.name, "owner": s.owner, "deploy_id": s.deploy.get("id"),
                              "character_id": s.deploy.get("character_id")}
        self.save_roster(roster)
        guests = self.mod_dir / "guests.lua"
        tmp = guests.with_suffix(".lua.tmp")
        tmp.write_text(render_guests_lua(roster))
        os.replace(tmp, guests)
        log.info("installed guest slots %s", [s.slot for s in staged])

    def _report(self, deploy_id: Any, status: str, detail: str) -> None:
        try:
            self.api.report_deploy(deploy_id, status, detail)
        except (ApiUnavailable, ApiError) as e:
            log.warning("POST /deploys/%s %s: %s", deploy_id, status, e)
