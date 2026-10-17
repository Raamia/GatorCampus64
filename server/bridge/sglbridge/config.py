"""Bridge configuration from the environment (server/deploy/bridge.env.example documents every key)."""
from __future__ import annotations

import os
import shlex
from dataclasses import dataclass
from pathlib import Path

from .deploy import DEFAULT_RENAME_TOOL
from .game import default_command

# the repo checkout the bridge runs from: its mods/sgl64 holds the shipped guest placeholders
REPO_MOD = Path(__file__).resolve().parents[3] / "mods" / "sgl64"


@dataclass
class Config:
    savepath: str
    mod_dir: str
    state_dir: str
    game_cmd: list[str]
    game_cwd: str | None
    line_buffer: bool
    api_url: str | None
    auth0_domain: str | None
    auth0_client_id: str | None
    auth0_audience: str | None
    auth0_issuer: str | None
    m2m_domain: str | None
    m2m_client_id: str | None
    m2m_client_secret: str | None
    deploys: bool
    placeholder_mod: str | None
    actor_rename: str
    deploy_poll: float
    deploy_gap: float
    announce_wait: float
    leaderboard_poll: float = 60.0

    @property
    def login_enabled(self) -> bool:
        return bool(self.auth0_domain and self.auth0_client_id and self.auth0_audience)

    @property
    def api_enabled(self) -> bool:
        return bool(self.api_url and self.m2m_client_id and self.m2m_client_secret
                    and (self.m2m_domain or self.auth0_domain) and self.auth0_audience)

    @property
    def modfs_path(self) -> Path:
        return Path(self.savepath) / "sav" / "sgl64.modfs"


def _flag(v: str | None, default: bool) -> bool:
    if v is None or v == "":
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def from_env(env: dict[str, str] | None = None) -> Config:
    e = dict(os.environ if env is None else env)
    g = lambda k: (e.get(k) or "").strip() or None  # noqa: E731
    savepath = g("SGL_SAVEPATH") or "/srv/sgl"
    cmd = shlex.split(e["GAME_CMD"]) if g("GAME_CMD") else default_command(savepath, g("GAME_BIN") or "/opt/sm64coopdx/sm64coopdx")
    return Config(
        savepath=savepath,
        mod_dir=g("SGL_MOD_DIR") or str(Path(savepath) / "mods" / "sgl64"),
        state_dir=g("SGL_BRIDGE_STATE") or str(Path(savepath) / "bridge"),
        game_cmd=cmd,
        game_cwd=g("GAME_CWD") or "/opt/sm64coopdx",
        line_buffer=_flag(e.get("GAME_LINE_BUFFER"), True),
        api_url=g("API_URL"),
        auth0_domain=g("AUTH0_DOMAIN"),
        auth0_client_id=g("AUTH0_CLIENT_ID"),
        auth0_audience=g("AUTH0_AUDIENCE"),
        auth0_issuer=g("AUTH0_ISSUER"),
        m2m_domain=g("AUTH0_M2M_DOMAIN"),
        m2m_client_id=g("AUTH0_M2M_CLIENT_ID"),
        m2m_client_secret=g("AUTH0_M2M_CLIENT_SECRET"),
        deploys=_flag(e.get("SGL_DEPLOYS"), True),
        placeholder_mod=g("SGL_PLACEHOLDER_MOD") or (str(REPO_MOD) if REPO_MOD.is_dir() else None),
        actor_rename=g("SGL_ACTOR_RENAME") or str(DEFAULT_RENAME_TOOL),
        deploy_poll=float(g("SGL_DEPLOY_POLL") or 30),
        deploy_gap=float(g("SGL_DEPLOY_MIN_GAP") or 300),
        announce_wait=float(g("SGL_DEPLOY_ANNOUNCE") or 60),
        leaderboard_poll=float(g("SGL_LEADERBOARD_POLL") or 60),
    )
