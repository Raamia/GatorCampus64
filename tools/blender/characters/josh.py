"""Josh: Anh's head (round face, straight black mushroom cut with side-swept bangs,
thick black rectangular glasses) on a browner skin, plain black t-shirt, dark jeans,
white sneakers. Donald (based_on josh) inherits this module: Josh without glasses.

Everything of Anh's comes from characters/anh.py, re-exported below. Its pieces are
gated on the spec being built, so Josh gets the glasses (his build.accessories lists
glasses_thick_rectangular), Donald gets no glasses, and neither gets the jersey
stripes / number / socks. Face art: art/josh/textures (Anh's art re-skinned with Josh's
colours, see make_textures.py there); Donald uses it through based_on.

The only addition is the plain tee's sleeve end (post_build).
"""
import bpy

import sgl_characters

_anh = sgl_characters._module_for("anh")

HAIR_STYLE = _anh.HAIR_STYLE
ACCESSORIES = _anh.ACCESSORIES
head_parts = _anh.head_parts
head_roles = _anh.head_roles

# Plain short tee sleeves. With sleeves "short" the builder only makes the forearm skin,
# so the sleeve is Mario's whole upper arm, whose tapered end cap (past the elbow joint)
# sits inside the bare forearm and pokes through it as black slivers whenever the elbow
# bends (front / back / side previews). The sleeve ends where Anh's jersey sleeve ends
# (anh.SLEEVE[1], a fraction of the upper arm shoulder -> elbow; Josh is Anh's build) and
# the rest of the upper arm, end cap included, becomes skin: the slivers are then skin
# on skin, and the tee sleeve has a real person's length instead of reaching the elbow.
TEE_SLEEVE_END = _anh.SLEEVE[1]


def tee_sleeve_ends(spec, mats):
    acc = spec.get("build", {}).get("accessories", [])
    if spec.get("build", {}).get("sleeves", "long") != "short" or "jersey_stripes" in acc:
        return 0  # long sleeves, or Anh's jersey (it cuts its own sleeve + cuff band)
    obj, arm = bpy.data.objects["Mario Mesh"], bpy.data.objects["Mario"]
    tris = 0
    for side in ("Left", "Right"):
        grp = f"{side} Arm Color"
        if grp not in obj.vertex_groups:
            continue
        tris += _anh._recolour_limb_bands(obj, arm, grp, grp, f"{side} Forearm",
                                          [(TEE_SLEEVE_END, 1.0, mats["skin"])])
    return tris


def post_build(ctx):
    out = {}
    base = getattr(_anh, "post_build", None)
    if base:
        out["anh"] = base(ctx)
    out["tee_sleeve_end_tris"] = tee_sleeve_ends(ctx["spec"], ctx["mats"])
    return out
