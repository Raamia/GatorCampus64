"""One Gatorize Me job: photos -> spec -> face -> build/export/validate -> preview -> store.

Every job is built under the neutral actor id BUILD_ID ("sglguest", see actor_rename.py): the
guest slot is not known until the API slots the ready character, and the bridge renames the
export to guest_<n> when it deploys it. Per-job working tree (WORK_ROOT/<job>/):
  photos/                    downloaded uploads
  art/sglguest/character.json + textures/   (the builder reads it via --art-dir)
  build/                     .blend, build_report.json, previews/
  actors/sglguest/           the Fast64 export
  portrait.png               64x64 character-select portrait
Stored in Object Storage under builds/<job>/ (manifest.json lists everything); photos/<job>/
is deleted when the job ends, success or failure.
"""
import importlib.util
import json
import os
import queue
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field

import actor_rename
import portrait
import spec_ai

BUILD_ID = actor_rename.BUILD_ID
PHOTO_EXTS = (".jpg", ".jpeg", ".png", ".webp")
# builder stdout markers -> (state, step) from that line on
MARKERS = [("SGL saved", "export"), ("SGL validation", "validate"), ("SGL_PREVIEW", "preview")]


@dataclass
class Config:
    repo: str = "/opt/sgl64"
    blender: str = "/opt/blender-4.5.3/blender"
    work_root: str = "/tmp/sglwork"
    build_timeout: float = 600.0
    face_timeout: float = 60.0
    python: str = sys.executable
    keep_workdir: bool = False
    require_model: bool = False
    use_cv: bool = True
    retries: int = 3  # run_blender.sh SGL_RETRIES (Blender crashes only)

    @classmethod
    def from_env(cls):
        e = os.environ
        return cls(repo=e.get("SGL_REPO", cls.repo), blender=e.get("BLENDER", cls.blender),
                   work_root=e.get("WORK_ROOT", cls.work_root),
                   build_timeout=float(e.get("BUILD_TIMEOUT", cls.build_timeout)),
                   keep_workdir=e.get("KEEP_WORKDIR", "0") == "1",
                   require_model=e.get("VLM_REQUIRED", "0") == "1",
                   use_cv=e.get("USE_OPENCV", "1") == "1",
                   retries=int(e.get("SGL_RETRIES", cls.retries)))

    @property
    def tools(self):
        return os.path.join(self.repo, "tools", "blender")


class StepFailed(Exception):
    def __init__(self, step, message):
        super().__init__(f"{step}: {message}")
        self.step = step


class JobCancelled(Exception):
    """Raised by the progress callback when the job's row is gone (the owner deleted the
    character). run_job stops, deletes photos/<job>/ and builds/<job>/, and re-raises it."""


@dataclass
class JobLog:
    """Job log + progress reporting: progress(state, step, log_text) is called on every step
    change and at most every `every` seconds for plain log lines."""
    progress: object = None
    every: float = 5.0
    lines: list = field(default_factory=list)
    state: str = "spec"
    step: str = "spec"
    _last: float = 0.0

    def text(self):
        return "\n".join(self.lines) + ("\n" if self.lines else "")

    def __call__(self, line):
        self.lines.append(line.rstrip("\n"))
        if self.progress and time.monotonic() - self._last >= self.every:
            self._push()

    def set(self, state, step=None):
        self.state, self.step = state, step or state
        self.lines.append(f"== {self.step}")
        self._push()

    def _push(self):
        self._last = time.monotonic()
        if self.progress:
            self.progress(self.state, self.step, self.text())


def run_streaming(cmd, timeout, on_line, cwd=None, env=None):
    """Run cmd, feed each stdout/stderr line to on_line, kill the whole process group after
    timeout seconds. Returns the exit code; raises TimeoutError."""
    proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            errors="replace", bufsize=1, start_new_session=True)
    q = queue.Queue()

    def pump():
        for line in proc.stdout:
            q.put(line)
        q.put(None)

    threading.Thread(target=pump, daemon=True).start()
    def kill():
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()

    deadline = time.monotonic() + timeout
    try:
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                kill()
                raise TimeoutError(f"{os.path.basename(cmd[0])} timed out after {timeout:.0f} s")
            try:
                line = q.get(timeout=min(1.0, left))
            except queue.Empty:
                continue
            if line is None:
                break
            on_line(line.rstrip("\n"))
    except BaseException:
        if proc.poll() is None:  # on_line raised (e.g. JobCancelled): don't leave Blender running
            kill()
        raise
    return proc.wait()


