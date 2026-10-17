"""Rename an exported actor (actors/<old>/ -> actors/<new>/) by rewriting its C symbols.

Why: guest slots are assigned by the API when a character is ready (and a character can be
evicted and re-deployed into another slot later), so the worker cannot know `guest_<n>` at
build time. It builds every job under the neutral actor id BUILD_ID ("sglguest"); the deploy
step (bridge) renames the stored export to the slot it lands in.

Fast64 derives every symbol in geo_header.h / geo.inc.c / model.inc.c from the actor name:
`<id>_geo` (the root GeoLayout DynOS looks up), `<id>_<node>` GeoLayouts and display lists,
`mat_<id>_<material>` / `mat_revert_<id>_...`, and the face textures `<id>_eyes_open_rgba16`
(sgl_textures.load_images names the images `<id>_<file>`). In the daniel export every
occurrence is an identifier that starts with `<id>_` at a word boundary or right after
`mat_` / `mat_revert_` (no other prefixes, no file paths), so a token-level rewrite of
`<old>_` -> `<new>_` is exact. The rename refuses ids that are not plain C identifiers and
checks that no `<old>` token is left. tests/test_actor_rename.py renames the real daniel
export and re-runs validate_export on the result.

Usable standalone (stdlib only), e.g. from the bridge:
    python3 actor_rename.py <actors_dir>/sglguest <out_actors_dir> guest_3
"""
import os
import re
import sys

BUILD_ID = "sglguest"
_ID = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
FILES = ("geo_header.h", "geo.inc.c", "model.inc.c")


def _pattern(old):
    # identifier chars before the id are only allowed as the mat_/mat_revert_ prefix ('_')
    return re.compile(r"(?<![A-Za-z0-9])" + re.escape(old) + r"(?=_)")


def rename_source(text, old, new):
    return _pattern(old).sub(new, text)


def rename_actor(src_dir, dst_actors_dir, new_id, old_id=None):
    """Copy src_dir (actors/<old>/) to <dst_actors_dir>/<new_id>/ with the symbols renamed.
    Returns the new directory."""
    old_id = old_id or os.path.basename(os.path.normpath(src_dir))
    for i in (old_id, new_id):
        if not _ID.match(i):
            raise ValueError(f"not a valid actor id: {i!r}")
    if new_id.startswith(old_id + "_") or old_id.startswith(new_id + "_"):
        raise ValueError(f"ids {old_id!r} / {new_id!r} are prefixes of each other; rename via a neutral id")
    out_dir = os.path.join(dst_actors_dir, new_id)
    os.makedirs(out_dir, exist_ok=True)
    left = re.compile(r"(?<![A-Za-z0-9])" + re.escape(old_id) + r"(?![A-Za-z0-9])")
    for name in sorted(os.listdir(src_dir)):
        src = os.path.join(src_dir, name)
        if not os.path.isfile(src):
            continue
        with open(src, encoding="utf-8", errors="surrogateescape") as f:
            text = f.read()
        if name.endswith((".c", ".h")):
            text = rename_source(text, old_id, new_id)
            hit = left.search(text)
            if hit:
                raise ValueError(f"{name}: {old_id!r} still present after rename near "
                                 f"{text[max(0, hit.start() - 40):hit.end() + 40]!r}")
        with open(os.path.join(out_dir, name), "w", encoding="utf-8", errors="surrogateescape") as f:
            f.write(text)
    return out_dir


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit("usage: actor_rename.py <src actor dir> <dst actors dir> <new id>")
    print(rename_actor(sys.argv[1], sys.argv[2], sys.argv[3]))
