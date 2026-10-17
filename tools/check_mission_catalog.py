#!/usr/bin/env python3
"""Check the companion catalog against registered Reitz and Marston missions."""

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "companion/app/src/data/mission-catalog.json"
SOURCE_FILES = (
    ROOT / "mods/sgl64/wf_reitz_missions.lua",
    ROOT / "mods/sgl64/uf_marston_missions.lua",
)


def lua_string(block: str, field: str) -> str | None:
    match = re.search(rf'^\s*{field}\s*=\s*"((?:[^"\\]|\\.)*)"\s*,?\s*$', block, re.MULTILINE)
    return match.group(1) if match else None


def source_missions() -> dict[str, tuple[str, str]]:
    missions: dict[str, tuple[str, str]] = {}
    registration = re.compile(r"sgl_mission_register\s*\(\s*\{(.*?)^\}\)", re.MULTILINE | re.DOTALL)
    for path in SOURCE_FILES:
        source = path.read_text(encoding="utf-8")
        for match in registration.finditer(source):
            block = match.group(1)
            mission_id = lua_string(block, "id")
            if mission_id is None:
                continue
            title = lua_string(block, "title")
            objective = lua_string(block, "objective")
            if title is None or objective is None:
                raise ValueError(f"{path}: {mission_id} is missing a title or objective")
            if mission_id in missions:
                raise ValueError(f"duplicate mission ID in Lua sources: {mission_id}")
            missions[mission_id] = (title, objective)
    return missions


def main() -> None:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    entries = catalog.get("missions")
    if not isinstance(entries, list) or not entries:
        raise ValueError("catalog must contain a non-empty missions list")

    known = source_missions()
    seen: set[str] = set()
    for entry in entries:
        mission_id = entry.get("id")
        if not isinstance(mission_id, str) or not mission_id:
            raise ValueError("each catalog entry needs a non-empty id")
        if mission_id in seen:
            raise ValueError(f"duplicate mission ID in catalog: {mission_id}")
        seen.add(mission_id)
        if mission_id not in known:
            raise ValueError(f"catalog mission ID is not registered in Lua: {mission_id}")
        source_title, source_objective = known[mission_id]
        if entry.get("title") != source_title:
            raise ValueError(f"{mission_id}: catalog title does not match Lua")
        if entry.get("objective") != source_objective:
            raise ValueError(f"{mission_id}: catalog objective does not match Lua")
        if not isinstance(entry.get("stage"), str) or not entry["stage"]:
            raise ValueError(f"{mission_id}: missing stage")
        if not isinstance(entry.get("act"), int) or entry["act"] < 1:
            raise ValueError(f"{mission_id}: act must be a positive integer")
        if entry.get("minimumPlayers") not in (1, 2, 3, 4):
            raise ValueError(f"{mission_id}: minimumPlayers must be between 1 and 4")
        if not isinstance(entry.get("hint"), str) or not entry["hint"].strip():
            raise ValueError(f"{mission_id}: missing static hint")
        if not isinstance(entry.get("hintTags"), list) or not entry["hintTags"]:
            raise ValueError(f"{mission_id}: missing hint tags")

    print(f"mission catalog: {len(entries)} entries match registered Lua missions")


if __name__ == "__main__":
    main()