def _load_tool(cfg, name):
    path = os.path.join(cfg.tools, name + ".py")
    spec = importlib.util.spec_from_file_location(f"sgl_tool_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def parse_build_report(lines):
    for line in reversed(lines):
        i = line.find("SGL_BUILD_REPORT ")
        if i >= 0:
            return json.loads(line[i + len("SGL_BUILD_REPORT "):])
    return None


# ------------------------------------------------------------------ steps
def step_photos(storage, job_id, work, log, keys=None):
    """Download the job's photos: the keys from jobs.photos (the API's photos/<job>/<i>.jpg), or,
    when the row has none, whatever is under photos/<job>/."""
    if not keys:
        keys = storage.list(f"photos/{job_id}/")
    keys = [k for k in keys if k.lower().endswith(PHOTO_EXTS)]
    if not keys:
        raise StepFailed("spec", f"no photos under photos/{job_id}/")
    out = []
    os.makedirs(os.path.join(work, "photos"), exist_ok=True)
    for k in keys[:4]:
        data = storage.get(k)
        with open(os.path.join(work, "photos", os.path.basename(k)), "wb") as f:
            f.write(data)
        out.append(data)
    log(f"spec: {len(out)} photo(s)")
    return out


def step_spec(photos, name, backend, cfg, work, log):
    try:
        spec, info = spec_ai.generate_spec(photos, BUILD_ID, name, backend, use_cv=cfg.use_cv,
                                           require_model=cfg.require_model, log=log)
    except spec_ai.VLMError as e:
        raise StepFailed("spec", str(e)) from e
    char_dir = os.path.join(work, "art", BUILD_ID)
    os.makedirs(char_dir, exist_ok=True)
    with open(os.path.join(char_dir, "character.json"), "w") as f:
        json.dump(spec, f, indent=2)
    log("spec: " + json.dumps(spec))
    return spec, info


def step_face(cfg, work, log):
    art = os.path.join(work, "art")
    out = os.path.join(art, BUILD_ID, "textures")  # "final" face art for the builder
    env = dict(os.environ, SGL_ART_DIR=art)
    try:
        rc = run_streaming([cfg.python, os.path.join(cfg.tools, "sgl_face_gen.py"), BUILD_ID, out],
                           cfg.face_timeout, log, cwd=cfg.repo, env=env)
    except TimeoutError as e:
        raise StepFailed("face", str(e)) from e
    if rc != 0:
        raise StepFailed("face", f"sgl_face_gen.py exited {rc}")
    return out


def step_build(cfg, work, jlog):
    """Blender build + export + builder-side validation + preview renders (one Blender run)."""
    build, actors, art = (os.path.join(work, d) for d in ("build", "actors", "art"))
    cmd = [os.path.join(cfg.tools, "run_blender.sh"), os.path.join(cfg.tools, "build_character.py"), "--",
           BUILD_ID, "--art-dir", art, "--build-dir", build, "--actors-dir", actors]
    env = dict(os.environ, BLENDER=cfg.blender, SGL_RETRIES=str(cfg.retries), PYTHONDONTWRITEBYTECODE="1")
    seen = set()

    def on_line(line):
        jlog(line)
        for marker, state in MARKERS:
            if state not in seen and line.startswith(marker):
                seen.add(state)
                jlog.set(state)
        if line.startswith("run_blender.sh: Blender crashed"):
            jlog.set("build")  # retry starts from scratch
            seen.clear()

    jlog.set("build")
    try:
        rc = run_streaming(cmd, cfg.build_timeout, on_line, cwd=cfg.repo, env=env)
    except TimeoutError as e:
        raise StepFailed(jlog.step, str(e)) from e
    report = parse_build_report(jlog.lines)
    if report is None:
        raise StepFailed(jlog.step, f"Blender exited {rc} without a build report")
    val = report.get("validation") or {}
    if not val.get("ok"):
        raise StepFailed("validate", f"export validation failed: {val.get('errors')}")
    if rc != 0:
        raise StepFailed(jlog.step, f"Blender exited {rc}")
    return report


def step_validate(cfg, work, log):
    """Re-validate the export outside Blender, and check it still validates after the deploy rename."""
    validate_export = _load_tool(cfg, "validate_export")
    actor = os.path.join(work, "actors", BUILD_ID)
    rep, _ = validate_export.validate(actor, BUILD_ID)
    if not rep["ok"]:
        raise StepFailed("validate", f"validate_export: {rep['errors']}")
    with tempfile.TemporaryDirectory() as tmp:
        renamed = actor_rename.rename_actor(actor, tmp, "guest_8")
        rep2, _ = validate_export.validate(renamed, "guest_8")
    if not rep2["ok"]:
        raise StepFailed("validate", f"renamed export (guest_8) fails validation: {rep2['errors']}")
    log("validate: export OK (also as guest_8)")
    return rep


def step_preview(spec, job_id, work, log):
    prev = os.path.join(work, "build", "previews")
    files = sorted(f for f in os.listdir(prev) if f.endswith(".png")) if os.path.isdir(prev) else []
    if "front.png" not in files:
        raise StepFailed("preview", f"no front.png in {prev}")
    card = portrait.pick_card_color(job_id, avoid=(spec["colors"].get("hair"), spec["colors"].get("top")))
    info = portrait.make_portrait(prev, os.path.join(work, "portrait.png"), card)
    log(f"preview: {len(files)} renders, portrait from {info['source']}, card {info['card_color']}")
    return files, info


def step_store(storage, job_id, work, spec, report, spec_info, previews, portrait_info, jlog):
    prefix = f"builds/{job_id}/"
    uploads = {"character.json": os.path.join(work, "art", BUILD_ID, "character.json"),
               "portrait.png": os.path.join(work, "portrait.png")}
    br = os.path.join(work, "build", "build_report.json")
    if os.path.isfile(br):
        uploads["build_report.json"] = br
    browser_model = os.path.join(work, "build", "preview.glb")
    if os.path.isfile(browser_model):
        uploads["preview.glb"] = browser_model
    for f in previews:
        uploads[f"previews/{f}"] = os.path.join(work, "build", "previews", f)
    actor = os.path.join(work, "actors", BUILD_ID)
    for f in sorted(os.listdir(actor)):
        uploads[f"actors/{BUILD_ID}/{f}"] = os.path.join(actor, f)
    sheet = os.path.join(work, "art", BUILD_ID, "textures", "preview_sheet.png")
    if os.path.isfile(sheet):
        uploads["face_sheet.png"] = sheet
    manifest = {
        "job": str(job_id),
        "build_id": BUILD_ID,
        "name": spec["name"],
        "actor_dir": prefix + f"actors/{BUILD_ID}/",
        "portrait": prefix + "portrait.png",
        "browser_model": prefix + "preview.glb" if "preview.glb" in uploads else None,
        "card_color": portrait_info["card_color"],
        "previews": {os.path.splitext(f)[0]: prefix + "previews/" + f for f in previews},
        "files": sorted(prefix + k for k in uploads) + [prefix + "manifest.json", prefix + "log.txt"],
        "tris": report.get("tris"),
        "hair_style": spec["build"]["hair_style"],
        "build_seconds": report.get("seconds"),
        "spec_notes": spec_info.get("notes", []),
        "photo_samples": spec_info.get("samples", {}),
        "deploy": f"actor_rename.py <actors/{BUILD_ID}> <mod actors dir> guest_<n>; "
                  f"portrait.png -> textures/sgl_portrait_guest_<n>.png",
    }
    for key, path in uploads.items():
        storage.put_file(prefix + key, path)
    mpath = os.path.join(work, "manifest.json")
    with open(mpath, "w") as f:
        json.dump(manifest, f, indent=2)
    storage.put_file(prefix + "manifest.json", mpath)
    jlog(f"store: {len(uploads) + 2} files -> {prefix}")
    lpath = os.path.join(work, "log.txt")
    with open(lpath, "w") as f:
        f.write(jlog.text())
    storage.put_file(prefix + "log.txt", lpath)
    return manifest


def artifacts_of(manifest):
    """jobs.artifacts (schema.sql worker contract): object keys only, so the API never lists S3."""
    prefix = f"builds/{manifest['job']}/"
    return {"build_id": manifest["build_id"], "prefix": prefix, "manifest": prefix + "manifest.json",
            "character_json": prefix + "character.json", "portrait": manifest["portrait"],
            "browser_model": manifest.get("browser_model"),
            "previews": sorted(manifest["previews"].values()), "actor_dir": manifest["actor_dir"],
            "files": list(manifest["files"])}


# ------------------------------------------------------------------ job
def run_job(job_id, name, storage, backend, cfg, progress=None, photos=None):
    """Run every step. Returns {"spec", "manifest", "artifacts", "log"}; raises StepFailed with
    .log (photos are deleted and the work dir removed either way). progress(state, step,
    log_text) reports as it goes; if it raises JobCancelled the job stops, builds/<job>/ is
    deleted too, and JobCancelled propagates. photos: the object keys from jobs.photos."""
    jlog = JobLog(progress)
    work = os.path.join(cfg.work_root, str(job_id))
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    t0 = time.monotonic()

    def cleanup(ok):
        try:
            n = storage.delete_prefix(f"photos/{job_id}/")
            jlog(f"photos: deleted {n} object(s)")
        except Exception as e:  # noqa: BLE001 - logged; the worker retries the delete at startup
            jlog(f"photos: DELETE FAILED: {e}")
        if not (cfg.keep_workdir or (not ok and os.environ.get("KEEP_FAILED") == "1")):
            shutil.rmtree(work, ignore_errors=True)

    try:
        jlog.set("spec")
        photo_data = step_photos(storage, job_id, work, jlog, photos)
        spec, spec_info = step_spec(photo_data, name, backend, cfg, work, jlog)
        jlog.set("face")
        step_face(cfg, work, jlog)
        report = step_build(cfg, work, jlog)  # build -> export -> validate -> preview (markers)
        step_validate(cfg, work, jlog)        # outside Blender + deploy-rename check
        if jlog.state != "preview":
            jlog.set("preview")
        previews, pinfo = step_preview(spec, job_id, work, jlog)
        jlog.set("preview", "store")
        jlog(f"build done in {time.monotonic() - t0:.0f} s")
        manifest = step_store(storage, job_id, work, spec, report, spec_info, previews, pinfo, jlog)
    except JobCancelled:
        jlog.progress = None  # the row is gone: nothing more to report
        jlog(f"cancelled at {jlog.step}: the character was deleted")
        cleanup(False)
        discard_build(storage, job_id, jlog)
        raise
    except Exception as e:
        jlog.progress = None  # the caller writes the final state + log (finish_job)
        err = e if isinstance(e, StepFailed) else StepFailed(jlog.step, f"{type(e).__name__}: {e}")
        jlog(f"FAILED at {err.step}: {err}")
        cleanup(False)
        err.log = jlog.text()
        if err is e:
            raise
        raise err from e
    jlog.progress = None
    cleanup(True)
    return {"spec": spec, "manifest": manifest, "artifacts": artifacts_of(manifest), "log": jlog.text()}


def discard_build(storage, job_id, log=print):
    """Delete builds/<job>/ (the job was cancelled: nothing may outlive the deleted character)."""
    try:
        n = storage.delete_prefix(f"builds/{job_id}/")
        log(f"builds: deleted {n} object(s)")
    except Exception as e:  # noqa: BLE001 - storage lifecycle rules catch strays
        log(f"builds: DELETE FAILED: {e}")
