# Per-character extensions, so characters can be tuned (and built in parallel)
# without editing the shared modules.
#
# tools/blender/characters/<id>.py may define any of:
#   HAIR_STYLE        dict merged over the build.hair_style preset from sgl_heads.HAIR_STYLES
#                     (a "base" key picks a different preset to start from)
#   ACCESSORIES       {name: fn(ctx)} body accessories; checked before sgl_body.ACCESSORIES
#   head_parts(g, style, spec)
#                     add geometry to the head builder after hair, nose and ears; it is
#                     copied into every head variant (eye states, cap on/off, metal)
#   head_roles(spec, mats) -> {role: material}
#                     materials for any extra roles head_parts used (e.g. "glasses")
#   post_build(ctx)   last hook before the metal rebuild; ctx has spec, mats, report
#   SHORT_SLEEVE_END  fraction of the upper arm (shoulder -> elbow) where a short sleeve
#                     ends (default sgl_body.SLEEVE_END); None when the module builds its
#                     own sleeve end
#   WING_SHIFT        (l, f, u) head-space move of the wing-cap wings (mirrored for the
#                     right wing), applied after post_build (sgl_body.move_wings)
#
# A spec with "based_on": "<other id>" falls back to that character's module.
import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CHAR_DIR = os.path.join(HERE, "characters")
_cache = {}


def _module_for(char_id):
    path = os.path.join(CHAR_DIR, f"{char_id}.py")
    if not os.path.isfile(path):
        return None
    if char_id not in _cache:
        spec = importlib.util.spec_from_file_location(f"sgl_char_{char_id}", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _cache[char_id] = mod
    return _cache[char_id]


def load(spec):
    """The extension module for this character (or the nearest based_on ancestor), or None."""
    from sgl_util import load_spec
    seen = set()
    char_id = spec.get("id")
    while char_id and char_id not in seen:
        seen.add(char_id)
        mod = _module_for(char_id)
        if mod is not None:
            return mod
        char_id = load_spec(char_id).get("based_on")
    return None


def get(spec, name, default=None):
    mod = load(spec)
    return getattr(mod, name, default) if mod is not None else default
