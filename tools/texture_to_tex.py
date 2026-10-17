#!/usr/bin/env python3
"""Wrap a PNG in the small .tex container used by sm64coopdx DynOS mods."""

from __future__ import annotations

import argparse
import struct
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("png", type=Path, help="PNG texture to wrap")
    parser.add_argument("--output", type=Path, help="output path (defaults to the same path with .tex)")
    args = parser.parse_args()

    png_path = args.png
    name = png_path.stem.encode("ascii")
    if len(name) > 255:
        parser.error("texture basename must be at most 255 ASCII bytes")
    payload = png_path.read_bytes()
    if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
        parser.error(f"{png_path} is not a PNG")

    output = args.output or png_path.with_suffix(".tex")
    output.write_bytes(b"\x02" + bytes([len(name)]) + name + struct.pack("<I", len(payload)) + payload)


if __name__ == "__main__":
    main()
