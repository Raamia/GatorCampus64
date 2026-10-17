"""Game -> bridge events: `SGLEVT {json}` lines on the game's stdout (spec §6.2, mods/sgl64/sgl_bridge.lua)."""
from __future__ import annotations

import json
from typing import Any

PREFIX = "SGLEVT "


def parse_line(line: str) -> tuple[dict[str, Any] | None, str | None]:
    """Split one stdout line into (event, other_text).

    event: the decoded SGLEVT object (a dict with a string "t"), or None.
    other_text: whatever else is on the line, for the journal (None when nothing).
    The marker is searched anywhere in the line: the engine's own block-buffered printf output can
    end up in front of a Lua print() (which flushes) on the same line.
    """
    line = line.rstrip("\r\n")
    at = line.find(PREFIX + "{")
    if at < 0:
        return None, (line if line.strip() else None)
    before = line[:at]
    payload = line[at + len(PREFIX):]
    try:
        ev = json.loads(payload)
    except ValueError:
        return None, line
    if not isinstance(ev, dict) or not isinstance(ev.get("t"), str):
        return None, line
    return ev, (before if before.strip() else None)


def event_payload(ev: dict[str, Any]) -> dict[str, Any]:
    """The event without its type: the `payload` of POST /events."""
    return {k: v for k, v in ev.items() if k != "t"}
